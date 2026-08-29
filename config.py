import os
from pathlib import Path

# Base Directory
BASE_DIR = Path(__file__).resolve().parent

# Server Config
HOST = "127.0.0.1"
PORT = 8000
WEBSOCKET_PATH = "/ws/live-ticks"

# Watchlist Defaults (Equities and Indices)
DEFAULT_WATCHLIST = [
    {"symbol": "NIFTY 50", "ticker": "^NSEI", "type": "INDEX", "exchange": "NSE"},
    {"symbol": "BANK NIFTY", "ticker": "^NSEBANK", "type": "INDEX", "exchange": "NSE"},
    {"symbol": "RELIANCE", "ticker": "RELIANCE.NS", "type": "EQUITY", "exchange": "NSE"},
    {"symbol": "TCS", "ticker": "TCS.NS", "type": "EQUITY", "exchange": "NSE"},
    {"symbol": "INFY", "ticker": "INFY.NS", "type": "EQUITY", "exchange": "NSE"},
    {"symbol": "HDFCBANK", "ticker": "HDFCBANK.NS", "type": "EQUITY", "exchange": "NSE"},
    {"symbol": "ICICIBANK", "ticker": "ICICIBANK.NS", "type": "EQUITY", "exchange": "NSE"},
    {"symbol": "TATAMOTORS", "ticker": "TATAMOTORS.NS", "type": "EQUITY", "exchange": "NSE"},
    {"symbol": "SBIN", "ticker": "SBIN.NS", "type": "EQUITY", "exchange": "NSE"},
    {"symbol": "BHARTIARTL", "ticker": "BHARTIARTL.NS", "type": "EQUITY", "exchange": "NSE"},
]

# Risk Engine Parameters
INITIAL_ACCOUNT_BALANCE = 2000.0   # 2,000 Paper Tokens / Credits
MAX_RISK_PER_TRADE_PCT = 2.0        # Max 2.0% capital risk per trade (40 tokens)
MAX_DAILY_DRAWDOWN_PCT = 3.0        # Max 3.0% daily loss limit (60 tokens)
MIN_RISK_REWARD_RATIO = 1.5         # Minimum 1:1.5 Risk-to-Reward ratio
ESTIMATED_TRANSACTION_COST_PCT = 0.05 # Transaction cost estimate (~0.05%)
ESTIMATED_SLIPPAGE_PCT = 0.03       # Average execution slippage (~0.03%)

# Autonomous Trading Engine
AUTONOMOUS_TRADING_ENABLED = os.getenv("AUTONOMOUS_TRADING_ENABLED", "True").lower() in ("true", "1", "yes")
AUTONOMOUS_SCAN_INTERVAL_SECONDS = int(os.getenv("AUTONOMOUS_SCAN_INTERVAL", "30"))
MAX_CONCURRENT_POSITIONS = int(os.getenv("MAX_CONCURRENT_POSITIONS", "3"))

# Telegram Bot Integration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

# AI Model Parameters
MIN_MODEL_CONFIDENCE = 0.65         # Minimum win probability threshold (65%)
LOOKBACK_CANDLES = 100              # Number of historical candles for feature calculation

# Storage Paths
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "data" / "models"
PAPER_DB_PATH = DATA_DIR / "paper_trading.db"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)
