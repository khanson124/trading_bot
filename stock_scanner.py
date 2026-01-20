"""
Stock scanner: find high-volume, liquid stocks ready for opening range breakout.
Uses a fixed liquid watchlist and 1-minute open gap detection.
"""
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from intraday_data import IntradayDataClient


class StockScanner:
    # Fixed liquid watchlist (high volume, tight spreads, consistent volume)
    LIQUID_WATCHLIST = [
        "SPY", "QQQ", "IWM", "EEM",  # ETFs
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",  # Mega cap tech
        "TSLA", "META", "NFLX",  # Growth
        "XLF", "XLV", "XLE", "XLY",  # Sectors
    ]
    
    def __init__(self):
        self.data_client = IntradayDataClient()

    def calculate_open_gap(self, symbol: str) -> dict:
        """
        Calculate opening gap using 1-minute bars.
        Gap = (today's first 1-min open - yesterday's last close) / yesterday's close
        This is more consistent and tradable than daily bars.
        
        Returns: {
            "symbol": str,
            "gap_pct": float,
            "prev_close": float,
            "today_open": float
        }
        """
        try:
            gap_info = self.data_client.get_premarket_data(symbol)
            return {
                "symbol": symbol,
                "gap_pct": gap_info.get("gap_pct", 0.0),
                "prev_close": gap_info.get("prev_close", 0.0),
                "today_open": gap_info.get("today_open", 0.0),
            }
        except Exception as e:
            print(f"Error calculating gap for {symbol}: {e}")
            return {"symbol": symbol, "gap_pct": 0.0, "prev_close": 0.0, "today_open": 0.0}

    def scan_for_breakout_candidates(self, 
                                     min_gap: float = 0.01,
                                     limit: int = 20) -> list:
        """
        Scan liquid watchlist for stocks ready for opening range breakout.
        Filters by minimum gap percentage.
        
        Returns: list of dicts with symbol, gap info
        """
        candidates = []
        
        print(f"Scanning {len(self.LIQUID_WATCHLIST)} liquid symbols for gaps >= {min_gap*100:.2f}%...")
        
        for symbol in self.LIQUID_WATCHLIST:
            try:
                gap_info = self.calculate_open_gap(symbol)
                gap_pct = gap_info["gap_pct"]
                
                # Only include if gap meets threshold
                if abs(gap_pct) >= min_gap:
                    candidates.append({
                        "symbol": symbol,
                        "gap_pct": gap_pct,
                        "gap_display": f"{gap_pct*100:+.2f}%",
                        "prev_close": gap_info["prev_close"],
                        "today_open": gap_info["today_open"],
                    })
                    
            except Exception as e:
                print(f"Error processing {symbol}: {e}")
                continue
        
        # Sort by gap % descending
        candidates.sort(key=lambda x: x["gap_pct"], reverse=True)
        
        print(f"Found {len(candidates)} candidates with gap >= {min_gap*100:.2f}%")
        for c in candidates[:10]:
            print(f"  {c['symbol']}: {c['gap_display']}")
        
        return candidates[:limit]


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    scanner = StockScanner()
    candidates = scanner.scan_for_breakout_candidates(limit=15)
    print(f"\n✓ Scanning {len(candidates)} symbols from liquid watchlist")
