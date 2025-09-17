# gui.py
# Advanced Crypto Trading GUI with Candlestick Chart, Volume, Live Update and OCO orders (Testnet)
# Author: ChatGPT (upgraded for user)
# Requirements: python-binance, pandas, matplotlib

import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import time
import math
import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates

# Binance client
from binance.client import Client
from binance.exceptions import BinanceAPIException

import config  # must contain API_KEY and API_SECRET
# add strategy module (create strategy.py as provided earlier)
import strategy
# ---------------------------------------------------------
# CONFIG / TUNEABLE PARAMETERS (edit here)
# ---------------------------------------------------------
UPDATE_INTERVAL_SEC = 3            # live price / chart refresh interval
CANDLES_LIMIT = 60                 # how many candles to fetch for chart
DEFAULT_INTERVAL = "5m"            # default timeframe for levels/chart
SL_PCT = 0.01                      # stop loss percent (1% default)
TP_PCT = 0.02                      # take profit percent (2% default)
CHART_CANDLE_WIDTH_MIN = 0.7       # relative candle width
# ---------------------------------------------------------

# init client for testnet
client = Client(config.API_KEY, config.API_SECRET)
# Force testnet endpoint (important)
client.API_URL = 'https://testnet.binance.vision/api'

# helper: convert kline -> DataFrame
def fetch_ohlcv_df(symbol: str, interval: str = DEFAULT_INTERVAL, limit: int = CANDLES_LIMIT):
    """
    Returns DataFrame indexed by datetime with columns: open, high, low, close, volume
    """
    try:
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        if not klines:
            return pd.DataFrame()
        df = pd.DataFrame(klines, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_av", "trades", "taker_base_av", "taker_quote_av", "ignore"
        ])
        # cast types
        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)
        df["datetime"] = pd.to_datetime(df["close_time"], unit="ms")
        df.set_index("datetime", inplace=True)
        return df[["open", "high", "low", "close", "volume"]]
    except Exception as e:
        raise

def compute_levels(df: pd.DataFrame):
    """ Simple level computation: entry = last close, SL = entry*(1-SL_PCT), TP = entry*(1+TP_PCT) """
    if df is None or df.empty:
        return None
    last = float(df["close"].iloc[-1])
    entry = round(last, 8) if last < 1 else round(last, 6)
    sl = round(entry * (1 - SL_PCT), 8) if entry < 1 else round(entry * (1 - SL_PCT), 6)
    tp = round(entry * (1 + TP_PCT), 8) if entry < 1 else round(entry * (1 + TP_PCT), 6)
    return {"entry": entry, "sl": sl, "tp": tp, "close": last}

# Candlestick drawing function (matplotlib axes)
def draw_candlestick(ax, df):
    ax.clear()
    if df is None or df.empty:
        ax.set_facecolor("#111111")
        ax.set_title("No data", color="white")
        return
    ax.set_facecolor("#111111")
    # styling
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    for spine in ax.spines.values():
        spine.set_color('#222222')

    dates = mdates.date2num(df.index.to_pydatetime())
    # compute width from dates
    width = (dates[1] - dates[0]) * CHART_CANDLE_WIDTH_MIN if len(dates) > 1 else 0.0007

    # plot candles and wicks
    for idx, (dt, row) in enumerate(df.iterrows()):
        o, h, l, c = row["open"], row["high"], row["low"], row["close"]
        color = "#4caf50" if c >= o else "#f44336"
        # wick
        ax.plot([dates[idx], dates[idx]], [l, h], color=color, linewidth=0.8)
        # body
        lower = o if c >= o else c
        height = abs(c - o)
        if height == 0:
            height = (df["close"].max() - df["close"].min()) * 0.001 or 0.0000001
        rect = Rectangle((dates[idx] - width / 2, lower), width, height, facecolor=color, edgecolor=color)
        ax.add_patch(rect)

    # volume subplot handled outside (here we only draw candles)
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.set_title("Candles (latest → right)", color="white")
    ax.grid(False)

# safe float parse
def safe_float(x, default=0.0):
    try:
        return float(x)
    except:
        return default

# ---------------------------------------------------------
# GUI Application
# ---------------------------------------------------------
class CryptoAppUI:
    def __init__(self, master):
        self.master = master
        master.title("🚀 Crypto Trading Bot - Advanced")
        master.configure(bg="#121212")
        master.geometry("1050x720")

        # top frame (controls)
        ctrl = tk.Frame(master, bg="#121212")
        ctrl.pack(side="top", fill="x", padx=12, pady=8)

        tk.Label(ctrl, text="Symbol:", fg="white", bg="#121212").grid(row=0, column=0, padx=6, sticky="w")
        self.symbol_var = tk.StringVar(value="BTCUSDT")
        self.sym_cb = ttk.Combobox(ctrl, textvariable=self.symbol_var, values=[
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT"
        ], width=12, state="readonly")
        self.sym_cb.grid(row=0, column=1, padx=6)

        tk.Label(ctrl, text="Interval:", fg="white", bg="#121212").grid(row=0, column=2, padx=6, sticky="w")
        self.interval_var = tk.StringVar(value=DEFAULT_INTERVAL)
        self.int_cb = ttk.Combobox(ctrl, textvariable=self.interval_var, values=[
            "1m", "3m", "5m", "15m", "30m", "1h", "4h"
        ], width=8, state="readonly")
        self.int_cb.grid(row=0, column=3, padx=6)

        tk.Label(ctrl, text="Qty:", fg="white", bg="#121212").grid(row=0, column=4, padx=6, sticky="w")
        self.qty_var = tk.StringVar(value="0.001")
        self.qty_entry = tk.Entry(ctrl, textvariable=self.qty_var, width=10)
        self.qty_entry.grid(row=0, column=5, padx=6)

        # Risk controls (editable)
        tk.Label(ctrl, text="SL %:", fg="white", bg="#121212").grid(row=0, column=6, padx=6, sticky="w")
        self.sl_pct_var = tk.StringVar(value=str(int(SL_PCT*100)))
        self.sl_pct_entry = tk.Entry(ctrl, textvariable=self.sl_pct_var, width=6)
        self.sl_pct_entry.grid(row=0, column=7, padx=6)

        tk.Label(ctrl, text="TP %:", fg="white", bg="#121212").grid(row=0, column=8, padx=6, sticky="w")
        self.tp_pct_var = tk.StringVar(value=str(int(TP_PCT*100)))
        self.tp_pct_entry = tk.Entry(ctrl, textvariable=self.tp_pct_var, width=6)
        self.tp_pct_entry.grid(row=0, column=9, padx=6)

        # Buttons
        self.get_btn = tk.Button(ctrl, text="📊 Get Levels", bg="#4caf50", fg="white", command=self.on_get_levels)
        self.get_btn.grid(row=0, column=10, padx=8)
        self.buy_btn = tk.Button(ctrl, text="✅ BUY (Market + OCO)", bg="#2196f3", fg="white", command=lambda: self.on_trade("BUY"))
        self.buy_btn.grid(row=0, column=11, padx=8)
        self.sell_btn = tk.Button(ctrl, text="❌ SELL (Market + OCO)", bg="#f44336", fg="white", command=lambda: self.on_trade("SELL"))
        self.sell_btn.grid(row=0, column=12, padx=8)
        self.balance_btn = tk.Button(ctrl, text="💰 Check Balance", bg="#9c27b0", fg="white", command=self.on_check_balance)
        self.balance_btn.grid(row=0, column=13, padx=8)
        # add this after the existing buttons (so it sits with other buttons)
        self.strategy_btn = tk.Button(ctrl, text="🔎 Scan Strategy", bg="#ff9800", fg="black", command=self.on_scan_strategy)
        self.strategy_btn.grid(row=0, column=14, padx=8)


        # Middle frame: levels + price + order history
        mid = tk.Frame(master, bg="#1e1e1e")
        mid.pack(side="top", fill="x", padx=12, pady=8)

        # left: levels box
        lv_frame = tk.Frame(mid, bg="#1e1e1e", bd=1, relief="ridge")
        lv_frame.pack(side="left", padx=6, pady=6, fill="y")

        tk.Label(lv_frame, text="Levels", bg="#1e1e1e", fg="white", font=("Arial", 12, "bold")).pack(anchor="w", padx=8, pady=6)
        self.entry_lbl = tk.Label(lv_frame, text="Entry: -", bg="#1e1e1e", fg="white", font=("Arial", 11))
        self.entry_lbl.pack(anchor="w", padx=12, pady=4)
        self.sl_lbl = tk.Label(lv_frame, text="Stop Loss: -", bg="#1e1e1e", fg="#ff6666", font=("Arial", 11))
        self.sl_lbl.pack(anchor="w", padx=12, pady=4)
        self.tp_lbl = tk.Label(lv_frame, text="Target: -", bg="#1e1e1e", fg="#74d374", font=("Arial", 11))
        self.tp_lbl.pack(anchor="w", padx=12, pady=4)

        # price label
        self.price_lbl = tk.Label(lv_frame, text="Price: -", bg="#1e1e1e", fg="white", font=("Arial", 13, "bold"))
        self.price_lbl.pack(anchor="w", padx=12, pady=10)

        # right: order history / logs
        logs_frame = tk.Frame(mid, bg="#1e1e1e")
        logs_frame.pack(side="left", padx=12, pady=6, fill="both", expand=True)

        tk.Label(logs_frame, text="Order History & Logs", bg="#1e1e1e", fg="white", font=("Arial", 12, "bold")).pack(anchor="w", padx=6, pady=6)
        self.log_box = tk.Text(logs_frame, height=8, bg="#0d0d0d", fg="lime", font=("Consolas", 10))
        self.log_box.pack(fill="both", expand=True, padx=6, pady=6)

        # bottom: chart + volume
        chart_frame = tk.Frame(master, bg="#121212")
        chart_frame.pack(side="top", fill="both", expand=True, padx=12, pady=6)

        # create matplotlib figure with two axes (candles + volume)
        self.fig = plt.Figure(figsize=(10, 4), facecolor="#121212")
        self.ax_candle = self.fig.add_axes([0.05, 0.25, 0.9, 0.7], facecolor="#121212")
        self.ax_vol = self.fig.add_axes([0.05, 0.05, 0.9, 0.18], facecolor="#121212", sharex=self.ax_candle)
        # tidy styles
        for ax in (self.ax_candle, self.ax_vol):
            ax.tick_params(axis='x', colors='white')
            ax.tick_params(axis='y', colors='white')
            for spine in ax.spines.values():
                spine.set_color('#333333')

        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # internal state
        self.current_df = pd.DataFrame()
        self.auto_running = True
        self.update_interval = UPDATE_INTERVAL_SEC

        # start background auto-updater
        self.start_auto_updater()

    # -------------------------
    # Logging utility
    # -------------------------
    def log(self, msg):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_box.insert(tk.END, f"[{ts}] {msg}\n")
        self.log_box.see(tk.END)

    # -------------------------
    # Background updater
    # -------------------------
    def _background_loop(self):
        while self.auto_running:
            try:
                self.fetch_and_update(show_levels=False)
            except Exception as ex:
                # schedule log update on main thread
                self.master.after(0, lambda: self.log(f"Auto-update error: {ex}"))
            time.sleep(self.update_interval)

    def start_auto_updater(self):
        t = threading.Thread(target=self._background_loop, daemon=True)
        t.start()

    def stop_auto_updater(self):
        self.auto_running = False

    # -------------------------
    # Fetch and update UI
    # -------------------------
    def fetch_and_update(self, show_levels=False):
        symbol = self.symbol_var.get()
        interval = self.interval_var.get()
        try:
            df = fetch_ohlcv_df(symbol=symbol, interval=interval, limit=CANDLES_LIMIT)
            self.current_df = df
            # schedule UI update in main thread
            self.master.after(0, lambda: self.update_ui_from_df(df, show_levels))
        except BinanceAPIException as e:
            self.master.after(0, lambda: self.log(f"Binance API error: {e}"))
        except Exception as e:
            self.master.after(0, lambda: self.log(f"Fetch error: {e}"))

    def update_ui_from_df(self, df, show_levels=False):
        # update price
        if df is None or df.empty:
            self.price_lbl.config(text="Price: -")
        else:
            last_price = float(df["close"].iloc[-1])
            self.price_lbl.config(text=f"Price: {last_price:.6f}")
        # update chart
        try:
            self.draw_chart(df)
        except Exception as e:
            self.log(f"Chart draw error: {e}")
        # optionally compute levels
        if show_levels:
            levels = compute_levels(df)
            if levels:
                self.entry_lbl.config(text=f"Entry: {levels['entry']}")
                self.sl_lbl.config(text=f"Stop Loss: {levels['sl']}")
                self.tp_lbl.config(text=f"Target: {levels['tp']}")
                self.log(f"Levels updated -> Entry {levels['entry']} SL {levels['sl']} TP {levels['tp']}")
            else:
                self.log("No data to compute levels")

    # -------------------------
    # Draw chart (candles + volume)
    # -------------------------
    def draw_chart(self, df):
        self.ax_candle.clear()
        self.ax_vol.clear()
        if df is None or df.empty:
            self.ax_candle.set_title("No data", color="white")
            self.canvas.draw_idle()
            return

        # draw candles
        df_plot = df.copy().tail(CANDLES_LIMIT)
        dates = mdates.date2num(df_plot.index.to_pydatetime())
        width = (dates[1] - dates[0]) * CHART_CANDLE_WIDTH_MIN if len(dates) > 1 else 0.0007

        for idx, (dt_idx, row) in enumerate(df_plot.iterrows()):
            o, h, l, c = row["open"], row["high"], row["low"], row["close"]
            color = "#4caf50" if c >= o else "#f44336"
            # wick
            self.ax_candle.plot([dates[idx], dates[idx]], [l, h], color=color, linewidth=0.8)
            # body
            lower = o if c >= o else c
            height = abs(c - o)
            if height == 0:
                height = (df_plot["close"].max() - df_plot["close"].min()) * 0.001 or 0.0000001
            rect = Rectangle((dates[idx] - width/2, lower), width, height, facecolor=color, edgecolor=color)
            self.ax_candle.add_patch(rect)

        # x formatting
        self.ax_candle.xaxis_date()
        self.ax_candle.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        self.ax_candle.tick_params(axis='x', rotation=45, labelsize=8, colors='white')
        self.ax_candle.tick_params(axis='y', colors='white')
        self.ax_candle.set_facecolor("#121212")
        self.ax_candle.set_title(f"{self.symbol_var.get()} - Candles", color="white")

        # volume bars
        vols = df_plot["volume"].values
        vol_dates = dates
        vol_colors = ["#4caf50" if df_plot["close"].iloc[i] >= df_plot["open"].iloc[i] else "#f44336" for i in range(len(df_plot))]
        self.ax_vol.bar(vol_dates, vols, width=width*0.9, color=vol_colors)
        self.ax_vol.set_facecolor("#121212")
        self.ax_vol.tick_params(axis='y', colors='white')
        self.ax_vol.xaxis_date()
        self.ax_vol.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        self.ax_vol.tick_params(axis='x', rotation=45, labelsize=8, colors='white')

        self.fig.tight_layout()
        self.canvas.draw_idle()

    # -------------------------
    # UI callbacks
    # -------------------------
    def on_get_levels(self):
        # fetch and display levels once (non-blocking)
        threading.Thread(target=lambda: self.fetch_and_update(show_levels=True), daemon=True).start()
            # -------------------------
    # Strategy integration: Scan and optional auto-execute
    # -------------------------
    def on_scan_strategy(self):
        """ Called by button -> runs strategy in background """
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self):
        """ Background worker: runs strategy.detect_breakout_retest and updates UI """
        symbol = self.symbol_var.get()
        interval = self.interval_var.get()
        # log start
        self.master.after(0, lambda: self.log(f"Scanning strategy for {symbol} @ {interval}..."))

        try:
            res = strategy.detect_breakout_retest(symbol=symbol, interval=interval)
        except Exception as e:
            self.master.after(0, lambda: self.log(f"Strategy error: {e}"))
            return

        # handle result on main thread
        if res.get("signal") in ("BUY", "SELL"):
            entry = res.get("entry")
            sl = res.get("sl")
            tp = res.get("tp")
            conf = res.get("confidence", 0)
            reason = res.get("reason", "")
            self.master.after(0, lambda: self.entry_lbl.config(text=f"Entry: {entry}"))
            self.master.after(0, lambda: self.sl_lbl.config(text=f"Stop Loss: {sl}"))
            self.master.after(0, lambda: self.tp_lbl.config(text=f"Target: {tp}"))
            self.master.after(0, lambda: self.log(f"STRATEGY -> {res['signal']} conf={conf} reason={reason}"))
            # ask user whether to place order
            def ask_place():
                place = messagebox.askyesno("Place Order?", f"{res['signal']} {symbol} ?\nEntry: {entry}\nSL: {sl}\nTP: {tp}\n\nPlace market order + OCO?")
                if place:
                    threading.Thread(target=lambda: self._trade_worker_with_levels(res), daemon=True).start()
            self.master.after(0, ask_place)
        else:
            reason = res.get("reason", "no_signal")
            self.master.after(0, lambda: self.log(f"STRATEGY -> No valid signal ({reason})"))

    def _trade_worker_with_levels(self, res):
        """
        Place market order then OCO based on strategy result dict `res`:
        res must have keys: signal ('BUY'/'SELL'), entry, sl, tp
        """
        symbol = self.symbol_var.get()
        side = res.get("signal")
        try:
            qty = float(self.qty_var.get())
        except:
            self.master.after(0, lambda: messagebox.showerror("Qty Error", "Invalid qty"))
            return

        try:
            self.master.after(0, lambda: self.log(f"Placing MARKET {side} for {symbol} qty={qty} (strategy)"))
            order = client.create_order(symbol=symbol, side=side, type="MARKET", quantity=qty)
            # get executed price if available
            fills = order.get("fills", [])
            exec_price = None
            if fills:
                exec_price = safe_float(fills[0].get("price", None))
            else:
                ticker = client.get_symbol_ticker(symbol=symbol)
                exec_price = safe_float(ticker.get("price", None))
            exec_price = exec_price or 0.0

            # use sl/tp from res (already computed)
            sl_price = res.get("sl")
            tp_price = res.get("tp")

            if side == "BUY":
                # create OCO SELL (TP above, stop below)
                try:
                    self.master.after(0, lambda: self.log(f"Placing OCO SELL: qty={qty}, TP={tp_price}, SL={sl_price}"))
                    oco = client.create_oco_order(
                        symbol=symbol,
                        side="SELL",
                        quantity=qty,
                        price=str(tp_price),
                        stopPrice=str(sl_price),
                        stopLimitPrice=str(round(sl_price * 0.999, 8)),
                        stopLimitTimeInForce='GTC'
                    )
                    self.master.after(0, lambda: self.log(f"✅ Strategy BUY executed @{exec_price}. OCO placed. TP={tp_price} SL={sl_price}"))
                except BinanceAPIException as e:
                    self.master.after(0, lambda: self.log(f"❌ OCO create error: {e}"))
                    self.master.after(0, lambda: messagebox.showerror("OCO Error", str(e)))
            else:
                # SELL -> OCO BUY
                try:
                    self.master.after(0, lambda: self.log(f"Placing OCO BUY: qty={qty}, TP={tp_price}, SL={sl_price}"))
                    oco = client.create_oco_order(
                        symbol=symbol,
                        side="BUY",
                        quantity=qty,
                        price=str(tp_price),
                        stopPrice=str(sl_price),
                        stopLimitPrice=str(round(sl_price * 1.001, 8)),
                        stopLimitTimeInForce='GTC'
                    )
                    self.master.after(0, lambda: self.log(f"✅ Strategy SELL executed @{exec_price}. OCO placed. TP={tp_price} SL={sl_price}"))
                except BinanceAPIException as e:
                    self.master.after(0, lambda: self.log(f"❌ OCO create error: {e}"))
                    self.master.after(0, lambda: messagebox.showerror("OCO Error", str(e)))

            self.master.after(0, lambda: self.log(f"Order response: id={order.get('orderId','NA')} status={order.get('status','NA')}"))
        except BinanceAPIException as e:
            self.master.after(0, lambda: self.log(f"Binance API Error (strategy trade): {e}"))
            self.master.after(0, lambda: messagebox.showerror("Trade Error", str(e)))
        except Exception as ex:
            self.master.after(0, lambda: self.log(f"Trade exception: {ex}"))
            self.master.after(0, lambda: messagebox.showerror("Trade Exception", str(ex)))


    def on_trade(self, side):
        # wrapper called by button to place market order then OCO
        threading.Thread(target=lambda: self._trade_worker(side), daemon=True).start()

    def _trade_worker(self, side):
        symbol = self.symbol_var.get()
        try:
            qty = float(self.qty_var.get())
            if qty <= 0:
                self.master.after(0, lambda: messagebox.showerror("Qty Error", "Quantity must be > 0"))
                return
        except:
            self.master.after(0, lambda: messagebox.showerror("Qty Error", "Invalid quantity"))
            return

        try:
            # Place market order first
            self.master.after(0, lambda: self.log(f"Placing MARKET {side} for {symbol} qty={qty}"))
            order = client.create_order(symbol=symbol, side=side, type="MARKET", quantity=qty)
            # try to read executed price (fills may be present)
            fills = order.get("fills", [])
            exec_price = None
            if fills:
                exec_price = safe_float(fills[0].get("price", None))
            else:
                # fallback to last price from ticker
                ticker = client.get_symbol_ticker(symbol=symbol)
                exec_price = safe_float(ticker.get("price", None))

            if exec_price is None:
                self.master.after(0, lambda: self.log("Warning: could not determine executed price"))
                exec_price = float(order.get("cummulativeQuoteQty", 0)) / qty if qty else 0.0

            exec_price = float(exec_price)

            # compute SL and TP using UI settings
            sl_pct = safe_float(self.sl_pct_var.get(), default=SL_PCT*100) / 100.0
            tp_pct = safe_float(self.tp_pct_var.get(), default=TP_PCT*100) / 100.0

            if side == "BUY":
                sl_price = round(exec_price * (1 - sl_pct), 8 if exec_price < 1 else 6)
                tp_price = round(exec_price * (1 + tp_pct), 8 if exec_price < 1 else 6)
                # create OCO SELL order (take profit and stop loss)
                try:
                    self.master.after(0, lambda: self.log(f"Placing OCO SELL: qty={qty}, TP={tp_price}, SL={sl_price}"))
                    oco = client.create_oco_order(
                        symbol=symbol,
                        side="SELL",
                        quantity=qty,
                        price=str(tp_price),
                        stopPrice=str(sl_price),
                        stopLimitPrice=str(round(sl_price * 0.999, 6)),
                        stopLimitTimeInForce='GTC'
                    )
                    self.master.after(0, lambda: self.log(f"✅ BUY executed @{exec_price}. OCO placed. TP={tp_price} SL={sl_price}"))
                except BinanceAPIException as e:
                    self.master.after(0, lambda: self.log(f"❌ OCO create error: {e}"))
                    self.master.after(0, lambda: messagebox.showerror("OCO Error", str(e)))
            else:
                # SELL then OCO BUY to lock profit / SL above
                sl_price = round(exec_price * (1 + sl_pct), 8 if exec_price < 1 else 6)
                tp_price = round(exec_price * (1 - tp_pct), 8 if exec_price < 1 else 6)
                try:
                    self.master.after(0, lambda: self.log(f"Placing OCO BUY: qty={qty}, TP={tp_price}, SL={sl_price}"))
                    oco = client.create_oco_order(
                        symbol=symbol,
                        side="BUY",
                        quantity=qty,
                        price=str(tp_price),
                        stopPrice=str(sl_price),
                        stopLimitPrice=str(round(sl_price * 1.001, 6)),
                        stopLimitTimeInForce='GTC'
                    )
                    self.master.after(0, lambda: self.log(f"✅ SELL executed @{exec_price}. OCO placed. TP={tp_price} SL={sl_price}"))
                except BinanceAPIException as e:
                    self.master.after(0, lambda: self.log(f"❌ OCO create error: {e}"))
                    self.master.after(0, lambda: messagebox.showerror("OCO Error", str(e)))

            # append order summary to logs
            self.master.after(0, lambda: self.log(f"Order response: id={order.get('orderId','NA')} status={order.get('status','NA')}"))
        except BinanceAPIException as e:
            self.master.after(0, lambda: self.log(f"Binance API Error (trade): {e}"))
            self.master.after(0, lambda: messagebox.showerror("Trade Error", str(e)))
        except Exception as ex:
            self.master.after(0, lambda: self.log(f"Trade exception: {ex}"))
            self.master.after(0, lambda: messagebox.showerror("Trade Exception", str(ex)))

    # -------------------------
    # Check balance (testnet)
    # -------------------------
    def on_check_balance(self):
        threading.Thread(target=self._balance_worker, daemon=True).start()

    def _balance_worker(self):
        try:
            sym = self.symbol_var.get()
            assets = ["USDT"]
            if sym.endswith("USDT"):
                base = sym.replace("USDT", "")
                assets.append(base)
            balance_msgs = []
            for a in assets:
                try:
                    bal = client.get_asset_balance(asset=a)
                    if bal:
                        free = bal.get("free", "0")
                        locked = bal.get("locked", "0")
                        balance_msgs.append(f"{a}: {free} free / {locked} locked")
                except Exception as e:
                    balance_msgs.append(f"{a}: error")
            msg = " | ".join(balance_msgs) if balance_msgs else "No balances"
            self.master.after(0, lambda: self.log(f"Balance -> {msg}"))
        except Exception as e:
            self.master.after(0, lambda: self.log(f"Balance error: {e}"))
            self.master.after(0, lambda: messagebox.showerror("Balance Error", str(e)))

    # -------------------------
    # Shutdown
    # -------------------------
    def shutdown(self):
        self.stop_auto_updater()
        self.master.quit()

# ---------------------------------------------------------
# Run the app
# ---------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = CryptoAppUI(root)
    # ensure clean shutdown
    try:
        root.protocol("WM_DELETE_WINDOW", lambda: (app.shutdown(), root.destroy()))
        root.mainloop()
    except Exception as e:
        print("Fatal exception:", e)
