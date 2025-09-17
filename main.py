from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.snackbar import Snackbar
from binance.client import Client
import config

# Binance Testnet Client
client = Client(config.API_KEY, config.API_SECRET)
client.API_URL = 'https://testnet.binance.vision/api'

KV = """
BoxLayout:
    orientation: "vertical"
    padding: 10
    spacing: 10

    MDLabel:
        text: "🚀 Advanced Crypto Bot"
        halign: "center"
        theme_text_color: "Primary"
        font_style: "H5"

    MDTextField:
        id: symbol
        hint_text: "Enter Symbol (e.g. BTCUSDT)"
        text: "BTCUSDT"

    MDTextField:
        id: qty
        hint_text: "Enter Quantity"
        text: "0.001"

    MDRaisedButton:
        text: "Get Levels"
        md_bg_color: 0, 0.6, 0, 1
        on_release: app.get_levels()

    MDRaisedButton:
        text: "BUY"
        md_bg_color: 0, 0, 1, 1
        on_release: app.buy_order()

    MDRaisedButton:
        text: "SELL"
        md_bg_color: 1, 0, 0, 1
        on_release: app.sell_order()

    MDRaisedButton:
        text: "Check Balance"
        md_bg_color: 0, 0, 0, 1
        on_release: app.check_balance()

    ScrollView:
        MDLabel:
            id: log_box
            text: ""
            halign: "left"
            theme_text_color: "Primary"
            size_hint_y: None
            height: self.texture_size[1]
"""

class CryptoBotApp(MDApp):
    def build(self):
        return Builder.load_string(KV)

    def log(self, msg):
        self.root.ids.log_box.text += msg + "\n"

    def get_levels(self):
        try:
            symbol = self.root.ids.symbol.text
            klines = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_5MINUTE, limit=2)
            last_close = float(klines[-1][4])
            entry = last_close
            stop_loss = entry * 0.99
            target = entry * 1.02
            self.log(f"Entry: {entry:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        except Exception as e:
            Snackbar(text=str(e)).open()

    def buy_order(self):
        try:
            symbol = self.root.ids.symbol.text
            qty = float(self.root.ids.qty.text)
            order = client.create_order(symbol=symbol, side="BUY", type="MARKET", quantity=qty)
            self.log(f"✅ BUY Order: {order}")
        except Exception as e:
            Snackbar(text=str(e)).open()

    def sell_order(self):
        try:
            symbol = self.root.ids.symbol.text
            qty = float(self.root.ids.qty.text)
            order = client.create_order(symbol=symbol, side="SELL", type="MARKET", quantity=qty)
            self.log(f"✅ SELL Order: {order}")
        except Exception as e:
            Snackbar(text=str(e)).open()

    def check_balance(self):
        try:
            balance = client.get_asset_balance(asset="USDT")
            self.log(f"💰 Balance: {balance}")
        except Exception as e:
            Snackbar(text=str(e)).open()

if __name__ == "__main__":
    CryptoBotApp().run()
