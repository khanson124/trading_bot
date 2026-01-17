"""
Fetch intraday (1-min) and premarket data for day trading.
"""
import os
from datetime import datetime, timedelta, timezone
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
        Get premarket close price and volume (previous day).
        Returns: {"premarket_close": float, "premarket_volume": float, "gap_pct": float}
        """
        end = datetime.now(timezone.utc).replace(hour=13, minute=30, second=0, microsecond=0)
        start = end - timedelta(days=5)

        req = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
            feed=DataFeed.SIP,  # Use SIP for full day data
        )

        bars = self.client.get_stock_bars(req)
        
        if symbol not in bars.data or not bars.data[symbol]:
            return {"premarket_close": None, "premarket_volume": None, "gap_pct": 0}

        bar_list = bars.data[symbol]
        if len(bar_list) < 1:
            return {"premarket_close": None, "premarket_volume": None, "gap_pct": 0}

        last_bar = bar_list[-1]
        premarket_close = float(last_bar.close)
        premarket_volume = float(last_bar.volume)

        return {
            "premarket_close": premarket_close,
            "premarket_volume": premarket_volume,
            "gap_pct": 0,  # Gap will be calculated when comparing to open
        }
