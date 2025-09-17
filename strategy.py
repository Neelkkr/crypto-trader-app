# strategy.py
# Breakout + Retest + Volume + VWAP + RSI detector
# Returns dict: { "signal": "BUY"/"SELL"/"NONE", "confidence": 0-1, "entry":..., "sl":..., "tp":..., "reason": "..." }

import pandas as pd
from binance.client import Client
import config
import numpy as np

# reuse client from config (testnet)
client = Client(config.API_KEY, config.API_SECRET)
client.API_URL = 'https://testnet.binance.vision/api'

def vwap(df: pd.DataFrame):
    p = (df["high"] + df["low"] + df["close"]) / 3.0
    q = df["volume"]
    return (p * q).cumsum() / q.cumsum()

def rsi(df: pd.Series, period: int = 14):
    delta = df.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def fetch_ohlcv(symbol: str, interval: str = "15m", limit: int = 100):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    if not klines:
        return pd.DataFrame()
    df = pd.DataFrame(klines, columns=[
        "open_time","open","high","low","close","volume",
        "close_time","qav","num_trades","taker_base","taker_quote","ignore"
    ])
    df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].astype(float)
    df["datetime"] = pd.to_datetime(df["close_time"], unit="ms")
    df.set_index("datetime", inplace=True)
    return df[["open","high","low","close","volume"]]

def detect_breakout_retest(symbol: str, interval: str = "15m"):
    """
    Logic:
      1) Identify recent swing high/low as resistance/support (using rolling max/min of last N bars)
      2) If a breakout bar closes above resistance with volume > recent avg*V factor -> candidate breakout
      3) Wait for 1-2 candles retest: price returns toward breakout level but holds above (for BUY) and closes above level -> confirmation
      4) Check VWAP and RSI to filter:
           - For BUY require price > VWAP and RSI between 40-80 (not extreme)
           - For SELL require price < VWAP and RSI between 20-60
      5) Compute entry = retest close (or next candle open), SL = retest low/break level - small buffer, TP = entry + (risk * RR)
    Returns dict with signal/confidence/levels/reason.
    """
    df = fetch_ohlcv(symbol, interval=interval, limit=200)
    if df.empty or len(df) < 30:
        return {"signal":"NONE","confidence":0.0,"reason":"no_data"}

    # params
    lookback = 30    # find swing in last 30 candles
    vol_factor = 1.5 # breakout volume must be > vol_factor * avg(volume)
    rr = 2.0         # risk:reward

    recent = df.tail(lookback)
    highs = recent["high"]
    lows = recent["low"]

    resistance = highs[:-3].rolling(window=10, min_periods=5).max().iloc[-1]  # approximate recent resistance
    support = lows[:-3].rolling(window=10, min_periods=5).min().iloc[-1]

    # find last 5 candles for breakout detection
    last_bars = df.iloc[-6:]  # include breakout + 1-5 retest bars
    breakout_bar = last_bars.iloc[-6]  # candidate: 6th last as breakout (we'll scan)
    # Actually search for a bar in last 6 that closed beyond resistance/support
    breakout_index = None
    breakout_type = None
    for i in range(-10, -1):  # scan recent bars
        bar = df.iloc[i]
        close = bar["close"]
        vol = bar["volume"]
        recent_avg_vol = df["volume"].rolling(20).mean().iloc[i]
        if not np.isnan(recent_avg_vol) and close > resistance and vol > recent_avg_vol * vol_factor:
            breakout_index = df.index[i]
            breakout_type = "BUY"
            break
        if not np.isnan(recent_avg_vol) and close < support and vol > recent_avg_vol * vol_factor:
            breakout_index = df.index[i]
            breakout_type = "SELL"
            break

    if breakout_index is None:
        return {"signal":"NONE","confidence":0.0,"reason":"no_breakout"}

    # now look for retest in the 1-3 candles after breakout
    bi = df.index.get_loc(breakout_index)
    # examine next up to 3 candles
    confirm_index = None
    confirm_close = None
    for j in range(bi+1, min(bi+4, len(df))):
        c = df.iloc[j]
        # BUY: retest should dip near breakout level but close above it
        if breakout_type == "BUY":
            if c["low"] <= resistance and c["close"] > resistance:
                confirm_index = df.index[j]
                confirm_close = c["close"]
                break
        else:
            if c["high"] >= support and c["close"] < support:
                confirm_index = df.index[j]
                confirm_close = c["close"]
                break

    if confirm_index is None:
        # no retest confirmation yet
        return {"signal":"NONE","confidence":0.2,"reason":"no_retest_yet"}

    # compute indicators to filter
    df_for_v = df.iloc[: (df.index.get_loc(confirm_index)+1) ]
    vwap_series = vwap(df_for_v)
    cur_vwap = vwap_series.iloc[-1]
    cur_rsi = rsi(df_for_v["close"], period=14).iloc[-1]

    # filter rules
    if breakout_type == "BUY":
        if confirm_close < cur_vwap:
            return {"signal":"NONE","confidence":0.25,"reason":"vwap_below"}
        if not (40 <= cur_rsi <= 80):
            return {"signal":"NONE","confidence":0.3,"reason":"rsi_filter"}
        # levels
        entry = float(confirm_close)
        sl = float(min(df_for_v["low"].iloc[-3:])) * 0.999  # small buffer below recent lows
        risk = entry - sl
        if risk <= 0:
            return {"signal":"NONE","confidence":0.0,"reason":"invalid_risk"}
        tp = entry + risk * rr
        confidence = 0.8  # good confirmation
        reason = f"breakout+retest confirmed vol+vwap+rsi"
        return {"signal":"BUY","confidence":confidence,"entry":round(entry,6),
                "sl":round(sl,6),"tp":round(tp,6),"reason":reason}
    else:
        # SELL case
        if confirm_close > cur_vwap:
            return {"signal":"NONE","confidence":0.25,"reason":"vwap_above"}
        if not (20 <= cur_rsi <= 60):
            return {"signal":"NONE","confidence":0.3,"reason":"rsi_filter"}
        entry = float(confirm_close)
        sl = float(max(df_for_v["high"].iloc[-3:])) * 1.001
        risk = sl - entry
        if risk <= 0:
            return {"signal":"NONE","confidence":0.0,"reason":"invalid_risk"}
        tp = entry - risk * rr
        confidence = 0.8
        reason = "breakdown+retest confirmed vol+vwap+rsi"
        return {"signal":"SELL","confidence":confidence,"entry":round(entry,6),
                "sl":round(sl,6),"tp":round(tp,6),"reason":reason}
