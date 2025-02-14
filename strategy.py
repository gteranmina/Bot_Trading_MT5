import pandas as pd
import numpy as np
import ta
import MetaTrader5 as mt5


def get_market_data(symbol, n=100):
    """Obtiene datos de mercado"""
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, n)
    if rates is None:
        print("Error al obtener datos de mercado")
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df


def get_higher_timeframe_trend(symbol, timeframe=mt5.TIMEFRAME_M5, n=50):
    """Obtiene la tendencia en un marco de tiempo mayor"""
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
    if rates is None:
        return False  # Devuelve False si no se pueden obtener datos
    df = pd.DataFrame(rates)
    df["EMA_50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
    return df["close"].iloc[-1] > df["EMA_50"].iloc[-1]  # True si la tendencia es alcista

'''def analyze_market(symbol, df):
    """Usa RSI, EMA, MACD, ATR y Volumen para mejorar señales"""
    if df is None or df.empty:
        return None, None, None

    df["RSI"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    df["EMA_14"] = ta.trend.EMAIndicator(df["close"], window=14).ema_indicator()
    df["EMA_50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
    df["MACD"] = ta.trend.MACD(df["close"]).macd()
    df["ATR"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=14).average_true_range()
    df["Volume_MA"] = df["tick_volume"].rolling(window=20).mean()

    rsi = df["RSI"].iloc[-1]
    ema_50 = df["EMA_50"].iloc[-1]
    macd = df["MACD"].iloc[-1]
    close_price = df["close"].iloc[-1]
    atr = df["ATR"].iloc[-1]
    volume = df["tick_volume"].iloc[-1]
    avg_volume = df["Volume_MA"].iloc[-1]

    higher_timeframe_trend = get_higher_timeframe_trend(symbol)

    if rsi < 30 and macd > 0 and close_price > ema_50 and volume > avg_volume and higher_timeframe_trend:
        return "BUY", atr * 1.5, atr * 3
    elif rsi > 70 and macd < 0 and close_price < ema_50 and volume > avg_volume and not higher_timeframe_trend:
        return "SELL", atr * 1.5, atr * 3
    return None, None, None'''

# funcion que calcula correctamente el SL y TP
def analyze_market(symbol, df):
    """Mejora la precisión de señales usando RSI, EMA, MACD, ATR y confirmación de tendencia."""
    if df is None or df.empty:
        return None, None, None

    # Cálculo de indicadores técnicos
    df["RSI"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    df["ATR"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=14).average_true_range()
    df["EMA_14"] = ta.trend.EMAIndicator(df["close"], window=14).ema_indicator()
    df["EMA_50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
    macd = ta.trend.MACD(df["close"])
    df["MACD"] = macd.macd()
    df["MACD_Hist"] = macd.macd_diff()

    # Últimos valores de los indicadores
    rsi = df["RSI"].iloc[-1]
    atr = df["ATR"].iloc[-1]
    close_price = df["close"].iloc[-1]
    ema_14 = df["EMA_14"].iloc[-1]
    ema_50 = df["EMA_50"].iloc[-1]
    macd_value = df["MACD"].iloc[-1]
    macd_hist = df["MACD_Hist"].iloc[-1]

    # Definir distancia mínima permitida por el broker (p.ej. 10 pips)
    min_stop_distance = 10 * 0.0001  # Para EURUSD, 10 pips = 0.0010

    # Calcular SL y TP en función del ATR (pero asegurando que cumplen la distancia mínima)
    sl_distance = max(atr * 1.2, min_stop_distance)  # Ajustado para menor riesgo
    tp_distance = max(atr * 2.5, min_stop_distance * 2)  # Ajustado para mejor precisión

    # Estrategia mejorada: RSI + MACD + Tendencia EMA + Confirmación MACD Histograma
    if rsi < 30 and macd_value > 0 and macd_hist > 0 and close_price > ema_14 > ema_50:
        sl_price = close_price - sl_distance
        tp_price = close_price + tp_distance
        return "BUY", sl_price, tp_price

    elif rsi > 70 and macd_value < 0 and macd_hist < 0 and close_price < ema_14 < ema_50:
        sl_price = close_price + sl_distance
        tp_price = close_price - tp_distance
        return "SELL", sl_price, tp_price

    return None, None, None  # No se detectó señal

def execute_strategy(symbol, lot_size):
    """Ejecuta la estrategia en base a las señales"""
    print(f"Intentando ejecutar orden en {symbol} con lote {lot_size}...")

    df = get_market_data(symbol, n=50)
    if df is None:
        print(f"No se pudo obtener datos de mercado para {symbol}.")
        return

    signal, sl_pips, tp_pips = analyze_market(symbol, df)

    if signal:
        print(f"Señal detectada: {signal}, preparando solicitud para MT5...")

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_BUY if signal == "BUY" else mt5.ORDER_TYPE_SELL,
            "price": mt5.symbol_info_tick(symbol).ask if signal == "BUY" else mt5.symbol_info_tick(symbol).bid,
            "sl": sl_pips,
            "tp": tp_pips,
            "deviation": 10,
            "magic": 123456,
            "comment": "Trading Bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        print("Enviando orden a MT5 con la siguiente solicitud:")
        print(request)

        result = mt5.order_send(request)

        if result is None:
            print("⚠ ERROR: `mt5.order_send()` devolvió None. La orden no fue enviada.")
        else:
            print("✅ Resumen de la orden enviada:", result)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                print(f"⚠ ERROR EN LA ORDEN: Código {result.retcode}")

    else:
        print("No se detectaron señales de trading.")

