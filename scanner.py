from data_fetch import get_historical_data
from indicators import apply_indicators
import config

def generate_signals(symbol):
    data = get_historical_data(symbol, config.INTERVAL)
    df = apply_indicators(data)

    latest = df.iloc[-1]  # आखिरी candle
    signal = None
    entry = sl = tp = None

    # Entry Long condition
    if latest["close"] > latest["EMA_20"] and latest["RSI"] > 50 and latest["close"] > latest["VWAP"]:
        signal = "BUY"
        entry = latest["close"]
        sl = latest["VWAP"]  # VWAP को Stop Loss मान रहे हैं
        risk = entry - sl
        tp = entry + (risk * 2)  # Risk:Reward = 1:2

    # Exit / Short condition
    elif latest["close"] < latest["EMA_20"] and latest["RSI"] < 50 and latest["close"] < latest["VWAP"]:
        signal = "SELL"
        entry = latest["close"]
        sl = latest["VWAP"]  # VWAP को Stop Loss मान रहे हैं
        risk = sl - entry
        tp = entry - (risk * 2)  # Risk:Reward = 1:2

    else:
        signal = "HOLD"

    return signal, latest, entry, sl, tp

if __name__ == "__main__":
    for symbol in config.SYMBOLS:
        signal, candle, entry, sl, tp = generate_signals(symbol)

        if signal in ["BUY", "SELL"]:
            print(f"\n{symbol}: {signal}")
            print(f"  Entry  = {entry:.2f}")
            print(f"  StopLoss = {sl:.2f}")
            print(f"  Target = {tp:.2f}")
            print(f"  (Close={candle['close']:.2f}, RSI={candle['RSI']:.2f}, VWAP={candle['VWAP']:.2f})")
        else:
            print(f"\n{symbol}: HOLD (No trade)")
