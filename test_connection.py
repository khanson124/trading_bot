from alpaca.trading.client import TradingClient
from dotenv import load_dotenv
import os

load_dotenv()

client = TradingClient(
    api_key=os.getenv("ALPACA_API_KEY"),
    secret_key=os.getenv("ALPACA_SECRET_KEY"),
    paper=True if os.getenv("ALPACA_PAPER") == "true" else False
)   

account = client.get_account()
print("Account status:", account.status)
print("Buying power:", account.buying_power)



