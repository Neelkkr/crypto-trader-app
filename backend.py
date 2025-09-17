# backend.py

from binance.client import Client
from binance.exceptions import BinanceAPIException
import config

# Binance Testnet URL
TESTNET_URL = "https://testnet.binance.vision"

# Binance Client (Testnet)
client = Client(config.API_KEY, config.API_SECRET)
client.API_URL = TESTNET_URL  # 🔑 Force testnet endpoint

# ---------------------------
# Balance Check Function
# ---------------------------
def get_balance(asset="USDT"):
    try:
        account = client.get_account()
        balances = account["balances"]

        for b in balances:
            if b["asset"] == asset:
                return {
                    "status": "success",
                    "asset": asset,
                    "free": b["free"],
                    "locked": b["locked"]
                }

        return {"status": "error", "message": f"{asset} balance not found"}
    except BinanceAPIException as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ---------------------------
# Levels Function (Dummy + Example)
# ---------------------------
def get_levels(symbol):
    try:
        klines = client.get_klines(symbol=symbol, interval=config.INTERVAL, limit=20)
        closes = [float(x[4]) for x in klines]
        last_close = closes[-1]

        entry = round(last_close, 2)
        stop_loss = round(entry * 0.99, 2)
        target = round(entry * 1.02, 2)

        return {
            "symbol": symbol,
            "entry": entry,
            "stop_loss": stop_loss,
            "target": target
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
