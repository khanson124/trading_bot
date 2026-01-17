"""
Strategy configuration - tune these values to optimize for your market conditions.
"""

# ===== MARKET & TIME =====
MARKET_OPEN_EST = 9.5  # 9:30 AM
TRADING_WINDOW_START = 9.583  # 9:35 AM (5 min after open)
TRADING_WINDOW_END = 10.5  # 10:30 AM
TRADING_WINDOW_ONLY = True  # Only trade in this window

# ===== OPENING RANGE =====
OPENING_RANGE_MINUTES = 5  # First 5 minutes = opening range
BREAKOUT_VOLUME_MULTIPLIER = 1.0  # Must have >= 1.0x avg volume on breakout

# ===== ENTRY RULES =====
GAP_UP_MIN_PCT = 0.03  # 3% minimum gap-up
SCANNER_LIMIT = 50  # Max symbols to monitor

# ===== POSITION SIZING & RISK =====
STARTING_CAPITAL = 40.0
RISK_PER_TRADE_PCT = 0.02  # Risk 2% of capital per trade
POSITION_SIZE_PCT = 0.80  # Use 80% of capital max per position

# ===== STOPS & TARGETS =====
STOP_LOSS_SOURCE = "opening_range"  # "opening_range" or "fixed_pct"
STOP_LOSS_PCT = 0.05  # -5% if using fixed
TARGET_PROFIT_PCT_CONSERVATIVE = 0.08  # +8% (primary target)
TARGET_PROFIT_PCT_AGGRESSIVE = 0.12  # +12% (if feeling bullish)
USE_TRAILING_STOP = False  # Enable trailing stop after +6%
TRAILING_STOP_TRIGGER_PCT = 0.06  # Start trailing after +6%
TRAILING_STOP_DISTANCE_PCT = 0.02  # 2% distance from high

# ===== KILL SWITCHES (NON-NEGOTIABLE) =====
MAX_TRADES_PER_DAY = 2
STOP_AFTER_FIRST_LOSS = True
MAX_DAILY_LOSS_PCT = -0.08  # -8% max daily loss
MAX_DAILY_LOSS_HARD_STOP = True

# ===== DATA & FEEDS =====
DATA_FEED = "IEX"  # "IEX" or "SIP" (SIP more expensive, IEX free)
BARS_TIMEFRAME = "1m"  # 1-minute bars
HISTORICAL_DAYS_BACK = 5  # Fetch last 5 days for backtesting

# ===== PAPER VS LIVE =====
PAPER_TRADING = True  # Set to False only when confident
VERBOSE_LOGGING = True  # Print detailed logs

# ===== EXAMPLE OPTIMIZATIONS =====
# 
# Conservative (lower risk, slower gains):
#   RISK_PER_TRADE_PCT = 0.01
#   TARGET_PROFIT_PCT_CONSERVATIVE = 0.05
#   MAX_TRADES_PER_DAY = 1
#
# Aggressive (higher risk, faster gains):
#   RISK_PER_TRADE_PCT = 0.05
#   TARGET_PROFIT_PCT_CONSERVATIVE = 0.12
#   MAX_TRADES_PER_DAY = 3
#
# High-frequency (more trades, higher volume):
#   TRADING_WINDOW_END = 11.5  # Trade until 11:30 AM instead of 10:30
#   SCANNER_LIMIT = 100  # Watch more symbols
#
