import pandas as pd

def trend_ma_signal(df: pd.DataFrame, window: int = 50) -> dict:
    """
    Returns a dict:
    {
      "signal": "BUY"|"SELL"|"HOLD",
      "close": float,
      "ma": float|None,
      "reason": str
    }
    """
    if len(df) < window + 1:
        return {"signal": "HOLD", "close": float(df.iloc[-1]["close"]), "ma": None, "reason": f"Not enough data (<{window})"}

    d = df.copy()
    d["ma"] = d["close"].rolling(window).mean()

    last = d.iloc[-1]
    close = float(last["close"])
    ma = float(last["ma"]) if pd.notna(last["ma"]) else None

    if ma is None:
        return {"signal": "HOLD", "close": close, "ma": None, "reason": "MA not available"}

    if close > ma:
        return {"signal": "BUY", "close": close, "ma": ma, "reason": f"close ({close:.2f}) > MA{window} ({ma:.2f})"}
    if close < ma:
        return {"signal": "SELL", "close": close, "ma": ma, "reason": f"close ({close:.2f}) < MA{window} ({ma:.2f})"}

    return {"signal": "HOLD", "close": close, "ma": ma, "reason": "close == MA"}
