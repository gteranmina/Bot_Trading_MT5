import MetaTrader5 as mt5
import json
import os

def start_mt5(username, password, server, path):
    """Inicializa y conecta MetaTrader 5"""
    uname = int(username)
    pword = str(password)
    trading_server = str(server)
    filepath = str(path)

    if mt5.initialize(login=uname, password=pword, server=trading_server, path=filepath):
        print("Bot de Trading Iniciado")
        # imprimir información sobre la cuenta
        account_info = mt5.account_info()
        print(f"Account info: {account_info}\n")

        if mt5.login(login=uname, password=pword, server=trading_server):
            print("Inicio de sesión exitoso en MT5")
            return True
        else:
            print("Error en el inicio de sesión")
            quit()
            return PermissionError
    else:
        print("Fallo en la inicialización de MT5")
        quit()
        return ConnectionAbortedError

def initialize_symbols(symbols):
    """Activa los símbolos que se van a operar"""
    for symbol in symbols:
        mt5.symbol_select(symbol, True)
        print(f"{symbol} activado")
    print("Símbolos listos para operar\n")

def place_order(symbol, order_type, lot_size, sl_pips, tp_pips):
    """Ejecuta órdenes de compra o venta"""
    price = mt5.symbol_info_tick(symbol).ask if order_type == "BUY" else mt5.symbol_info_tick(symbol).bid
    point = mt5.symbol_info(symbol).point
    sl = price - sl_pips * point if order_type == "BUY" else price + sl_pips * point
    tp = price + tp_pips * point if order_type == "BUY" else price - tp_pips * point

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": mt5.ORDER_TYPE_BUY if order_type == "BUY" else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 10,
        "magic": 123456,
        "comment": "Trading Bot",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    return result

def close_mt5():
    """Cierra la conexión con MT5"""
    mt5.shutdown()
    print("Conexión con MT5 cerrada")