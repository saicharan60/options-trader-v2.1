import os
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()
TRADING_MODE = os.getenv("TRADING_MODE", "PAPER").upper()
SCAN_SECONDS = int(os.getenv("SCAN_SECONDS", "60"))
CANDLE_INTERVAL_MINUTES = int(os.getenv("CANDLE_INTERVAL_MINUTES", "5"))
MIN_CONFIDENCE = int(os.getenv("MIN_CONFIDENCE", "50"))
STRIKES_EACH_SIDE = int(os.getenv("STRIKES_EACH_SIDE", "5"))
MAX_STOCKS = int(os.getenv("MAX_STOCKS", "15"))
MIN_OPTION_LTP = float(os.getenv("MIN_OPTION_LTP", "5"))
MAX_SPREAD_PERCENT = float(os.getenv("MAX_SPREAD_PERCENT", "3.0"))
INDEXES = [
    ("NIFTY", os.getenv("NIFTY_KEY", "NSE_INDEX|Nifty 50")),
    ("BANKNIFTY", os.getenv("BANKNIFTY_KEY", "NSE_INDEX|Nifty Bank")),
    ("SENSEX", os.getenv("SENSEX_KEY", "BSE_INDEX|SENSEX")),
]
STOCKS = [s.strip().upper() for s in os.getenv(
    "STOCKS", "RELIANCE,HDFCBANK,ICICIBANK,SBIN,INFY,TCS,AXISBANK,KOTAKBANK,LT,BHARTIARTL,ITC,MARUTI,M&M,TATASTEEL,SUNPHARMA"
).split(",") if s.strip()]
