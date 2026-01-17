"""
Main trading bot: orchestrates scanner, strategy, and position management.
"""
import os
import time
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from intraday_data import IntradayDataClient
from stock_scanner import StockScanner
from opening_range_strategy import OpeningRangeBreakout
from position_manager import PositionManager
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

load_dotenv()


class DayTradingBot:
    """
    Opening Range Breakout bot.
    - Scans for gap-up stocks 9:30-10:30 EST
    - Enters on breakout above opening range high
    - Manages stops/targets with risk controls
    """
    
    def __init__(self, starting_capital: float = 40.0, paper: bool = True):
        self.starting_capital = starting_capital
        self.paper = paper
        
        # Initialize components
        self.trading_client = TradingClient(
            api_key=os.getenv("ALPACA_API_KEY"),
            secret_key=os.getenv("ALPACA_SECRET_KEY"),
            paper=paper,
        )
        self.data_client = IntradayDataClient()
        self.scanner = StockScanner()
        self.position_manager = PositionManager(starting_capital=starting_capital)
        
        self.active_symbols = {}  # symbol -> OpeningRangeBreakout()
        self.session_start_time = None
    
    def is_market_open(self) -> bool:
        """Check if market is open (9:30-16:00 EST)."""
        now = datetime.now(timezone.utc)
        est_tz = ZoneInfo("America/New_York")
        est_now = now.astimezone(est_tz)
        
        # Check if weekday (0=Mon, 6=Sun)
        if est_now.weekday() >= 5:
            return False
        
        # Check time (9:30-16:00)
        hour = est_now.hour + est_now.minute / 60.0
        return 9.5 <= hour <= 16.0
    
    def is_trading_window(self) -> bool:
        """Check if in 9:35-10:30 EST trading window."""
        now = datetime.now(timezone.utc)
        est_tz = ZoneInfo("America/New_York")
        est_now = now.astimezone(est_tz)
        
        hour = est_now.hour + est_now.minute / 60.0
        return 9.583 <= hour <= 10.5  # 9:35-10:30
    
    def get_est_time_str(self) -> str:
        """Get current time as EST string."""
        now = datetime.now(timezone.utc)
        est_tz = ZoneInfo("America/New_York")
        est_now = now.astimezone(est_tz)
        return est_now.strftime("%H:%M:%S")
    
    def scan_candidates(self) -> list:
        """Scan for gap-up candidates."""
        print(f"\n[{self.get_est_time_str()}] 🔍 Scanning for gap-up candidates...")
        try:
            candidates = self.scanner.scan_for_breakout_candidates(
                min_gap=0.03,  # 3% gap
                limit=30
            )
            print(f"  Found {len(candidates)} candidates")
            return candidates
        except Exception as e:
            print(f"  Error scanning: {e}")
            return []
    
    def monitor_symbol(self, symbol: str) -> bool:
        """
        Monitor one symbol for opening range breakout.
        Returns: True if trade was entered
        """
        try:
            # Fetch latest 1-min bars
            df = self.data_client.get_1min_bars(symbol, days_back=1)
            
            if df.empty:
                return False
            
            # Initialize strategy if first time
            if symbol not in self.active_symbols:
                self.active_symbols[symbol] = OpeningRangeBreakout()
            
            strategy = self.active_symbols[symbol]
            
            # Step 1: Calculate opening range (first 5 min)
            if strategy.opening_range is None:
                or_range = strategy.calculate_opening_range(df)
                if or_range:
                    print(f"  {symbol} OR: {or_range['low']:.2f}-{or_range['high']:.2f}")
            
            # Step 2: Check for breakout
            last_bar = df.iloc[-1]
            breakout_result = strategy.check_breakout(last_bar)
            
            if breakout_result["signal"] == "LONG_BREAKOUT":
                # Check if we already have a position
                existing = self.position_manager.get_open_position(symbol)
                if existing:
                    return False
                
                # Check kill switches
                can_trade, reason = self.position_manager.can_open_trade()
                if not can_trade:
                    print(f"  {symbol} setup ready but: {reason}")
                    return False
                
                # ENTER TRADE
                entry_price = breakout_result["entry_price"]
                levels = strategy.calculate_stops_and_targets(entry_price)
                
                trade = self.position_manager.open_trade(
                    symbol=symbol,
                    entry_price=entry_price,
                    stop_loss=levels["stop_loss"],
                    take_profit=levels["take_profit_conservative"],
                )
                
                print(f"\n✅ LONG {symbol} @ ${entry_price:.2f} | "
                      f"SL: ${levels['stop_loss']:.2f} | "
                      f"TP: ${levels['take_profit_conservative']:.2f}")
                
                # Place order via Alpaca
                if not self.paper:
                    self._place_order(symbol, trade.quantity, OrderSide.BUY)
                
                return True
            
            return False
        
        except Exception as e:
            print(f"  Error monitoring {symbol}: {e}")
            return False
    
    def monitor_open_positions(self):
        """Check open positions for exits."""
        for trade in list(self.position_manager.open_trades):
            try:
                df = self.data_client.get_1min_bars(trade.symbol, days_back=1)
                if df.empty:
                    continue
                
                last_bar = df.iloc[-1]
                current_price = float(last_bar["close"])
                
                # Simple exit logic: hit SL or TP
                if current_price <= trade.stop_loss:
                    self.position_manager.close_trade(
                        trade,
                        exit_price=trade.stop_loss,
                        reason="Stop loss"
                    )
                    # Place sell order
                    if not self.paper:
                        self._place_order(trade.symbol, trade.quantity, OrderSide.SELL)
                
                elif current_price >= trade.take_profit:
                    self.position_manager.close_trade(
                        trade,
                        exit_price=trade.take_profit,
                        reason="Take profit"
                    )
                    # Place sell order
                    if not self.paper:
                        self._place_order(trade.symbol, trade.quantity, OrderSide.SELL)
            
            except Exception as e:
                print(f"  Error monitoring {trade.symbol}: {e}")
    
    def _place_order(self, symbol: str, quantity: float, side: OrderSide):
        """Place a market order via Alpaca."""
        try:
            order = self.trading_client.submit_order(
                MarketOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=side,
                    time_in_force=TimeInForce.DAY,
                )
            )
            print(f"  Order placed: {order.symbol} {order.qty} @ {side}")
        except Exception as e:
            print(f"  Error placing order: {e}")
    
    def run_session(self):
        """Run one trading session (market open to close)."""
        if not self.is_market_open():
            print("Market is closed")
            return
        
        print(f"\n{'='*60}")
        print(f"🚀 DayTradingBot Session Started")
        print(f"   Capital: ${self.position_manager.current_capital:.2f}")
        print(f"   Paper trading: {self.paper}")
        print(f"{'='*60}")
        
        self.position_manager.reset_daily_limits()
        self.session_start_time = datetime.now(timezone.utc)
        
        # Scan once at market open
        candidates = self.scan_candidates()
        if not candidates:
            print("No candidates found, exiting")
            return
        
        candidate_symbols = [c["symbol"] for c in candidates[:5]]
        
        # Main loop: monitor until 10:30 EST or stop condition
        loop_count = 0
        while self.is_trading_window():
            loop_count += 1
            
            # Monitor candidates for breakouts
            for symbol in candidate_symbols:
                self.monitor_symbol(symbol)
            
            # Monitor open positions for exits
            self.monitor_open_positions()
            
            # Print status every 5 loops
            if loop_count % 5 == 0:
                summary = self.position_manager.get_daily_summary()
                print(f"[{self.get_est_time_str()}] 📊 Open: {summary['open_trades']} | "
                      f"Closed: {summary['closed_trades']} | "
                      f"PnL: {summary['daily_pnl_pct']:+.2f}%")
            
            # Check kill switches
            if self.position_manager.losing_trade_hit:
                print(f"[{self.get_est_time_str()}] ⛔ Losing trade hit, stopping")
                break
            
            daily_loss_pct = self.position_manager.daily_pnl / self.position_manager.starting_capital
            if daily_loss_pct <= -0.08:
                print(f"[{self.get_est_time_str()}] ⛔ Max daily loss hit, stopping")
                break
            
            # Sleep to avoid hammering API
            time.sleep(60)
        
        # Close any remaining positions at market close (at current price, not TP)
        for trade in list(self.position_manager.open_trades):
            try:
                # Get latest price for the symbol
                df = self.data_client.get_1min_bars(trade.symbol, days_back=1)
                if not df.empty:
                    current_price = float(df.iloc[-1]["close"])
                else:
                    current_price = trade.entry_price  # Fallback
            except Exception as e:
                print(f"  Error getting close price for {trade.symbol}: {e}")
                current_price = trade.entry_price
            
            self.position_manager.close_trade(
                trade,
                exit_price=current_price,
                reason="Market close"
            )
        
        # Print final summary
        summary = self.position_manager.get_daily_summary()
        print(f"\n{'='*60}")
        print(f"📈 Session Summary")
        print(f"   Starting capital: ${self.position_manager.starting_capital:.2f}")
        print(f"   Ending capital: ${summary['capital']:.2f}")
        print(f"   Daily P&L: ${summary['daily_pnl']:+.2f} ({summary['daily_pnl_pct']:+.2f}%)")
        print(f"   Trades: {summary['closed_trades']} closed")
        print(f"{'='*60}\n")
        
        # Save trade history
        self.position_manager.save_trades_to_file()


def main():
    # Paper trading by default (set to False to trade live)
    bot = DayTradingBot(starting_capital=40.0, paper=True)
    bot.run_session()


if __name__ == "__main__":
    main()
