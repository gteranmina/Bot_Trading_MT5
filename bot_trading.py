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
script_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, "config.env")

# Cargar credenciales
load_dotenv(env_path)

MT5_LOGIN = os.getenv("MT5_LOGIN")
MT5_PASSWORD = os.getenv("MT5_PASSWORD")
MT5_SERVER = os.getenv("MT5_SERVER")

if not MT5_LOGIN or not MT5_PASSWORD or not MT5_SERVER:
    print("❌ ERROR: No se encontraron credenciales en config.env")
    sys.exit(1)

MT5_LOGIN = int(MT5_LOGIN)

# Parámetros generales
SIMBOLOS = ["EURUSD", "GBPUSD"]
# Timeframe 1 hora
TIEMPO_FRAME = mt5.TIMEFRAME_H1
LOTE = os.getenv("LOTE")  # Ajustar según la gestión de capital
ORDENES_ACTIVAS = {}  # Diccionario para evitar abrir múltiples órdenes seguidas en un mismo símbolo
CSV_FILENAME = "registro_trading.csv"

# Inicializar archivo CSV si no existe
if not os.path.exists(CSV_FILENAME):
    with open(CSV_FILENAME, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Fecha", "Símbolo", "Orden", "Precio Entrada", "Stop Loss", "Take Profit", "Estado", "Resultado"])


# Conectar a MetaTrader 5
def conectar_mt5():
    if not mt5.initialize():
        print("Error al inicializar MT5:", mt5.last_error())
        return False
    if not mt5.login(int(MT5_LOGIN), password=MT5_PASSWORD, server=MT5_SERVER):
        print("Error al iniciar sesión:", mt5.last_error())
        return False
    return True


# Obtener datos históricos
def obtener_datos(simbolo, num_velas=100):
    rates = mt5.copy_rates_from_pos(simbolo, TIEMPO_FRAME, 0, num_velas)
    if rates is None:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df


# Estrategia basada en Cruce de EMA y ATR con TP ajustado
def analizar_mercado(simbolo, df):
    if df is None or df.empty:
        return None, None, None

    df["EMA_9"] = talib.EMA(df["close"], timeperiod=9)
    df["EMA_21"] = talib.EMA(df["close"], timeperiod=21)
    df["ATR"] = talib.ATR(df["high"], df["low"], df["close"], timeperiod=14)
    df["ADX"] = talib.ADX(df["high"], df["low"], df["close"], timeperiod=14)

    df["Volume_Avg"] = df["tick_volume"].rolling(window=5).mean()
    valid_volume = df["tick_volume"].iloc[-1] >= df["Volume_Avg"].iloc[-1]

    close_price = df["close"].iloc[-1]
    atr = df["ATR"].iloc[-1]
    adx = df["ADX"].iloc[-1]

    min_stop_distance = 10 * 0.0001

    sl_distance = max(atr * 1.5, min_stop_distance)
    tp_distance = max(atr * 1.8, min_stop_distance * 2)

    if adx < 15:
        return None, None, None

    if df["EMA_9"].iloc[-1] > df["EMA_21"].iloc[-1] and df["EMA_9"].iloc[-2] < df["EMA_21"].iloc[-2] and valid_volume:
        return "BUY", close_price - sl_distance, close_price + tp_distance

    elif df["EMA_9"].iloc[-1] < df["EMA_21"].iloc[-1] and df["EMA_9"].iloc[-2] > df["EMA_21"].iloc[-2] and valid_volume:
        return "SELL", close_price + sl_distance, close_price - tp_distance

    return None, None, None


# Guardar datos en CSV
def registrar_operacion(simbolo, tipo_orden, precio_entrada, sl_price, tp_price, estado, resultado="Pendiente"):
    with open(CSV_FILENAME, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), simbolo, tipo_orden, precio_entrada, sl_price, tp_price, estado, resultado])


# Monitorear la operación en segundo plano
def monitorear_operacion(order_id, simbolo, tipo_orden, precio_entrada):
    while True:
        time.sleep(1)
        posiciones = mt5.positions_get(ticket=order_id)

        if not posiciones:
            historial = mt5.history_deals_get(time.time() - 86400, time.time())
            for operacion in historial:
                if operacion.ticket == order_id:
                    resultado = "Ganada" if (operacion.price > precio_entrada and tipo_orden == "BUY") or (operacion.price < precio_entrada and tipo_orden == "SELL") else "Perdida"
                    registrar_operacion(simbolo, tipo_orden, precio_entrada, "N/A", "N/A", "Cerrada", resultado)
                    print(f"📊 Operación {tipo_orden} en {simbolo} {resultado}")
                    ORDENES_ACTIVAS[simbolo] = False  # Permitir nueva operación en este símbolo
                    return


# Ejecutar orden en segundo plano
def ejecutar_orden(simbolo, tipo_orden, lotes, precio_entrada, sl_price, tp_price):
    ORDENES_ACTIVAS[simbolo] = True  # Marcar símbolo como en operación

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
        print(f"❌ Excepción al enviar la orden: {e}")
        registrar_operacion(simbolo, tipo_orden, precio_entrada, sl_price, tp_price, "Error")
        ORDENES_ACTIVAS[simbolo] = False
        return

    if not resultado or not hasattr(resultado, 'retcode'):
        print("❌ Error: mt5.order_send devolvió un resultado inválido")
        registrar_operacion(simbolo, tipo_orden, precio_entrada, sl_price, tp_price, "Error")
        ORDENES_ACTIVAS[simbolo] = False
        return

    if resultado.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"✅ Orden {tipo_orden} ejecutada en {simbolo}")
        registrar_operacion(simbolo, tipo_orden, precio_entrada, sl_price, tp_price, "Ejecutada")
        threading.Thread(target=monitorear_operacion, args=(resultado.order, simbolo, tipo_orden, precio_entrada)).start()
        time.sleep(25)  # Esperar 25 segundos solo después de ejecutar una orden
    else:
        print(f"❌ Error al ejecutar la orden: {resultado.retcode}")
        registrar_operacion(simbolo, tipo_orden, precio_entrada, sl_price, tp_price, "Error")
        ORDENES_ACTIVAS[simbolo] = False  # Permitir nueva operación


# Monitoreo continuo en hilos de ejecución
def monitorear_mercado():
    if not conectar_mt5():
        return

    print("\n\t=======📡 Inicio del Bot AutoTrader 📡=======\n")

    for simbolo in SIMBOLOS:
        print(f"📈 Analizando {simbolo}...")
        ORDENES_ACTIVAS[simbolo] = False
        threading.Thread(target=analizar_simbolo, args=(simbolo,)).start()


def analizar_simbolo(simbolo):
    ultima_impresion = time.time()  # Guardar el tiempo de inicio

    while True:
        df = obtener_datos(simbolo)
        if df is not None and not ORDENES_ACTIVAS[simbolo]:
            tipo_orden, sl_price, tp_price = analizar_mercado(simbolo, df)
            if tipo_orden:
                precio_entrada = mt5.symbol_info_tick(simbolo).ask if tipo_orden == "BUY" else mt5.symbol_info_tick(simbolo).bid
                threading.Thread(target=ejecutar_orden, args=(simbolo, tipo_orden, LOTE, precio_entrada, sl_price, tp_price)).start()

        # Sí han pasado 10 segundos desde la última impresión, mostrar mensaje
        if time.time() - ultima_impresion >= 10:
            print(f"📡 Monitoreando {simbolo} en tiempo real...")
            ultima_impresion = time.time()  # Reiniciar el temporizador

        # Pequeña pausa para evitar que el bucle consuma demasiada CPU
        time.sleep(5)  # Se ejecuta cada segundo sin bloquear el mercado


# Ejecutar bot
if __name__ == "__main__":
    monitorear_mercado()
