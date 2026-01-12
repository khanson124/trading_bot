from dotenv import load_dotenv
import os
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

load_dotenv()

trading_client = TradingClient(
    api_key=os.getenv("ALPACA_API_KEY"),
    secret_key=os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)

def get_position_qty(symbol: str) -> float:
    """
    Returns position quantity if we have it, else 0.
    """
    try:
        pos = trading_client.get_open_position(symbol)
        return float(pos.qty)
    except Exception:
        return 0.0

def place_market_order_notional(symbol: str, side: str, notional_usd: float):
    """
    Places a market order using notional amount (USD).
    """
    order = MarketOrderRequest(
        symbol=symbol,
        side=OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
        notional=notional_usd
    )
    return trading_client.submit_order(order)

def execute_signal(symbol: str, signal: str, notional_usd: float = 25.0):
    """
    Executes BUY/SELL if appropriate, otherwise does nothing.
    """
    qty = get_position_qty(symbol)

    if signal == "BUY":
        if qty > 0:
            return {"action": "SKIP", "reason": f"Already holding {qty} shares of {symbol}"}
        order = place_market_order_notional(symbol, "BUY", notional_usd)
        return {"action": "BUY", "order_id": str(order.id), "reason": f"Placed BUY for ${notional_usd} notional"}

    if signal == "SELL":
        if qty <= 0:
            return {"action": "SKIP", "reason": f"No position to sell for {symbol}"}
        # Selling notional is fine, but could leave a tiny remainder; later we can switch to qty-based sells
        order = place_market_order_notional(symbol, "SELL", notional_usd)
        return {"action": "SELL", "order_id": str(order.id), "reason": f"Placed SELL for ${notional_usd} notional"}

    return {"action": "SKIP", "reason": "Signal is HOLD"}
