# indicators.py
import pandas as pd

# EMA Calculation
def ema(df, period=20):
    df[f"EMA_{period}"] = df["close"].ewm(span=period, adjust=False).mean()
    return df

# RSI Calculation
def rsi(df, period=14):
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

# VWAP Calculation
def vwap(df):
    q = df["volume"]
    p = (df["high"] + df["low"] + df["close"]) / 3
    df["VWAP"] = (p * q).cumsum() / q.cumsum()
    return df

# Helper function: Apply all indicators
def apply_indicators(data):
    df = pd.DataFrame(data)
    df = ema(df, 20)
    df = ema(df, 50)
    df = rsi(df, 14)
    df = vwap(df)
    return df
