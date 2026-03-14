# ============================================================
#  TRADING BOT — CONFIGURACIÓN CENTRAL
#  Lee las keys desde variables de entorno (Railway)
#  o desde el archivo directamente (local)
# ============================================================
import os

# --- BINANCE API ---
BINANCE_API_KEY    = os.getenv("BINANCE_API_KEY",    "TSUPwP3HI7xzj2sWkDsAAFjLAg75EO6Y7zl5aXD6Qb7VOmempkWT0otB4dNLnBRf")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "q1jwt8nrodwDyWCPpvVhf7uos1azM1upSGvqpiIdzpRla6c21ADzDHeGYWG5vJrH")
BINANCE_TESTNET    = os.getenv("BINANCE_TESTNET", "False") == "True"
DRY_RUN            = os.getenv("DRY_RUN", "True") == "True"

# --- TELEGRAM ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8793819185:AAEHlCZHBk89cYLwrmKCfaG1oSFQC0UuW_c")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID",   "8763677371")

# --- ACTIVOS A OPERAR ---
SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]

# --- GESTIÓN DE RIESGO ---
CAPITAL_TOTAL_USDT      = float(os.getenv("CAPITAL_TOTAL_USDT", "100"))
MAX_POSITION_PCT        = 0.10
STOP_LOSS_PCT           = 0.02
TAKE_PROFIT_PCT         = 0.04
PARTIAL_TP_PCT          = 0.03
PARTIAL_TP_SIZE         = 0.50
TRAILING_STOP_PCT       = 0.015
MAX_LOSS_DAILY_PCT      = 0.04
MAX_LOSS_WEEKLY_PCT     = 0.06
MAX_LOSS_MONTHLY_PCT    = 0.08
FLASH_CRASH_PCT         = 0.10
MAX_OPEN_POSITIONS      = 4
CASH_RESERVE_PCT        = 0.30

# --- POSITION SIZING DINÁMICO ---
POSITION_SIZE_LOW       = 0.05
POSITION_SIZE_MID       = 0.10
POSITION_SIZE_HIGH      = 0.15

# --- PARÁMETROS TÉCNICOS ---
TIMEFRAME               = "15m"
MA_SHORT                = 20
MA_LONG                 = 50
RSI_PERIOD              = 14
RSI_OVERSOLD            = 30
RSI_OVERBOUGHT          = 70
ADX_PERIOD              = 14
ADX_TREND_THRESHOLD     = 25
ADX_FLAT_THRESHOLD      = 20

# --- SENTIMENT ANALYSIS ---
SENTIMENT_WEIGHT        = 0.10
TECHNICAL_WEIGHT        = 0.55
REGIME_WEIGHT           = 0.35
SENTIMENT_MIN_SOURCES   = 2
NEWSAPI_KEY             = os.getenv("NEWSAPI_KEY", "TU_NEWSAPI_KEY")

# --- LOOP PRINCIPAL ---
BOT_INTERVAL_SECONDS    = 60

# --- FUTUROS BINANCE ---
LEVERAGE                = 2
MARGIN_TYPE             = "ISOLATED"