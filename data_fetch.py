# data_fetch.py
from binance.client import Client
import config

# Binance client बनाना
client = Client(api_key=config.API_KEY, api_secret=config.API_SECRET, testnet=True)

def get_historical_data(symbol, interval="5m", limit=100):
    """
    Binance से पिछले candles लाता है।
    symbol: BTCUSDT
    interval: 1m, 5m, 15m...
    limit: कितनी candles चाहिए (default 100)
    """
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)

    data = []
    for k in klines:
        data.append({
            "timestamp": k[0],
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5])
        })
    return data

if __name__ == "__main__":
    candles = get_historical_data("BTCUSDT", config.INTERVAL)
    print(candles[-5:])  # आखिरी 5 candles print करके check करेंगे
