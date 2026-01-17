"""
Stock scanner: find gapping, high-volume stocks ready for opening range breakout.
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
        # Filter: stocks only, tradable, price $5-$150
        return [a for a in assets if a.tradable and a.asset_class == "us_equity"]

    def calculate_premarket_gap(self, symbol: str) -> float:
        """
        Calculate % gap from previous close to current premarket.
        Returns: gap_pct (e.g., 0.05 = +5%)
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
                return 0.0

            bar_list = bars.data[symbol]
            
            # Last bar is today's incomplete bar
            # Previous bar is yesterday's close
            if len(bar_list) >= 2:
                prev_close = float(bar_list[-2].close)
                current_price = float(bar_list[-1].open)  # Today's open price
                gap = (current_price - prev_close) / prev_close if prev_close > 0 else 0
                return gap
            
            return 0.0
        except Exception as e:
            print(f"Error calculating gap for {symbol}: {e}")
            return 0.0

    def scan_for_breakout_candidates(self, 
                                     min_price: float = 5.0,
                                     max_price: float = 150.0,
                                     min_gap: float = 0.03,
                                     min_volume_spike: float = 1.5,
                                     limit: int = 20) -> list:
        """
        Scan for stocks that:
        - Gapped up >= 3% premarket
        - Have tradable volumes
        - Price between $5-$150
        
        Returns: list of symbols ready for opening range breakout
        """
        candidates = []
        assets = self.get_asset_list()
        
        print(f"Scanning {len(assets)} assets for breakout candidates...")
        
        for asset in assets[:limit]:  # Limit scan to top N for speed
            try:
                gap = self.calculate_premarket_gap(asset.symbol)
                
                if gap >= min_gap:
                    candidates.append({
                        "symbol": asset.symbol,
                        "gap_pct": gap,
                        "price": float(asset.fractionable),
                    })
                    
            except Exception as e:
                print(f"Error processing {asset.symbol}: {e}")
                continue
        
        # Sort by gap % descending
        candidates.sort(key=lambda x: x["gap_pct"], reverse=True)
        
        print(f"Found {len(candidates)} candidates with gap >= {min_gap*100:.1f}%")
        for c in candidates[:5]:
            print(f"  {c['symbol']}: +{c['gap_pct']*100:.2f}%")
        
        return candidates


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    scanner = StockScanner()
    candidates = scanner.scan_for_breakout_candidates(min_gap=0.03, limit=50)
    print(f"\n✓ Found {len(candidates)} gap-up candidates")
