"""
Opening Range Breakout strategy logic.
"""
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Optional


class OpeningRangeBreakout:
    """
    9:35 AM - 10:30 AM EST only.
    
    Opening range = first 5 minutes (9:30-9:35)
    Entry: break above range high on volume
    Stop: below range low
    Target: +8-12% or trailing stop at +6%
    """
    
    MARKET_OPEN_EST = 9.5  # 9:30 AM
    TRADING_WINDOW_START = 9.583  # 9:35 AM
    TRADING_WINDOW_END = 10.5  # 10:30 AM
    
    def __init__(self):
        self.opening_range = None
        self.entry_price = None
        self.breakout_triggered = False
    
    def get_est_hour(self, dt: datetime) -> float:
        """Convert UTC datetime to America/New_York hour (float) with DST support."""
        est_tz = ZoneInfo("America/New_York")
        est_dt = dt.astimezone(est_tz)
        return est_dt.hour + est_dt.minute / 60.0
    
    def calculate_opening_range(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Calculate opening range from first 5 minutes (9:30-9:35 EST).
        
        Returns: {
            "high": float,
            "low": float,
            "range_width": float
        }
        """
        if df.empty:
            return None
        
        # Filter to 9:30-9:35 EST window (strictly before 9:35)
        opening_bars = []
        for _, row in df.iterrows():
            hour = self.get_est_hour(row["time"])
            if self.MARKET_OPEN_EST <= hour < self.TRADING_WINDOW_START:
                opening_bars.append(row)
        
        if not opening_bars:
            return None
        
        opening_df = pd.DataFrame(opening_bars)
        high = float(opening_df["high"].max())
        low = float(opening_df["low"].min())
        avg_volume = float(opening_df["volume"].mean())
        
        self.opening_range = {
            "high": high,
            "low": low,
            "range_width": high - low,
            "avg_volume": avg_volume,
        }
        
        return self.opening_range
    
    def check_breakout(self, current_bar: pd.Series, volume_threshold: float = 1.5) -> Optional[Dict]:
        """
        Check if current bar breaks above opening range high on volume.
        Entry price is the close of the breakout bar (realistic fill).
        Volume must be >= volume_threshold * avg_opening_range_volume to confirm.
        
        Returns: {
            "signal": "LONG_BREAKOUT" | "NO_SETUP",
            "entry_price": float,
            "reason": str
        }
        """
        if self.opening_range is None:
            return {"signal": "NO_SETUP", "entry_price": None, "reason": "No opening range"}
        
        # Check time window (9:35-10:30 EST)
        hour = self.get_est_hour(current_bar["time"])
        if not (self.TRADING_WINDOW_START <= hour <= self.TRADING_WINDOW_END):
            return {"signal": "NO_SETUP", "entry_price": None, "reason": "Outside trading window"}
        
        # Check if price broke above opening range high
        close = float(current_bar["close"])
        high = float(current_bar["high"])
        volume = float(current_bar["volume"])
        
        # Check volume confirmation
        min_volume = self.opening_range["avg_volume"] * volume_threshold
        if volume < min_volume:
            return {"signal": "NO_SETUP", "entry_price": None, "reason": f"Volume too low ({volume:.0f} < {min_volume:.0f})"}
        
        if high > self.opening_range["high"]:
            return {
                "signal": "LONG_BREAKOUT",
                "entry_price": close,  # Entry at breakout bar close (realistic fill)
                "reason": f"Breakout above range high ${self.opening_range['high']:.2f} on volume, entry at ${close:.2f}",
            }
        
        return {"signal": "NO_SETUP", "entry_price": None, "reason": "No breakout yet"}
    
    def calculate_stops_and_targets(self, entry_price: float, account_risk: float = 0.05) -> Dict:
        """
        Calculate stop loss and take profit levels.
        
        Args:
            entry_price: Entry price
            account_risk: Max account risk per trade (5%)
        
        Returns: {
            "stop_loss": float,
            "take_profit_aggressive": float,  # +12%
            "take_profit_conservative": float,  # +8%
            "trailing_stop_start": float,  # +6%
        }
        """
        if self.opening_range is None:
            return {}
        
        stop_loss = self.opening_range["low"]
        
        tp_aggressive = entry_price * 1.12  # +12%
        tp_conservative = entry_price * 1.08  # +8%
        trailing_start = entry_price * 1.06  # +6%
        
        return {
            "stop_loss": stop_loss,
            "take_profit_aggressive": tp_aggressive,
            "take_profit_conservative": tp_conservative,
            "trailing_stop_start": trailing_start,
            "risk_per_trade": entry_price - stop_loss,
        }
    
    def should_exit(self, current_price: float, stop_loss: float, 
                   take_profit: float, trailing_stop: Optional[float] = None) -> Optional[Dict]:
        """
        Check exit conditions.
        
        Returns: {
            "signal": "EXIT_PROFIT" | "EXIT_LOSS" | "HOLD",
            "exit_price": float,
            "reason": str
        }
        """
        if current_price <= stop_loss:
            return {
                "signal": "EXIT_LOSS",
                "exit_price": stop_loss,
                "reason": f"Stop loss hit at ${stop_loss:.2f}",
            }
        
        if current_price >= take_profit:
            return {
                "signal": "EXIT_PROFIT",
                "exit_price": take_profit,
                "reason": f"Take profit hit at ${take_profit:.2f}",
            }
        
        if trailing_stop is not None and current_price >= trailing_stop:
            return {
                "signal": "EXIT_PROFIT",
                "exit_price": current_price,
                "reason": f"Trailing stop at ${current_price:.2f}",
            }
        
        return {"signal": "HOLD", "exit_price": None, "reason": "No exit condition"}


if __name__ == "__main__":
    # Test example
    strategy = OpeningRangeBreakout()
    
    # Mock data
    data = {
        "time": [
            pd.Timestamp("2024-01-11 13:30:00", tz="UTC"),
            pd.Timestamp("2024-01-11 13:31:00", tz="UTC"),
            pd.Timestamp("2024-01-11 13:32:00", tz="UTC"),
            pd.Timestamp("2024-01-11 13:35:00", tz="UTC"),
            pd.Timestamp("2024-01-11 13:36:00", tz="UTC"),
        ],
        "open": [100, 101, 101.5, 102, 103],
        "high": [101, 101.5, 102, 102.5, 104],
        "low": [100, 100.5, 101, 101.5, 102.5],
        "close": [100.5, 101, 101.5, 102, 103.5],
        "volume": [10000, 12000, 15000, 18000, 25000],
    }
    df = pd.DataFrame(data)
    
    # Test opening range
    or_range = strategy.calculate_opening_range(df)
    print(f"Opening range: {or_range}")
    
    # Test breakout on last bar
    breakout = strategy.check_breakout(df.iloc[-1])
    print(f"Breakout check: {breakout}")
    
    # Test stops/targets
    if breakout["signal"] == "LONG_BREAKOUT":
        levels = strategy.calculate_stops_and_targets(breakout["entry_price"])
        print(f"Stops & targets: {levels}")
