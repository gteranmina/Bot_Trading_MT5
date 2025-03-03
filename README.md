# Bot_Trading_MT5

Este es un bot de trading automatizado para MetaTrader 5 (MT5) que opera en múltiples mercados simultáneamente. La nueva versión utiliza una estrategia basada en el cruce de EMA y el ATR con TP ajustado, complementada con el indicador ADX y validación de volumen para determinar oportunidades de trading con temporalidades de 1H (1 hora).

---

## 📌 Características

- **Multiplicidad de Mercados:** Opera en varios mercados simultáneamente.
- **Estrategia Técnica:** Basada en el cruce de EMA (9 y 21) y en el cálculo del ATR para definir Stop Loss y Take Profit.
- **Filtrado de Señales:** Incorpora ADX y validación de volumen para descartar señales débiles.
- **Ejecución Asíncrona:** Utiliza hilos (threads) para el análisis en tiempo real y la ejecución de órdenes, evitando órdenes duplicadas en un mismo símbolo.
- **Registro Detallado:** Guarda un historial de operaciones en un archivo CSV (**registro_trading.csv**).
- **Manejo de Errores:** Incluye comprobaciones robustas para evitar errores al enviar órdenes, por ejemplo, al intentar operar fuera del horario de mercado.

---

## ⚙ Requisitos

- **MetaTrader 5 (MT5) Desktop**  
  Asegúrate de tener MT5 abierto y con el trading automático habilitado.

- **Python 3.8+** (se recomienda Python 3.10).

- **Librerías Python:**
  - MetaTrader5
  - pandas
  - numpy
  - talib
  - python-dotenv  
  Estas dependencias se pueden instalar utilizando el archivo de requirements.txt.

- **Credenciales de MT5:**  
  Una cuenta de trading demo o real en MT5. Para cambiar las credenciales de la cuenta de MT5, unicamente hay que modificar el archivo "config.env" y escribir las credenciales referentes a la cuenta a operar por el bot.
