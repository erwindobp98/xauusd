from pathlib import Path
import json
import os

# ===================== CONFIG BOOTSTRAP =====================
# Config is created BEFORE any external dependency (MT5/Rich/etc.) is imported.
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"

DEFAULT_CONFIG = {
    # ===== MT5 / SYMBOL =====
    "SYMBOL": "XAUUSD.vxc",

    # ===== TIMEFRAME SETTINGS =====
    "TIMEFRAME_ENTRY": "M5",
    "TIMEFRAME_TREND": "M15",
    "TIMEFRAME_SMC": "M15",
    "CONFLUENCE_TF": "H1",

    # ===== ENTRY / LOT =====
    "LOT_SIZE": 0.01,
    "USE_DYNAMIC_LOT": False,
    "RISK_PER_TRADE_PERCENT": 1.0,
    "MIN_LOT_SIZE": 0.01,
    "MAX_LOT_SIZE": 1.00,
    "LOT_STEP": 0.01,

    # ===== RISK =====
    "SL_POINTS": 4.0,
    "RR_RATIO": 1.5,
    "MAX_DAILY_LOSS_PERCENT": 30.0,

    # ===== ATR-BASED SL =====
    "USE_ATR_SL": True,
    "ATR_SL_MULTIPLIER": 1.5,
    "MIN_ATR_SL": 4.0,
    "MAX_ATR_SL": 15.0,

    # ===== ATR SL FOR EXISTING POSITIONS =====
    "USE_ATR_SL_EXISTING": True,
    "ATR_SL_UPDATE_ON_STARTUP": True,

    # ===== PATTERN SETTINGS =====
    "USE_PINBAR": True,
    "USE_REJECTION_WICK": True,
    "USE_ORDER_BLOCK": True,
    "USE_FVG": True,

    # ===== DYNAMIC SWING SL =====
    "USE_SWING_SL": False,
    "SWING_LOOKBACK": 10,
    "SL_BUFFER": 0.5,

    # ===== TRADE MANAGEMENT ENGINE =====
    "USE_TRADE_MGMT": False,
    "R1_BE_BUFFER": 0.1,
    "PARTIAL_CLOSE_PCT": 50,
    "TRAIL_BUFFER": 0.5,

    # ===== TRADING MODE =====
    "USE_TAKE_PROFIT": True,
    "USE_AUTO_TRADE": True,

    # ===== MAX POSITIONS =====
    "MAX_OPEN_POSITIONS": 1,

    # ===== FILTERS =====
    "USE_TREND_FILTER": True,
    "USE_ENGULFING": True,
    "USE_ATR_FILTER": True,
    "USE_SESSION_FILTER": True,
    "USE_BREAK_EVEN": True,
    "USE_LIVE_PRICE": True,

    # ===== SMC ENGINE =====
    "USE_SMC_SUPPLY_DEMAND": True,
    "USE_SMART_SWEEP": True,
    "USE_FAKE_BREAK_FILTER": True,
    "USE_BOS": True,
    "USE_CHOCH": True,

    # ===== IMPROVED SMC =====
    "USE_CONFLUENCE_CHECK": True,
    "USE_MANDATORY_SMC": False,
    "MANDATORY_SMC_MIN_CONDITIONS": 2,

    # ===== TRAILING SL =====
    "USE_TRAILING_SL": False,
    "TRAIL_START_PROFIT": 2.0,
    "TRAIL_SECURE_PERCENT": 50,

    # ===== ATR-BASED TRAILING START =====
    "USE_ATR_TRAIL_START": False,
    "TRAIL_START_PERCENT": 0.80,

    # ===== CANDLE CONFIRMATION =====
    "USE_CANDLE_CONFIRMATION": False,
    "CONFIRMATION_LOOKBACK": 1,

    # ===== SCORING SYSTEM =====
    "USE_SCORING_SYSTEM": True,
    "MIN_SCORE_FOR_ENTRY": 7,
    "MAX_SCORE": 13,

    # ===== PARAMETERS =====
    "SMC_ZONE_SENSITIVITY": 0.22,
    "SMC_MAX_ZONES": 5,
    "SWEEP_LOOKBACK": 15,
    "BOS_LOOKBACK": 20,
    "ATR_PERIOD": 8,
    "MIN_ATR_VALUE": 1.5,
    "BE_TRIGGER": 4.0,
    "USE_BE_R_BASED": True,
    "BE_TRIGGER_R": 1.0,

    # ===== SESSION SETTINGS =====
    # All times below are WIB (Asia/Jakarta).
    # Session detection is informational; ENABLED decides whether entry is allowed.
    "SESSION_TIMEZONE": "Asia/Jakarta",
    "SESSION_FILTER": {
        "ENABLED": True,
        "ASIA": {"ENABLED": True, "START": "07:00", "END": "15:00"},
        "LONDON": {"ENABLED": True, "START": "15:00", "END": "23:00"},
        "NEW_YORK": {"ENABLED": True, "START": "20:00", "END": "04:00"},
        "LONDON_NEW_YORK_OVERLAP": {"ENABLED": True, "START": "20:00", "END": "23:00"}
    },

    # ===== SIGNAL HISTORY =====
    "SIGNAL_COOLDOWN": 60
}

def _deep_merge(default, current):
    if isinstance(default, dict) and isinstance(current, dict):
        result = dict(default)
        for key, value in current.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = _deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    return current

def load_or_create_config(path=CONFIG_FILE):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        path.write_text(
            json.dumps(DEFAULT_CONFIG, indent=4, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )
        return dict(DEFAULT_CONFIG)

    try:
        current = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(current, dict):
            raise ValueError("root config harus object/dict")
    except Exception:
        backup = path.with_suffix(path.suffix + ".broken")
        try:
            path.replace(backup)
        except OSError:
            pass
        path.write_text(
            json.dumps(DEFAULT_CONFIG, indent=4, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )
        return dict(DEFAULT_CONFIG)

    merged = _deep_merge(DEFAULT_CONFIG, current)
    if merged != current:
        path.write_text(
            json.dumps(merged, indent=4, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )
    return merged

CONFIG = load_or_create_config()

# ===================== EXTERNAL DEPENDENCIES =====================
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import time
from colorama import init, Fore, Style

from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.live import Live

init(autoreset=True)
console = Console()
runtime_message_text = ""

def runtime_message(message):
    global runtime_message_text
    runtime_message_text = str(message)


def timeframe_from_name(value):
    if isinstance(value, int):
        return value
    mapping = {
        "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1
    }
    return mapping.get(str(value).upper(), mt5.TIMEFRAME_M5)

def apply_config(c):
    g = globals()
    for key, value in c.items():
        if key == "SESSION_FILTER" or key == "SESSION_TIMEZONE":
            continue
        if key in ("TIMEFRAME_ENTRY", "TIMEFRAME_TREND", "TIMEFRAME_SMC", "CONFLUENCE_TF"):
            g[key] = timeframe_from_name(value)
        else:
            g[key] = value

apply_config(CONFIG)
SESSION_CONFIG = CONFIG.get("SESSION_FILTER", DEFAULT_CONFIG["SESSION_FILTER"])
WIB = pytz.timezone(CONFIG.get("SESSION_TIMEZONE", "Asia/Jakarta"))
SESSION_STATUS = "OUT OF SESSION"

# TP_POINTS is derived from the configured base SL for compatibility/display.
TP_POINTS = SL_POINTS * RR_RATIO

# ===================== PENDING SIGNAL STATE =====================
pending_signal = None
last_candle_time = None

# ===================== MARKET BIAS STATE =====================
market_bias = "SIDEWAYS"
bias_changed = False

# ===================== SIGNAL HISTORY =====================
last_buy_signal_time = 0
last_sell_signal_time = 0
SIGNAL_COOLDOWN = 60  # Detik antara sinyal

# ===================== CONNECT =====================
if not mt5.initialize():
    runtime_message("❌ MT5 gagal connect")
    quit()

daily_start_balance = mt5.account_info().balance
daily_date = datetime.now(WIB).date()
trading_disabled_today = False

# ===================== DATA FUNCTIONS =====================
def get_data(tf, bars=300):
    rates = mt5.copy_rates_from_pos(SYMBOL, tf, 0, bars)
    if rates is None:
        return pd.DataFrame()
    return pd.DataFrame(rates)

def get_closed_data(tf, bars=300):
    """V3: return only fully closed candles; live candle is never used for signal logic."""
    df = get_data(tf, bars + 1)
    if df is None or df.empty or len(df) < 3:
        return pd.DataFrame()
    return df.iloc[:-1].copy().reset_index(drop=True)

def get_candle_time(df, lookback=1):
    if len(df) > lookback:
        return df['time'].iloc[-lookback]
    return None

def trend_m5():
    df = get_closed_data(TIMEFRAME_TREND)
    if df.empty:
        return "SIDEWAYS"
    df['ema20'] = df['close'].ewm(span=20).mean()
    df['ema50'] = df['close'].ewm(span=50).mean()
    if df['ema20'].iloc[-1] > df['ema50'].iloc[-1]:
        return "BULLISH"
    elif df['ema20'].iloc[-1] < df['ema50'].iloc[-1]:
        return "BEARISH"
    return "SIDEWAYS"

# ===== IMPROVED TREND DETECTION (BARU) =====
def get_higher_timeframe_trend():
    """Dapatkan trend dari timeframe lebih tinggi untuk confluence"""
    df = get_closed_data(CONFLUENCE_TF, bars=100)
    if df is None or df.empty:
        return "SIDEWAYS"
    
    df['ema20'] = df['close'].ewm(span=20).mean()
    df['ema50'] = df['close'].ewm(span=50).mean()
    df['ema100'] = df['close'].ewm(span=100).mean()
    
    #确认 EMA排列
    ema20 = df['ema20'].iloc[-1]
    ema50 = df['ema50'].iloc[-1]
    ema100 = df['ema100'].iloc[-1]
    
    if ema20 > ema50 > ema100:
        return "BULLISH"
    elif ema20 < ema50 < ema100:
        return "BEARISH"
    elif ema20 > ema50:
        return "BULLISH"
    elif ema20 < ema50:
        return "BEARISH"
    return "SIDEWAYS"

def engulfing(df, direction):
    prev, curr = df.iloc[-2], df.iloc[-1]
    if direction == "BUY":
        return prev['close'] < prev['open'] and curr['close'] > prev['open']
    if direction == "SELL":
        return prev['close'] > prev['open'] and curr['close'] < prev['open']
    return False

def engulfing_on_candle(df, direction, lookback=1):
    if len(df) <= lookback:
        return False
    
    target_candle = df.iloc[-lookback]
    prev_candle = df.iloc[-lookback-1]
    
    if direction == "BUY":
        return prev_candle['close'] < prev_candle['open'] and target_candle['close'] > prev_candle['open']
    if direction == "SELL":
        return prev_candle['close'] > prev_candle['open'] and target_candle['close'] < prev_candle['open']
    return False

def atr_value(df):
    """V3: True Range based ATR, consistent with the ATR series engine."""
    if df is None or len(df) < ATR_PERIOD + 1:
        return None
    prev_close = df['close'].shift(1)
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - prev_close).abs(),
        (df['low'] - prev_close).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(ATR_PERIOD).mean()
    value = atr.iloc[-1]
    return float(value) if pd.notna(value) else None

def get_atr_current():
    """Get ATR value for SL calculation"""
    df = get_closed_data(TIMEFRAME_ENTRY, bars=100)
    return atr_value(df)

def get_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def get_live_price():
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick:
        return tick.bid, tick.ask
    return None, None

# ===================== IMPROVED BOS & CHOCH =====================
def detect_swing_points(df, lookback=10):
    """Detect swing highs and lows"""
    highs = []
    lows = []
    
    for i in range(lookback, len(df)-lookback):
        is_high = True
        is_low = True
        
        # Check if this is a swing point
        for j in range(i-lookback, i+lookback+1):
            if j != i and j < len(df):
                if df['high'].iloc[j] >= df['high'].iloc[i]:
                    is_high = False
                if df['low'].iloc[j] <= df['low'].iloc[i]:
                    is_low = False
        
        if is_high:
            highs.append((i, df['high'].iloc[i]))
        if is_low:
            lows.append((i, df['low'].iloc[i]))
    
    return highs, lows

def detect_bos(df, lookback=20):
    """V3: BOS = confirmed close beyond the most recent confirmed swing."""
    if df is None or len(df) < lookback + 10:
        return None
    highs, lows = detect_swing_points(df, 3)
    if not highs or not lows:
        return None

    close = float(df['close'].iloc[-1])
    recent_high = float(highs[-1][1])
    recent_low = float(lows[-1][1])

    if close > recent_high:
        return "BULL_BOS"
    if close < recent_low:
        return "BEAR_BOS"
    return None

def detect_choch(df):
    """V3: CHoCH direction fixed: break above swing high = bullish, below swing low = bearish."""
    if df is None or len(df) < 30:
        return None
    highs, lows = detect_swing_points(df, 3)
    if len(highs) < 2 or len(lows) < 2:
        return None

    close = float(df['close'].iloc[-1])
    prev_high = float(highs[-2][1])
    prev_low = float(lows[-2][1])

    # A CHoCH is treated as a break against the immediately prior structural leg.
    if close > prev_high:
        return "BULL_CHoCH"
    if close < prev_low:
        return "BEAR_CHoCH"
    return None

# ===================== SMC SUPPLY/DEMAND =====================
def calculate_atr_series(df, period=14):
    df['tr'] = np.maximum(df['high'] - df['low'], 
                          np.maximum(abs(df['high'] - df['close'].shift(1)), 
                                     abs(df['low'] - df['close'].shift(1))))
    df['atr'] = df['tr'].rolling(window=period).mean()
    return df

def detect_demand_zones(df, sensitivity=0.25):
    zones = []
    df = calculate_atr_series(df.copy())
    
    if len(df) < 20:
        return []
    
    for i in range(10, len(df)-5):
        try:
            if df['close'].iloc[i] < df['open'].iloc[i]:
                body_size = abs(df['close'].iloc[i] - df['open'].iloc[i])
                atr_val = df['atr'].iloc[i]
                
                if atr_val is None or atr_val == 0:
                    continue
                    
                if body_size > atr_val * sensitivity:
                    future_high = df['high'].iloc[i+1:i+6].max()
                    if future_high > df['high'].iloc[i]:
                        zone_low = df['low'].iloc[i]
                        zone_high = df['high'].iloc[i]
                        strength = min(100, int((body_size / atr_val) * 50))               

                        if not any(abs(z[0] - zone_low) < atr_val * 0.5 for z in zones):
                            zones.append((zone_low, zone_high, strength, "DEMAND"))
        except:
            continue
    
    return zones[-SMC_MAX_ZONES:] if zones else []

def detect_supply_zones(df, sensitivity=0.25):
    zones = []
    df = calculate_atr_series(df.copy())
    
    if len(df) < 20:
        return []
    
    for i in range(10, len(df)-5):
        try:
            if df['close'].iloc[i] > df['open'].iloc[i]:
                body_size = abs(df['close'].iloc[i] - df['open'].iloc[i])
                atr_val = df['atr'].iloc[i]
                
                if atr_val is None or atr_val == 0:
                    continue
                    
                if body_size > atr_val * sensitivity:
                    future_low = df['low'].iloc[i+1:i+6].min()
                    if future_low < df['low'].iloc[i]:
                        zone_low = df['low'].iloc[i]
                        zone_high = df['high'].iloc[i]
                        strength = min(100, int((body_size / atr_val) * 50))
                        
                        if not any(abs(z[0] - zone_low) < atr_val * 0.5 for z in zones):
                            zones.append((zone_low, zone_high, strength, "SUPPLY"))
        except:
            continue
    
    return zones[-SMC_MAX_ZONES:] if zones else []

def price_in_smc_zone(price, zones, zone_type=None):
    if not zones or price is None:
        return False, None
    
    for zone in zones:
        try:
            zone_low, zone_high, strength, z_type = zone
            if zone_type and z_type != zone_type:
                continue
            if zone_low <= price <= zone_high:
                return True, zone
        except:
            continue
    
    return False, None

# ===================== SMART SWEEP (LIQUIDITY SWEEP) =====================
def smart_liquidity_sweep(df, direction):
    """V3: liquidity sweep on closed candles with close-back-through confirmation."""
    if df is None or len(df) < SWEEP_LOOKBACK + 3:
        return False
    try:
        # Exclude the signal candle itself from the liquidity reference.
        reference = df.iloc[-SWEEP_LOOKBACK-1:-1]
        last = df.iloc[-1]
        prev = df.iloc[-2]
        recent_high = float(reference['high'].max())
        recent_low = float(reference['low'].min())

        if direction == "BUY":
            swept = last['low'] < recent_low or prev['low'] < recent_low
            reclaimed = last['close'] > recent_low
            rejection = last['close'] > last['open'] or (last['close'] - last['low']) > (last['high'] - last['close'])
            return bool(swept and reclaimed and rejection)

        if direction == "SELL":
            swept = last['high'] > recent_high or prev['high'] > recent_high
            reclaimed = last['close'] < recent_high
            rejection = last['close'] < last['open'] or (last['high'] - last['close']) > (last['close'] - last['low'])
            return bool(swept and reclaimed and rejection)
    except Exception:
        return False
    return False

# ===================== FAKE BREAKOUT =====================
def fake_breakout_filter(df):
    if len(df) < 2:
        return False
        
    last = df.iloc[-1]
    prev = df.iloc[-2]

    body = abs(last['close'] - last['open'])
    range_candle = last['high'] - last['low']

    if range_candle == 0:
        return False

    body_ratio = body / range_candle

    if body_ratio < 0.25:
        return True

    if prev['close'] == last['close']:
        return True

    return False

# ===================== PATTERN DETECTIONS =====================
def _signal_candle(df):
    if df is None or len(df) < 1:
        return None
    return df.iloc[-1]

def detect_pinbar(df):
    candle = _signal_candle(df)
    if candle is None:
        return None
    body = abs(candle['close'] - candle['open'])
    upper_wick = candle['high'] - max(candle['open'], candle['close'])
    lower_wick = min(candle['open'], candle['close']) - candle['low']
    total_range = candle['high'] - candle['low']
    if total_range <= 0:
        return None
    if body / total_range <= 0.35 and lower_wick / total_range >= 0.55 and lower_wick >= upper_wick * 1.5:
        return "BULL"
    if body / total_range <= 0.35 and upper_wick / total_range >= 0.55 and upper_wick >= lower_wick * 1.5:
        return "BEAR"
    return None

def detect_rejection_wick(df):
    candle = _signal_candle(df)
    if candle is None:
        return None
    upper_wick = candle['high'] - max(candle['open'], candle['close'])
    lower_wick = min(candle['open'], candle['close']) - candle['low']
    total_range = candle['high'] - candle['low']
    if total_range <= 0:
        return None
    if lower_wick / total_range >= 0.60 and lower_wick > upper_wick * 1.5:
        return "BULL"
    if upper_wick / total_range >= 0.60 and upper_wick > lower_wick * 1.5:
        return "BEAR"
    return None

def detect_order_block(df):
    """V3: simple SMC OB = last opposite candle before a displacement candle."""
    if df is None or len(df) < 5:
        return None
    atr = atr_value(df)
    if atr is None or atr <= 0:
        return None
    base = df.iloc[-2]
    impulse = df.iloc[-1]
    impulse_body = abs(impulse['close'] - impulse['open'])
    if impulse_body < atr * 0.8:
        return None
    if base['close'] < base['open'] and impulse['close'] > impulse['open'] and impulse['close'] > base['high']:
        return "BULL"
    if base['close'] > base['open'] and impulse['close'] < impulse['open'] and impulse['close'] < base['low']:
        return "BEAR"
    return None

def detect_fvg(df):
    """V3: three-candle FVG; uses the last three closed candles and requires a real gap."""
    if df is None or len(df) < 3:
        return None
    a, b, c = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    atr = atr_value(df)
    min_gap = 0.0 if atr is None else max(0.01, atr * 0.05)
    if c['low'] > a['high'] + min_gap and b['close'] > b['open']:
        return "BULL"
    if c['high'] < a['low'] - min_gap and b['close'] < b['open']:
        return "BEAR"
    return None

# ===================== DAILY LOSS =====================
def check_daily_loss():
    global daily_start_balance, daily_date, trading_disabled_today

    now = datetime.now(WIB).date()

    if now != daily_date:
        daily_date = now
        daily_start_balance = mt5.account_info().balance
        trading_disabled_today = False
        runtime_message("🔄 New trading day. Daily reset.")

    account = mt5.account_info()
    daily_pnl = account.balance - daily_start_balance
    daily_loss_percent = (-daily_pnl / daily_start_balance) * 100 if daily_pnl < 0 else 0

    if daily_loss_percent >= MAX_DAILY_LOSS_PERCENT:
        trading_disabled_today = True

    return daily_pnl, round(daily_loss_percent, 2)

# ===================== TRADE ENGINE =====================
def calculate_lot(sl_points=None):
    """Return configured fixed lot, or calculate risk-based lot when enabled."""
    symbol_info = mt5.symbol_info(SYMBOL)
    if symbol_info is None:
        return float(LOT_SIZE)

    if not USE_DYNAMIC_LOT:
        return float(LOT_SIZE)

    account = mt5.account_info()
    if account is None:
        return float(LOT_SIZE)

    sl_points = float(sl_points or calculate_dynamic_sl())
    risk_money = float(account.balance) * (float(RISK_PER_TRADE_PERCENT) / 100.0)
    if sl_points <= 0 or risk_money <= 0:
        return float(LOT_SIZE)

    # Approximate monetary loss per 1 lot using tick value/tick size.
    tick_size = float(symbol_info.trade_tick_size or symbol_info.point or 0.01)
    tick_value = float(symbol_info.trade_tick_value or 0.0)
    distance_price = float(sl_points)
    if tick_size <= 0 or tick_value <= 0:
        return float(LOT_SIZE)

    loss_per_lot = (distance_price / tick_size) * tick_value
    if loss_per_lot <= 0:
        return float(LOT_SIZE)

    lot = risk_money / loss_per_lot
    return max(float(MIN_LOT_SIZE), min(float(MAX_LOT_SIZE), lot))

def calculate_dynamic_sl():
    """✅ BARU: Calculate SL based on ATR"""
    if not USE_ATR_SL:
        return SL_POINTS
    
    atr = get_atr_current()
    if atr is None or atr == 0:
        return SL_POINTS
    
    sl = atr * ATR_SL_MULTIPLIER
    return max(MIN_ATR_SL, min(MAX_ATR_SL, sl))

# ===== ATR SL FOR EXISTING POSITIONS (BARU) =====
def update_existing_positions_sl():
    """✅ BARU: Apply ATR SL to existing positions without SL (SL = 0)"""
    if not USE_ATR_SL_EXISTING:
        return
    
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions:
        return
    
    # Calculate ATR-based SL
    atr_sl_points = calculate_dynamic_sl()
    
    for pos in positions:
        # Only update if SL is 0 (no SL set)
        if pos.sl == 0:
            symbol_info = mt5.symbol_info(SYMBOL)
            if symbol_info is None:
                continue
            
            digits = symbol_info.digits
            
            if pos.type == 0:  # BUY
                new_sl = pos.price_open - atr_sl_points
                new_sl = round(new_sl, digits)
                # Ensure SL is below entry for BUY
                if new_sl < pos.price_open:
                    result = mt5.order_send({
                        "action": mt5.TRADE_ACTION_SLTP,
                        "position": pos.ticket,
                        "sl": new_sl,
                        "tp": pos.tp
                    })
                    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                        runtime_message(f"✅ ATR SL Applied to BUY #{pos.ticket}: Entry={pos.price_open}, New SL={new_sl}")
            else:  # SELL
                new_sl = pos.price_open + atr_sl_points
                new_sl = round(new_sl, digits)
                # Ensure SL is above entry for SELL
                if new_sl > pos.price_open:
                    result = mt5.order_send({
                        "action": mt5.TRADE_ACTION_SLTP,
                        "position": pos.ticket,
                        "sl": new_sl,
                        "tp": pos.tp
                    })
                    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                        runtime_message(f"✅ ATR SL Applied to SELL #{pos.ticket}: Entry={pos.price_open}, New SL={new_sl}")

def open_trade(direction):
    positions = mt5.positions_get(symbol=SYMBOL)
    if positions and len(positions) >= MAX_OPEN_POSITIONS:
            runtime_message(f"⚠️ Max positions reached ({MAX_OPEN_POSITIONS})")
            return
    
    # REMOVED: Check untuk mencegah multiple positions
    # Sekarang bisa buka posisi baru tanpa tunggu SL/TP posisi sebelumnya
    # Setiap posisi punya SL/TP sendiri

    symbol_info = mt5.symbol_info(SYMBOL)
    if symbol_info is None:
        runtime_message("❌ Symbol tidak ditemukan")
        return

    if not symbol_info.visible:
        mt5.symbol_select(SYMBOL, True)

    sl_points = calculate_dynamic_sl()
    lot = calculate_lot(sl_points)
    broker_min = float(symbol_info.volume_min)
    broker_max = float(symbol_info.volume_max)
    broker_step = float(symbol_info.volume_step or 0.01)
    lot = max(broker_min, min(broker_max, float(lot)))
    lot = round(lot / broker_step) * broker_step
    lot = round(lot, 8)

    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        runtime_message("❌ Tick tidak tersedia")
        return

    digits = symbol_info.digits
    
    # Gunakan SL dinamis / fixed sesuai konfigurasi
    tp_points = sl_points * RR_RATIO

    if direction == "BUY":
        price = tick.ask
        sl = price - sl_points
        tp = price + tp_points
        order_type = mt5.ORDER_TYPE_BUY
    else:
        price = tick.bid
        sl = price + sl_points
        tp = price - tp_points
        order_type = mt5.ORDER_TYPE_SELL

    price = round(price, digits)
    sl = round(sl, digits)
    tp = round(tp, digits)

    filling_modes = [
        mt5.ORDER_FILLING_IOC,
        mt5.ORDER_FILLING_FOK,
        mt5.ORDER_FILLING_RETURN
    ]

    for filling in filling_modes:
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": SYMBOL,
            "volume": lot,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": 777777,
            "type_filling": filling,
            "type_time": mt5.ORDER_TIME_GTC,
            "comment": "WEENfx_PRO"
        }

        result = mt5.order_send(request)

        if result is None:
            continue

        if result.retcode == mt5.TRADE_RETCODE_DONE:
            runtime_message(f"✅ SUCCESS: {direction} @ {price} | SL: {sl} | TP: {tp}")
            return
        else:
            runtime_message(f"❌ Failed: {result.retcode}")

    runtime_message(f"❌ ALL FILLING MODES FAILED:{filling_modes} Price:{price} SL:{sl} TP:{tp}")

def manage_trailing_sl():
    if not USE_TRAILING_SL:
        return
    
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions:
        return
    
    # ✅ Calculate ATR-based trailing start if enabled
    if USE_ATR_TRAIL_START:
        current_sl = calculate_dynamic_sl()
        trail_start = current_sl * TRAIL_START_PERCENT  # 50% of ATR SL
    else:
        trail_start = TRAIL_START_PROFIT  # Fixed $2
    for pos in positions:
        profit = pos.profit
        
        if profit < trail_start:
            continue
        
        tick = mt5.symbol_info_tick(SYMBOL)
        
        secure_profit = profit * (TRAIL_SECURE_PERCENT / 100)
        secure_points = secure_profit * 100
        
        if pos.type == 0:
            new_sl = pos.price_open + (secure_points / 100)
            if new_sl > pos.sl:
                mt5.order_send({
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "sl": round(new_sl, 3),
                    "tp": pos.tp
                })
        else:
            new_sl = pos.price_open - (secure_points / 100)
            if new_sl < pos.sl or pos.sl == 0:
                mt5.order_send({
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "sl": round(new_sl, 3),
                    "tp": pos.tp
                })

def manage_break_even():
    if not USE_BREAK_EVEN:
        return
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions:
        return
    for pos in positions:
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None:
            continue
        price = tick.bid if pos.type == 0 else tick.ask
        risk = abs(pos.price_open - pos.sl) if pos.sl and pos.sl > 0 else calculate_dynamic_sl()
        trigger = (risk * BE_TRIGGER_R) if USE_BE_R_BASED else BE_TRIGGER

        if pos.type == 0 and price - pos.price_open >= trigger:
            new_sl = pos.price_open + R1_BE_BUFFER
            if pos.sl == 0 or new_sl > pos.sl:
                mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "sl": new_sl, "tp": pos.tp})
        elif pos.type == 1 and pos.price_open - price >= trigger:
            new_sl = pos.price_open - R1_BE_BUFFER
            if pos.sl == 0 or new_sl < pos.sl:
                mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "sl": new_sl, "tp": pos.tp})

# ===================== SESSION ENGINE =====================
def _minutes(hhmm):
    h, m = map(int, str(hhmm).split(":"))
    return h * 60 + m

def _in_time_range(now_minutes, start, end):
    start_m = _minutes(start)
    end_m = _minutes(end)
    if start_m == end_m:
        return True
    if start_m < end_m:
        return start_m <= now_minutes < end_m
    return now_minutes >= start_m or now_minutes < end_m

def detect_sessions():
    """Detect all configured sessions. Detection never disables trading by itself."""
    global SESSION_STATUS
    now = datetime.now(WIB)
    now_minutes = now.hour * 60 + now.minute
    active = []
    for name in ("ASIA", "LONDON", "NEW_YORK", "LONDON_NEW_YORK_OVERLAP"):
        cfg = SESSION_CONFIG.get(name, {})
        if _in_time_range(now_minutes, cfg.get("START", "00:00"), cfg.get("END", "00:00")):
            active.append(name)

    # Display the most useful combined label.
    if "LONDON_NEW_YORK_OVERLAP" in active:
        SESSION_STATUS = "LONDON + NEW YORK (OVERLAP)"
    elif "NEW_YORK" in active:
        SESSION_STATUS = "NEW YORK"
    elif "LONDON" in active:
        SESSION_STATUS = "LONDON"
    elif "ASIA" in active:
        SESSION_STATUS = "ASIA"
    else:
        SESSION_STATUS = "OUT OF SESSION"
    return active

def in_session():
    """Return whether the current detected session is allowed to trade."""
    active = detect_sessions()
    if not USE_SESSION_FILTER or not SESSION_CONFIG.get("ENABLED", True):
        return True
    for name in active:
        if SESSION_CONFIG.get(name, {}).get("ENABLED", False):
            return True
    return False

def get_session_status_text():
    active = detect_sessions()
    enabled = []
    for name in active:
        if SESSION_CONFIG.get(name, {}).get("ENABLED", False):
            enabled.append(name)
    if not active:
        return SESSION_STATUS, "NO ACTIVE SESSION", False
    if not USE_SESSION_FILTER or not SESSION_CONFIG.get("ENABLED", True):
        return SESSION_STATUS, ", ".join(active), True
    return SESSION_STATUS, ", ".join(active), bool(enabled)

# ===================== CANDLE CONFIRMATION =====================
def check_candle_confirmation(df, direction):
    if not USE_CANDLE_CONFIRMATION:
        return True
    if df is None or len(df) < 2:
        return False

    candle = df.iloc[-1]
    previous = df.iloc[-2]
    if direction == "BUY":
        return bool(candle['close'] > candle['open'] or engulfing_on_candle(df, "BUY", 1) or previous['close'] < previous['open'])
    if direction == "SELL":
        return bool(candle['close'] < candle['open'] or engulfing_on_candle(df, "SELL", 1) or previous['close'] > previous['open'])
    return False

def is_new_candle(current_time, tf_seconds):
    global last_candle_time
    
    if last_candle_time is None:
        last_candle_time = current_time
        return True
    
    if current_time >= last_candle_time + tf_seconds:
        last_candle_time = current_time
        return True
    
    return False

def get_timeframe_seconds(tf):
    tf_map = {
        mt5.TIMEFRAME_M1: 60,
        mt5.TIMEFRAME_M5: 300,
        mt5.TIMEFRAME_M15: 900,
        mt5.TIMEFRAME_M30: 1800,
        mt5.TIMEFRAME_H1: 3600,
        mt5.TIMEFRAME_H4: 14400,
        mt5.TIMEFRAME_D1: 86400,
    }
    return tf_map.get(tf, 60)

# ===================== MARKET BIAS =====================
def update_market_bias(choch, trend):
    global market_bias, bias_changed
    
    old_bias = market_bias
    bias_changed = False
    
    if USE_CHOCH:
        if choch == "BULL_CHoCH":
            if market_bias != "BULLISH":
                market_bias = "BULLISH"
                bias_changed = True
                runtime_message(f"🔄 BIAS CHANGED: {old_bias} → BULLISH (CHoCH)")
        elif choch == "BEAR_CHoCH":
            if market_bias != "BEARISH":
                market_bias = "BEARISH"
                bias_changed = True
                runtime_message(f"🔄 BIAS CHANGED: {old_bias} → BEARISH (CHoCH)")
    
    if market_bias == "SIDEWAYS" and USE_TREND_FILTER:
        if trend == "BULLISH":
            market_bias = "BULLISH"
            bias_changed = True
        elif trend == "BEARISH":
            market_bias = "BEARISH"
            bias_changed = True
    
    return market_bias, bias_changed

# ===================== IMPROVED SCORING SYSTEM =====================
def calculate_signal_score(direction, conditions, df):
    """V3: keep the original 13-point compatibility score, but make each point meaningful."""
    score = 0
    met_conditions = []

    checks = [
        ("ENGULFING", direction == "BUY" and conditions.get('engulfing_buy') or direction == "SELL" and conditions.get('engulfing_sell')),
        ("ZONE", direction == "BUY" and conditions.get('in_demand_zone') or direction == "SELL" and conditions.get('in_supply_zone')),
        ("SWEEP", direction == "BUY" and conditions.get('sweep_buy') or direction == "SELL" and conditions.get('sweep_sell')),
        ("BOS", conditions.get('bos') == ("BULL_BOS" if direction == "BUY" else "BEAR_BOS")),
        ("TREND/BIAS", conditions.get('trend') == direction and False),
    ]
    # Trend/Bias is direction-mapped explicitly.
    trend_ok = (direction == "BUY" and (conditions.get('trend') == "BULLISH" or conditions.get('bias') == "BULLISH")) or (direction == "SELL" and (conditions.get('trend') == "BEARISH" or conditions.get('bias') == "BEARISH"))
    checks[4] = ("TREND/BIAS", trend_ok)

    pin = detect_pinbar(df)
    wick = detect_rejection_wick(df)
    ob = detect_order_block(df)
    fvg = detect_fvg(df)
    choch_ok = conditions.get('choch') == ("BULL_CHoCH" if direction == "BUY" else "BEAR_CHoCH")

    checks += [
        ("PINBAR", pin == ("BULL" if direction == "BUY" else "BEAR")),
        ("REJECTION", wick == ("BULL" if direction == "BUY" else "BEAR")),
        ("ORDERBLOCK", ob == ("BULL" if direction == "BUY" else "BEAR")),
        ("FVG", fvg == ("BULL" if direction == "BUY" else "BEAR")),
        ("ATR", bool(conditions.get("atr_ok"))),
        ("NO_FAKEBREAK", bool(conditions.get("not_fakeout"))),
        ("SESSION", bool(conditions.get("in_session"))),
        ("HTF", conditions.get("htf_trend") == ("BULLISH" if direction == "BUY" else "BEARISH")),
    ]

    # Keep MAX_SCORE = 13 by treating CHoCH as a quality gate, not an extra point.
    # This preserves the original UI/range while mandatory SMC handles core structure.
    for name, ok in checks:
        if ok:
            score += 1
            met_conditions.append(name)

    return score, met_conditions

# ===================== MANDATORY SMC CHECK (BARU) =====
def check_mandatory_smc(direction, bos, choch, in_zone):
    """V3: when enabled, require at least 2 of CHoCH, BOS and SMC zone."""
    if not USE_MANDATORY_SMC:
        return True

    if direction == "BUY":
        has_choch = choch == "BULL_CHoCH"
        has_bos = bos == "BULL_BOS"
    else:
        has_choch = choch == "BEAR_CHoCH"
        has_bos = bos == "BEAR_BOS"

    conditions_met = sum([has_choch, has_bos, bool(in_zone)])
    return conditions_met >= 2

# ===================== CONFLUENCE CHECK (BARU) =====
def check_confluence(htf_trend, direction):
    """✅ BARU: Multi-timeframe confluence"""
    if not USE_CONFLUENCE_CHECK:
        return True
    
    if direction == "BUY":
        return htf_trend == "BULLISH"
    else:  # SELL
        return htf_trend == "BEARISH"


# ===================== RICH DASHBOARD =====================
def rich_status(value, on_color="green", off_color="red"):
    return Text("ON", style=on_color) if value else Text("OFF", style=off_color)

def rich_direction(value):
    if value == "BULLISH" or value == "BUY":
        return Text(str(value), style="green")
    if value == "BEARISH" or value == "SELL":
        return Text(str(value), style="red")
    return Text(str(value), style="yellow")

def rich_signal(ready, score, max_score):
    t = Text()
    t.append("✓ READY " if ready else "✗ WAIT ", style="bold green" if ready else "bold red")
    t.append(f"{score}/{max_score}", style="green" if ready else "yellow")
    return t

def rich_pattern(value):
    if value in ("BULL", "BUY"):
        return Text(str(value), style="green")
    if value in ("BEAR", "SELL"):
        return Text(str(value), style="red")
    return Text("—" if value in (None, "None", "") else str(value), style="yellow")

def session_config_text():
    names = [
        ("ASIA", "ASIA"),
        ("LONDON", "LONDON"),
        ("NEW_YORK", "NEW YORK"),
        ("LONDON_NEW_YORK_OVERLAP", "OVERLAP")
    ]
    parts=[]
    for key,label in names:
        cfg=SESSION_CONFIG.get(key,{})
        enabled=cfg.get("ENABLED",False)
        start=cfg.get("START","--:--")
        end=cfg.get("END","--:--")
        parts.append(f"{label} {start}-{end} {'●' if enabled else '○'}")
    return parts

def render_rich_dashboard(*, account, positions, bid, ask, price_direction,
                          current_sl_points, current_session, active_sessions_text,
                          session_trade_allowed, trend, htf_trend, current_bias,
                          atr_val, atr_ok, buy_ready, sell_ready, buy_score, sell_score,
                          pending_direction, smart_sweep_buy, smart_sweep_sell,
                          choch, bos, engulf_buy, engulf_sell, in_supply_zone,
                          in_demand_zone, pinbar_status, wick_status, ob_status, fvg_status,
                          fakeout, daily_pnl, daily_loss_percent, trading_disabled_today,
                          buy_conditions, sell_conditions):
    now = datetime.now(WIB).strftime("%H:%M:%S WIB")
    trade_txt = Text("● ON", style="bold green") if USE_AUTO_TRADE else Text("○ OFF", style="bold red")
    tp_txt = Text("● ON", style="green") if USE_TAKE_PROFIT else Text("○ OFF", style="red")
    session_txt = Text(current_session, style="bold green" if session_trade_allowed else "bold yellow")

    header = Table.grid(expand=True)
    header.add_column(ratio=1)
    header.add_column(justify="center", ratio=1)
    header.add_column(justify="right", ratio=1)
    title=Text("WEENfx PRO SMC SCALPER", style="bold cyan")
    symbol=Text(SYMBOL, style="bold white")
    right=Text()
    right.append(now, style="white")
    right.append("  TRADE ", style="dim")
    right.append(trade_txt)
    right.append("  TP ", style="dim")
    right.append(tp_txt)
    header.add_row(title, symbol, right)

    price=Text()
    price.append("PRICE ", style="bold cyan")
    if bid is not None:
        pc="green" if price_direction=="▲" else "red" if price_direction=="▼" else "yellow"
        price.append(f"{bid:.2f} {price_direction}", style=f"bold {pc}")
    else:
        price.append("--", style="yellow")
    price.append(f"  BID {bid:.2f}" if bid is not None else "  BID --")
    price.append(f"  ASK {ask:.2f}" if ask is not None else "  ASK --")
    price.append(f"  ATR {atr_val:.2f}")
    price.append(f"  ATR-SL {current_sl_points:.2f}")
    price.append("  SESSION ")
    price.append(session_txt)
    price.append("  ")
    price.append("ALLOWED" if session_trade_allowed else "BLOCKED", style="bold green" if session_trade_allowed else "bold red")

    market=Table.grid(expand=True, padding=(0,1))
    market.add_column(style="cyan", no_wrap=True); market.add_column(ratio=1)
    market.add_row("Bias", rich_direction(current_bias))
    market.add_row("Trend", rich_direction(trend))
    market.add_row("HTF", rich_direction(htf_trend) if USE_CONFLUENCE_CHECK else Text("OFF", style="dim"))
    market.add_row("ATR", Text(f"{atr_val:.2f}  {'OK' if atr_ok else 'LOW'}", style="green" if atr_ok else "red"))
    market.add_row("Session", session_txt)
    market.add_row("Trading", Text("ALLOWED" if session_trade_allowed else "BLOCKED", style="bold green" if session_trade_allowed else "bold red"))

    signal=Table.grid(expand=True, padding=(0,1))
    signal.add_column(style="cyan", no_wrap=True); signal.add_column(ratio=1)
    signal.add_row("BUY", rich_signal(buy_ready,buy_score,MAX_SCORE))
    signal.add_row("SELL", rich_signal(sell_ready,sell_score,MAX_SCORE))
    confirm = "PENDING BUY" if pending_direction=="BUY" else "PENDING SELL" if pending_direction=="SELL" else "OFF"
    signal.add_row("Confirm", Text(confirm, style="yellow" if pending_direction else "dim"))
    signal.add_row("Minimum", Text(f"{MIN_SCORE_FOR_ENTRY}/{MAX_SCORE}"))
    if buy_ready and buy_conditions:
        signal.add_row("BUY+", Text(", ".join(buy_conditions.get("met",[])) or "—", style="green"))
    elif sell_ready and sell_conditions:
        signal.add_row("SELL+", Text(", ".join(sell_conditions.get("met",[])) or "—", style="red"))

    smc=Table.grid(expand=True, padding=(0,1))
    smc.add_column(style="cyan", no_wrap=True); smc.add_column(ratio=1)
    smc.add_row("Sweep", Text(f"{'✓' if smart_sweep_buy else '✗'} / {'✓' if smart_sweep_sell else '✗'}", style="green" if smart_sweep_buy or smart_sweep_sell else "red"))
    smc.add_row("CHoCH", rich_pattern("BULL" if choch=="BULL_CHoCH" else "BEAR" if choch=="BEAR_CHoCH" else None))
    smc.add_row("BOS", rich_pattern("BULL" if bos=="BULL_BOS" else "BEAR" if bos=="BEAR_BOS" else None))
    smc.add_row("Engulf", Text(f"{'✓' if engulf_buy else '✗'} / {'✓' if engulf_sell else '✗'}"))
    zone="SUPPLY" if in_supply_zone else "DEMAND" if in_demand_zone else "—"
    smc.add_row("Zone", Text(zone, style="red" if zone=="SUPPLY" else "green" if zone=="DEMAND" else "yellow"))
    smc.add_row("PinBar", rich_pattern(pinbar_status))
    smc.add_row("Reject", rich_pattern(wick_status))
    smc.add_row("OB", rich_pattern(ob_status))
    smc.add_row("FVG", rich_pattern(fvg_status))

    # Fixed symmetric 3-column layout. Rich controls the available width and
    # every column receives exactly the same ratio; panel content cannot change
    # the outer column proportions.
    top = Table.grid(expand=True, padding=0, pad_edge=False)
    top.add_column(ratio=1, overflow="fold")
    top.add_column(ratio=1, overflow="fold")
    top.add_column(ratio=1, overflow="fold")
    top.add_row(
        Panel(market, title="📊 MARKET", border_style="cyan", expand=True),
        Panel(signal, title="🎯 SIGNAL", border_style="yellow", expand=True),
        Panel(smc, title="📈 SMC", border_style="magenta", expand=True),
    )

    pos_table=Table(expand=True, show_header=True, header_style="bold cyan", box=None, padding=(0,1), pad_edge=False)
    pos_table.add_column("#", justify="center", width=4, no_wrap=True)
    pos_table.add_column("TYPE", justify="center", width=8, no_wrap=True)
    pos_table.add_column("LOT", justify="right", width=9, no_wrap=True)
    pos_table.add_column("ENTRY", justify="right", ratio=2, no_wrap=True)
    pos_table.add_column("CURRENT", justify="right", ratio=2, no_wrap=True)
    pos_table.add_column("SL", justify="right", ratio=2, no_wrap=True)
    pos_table.add_column("TP", justify="right", ratio=2, no_wrap=True)
    pos_table.add_column("P/L", justify="right", ratio=2, no_wrap=True)
    pos_table.add_column("STATUS", justify="left", ratio=2, no_wrap=True)
    if positions:
        for i,pos in enumerate(positions,1):
            ptype="BUY" if pos.type==0 else "SELL"
            pstyle="green" if pos.type==0 else "red"
            tick_price=(bid if pos.type==0 else ask) if (bid is not None and ask is not None) else pos.price_current
            pnl=float(pos.profit)
            risk=abs(pos.price_open-pos.sl) if pos.sl else calculate_dynamic_sl()
            if USE_ATR_TRAIL_START:
                trail_trigger=risk*TRAIL_START_PERCENT
            else:
                trail_trigger=TRAIL_START_PROFIT
            status="OPEN"
            if USE_BREAK_EVEN and ((pos.type==0 and tick_price-pos.price_open>=risk*BE_TRIGGER_R) or (pos.type==1 and pos.price_open-tick_price>=risk*BE_TRIGGER_R)):
                status="BE ACTIVE"
            if USE_TRAILING_SL and pnl>=trail_trigger:
                status="TRAILING"
            if pos.sl and ((pos.type==0 and pos.sl>=pos.price_open) or (pos.type==1 and pos.sl<=pos.price_open)):
                status="BE ACTIVE"
            pos_table.add_row(str(i),Text(ptype,style=f"bold {pstyle}"),f"{pos.volume:g}",f"{pos.price_open:.2f}",f"{tick_price:.2f}",f"{pos.sl:.2f}",f"{pos.tp:.2f}",Text(f"${pnl:.2f}",style="green" if pnl>=0 else "red"),Text(status,style="green" if status!="OPEN" else "yellow"))
    else:
        pos_table.add_row("—","—","—","—","—","—","—",Text("$0.00"),"NO POSITIONS")

    total_pnl=sum(float(p.profit) for p in positions) if positions else 0.0
    total_lot=sum(float(p.volume) for p in positions) if positions else 0.0
    buys=sum(1 for p in positions if p.type==0) if positions else 0
    sells=sum(1 for p in positions if p.type==1) if positions else 0
    maxpos="∞" if MAX_OPEN_POSITIONS==0 else str(MAX_OPEN_POSITIONS)
    pos_summary=Text()
    pos_summary.append(f"TOTAL P/L ${total_pnl:.2f}", style="green" if total_pnl>=0 else "red")
    pos_summary.append(f"  │ BUY {buys} │ SELL {sells} │ TOTAL LOT {total_lot:g} │ {len(positions) if positions else 0}/{maxpos}")
    pos_group=Group(pos_table,pos_summary)

    filters=Table.grid(expand=True,padding=(0,1)); filters.add_column(style="cyan"); filters.add_column(ratio=1)
    filters.add_row("Trend",rich_status(USE_TREND_FILTER)); filters.add_row("ATR",rich_status(USE_ATR_FILTER)); filters.add_row("Session",rich_status(USE_SESSION_FILTER)); filters.add_row("FakeBreak",Text("SAFE" if not fakeout else "FAKE",style="green" if not fakeout else "red")); filters.add_row("Scoring",Text(f"{'ON' if USE_SCORING_SYSTEM else 'OFF'}  Min {MIN_SCORE_FOR_ENTRY}/{MAX_SCORE}")); filters.add_row("Mandatory",Text("ON" if USE_MANDATORY_SMC else "OFF")); filters.add_row("Confluence",Text("ON" if USE_CONFLUENCE_CHECK else "OFF"))

    risk=Table.grid(expand=True,padding=(0,1)); risk.add_column(style="cyan"); risk.add_column(ratio=1)
    risk.add_row("AutoTrade",rich_status(USE_AUTO_TRADE)); risk.add_row("TakeProfit",rich_status(USE_TAKE_PROFIT)); risk.add_row("BreakEven",rich_status(USE_BREAK_EVEN)); risk.add_row("Trailing",rich_status(USE_TRAILING_SL)); risk.add_row("Lot",Text(f"{LOT_SIZE:g}  {'DYNAMIC' if USE_DYNAMIC_LOT else 'FIXED'}")); risk.add_row("SL / RR",Text(f"{current_sl_points:.2f} / 1:{RR_RATIO:g}")); risk.add_row("Daily",Text(f"${daily_pnl:.2f} / Loss {daily_loss_percent:.2f}%"))

    sess=Table.grid(expand=True,padding=(0,1)); sess.add_column(style="cyan"); sess.add_column(ratio=1)
    for key,label in (("ASIA","ASIA"),("LONDON","LONDON"),("NEW_YORK","NEW YORK"),("LONDON_NEW_YORK_OVERLAP","OVERLAP")):
        cfg=SESSION_CONFIG.get(key,{})
        active=key in detect_sessions()
        enabled=cfg.get("ENABLED",False)
        state="ACTIVE" if active else ("ENABLED" if enabled else "OFF")
        style="bold green" if active and enabled else "green" if enabled else "dim"
        sess.add_row(label,Text(f"{cfg.get('START','--:--')}-{cfg.get('END','--:--')}  {state}",style=style))

    # Same symmetric 3-column layout for FILTERS / RISK / SESSION.
    bottom = Table.grid(expand=True, padding=0, pad_edge=False)
    bottom.add_column(ratio=1, overflow="fold")
    bottom.add_column(ratio=1, overflow="fold")
    bottom.add_column(ratio=1, overflow="fold")
    bottom.add_row(
        Panel(filters, title="🔎 FILTERS", border_style="blue", expand=True),
        Panel(risk, title="⚙️ RISK / MANAGEMENT", border_style="green", expand=True),
        Panel(sess, title="🕐 SESSION", border_style="yellow", expand=True),
    )

    patterns=Text()
    patterns.append("PinBar ",style="cyan"); patterns.append(str(pinbar_status or "—"),style="green" if pinbar_status=="BULL" else "red" if pinbar_status=="BEAR" else "yellow")
    patterns.append(" │ Reject "); patterns.append(str(wick_status or "—"),style="green" if wick_status=="BULL" else "red" if wick_status=="BEAR" else "yellow")
    patterns.append(" │ OB "); patterns.append(str(ob_status or "—"),style="green" if ob_status=="BULL" else "red" if ob_status=="BEAR" else "yellow")
    patterns.append(" │ FVG "); patterns.append(str(fvg_status or "—"),style="green" if fvg_status=="BULL" else "red" if fvg_status=="BEAR" else "yellow")
    patterns.append(f" │ S/D {'SUPPLY' if in_supply_zone else 'DEMAND' if in_demand_zone else '—'}")
    patterns.append(f" │ Sweep {'●' if USE_SMART_SWEEP else '○'} │ BOS {'●' if USE_BOS else '○'} │ CHoCH {'●' if USE_CHOCH else '○'}")

    account_text=Text()
    bal=float(account.balance) if account else 0.0; eq=float(account.equity) if account else 0.0
    account_text.append(f"Balance ${bal:.2f} │ Equity ${eq:.2f} │ Daily P/L ",style="white")
    account_text.append(f"${daily_pnl:.2f}",style="green" if daily_pnl>=0 else "red")
    account_text.append(f" │ Daily Loss Limit {MAX_DAILY_LOSS_PERCENT:g}%")
    if trading_disabled_today:
        account_text.append(" │ ⛔ TRADING DISABLED",style="bold red")

    status="MONITORING POSITIONS" if positions else "WAITING FOR VALID SETUP"
    if trading_disabled_today: status="TRADING DISABLED — DAILY LOSS LIMIT"
    elif not session_trade_allowed and USE_SESSION_FILTER: status=f"OUTSIDE ENABLED SESSION — {current_session}"
    status_text=Text()
    status_text.append("● "+status,style="bold green" if positions else "bold yellow")
    status_text.append(f" │ Bias {current_bias} │ HTF {htf_trend} │ Cooldown {SIGNAL_COOLDOWN}s")

    parts=[
        Panel(header,border_style="cyan",padding=(0,1)),
        Panel(price,border_style="cyan",padding=(0,1)),
        top,
        Panel(pos_group,title=f"💼 OPEN POSITIONS  {len(positions) if positions else 0}/{maxpos}",border_style="white",padding=(0,1)),
        bottom,
        Panel(patterns,title="🧩 PATTERNS",border_style="magenta",padding=(0,1)),
        Panel(account_text,title="💰 ACCOUNT",border_style="green",padding=(0,1)),
        Panel(status_text,title="STATUS",border_style="cyan",padding=(0,1))
    ]
    status_line = Text()
    if runtime_message_text:
        status_line.append("EVENT ", style="bold cyan")
        status_line.append(runtime_message_text, style="white")
        parts.append(Panel(status_line, border_style="dim", padding=(0,1)))
    return Group(*parts)

# ===================== MAIN LOOP =====================
DASHBOARD_VERSION = "RICH-LIVE-SYMMETRIC-V2"
# Clean the terminal once at startup so output from a previous run is not
# left above the live dashboard. No startup log is printed into the dashboard.
console.clear()

# Initialization is performed inside Live so nothing is printed above the dashboard.
demand_zones = []
supply_zones = []
last_bid = None
price_direction = ""
last_smc_update = time.time()
signal_detected = False
pending_direction = None

# Cooldown tracking
last_buy_time = 0
last_sell_time = 0

# Track last SL update for existing positions
last_sl_update = time.time()

with Live(console=console, refresh_per_second=4, screen=True, transient=False) as live:
    # Silent startup: initialize SMC and existing-position SL without print()/console output.
    try:
        df_smc = get_data(TIMEFRAME_SMC, bars=500)
        if df_smc is not None and not df_smc.empty:
            demand_zones = detect_demand_zones(df_smc, SMC_ZONE_SENSITIVITY)
            supply_zones = detect_supply_zones(df_smc, SMC_ZONE_SENSITIVITY)
        if ATR_SL_UPDATE_ON_STARTUP and USE_ATR_SL_EXISTING:
            update_existing_positions_sl()
    except Exception as e:
        runtime_message(f"⚠ Startup initialization: {e}")

    while True:
        try:
            if not mt5.account_info():
                runtime_message("⚠ Reconnecting MT5...")
                mt5.initialize()
                time.sleep(3)
                continue

            df = get_closed_data(TIMEFRAME_ENTRY)
            if df is None or df.empty:
                runtime_message("Waiting for data...")
                time.sleep(2)
                continue

            bid, ask = get_live_price()
        
            if bid and last_bid:
                if bid > last_bid:
                    price_direction = "▲"
                elif bid < last_bid:
                    price_direction = "▼"
                else:
                    price_direction = "▶"
            last_bid = bid

            current_time = time.time()
        
            session_ok = in_session()
        
            # Update SMC zones
            if USE_SMC_SUPPLY_DEMAND and (current_time - last_smc_update > 60):
                df_smc = get_data(TIMEFRAME_SMC, bars=500)
                if df_smc is not None and not df_smc.empty:
                    demand_zones = detect_demand_zones(df_smc, SMC_ZONE_SENSITIVITY)
                    supply_zones = detect_supply_zones(df_smc, SMC_ZONE_SENSITIVITY)                            
                last_smc_update = current_time

            # ✅ Update ATR SL for existing positions without SL (every 60 seconds)
            if USE_ATR_SL_EXISTING and (current_time - last_sl_update > 60):
                update_existing_positions_sl()
                last_sl_update = current_time

            # Get indicators
            trend = trend_m5()
        
            # ✅ Higher timeframe trend for confluence
            htf_trend = get_higher_timeframe_trend() if USE_CONFLUENCE_CHECK else "SIDEWAYS"
        
            engulf_buy = engulfing(df, "BUY")
            engulf_sell = engulfing(df, "SELL")

            # ===== PATTERN STATUS FOR DASHBOARD =====
            # These values must be calculated before render_rich_dashboard().
            # Previously they were only calculated inside calculate_signal_score(),
            # which caused NameError when the dashboard tried to display them.
            pinbar_status = detect_pinbar(df) if USE_PINBAR else None
            wick_status = detect_rejection_wick(df) if USE_REJECTION_WICK else None
            ob_status = detect_order_block(df) if USE_ORDER_BLOCK else None
            fvg_status = detect_fvg(df) if USE_FVG else None

            atr_raw = atr_value(df)
            atr_val = round(atr_raw, 2) if atr_raw is not None else 0.0
            atr_ok = atr_raw is not None and atr_raw >= MIN_ATR_VALUE
        
            # BOS & CHoCH (Improved)
            bos = detect_bos(df, BOS_LOOKBACK)
            choch = detect_choch(df)
        
            # Update Market Bias
            current_bias, bias_just_changed = update_market_bias(choch, trend)
        
            # SMC Zones
            in_demand_zone = False
            in_supply_zone = False
            if bid and USE_SMC_SUPPLY_DEMAND:
                in_demand_zone, _ = price_in_smc_zone(bid, demand_zones, "DEMAND")
                in_supply_zone, _ = price_in_smc_zone(bid, supply_zones, "SUPPLY")
        
            # Smart Sweep
            smart_sweep_buy = smart_liquidity_sweep(df, "BUY")
            smart_sweep_sell = smart_liquidity_sweep(df, "SELL")
        
            # Fakeout
            fakeout = fake_breakout_filter(df)

            daily_pnl, daily_loss_percent = check_daily_loss()

            # ===== ENTRY LOGIC =====
            buy_ready = False
            sell_ready = False
            buy_score = 0
            sell_score = 0
            buy_conditions = {}
            sell_conditions = {}
        
            base_conditions = {
                'engulfing_buy': engulf_buy,
                'engulfing_sell': engulf_sell,
                'in_demand_zone': in_demand_zone,
                'in_supply_zone': in_supply_zone,
                'sweep_buy': smart_sweep_buy,
                'sweep_sell': smart_sweep_sell,
                'bos': bos,
                'choch': choch,
                'trend': trend,
                'bias': current_bias,
                'not_fakeout': not fakeout,
                'atr_ok': atr_ok,
                'in_session': session_ok,
                'htf_trend': htf_trend
            }
        
            if USE_SCORING_SYSTEM:
                buy_score, buy_met = calculate_signal_score("BUY", base_conditions, df)
                sell_score, sell_met = calculate_signal_score("SELL", base_conditions, df)
            
                # ✅ Apply mandatory SMC check
                mandatory_buy_ok = check_mandatory_smc("BUY", bos, choch, in_demand_zone)
                mandatory_sell_ok = check_mandatory_smc("SELL", bos, choch, in_supply_zone)
            
                # ✅ Apply confluence check
                confluence_buy = check_confluence(htf_trend, "BUY")
                confluence_sell = check_confluence(htf_trend, "SELL")
            
                # Apply all filters - JIKA USE_MANDATORY_SMC dan USE_CONFLUENCE_CHECK OFF baru langsung 3/13
                if USE_MANDATORY_SMC or USE_CONFLUENCE_CHECK:
                    buy_ready = buy_score >= MIN_SCORE_FOR_ENTRY and mandatory_buy_ok and confluence_buy
                    sell_ready = sell_score >= MIN_SCORE_FOR_ENTRY and mandatory_sell_ok and confluence_sell
                else:
                    # Jika mandatory dan confluence OFF, cukup score saja
                    buy_ready = buy_score >= MIN_SCORE_FOR_ENTRY
                    sell_ready = sell_score >= MIN_SCORE_FOR_ENTRY
            
                buy_conditions = {'score': buy_score, 'met': buy_met}
                sell_conditions = {'score': sell_score, 'met': sell_met}
            else:
                buy_ready = True
                sell_ready = True
            
                if USE_TREND_FILTER:
                    buy_ready = buy_ready and (trend == "BULLISH" or current_bias == "BULLISH")
                    sell_ready = sell_ready and (trend == "BEARISH" or current_bias == "BEARISH")
            
                if USE_ENGULFING:
                    buy_ready = buy_ready and engulf_buy
                    sell_ready = sell_ready and engulf_sell
            
                if USE_ATR_FILTER:
                    buy_ready = buy_ready and atr_ok
                    sell_ready = sell_ready and atr_ok
            
                if USE_SMC_SUPPLY_DEMAND:
                    buy_ready = buy_ready and in_demand_zone
                    sell_ready = sell_ready and in_supply_zone
            
                if USE_SMART_SWEEP:
                    buy_ready = buy_ready and smart_sweep_buy
                    sell_ready = sell_ready and smart_sweep_sell
            
                if USE_FAKE_BREAK_FILTER:
                    buy_ready = buy_ready and (not fakeout)
                    sell_ready = sell_ready and (not fakeout)
            
                if USE_BOS:
                    buy_ready = buy_ready and (bos == "BULL_BOS")
                    sell_ready = sell_ready and (bos == "BEAR_BOS")

                if USE_CHOCH:
                    buy_ready = buy_ready and (choch == "BULL_CHoCH")
                    sell_ready = sell_ready and (choch == "BEAR_CHoCH")

                if USE_SESSION_FILTER:
                    buy_ready = buy_ready and session_ok
                    sell_ready = sell_ready and session_ok

            # ===== COOLDOWN =====
            current_sl_points = calculate_dynamic_sl()
        
            # Apply cooldown
            if buy_ready and (current_time - last_buy_time < SIGNAL_COOLDOWN):
                buy_ready = False
            if sell_ready and (current_time - last_sell_time < SIGNAL_COOLDOWN):
                sell_ready = False

            # ===== CANDLE CONFIRMATION =====
            tf_seconds = get_timeframe_seconds(TIMEFRAME_ENTRY)
            new_candle = is_new_candle(current_time, tf_seconds)
        
            if pending_direction is not None and new_candle:
                confirmation_valid = check_candle_confirmation(df, pending_direction)
            
                if confirmation_valid:
                    if not trading_disabled_today and USE_AUTO_TRADE and session_ok:
                        if pending_direction == "BUY" and buy_ready:
                            runtime_message("✅ CONFIRMED BUY - Opening trade after candle confirmation!")
                            open_trade("BUY")
                            last_buy_time = current_time
                        elif pending_direction == "SELL" and sell_ready:
                            runtime_message("✅ CONFIRMED SELL - Opening trade after candle confirmation!")
                            open_trade("SELL")
                            last_sell_time = current_time
            
                pending_direction = None
                signal_detected = False
        
            if USE_CANDLE_CONFIRMATION:
                if buy_ready and not signal_detected:
                    pending_direction = "BUY"
                    signal_detected = True
                    runtime_message("⏳ BUY signal detected - Waiting for candle confirmation...")
                elif sell_ready and not signal_detected:
                    pending_direction = "SELL"
                    signal_detected = True
                    runtime_message("⏳ SELL signal detected - Waiting for candle confirmation...")
            else:
                if not trading_disabled_today and USE_AUTO_TRADE and session_ok:
                    if buy_ready and not sell_ready:
                        runtime_message("🚀 BUY SIGNAL!")
                        open_trade("BUY")
                        last_buy_time = current_time
                    elif sell_ready and not buy_ready:
                        runtime_message("🚀 SELL SIGNAL!")
                        open_trade("SELL")
                        last_sell_time = current_time

            manage_trailing_sl()
            manage_break_even()

            account = mt5.account_info()
            positions = mt5.positions_get(symbol=SYMBOL)

            # Colors
            def c(val):
                return f"{Fore.GREEN}ON{Style.RESET_ALL}" if val else f"{Fore.RED}OFF{Style.RESET_ALL}"
        
            def cn(val):
                return f"{Fore.GREEN}{val}{Style.RESET_ALL}"
            def cr(val):
                return f"{Fore.RED}{val}{Style.RESET_ALL}"
            def cy(val):
                return f"{Fore.YELLOW}{val}{Style.RESET_ALL}"
        
            current_session, active_sessions_text, session_trade_allowed = get_session_status_text()

            # Status colors
            trendclr = cn(trend) if trend == "BULLISH" else (cr(trend) if trend == "BEARISH" else cy(trend))
        
            # HTF Trend
            htf_clr = cn(htf_trend) if htf_trend == "BULLISH" else (cr(htf_trend) if htf_trend == "BEARISH" else cy(htf_trend))
        
            biasclr = cn(current_bias) if current_bias == "BULLISH" else (cr(current_bias) if current_bias == "BEARISH" else cy(current_bias))
        
            buyclr = cn("BUY") if buy_ready else cr("WAIT")
            sellclr = cr("SELL") if sell_ready else cn("SELL")
        
            if price_direction == "▲":
                pclr = cn(bid)
            elif price_direction == "▼":
                pclr = cr(bid)
            else:
                pclr = cy(bid)
        
            # Session display - Updated for Australia, Asia, Europe, America
            if "OVERLAP" in current_session or "NEW YORK" in current_session or "LONDON" in current_session:
                sessclr = cn(current_session)
            elif "ASIA" in current_session:
                sessclr = cy(current_session)
            else:
                sessclr = cy(current_session)
        
            pnlclr = cn(f"${round(daily_pnl,2)}") if daily_pnl >= 0 else cr(f"-${abs(daily_pnl)}")
        
            auto_clr = cn("ON") if USE_AUTO_TRADE else cr("OFF")
            tp_clr = c(USE_TAKE_PROFIT)
            trail_clr = c(USE_TRAILING_SL)
        
            confirm_clr = c(USE_CANDLE_CONFIRMATION)
            scoring_clr = c(USE_SCORING_SYSTEM)
            mandatory_clr = c(USE_MANDATORY_SMC)
            confluence_clr = c(USE_CONFLUENCE_CHECK)
            atr_sl_clr = c(USE_ATR_SL)
        
            # ✅ ATR SL Existing display
            atr_sl_existing_clr = c(USE_ATR_SL_EXISTING)

            # ===== RICH RESPONSIVE DASHBOARD =====
            live.update(render_rich_dashboard(
                account=account, positions=positions, bid=bid, ask=ask,
                price_direction=price_direction, current_sl_points=current_sl_points,
                current_session=current_session, active_sessions_text=active_sessions_text,
                session_trade_allowed=session_trade_allowed, trend=trend, htf_trend=htf_trend,
                current_bias=current_bias, atr_val=atr_val, atr_ok=atr_ok,
                buy_ready=buy_ready, sell_ready=sell_ready, buy_score=buy_score,
                sell_score=sell_score, pending_direction=pending_direction,
                smart_sweep_buy=smart_sweep_buy, smart_sweep_sell=smart_sweep_sell,
                choch=choch, bos=bos, engulf_buy=engulf_buy, engulf_sell=engulf_sell,
                in_supply_zone=in_supply_zone, in_demand_zone=in_demand_zone,
                pinbar_status=pinbar_status, wick_status=wick_status,
                ob_status=ob_status, fvg_status=fvg_status, fakeout=fakeout,
                daily_pnl=daily_pnl, daily_loss_percent=daily_loss_percent,
                trading_disabled_today=trading_disabled_today,
                buy_conditions=buy_conditions, sell_conditions=sell_conditions
            ))

            time.sleep(1)

        except KeyboardInterrupt:
            runtime_message("🛑 Script dihentikan oleh user (Ctrl+C)")
            break
        except Exception as e:
            runtime_message(f"❌ ERROR: {e}")
            time.sleep(3)   
