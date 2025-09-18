# main.py (Kivy Version with Dropdown Menu)
import threading
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.menu import MDDropdownMenu
from kivy.clock import Clock

# Binance client
try:
    from binance.client import Client
    import config
    # Make sure you have API_KEY and API_SECRET in your config.py
    client = Client(config.API_KEY, config.API_SECRET, testnet=True)
except (ImportError, AttributeError):
    client = None
    print("Warning: Binance library or config not found. Running in UI test mode.")


KV_STRING = """
MDScreen:
    MDBoxLayout:
        orientation: 'vertical'
        padding: "10dp"
        spacing: "10dp"

        MDTopAppBar:
            title: "Crypto Trading Bot"
            elevation: 4

        MDBoxLayout:
            orientation: 'horizontal'
            spacing: "10dp"
            size_hint_y: None
            height: self.minimum_height

            MDBoxLayout:
                md_bg_color: self.theme_cls.bg_light
                padding: "8dp", 0, "8dp", 0
                
                MDIcon:
                    icon: "bitcoin"
                    halign: "center"

                MDLabel:
                    id: symbol_label
                    text: "Select Symbol"
                    halign: "center"
                    font_style: "Button"
                    
                MDIconButton:
                    icon: "menu-down"
                    on_release: app.open_symbol_menu()

            MDTextField:
                id: qty_input
                hint_text: "Quantity"
                text: "0.001"
                mode: "fill"
                size_hint_x: 0.4

        # Rest of the buttons...
        MDBoxLayout:
            orientation: 'horizontal'
            adaptive_height: True
            spacing: "10dp"
            MDRaisedButton:
                text: "GET LEVELS"
                on_release: app.get_levels()
                md_bg_color: 0, 0.6, 0, 1
                size_hint_x: 1
            MDRaisedButton:
                text: "BALANCE"
                on_release: app.check_balance()
                md_bg_color: 0.2, 0.2, 0.2, 1
                size_hint_x: 1
        MDBoxLayout:
            orientation: 'horizontal'
            adaptive_height: True
            spacing: "10dp"
            MDRaisedButton:
                text: "BUY"
                on_release: app.place_order("BUY")
                md_bg_color: 0, 0, 1, 1
                size_hint_x: 1
            MDRaisedButton:
                text: "SELL"
                on_release: app.place_order("SELL")
                md_bg_color: 1, 0, 0, 1
                size_hint_x: 1
                
        ScrollView:
            MDLabel:
                id: log_box
                text: "Welcome to Crypto Bot!\\n"
                padding: "10dp"
                size_hint_y: None
                height: self.texture_size[1]
                markup: True
"""

class CryptoBotApp(MDApp):
    def build(self):
        self.title = "CryptoBot"
        return Builder.load_string(KV_STRING)

    def on_start(self):
        # We create the dropdown menu when the app starts
        self.symbol_list = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT"]
        menu_items = [
            {"text": f"{symbol}", "on_release": lambda x=f"{symbol}": self.set_symbol(x)}
            for symbol in self.symbol_list
        ]
        # Anchor the menu to the label for positioning
        self.symbol_menu = MDDropdownMenu(
            caller=self.root.ids.symbol_label,
            items=menu_items,
            width_mult=4,
        )
        # Set a default symbol
        Clock.schedule_once(lambda dt: self.set_symbol(self.symbol_list[0]))

    def set_symbol(self, symbol_text):
        # This function is called when a menu item is selected
        self.root.ids.symbol_label.text = symbol_text
        self.symbol_menu.dismiss()

    def open_symbol_menu(self):
        # This opens the dropdown menu
        self.symbol_menu.open()

    def log(self, message):
        from kivy.clock import mainthread
        @mainthread
        def update_log_on_main_thread():
            log_label = self.root.ids.log_box
            log_label.text += message + "\\n"
        update_log_on_main_thread()

    def show_snackbar(self, message):
        from kivy.clock import mainthread
        @mainthread
        def show_snackbar_on_main_thread():
            Snackbar(text=message).open()
        show_snackbar_on_main_thread()

    def get_levels(self):
        threading.Thread(target=self._get_levels_thread, daemon=True).start()

    def _get_levels_thread(self):
        if not client:
            self.show_snackbar("Binance client not configured.")
            return
        try:
            symbol = self.root.ids.symbol_label.text
            klines = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_5MINUTE, limit=2)
            last_close = float(klines[-1][4])
            entry = last_close
            stop_loss = entry * 0.99
            target = entry * 1.02
            self.log(f"[INFO] Levels for {symbol}: Entry: {entry:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        except Exception as e:
            self.show_snackbar(f"Error: {str(e)}")

    def check_balance(self):
        threading.Thread(target=self._check_balance_thread, daemon=True).start()

    def _check_balance_thread(self):
        if not client:
            self.show_snackbar("Binance client not configured.")
            return
        try:
            balance = client.get_asset_balance(asset="USDT")
            self.log(f"[INFO] Balance: {balance['free']} USDT")
        except Exception as e:
            self.show_snackbar(f"Error: {str(e)}")

    def place_order(self, side):
        threading.Thread(target=self._place_order_thread, args=(side,), daemon=True).start()

    def _place_order_thread(self, side):
        if not client:
            self.show_snackbar("Binance client not configured.")
            return
        try:
            symbol = self.root.ids.symbol_label.text
            qty = float(self.root.ids.qty_input.text)
            order = client.create_test_order(symbol=symbol, side=side, type='MARKET', quantity=qty)
            self.log(f"[SUCCESS] {side} order placed for {qty} {symbol}.")
            self.show_snackbar(f"{side} order successful!")
        except Exception as e:
            self.show_snackbar(f"Order Error: {str(e)}")


if __name__ == "__main__":
    CryptoBotApp().run()