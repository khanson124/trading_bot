import csv
import os
from datetime import datetime, timezone

LOG_PATH = os.path.join("logs", "decisions.csv")

def log_decision(symbol: str, window: int, result: dict):
    """
    Appends a row to logs/decisions.csv
    """
    os.makedirs("logs", exist_ok=True)

    row = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "window": window,
        "signal": result.get("signal"),
        "close": result.get("close"),
        "ma": result.get("ma"),
        "reason": result.get("reason"),
    }

    file_exists = os.path.exists(LOG_PATH)

    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
