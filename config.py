"""
GOLD SNIPER V2.0 [FREE] - Configuration
==========================================
Advanced Gold (XAUUSD) Trading System for MT5
100% FREE - No paid indicators required!

All indicators are built into the Pine Script:
  EMA (9/21/200) + Supertrend + RSI + MACD + ATR + BB + SMC

All times displayed in UTC+3.
"""
import os

# ============================================================
# TELEGRAM
# ============================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")

# ============================================================
# TRADING INSTRUMENT
# ============================================================
SYMBOL = "XAUUSD"
SYMBOL_DISPLAY = "XAUUSD (Gold)"

# Yahoo Finance symbol for live price monitoring
YF_SYMBOL = "GC=F"  # Gold Futures (Yahoo Finance)

# Price precision for gold (2 decimal places)
PRICE_PRECISION = 2

# ============================================================
# TIMEFRAMES
# ============================================================
HTF_TIMEFRAME = "1h"
LTF_TIMEFRAME = "15m"
CANDLE_INTERVAL = 15

# ============================================================
# TIMEZONE
# ============================================================
UTC_OFFSET = 3  # UTC+3 (Riyadh / AST)

# ============================================================
# WEBHOOK SECURITY
# ============================================================
# Single webhook secret - same value set in Pine Script
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "gold_sniper_v2_secret")

# ============================================================
# STRATEGY FILTERS (Enable/Disable)
# ============================================================

# Stage 1: Signal Detection (from Pine Script webhook)
SIGNAL_DETECTION_ENABLED = True

# Stage 2: Signal Stability (seconds to wait before confirming)
STABILITY_ENABLED = True
STABILITY_WINDOW_SECONDS = 60

# Stage 3: SMC Filter (Order Blocks / FVG / BOS)
# Data comes from Pine Script (built-in SMC detection)
SMC_FILTER_ENABLED = True
SMC_TOLERANCE_POINTS = 5.0

# Stage 4: Supertrend Filter (trend alignment)
# Data comes from Pine Script
SUPERTREND_FILTER_ENABLED = True

# Stage 5: EMA Trend Filter (EMA 200 for HTF bias)
# Data comes from Pine Script
EMA_TREND_FILTER_ENABLED = True
EMA_FAST = 9
EMA_SLOW = 21
EMA_TREND = 200

# Stage 6: RSI Filter (avoid overbought/oversold entries)
# Data comes from Pine Script
RSI_FILTER_ENABLED = True
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
RSI_DIVERGENCE_ENABLED = True

# Stage 7: MACD Confirmation
# Data comes from Pine Script
MACD_FILTER_ENABLED = True
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Stage 8: Wick Filter (candle body strength)
WICK_FILTER_ENABLED = True
WICK_BODY_RATIO_MAX = 0.30  # Min body/range ratio (0.30 = 30%)

# ============================================================
# ATR-BASED STOP LOSS & TAKE PROFIT
# ============================================================
ATR_PERIOD = 14
ATR_SL_MULTIPLIER = 1.5     # SL = 1.5 * ATR
ATR_TP1_MULTIPLIER = 1.0    # TP1 = 1.0 * ATR (quick profit)
ATR_TP2_MULTIPLIER = 2.0    # TP2 = 2.0 * ATR
ATR_TP3_MULTIPLIER = 3.0    # TP3 = 3.0 * ATR

# Minimum SL/TP in points (safety net for gold)
MIN_SL_POINTS = 3.0
MAX_SL_POINTS = 30.0
MIN_TP_POINTS = 2.0

# ============================================================
# TRADE MANAGEMENT
# ============================================================
MOVE_SL_TO_BREAKEVEN_ON_TP1 = True
BREAKEVEN_OFFSET = 0.5  # Add 0.5 points above entry for breakeven

TRAILING_STOP_ENABLED = True
TRAILING_STOP_ATR_MULTIPLIER = 0.75

MAX_CONCURRENT_TRADES = 1

# ============================================================
# TRADING SESSIONS (Kill Zones) - UTC Hours
# ============================================================
ENABLE_TRADING_HOURS = os.getenv("ENABLE_TRADING_HOURS", "true").lower() == "true"
TRADING_START_HOUR_UTC = int(os.getenv("TRADING_START_HOUR", "7"))
TRADING_END_HOUR_UTC = int(os.getenv("TRADING_END_HOUR", "20"))

KILL_ZONES_ENABLED = True
KILL_ZONES = [
    (7, 10),   # London Open
    (12, 16),  # NY Open + London/NY Overlap
    (16, 19),  # NY Afternoon
]

# ============================================================
# TRADING DAYS (0=Monday ... 6=Sunday)
# ============================================================
ENABLE_TRADING_DAYS = os.getenv("ENABLE_TRADING_DAYS", "true").lower() == "true"
TRADING_DAYS = [0, 1, 2, 3, 4]  # Monday to Friday

# ============================================================
# NEWS FILTER
# ============================================================
NEWS_FILTER_ENABLED = os.getenv("NEWS_FILTER_ENABLED", "true").lower() == "true"
NEWS_PAUSE_MINUTES_BEFORE = 30
NEWS_PAUSE_MINUTES_AFTER = 15

# ============================================================
# RISK MANAGEMENT
# ============================================================
RISK_PERCENTAGE = 1.0
DEFAULT_ACCOUNT_BALANCE = 1000
LOT_SIZE_PER_POINT = 0.01

# ============================================================
# PRICE MONITORING
# ============================================================
PRICE_CHECK_INTERVAL = 5
PRICE_SOURCE = os.getenv("PRICE_SOURCE", "yfinance")

# ============================================================
# ANTI-FLICKER
# ============================================================
MIN_SIGNAL_INTERVAL_SECONDS = 300

# ============================================================
# HOSTING
# ============================================================
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

KEEP_ALIVE_ENABLED = os.getenv("KEEP_ALIVE_ENABLED", "true").lower() == "true"
KEEP_ALIVE_URL = os.getenv("KEEP_ALIVE_URL", "")
KEEP_ALIVE_INTERVAL = 300

# ============================================================
# DISPLAY
# ============================================================
BOT_NAME = "GOLD SNIPER"
BOT_VERSION = "V2.0 [FREE]"
BOT_DISPLAY_HEADER = "🥇 GOLD SNIPER V2.0 | XAUUSD"

# ============================================================
# DATABASE
# ============================================================
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "trades.db")

# ============================================================
# RESULT CHECK FALLBACK
# ============================================================
RESULT_CHECK_INTERVAL = int(os.getenv("RESULT_CHECK_INTERVAL", "15"))

# ============================================================
# CONFIDENCE SCORING
# ============================================================
MIN_CONFIDENCE_SCORE = 4.0  # Minimum to accept (out of 10)

# Weights for each filter in confidence calculation
CONFIDENCE_WEIGHTS = {
    "signal_base": 2.0,       # Base score for valid signal
    "smc": 2.5,               # SMC Order Block / FVG / BOS
    "supertrend": 1.5,        # Supertrend alignment
    "ema_trend": 1.5,         # EMA 200 trend
    "rsi": 1.0,               # RSI confirmation
    "macd": 1.0,              # MACD confirmation
    "kill_zone": 0.5,         # Kill zone bonus
    "rsi_divergence": 1.5,    # RSI divergence bonus
    "bb_squeeze": 1.0,        # Bollinger Bands squeeze bonus
    "volume": 0.5,            # Volume above average bonus
}
