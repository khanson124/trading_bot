"""
Trading summary & statistics from trades.json
"""
import json
import pandas as pd
from pathlib import Path
from datetime import datetime


def load_trades(filename: str = "trades.json") -> list[dict]:
    """Load trades from JSON file."""
    if not Path(filename).exists():
        return []
    
    with open(filename, "r") as f:
        return json.load(f)


def calculate_stats(trades: list[dict]) -> dict:
    """Calculate trading statistics."""
    if not trades:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "profit_factor": 0,
            "largest_win": 0,
            "largest_loss": 0,
        }
    
    df = pd.DataFrame(trades)
    
    wins = df[df["pnl"] > 0]
    losses = df[df["pnl"] < 0]
    
    total_pnl = float(df["pnl"].sum())
    win_count = len(wins)
    loss_count = len(losses)
    
    profit_factor = (wins["pnl"].sum() / abs(losses["pnl"].sum())) if len(losses) > 0 else 0
    
    return {
        "total_trades": len(trades),
        "winning_trades": win_count,
        "losing_trades": loss_count,
        "win_rate": (win_count / len(trades) * 100) if len(trades) > 0 else 0,
        "total_pnl": total_pnl,
        "total_pnl_pct": (total_pnl / 40.0) * 100,  # Assuming $40 starting
        "avg_win": float(wins["pnl"].mean()) if len(wins) > 0 else 0,
        "avg_loss": float(losses["pnl"].mean()) if len(losses) > 0 else 0,
        "profit_factor": profit_factor,
        "largest_win": float(wins["pnl"].max()) if len(wins) > 0 else 0,
        "largest_loss": float(losses["pnl"].min()) if len(losses) > 0 else 0,
    }


def print_summary(trades: list[dict]):
    """Print formatted trading summary."""
    if not trades:
        print("No trades found in trades.json")
        return
    
    stats = calculate_stats(trades)
    
    print(f"\n{'='*70}")
    print(f"📊 TRADING SUMMARY")
    print(f"{'='*70}")
    print(f"\nTotal Trades:      {stats['total_trades']}")
    print(f"  ✅ Wins:        {stats['winning_trades']}")
    print(f"  ❌ Losses:      {stats['losing_trades']}")
    print(f"  📈 Win Rate:    {stats['win_rate']:.1f}%")
    
    print(f"\nProfit & Loss:")
    print(f"  Total P&L:      ${stats['total_pnl']:+.2f}")
    print(f"  P&L %:          {stats['total_pnl_pct']:+.2f}%")
    print(f"  Profit Factor:  {stats['profit_factor']:.2f}x")
    
    print(f"\nAverage Trade:")
    print(f"  Avg Win:        ${stats['avg_win']:+.2f}")
    print(f"  Avg Loss:       ${stats['avg_loss']:+.2f}")
    print(f"  Largest Win:    ${stats['largest_win']:+.2f}")
    print(f"  Largest Loss:   ${stats['largest_loss']:+.2f}")
    
    # Per-symbol breakdown
    print(f"\n{'='*70}")
    print(f"📍 BY SYMBOL")
    print(f"{'='*70}")
    
    df = pd.DataFrame(trades)
    by_symbol = df.groupby("symbol").agg({
        "pnl": ["count", "sum", "mean"],
        "pnl_pct": "mean",
    }).round(2)
    
    by_symbol.columns = ["Trades", "Total PnL", "Avg PnL", "Avg %"]
    print(by_symbol)
    
    print(f"\n{'='*70}\n")


def print_recent_trades(trades: list[dict], limit: int = 5):
    """Print recent trades."""
    if not trades:
        return
    
    recent = trades[-limit:]
    
    print(f"\n📋 RECENT TRADES (Last {min(limit, len(trades))})")
    print(f"{'='*70}")
    print(f"{'Symbol':<8} {'Entry':<10} {'Exit':<10} {'PnL':<10} {'%':<8} {'Reason':<15}")
    print(f"{'-'*70}")
    
    for trade in recent:
        pnl = trade["pnl"]
        pnl_pct = trade["pnl_pct"]
        reason = trade.get("exit_reason", "N/A")[:14]
        
        print(f"{trade['symbol']:<8} ${trade['entry_price']:<9.2f} "
              f"${trade['exit_price']:<9.2f} ${pnl:<9.2f} {pnl_pct:<7.2f}% {reason:<15}")
    
    print(f"{'='*70}\n")


if __name__ == "__main__":
    trades = load_trades()
    
    if trades:
        print_summary(trades)
        print_recent_trades(trades, limit=10)
    else:
        print("\n📭 No trades recorded yet.")
        print("Run trading_bot.py to start trading!")
