from data_fetch import get_historical_data
import config
from indicators import apply_indicators

# Binance से candle data लाना
data = get_historical_data("BTCUSDT", config.INTERVAL)

# Indicators apply करना
df = apply_indicators(data)

# आखिरी 5 rows print करना
print(df.tail(5))
