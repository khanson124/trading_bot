from data import get_daily_bars
from strategy import trend_ma_signal
from logger import log_decision

symbols = ["AAPL", "MSFT", "QQQ", "SPY"]
WINDOW = 50

for sym in symbols:
    df = get_daily_bars(sym, limit=200)
    result = trend_ma_signal(df, window=WINDOW)

    print(f"{sym}: close={result['close']:.2f} MA{WINDOW}={result['ma']:.2f} signal={result['signal']}")
    print(f"  reason: {result['reason']}")

    log_decision(sym, WINDOW, result)

print("\nLogged to: logs/decisions.csv")
