from dotenv import load_dotenv
import os
import pandas as pd
from datetime import datetime, timedelta, timezone

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed

load_dotenv()

data_client = StockHistoricalDataClient(
    api_key=os.getenv("ALPACA_API_KEY"),
    secret_key=os.getenv("ALPACA_SECRET_KEY"),
)

def get_daily_bars(symbol: str, limit: int = 200) -> pd.DataFrame:
    end = datetime.now(timezone.utc) - timedelta(days=2)
    start = end - timedelta(days=365)

    req = StockBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=TimeFrame.Day,
        start=start,
        end=end,
        limit=limit,
        feed=DataFeed.IEX,
    )

    bars = data_client.get_stock_bars(req)
    returned = list(bars.data.keys())
    print("Returned symbols:", returned)

    if symbol not in bars.data or not bars.data[symbol]:
        raise ValueError(f"No bars returned for {symbol}")

    # ✅ bars.data[symbol] is a list of Bar objects -> convert to DataFrame
    rows = []
    for b in bars.data[symbol]:
        # Bar objects support model_dump() in newer versions; fallback to vars()
        if hasattr(b, "model_dump"):
            rows.append(b.model_dump())
        else:
            rows.append(vars(b))

    df = pd.DataFrame(rows)

    # Normalize timestamp column name
    if "timestamp" in df.columns:
        df = df.rename(columns={"timestamp": "time"})
    elif "t" in df.columns:
        df = df.rename(columns={"t": "time"})

    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.sort_values("time").reset_index(drop=True)

    # Make sure standard column names exist
    rename_map = {"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    return df
