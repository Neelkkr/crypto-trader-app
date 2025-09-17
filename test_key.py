# test_key.py

import config
from binance.client import Client

# यह स्क्रिप्ट सिर्फ यह चेक करेगी कि आपकी API keys काम कर रही हैं या नहीं।

try:
    print("Connecting to Binance Testnet...")
    
    # यह config.py से आपकी keys का उपयोग करेगा
    client = Client(config.API_KEY, config.API_SECRET, testnet=True)
    
    print("Connection successful. Checking USDT balance...")
    
    # यह वही प्राइवेट API कॉल है जो फेल हो रही है
    balance = client.get_asset_balance(asset='USDT')
    
    print("\n✅ SUCCESS! Your API keys are working correctly.")
    print(f"Your USDT balance is: {balance['free']}")

except Exception as e:
    print("\n❌ FAILED. The error is still happening.")
    print(f"Error Message: {e}")