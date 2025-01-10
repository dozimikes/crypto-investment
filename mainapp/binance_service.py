# binance_service.py
from binance.client import Client
from django.conf import settings

# Initialize Binance client (API key is optional for public endpoints)
client = Client(settings.BINANCE_API_KEY, settings.BINANCE_API_SECRET)

def get_crypto_price(symbol="BTCUSDT"):
    """
    Fetch the real-time price for a cryptocurrency pair (e.g., BTC/USDT).
    """
    try:
        ticker = client.get_symbol_ticker(symbol=symbol)
        price = ticker['price']
        return price
    except Exception as e:
        print(f"Error fetching price: {e}")
        return None
