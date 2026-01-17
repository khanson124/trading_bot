"""
Position manager: tracks open positions, risk controls, kill switches.
"""
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime, timezone
import json


@dataclass
class Trade:
    """Single trade record."""
    symbol: str
    entry_price: float
    entry_time: datetime
    quantity: float
    stop_loss: float
    take_profit: float
    
    # Exit info
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    
    def close(self, exit_price: float, exit_time: datetime, reason: str):
        """Close the trade."""
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.exit_reason = reason
        self.pnl = (exit_price - self.entry_price) * self.quantity
        self.pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100
    
    def to_dict(self):
        return {
            "symbol": self.symbol,
            "entry_price": self.entry_price,
            "entry_time": self.entry_time.isoformat(),
            "quantity": self.quantity,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "exit_price": self.exit_price,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "exit_reason": self.exit_reason,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
        }


class PositionManager:
    """
    Manages open positions and enforces kill switches:
    - Max 2 trades per day
    - Stop trading after 1 losing trade
    - Max -8% daily loss
    """
    
    def __init__(self, starting_capital: float = 40.0):
        self.starting_capital = starting_capital
        self.current_capital = starting_capital
        self.open_trades: List[Trade] = []
        self.closed_trades: List[Trade] = []
        
        self.trades_today = 0
        self.losing_trade_hit = False
        self.daily_pnl = 0.0
        
        # Kill switch thresholds
        self.MAX_TRADES_PER_DAY = 2
        self.MAX_DAILY_LOSS_PCT = -0.08
        self.POSITION_SIZE_PCT = 0.8  # Use 80% of capital per trade
    
    def reset_daily_limits(self):
        """Reset daily counters (call at market open)."""
        self.trades_today = 0
        self.losing_trade_hit = False
        self.daily_pnl = 0.0
    
    def can_open_trade(self) -> tuple[bool, str]:
        """
        Check if we can open a new trade.
        Returns: (can_trade, reason)
        """
        # Kill switch 1: Max 2 trades/day
        if self.trades_today >= self.MAX_TRADES_PER_DAY:
            return False, "Max 2 trades/day reached"
        
        # Kill switch 2: Stop after losing trade
        if self.losing_trade_hit:
            return False, "Stopped after losing trade"
        
        # Kill switch 3: Max daily loss
        daily_loss_pct = self.daily_pnl / self.starting_capital
        if daily_loss_pct <= self.MAX_DAILY_LOSS_PCT:
            return False, f"Max daily loss (-8%) reached: {daily_loss_pct*100:.2f}%"
        
        return True, "OK"
    
    def calculate_position_size(self, entry_price: float, stop_loss: float) -> float:
        """
        Calculate position size based on risk management.
        Risk per trade = entry_price - stop_loss
        Size = (account_risk_$) / (risk_per_share)
        """
        risk_per_share = entry_price - stop_loss
        if risk_per_share <= 0:
            return 0
        
        # Risk max 2% per trade on $40 account = $0.80
        account_risk = self.current_capital * 0.02
        position_size = account_risk / risk_per_share
        
        return position_size
    
    def open_trade(self, symbol: str, entry_price: float, 
                   stop_loss: float, take_profit: float) -> Trade:
        """
        Open a new trade.
        """
        can_trade, reason = self.can_open_trade()
        if not can_trade:
            raise ValueError(f"Cannot open trade: {reason}")
        
        position_size = self.calculate_position_size(entry_price, stop_loss)
        if position_size <= 0:
            raise ValueError("Position size <= 0")
        
        trade = Trade(
            symbol=symbol,
            entry_price=entry_price,
            entry_time=datetime.now(timezone.utc),
            quantity=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        
        self.open_trades.append(trade)
        self.trades_today += 1
        
        return trade
    
    def close_trade(self, trade: Trade, exit_price: float, reason: str):
        """
        Close an open trade.
        """
        trade.close(exit_price, datetime.now(timezone.utc), reason)
        
        self.open_trades.remove(trade)
        self.closed_trades.append(trade)
        
        # Update daily P&L and capital
        self.daily_pnl += trade.pnl
        self.current_capital += trade.pnl
        
        # Check if it was a losing trade (kill switch)
        if trade.pnl < 0:
            self.losing_trade_hit = True
        
        print(f"✓ Closed {trade.symbol}: {trade.pnl_pct:+.2f}% (${trade.pnl:+.2f})")
    
    def get_open_position(self, symbol: str) -> Optional[Trade]:
        """Get open trade for symbol, if any."""
        for trade in self.open_trades:
            if trade.symbol == symbol:
                return trade
        return None
    
    def get_daily_summary(self) -> dict:
        """Get summary of today's trading."""
        return {
            "capital": self.current_capital,
            "daily_pnl": self.daily_pnl,
            "daily_pnl_pct": (self.daily_pnl / self.starting_capital) * 100,
            "trades_today": self.trades_today,
            "losing_trade_hit": self.losing_trade_hit,
            "open_trades": len(self.open_trades),
            "closed_trades": len(self.closed_trades),
        }
    
    def save_trades_to_file(self, filename: str = "trades.json"):
        """Save trade history to JSON."""
        trades_data = [t.to_dict() for t in self.closed_trades]
        with open(filename, "w") as f:
            json.dump(trades_data, f, indent=2, default=str)
        print(f"✓ Saved {len(self.closed_trades)} trades to {filename}")


if __name__ == "__main__":
    # Test example
    pm = PositionManager(starting_capital=40.0)
    
    # Can we open a trade?
    can_open, msg = pm.can_open_trade()
    print(f"Can open trade? {can_open} ({msg})")
    
    # Open a trade
    trade = pm.open_trade(
        symbol="AAPL",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=108.0
    )
    print(f"✓ Opened {trade.symbol}: {trade.quantity} shares at ${trade.entry_price}")
    
    # Close it with profit
    pm.close_trade(trade, exit_price=108.0, reason="Take profit")
    
    # Check summary
    print(f"\nDaily summary: {pm.get_daily_summary()}")
