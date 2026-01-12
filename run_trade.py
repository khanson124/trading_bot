print("1) imports starting...")

from data import get_daily_bars
from strategy import trend_ma_signal
from logger import log_decision
from trader import execute_signal

print("2) imports done.")

SYMBOL = "SPY"
WINDOW = 50
NOTIONAL = 25.0

print("3) fetching bars...")
df = get_daily_bars(SYMBOL, limit=200)
print("4) bars fetched:", len(df))

print("5) generating signal...")
result = trend_ma_signal(df, window=WINDOW)
print("6) signal:", result)

print("7) logging decision...")
log_decision(SYMBOL, WINDOW, result)
print("8) logged.")

print("9) executing trade...")
trade_result = execute_signal(SYMBOL, result["signal"], notional_usd=NOTIONAL)
print("10) TRADE RESULT:", trade_result)
