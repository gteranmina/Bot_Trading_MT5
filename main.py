import json
import os
import time
import asyncio
import mt5_interface
import strategy

def get_project_settings(import_filepath):
    """Carga las configuraciones desde settings.json"""
    if os.path.exists(import_filepath):
        with open(import_filepath, "r") as f:
            project_settings = json.load(f)
        return project_settings
    else:
        raise ImportError("No se pudo encontrar el archivo de configuración.")

async def trade_symbol(symbol, max_trades):
    """Ejecuta trading en un símbolo de forma independiente"""
    executed_trades = 0

    # Ejecutar una operación de prueba antes de iniciar el ciclo de trading
    print(f"Ejecutando operación de prueba en {symbol}...")
    strategy.execute_strategy(symbol=symbol, lot_size=0.1)
    print(f"Operación de prueba en {symbol} ejecutada.\n")

    while executed_trades < max_trades:
        print(f"Analizando {symbol} en busca de oportunidades...")
        df = strategy.get_market_data(symbol)
        signal, sl_pips, tp_pips = strategy.analyze_market(symbol, df)

        if signal:
            print(f"Señal detectada en {symbol}: {signal}, ejecutando operación...")
            strategy.execute_strategy(symbol=symbol, lot_size=0.1)
            executed_trades += 1
            print(f"Operaciones ejecutadas en {symbol}: {executed_trades}/{max_trades}")

            await asyncio.sleep(60)  # Espera 60 segundos después de operar
        else:
            print(f"No se detectaron señales en {symbol}, esperando 5 segundos...\n")
            await asyncio.sleep(5)  # Pequeña pausa antes del próximo análisis

    print(f"\n======Se han completado {max_trades} operaciones en {symbol}, deteniendo operaciones.======\n")

async def main():
    import_filepath = "settings.json"
    project_settings = get_project_settings(import_filepath)

    mt5_interface.start_mt5(
        project_settings["username"],
        project_settings["password"],
        project_settings["server"],
        project_settings["mt5Pathway"]
    )

    symbols_to_trade = project_settings["symbols"][:3]  # Toma los primeros 3 mercados
    mt5_interface.initialize_symbols(symbols_to_trade)

    max_trades_per_symbol = 5  # Cada símbolo ejecutará hasta 5 operaciones

    # Crear tareas de trading para cada mercado
    tasks = [trade_symbol(symbol, max_trades_per_symbol) for symbol in symbols_to_trade]

    # Ejecutar todas las tareas en paralelo
    await asyncio.gather(*tasks)

    print("Se han completado todas las operaciones, cerrando el bot.")
    mt5_interface.close_mt5()

# Ejecutar el bot de forma asíncrona
asyncio.run(main())
