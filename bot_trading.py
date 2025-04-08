import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import talib
import time
import csv
import os
import threading
from dotenv import load_dotenv
import sys

# Obtener la ruta del archivo .env en la misma carpeta del ejecutable
script_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(
    os.path.abspath(__file__))
env_path = os.path.join(script_dir, "config.env")

# Cargar credenciales
load_dotenv(env_path)
MT5_LOGIN = os.getenv("MT5_LOGIN")
MT5_PASSWORD = os.getenv("MT5_PASSWORD")
MT5_SERVER = os.getenv("MT5_SERVER")
if not MT5_LOGIN or not MT5_PASSWORD or not MT5_SERVER:
    print("ERROR: No se encontraron credenciales en config.env")
    sys.exit(1)
MT5_LOGIN = int(MT5_LOGIN)

# Parámetros generales
SIMBOLOS = ["EURUSD", "GBPUSD"]
TIEMPO_FRAME = mt5.TIMEFRAME_M15  # Temporalidad principal de 15 minutos
TIEMPO_FRAME_SUP = mt5.TIMEFRAME_H1  # Temporalidad superior para confirmar tendencia
LOTE = float(os.getenv("LOTE", "0.01"))
ORDENES_ACTIVAS = {}
CSV_FILENAME = "registro_trading.csv"

# Inicializar archivo CSV si no existe
if not os.path.exists(CSV_FILENAME):
    with open(CSV_FILENAME, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            ["Fecha", "Símbolo", "Orden", "Precio Entrada", "Stop Loss", "Take Profit", "Estado", "Resultado"])


def conectar_mt5():
    if not mt5.initialize():
        print("Error al inicializar MT5:", mt5.last_error())
        return False
    if not mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
        print("Error al iniciar sesión:", mt5.last_error())
        return False
    return True


def mantener_conexion():
    """
    Función que se ejecuta en un hilo para verificar la conexión a MT5 de forma periódica.
    Si se detecta que la conexión se perdió, intenta reconectarse hasta restablecerla.
    """
    while True:
        # Verifica si la terminal está activa
        terminal_info = mt5.terminal_info()
        if terminal_info is None:
            print("Conexión a MT5 perdida. Intentando reconectar...")
            # Se finaliza la sesión actual
            mt5.shutdown()
            # Se intenta reconectar en bucle cada 5 segundos
            while not conectar_mt5():
                print("No fue posible reconectar a MT5, reintentando en 5 segundos...")
                time.sleep(5)
            print("Conexión a MT5 restablecida.")
        time.sleep(60)  # Verifica cada 60 segundos


def obtener_datos(simbolo, num_velas=100, timeframe=TIEMPO_FRAME):
    rates = mt5.copy_rates_from_pos(simbolo, timeframe, 0, num_velas)
    if rates is None:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df


def analizar_mercado(simbolo, df):
    ultima_impresion_mercado = time.time()
    if df is None or df.empty:
        return None, None, None

    # Cálculo de indicadores en temporalidad M15
    df["EMA_12"] = talib.EMA(df["close"], timeperiod=12)
    df["EMA_26"] = talib.EMA(df["close"], timeperiod=26)
    df["ATR"] = talib.ATR(df["high"], df["low"], df["close"], timeperiod=14)
    df["ADX"] = talib.ADX(df["high"], df["low"], df["close"], timeperiod=14)
    rsi = talib.RSI(df["close"], timeperiod=14)

    # Cálculo del volumen promedio
    df["Volume_Avg"] = df["tick_volume"].rolling(window=5).mean()
    valid_volume = df["tick_volume"].iloc[-1] >= df["Volume_Avg"].iloc[-1]

    close_price = df["close"].iloc[-1]
    atr = df["ATR"].iloc[-1]
    adx = df["ADX"].iloc[-1]
    rsi_last = rsi.iloc[-1]

    if not hasattr(analizar_mercado, "ultimo_debug"):
        analizar_mercado.ultimo_debug = 0
    if time.time() - analizar_mercado.ultimo_debug >= 15:
        print(
            f"DEBUG - Símbolo: {simbolo}, ADX: {adx:.2f}, EMA_12: {df['EMA_12'].iloc[-1]:.5f}, EMA_26: {df['EMA_26'].iloc[-1]:.5f}, Tick Volume: {df['tick_volume'].iloc[-1]}, Volume_Avg: {df['Volume_Avg'].iloc[-1]:.2f}, RSI: {rsi_last:.2f}")
        analizar_mercado.ultimo_debug = time.time()

    # Filtro ADX dinámico según volatilidad
    volatility_ratio = atr / close_price
    if volatility_ratio < 0.005:
        adx_threshold = 15
    elif volatility_ratio < 0.01:
        adx_threshold = 20
    else:
        adx_threshold = 25

    if adx < adx_threshold:
        print(f"DEBUG - ADX {adx:.2f} inferior al umbral dinámico {adx_threshold}")
        return None, None, None

    tolerance = atr * 0.5
    if volatility_ratio < 0.005:
        sl_factor = 1.5
        tp_factor = 2.0
    elif volatility_ratio < 0.01:
        sl_factor = 1.0
        tp_factor = 1.5
    else:
        sl_factor = 0.8
        tp_factor = 1.2

    min_stop_distance = 10 * 0.0001
    sl_distance = max(atr * sl_factor, min_stop_distance)
    tp_distance = max(atr * tp_factor, min_stop_distance * 2)

    ema_diff = df["EMA_12"].iloc[-1] - df["EMA_26"].iloc[-1]
    # Confirmación en timeframe superior (H1)
    df_sup = obtener_datos(simbolo, num_velas=100, timeframe=TIEMPO_FRAME_SUP)
    if df_sup is not None and not df_sup.empty:
        sma50 = df_sup['close'].rolling(window=50).mean().iloc[-1]
    else:
        sma50 = None

    if ema_diff > tolerance and valid_volume and rsi_last < 70:
        if sma50 is not None and close_price < sma50:
            print(f"DEBUG - Tendencia en H1 no alcista para señal BUY: precio {close_price:.5f} < SMA50 {sma50:.5f}")
            return None, None, None
        return "BUY", close_price - sl_distance, close_price + tp_distance
    elif -ema_diff > tolerance and valid_volume and rsi_last > 30:
        if sma50 is not None and close_price > sma50:
            print(f"DEBUG - Tendencia en H1 no bajista para señal SELL: precio {close_price:.5f} > SMA50 {sma50:.5f}")
            return None, None, None
        return "SELL", close_price + sl_distance, close_price - tp_distance

    return None, None, None


def registrar_operacion(simbolo, tipo_orden, precio_entrada, sl_price, tp_price, estado, resultado="Pendiente"):
    with open(CSV_FILENAME, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            time.strftime("%Y-%m-%d %H:%M:%S"),
            simbolo,
            tipo_orden,
            precio_entrada,
            sl_price,
            tp_price,
            estado,
            resultado
        ])


def monitorear_operacion(order_id, simbolo, tipo_orden, precio_entrada):
    while True:
        time.sleep(1)
        posiciones = mt5.positions_get(ticket=order_id)
        if not posiciones:
            historial = mt5.history_deals_get(time.time() - 86400, time.time())
            for operacion in historial:
                if operacion.ticket == order_id:
                    resultado = "Ganada" if (operacion.price > precio_entrada and tipo_orden == "BUY") or \
                                            (operacion.price < precio_entrada and tipo_orden == "SELL") else "Perdida"
                    registrar_operacion(simbolo, tipo_orden, precio_entrada, "N/A", "N/A", "Cerrada", resultado)
                    print(f"Operación {tipo_orden} en {simbolo} {resultado}")
                    ORDENES_ACTIVAS[simbolo] = False
                    return


def ejecutar_orden(simbolo, tipo_orden, lotes, precio_entrada, sl_price, tp_price):
    ORDENES_ACTIVAS[simbolo] = True
    orden = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": simbolo,
        "volume": lotes,
        "type": mt5.ORDER_TYPE_BUY if tipo_orden == "BUY" else mt5.ORDER_TYPE_SELL,
        "price": precio_entrada,
        "sl": sl_price,
        "tp": tp_price,
        "deviation": 10,
        "magic": 123456,
        "comment": "Bot AutoTrader",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC
    }

    try:
        resultado = mt5.order_send(orden)
    except Exception as e:
        print(f"Excepción al enviar la orden: {e}")
        registrar_operacion(simbolo, tipo_orden, precio_entrada, sl_price, tp_price, "Error")
        ORDENES_ACTIVAS[simbolo] = False
        return

    if resultado is None:
        print("Error: mt5.order_send devolvió None")
        registrar_operacion(simbolo, tipo_orden, precio_entrada, sl_price, tp_price, "Error")
        ORDENES_ACTIVAS[simbolo] = False
        return

    try:
        retcode = resultado.retcode
    except Exception as e:
        print(f"Error al acceder a retcode: {e}. Resultado recibido: {resultado}")
        registrar_operacion(simbolo, tipo_orden, precio_entrada, sl_price, tp_price, "Error")
        ORDENES_ACTIVAS[simbolo] = False
        return

    if retcode == mt5.TRADE_RETCODE_DONE:
        print(f"Orden {tipo_orden} ejecutada en {simbolo}")
        registrar_operacion(simbolo, tipo_orden, precio_entrada, sl_price, tp_price, "Ejecutada")
        threading.Thread(target=monitorear_operacion,
                         args=(resultado.order, simbolo, tipo_orden, precio_entrada)).start()
        time.sleep(25)
    else:
        # Registro detallado del error
        error_info = mt5.last_error()
        print(f"Error al ejecutar la orden: retcode {retcode}, error: {error_info}")
        registrar_operacion(simbolo, tipo_orden, precio_entrada, sl_price, tp_price, "Error")
        ORDENES_ACTIVAS[simbolo] = False


def monitorear_mercado():
    if not conectar_mt5():
        return
    print("\n======= Inicio del Bot AutoTrader =======\n")
    for simbolo in SIMBOLOS:
        print(f"Analizando {simbolo}...")
        ORDENES_ACTIVAS[simbolo] = False
        threading.Thread(target=analizar_simbolo, args=(simbolo,)).start()


def analizar_simbolo(simbolo):
    ultima_impresion = time.time()
    while True:
        # Verifica la conexión antes de cada análisis
        if mt5.terminal_info() is None:
            print("Conexión perdida durante el análisis. Intentando reconectar...")
            mt5.shutdown()
            while not conectar_mt5():
                print(f"Reintentando conexión durante el análisis para {simbolo}...")
                time.sleep(5)
            print(f"Conexión restaurada para {simbolo}.")

        df = obtener_datos(simbolo)
        if df is not None and not ORDENES_ACTIVAS[simbolo]:
            tipo_orden, sl_price, tp_price = analizar_mercado(simbolo, df)
            if tipo_orden:
                tick = mt5.symbol_info_tick(simbolo)
                if tick is None:
                    continue
                precio_entrada = tick.ask if tipo_orden == "BUY" else tick.bid
                threading.Thread(target=ejecutar_orden,
                                 args=(simbolo, tipo_orden, LOTE, precio_entrada, sl_price, tp_price)).start()

        if time.time() - ultima_impresion >= 60:
            print(f"Monitoreando {simbolo} en temporalidad 15 minutos...")
            ultima_impresion = time.time()
        time.sleep(1)


if __name__ == "__main__":
    # Inicia el hilo para mantener la conexión de forma periódica
    threading.Thread(target=mantener_conexion, daemon=True).start()
    monitorear_mercado()
