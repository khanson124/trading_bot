import pandas as pd

def trend_ma_signal(df: pd.DataFrame, window: int = 50) -> dict:
    """
    Compute rolling MA and compare latest close to it.
    
    Returns a dict:
    {
      "signal": "BUY"|"SELL"|"HOLD",
      "close": float|None,
      "ma": float|None,
      "reason": str
    }
    
    Note: This uses a simple MA on 1-minute bars (e.g., 50-period = ~50 min MA).
    Best used as a filter (e.g., "only take ORB longs if price > 50-min MA")
    rather than a standalone entry/exit signal for intraday scalps.
    """
    if df is None or df.empty:
        return {"signal": "HOLD", "close": None, "ma": None, "reason": "Empty dataframe"}
    
    d = df.copy()
    
    # Ensure data is sorted by time
    if "time" in d.columns:
        d = d.sort_values("time")
    
    # Validate required column
    if "close" not in d.columns:
        return {"signal": "HOLD", "close": None, "ma": None, "reason": "Missing close column"}
    
    # Need enough data for MA calculation
    if len(d) < window:
        close = float(d.iloc[-1]["close"])
        return {"signal": "HOLD", "close": close, "ma": None, "reason": f"Not enough data (<{window})"}
    
    # Calculate MA efficiently (only over last window)
    last_window = d["close"].tail(window)
    ma = float(last_window.mean()) if pd.notna(last_window.mean()) else None
    close = float(d.iloc[-1]["close"])
    
    if ma is None:
        return {"signal": "HOLD", "close": close, "ma": None, "reason": "MA not available"}
    
    # Use tolerance for floating-point comparison
    price_ma_ratio = abs(close - ma) / ma if ma != 0 else 0.0
    
    if close > ma * 1.000001:  # Tolerance: 0.0001%
        return {"signal": "BUY", "close": close, "ma": ma, "reason": f"close ({close:.2f}) > MA{window} ({ma:.2f})"}
    if close < ma * 0.999999:  # Tolerance: 0.0001%
        return {"signal": "SELL", "close": close, "ma": ma, "reason": f"close ({close:.2f}) < MA{window} ({ma:.2f})"}
    
    return {"signal": "HOLD", "close": close, "ma": ma, "reason": "close ~= MA (within tolerance)"}
