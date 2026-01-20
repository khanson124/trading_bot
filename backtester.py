"""
Simple backtester: run opening range breakout strategy on historical 1-min data.
Groups by trading date and resets daily limits for each day.
"""
import pandas as pd
from datetime import datetime, timedelta
from opening_range_strategy import OpeningRangeBreakout
from position_manager import PositionManager


def backtest_symbol(df: pd.DataFrame, symbol: str, starting_capital: float = 40.0) -> dict:
    """
    Backtest opening range breakout on 1-min data.
    Groups by trading date and resets limits each day.
    
    Args:
        df: DataFrame with columns [time, open, high, low, close, volume]
        symbol: Stock symbol
        starting_capital: Starting capital ($)
    
    Returns: {
        "symbol": str,
        "total_trades": int,
        "winning_trades": int,
        "losing_trades": int,
        "total_pnl": float,
        "total_pnl_pct": float,
        "win_rate": float,
        "avg_win": float,
        "avg_loss": float,
    }
    """
    if df.empty:
        return None
    
    # Ensure time column is datetime
    if not pd.api.types.is_datetime64_any_dtype(df['time']):
        df['time'] = pd.to_datetime(df['time'])
    
    # Group by trading date (date only, no time)
    df['trading_date'] = df['time'].dt.date
    
    position_manager = PositionManager(starting_capital=starting_capital)
    open_position = None
    
    # Process each trading day separately
    for trading_date, day_df in df.groupby('trading_date', sort=True):
        # Reset daily limits at start of each trading day
        position_manager.reset_daily_limits()
        strategy = OpeningRangeBreakout()  # Fresh strategy for each day
        
        day_df = day_df.reset_index(drop=True)
        
        for idx, row in day_df.iterrows():
            # Step 1: Calculate opening range (first 5 min of the day)
            if strategy.opening_range is None:
                strategy.calculate_opening_range(day_df.iloc[:idx+1])
            
            # Step 2: Check for breakout entry
            if open_position is None:
                breakout = strategy.check_breakout(row)
                
                if breakout["signal"] == "LONG_BREAKOUT":
                    can_trade, _ = position_manager.can_open_trade()
                    if can_trade:
                        entry_price = breakout["entry_price"]
                        levels = strategy.calculate_stops_and_targets(entry_price)
                        
                        open_position = position_manager.open_trade(
                            symbol=symbol,
                            entry_price=entry_price,
                            stop_loss=levels["stop_loss"],
                            take_profit=levels["take_profit_conservative"],
                            entry_time=row["time"],
                        )
            
            # Step 3: Check for exit
            if open_position is not None:
                current_price = float(row["close"])
                exit_check = strategy.should_exit(
                    current_price,
                    open_position.stop_loss,
                    open_position.take_profit,
                )
                
                if exit_check["signal"] != "HOLD":
                    position_manager.close_trade(
                        open_position,
                        exit_price=exit_check["exit_price"],
                        reason=exit_check["reason"],
                        exit_time=row["time"],
                    )
                    open_position = None
        
        # Close any remaining open position at end-of-day (last close)
        if open_position is not None:
            last_close = float(day_df.iloc[-1]["close"])
            position_manager.close_trade(
                open_position,
                exit_price=last_close,
                reason="End of day",
                exit_time=day_df.iloc[-1]["time"],
            )
            open_position = None
    
    # Summary stats
    trades = position_manager.closed_trades
    if not trades:
        return {
            "symbol": symbol,
            "total_trades": 0,
            "total_pnl": 0,
            "total_pnl_pct": 0,
        }
    
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl < 0]
    
    avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t.pnl for t in losses) / len(losses) if losses else 0
    
    total_pnl = position_manager.current_capital - starting_capital
    
    return {
        "symbol": symbol,
        "total_trades": len(trades),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "total_pnl": total_pnl,
        "total_pnl_pct": (total_pnl / starting_capital) * 100,
        "win_rate": (len(wins) / len(trades) * 100) if trades else 0,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
    }


def print_backtest_results(results: list[dict]):
    """Pretty print backtest results."""
    if not results:
        print("No results to display")
        return
    
    print(f"\n{'='*80}")
    print(f"BACKTEST RESULTS")
    print(f"{'='*80}")
    print(f"{'Symbol':<10} {'Trades':<8} {'Win%':<8} {'PnL':<12} {'PnL%':<10} {'Avg W/L':<15}")
    print(f"{'-'*80}")
    
    total_pnl = 0
    total_trades = 0
    
    for r in results:
        if r["total_trades"] == 0:
            continue
        
        avg_ratio = f"{r['avg_win']/abs(r['avg_loss']):.2f}x" if r['avg_loss'] != 0 else "N/A"
        
        print(f"{r['symbol']:<10} {r['total_trades']:<8} "
              f"{r['win_rate']:<7.1f}% ${r['total_pnl']:<11.2f} "
              f"{r['total_pnl_pct']:<9.2f}% {avg_ratio:<15}")
        
        total_pnl += r['total_pnl']
        total_trades += r['total_trades']
    
    print(f"{'-'*80}")
    if total_trades > 0:
        print(f"{'TOTAL':<10} {total_trades:<8} ${total_pnl:<11.2f} {(total_pnl/40)*100:<9.2f}%")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    """
    Example: backtest on historical data
    
    To use:
    1. Import get_1min_bars from intraday_data.py
    2. Fetch historical data
    3. Run backtest
    """
    from dotenv import load_dotenv
    from intraday_data import IntradayDataClient
    
    load_dotenv()
    
    client = IntradayDataClient()
    
    # Test on a few symbols
    symbols = ["SPY", "QQQ", "AAPL"]
    results = []
    
    print("Running backtests...")
    for symbol in symbols:
        print(f"  {symbol}...", end=" ", flush=True)
        try:
            df = client.get_1min_bars(symbol, days_back=5)
            if not df.empty:
                result = backtest_symbol(df, symbol)
                if result:
                    results.append(result)
                    print(f"✓ ({result['total_trades']} trades)")
            else:
                print("No data")
        except Exception as e:
            print(f"Error: {e}")
    
    print_backtest_results(results)
