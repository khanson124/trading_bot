"""
Stock scanner: find high-volume, liquid stocks ready for opening range breakout.
Uses a fixed liquid watchlist instead of premarket gap detection.
"""
import os
import pandas as pd
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed
from datetime import datetime, timedelta, timezone


class StockScanner:
    # Fixed liquid watchlist (high volume, tight spreads, consistent volume)
    LIQUID_WATCHLIST = [
        "SPY", "QQQ", "IWM", "EEM",  # ETFs
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",  # Mega cap tech
        "TSLA", "META", "NFLX",  # Growth
        "XLF", "XLV", "XLE", "XLY",  # Sectors
    ]
    
    def __init__(self):
        self.trading_client = TradingClient(
            api_key=os.getenv("ALPACA_API_KEY"),
            secret_key=os.getenv("ALPACA_SECRET_KEY"),
            paper=True,
        )
        self.data_client = StockHistoricalDataClient(
            api_key=os.getenv("ALPACA_API_KEY"),
            secret_key=os.getenv("ALPACA_SECRET_KEY"),
        )

    def get_asset_list(self) -> list:
        """Get all tradable assets from Alpaca."""
        assets = self.trading_client.get_all_assets()
        # Filter: stocks only, tradable
        return [a for a in assets if a.tradable and a.asset_class == "us_equity"]

    def calculate_daily_gap(self, symbol: str) -> dict:
        """
        Calculate gap from yesterday's close to today's open.
        Note: Uses daily bars which show today's open after market opens.
        For true premarket gaps, would need premarket data source.
        
        Returns: {
            "symbol": str,
            "gap_pct": float,
            "prev_close": float,
            "today_open": float
        }
        """
        try:
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=10)

            req = StockBarsRequest(
                symbol_or_symbols=[symbol],
                timeframe=TimeFrame.Day,
                start=start,
                end=end,
                feed=DataFeed.SIP,
            )

            bars = self.data_client.get_stock_bars(req)
            
            if symbol not in bars.data or len(bars.data[symbol]) < 2:
                return {"symbol": symbol, "gap_pct": 0.0, "prev_close": 0.0, "today_open": 0.0}

            bar_list = bars.data[symbol]
            
            # Last bar is today's (may be incomplete)
            # Previous bar is yesterday's close
            if len(bar_list) >= 2:
                prev_close = float(bar_list[-2].close)
                today_open = float(bar_list[-1].open)
                
                if prev_close > 0:
                    gap_pct = (today_open - prev_close) / prev_close
                else:
                    gap_pct = 0.0
                
                return {
                    "symbol": symbol,
                    "gap_pct": gap_pct,
                    "prev_close": prev_close,
                    "today_open": today_open,
                }
            
            return {"symbol": symbol, "gap_pct": 0.0, "prev_close": 0.0, "today_open": 0.0}
        except Exception as e:
            print(f"Error calculating gap for {symbol}: {e}")
            return {"symbol": symbol, "gap_pct": 0.0, "prev_close": 0.0, "today_open": 0.0}

    def scan_for_breakout_candidates(self, 
                                     min_gap: float = 0.01,
                                     limit: int = 20) -> list:
        """
        Scan liquid watchlist for stocks ready for opening range breakout.
        
        Returns: list of dicts with symbol, gap info
        """
        candidates = []
        
        print(f"Scanning {len(self.LIQUID_WATCHLIST)} liquid symbols for gaps...")
        
        for symbol in self.LIQUID_WATCHLIST:
            try:
                gap_info = self.calculate_daily_gap(symbol)
                gap_pct = gap_info["gap_pct"]
                
                # Include all symbols from watchlist (filter by gap if needed)
                # You can adjust min_gap to filter more strictly
                candidates.append({
                    "symbol": symbol,
                    "gap_pct": gap_pct,
                    "gap_display": f"{gap_pct*100:+.2f}%",
                })
                    
            except Exception as e:
                print(f"Error processing {symbol}: {e}")
                continue
        
        # Sort by gap % descending
        candidates.sort(key=lambda x: x["gap_pct"], reverse=True)
        
        print(f"Candidates (showing all {len(candidates)}):")
        for c in candidates[:10]:
            print(f"  {c['symbol']}: {c['gap_display']}")
        
        return candidates[:limit]


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    scanner = StockScanner()
    candidates = scanner.scan_for_breakout_candidates(limit=15)
    print(f"\n✓ Scanning {len(candidates)} symbols from liquid watchlist")
