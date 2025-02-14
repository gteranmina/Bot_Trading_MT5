# Bot_Trading_MT5
Este es un bot de trading automatizado para MetaTrader 5 (MT5) que opera en hasta 3 mercados simultáneamente. Utiliza indicadores técnicos como RSI, EMA, MACD, ATR y Volumen para analizar el mercado y ejecutar órdenes automáticamente.

# 📌 Características

✅ Opera hasta 3 mercados simultáneamente. 
✅ Utiliza RSI, EMA, MACD, ATR y volumen para detectar oportunidades.
✅ Optimizado para ahorrar recursos de CPU y memoria.
✅ Detiene la ejecución después de 5 operaciones por mercado.
✅ Totalmente automatizado y diseñado para trabajar con MT5 Desktop.

# ⚙ Requisitos
🔹 MetaTrader 5 (MT5) Desktop.

🔹 Python 3.8+ (Recomendado Python 3.10).

🔹 PyCharm Community Edition (Recomendado para facilitar la instalación y configuración). 

    Enlace de descarga para windows: 
    https://www.jetbrains.com/pycharm/download/download-thanks.html?platform=windows&code=PCC

🔹 Cuenta de trading demo o real en MT5.

# 📥 Instalación

🔹 1️⃣ Descargar el código

    git clone https://github.com/0-RnE/trading-bot-mt5.git
    cd trading-bot-mt5

🔹 2️⃣ Instalar dependencias

Ejecuta el siguiente comando para instalar las librerías necesarias:

    pip install -r requirements.txt

🔹 3️⃣ Configurar settings.json

Edita el archivo settings.json con tus credenciales de MetaTrader 5:

    {
      "username": "TU_NUMERO_DE_CUENTA",
      "password": "TU_CONTRASEÑA",  
      "server": "TU_SERVIDOR",
      "mt5Pathway": "C:/Program Files/MetaTrader 5/terminal64.exe",
      "symbols": ["EURUSD", "USDJPY", "XAUUSD"],
      "timeframe": "M1",
      "pip_size": 0.0001
    }  

🔹 4️⃣ Ejecutar el bot

Para iniciar el bot, ejecuta:

    python3 main.py

# 📜 Uso del Bot

1️⃣ El bot analizará el mercado cada 5 segundos en busca de oportunidades.

2️⃣ Si detecta una señal, ejecutará una orden y esperará 60 segundos antes de operar nuevamente en ese mercado.

3️⃣ Cuando un mercado complete 5 operaciones, dejará de operar ese símbolo.

4️⃣ Cuando todos los mercados hayan completado 5 operaciones, el bot se cerrará automáticamente.

# 🛠 Solución de Problemas

❌ ImportError: No se pudo encontrar el archivo de configuración.

    📌 Solución: Asegúrate de que settings.json está en la misma carpeta que main.py y tiene las credenciales correctas.

❌ Error al inicializar MT5

    📌 Solución: Verifica que MetaTrader 5 esté abierto y que la cuenta tenga trading automático activado en:
    Herramientas > Opciones > Expert Advisors.
