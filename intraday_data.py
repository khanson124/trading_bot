"""
Fetch intraday (1-min) and premarket data for day trading.
"""
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed


class IntradayDataClient:
    def __init__(self):
        self.client = StockHistoricalDataClient(
            api_key=os.getenv("ALPACA_API_KEY"),
            secret_key=os.getenv("ALPACA_SECRET_KEY"),
        )

    def get_1min_bars(self, symbol: str, days_back: int = 5) -> pd.DataFrame:
        """
        Fetch 1-minute bars for the last N trading days.
        """
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days_back)

        req = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=TimeFrame.Minute,
            start=start,
            end=end,
            feed=DataFeed.IEX,
        )

        bars = self.client.get_stock_bars(req)
        
        if symbol not in bars.data or not bars.data[symbol]:
            return pd.DataFrame()

        rows = []
        for b in bars.data[symbol]:
            if hasattr(b, "model_dump"):
                rows.append(b.model_dump())
            else:
                rows.append(vars(b))

        df = pd.DataFrame(rows)
        
        # Normalize columns
        if "timestamp" in df.columns:
            df = df.rename(columns={"timestamp": "time"})
        elif "t" in df.columns:
            df = df.rename(columns={"t": "time"})

        rename_map = {"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        df["time"] = pd.to_datetime(df["time"], utc=True)
        df = df.sort_values("time").reset_index(drop=True)

        return df

    def get_premarket_data(self, symbol: str) -> dict:
        """
        Get opening gap by comparing today's first 1-min open to yesterday's close.
        This is a tradable gap (not true premarket which requires extended hours data).
        
        Returns: {
            "prev_close": float,
            "today_open": float,
            "gap_pct": float
        }
        """
        try:
            df = self.get_1min_bars(symbol, days_back=5)
            if df.empty:
                return {"prev_close": None, "today_open": None, "gap_pct": 0.0}
            
            gap_pct = self.compute_open_gap_from_1m(df)
            
            # Get yesterday's close and today's open
            ny_tz = ZoneInfo("America/New_York")
            df["ny_date"] = df["time"].dt.tz_convert(ny_tz).dt.date
            
            days = sorted(df["ny_date"].unique())
            if len(days) < 2:
                return {"prev_close": None, "today_open": None, "gap_pct": 0.0}
            
            prev_day, today = days[-2], days[-1]
            prev_close = float(df[df["ny_date"] == prev_day].iloc[-1]["close"])
            today_open = float(df[df["ny_date"] == today].iloc[0]["open"])
            
            return {
                "prev_close": prev_close,
                "today_open": today_open,
                "gap_pct": gap_pct,
            }
        except Exception as e:
            print(f"Error computing gap for {symbol}: {e}")
            return {"prev_close": None, "today_open": None, "gap_pct": 0.0}

    def compute_open_gap_from_1m(self, df: pd.DataFrame) -> float:
        """
        Calculate opening gap from 1-minute bars.
        Gap = (today's first open - yesterday's last close) / yesterday's close
        
        Args:
            df: DataFrame with 1-min bars (UTC timestamps)
        
        Returns:
            gap_pct (e.g., 0.05 = +5% gap)
        """
        if df.empty or "time" not in df.columns:
            return 0.0
        
        df = df.copy()
        ny_tz = ZoneInfo("America/New_York")
        df["ny_date"] = df["time"].dt.tz_convert(ny_tz).dt.date
        
        # Need at least 2 trading days
        days = sorted(df["ny_date"].unique())
        if len(days) < 2:
            return 0.0
        
        prev_day, today = days[-2], days[-1]
        
        prev_close = float(df[df["ny_date"] == prev_day].iloc[-1]["close"])
        today_open = float(df[df["ny_date"] == today].iloc[0]["open"])
        
        if prev_close <= 0:
            return 0.0
        
        return (today_open - prev_close) / prev_close
