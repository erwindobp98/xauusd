from pathlib import Path
import json
import os

# ===================== CONFIG BOOTSTRAP =====================
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
STATE_FILE = BASE_DIR / "state.json"   # FIX #9: persist daily baseline across restarts

DEFAULT_CONFIG = {
    "SYMBOL": "XAUUSD",
    "TIMEFRAME_ENTRY": "M5",
    "TIMEFRAME_TREND": "M15",
    "TIMEFRAME_SMC": "M15",
    "CONFLUENCE_TF": "H1",
    "LOT_SIZE": 0.01,
    "USE_DYNAMIC_LOT": False,
    "RISK_PER_TRADE_PERCENT": 1.0,
    "MIN_LOT_SIZE": 0.01,
    "MAX_LOT_SIZE": 1.00,
    "LOT_STEP": 0.01,
    "SL_POINTS": 4.0,
    "RR_RATIO": 1.5,
    # FIX #11: 30% daily loss cap was extremely aggressive for an auto-scalper.
    # Left configurable but defaulted much tighter. Adjust to your own risk tolerance.
    "MAX_DAILY_LOSS_PERCENT": 5.0,
    "USE_ATR_SL": True,
    "ATR_SL_MULTIPLIER": 1.5,
    "MIN_ATR_SL": 4.0,
    "MAX_ATR_SL": 15.0,
    "USE_ATR_SL_EXISTING": True,
    "ATR_SL_UPDATE_ON_STARTUP": True,
    "USE_PINBAR": True,
    "USE_REJECTION_WICK": True,
    "USE_ORDER_BLOCK": True,
    "USE_FVG": True,
    "USE_SWING_SL": False,
    "SWING_LOOKBACK": 10,
    "SL_BUFFER": 0.5,
    "USE_TRADE_MGMT": False,
    "R1_BE_BUFFER": 0.1,
    "PARTIAL_CLOSE_PCT": 50,
    "TRAIL_BUFFER": 0.5,
    "USE_TAKE_PROFIT": True,
    "USE_AUTO_TRADE": True,
    "MAX_OPEN_POSITIONS": 1,       # 0 == unlimited (see FIX #2)
    "USE_TREND_FILTER": True,
    "USE_ENGULFING": True,
    "USE_ATR_FILTER": True,
    "USE_SESSION_FILTER": True,
    "USE_BREAK_EVEN": True,
    "USE_LIVE_PRICE": True,
    "USE_SMC_SUPPLY_DEMAND": True,
    "USE_SMART_SWEEP": True,
    "USE_FAKE_BREAK_FILTER": True,
    "USE_BOS": True,
    "USE_CHOCH": True,
    "USE_CONFLUENCE_CHECK": True,
    "USE_MANDATORY_SMC": True,
    "MANDATORY_SMC_MIN_CONDITIONS": 2,
    "USE_TRAILING_SL": False,
    "TRAIL_START_PROFIT": 2.0,
    "TRAIL_SECURE_PERCENT": 50,
    "USE_ATR_TRAIL_START": False,
    "TRAIL_START_PERCENT": 0.80,
    "USE_CANDLE_CONFIRMATION": False,
    "CONFIRMATION_LOOKBACK": 1,
    "USE_SCORING_SYSTEM": True,
    "MIN_SCORE_FOR_ENTRY": 6,
    "MAX_SCORE": 15,
    "SMC_ZONE_SENSITIVITY": 0.22,
    "SMC_MAX_ZONES": 5,
    "SWEEP_LOOKBACK": 15,
    "BOS_LOOKBACK": 20,
    "SWING_STRICTNESS": 3,          # FIX #3: now actually used by BOS/CHoCH swing detection
    "ATR_PERIOD": 8,
    "MIN_ATR_VALUE": 1.5,
    "BE_TRIGGER": 4.0,
    "USE_BE_R_BASED": True,
    "BE_TRIGGER_R": 1.0,
    "SESSION_TIMEZONE": "Asia/Jakarta",
    "SESSION_FILTER": {
        "ENABLED": True,
        "ASIA": {"ENABLED": True, "START": "07:00", "END": "15:00"},
        "LONDON": {"ENABLED": True, "START": "15:00", "END": "23:00"},
        "NEW_YORK": {"ENABLED": True, "START": "20:00", "END": "04:00"},
        "LONDON_NEW_YORK_OVERLAP": {"ENABLED": True, "START": "20:00", "END": "23:00"}
    },
    "SIGNAL_COOLDOWN": 60,
    "USE_CLOSED_CANDLE_LOCK": True,
    "MT5_CONNECT_RETRIES": 5,       # FIX #12: retry instead of quit() immediately
    "MT5_CONNECT_RETRY_DELAY": 5,
    "AUTO_FLATTEN_ON_DAILY_LOSS_LIMIT": True,   # FIX #2: close open positions when daily loss limit is hit
    "REVALIDATE_LOCKED_SIGNAL_ON_EXECUTION": True,  # FIX #4: re-check ATR/fakeout/zone right before firing a locked signal
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
        path.write_text(json.dumps(DEFAULT_CONFIG, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
        print("✅ Config file created successfully!")
        print(f"   📁 {path}")
        return dict(DEFAULT_CONFIG)

    try:
        current = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(current, dict):
            raise ValueError("root config harus object/dict")
        print(f"✅ Config loaded successfully from: {path}")
    except Exception as e:
        backup = path.with_suffix(path.suffix + ".broken")
        try:
            path.replace(backup)
            print(f"⚠️ Config corrupted ({e}), backed up to: {backup}")
        except OSError:
            pass
        path.write_text(json.dumps(DEFAULT_CONFIG, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
        print("✅ New config file created (recovered from default)")
        return dict(DEFAULT_CONFIG)

    merged = _deep_merge(DEFAULT_CONFIG, current)
    if merged != current:
        path.write_text(json.dumps(merged, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"✅ Config updated with new default values: {path}")
    return merged


def load_state(path=STATE_FILE):
    """FIX #9: persist daily baseline so a restart mid-day doesn't reset the loss limit."""
    path = Path(path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state, path=STATE_FILE):
    path = Path(path)
    try:
        path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except OSError:
        pass


print("=" * 60)
print("🚀 WEENfx PRO SMC SCALPER (CLEAN UI - FIXED)")
print("=" * 60)

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
TP_POINTS = SL_POINTS * RR_RATIO

# ===================== STATE VARIABLES =====================
last_candle_time = None
market_bias = "SIDEWAYS"
bias_changed = False

# ===================== CLOSED CANDLE LOCK =====================
locked_signal = None
locked_candle_time = None
locked_buy_score = 0
locked_sell_score = 0
locked_buy_conditions = {}
locked_sell_conditions = {}
is_locked = False

# ===================== ZONE (TANPA LOCK) =====================
locked_demand_zones = []
locked_supply_zones = []

# ===================== CONNECT MT5 (FIX #12: retry instead of instant quit) =====================
print("⏳ Connecting to MetaTrader 5...")
_connect_retries = int(CONFIG.get("MT5_CONNECT_RETRIES", 5))
_connect_delay = float(CONFIG.get("MT5_CONNECT_RETRY_DELAY", 5))
_connected = False
for _attempt in range(1, _connect_retries + 1):
    if mt5.initialize():
        _connected = True
        break
    print(f"⚠️ MT5 initialize failed (attempt {_attempt}/{_connect_retries}). Retrying in {_connect_delay}s...")
    time.sleep(_connect_delay)

if not _connected:
    runtime_message("❌ MT5 gagal connect setelah beberapa percobaan")
    print("❌ MT5 failed to initialize after retries!")
    quit()
print("✅ MT5 Connected")

_account_info = mt5.account_info()
if _account_info is None:
    print("❌ Tidak bisa membaca account_info() setelah connect. Cek login terminal MT5.")
    quit()

# FIX #9: restore daily baseline from persisted state if it's the same trading day
_state = load_state()
_today_wib = datetime.now(WIB).date()
_state_date = _state.get("daily_date")
if _state_date == str(_today_wib):
    daily_start_balance = float(_state.get("daily_start_balance", _account_info.balance))
    trading_disabled_today = bool(_state.get("trading_disabled_today", False))
else:
    daily_start_balance = _account_info.balance
    trading_disabled_today = False
daily_date = _today_wib
save_state({
    "daily_date": str(daily_date),
    "daily_start_balance": daily_start_balance,
    "trading_disabled_today": trading_disabled_today,
})


# ===================== DATA FUNCTIONS =====================
def get_data(tf, bars=300):
    rates = mt5.copy_rates_from_pos(SYMBOL, tf, 0, bars)
    if rates is None:
        return pd.DataFrame()
    return pd.DataFrame(rates)


def get_closed_data(tf, bars=300):
    df = get_data(tf, bars + 1)
    if df is None or df.empty or len(df) < 3:
        return pd.DataFrame()
    return df.iloc[:-1].copy().reset_index(drop=True)


def get_mt5_candle_time(tf):
    rates = mt5.copy_rates_from_pos(SYMBOL, tf, 0, 1)
    if rates is None or len(rates) == 0:
        return None
    return rates[0]['time']


def get_last_closed_candle_time(tf):
    df = get_closed_data(tf, bars=2)
    if df is None or df.empty:
        return None
    return df['time'].iloc[-1]


def is_new_candle_mt5(tf):
    global last_candle_time
    current_candle_time = get_mt5_candle_time(tf)
    if current_candle_time is None:
        return False
    if last_candle_time is None:
        last_candle_time = current_candle_time
        return True
    if current_candle_time != last_candle_time:
        last_candle_time = current_candle_time
        return True
    return False


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


def get_higher_timeframe_trend():
    df = get_closed_data(CONFLUENCE_TF, bars=100)
    if df is None or df.empty:
        return "SIDEWAYS"
    df['ema20'] = df['close'].ewm(span=20).mean()
    df['ema50'] = df['close'].ewm(span=50).mean()
    df['ema100'] = df['close'].ewm(span=100).mean()
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
    if len(df) < 2:
        return False
    prev, curr = df.iloc[-2], df.iloc[-1]
    if direction == "BUY":
        return prev['close'] < prev['open'] and curr['close'] > prev['open'] and curr['close'] > prev['high']
    if direction == "SELL":
        return prev['close'] > prev['open'] and curr['close'] < prev['open'] and curr['close'] < prev['low']
    return False


def atr_value(df):
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


def get_atr_current(df=None):
    # FIX #5: allow passing an already-fetched df so we don't refetch/recompute repeatedly
    if df is None:
        df = get_closed_data(TIMEFRAME_ENTRY, bars=100)
    return atr_value(df)


def get_live_price():
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick:
        return tick.bid, tick.ask
    return None, None


def detect_swing_points(df, lookback=10):
    highs = []
    lows = []
    for i in range(lookback, len(df) - lookback):
        is_high = True
        is_low = True
        for j in range(i - lookback, i + lookback + 1):
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


def detect_bos(df, lookback=20, swing_strictness=3):
    # FIX #3: previously hardcoded `3` regardless of the `lookback`/config value passed in.
    if df is None or len(df) < lookback + 10:
        return None
    highs, lows = detect_swing_points(df, swing_strictness)
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


def detect_choch(df, swing_strictness=3):
    # FIX #3: same fix as detect_bos - strictness now configurable, not hardcoded.
    if df is None or len(df) < 30:
        return None
    highs, lows = detect_swing_points(df, swing_strictness)
    if len(highs) < 2 or len(lows) < 2:
        return None
    close = float(df['close'].iloc[-1])
    prev_high = float(highs[-2][1])
    prev_low = float(lows[-2][1])
    if close > prev_high:
        return "BULL_CHoCH"
    if close < prev_low:
        return "BEAR_CHoCH"
    return None


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
    for i in range(10, len(df) - 5):
        try:
            if df['close'].iloc[i] < df['open'].iloc[i]:
                body_size = abs(df['close'].iloc[i] - df['open'].iloc[i])
                atr_val = df['atr'].iloc[i]
                if atr_val is None or atr_val == 0 or pd.isna(atr_val):
                    continue
                if body_size > atr_val * sensitivity:
                    future_high = df['high'].iloc[i + 1:i + 6].max()
                    if future_high > df['high'].iloc[i]:
                        zone_low = df['low'].iloc[i]
                        zone_high = df['high'].iloc[i]
                        strength = min(100, int((body_size / atr_val) * 50))
                        if not any(abs(z[0] - zone_low) < atr_val * 0.5 for z in zones):
                            zones.append((zone_low, zone_high, strength, "DEMAND"))
        except (KeyError, ValueError, TypeError) as e:
            # FIX #8: no longer a silent bare except - at least surfaces unexpected errors
            runtime_message(f"⚠ demand_zone calc issue at i={i}: {e}")
            continue
    return zones[-SMC_MAX_ZONES:] if zones else []


def detect_supply_zones(df, sensitivity=0.25):
    zones = []
    df = calculate_atr_series(df.copy())
    if len(df) < 20:
        return []
    for i in range(10, len(df) - 5):
        try:
            if df['close'].iloc[i] > df['open'].iloc[i]:
                body_size = abs(df['close'].iloc[i] - df['open'].iloc[i])
                atr_val = df['atr'].iloc[i]
                if atr_val is None or atr_val == 0 or pd.isna(atr_val):
                    continue
                if body_size > atr_val * sensitivity:
                    future_low = df['low'].iloc[i + 1:i + 6].min()
                    if future_low < df['low'].iloc[i]:
                        zone_low = df['low'].iloc[i]
                        zone_high = df['high'].iloc[i]
                        strength = min(100, int((body_size / atr_val) * 50))
                        if not any(abs(z[0] - zone_low) < atr_val * 0.5 for z in zones):
                            zones.append((zone_low, zone_high, strength, "SUPPLY"))
        except (KeyError, ValueError, TypeError) as e:
            runtime_message(f"⚠ supply_zone calc issue at i={i}: {e}")
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
        except (ValueError, TypeError):
            continue
    return False, None


def smart_liquidity_sweep(df, direction):
    if df is None or len(df) < SWEEP_LOOKBACK + 3:
        return False
    try:
        reference = df.iloc[-SWEEP_LOOKBACK - 1:-1]
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
    except Exception as e:
        runtime_message(f"⚠ sweep calc issue: {e}")
        return False
    return False


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


def detect_order_block(df, atr=None):
    # FIX #5: accept a precomputed ATR to avoid recalculating it redundantly.
    if df is None or len(df) < 5:
        return None
    if atr is None:
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


def detect_fvg(df, atr=None):
    # FIX #5: accept a precomputed ATR to avoid recalculating it redundantly.
    if df is None or len(df) < 3:
        return None
    a, b, c = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    if atr is None:
        atr = atr_value(df)
    min_gap = 0.0 if atr is None else max(0.01, atr * 0.05)
    if c['low'] > a['high'] + min_gap and b['close'] > b['open']:
        return "BULL"
    if c['high'] < a['low'] - min_gap and b['close'] < b['open']:
        return "BEAR"
    return None


def detect_divergence(df, direction, lookback=15):
    # NOTE: this is a simplified last-2-candle price-swing check, not a true
    # multi-swing price/oscillator divergence. Kept as-is for behavior parity,
    # just documented so it isn't mistaken for RSI/MACD divergence.
    if df is None or len(df) < lookback + 2:
        return False
    try:
        highs = df['high'].tail(lookback).values
        lows = df['low'].tail(lookback).values
        last_price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2]
        if direction == "SELL":
            if highs[-1] > highs[-2] and last_price < prev_price:
                return True
        elif direction == "BUY":
            if lows[-1] < lows[-2] and last_price > prev_price:
                return True
    except (KeyError, IndexError, ValueError) as e:
        runtime_message(f"⚠ divergence calc issue: {e}")
        return False
    return False


def check_daily_loss():
    global daily_start_balance, daily_date, trading_disabled_today
    now = datetime.now(WIB).date()
    if now != daily_date:
        daily_date = now
        account = mt5.account_info()
        daily_start_balance = account.balance if account else daily_start_balance
        trading_disabled_today = False
        runtime_message("🔄 New trading day. Daily reset.")
        save_state({
            "daily_date": str(daily_date),
            "daily_start_balance": daily_start_balance,
            "trading_disabled_today": trading_disabled_today,
        })
    account = mt5.account_info()
    if account is None:
        return 0.0, 0.0
    daily_pnl = account.balance - daily_start_balance
    daily_loss_percent = (-daily_pnl / daily_start_balance) * 100 if daily_pnl < 0 and daily_start_balance > 0 else 0
    was_disabled = trading_disabled_today
    if daily_loss_percent >= MAX_DAILY_LOSS_PERCENT:
        trading_disabled_today = True
    if trading_disabled_today and not was_disabled:
        # FIX #2: transition into "disabled" -> optionally flatten all open
        # positions immediately instead of just blocking new entries.
        runtime_message(f"⛔ DAILY LOSS LIMIT HIT: {daily_loss_percent:.2f}% >= {MAX_DAILY_LOSS_PERCENT:g}%")
        if AUTO_FLATTEN_ON_DAILY_LOSS_LIMIT:
            close_all_positions(SYMBOL, reason="daily_loss_limit")
    if trading_disabled_today != was_disabled:
        save_state({
            "daily_date": str(daily_date),
            "daily_start_balance": daily_start_balance,
            "trading_disabled_today": trading_disabled_today,
        })
    return daily_pnl, round(daily_loss_percent, 2)


def calculate_lot(sl_points=None):
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


def calculate_dynamic_sl(atr=None):
    # FIX #5: allow reusing an already-computed ATR value
    if not USE_ATR_SL:
        return SL_POINTS
    if atr is None:
        atr = get_atr_current()
    if atr is None or atr == 0:
        return SL_POINTS
    sl = atr * ATR_SL_MULTIPLIER
    return max(MIN_ATR_SL, min(MAX_ATR_SL, sl))


def _price_to_points(money_amount, symbol_info, volume):
    """
    FIX #1: proper conversion of a money P/L amount into a price distance,
    using the same tick_value/tick_size/volume math as calculate_lot(),
    instead of the previous arbitrary `* 100 / 100` shortcut.
    """
    if symbol_info is None or volume is None or volume <= 0:
        return None
    tick_size = float(symbol_info.trade_tick_size or symbol_info.point or 0.01)
    tick_value = float(symbol_info.trade_tick_value or 0.0)
    if tick_size <= 0 or tick_value <= 0:
        return None
    # money per 1.0 price-unit move, for this position's volume
    value_per_price_unit = (tick_value / tick_size) * volume
    if value_per_price_unit <= 0:
        return None
    return money_amount / value_per_price_unit


def update_existing_positions_sl():
    if not USE_ATR_SL_EXISTING:
        return
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions:
        return
    atr_sl_points = calculate_dynamic_sl()
    for pos in positions:
        if pos.sl == 0:
            symbol_info = mt5.symbol_info(SYMBOL)
            if symbol_info is None:
                continue
            digits = symbol_info.digits
            if pos.type == 0:
                new_sl = pos.price_open - atr_sl_points
                new_sl = round(new_sl, digits)
                if new_sl < pos.price_open:
                    result = mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "sl": new_sl, "tp": pos.tp})
                    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                        runtime_message(f"✅ ATR SL Applied to BUY #{pos.ticket}: Entry={pos.price_open}, New SL={new_sl}")
            else:
                new_sl = pos.price_open + atr_sl_points
                new_sl = round(new_sl, digits)
                if new_sl > pos.price_open:
                    result = mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "sl": new_sl, "tp": pos.tp})
                    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                        runtime_message(f"✅ ATR SL Applied to SELL #{pos.ticket}: Entry={pos.price_open}, New SL={new_sl}")


def open_trade(direction):
    positions = mt5.positions_get(symbol=SYMBOL)
    # FIX #2: MAX_OPEN_POSITIONS == 0 now truly means "unlimited" instead of
    # blocking every trade once one position exists.
    if MAX_OPEN_POSITIONS > 0 and positions and len(positions) >= MAX_OPEN_POSITIONS:
        runtime_message(f"⚠️ Max positions reached ({MAX_OPEN_POSITIONS})")
        return
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
    filling_modes = [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN]
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


def close_all_positions(symbol, reason=""):
    """
    FIX #2: previously the daily loss circuit breaker only blocked NEW entries
    (`trading_disabled_today`) but left already-open positions running until
    their own SL/TP hit. If the intent of MAX_DAILY_LOSS_PERCENT is a hard
    daily stop, that's a gap. This force-closes every open position for
    `symbol` at market when called. Gated by AUTO_FLATTEN_ON_DAILY_LOSS_LIMIT
    so it stays optional.
    """
    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        return
    symbol_info = mt5.symbol_info(symbol)
    digits = symbol_info.digits if symbol_info else 2
    filling_modes = [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN]
    for pos in positions:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            continue
        close_type = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY
        price = tick.bid if pos.type == 0 else tick.ask
        price = round(price, digits)
        closed = False
        for filling in filling_modes:
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": pos.volume,
                "type": close_type,
                "position": pos.ticket,
                "price": price,
                "deviation": 20,
                "magic": 777777,
                "type_filling": filling,
                "type_time": mt5.ORDER_TIME_GTC,
                "comment": f"AUTO_FLATTEN:{reason}"[:31],
            }
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                runtime_message(f"⛔ Auto-closed #{pos.ticket} ({reason})")
                closed = True
                break
        if not closed:
            runtime_message(f"❌ Failed to auto-close position #{pos.ticket}")


def manage_trailing_sl():
    if not USE_TRAILING_SL:
        return
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions:
        return
    symbol_info = mt5.symbol_info(SYMBOL)
    if symbol_info is None:
        return
    digits = symbol_info.digits

    if USE_ATR_TRAIL_START:
        current_sl = calculate_dynamic_sl()
        trail_start = current_sl * TRAIL_START_PERCENT
    else:
        trail_start = TRAIL_START_PROFIT

    for pos in positions:
        profit = pos.profit
        if profit < trail_start:
            continue
        secure_profit_money = profit * (TRAIL_SECURE_PERCENT / 100)
        # FIX #1: convert the money amount we want to "lock in" into an actual
        # price distance using tick value/size/volume, instead of `* 100 / 100`.
        secure_points = _price_to_points(secure_profit_money, symbol_info, pos.volume)
        if secure_points is None or secure_points <= 0:
            continue
        if pos.type == 0:
            new_sl = round(pos.price_open + secure_points, digits)
            if new_sl > pos.sl and new_sl < pos.price_current:
                mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "sl": new_sl, "tp": pos.tp})
        else:
            new_sl = round(pos.price_open - secure_points, digits)
            if (pos.sl == 0 or new_sl < pos.sl) and new_sl > pos.price_current:
                mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "sl": new_sl, "tp": pos.tp})


def manage_break_even():
    if not USE_BREAK_EVEN:
        return
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions:
        return
    symbol_info = mt5.symbol_info(SYMBOL)
    digits = symbol_info.digits if symbol_info else 2
    for pos in positions:
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None:
            continue
        price = tick.bid if pos.type == 0 else tick.ask
        risk = abs(pos.price_open - pos.sl) if pos.sl and pos.sl > 0 else calculate_dynamic_sl()
        trigger = (risk * BE_TRIGGER_R) if USE_BE_R_BASED else BE_TRIGGER
        if pos.type == 0 and price - pos.price_open >= trigger:
            new_sl = round(pos.price_open + R1_BE_BUFFER, digits)  # FIX #6: round to symbol digits
            if pos.sl == 0 or new_sl > pos.sl:
                mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "sl": new_sl, "tp": pos.tp})
        elif pos.type == 1 and pos.price_open - price >= trigger:
            new_sl = round(pos.price_open - R1_BE_BUFFER, digits)  # FIX #6
            if pos.sl == 0 or new_sl < pos.sl:
                mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "sl": new_sl, "tp": pos.tp})


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
    global SESSION_STATUS
    now = datetime.now(WIB)
    now_minutes = now.hour * 60 + now.minute
    active = []
    for name in ("ASIA", "LONDON", "NEW_YORK", "LONDON_NEW_YORK_OVERLAP"):
        cfg = SESSION_CONFIG.get(name, {})
        if _in_time_range(now_minutes, cfg.get("START", "00:00"), cfg.get("END", "00:00")):
            active.append(name)
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


# ===================== FINAL SCORING LOGIC =====================
def calculate_signal_score(direction, conditions, df):
    score = 0
    met_conditions = []

    # 1. ZONE (WAJIB, 1 Poin)
    zone_ok = (direction == "BUY" and conditions.get('in_demand_zone')) or (direction == "SELL" and conditions.get('in_supply_zone'))
    if zone_ok:
        score += 1
        met_conditions.append("ZONE")

    # 2. SWEEP (2 Poin)
    sweep_ok = (direction == "BUY" and conditions.get('sweep_buy')) or (direction == "SELL" and conditions.get('sweep_sell'))
    if sweep_ok:
        score += 2
        met_conditions.append("SWEEP")

    # 3. REJECTION WICK (2 Poin)
    wick_ok = (conditions.get('rejection_buy') if direction == "BUY" else conditions.get('rejection_sell'))
    if wick_ok:
        score += 2
        met_conditions.append("REJECT")

    # 4. PINBAR (2 Poin)
    pin_ok = (conditions.get('pinbar_buy') if direction == "BUY" else conditions.get('pinbar_sell'))
    if pin_ok:
        score += 2
        met_conditions.append("PINBAR")

    # 5. DIVERGENCE (2 Poin)
    div_ok = (conditions.get('divergence_buy') if direction == "BUY" else conditions.get('divergence_sell'))
    if div_ok:
        score += 2
        met_conditions.append("DIVERGENCE")

    # 6. CHOCH (1 Poin)
    choch_ok = conditions.get('choch') == ("BULL_CHoCH" if direction == "BUY" else "BEAR_CHoCH")
    if choch_ok:
        score += 1
        met_conditions.append("CHOCH")

    # 7. BOS (1 Poin)
    bos_ok = conditions.get('bos') == ("BULL_BOS" if direction == "BUY" else "BEAR_BOS")
    if bos_ok:
        score += 1
        met_conditions.append("BOS")

    # 8. ENGULFING (1 Poin)
    eng_ok = (conditions.get('engulfing_buy') if direction == "BUY" else conditions.get('engulfing_sell'))
    if eng_ok:
        score += 1
        met_conditions.append("ENGULF")

    # 9. ORDER BLOCK (1 Poin)
    ob_ok = (conditions.get('ob_buy') if direction == "BUY" else conditions.get('ob_sell'))
    if ob_ok:
        score += 1
        met_conditions.append("OB")

    # 10. FVG (1 Poin)
    fvg_ok = (conditions.get('fvg_buy') if direction == "BUY" else conditions.get('fvg_sell'))
    if fvg_ok:
        score += 1
        met_conditions.append("FVG")

    # 11. TREND (1 Poin)
    trend_ok = (direction == "BUY" and conditions.get('trend') == "BULLISH") or (direction == "SELL" and conditions.get('trend') == "BEARISH")
    if trend_ok:
        score += 1
        met_conditions.append("TREND")

    # 12. HTF (1 Poin)
    htf_ok = (direction == "BUY" and conditions.get('htf_trend') == "BULLISH") or (direction == "SELL" and conditions.get('htf_trend') == "BEARISH")
    if htf_ok:
        score += 1
        met_conditions.append("HTF")

    # 13. CONFLUENCE (1 Poin)
    confluence_ok = conditions.get('confluence')
    if confluence_ok:
        score += 1
        met_conditions.append("CONFLUENCE")

    return score, met_conditions


# ===================== FINAL MANDATORY LOGIC (GATE) =====================
def check_mandatory_smc(direction, in_zone, sweep, rejection, divergence):
    if not USE_MANDATORY_SMC:
        return True
    if not in_zone:
        return False
    trigger_points = sum([bool(sweep), bool(rejection), bool(divergence)])
    if trigger_points < MANDATORY_SMC_MIN_CONDITIONS:
        return False
    return True


def check_confluence(htf_trend, direction):
    if direction == "BUY":
        return htf_trend == "BULLISH"
    else:
        return htf_trend == "BEARISH"


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


def render_rich_dashboard(*, account, positions, bid, ask, price_direction,
                          current_sl_points, current_session, active_sessions_text,
                          session_trade_allowed, trend, htf_trend, current_bias,
                          atr_val, atr_ok, buy_ready, sell_ready, buy_score, sell_score,
                          smart_sweep_buy, smart_sweep_sell,
                          choch, bos, engulf_buy, engulf_sell, in_supply_zone,
                          in_demand_zone, pinbar_status, wick_status, ob_status, fvg_status,
                          fakeout, daily_pnl, daily_loss_percent, trading_disabled_today,
                          buy_conditions, sell_conditions, is_locked, locked_signal,
                          locked_buy_score, locked_sell_score, locked_candle_time,
                          div_status_buy, div_status_sell):
    now = datetime.now(WIB).strftime("%H:%M:%S WIB")
    trade_txt = Text("● ON", style="bold green") if USE_AUTO_TRADE else Text("○ OFF", style="bold red")
    tp_txt = Text("● ON", style="green") if USE_TAKE_PROFIT else Text("○ OFF", style="red")
    session_txt = Text(current_session, style="bold green" if session_trade_allowed else "bold yellow")

    header = Table.grid(expand=True)
    header.add_column(ratio=1)
    header.add_column(justify="center", ratio=1)
    header.add_column(justify="right", ratio=1)
    title = Text("WEENfx PRO SMC SCALPER", style="bold cyan")
    symbol = Text(SYMBOL, style="bold white")
    right = Text()
    right.append(now, style="white")
    right.append("  TRADE ", style="dim")
    right.append(trade_txt)
    right.append("  TP ", style="dim")
    right.append(tp_txt)
    header.add_row(title, symbol, right)

    price = Text()
    price.append("PRICE ", style="bold cyan")
    if bid is not None:
        pc = "green" if price_direction == "▲" else "red" if price_direction == "▼" else "yellow"
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

    market = Table.grid(expand=True, padding=(0, 1))
    market.add_column(style="cyan", no_wrap=True)
    market.add_column(ratio=1)
    market.add_row("Bias", rich_direction(current_bias))
    market.add_row("Trend", rich_direction(trend))
    market.add_row("HTF", rich_direction(htf_trend) if USE_CONFLUENCE_CHECK else Text("OFF", style="dim"))
    market.add_row("ATR", Text(f"{atr_val:.2f}  {'OK' if atr_ok else 'LOW'}", style="green" if atr_ok else "red"))
    market.add_row("Session", session_txt)
    market.add_row("Trading", Text("ALLOWED" if session_trade_allowed else "BLOCKED", style="bold green" if session_trade_allowed else "bold red"))

    signal = Table.grid(expand=True, padding=(0, 1))
    signal.add_column(style="cyan", no_wrap=True)
    signal.add_column(ratio=1)

    if is_locked and locked_signal:
        lock_text = Text("🔒 LOCKED", style="bold yellow")
        signal.add_row("STATUS", lock_text)
        if locked_signal == "BUY":
            signal.add_row("LOCKED", Text(f"BUY {locked_buy_score}/{MAX_SCORE}", style="bold green"))
        else:
            signal.add_row("LOCKED", Text(f"SELL {locked_sell_score}/{MAX_SCORE}", style="bold red"))
        signal.add_row("CANDLE", Text(time.strftime('%H:%M', time.gmtime(locked_candle_time)) if locked_candle_time else "--", style="dim"))
    else:
        signal.add_row("STATUS", Text("🔄 ANALYZING", style="cyan"))

    signal.add_row("BUY", rich_signal(buy_ready, buy_score, MAX_SCORE))
    signal.add_row("SELL", rich_signal(sell_ready, sell_score, MAX_SCORE))
    signal.add_row("Minimum", Text(f"{MIN_SCORE_FOR_ENTRY}/{MAX_SCORE}"))
    if is_locked and locked_signal == "BUY":
        signal.add_row("BUY+", Text(", ".join(locked_buy_conditions.get("met", [])) or "—", style="green"))
    elif is_locked and locked_signal == "SELL":
        signal.add_row("SELL+", Text(", ".join(locked_sell_conditions.get("met", [])) or "—", style="red"))
    elif buy_ready and buy_conditions:
        signal.add_row("BUY+", Text(", ".join(buy_conditions.get("met", [])) or "—", style="green"))
    elif sell_ready and sell_conditions:
        signal.add_row("SELL+", Text(", ".join(sell_conditions.get("met", [])) or "—", style="red"))

    smc = Table.grid(expand=True, padding=(0, 1))
    smc.add_column(style="cyan", no_wrap=True)
    smc.add_column(ratio=1)
    smc.add_row("Sweep", Text(f"{'✓' if smart_sweep_buy else '✗'} / {'✓' if smart_sweep_sell else '✗'}", style="green" if smart_sweep_buy or smart_sweep_sell else "red"))
    smc.add_row("CHoCH", rich_pattern("BULL" if choch == "BULL_CHoCH" else "BEAR" if choch == "BEAR_CHoCH" else None))
    smc.add_row("BOS", rich_pattern("BULL" if bos == "BULL_BOS" else "BEAR" if bos == "BEAR_BOS" else None))
    smc.add_row("Engulf", Text(f"{'✓' if engulf_buy else '✗'} / {'✓' if engulf_sell else '✗'}"))
    zone = "SUPPLY" if in_supply_zone else "DEMAND" if in_demand_zone else "—"
    smc.add_row("Zone", Text(zone, style="red" if zone == "SUPPLY" else "green" if zone == "DEMAND" else "yellow"))
    smc.add_row("Div", Text(f"{'BULL' if div_status_buy else 'BEAR' if div_status_sell else '—'}", style="green" if div_status_buy else "red" if div_status_sell else "yellow"))
    smc.add_row("PinBar", rich_pattern(pinbar_status))
    smc.add_row("Reject", rich_pattern(wick_status))
    smc.add_row("OB", rich_pattern(ob_status))
    smc.add_row("FVG", rich_pattern(fvg_status))

    top = Table.grid(expand=True, padding=0, pad_edge=False)
    top.add_column(ratio=1, overflow="fold")
    top.add_column(ratio=1, overflow="fold")
    top.add_column(ratio=1, overflow="fold")
    top.add_row(
        Panel(market, title="📊 MARKET", border_style="cyan", expand=True),
        Panel(signal, title="🎯 SIGNAL", border_style="yellow", expand=True),
        Panel(smc, title="📈 SMC", border_style="magenta", expand=True),
    )

    pos_table = Table(expand=True, show_header=True, header_style="bold cyan", box=None, padding=(0, 1), pad_edge=False)
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
        for i, pos in enumerate(positions, 1):
            ptype = "BUY" if pos.type == 0 else "SELL"
            pstyle = "green" if pos.type == 0 else "red"
            tick_price = (bid if pos.type == 0 else ask) if (bid is not None and ask is not None) else pos.price_current
            pnl = float(pos.profit)
            risk = abs(pos.price_open - pos.sl) if pos.sl else calculate_dynamic_sl()
            if USE_ATR_TRAIL_START:
                trail_trigger = risk * TRAIL_START_PERCENT
            else:
                trail_trigger = TRAIL_START_PROFIT
            status = "OPEN"
            if USE_BREAK_EVEN and ((pos.type == 0 and tick_price - pos.price_open >= risk * BE_TRIGGER_R) or (pos.type == 1 and pos.price_open - tick_price >= risk * BE_TRIGGER_R)):
                status = "BE ACTIVE"
            if USE_TRAILING_SL and pnl >= trail_trigger:
                status = "TRAILING"
            if pos.sl and ((pos.type == 0 and pos.sl >= pos.price_open) or (pos.type == 1 and pos.sl <= pos.price_open)):
                status = "BE ACTIVE"
            pos_table.add_row(str(i), Text(ptype, style=f"bold {pstyle}"), f"{pos.volume:g}", f"{pos.price_open:.2f}", f"{tick_price:.2f}", f"{pos.sl:.2f}", f"{pos.tp:.2f}", Text(f"${pnl:.2f}", style="green" if pnl >= 0 else "red"), Text(status, style="green" if status != "OPEN" else "yellow"))
    else:
        pos_table.add_row("—", "—", "—", "—", "—", "—", "—", Text("$0.00"), "NO POSITIONS")

    total_pnl = sum(float(p.profit) for p in positions) if positions else 0.0
    total_lot = sum(float(p.volume) for p in positions) if positions else 0.0
    buys = sum(1 for p in positions if p.type == 0) if positions else 0
    sells = sum(1 for p in positions if p.type == 1) if positions else 0
    maxpos = "∞" if MAX_OPEN_POSITIONS == 0 else str(MAX_OPEN_POSITIONS)
    pos_summary = Text()
    pos_summary.append(f"TOTAL P/L ${total_pnl:.2f}", style="green" if total_pnl >= 0 else "red")
    pos_summary.append(f"  │ BUY {buys} │ SELL {sells} │ TOTAL LOT {total_lot:g} │ {len(positions) if positions else 0}/{maxpos}")
    pos_group = Group(pos_table, pos_summary)

    filters = Table.grid(expand=True, padding=(0, 1))
    filters.add_column(style="cyan")
    filters.add_column(ratio=1)
    filters.add_row("Trend", rich_status(USE_TREND_FILTER))
    filters.add_row("ATR", rich_status(USE_ATR_FILTER))
    filters.add_row("Session", rich_status(USE_SESSION_FILTER))
    filters.add_row("FakeBreak", Text("SAFE" if not fakeout else "FAKE", style="green" if not fakeout else "red"))
    filters.add_row("Scoring", Text(f"{'ON' if USE_SCORING_SYSTEM else 'OFF'}  Min {MIN_SCORE_FOR_ENTRY}/{MAX_SCORE}"))
    filters.add_row("Mandatory", Text("ON" if USE_MANDATORY_SMC else "OFF"))
    filters.add_row("Confluence", Text("ON" if USE_CONFLUENCE_CHECK else "OFF"))
    filters.add_row("CandleLock", rich_status(USE_CLOSED_CANDLE_LOCK))

    risk = Table.grid(expand=True, padding=(0, 1))
    risk.add_column(style="cyan")
    risk.add_column(ratio=1)
    risk.add_row("AutoTrade", rich_status(USE_AUTO_TRADE))
    risk.add_row("TakeProfit", rich_status(USE_TAKE_PROFIT))
    risk.add_row("BreakEven", rich_status(USE_BREAK_EVEN))
    risk.add_row("Trailing", rich_status(USE_TRAILING_SL))
    risk.add_row("Lot", Text(f"{LOT_SIZE:g}  {'DYNAMIC' if USE_DYNAMIC_LOT else 'FIXED'}"))
    risk.add_row("SL / RR", Text(f"{current_sl_points:.2f} / 1:{RR_RATIO:g}"))
    risk.add_row("Daily", Text(f"${daily_pnl:.2f} / Loss {daily_loss_percent:.2f}%"))

    sess = Table.grid(expand=True, padding=(0, 1))
    sess.add_column(style="cyan")
    sess.add_column(ratio=1)
    for key, label in (("ASIA", "ASIA"), ("LONDON", "LONDON"), ("NEW_YORK", "NEW YORK"), ("LONDON_NEW_YORK_OVERLAP", "OVERLAP")):
        cfg = SESSION_CONFIG.get(key, {})
        active = key in detect_sessions()
        enabled = cfg.get("ENABLED", False)
        state = "ACTIVE" if active else ("ENABLED" if enabled else "OFF")
        style = "bold green" if active and enabled else "green" if enabled else "dim"
        sess.add_row(label, Text(f"{cfg.get('START', '--:--')}-{cfg.get('END', '--:--')}  {state}", style=style))

    bottom = Table.grid(expand=True, padding=0, pad_edge=False)
    bottom.add_column(ratio=1, overflow="fold")
    bottom.add_column(ratio=1, overflow="fold")
    bottom.add_column(ratio=1, overflow="fold")
    bottom.add_row(
        Panel(filters, title="🔎 FILTERS", border_style="blue", expand=True),
        Panel(risk, title="⚙️ RISK / MANAGEMENT", border_style="green", expand=True),
        Panel(sess, title="🕐 SESSION", border_style="yellow", expand=True),
    )

    account_text = Text()
    bal = float(account.balance) if account else 0.0
    eq = float(account.equity) if account else 0.0
    account_text.append(f"Balance ${bal:.2f} │ Equity ${eq:.2f} │ Daily P/L ", style="white")
    account_text.append(f"${daily_pnl:.2f}", style="green" if daily_pnl >= 0 else "red")
    account_text.append(f" │ Daily Loss Limit {MAX_DAILY_LOSS_PERCENT:g}%")
    if trading_disabled_today:
        account_text.append(" │ ⛔ TRADING DISABLED", style="bold red")

    status = "MONITORING POSITIONS" if positions else "WAITING FOR VALID SETUP"
    if trading_disabled_today:
        status = "TRADING DISABLED — DAILY LOSS LIMIT"
    elif not session_trade_allowed and USE_SESSION_FILTER:
        status = f"OUTSIDE ENABLED SESSION — {current_session}"
    if is_locked and locked_signal:
        status += f" 🔒 LOCKED: {locked_signal}"
    status_text = Text()
    status_text.append("● " + status, style="bold green" if positions else "bold yellow")
    status_text.append(f" │ Bias {current_bias} │ HTF {htf_trend} │ Cooldown {SIGNAL_COOLDOWN}s")

    parts = [
        Panel(header, border_style="cyan", padding=(0, 1)),
        Panel(price, border_style="cyan", padding=(0, 1)),
        top,
        Panel(pos_group, title=f"💼 OPEN POSITIONS  {len(positions) if positions else 0}/{maxpos}", border_style="white", padding=(0, 1)),
        bottom,
        Panel(account_text, title="💰 ACCOUNT", border_style="green", padding=(0, 1)),
        Panel(status_text, title="STATUS", border_style="cyan", padding=(0, 1))
    ]
    status_line = Text()
    if runtime_message_text:
        status_line.append("EVENT ", style="bold cyan")
        status_line.append(runtime_message_text, style="white")
        parts.append(Panel(status_line, border_style="dim", padding=(0, 1)))
    return Group(*parts)


# ===================== MAIN LOOP =====================
print("=" * 60)
print("📊 Starting Dashboard...")
print(f"   Symbol: {SYMBOL}")
print(f"   Entry TF: {TIMEFRAME_ENTRY}")
print(f"   SMC TF: {TIMEFRAME_SMC}")
print(f"   Auto Trade: {'ON' if USE_AUTO_TRADE else 'OFF'}")
print(f"   Closed Candle Lock: {'ON' if USE_CLOSED_CANDLE_LOCK else 'OFF'}")
print(f"   Session Filter: {'ON' if USE_SESSION_FILTER else 'OFF'}")
print(f"   Max Open Positions: {'∞' if MAX_OPEN_POSITIONS == 0 else MAX_OPEN_POSITIONS}")
print("=" * 60)
print("⏳ Press Ctrl+C to stop")
print("=" * 60)

time.sleep(2)
console.clear()

# ===================== INITIALIZATION =====================
demand_zones = []
supply_zones = []
last_bid = None
price_direction = ""
last_smc_update = time.time()
last_buy_time = 0
last_sell_time = 0
last_sl_update = time.time()
last_candle_time = get_last_closed_candle_time(TIMEFRAME_ENTRY)

with Live(console=console, refresh_per_second=4, screen=True, transient=False) as live:
    try:
        df_smc = get_closed_data(TIMEFRAME_SMC, bars=500)
        if df_smc is not None and not df_smc.empty:
            demand_zones = detect_demand_zones(df_smc, SMC_ZONE_SENSITIVITY)
            supply_zones = detect_supply_zones(df_smc, SMC_ZONE_SENSITIVITY)
            print(f"✅ SMC Zones loaded: {len(demand_zones)} Demand, {len(supply_zones)} Supply")
        if ATR_SL_UPDATE_ON_STARTUP and USE_ATR_SL_EXISTING:
            update_existing_positions_sl()
    except Exception as e:
        runtime_message(f"⚠ Startup initialization: {e}")

    while True:
        try:
            current_time = time.time()
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

            new_candle = is_new_candle_mt5(TIMEFRAME_ENTRY)
            session_ok = in_session()

            if USE_SMC_SUPPLY_DEMAND and (current_time - last_smc_update > 60):
                df_smc = get_closed_data(TIMEFRAME_SMC, bars=500)
                if df_smc is not None and not df_smc.empty:
                    demand_zones = detect_demand_zones(df_smc, SMC_ZONE_SENSITIVITY)
                    supply_zones = detect_supply_zones(df_smc, SMC_ZONE_SENSITIVITY)
                last_smc_update = current_time

            if USE_ATR_SL_EXISTING and (current_time - last_sl_update > 60):
                update_existing_positions_sl()
                last_sl_update = current_time

            trend = trend_m5()
            htf_trend = get_higher_timeframe_trend() if USE_CONFLUENCE_CHECK else "SIDEWAYS"

            engulf_buy = engulfing(df, "BUY")
            engulf_sell = engulfing(df, "SELL")

            # FIX #4 + #5: compute each pattern exactly once, respecting its toggle,
            # and share a single ATR value across everything that needs it this iteration.
            atr_raw = atr_value(df)
            atr_val = round(atr_raw, 2) if atr_raw is not None else 0.0
            atr_ok = atr_raw is not None and atr_raw >= MIN_ATR_VALUE

            pinbar_status = detect_pinbar(df) if USE_PINBAR else None
            wick_status = detect_rejection_wick(df) if USE_REJECTION_WICK else None
            ob_status = detect_order_block(df, atr=atr_raw) if USE_ORDER_BLOCK else None
            fvg_status = detect_fvg(df, atr=atr_raw) if USE_FVG else None

            bos = detect_bos(df, BOS_LOOKBACK, SWING_STRICTNESS) if USE_BOS else None
            choch = detect_choch(df, SWING_STRICTNESS) if USE_CHOCH else None
            current_bias, bias_just_changed = update_market_bias(choch, trend)

            in_demand_zone = False
            in_supply_zone = False

            if USE_SMC_SUPPLY_DEMAND:
                # 1. CLOSE CANDLE (Untuk Skor & Mandatory)
                zone_check_price = df['close'].iloc[-1]
                signal_in_demand_zone, _ = price_in_smc_zone(zone_check_price, demand_zones, "DEMAND")
                signal_in_supply_zone, _ = price_in_smc_zone(zone_check_price, supply_zones, "SUPPLY")

                # 2. LIVE PRICE (Untuk Eksekusi)
                execution_in_demand_zone, _ = price_in_smc_zone(bid, demand_zones, "DEMAND")
                execution_in_supply_zone, _ = price_in_smc_zone(bid, supply_zones, "SUPPLY")
            else:
                signal_in_demand_zone = signal_in_supply_zone = False
                execution_in_demand_zone = execution_in_supply_zone = False

            smart_sweep_buy = smart_liquidity_sweep(df, "BUY") if USE_SMART_SWEEP else False
            smart_sweep_sell = smart_liquidity_sweep(df, "SELL") if USE_SMART_SWEEP else False

            div_buy = detect_divergence(df, "BUY")
            div_sell = detect_divergence(df, "SELL")

            # FIX #4: these used to be recomputed as separate, redundant, unconditional
            # calls (`rej_buy`/`rej_sell` and `pin_buy`/`pin_sell` were literally
            # identical calls to the same function). Now derived once from the
            # single toggled `pinbar_status` / `wick_status` computed above.
            rej_status_buy = wick_status == "BULL"
            rej_status_sell = wick_status == "BEAR"
            pin_status_buy = pinbar_status == "BULL"
            pin_status_sell = pinbar_status == "BEAR"

            ob_buy = ob_status == "BULL"
            ob_sell = ob_status == "BEAR"
            fvg_buy = fvg_status == "BULL"
            fvg_sell = fvg_status == "BEAR"

            fakeout = fake_breakout_filter(df)
            daily_pnl, daily_loss_percent = check_daily_loss()

            buy_ready = False
            sell_ready = False
            buy_score = 0
            sell_score = 0
            buy_conditions = {}
            sell_conditions = {}

            # HITUNG CONFLUENCE (TIDAK MEMBLOKIR, HANYA BONUS POIN)
            confluence_buy = check_confluence(htf_trend, "BUY") if USE_CONFLUENCE_CHECK else False
            confluence_sell = check_confluence(htf_trend, "SELL") if USE_CONFLUENCE_CHECK else False

            base_conditions = {
                'in_demand_zone': signal_in_demand_zone,
                'in_supply_zone': signal_in_supply_zone,
                'sweep_buy': smart_sweep_buy,
                'sweep_sell': smart_sweep_sell,
                'rejection_buy': rej_status_buy,
                'rejection_sell': rej_status_sell,
                'pinbar_buy': pin_status_buy,
                'pinbar_sell': pin_status_sell,
                'divergence_buy': div_buy,
                'divergence_sell': div_sell,
                'bos': bos,
                'choch': choch,
                'ob_buy': ob_buy,
                'ob_sell': ob_sell,
                'fvg_buy': fvg_buy,
                'fvg_sell': fvg_sell,
                'engulfing_buy': engulf_buy if USE_ENGULFING else False,
                'engulfing_sell': engulf_sell if USE_ENGULFING else False,
                # FIX #1: USE_TREND_FILTER previously only fed market_bias, not
                # the TREND scoring point - toggling it off had zero effect on
                # scoring. Now it actually gates the point ("SIDEWAYS" never
                # matches BULLISH/BEARISH so trend_ok becomes False when off).
                'trend': trend if USE_TREND_FILTER else "SIDEWAYS",
                'htf_trend': htf_trend,
                'confluence': False  # Placeholder, added per-direction below
            }

            # Hitung Score untuk Buy dan Sell secara terpisah
            buy_score, buy_met = calculate_signal_score("BUY", base_conditions, df)
            sell_score, sell_met = calculate_signal_score("SELL", base_conditions, df)

            # Tambahkan poin confluence langsung jika sesuai arah
            if confluence_buy:
                buy_score += 1
                buy_met.append("CONFLUENCE")
            if confluence_sell:
                sell_score += 1
                sell_met.append("CONFLUENCE")

            # Mandatory: Zona (Close) + N Trigger (config-driven, FIX for hardcoded "2")
            mandatory_buy_ok = check_mandatory_smc("BUY", signal_in_demand_zone, smart_sweep_buy, rej_status_buy, div_buy)
            mandatory_sell_ok = check_mandatory_smc("SELL", signal_in_supply_zone, smart_sweep_sell, rej_status_sell, div_sell)

            filter_buy_ok = True
            filter_sell_ok = True

            # SESSION = HARD GATE! Jika tidak aktif, bot TIDAK AKAN PERNAH ENTRY.
            if USE_SESSION_FILTER:
                filter_buy_ok = filter_buy_ok and session_ok
                filter_sell_ok = filter_sell_ok and session_ok

            if USE_ATR_FILTER:
                filter_buy_ok = filter_buy_ok and atr_ok
                filter_sell_ok = filter_sell_ok and atr_ok

            if USE_FAKE_BREAK_FILTER:
                filter_buy_ok = filter_buy_ok and (not fakeout)
                filter_sell_ok = filter_sell_ok and (not fakeout)

            # FINAL DECISION
            buy_ready = buy_score >= MIN_SCORE_FOR_ENTRY and mandatory_buy_ok and filter_buy_ok and execution_in_demand_zone
            sell_ready = sell_score >= MIN_SCORE_FOR_ENTRY and mandatory_sell_ok and filter_sell_ok and execution_in_supply_zone

            buy_conditions = {'score': buy_score, 'met': buy_met}
            sell_conditions = {'score': sell_score, 'met': sell_met}

            current_sl_points = calculate_dynamic_sl(atr=atr_raw)

            if buy_ready and (current_time - last_buy_time < SIGNAL_COOLDOWN):
                buy_ready = False
            if sell_ready and (current_time - last_sell_time < SIGNAL_COOLDOWN):
                sell_ready = False

            if USE_CLOSED_CANDLE_LOCK:
                if new_candle:
                    current_candle_time = get_last_closed_candle_time(TIMEFRAME_ENTRY)
                    if buy_ready and not sell_ready:
                        locked_signal = "BUY"
                        locked_buy_score = buy_score
                        locked_sell_score = sell_score
                        locked_buy_conditions = buy_conditions
                        locked_sell_conditions = sell_conditions
                        locked_candle_time = current_candle_time
                        is_locked = True
                        runtime_message(f"🔒 LOCKED BUY @ {time.strftime('%H:%M', time.gmtime(current_candle_time)) if current_candle_time else '--'} ({buy_score}/{MAX_SCORE})")
                    elif sell_ready and not buy_ready:
                        locked_signal = "SELL"
                        locked_buy_score = buy_score
                        locked_sell_score = sell_score
                        locked_buy_conditions = buy_conditions
                        locked_sell_conditions = sell_conditions
                        locked_candle_time = current_candle_time
                        is_locked = True
                        runtime_message(f"🔒 LOCKED SELL @ {time.strftime('%H:%M', time.gmtime(current_candle_time)) if current_candle_time else '--'} ({sell_score}/{MAX_SCORE})")
                    else:
                        is_locked = False
                        locked_signal = None
                        runtime_message("No clear signal at candle close")
            else:
                is_locked = False
                locked_signal = None

            if USE_CLOSED_CANDLE_LOCK:
                if is_locked and locked_signal:
                    # FIX #4: a locked signal can sit waiting for cooldown across
                    # several loop iterations. Previously execution only re-checked
                    # session_ok - not whether ATR is still healthy, a fake-breakout
                    # has since appeared, or live price has left the SMC zone. Those
                    # are recomputed fresh every iteration anyway, so re-use them here
                    # instead of firing blindly on stale conditions.
                    execution_filters_ok = True
                    if REVALIDATE_LOCKED_SIGNAL_ON_EXECUTION:
                        if USE_ATR_FILTER:
                            execution_filters_ok = execution_filters_ok and atr_ok
                        if USE_FAKE_BREAK_FILTER:
                            execution_filters_ok = execution_filters_ok and (not fakeout)
                        if USE_SMC_SUPPLY_DEMAND:
                            if locked_signal == "BUY":
                                execution_filters_ok = execution_filters_ok and execution_in_demand_zone
                            elif locked_signal == "SELL":
                                execution_filters_ok = execution_filters_ok and execution_in_supply_zone

                    if not execution_filters_ok:
                        runtime_message(f"⚠️ Locked {locked_signal} cancelled — conditions changed before execution (ATR/fakeout/zone)")
                        is_locked = False
                        locked_signal = None
                    elif not trading_disabled_today and USE_AUTO_TRADE and session_ok:
                        if locked_signal == "BUY" and (current_time - last_buy_time >= SIGNAL_COOLDOWN):
                            runtime_message(f"🚀 EXECUTING LOCKED BUY ({locked_buy_score}/{MAX_SCORE})")
                            open_trade("BUY")
                            last_buy_time = current_time
                            is_locked = False
                            locked_signal = None
                        elif locked_signal == "SELL" and (current_time - last_sell_time >= SIGNAL_COOLDOWN):
                            runtime_message(f"🚀 EXECUTING LOCKED SELL ({locked_sell_score}/{MAX_SCORE})")
                            open_trade("SELL")
                            last_sell_time = current_time
                            is_locked = False
                            locked_signal = None
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
            current_session, active_sessions_text, session_trade_allowed = get_session_status_text()

            live.update(render_rich_dashboard(
                account=account, positions=positions, bid=bid, ask=ask,
                price_direction=price_direction, current_sl_points=current_sl_points,
                current_session=current_session, active_sessions_text=active_sessions_text,
                session_trade_allowed=session_trade_allowed, trend=trend, htf_trend=htf_trend,
                current_bias=current_bias, atr_val=atr_val, atr_ok=atr_ok,
                buy_ready=buy_ready, sell_ready=sell_ready, buy_score=buy_score,
                sell_score=sell_score, smart_sweep_buy=smart_sweep_buy, smart_sweep_sell=smart_sweep_sell,
                choch=choch, bos=bos, engulf_buy=engulf_buy, engulf_sell=engulf_sell,
                in_supply_zone=execution_in_supply_zone, in_demand_zone=execution_in_demand_zone,
                pinbar_status=pinbar_status, wick_status=wick_status,
                ob_status=ob_status, fvg_status=fvg_status, fakeout=fakeout,
                daily_pnl=daily_pnl, daily_loss_percent=daily_loss_percent,
                trading_disabled_today=trading_disabled_today,
                buy_conditions=buy_conditions, sell_conditions=sell_conditions,
                is_locked=is_locked, locked_signal=locked_signal,
                locked_buy_score=locked_buy_score, locked_sell_score=locked_sell_score,
                locked_candle_time=locked_candle_time,
                div_status_buy=div_buy, div_status_sell=div_sell
            ))

            time.sleep(1)

        except KeyboardInterrupt:
            runtime_message("🛑 Script dihentikan oleh user (Ctrl+C)")
            break
        except Exception as e:
            runtime_message(f"❌ ERROR: {e}")
            time.sleep(3)
