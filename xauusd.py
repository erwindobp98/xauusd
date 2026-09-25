# ============================================================
# Wfx PRO — SMC + FIBONACCI (3 MODEL) — v4.8
# ============================================================

# ===================== STDLIB IMPORTS =====================
from pathlib import Path
from datetime import datetime, timedelta
import json
import traceback
import time
import pytz

# ===================== THIRD-PARTY IMPORTS =====================
import numpy as np
import pandas as pd
from colorama import init
from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.live import Live

# ===================== CONFIG BOOTSTRAP =====================
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
STATE_FILE = BASE_DIR / "state.json"
ERROR_LOG = BASE_DIR / "error.log"

DEFAULT_CONFIG = {
    # =====================================================
    # ============ SYMBOL & TIMEFRAMES ====================
    # =====================================================
    "SYMBOL": "XAUUSD",
    "TIMEFRAME_ENTRY": "M5",       # TF eksekusi utama
    "TIMEFRAME_TREND": "M15",      # TF untuk deteksi trend
    "TIMEFRAME_SMC": "M15",        # TF untuk deteksi SMC zone
    "CONFLUENCE_TF": "H1",         # TF HTF untuk confluence check

    # =====================================================
    # ============ MODEL TOGGLES ==========================
    # =====================================================
    "USE_MODEL_CONTINUATION": True,
    "USE_MODEL_REVERSAL": True,
    "USE_MODEL_SWEEP": True,
    "USE_MODEL_PROFILES": True,    # Auto-switch setting per model

    # =====================================================
    # ============ SL (Stop Loss) =========================
    # =====================================================
    "USE_FIB_SL": True,            # Master toggle SL FIB
    "SL_MODEL_MAPPING": {          # Fallback SL source per model
        "CONTINUATION": "FIB",
        "REVERSAL": "FIB",
        "SWEEP": "ATR"
    },
    "SL_POINTS": 4.0,              # Fallback SL jika ATR off
    "USE_ATR_SL": True,            # Aktifkan ATR sebagai fallback SL
    "ATR_SL_MULTIPLIER": 1.5,      # SL = ATR × multiplier
    "MIN_ATR_SL": 4.0,             # Minimum SL dari ATR ($)
    "MAX_ATR_SL": 15.0,            # Maximum SL dari ATR ($)
    "SL_BUFFER": 1.5,              # Buffer tambahan di SL FIB ($)
    "MIN_SL_DISTANCE": 1.5,        # Jarak minimum SL dari entry ($)
    "MIN_SWING_SIZE": 5.0,         # Minimum ukuran swing untuk valid FIB ($)
    "SWING_FIB_LOOKBACK": 50,      # Lookback candle untuk cari swing FIB
    "USE_ATR_SL_EXISTING": False,  # Auto-pasang ATR SL untuk posisi tanpa SL
    "ATR_SL_UPDATE_ON_STARTUP": True,  # Cek posisi tanpa SL saat startup

    # =====================================================
    # ============ FIBONACCI ENTRY ZONES ==================
    # =====================================================
    "FIB_ENTRY_ZONE_CONTINUATION": [0.382, 0.786],  # Zona OTE continuation
    "FIB_ENTRY_ZONE_REVERSAL": [0.618, 0.79],       # Zona OTE reversal
    "FIB_ENTRY_ZONE_SWEEP": [0.5, 0.618],           # Zona OTE sweep

    # =====================================================
    # ============ TP (Take Profit) =======================
    # =====================================================
    "TP_MODE": "FIB",              # Fallback: FIB / LIQUIDITY / FIXED_RR
    "USE_TAKE_PROFIT": True,
    "USE_TP_AT_LIQUIDITY": True,   # True: TP3 ≤ liquidity target
    "FIXED_RR_TP1": 1.0,           # RR TP1 untuk mode FIXED_RR
    "FIXED_RR_TP2": 1.5,           # RR TP2 untuk mode FIXED_RR
    "FIXED_RR_TP3": 2.0,           # RR TP3 untuk mode FIXED_RR
    "FIB_TP1_EXT": 1.272,          # FIB extension level TP1
    "FIB_TP2_EXT": 1.618,          # FIB extension level TP2
    "FIB_TP3_EXT": 1.618,          # FIB extension level TP3

    # =====================================================
    # ============ PARTIAL CLOSE (BY LOT) =================
    # =====================================================
    # Logika: level partial otomatis dari lot entry
    #   lot < THR1            → no partial (single TP3)
    #   THR1 ≤ lot < THR2     → TP1 + TP2
    #   lot ≥ THR2            → TP1 + TP2 + TP3
    "PARTIAL_LOT_THRESHOLD_1": 0.015,
    "PARTIAL_LOT_THRESHOLD_2": 0.025,

    # =====================================================
    # ============ RR GUARD ===============================
    # =====================================================
    "USE_TP_RR_GUARD": True,
    "MIN_RR_TP3": 1.2,             # RR minimal (tolak di bawah ini)
    "MAX_RR_TP3": 10.0,            # RR soft cap (peringatan)
    "HARD_MAX_RR_TP3": 15.0,       # RR hard cap (tolak di atas ini)
    "RR_SOFT_WARN": True,          # RR 10-15 lolos dengan warning

    # =====================================================
    # ============ SIZING (LOT) ===========================
    # =====================================================
    "USE_BONUS_SIZING": True,      # Lot dari bonus point
    "BONUS_LOT_TIER_1": 0.01,      # Bonus ≤ 3 → lot
    "BONUS_LOT_TIER_2": 0.02,      # Bonus 4-8 → lot
    "BONUS_LOT_TIER_3": 0.03,      # Bonus ≥ 9 → lot
    "LOT_SIZE": 0.01,              # Fallback lot fixed
    "USE_DYNAMIC_LOT": False,      # Lot dari risk % balance
    "RISK_PER_TRADE_PERCENT": 1.0, # Risk % jika dynamic lot
    "MIN_LOT_SIZE": 0.01,
    "MAX_LOT_SIZE": 0.05,
    "HARD_LOT_CAP": 0.05,          # Cap keras (extra safety)
    "USE_HARD_LOT_CAP": True,
    "LOT_STEP": 0.01,

    # =====================================================
    # ============ MARGIN GUARD ===========================
    # =====================================================
    "USE_MARGIN_GUARD": True,
    "MARGIN_SAFETY_PERCENT": 30.0, # Tolak kalau margin > 30% free margin

    # =====================================================
    # ============ FILTERS ================================
    # =====================================================
    "USE_FAKE_BREAK_FILTER": False,
    "USE_PINBAR": True,
    "USE_REJECTION_WICK": True,
    "USE_ORDER_BLOCK": True,
    "USE_FVG": True,
    "USE_TRADE_MGMT": True,
    "USE_AUTO_TRADE": True,
    "MAX_OPEN_POSITIONS": 1,
    "USE_TREND_FILTER": True,
    "USE_ENGULFING": True,
    "USE_ATR_FILTER": True,
    "USE_SESSION_FILTER": True,
    "USE_LIVE_PRICE": True,
    "USE_SMC_SUPPLY_DEMAND": True,
    "USE_SMART_SWEEP": True,
    "USE_BOS": True,
    "USE_CHOCH": True,
    "USE_CONFLUENCE_CHECK": True,
    "USE_CLOSED_CANDLE_LOCK": True,

    # =====================================================
    # ============ TRAILING SL ============================
    # =====================================================
    "USE_TRAILING_SL": True,
    "USE_ATR_TRAIL_START": True,   # True: trigger ATR-based, False: fixed $
    "TRAIL_START_PERCENT": 0.80,   # % ATR untuk trigger (jika ATR mode)
    "TRAIL_SECURE_PERCENT": 75,    # % profit yang diamankan
    "TRAIL_START_PROFIT": 5.0,     # Trigger $ (jika fixed mode)

    # =====================================================
    # ============ BREAK EVEN =============================
    # =====================================================
    "USE_BREAK_EVEN": True,
    "BE_TRIGGER_R": 1.0,           # Trigger BE saat profit = N × risk
    "USE_BE_R_BASED": True,        # True: R-based, False: fixed $
    "BE_TRIGGER": 4.0,             # Trigger $ (jika non-R mode)
    "R1_BE_BUFFER": 0.1,           # Buffer BE di atas entry ($)

    # =====================================================
    # ============ SMC (Smart Money Concepts) =============
    # =====================================================
    "SMC_ZONE_SENSITIVITY": 0.15,  # Sensitivitas deteksi zona
    "SMC_MAX_ZONES": 10,           # Max zona yang disimpan
    "SWEEP_LOOKBACK": 10,          # Lookback untuk deteksi sweep
    "BOS_LOOKBACK": 20,            # Lookback untuk deteksi BOS
    "SWING_STRICTNESS": 1,         # Strictness swing (1=longgar, 3=ketat)
    "ATR_PERIOD": 14,              # Period ATR
    "MIN_ATR_VALUE": 1.0,          # Minimal ATR untuk boleh entry

    # =====================================================
    # ============ SESSION FILTER =========================
    # =====================================================
    "SESSION_TIMEZONE": "Asia/Jakarta",
    "SESSION_FILTER": {
        "ENABLED": True,
        "ASIA": {"ENABLED": True, "START": "07:00", "END": "15:00"},
        "LONDON": {"ENABLED": True, "START": "15:00", "END": "23:00"},
        "NEW_YORK": {"ENABLED": True, "START": "20:00", "END": "04:00"},
        "LONDON_NEW_YORK_OVERLAP": {"ENABLED": True, "START": "20:00", "END": "23:00"}
    },

    # =====================================================
    # ============ RISK MANAGEMENT ========================
    # =====================================================
    "MAX_DAILY_LOSS_PERCENT": 20.0,  # Stop trading jika daily loss ≥ ini
    "SIGNAL_COOLDOWN": 300,          # Jeda antar entry (detik)

    # =====================================================
    # ============ CONNECTION =============================
    # =====================================================
    "MT5_CONNECT_RETRIES": 5,
    "MT5_CONNECT_RETRY_DELAY": 5,

    # =====================================================
    # ============ STATS ==================================
    # =====================================================
    "STATS_LOOKBACK_DAYS": 7,
    "STATS_MAGIC": 777777,

    # =====================================================
    # ============ DIAGNOSTIC PANEL =======================
    # =====================================================
    "SHOW_DIAGNOSTIC_PANEL": True,

    # =====================================================
    # ============ MANUAL RECOVERY ========================
    # =====================================================
    "USE_MANUAL_RECOVERY": True,
    "MANUAL_PROFILE": {
        # --- SL / TP Recovery ---
        "SL_TP_MODE": "HYBRID",    # FIB / ATR / HYBRID
        "RR": 1.5,                 # RR untuk TP ATR fallback
        "FIB_TP_EXT": 1.618,       # FIB extension untuk TP
        "MIN_SL_PRICE": 3.0,       # SL minimal ($)
        "MAX_SL_PRICE": 20.0,      # SL maksimal ($)
        "CHECK_INTERVAL": 30,      # Interval cek (detik)
        "OVERRIDE_EXISTING": False,# Override SL/TP yang sudah ada

        # --- Trailing SL ---
        "USE_TRAILING_SL": True,
        "USE_ATR_TRAIL_START": True,
        "TRAIL_START_PERCENT": 0.70,
        "TRAIL_SECURE_PERCENT": 70,

        # --- Break Even ---
        "USE_BREAK_EVEN": True,
        "BE_TRIGGER_R": 1.0,
    },

    # =====================================================
    # ============ MODEL PROFILES =========================
    # =====================================================
    # Override setting global per model.
    # Setting yang tidak ada di sini akan fallback ke global.
    "MODEL_PROFILES": {
        "CONTINUATION": {
            "TP_MODE": "FIB",
            "USE_TAKE_PROFIT": True,
            "USE_FAKE_BREAK_FILTER": True,
            "SL_SOURCE": "FIB",
            "USE_BREAK_EVEN": True,
            "BE_TRIGGER_R": 1.0,
            "USE_TRAILING_SL": True,
            "USE_ATR_TRAIL_START": True,
            "TRAIL_START_PERCENT": 0.80,
            "TRAIL_SECURE_PERCENT": 75,
        },
        "REVERSAL": {
            "TP_MODE": "FIB",
            "USE_TAKE_PROFIT": True,
            "USE_FAKE_BREAK_FILTER": False,
            "SL_SOURCE": "FIB",
            "USE_BREAK_EVEN": True,
            "BE_TRIGGER_R": 1.0,
            "USE_TRAILING_SL": True,
            "USE_ATR_TRAIL_START": True,
            "TRAIL_START_PERCENT": 0.70,
            "TRAIL_SECURE_PERCENT": 70,
        },
        "SWEEP": {
            "TP_MODE": "LIQUIDITY",
            "USE_TAKE_PROFIT": True,
            "USE_FAKE_BREAK_FILTER": False,
            "SL_SOURCE": "ATR",
            "USE_BREAK_EVEN": True,
            "BE_TRIGGER_R": 0.5,
            "USE_TRAILING_SL": True,
            "USE_ATR_TRAIL_START": True,
            "TRAIL_START_PERCENT": 0.70,
            "TRAIL_SECURE_PERCENT": 70,
        },
    },
}


# ===================== CONFIG HELPERS =====================
def _deep_merge(default, current):
    """Merge nested dict: default di-merge dengan current."""
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
    """Load config dari file atau buat baru dengan default."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(DEFAULT_CONFIG, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
        print("[OK] Config created:", path)
        return dict(DEFAULT_CONFIG)
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(current, dict):
            raise ValueError("root not dict")
        print("[OK] Config loaded:", path)
    except Exception as e:
        backup = path.with_suffix(path.suffix + ".broken")
        try:
            path.replace(backup)
            print("[WARN] Config corrupted, backed up:", backup)
        except OSError:
            pass
        path.write_text(json.dumps(DEFAULT_CONFIG, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
        return dict(DEFAULT_CONFIG)
    merged = _deep_merge(DEFAULT_CONFIG, current)
    if merged != current:
        path.write_text(json.dumps(merged, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
        print("[OK] Config updated:", path)
    return merged


def load_state(path=STATE_FILE):
    """Load state dari file."""
    path = Path(path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state, path=STATE_FILE):
    """Simpan state ke file."""
    path = Path(path)
    try:
        path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except OSError:
        pass


def log_error(exc_text):
    """Log error ke file."""
    try:
        from datetime import datetime as _dt
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(f"\n[{_dt.now()}]\n{exc_text}\n")
    except Exception:
        pass


# ===================== BOOTSTRAP =====================
print("=" * 60)
print("WEENfx PRO - v4.8 (Dashboard Rapi + Session Lengkap)")
print("=" * 60)

CONFIG = load_or_create_config()

# ===================== MT5 IMPORT (setelah config) =====================
import MetaTrader5 as mt5

# ===================== INIT LIBRARIES =====================
init(autoreset=True)
console = Console()

# ===================== RUNTIME GLOBALS =====================
runtime_message_text = ""

# ===================== TIMEFRAME HELPER =====================
def timeframe_from_name(value):
    """Konversi nama TF ke konstanta MT5."""
    if isinstance(value, int):
        return value
    mapping = {
        "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1
    }
    return mapping.get(str(value).upper(), mt5.TIMEFRAME_M5)


def apply_config(c):
    """Load semua top-level config ke globals."""
    g = globals()
    for key, value in c.items():
        if key in ("SESSION_FILTER", "SESSION_TIMEZONE", "SL_MODEL_MAPPING",
                   "MODEL_PROFILES", "MANUAL_PROFILE"):
            continue
        if key in ("TIMEFRAME_ENTRY", "TIMEFRAME_TREND", "TIMEFRAME_SMC", "CONFLUENCE_TF"):
            g[key] = timeframe_from_name(value)
        else:
            g[key] = value


apply_config(CONFIG)

# ===================== CONFIG SHORTCUTS =====================
SESSION_CONFIG = CONFIG.get("SESSION_FILTER", DEFAULT_CONFIG["SESSION_FILTER"])
SL_MODEL_MAPPING = CONFIG.get("SL_MODEL_MAPPING", DEFAULT_CONFIG["SL_MODEL_MAPPING"])
MODEL_PROFILES = CONFIG.get("MODEL_PROFILES", DEFAULT_CONFIG["MODEL_PROFILES"])
MANUAL_PROFILE = CONFIG.get("MANUAL_PROFILE", DEFAULT_CONFIG["MANUAL_PROFILE"])
USE_MODEL_PROFILES = CONFIG.get("USE_MODEL_PROFILES", False)
SHOW_DIAGNOSTIC_PANEL = CONFIG.get("SHOW_DIAGNOSTIC_PANEL", True)
USE_ATR_SL_EXISTING = CONFIG.get("USE_ATR_SL_EXISTING", False)
ATR_SL_UPDATE_ON_STARTUP = CONFIG.get("ATR_SL_UPDATE_ON_STARTUP", True)
MAX_RR_TP3 = CONFIG.get("MAX_RR_TP3", 10.0)
HARD_MAX_RR_TP3 = CONFIG.get("HARD_MAX_RR_TP3", 15.0)
MIN_SWING_SIZE = CONFIG.get("MIN_SWING_SIZE", 5.0)
MIN_SL_DISTANCE = CONFIG.get("MIN_SL_DISTANCE", 1.5)
PARTIAL_LOT_THRESHOLD_1 = CONFIG.get("PARTIAL_LOT_THRESHOLD_1", 0.015)
PARTIAL_LOT_THRESHOLD_2 = CONFIG.get("PARTIAL_LOT_THRESHOLD_2", 0.025)
WIB = pytz.timezone(CONFIG.get("SESSION_TIMEZONE", "Asia/Jakarta"))
SESSION_STATUS = "OUT OF SESSION"


# ===================== SETTINGS GETTER =====================
def get_model_setting(model_name, key, default=None):
    """
    Ambil setting untuk model tertentu.
    Priority: MODEL_PROFILES → MANUAL_PROFILE → globals → default
    """
    if USE_MODEL_PROFILES and model_name in MODEL_PROFILES:
        profile = MODEL_PROFILES[model_name]
        if key in profile:
            return profile[key]
    if model_name == "MANUAL":
        if key in MANUAL_PROFILE:
            return MANUAL_PROFILE[key]
    if default is not None:
        return default
    return globals().get(key, default)


def runtime_message(message):
    """Set pesan runtime untuk ditampilkan di EVENT panel."""
    global runtime_message_text
    try:
        txt = str(message)
        txt = txt.replace("[", "(").replace("]", ")")
        runtime_message_text = txt[:250]
    except Exception:
        runtime_message_text = ""


# ===================== STATE =====================
last_candle_time = None
market_bias = "SIDEWAYS"
bias_changed = False
locked_signal = None
locked_candle_time = None
locked_buy_score = 0
locked_sell_score = 0
is_locked = False

POSITION_META = {}     # Metadata posisi bot {ticket: {...}}
PARTIAL_STATE = {}     # State partial close {ticket: {...}}

DIAG_STATE = {
    "swing_buy": False, "swing_sell": False,
    "demand_zones": 0, "supply_zones": 0,
    "htf_trend": "SIDEWAYS", "choch": None, "rej_wick": None,
    "in_demand": False, "in_supply": False,
    "sweep_buy": False, "sweep_sell": False,
    "notes": [],
}

MODEL_SCORES = {
    "CONTINUATION": {"bonus": 0, "rr": 0.0, "fib_ok": False, "dir": "-",
                     "valid": False, "met": []},
    "REVERSAL": {"bonus": 0, "rr": 0.0, "fib_ok": False, "dir": "-",
                 "valid": False, "met": []},
    "SWEEP": {"bonus": 0, "rr": 0.0, "fib_ok": False, "dir": "-",
              "valid": False, "met": []},
}


# ===================== MT5 CONNECTION =====================
def connect_mt5():
    """Connect ke MT5 dengan retry."""
    print("[..] Connecting to MT5...")
    retries = int(CONFIG.get("MT5_CONNECT_RETRIES", 5))
    delay = float(CONFIG.get("MT5_CONNECT_RETRY_DELAY", 5))
    for attempt in range(1, retries + 1):
        if mt5.initialize():
            print("[OK] MT5 Connected")
            return True
        print(f"[WARN] MT5 init failed ({attempt}/{retries})")
        time.sleep(delay)
    return False


if not connect_mt5():
    print("[ERR] MT5 failed to initialize!")
    quit()

_account_info = mt5.account_info()
if _account_info is None:
    print("[ERR] account_info() None")
    quit()


# ===================== STATE PERSISTENCE =====================
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

# Load POSITION_META
_pm_saved = _state.get("position_meta", {})
if isinstance(_pm_saved, dict):
    for k, v in _pm_saved.items():
        try:
            POSITION_META[int(k)] = v
        except (ValueError, TypeError):
            continue

# Load PARTIAL_STATE
_ps_saved = _state.get("partial_state", {})
if isinstance(_ps_saved, dict):
    for k, v in _ps_saved.items():
        try:
            PARTIAL_STATE[int(k)] = v
        except (ValueError, TypeError):
            continue


def persist_state():
    """Simpan POSITION_META, PARTIAL_STATE, dan daily state ke file."""
    try:
        save_state({
            "daily_date": str(daily_date),
            "daily_start_balance": daily_start_balance,
            "trading_disabled_today": trading_disabled_today,
            "position_meta": {str(k): v for k, v in POSITION_META.items()},
            "partial_state": {str(k): v for k, v in PARTIAL_STATE.items()},
        })
    except Exception:
        pass


persist_state()


# ===================== DATA FETCHING =====================
def get_data(tf, bars=300):
    """Ambil data OHLC dari MT5."""
    rates = mt5.copy_rates_from_pos(SYMBOL, tf, 0, bars)
    if rates is None:
        return pd.DataFrame()
    return pd.DataFrame(rates)


def get_closed_data(tf, bars=300):
    """Ambil data OHLC yang sudah closed (tanpa candle current)."""
    df = get_data(tf, bars + 1)
    if df is None or df.empty or len(df) < 3:
        return pd.DataFrame()
    return df.iloc[:-1].copy().reset_index(drop=True)


def get_mt5_candle_time(tf):
    """Waktu candle current dari MT5."""
    rates = mt5.copy_rates_from_pos(SYMBOL, tf, 0, 1)
    if rates is None or len(rates) == 0:
        return None
    return rates[0]['time']


def get_last_closed_candle_time(tf):
    """Waktu candle terakhir yang closed."""
    df = get_closed_data(tf, bars=2)
    if df is None or df.empty:
        return None
    return df['time'].iloc[-1]


def is_new_candle_mt5(tf):
    """Cek apakah ada candle baru (closed)."""
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


def get_live_price():
    """Ambil bid/ask terbaru."""
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick:
        return tick.bid, tick.ask
    return None, None


# ===================== TREND DETECTION =====================
def trend_m5():
    """Deteksi trend dari TF trend (EMA20 vs EMA50)."""
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
    """Deteksi trend dari HTF (EMA20, EMA50, EMA100)."""
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


def update_market_bias(choch, trend):
    """Update market bias dari CHoCH dan trend."""
    global market_bias, bias_changed
    old_bias = market_bias
    bias_changed = False
    if USE_CHOCH:
        if choch == "BULL_CHoCH" and market_bias != "BULLISH":
            market_bias = "BULLISH"
            bias_changed = True
            runtime_message(f"BIAS: {old_bias} -> BULLISH")
        elif choch == "BEAR_CHoCH" and market_bias != "BEARISH":
            market_bias = "BEARISH"
            bias_changed = True
            runtime_message(f"BIAS: {old_bias} -> BEARISH")
    if market_bias == "SIDEWAYS" and USE_TREND_FILTER:
        if trend == "BULLISH":
            market_bias = "BULLISH"
        elif trend == "BEARISH":
            market_bias = "BEARISH"
    return market_bias, bias_changed


# ===================== ATR =====================
def atr_value(df):
    """Hitung nilai ATR dari dataframe."""
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
    """Ambil nilai ATR saat ini."""
    if df is None:
        df = get_closed_data(TIMEFRAME_ENTRY, bars=100)
    return atr_value(df)


def calculate_atr_series(df, period=14):
    """Tambah kolom ATR ke dataframe."""
    df['tr'] = np.maximum(df['high'] - df['low'],
                          np.maximum(abs(df['high'] - df['close'].shift(1)),
                                     abs(df['low'] - df['close'].shift(1))))
    df['atr'] = df['tr'].rolling(window=period).mean()
    return df


def calculate_dynamic_sl(atr=None):
    """Hitung SL dari ATR."""
    if not USE_ATR_SL:
        return SL_POINTS
    if atr is None:
        atr = get_atr_current()
    if atr is None or atr == 0:
        return SL_POINTS
    sl = atr * ATR_SL_MULTIPLIER
    return max(MIN_ATR_SL, min(MAX_ATR_SL, sl))


# ===================== SWING & PATTERN =====================
def detect_swing_points(df, lookback=10):
    """Deteksi swing high/low dari dataframe."""
    highs = []
    lows = []
    if df is None or len(df) < lookback * 2 + 1:
        return highs, lows
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
    """Deteksi Break of Structure."""
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
    """Deteksi Change of Character."""
    if df is None or len(df) < 30:
        return None
    highs, lows = detect_swing_points(df, swing_strictness)
    if len(highs) < 2 or len(lows) < 2:
        try:
            recent = df.tail(20).iloc[:-1]
            recent_high = float(recent['high'].max())
            recent_low = float(recent['low'].min())
            close = float(df['close'].iloc[-1])
            if close > recent_high:
                return "BULL_CHoCH"
            if close < recent_low:
                return "BEAR_CHoCH"
        except Exception:
            pass
        return None
    close = float(df['close'].iloc[-1])
    prev_high = float(highs[-2][1])
    prev_low = float(lows[-2][1])
    if close > prev_high:
        return "BULL_CHoCH"
    if close < prev_low:
        return "BEAR_CHoCH"
    return None


def engulfing(df, direction):
    """Deteksi pola engulfing."""
    if len(df) < 2:
        return False
    prev, curr = df.iloc[-2], df.iloc[-1]
    if direction == "BUY":
        return prev['close'] < prev['open'] and curr['close'] > prev['open'] and curr['close'] > prev['high']
    if direction == "SELL":
        return prev['close'] > prev['open'] and curr['close'] < prev['open'] and curr['close'] < prev['low']
    return False


def _signal_candle(df):
    """Ambil candle terakhir (signal)."""
    if df is None or len(df) < 1:
        return None
    return df.iloc[-1]


def detect_pinbar(df):
    """Deteksi pola pinbar."""
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
    """Deteksi rejection wick."""
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
    """Deteksi order block."""
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
    """Deteksi Fair Value Gap."""
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
    """Deteksi divergence sederhana."""
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
    except (KeyError, IndexError, ValueError):
        return False
    return False


def fake_breakout_filter(df):
    """Deteksi fake breakout (body kecil / close sama prev)."""
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


# ===================== SMC ZONES =====================
def detect_demand_zones(df, sensitivity=0.25):
    """Deteksi zona demand."""
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
        except (KeyError, ValueError, TypeError):
            continue
    return zones[-SMC_MAX_ZONES:] if zones else []


def detect_supply_zones(df, sensitivity=0.25):
    """Deteksi zona supply."""
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
        except (KeyError, ValueError, TypeError):
            continue
    return zones[-SMC_MAX_ZONES:] if zones else []


def price_in_smc_zone(price, zones, zone_type=None):
    """Cek apakah harga ada di dalam zona SMC."""
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


def smart_liquidity_sweep(df, direction, lookback=None):
    """Deteksi liquidity sweep (versi longgar)."""
    if lookback is None:
        lookback = SWEEP_LOOKBACK
    if df is None or len(df) < lookback + 3:
        return False
    try:
        reference = df.iloc[-lookback - 1:-1]
        last = df.iloc[-1]
        prev = df.iloc[-2]
        recent_high = float(reference['high'].max())
        recent_low = float(reference['low'].min())

        if direction == "BUY":
            swept = last['low'] < recent_low or prev['low'] < recent_low
            if not swept:
                return False
            reclaimed = last['close'] > recent_low
            rejection = (last['close'] > last['open']) or \
                        ((last['close'] - last['low']) > (last['high'] - last['close']))
            return bool(reclaimed or rejection)

        if direction == "SELL":
            swept = last['high'] > recent_high or prev['high'] > recent_high
            if not swept:
                return False
            reclaimed = last['close'] < recent_high
            rejection = (last['close'] < last['open']) or \
                        ((last['high'] - last['close']) > (last['close'] - last['low']))
            return bool(reclaimed or rejection)
    except Exception:
        return False
    return False


# ===================== FIBONACCI =====================
def fib_retracement(swing_low, swing_high, level):
    """Hitung level fib retracement."""
    diff = swing_high - swing_low
    return swing_low + diff * (1 - level)


def fib_extension(swing_low, swing_high, level):
    """FIB extension untuk BUY (TP di atas)."""
    diff = swing_high - swing_low
    return swing_low + diff * level


def fib_extension_sell(swing_low, swing_high, level):
    """FIB extension untuk SELL (TP di bawah)."""
    diff = swing_high - swing_low
    return swing_high - diff * level


def find_last_swing_for_fib(df, direction, lookback=None):
    """
    Return (swing_low, swing_high) atau (None, None).
    Versi longgar dengan fallback ke max/min dari window.
    """
    if lookback is None:
        lookback = SWING_FIB_LOOKBACK
    if df is None or len(df) < 30:
        return None, None

    highs, lows = detect_swing_points(df, SWING_STRICTNESS)

    if direction == "BUY":
        if highs and lows:
            last_low_idx, last_low_price = lows[-1]
            future_highs = [h for h in highs if h[0] > last_low_idx]
            if future_highs:
                swing_high_price = max(h[1] for h in future_highs)
                if swing_high_price > last_low_price:
                    return last_low_price, swing_high_price
        recent = df.tail(lookback)
        if len(recent) < 10:
            return None, None
        swing_low_price = float(recent['low'].min())
        swing_high_price = float(recent['high'].max())
        if swing_high_price > swing_low_price:
            return swing_low_price, swing_high_price
        return None, None
    else:
        if highs and lows:
            last_high_idx, last_high_price = highs[-1]
            future_lows = [l for l in lows if l[0] > last_high_idx]
            if future_lows:
                swing_low_price = min(l[1] for l in future_lows)
                if swing_low_price < last_high_price:
                    return swing_low_price, last_high_price
        recent = df.tail(lookback)
        if len(recent) < 10:
            return None, None
        swing_low_price = float(recent['low'].min())
        swing_high_price = float(recent['high'].max())
        if swing_high_price > swing_low_price:
            return swing_low_price, swing_high_price
        return None, None


def in_fib_zone(price, swing_low, swing_high, zone_low, zone_high):
    """Cek apakah harga berada di zona fib."""
    if None in (price, swing_low, swing_high):
        return False
    level_a = fib_retracement(swing_low, swing_high, zone_low)
    level_b = fib_retracement(swing_low, swing_high, zone_high)
    lo, hi = min(level_a, level_b), max(level_a, level_b)
    return lo <= price <= hi


def get_liquidity_target(df, direction, lookback=None):
    """Ambil target likuiditas (high/low N candle)."""
    if lookback is None:
        lookback = 50
    if df is None or len(df) < lookback:
        return None
    recent = df.tail(lookback)
    if direction == "BUY":
        return float(recent['high'].max())
    else:
        return float(recent['low'].min())


def resolve_tp(swing_low, swing_high, direction, entry, sl, df, model):
    """Hitung TP plan (tp1, tp2, tp3) berdasarkan mode dan arah."""
    mode = str(get_model_setting(model, "TP_MODE", CONFIG.get("TP_MODE", "FIB"))).upper()
    use_liq = get_model_setting(model, "USE_TP_AT_LIQUIDITY", USE_TP_AT_LIQUIDITY)

    risk = abs(entry - sl)
    if risk <= 0:
        risk = 1e-9

    if mode == "FIXED_RR":
        rr1 = CONFIG.get("FIXED_RR_TP1", 1.0)
        rr2 = CONFIG.get("FIXED_RR_TP2", 1.5)
        rr3 = CONFIG.get("FIXED_RR_TP3", 2.0)
        if direction == "BUY":
            tp1 = entry + risk * rr1
            tp2 = entry + risk * rr2
            tp3 = entry + risk * rr3
        else:
            tp1 = entry - risk * rr1
            tp2 = entry - risk * rr2
            tp3 = entry - risk * rr3
        return {"tp1": tp1, "tp2": tp2, "tp3": tp3, "mode": "FIXED_RR"}

    if direction == "BUY":
        ext1 = fib_extension(swing_low, swing_high, FIB_TP1_EXT)
        ext2 = fib_extension(swing_low, swing_high, FIB_TP2_EXT)
        ext3 = fib_extension(swing_low, swing_high, FIB_TP3_EXT)
    else:
        ext1 = fib_extension_sell(swing_low, swing_high, FIB_TP1_EXT)
        ext2 = fib_extension_sell(swing_low, swing_high, FIB_TP2_EXT)
        ext3 = fib_extension_sell(swing_low, swing_high, FIB_TP3_EXT)

    if direction == "BUY":
        if ext1 <= entry: ext1 = entry + risk * 1.0
        if ext2 <= ext1: ext2 = entry + risk * 1.5
        if ext3 <= ext2: ext3 = entry + risk * 2.0
    else:
        if ext1 >= entry: ext1 = entry - risk * 1.0
        if ext2 >= ext1: ext2 = entry - risk * 1.5
        if ext3 >= ext2: ext3 = entry - risk * 2.0

    if mode == "LIQUIDITY" and use_liq:
        liq = get_liquidity_target(df, direction)
        if liq is not None:
            if direction == "BUY" and liq > entry:
                ext3 = min(ext3, liq)
            elif direction == "SELL" and liq < entry:
                ext3 = max(ext3, liq)

    return {"tp1": ext1, "tp2": ext2, "tp3": ext3, "mode": mode}


def validate_tp(tp_plan, entry, sl, direction, min_rr=None):
    """Validasi TP dengan soft warning untuk RR tinggi."""
    if min_rr is None:
        min_rr = CONFIG.get("MIN_RR_TP3", 1.2)
    max_rr = CONFIG.get("MAX_RR_TP3", 10.0)
    hard_max_rr = CONFIG.get("HARD_MAX_RR_TP3", 15.0)
    soft_warn = CONFIG.get("RR_SOFT_WARN", True)

    risk = abs(entry - sl)
    if risk <= 0:
        return False, 0.0, tp_plan

    reward = abs(tp_plan["tp3"] - entry)
    rr = reward / risk

    if rr > hard_max_rr:
        return False, rr, tp_plan

    if rr > max_rr and soft_warn:
        return True, rr, tp_plan

    if not CONFIG.get("USE_TP_RR_GUARD", True):
        return True, rr, tp_plan

    if rr >= min_rr:
        return True, rr, tp_plan

    if direction == "BUY":
        adjusted = entry + risk * min_rr
        if adjusted < tp_plan["tp3"]:
            new_plan = dict(tp_plan)
            new_plan["tp3"] = adjusted
            return True, min_rr, new_plan
    else:
        adjusted = entry - risk * min_rr
        if adjusted > tp_plan["tp3"]:
            new_plan = dict(tp_plan)
            new_plan["tp3"] = adjusted
            return True, min_rr, new_plan

    return False, rr, tp_plan


def resolve_fib_sl(swing_low, swing_high, direction, entry, atr_fallback=None):
    """Hitung SL dari FIB retracement 0.786 dengan minimum distance."""
    if not USE_FIB_SL:
        return None
    if None in (swing_low, swing_high):
        return None
    if swing_high <= swing_low:
        return None

    min_sl_dist = float(CONFIG.get("MIN_SL_DISTANCE", 1.5))

    sl_fib = fib_retracement(swing_low, swing_high, 0.786)
    if direction == "BUY":
        sl = sl_fib - SL_BUFFER
        if sl >= entry:
            return None
        if (entry - sl) < min_sl_dist:
            sl = entry - min_sl_dist
        return sl
    else:
        sl = sl_fib + SL_BUFFER
        if sl <= entry:
            return None
        if (sl - entry) < min_sl_dist:
            sl = entry + min_sl_dist
        return sl


def resolve_initial_sl(model_data, entry, atr_raw, digits=2):
    """Hitung SL awal dari FIB atau ATR (fallback)."""
    model_name = model_data.get("model", "")
    direction = model_data["direction"]
    sl_source_pref = get_model_setting(model_name, "SL_SOURCE",
                                       SL_MODEL_MAPPING.get(model_name, "ATR"))
    wants_fib = USE_FIB_SL and sl_source_pref == "FIB"

    if wants_fib:
        fib_sl = resolve_fib_sl(
            model_data.get("swing_low"),
            model_data.get("swing_high"),
            direction,
            entry,
        )
        if fib_sl is not None:
            return round(fib_sl, digits), "FIB"

    sl_pts = calculate_dynamic_sl(atr=atr_raw)
    if direction == "BUY":
        sl = entry - sl_pts
    else:
        sl = entry + sl_pts
    source = "ATR (fallback)" if wants_fib else "ATR"
    return round(sl, digits), source


# ===================== LOT CALCULATION =====================
def _clamp_lot(raw_lot, symbol_info=None):
    """Clamp lot ke batas aman."""
    if symbol_info is None:
        symbol_info = mt5.symbol_info(SYMBOL)
    if symbol_info is None:
        return float(LOT_SIZE)
    broker_min = float(symbol_info.volume_min or 0.01)
    broker_max = float(symbol_info.volume_max or 100.0)
    broker_step = float(symbol_info.volume_step or 0.01)
    hard_cap = float(CONFIG.get("HARD_LOT_CAP", 0.05)) if CONFIG.get("USE_HARD_LOT_CAP", True) else 999.0
    eff_max = min(float(MAX_LOT_SIZE), hard_cap, broker_max)
    eff_min = max(float(MIN_LOT_SIZE), broker_min)
    lot = max(eff_min, min(eff_max, float(raw_lot)))
    if broker_step > 0:
        lot = round(lot / broker_step) * broker_step
    return round(lot, 8)


def calculate_lot(sl_points=None):
    """Hitung lot dari risk % balance (jika dynamic lot aktif)."""
    symbol_info = mt5.symbol_info(SYMBOL)
    if symbol_info is None or not USE_DYNAMIC_LOT:
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
    if tick_size <= 0 or tick_value <= 0:
        return float(LOT_SIZE)
    loss_per_lot = (sl_points / tick_size) * tick_value
    if loss_per_lot <= 0:
        return float(LOT_SIZE)
    lot = risk_money / loss_per_lot
    return max(float(MIN_LOT_SIZE), min(float(MAX_LOT_SIZE), lot))


def lot_from_bonus(bonus_pts):
    """Hitung lot dari bonus points."""
    if not USE_BONUS_SIZING:
        return _clamp_lot(float(LOT_SIZE))
    if bonus_pts <= 3:
        lot = float(BONUS_LOT_TIER_1)
    elif bonus_pts <= 8:
        lot = float(BONUS_LOT_TIER_2)
    else:
        lot = float(BONUS_LOT_TIER_3)
    return _clamp_lot(lot)


def _check_margin_safety(lot, symbol_info=None):
    """Cek apakah margin cukup untuk lot ini."""
    if not CONFIG.get("USE_MARGIN_GUARD", True):
        return True, "guard off"
    try:
        if symbol_info is None:
            symbol_info = mt5.symbol_info(SYMBOL)
        if symbol_info is None:
            return True, "no symbol"
        account = mt5.account_info()
        if account is None:
            return True, "no account"
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None:
            return True, "no tick"
        try:
            margin_needed = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, SYMBOL, lot, tick.ask)
        except Exception:
            margin_needed = None
        if margin_needed is None or margin_needed <= 0:
            return True, "skip"
        free_margin = float(account.margin_free)
        if free_margin <= 0:
            return False, "no free margin"
        usage_pct = (margin_needed / free_margin) * 100.0
        safety_pct = float(CONFIG.get("MARGIN_SAFETY_PERCENT", 30.0))
        if usage_pct > safety_pct:
            return False, f"margin {usage_pct:.1f}% > {safety_pct:.0f}%"
        return True, f"margin {usage_pct:.1f}%"
    except Exception:
        return True, "skip err"


# ===================== SESSION =====================
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
    """Deteksi session aktif saat ini."""
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
    """Cek apakah sedang di session yang enabled."""
    active = detect_sessions()
    if not USE_SESSION_FILTER or not SESSION_CONFIG.get("ENABLED", True):
        return True
    for name in active:
        if SESSION_CONFIG.get(name, {}).get("ENABLED", False):
            return True
    return False


def get_session_status_text():
    """Ambil status session untuk display."""
    active = detect_sessions()
    enabled = [n for n in active if SESSION_CONFIG.get(n, {}).get("ENABLED", False)]
    if not active:
        return SESSION_STATUS, "NO ACTIVE SESSION", False
    if not USE_SESSION_FILTER or not SESSION_CONFIG.get("ENABLED", True):
        return SESSION_STATUS, ", ".join(active), True
    return SESSION_STATUS, ", ".join(active), bool(enabled)


# ===================== DAILY LOSS =====================
def check_daily_loss():
    """Cek daily loss dan disable trading kalau lewat limit."""
    global daily_start_balance, daily_date, trading_disabled_today
    now = datetime.now(WIB).date()
    if now != daily_date:
        daily_date = now
        account = mt5.account_info()
        daily_start_balance = account.balance if account else daily_start_balance
        trading_disabled_today = False
        runtime_message("New trading day. Daily reset.")
        persist_state()
    account = mt5.account_info()
    if account is None:
        return 0.0, 0.0
    daily_pnl = account.balance - daily_start_balance
    daily_loss_percent = (-daily_pnl / daily_start_balance) * 100 if daily_pnl < 0 and daily_start_balance > 0 else 0
    was_disabled = trading_disabled_today
    if daily_loss_percent >= MAX_DAILY_LOSS_PERCENT:
        trading_disabled_today = True
    if trading_disabled_today != was_disabled:
        persist_state()
    return daily_pnl, round(daily_loss_percent, 2)


# ===================== MODEL DETECTORS =====================
def _diag_model(name, reason):
    """Update DIAG_STATE notes untuk model yang gagal."""
    tag_map = {"CONTINUATION": "C", "REVERSAL": "R", "SWEEP": "S"}
    short = tag_map.get(name, name[0])
    note = f"{short}={reason}"
    if note not in DIAG_STATE["notes"]:
        DIAG_STATE["notes"].append(note)


def _check_swing_size(swing_low, swing_high, model_name):
    """Return True kalau swing cukup besar."""
    if swing_low is None or swing_high is None:
        return False
    size = abs(swing_high - swing_low)
    if size < MIN_SWING_SIZE:
        _diag_model(model_name, f"swing-small({size:.1f})")
        return False
    return True


def detect_model_continuation(df_ltf, df_htf, demand_zones, supply_zones, htf_trend):
    """Deteksi model CONTINUATION."""
    if not USE_MODEL_CONTINUATION:
        _diag_model("CONTINUATION", "OFF")
        return None
    if htf_trend not in ("BULLISH", "BEARISH"):
        _diag_model("CONTINUATION", f"HTF={htf_trend}")
        return None
    direction = "BUY" if htf_trend == "BULLISH" else "SELL"
    if direction == "BUY":
        in_poi, zone = price_in_smc_zone(df_ltf['close'].iloc[-1], demand_zones, "DEMAND")
    else:
        in_poi, zone = price_in_smc_zone(df_ltf['close'].iloc[-1], supply_zones, "SUPPLY")
    if not in_poi:
        _diag_model("CONTINUATION", f"no-POI({direction})")
        return None
    ltf_choch = detect_choch(df_ltf, SWING_STRICTNESS) if USE_CHOCH else None
    ltf_rej = detect_rejection_wick(df_ltf) if USE_REJECTION_WICK else None
    confirmed = (
        (direction == "BUY" and (ltf_choch == "BULL_CHoCH" or ltf_rej == "BULL")) or
        (direction == "SELL" and (ltf_choch == "BEAR_CHoCH" or ltf_rej == "BEAR"))
    )
    if not confirmed:
        _diag_model("CONTINUATION", f"no-Confirm(choch={ltf_choch},wick={ltf_rej})")
        return None
    swing_low, swing_high = find_last_swing_for_fib(df_ltf, direction)
    if swing_low is None:
        _diag_model("CONTINUATION", f"no-Swing({direction})")
        return None
    if not _check_swing_size(swing_low, swing_high, "CONTINUATION"):
        return None
    entry_price = df_ltf['close'].iloc[-1]
    zone_lo, zone_hi = FIB_ENTRY_ZONE_CONTINUATION
    fib_ok = in_fib_zone(entry_price, swing_low, swing_high, zone_lo, zone_hi)
    return {
        "model": "CONTINUATION", "direction": direction,
        "swing_low": swing_low, "swing_high": swing_high,
        "fib_zone_ok": fib_ok, "poi_zone": zone,
        "choch": ltf_choch, "rejection": ltf_rej, "sweep": False,
    }


def detect_model_reversal(df_ltf, df_htf, demand_zones, supply_zones):
    """Deteksi model REVERSAL."""
    if not USE_MODEL_REVERSAL:
        _diag_model("REVERSAL", "OFF")
        return None
    sweep_buy = smart_liquidity_sweep(df_ltf, "BUY") if USE_SMART_SWEEP else False
    sweep_sell = smart_liquidity_sweep(df_ltf, "SELL") if USE_SMART_SWEEP else False
    direction = None
    if sweep_buy:
        direction = "BUY"
    elif sweep_sell:
        direction = "SELL"
    if direction is None:
        _diag_model("REVERSAL", "no-Sweep")
        return None
    mss = detect_choch(df_ltf, SWING_STRICTNESS) if USE_CHOCH else None
    if direction == "BUY" and mss != "BULL_CHoCH":
        _diag_model("REVERSAL", f"no-CHoCH({mss})")
        return None
    if direction == "SELL" and mss != "BEAR_CHoCH":
        _diag_model("REVERSAL", f"no-CHoCH({mss})")
        return None
    if direction == "BUY":
        retest, zone = price_in_smc_zone(df_ltf['close'].iloc[-1], demand_zones, "DEMAND")
    else:
        retest, zone = price_in_smc_zone(df_ltf['close'].iloc[-1], supply_zones, "SUPPLY")
    if not retest:
        _diag_model("REVERSAL", f"no-Retest({direction})")
        return None
    swing_low, swing_high = find_last_swing_for_fib(df_ltf, direction)
    if swing_low is None:
        _diag_model("REVERSAL", f"no-Swing({direction})")
        return None
    if not _check_swing_size(swing_low, swing_high, "REVERSAL"):
        return None
    entry_price = df_ltf['close'].iloc[-1]
    zone_lo, zone_hi = FIB_ENTRY_ZONE_REVERSAL
    fib_ok = in_fib_zone(entry_price, swing_low, swing_high, zone_lo, zone_hi)
    return {
        "model": "REVERSAL", "direction": direction,
        "swing_low": swing_low, "swing_high": swing_high,
        "fib_zone_ok": fib_ok, "poi_zone": zone,
        "choch": mss, "sweep": True,
    }


def detect_model_sweep(df_ltf, demand_zones, supply_zones):
    """Deteksi model SWEEP."""
    if not USE_MODEL_SWEEP:
        _diag_model("SWEEP", "OFF")
        return None
    sweep_buy = smart_liquidity_sweep(df_ltf, "BUY") if USE_SMART_SWEEP else False
    sweep_sell = smart_liquidity_sweep(df_ltf, "SELL") if USE_SMART_SWEEP else False
    direction = None
    if sweep_buy:
        direction = "BUY"
    elif sweep_sell:
        direction = "SELL"
    if direction is None:
        _diag_model("SWEEP", "no-Sweep")
        return None
    wick = detect_rejection_wick(df_ltf) if USE_REJECTION_WICK else None
    if direction == "BUY" and wick != "BULL":
        _diag_model("SWEEP", f"no-Wick({wick})")
        return None
    if direction == "SELL" and wick != "BEAR":
        _diag_model("SWEEP", f"no-Wick({wick})")
        return None
    if direction == "BUY":
        in_poi, zone = price_in_smc_zone(df_ltf['close'].iloc[-1], demand_zones, "DEMAND")
    else:
        in_poi, zone = price_in_smc_zone(df_ltf['close'].iloc[-1], supply_zones, "SUPPLY")
    if not in_poi:
        _diag_model("SWEEP", f"no-POI({direction})")
        return None
    swing_low, swing_high = find_last_swing_for_fib(df_ltf, direction)
    if swing_low is None:
        _diag_model("SWEEP", f"no-Swing({direction})")
        return None
    if not _check_swing_size(swing_low, swing_high, "SWEEP"):
        return None
    entry_price = df_ltf['close'].iloc[-1]
    zone_lo, zone_hi = FIB_ENTRY_ZONE_SWEEP
    fib_ok = in_fib_zone(entry_price, swing_low, swing_high, zone_lo, zone_hi)
    return {
        "model": "SWEEP", "direction": direction,
        "swing_low": swing_low, "swing_high": swing_high,
        "fib_zone_ok": fib_ok, "poi_zone": zone,
        "rejection": wick, "sweep": True,
    }


# ===================== BONUS POINTS =====================
def calculate_bonus_points(model_data, df, session_ok, rr_estimate=None):
    """Hitung bonus points untuk sizing kualitas sinyal."""
    if not model_data:
        return 0, []
    pts = 0
    met = []
    model = model_data["model"]

    if session_ok:
        pts += 3
        met.append("KILLZONE")

    if model_data.get("fib_zone_ok"):
        if model == "REVERSAL":
            pts += 3
            met.append("OTE")
        else:
            pts += 2
            met.append("FIB-OTE")

    ob = detect_order_block(df) if USE_ORDER_BLOCK else None
    fvg = detect_fvg(df) if USE_FVG else None
    if ob and fvg and ob == fvg:
        pts += 2
        met.append("OB+FVG")

    if model_data.get("sweep"):
        candle = df.iloc[-1]
        rng = candle['high'] - candle['low']
        wick_ratio = 0
        if rng > 0:
            if model_data["direction"] == "BUY":
                wick_ratio = (min(candle['open'], candle['close']) - candle['low']) / rng
            else:
                wick_ratio = (candle['high'] - max(candle['open'], candle['close'])) / rng
        if wick_ratio >= 0.70:
            pts += 2
            met.append("WICK>70%")

    htf = get_higher_timeframe_trend() if USE_CONFLUENCE_CHECK else "SIDEWAYS"
    if htf == ("BULLISH" if model_data["direction"] == "BUY" else "BEARISH"):
        pts += 3
        met.append("HTF-POI")

    if rr_estimate is not None and rr_estimate >= 3.0:
        pts += 2
        met.append("RR>=3")

    if detect_divergence(df, model_data["direction"]):
        pts += 1
        met.append("DIV")

    return pts, met


# ===================== PARTIAL CLOSE =====================
def register_partial_plan(ticket, tp_plan, orig_volume, model_name):
    """
    Register partial plan berdasarkan LOT:
      - lot < 0.015       → no partial
      - lot 0.015-0.025   → TP1 & TP2
      - lot >= 0.025      → TP1, TP2, TP3
    """
    lot = float(orig_volume)

    if lot < PARTIAL_LOT_THRESHOLD_1:
        tp1_en, tp2_en, tp3_en = False, False, False
    elif lot < PARTIAL_LOT_THRESHOLD_2:
        tp1_en, tp2_en, tp3_en = True, True, False
    else:
        tp1_en, tp2_en, tp3_en = True, True, True

    if not (tp1_en or tp2_en or tp3_en):
        return

    if tp3_en:
        pct1, pct2, pct3 = 50, 30, 20
    elif tp2_en:
        pct1, pct2, pct3 = 50, 50, 0
    else:
        pct1, pct2, pct3 = 0, 0, 0

    PARTIAL_STATE[ticket] = {
        "tp1": tp_plan["tp1"], "tp2": tp_plan["tp2"], "tp3": tp_plan["tp3"],
        "tp1_done": False, "tp2_done": False, "tp3_done": False,
        "tp1_enabled": tp1_en, "tp2_enabled": tp2_en, "tp3_enabled": tp3_en,
        "pct1": pct1, "pct2": pct2, "pct3": pct3,
        "orig_volume": lot, "model": model_name,
    }
    persist_state()

    level_info = []
    if tp1_en: level_info.append(f"TP1({pct1}%)")
    if tp2_en: level_info.append(f"TP2({pct2}%)")
    if tp3_en: level_info.append(f"TP3({pct3}%)")
    runtime_message(f"Partial #{ticket} Lot {lot}: {'/'.join(level_info)}")


def _close_partial(position, close_volume, symbol_info):
    """Close sebagian posisi."""
    try:
        close_volume = max(symbol_info.volume_min,
                           round(close_volume / symbol_info.volume_step) * symbol_info.volume_step)
        close_volume = min(close_volume, position.volume)
        if close_volume < symbol_info.volume_min:
            return False
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None:
            return False
        price = tick.bid if position.type == 0 else tick.ask
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": position.ticket,
            "symbol": SYMBOL,
            "volume": close_volume,
            "type": mt5.ORDER_TYPE_SELL if position.type == 0 else mt5.ORDER_TYPE_BUY,
            "price": price, "deviation": 20, "magic": 777777,
            "comment": "PARTIAL_FIB",
            "type_filling": mt5.ORDER_FILLING_IOC,
            "type_time": mt5.ORDER_TIME_GTC,
        }
        res = mt5.order_send(req)
        return res is not None and res.retcode == mt5.TRADE_RETCODE_DONE
    except Exception:
        log_error(f"_close_partial: {traceback.format_exc()}")
        return False


def manage_partial_close_fib():
    """Proses partial close TP1/TP2 untuk posisi yang punya plan."""
    try:
        positions = mt5.positions_get(symbol=SYMBOL)
        if not positions:
            PARTIAL_STATE.clear()
            persist_state()
            return
        symbol_info = mt5.symbol_info(SYMBOL)
        if symbol_info is None:
            return
        active_tickets = {p.ticket for p in positions}
        for tk in list(PARTIAL_STATE.keys()):
            if tk not in active_tickets:
                PARTIAL_STATE.pop(tk, None)
        persist_state()
        if not PARTIAL_STATE:
            return

        for pos in positions:
            plan = PARTIAL_STATE.get(pos.ticket)
            if not plan:
                continue

            tp1_en = plan.get("tp1_enabled", False)
            tp2_en = plan.get("tp2_enabled", False)
            tp3_en = plan.get("tp3_enabled", False)
            pct1 = plan.get("pct1", 50)
            pct2 = plan.get("pct2", 30)

            if not (tp1_en or tp2_en or tp3_en):
                continue

            tick = mt5.symbol_info_tick(SYMBOL)
            if tick is None:
                continue
            current = tick.bid if pos.type == 0 else tick.ask

            # === TP1 ===
            if tp1_en and not plan.get("tp1_done", False):
                hit = (pos.type == 0 and current >= plan["tp1"]) or \
                      (pos.type == 1 and current <= plan["tp1"])
                if hit:
                    vol = plan["orig_volume"] * (pct1 / 100.0)
                    if _close_partial(pos, vol, symbol_info):
                        plan["tp1_done"] = True
                        persist_state()
                        runtime_message(f"TP1 hit #{pos.ticket} @ {plan['tp1']:.2f} ({pct1}%)")
                    continue

            # === TP2 ===
            if tp2_en and plan.get("tp1_done", False) and not plan.get("tp2_done", False):
                hit = (pos.type == 0 and current >= plan["tp2"]) or \
                      (pos.type == 1 and current <= plan["tp2"])
                if hit:
                    vol = plan["orig_volume"] * (pct2 / 100.0)
                    if _close_partial(pos, vol, symbol_info):
                        plan["tp2_done"] = True
                        persist_state()
                        runtime_message(f"TP2 hit #{pos.ticket} @ {plan['tp2']:.2f} ({pct2}%)")
                    continue

            # TP3 = pos.tp broker (otomatis) - hanya track status
            if tp3_en and plan.get("tp2_done", False) and not plan.get("tp3_done", False):
                hit = (pos.type == 0 and current >= plan["tp3"]) or \
                      (pos.type == 1 and current <= plan["tp3"])
                if hit:
                    plan["tp3_done"] = True
                    persist_state()

    except Exception:
        log_error(f"manage_partial: {traceback.format_exc()}")


# ===================== TRAILING SL =====================
def manage_trailing_sl():
    """Trailing SL berdasarkan pergerakan harga (ATR-based atau fixed $)."""
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions:
        return
    symbol_info = mt5.symbol_info(SYMBOL)
    if symbol_info is None:
        return
    digits = symbol_info.digits

    for pos in positions:
        meta = POSITION_META.get(pos.ticket, {})
        model_name = meta.get("model", "")
        if not model_name:
            continue

        use_trail = get_model_setting(model_name, "USE_TRAILING_SL", USE_TRAILING_SL)
        if not use_trail:
            continue

        use_atr_trail = get_model_setting(model_name, "USE_ATR_TRAIL_START", USE_ATR_TRAIL_START)
        trail_pct = float(get_model_setting(model_name, "TRAIL_START_PERCENT", TRAIL_START_PERCENT))
        secure_pct = float(get_model_setting(model_name, "TRAIL_SECURE_PERCENT", TRAIL_SECURE_PERCENT))
        trail_profit = float(get_model_setting(model_name, "TRAIL_START_PROFIT", TRAIL_START_PROFIT))

        if use_atr_trail:
            atr_now = get_atr_current()
            if atr_now is None or atr_now <= 0:
                continue
            trigger_price_move = atr_now * trail_pct
        else:
            lot = float(pos.volume or 0.01)
            if lot <= 0:
                continue
            trigger_price_move = trail_profit / (lot * 100.0)

        if pos.type == 0:
            current_move = pos.price_current - pos.price_open
        else:
            current_move = pos.price_open - pos.price_current

        if current_move < trigger_price_move:
            continue

        secure_move = current_move * (secure_pct / 100.0)
        if secure_move <= 0:
            continue

        if pos.type == 0:
            new_sl = round(pos.price_open + secure_move, digits)
            old_sl = pos.sl if pos.sl and pos.sl > 0 else -1e9
            if new_sl > old_sl and new_sl < pos.price_current:
                result = mt5.order_send({
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "sl": new_sl,
                    "tp": pos.tp,
                })
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    runtime_message(f"TRAIL {model_name} BUY #{pos.ticket} SL→{new_sl}")
        else:
            new_sl = round(pos.price_open - secure_move, digits)
            old_sl = pos.sl if pos.sl and pos.sl > 0 else 1e9
            if new_sl < old_sl and new_sl > pos.price_current:
                result = mt5.order_send({
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "sl": new_sl,
                    "tp": pos.tp,
                })
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    runtime_message(f"TRAIL {model_name} SELL #{pos.ticket} SL→{new_sl}")


# ===================== BREAK EVEN =====================
def manage_break_even():
    """Break Even: pindah SL ke entry saat profit capai N×R."""
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions:
        return
    symbol_info = mt5.symbol_info(SYMBOL)
    digits = symbol_info.digits if symbol_info else 2

    for pos in positions:
        meta = POSITION_META.get(pos.ticket, {})
        model_name = meta.get("model", "")
        if not model_name:
            continue

        use_be = get_model_setting(model_name, "USE_BREAK_EVEN", USE_BREAK_EVEN)
        if not use_be:
            continue

        be_r = float(get_model_setting(model_name, "BE_TRIGGER_R", BE_TRIGGER_R))

        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None:
            continue
        price = tick.bid if pos.type == 0 else tick.ask

        if pos.sl and pos.sl > 0:
            risk = abs(pos.price_open - pos.sl)
        else:
            risk = calculate_dynamic_sl()
        if risk <= 0:
            continue

        trigger = (risk * be_r) if USE_BE_R_BASED else BE_TRIGGER

        if pos.type == 0:
            move = price - pos.price_open
        else:
            move = pos.price_open - price

        if move < trigger:
            continue

        if pos.type == 0:
            new_sl = round(pos.price_open + R1_BE_BUFFER, digits)
            old_sl = pos.sl if pos.sl and pos.sl > 0 else -1e9
            if new_sl > old_sl and new_sl < price:
                result = mt5.order_send({
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "sl": new_sl,
                    "tp": pos.tp,
                })
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    runtime_message(f"BE {model_name} BUY #{pos.ticket} SL→{new_sl}")
        else:
            new_sl = round(pos.price_open - R1_BE_BUFFER, digits)
            old_sl = pos.sl if pos.sl and pos.sl > 0 else 1e9
            if new_sl < old_sl and new_sl > price:
                result = mt5.order_send({
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "sl": new_sl,
                    "tp": pos.tp,
                })
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    runtime_message(f"BE {model_name} SELL #{pos.ticket} SL→{new_sl}")


# ===================== MANUAL RECOVERY =====================
def _recover_manual_position(pos, symbol_info, atr_raw, digits):
    """Hitung SL/TP untuk posisi manual."""
    direction = "BUY" if pos.type == 0 else "SELL"
    entry = float(pos.price_open)
    mode = str(MANUAL_PROFILE.get("SL_TP_MODE", "HYBRID")).upper()
    min_sl_price = float(MANUAL_PROFILE.get("MIN_SL_PRICE", 3.0))
    max_sl_price = float(MANUAL_PROFILE.get("MAX_SL_PRICE", 20.0))

    if mode in ("FIB", "HYBRID") and USE_FIB_SL:
        try:
            df_entry = get_closed_data(TIMEFRAME_ENTRY, bars=100)
            swing_low, swing_high = find_last_swing_for_fib(df_entry, direction)
            if swing_low is not None and swing_high is not None:
                fib_sl = resolve_fib_sl(swing_low, swing_high, direction, entry)
                if fib_sl is not None:
                    sl_dist = abs(entry - fib_sl)
                    if min_sl_price <= sl_dist <= max_sl_price:
                        ext_level = float(MANUAL_PROFILE.get("FIB_TP_EXT", 1.618))
                        if direction == "BUY":
                            tp_price = fib_extension(swing_low, swing_high, ext_level)
                        else:
                            tp_price = fib_extension_sell(swing_low, swing_high, ext_level)
                        valid = (
                            (direction == "BUY" and fib_sl < entry and tp_price > entry) or
                            (direction == "SELL" and fib_sl > entry and tp_price < entry)
                        )
                        if valid:
                            return True, "FIB", round(fib_sl, digits), round(tp_price, digits)
        except Exception as e:
            runtime_message(f"Manual FIB calc: {e}")

    if mode in ("ATR", "HYBRID"):
        sl_price_dist = calculate_dynamic_sl(atr=atr_raw)
        sl_price_dist = max(min_sl_price, min(max_sl_price, sl_price_dist))
        rr = float(MANUAL_PROFILE.get("RR", 1.5))
        tp_dist = sl_price_dist * rr
        if direction == "BUY":
            sl_price = entry - sl_price_dist
            tp_price = entry + tp_dist
        else:
            sl_price = entry + sl_price_dist
            tp_price = entry - tp_dist
        return True, "ATR", round(sl_price, digits), round(tp_price, digits)

    return False, "NONE", 0.0, 0.0


def recover_manual_entries():
    """Pasang SL/TP untuk posisi manual (magic != 777777)."""
    if not CONFIG.get("USE_MANUAL_RECOVERY", True):
        return
    try:
        positions = mt5.positions_get(symbol=SYMBOL)
        if not positions:
            return
        symbol_info = mt5.symbol_info(SYMBOL)
        if symbol_info is None:
            return
        digits = symbol_info.digits
        df_entry = get_closed_data(TIMEFRAME_ENTRY, bars=100)
        atr_raw = atr_value(df_entry)
        override = bool(MANUAL_PROFILE.get("OVERRIDE_EXISTING", False))
        for pos in positions:
            if pos.magic == 777777:
                continue
            if pos.ticket in POSITION_META:
                continue
            if not override and (pos.sl != 0 or pos.tp != 0):
                continue
            ok, method, sl_price, tp_price = _recover_manual_position(pos, symbol_info, atr_raw, digits)
            if not ok:
                continue
            new_sl = sl_price if (override or pos.sl == 0) else pos.sl
            new_tp = tp_price if (override or pos.tp == 0) else pos.tp
            result = mt5.order_send({
                "action": mt5.TRADE_ACTION_SLTP,
                "position": pos.ticket,
                "sl": new_sl,
                "tp": new_tp,
            })
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                runtime_message(f"Manual #{pos.ticket} SL:{new_sl} TP:{new_tp} [{method}]")
                POSITION_META[pos.ticket] = {"model": "MANUAL", "sl_source": method, "source": "manual_recovery"}
                persist_state()
    except Exception:
        log_error(f"recover_manual_entries: {traceback.format_exc()}")


def rebuild_partial_plans():
    """Rebuild PARTIAL_STATE untuk posisi lama tanpa plan (setelah restart)."""
    try:
        positions = mt5.positions_get(symbol=SYMBOL)
        if not positions:
            return
        for pos in positions:
            if pos.ticket in PARTIAL_STATE:
                continue
            meta = POSITION_META.get(pos.ticket, {})
            model_name = meta.get("model", "")
            if not model_name:
                continue
            tp3 = pos.tp
            if not tp3 or tp3 <= 0:
                continue

            entry = pos.price_open
            if pos.type == 0:
                dist = tp3 - entry
                tp1 = entry + dist * 0.5
                tp2 = entry + dist * 0.75
            else:
                dist = entry - tp3
                tp1 = entry - dist * 0.5
                tp2 = entry - dist * 0.75

            register_partial_plan(pos.ticket, {
                "tp1": tp1, "tp2": tp2, "tp3": tp3
            }, pos.volume, model_name)

            runtime_message(f"Rebuild plan #{pos.ticket} lot={pos.volume}")
    except Exception:
        log_error(f"rebuild_partial_plans: {traceback.format_exc()}")


# ===================== ORDER EXECUTION =====================
def open_trade_model(model_data, bonus_pts, symbol_info=None):
    """Buka posisi berdasarkan model data."""
    try:
        positions = mt5.positions_get(symbol=SYMBOL)
        if MAX_OPEN_POSITIONS > 0 and positions and len(positions) >= MAX_OPEN_POSITIONS:
            runtime_message(f"Max positions ({MAX_OPEN_POSITIONS})")
            return
        symbol_info = symbol_info or mt5.symbol_info(SYMBOL)
        if symbol_info is None:
            runtime_message("Symbol not found")
            return
        if not symbol_info.visible:
            mt5.symbol_select(SYMBOL, True)

        direction = model_data["direction"]
        swing_low = model_data["swing_low"]
        swing_high = model_data["swing_high"]
        model_name = model_data["model"]

        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None:
            runtime_message("No tick")
            return
        digits = symbol_info.digits
        entry = tick.ask if direction == "BUY" else tick.bid

        df_entry = get_closed_data(TIMEFRAME_ENTRY)
        atr_raw = atr_value(df_entry)
        sl, sl_source = resolve_initial_sl(model_data, entry, atr_raw, digits=digits)
        sl_distance = abs(entry - sl)
        if sl_distance <= 0:
            runtime_message("SL=0 skip")
            return

        use_tp = get_model_setting(model_name, "USE_TAKE_PROFIT", USE_TAKE_PROFIT)
        tp_plan = resolve_tp(swing_low, swing_high, direction, entry, sl, df_entry, model_name)
        tp_valid, rr_est, tp_plan = validate_tp(tp_plan, entry, sl, direction)
        if not tp_valid:
            if rr_est > HARD_MAX_RR_TP3:
                runtime_message(f"Skip RR too high 1:{rr_est:.1f}")
            else:
                runtime_message(f"Skip RR < min (actual {rr_est:.2f})")
            return
        tp3 = tp_plan["tp3"]

        # Hitung lot
        if USE_DYNAMIC_LOT:
            lot = _clamp_lot(calculate_lot(sl_distance), symbol_info)
            lot_source = "DYNAMIC"
        elif USE_BONUS_SIZING:
            lot = lot_from_bonus(bonus_pts)
            lot_source = f"BONUS({bonus_pts})"
        else:
            lot = _clamp_lot(float(LOT_SIZE), symbol_info)
            lot_source = "FIXED"

        margin_ok, margin_reason = _check_margin_safety(lot, symbol_info)
        if not margin_ok:
            runtime_message(f"Skip {margin_reason}")
            return

        entry = round(entry, digits)
        sl = round(sl, digits)
        tp3 = round(tp3, digits)

        if direction == "BUY":
            if sl >= entry:
                runtime_message(f"BAD SL: BUY SL{sl}>=E{entry}")
                return
            if use_tp and tp3 <= entry:
                runtime_message(f"BAD TP: BUY TP{tp3}<=E{entry}")
                return
        else:
            if sl <= entry:
                runtime_message(f"BAD SL: SELL SL{sl}<=E{entry}")
                return
            if use_tp and tp3 >= entry:
                runtime_message(f"BAD TP: SELL TP{tp3}>=E{entry}")
                return

        tp_broker = tp3 if use_tp else 0.0
        tp_str = f"TP:{tp3} ({tp_plan['mode']})" if use_tp else "TP:OFF"
        warn_rr = f" WARN-RR1:{rr_est:.1f}" if rr_est > MAX_RR_TP3 else ""

        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        filling_modes = [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN]
        last_retcode = None
        last_comment = None

        for filling in filling_modes:
            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": SYMBOL, "volume": lot, "type": order_type,
                "price": entry, "sl": sl, "tp": tp_broker,
                "deviation": 20, "magic": 777777,
                "type_filling": filling, "type_time": mt5.ORDER_TIME_GTC,
                "comment": f"Wfx_{model_name}",
            }
            result = mt5.order_send(req)
            if result is None:
                last_retcode = "None"
                last_comment = mt5.last_error()
                continue
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                runtime_message(f"OK {model_name} {direction} @{entry} SL:{sl} {tp_str} Lot:{lot} {warn_rr}")
                time.sleep(0.5)
                poss = mt5.positions_get(symbol=SYMBOL)
                if poss:
                    latest = max(poss, key=lambda p: p.time)
                    register_partial_plan(latest.ticket, tp_plan, lot, model_name)
                    POSITION_META[latest.ticket] = {
                        "model": model_name,
                        "sl_source": sl_source,
                        "lot_source": lot_source,
                    }
                    persist_state()
                return
            last_retcode = result.retcode
            last_comment = result.comment

        runtime_message(f"ALL FAIL rc={last_retcode} {last_comment} | {direction} E{entry} SL{sl} TP{tp3}")
    except Exception:
        log_error(f"open_trade_model: {traceback.format_exc()}")


def update_existing_positions_sl():
    """Update SL untuk posisi yang belum punya SL (jika fitur aktif)."""
    if not USE_ATR_SL_EXISTING or USE_FIB_SL:
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
                new_sl = round(pos.price_open - atr_sl_points, digits)
                if new_sl < pos.price_open:
                    result = mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "sl": new_sl, "tp": pos.tp})
                    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                        runtime_message(f"ATR SL BUY #{pos.ticket}")
            else:
                new_sl = round(pos.price_open + atr_sl_points, digits)
                if new_sl > pos.price_open:
                    result = mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "sl": new_sl, "tp": pos.tp})
                    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                        runtime_message(f"ATR SL SELL #{pos.ticket}")


# ===================== STATS =====================
def _parse_model_from_comment(comment):
    if not comment:
        return "UNKNOWN"
    c = comment.upper()
    for tag in ("CONTINUATION", "REVERSAL", "SWEEP"):
        if tag in c:
            return tag
    if "MANUAL" in c:
        return "MANUAL"
    return "UNKNOWN"


def fetch_trade_history(lookback_days=None, magic=None):
    """Ambil history trades dari MT5."""
    if lookback_days is None:
        lookback_days = int(CONFIG.get("STATS_LOOKBACK_DAYS", 7))
    if magic is None:
        magic = int(CONFIG.get("STATS_MAGIC", 777777))
    try:
        date_from = datetime.now() - timedelta(days=lookback_days)
        date_to = datetime.now() + timedelta(days=1)
        deals = mt5.history_deals_get(date_from, date_to)
        if deals is None or len(deals) == 0:
            return []
        positions_map = {}
        for d in deals:
            if d.magic != magic:
                continue
            if d.symbol != SYMBOL:
                continue
            pid = d.position_id
            if pid not in positions_map:
                positions_map[pid] = {"profit": 0.0, "volume": 0.0,
                                      "time_open": d.time, "time_close": d.time,
                                      "comment": "", "direction": None}
            positions_map[pid]["profit"] += float(d.profit) + float(d.swap) + float(d.commission)
            if d.entry == 0:
                positions_map[pid]["volume"] = float(d.volume)
                positions_map[pid]["time_open"] = d.time
                positions_map[pid]["comment"] = d.comment
                positions_map[pid]["direction"] = "BUY" if d.type == 0 else "SELL"
            if d.entry == 1:
                positions_map[pid]["time_close"] = d.time
        result = []
        for pid, info in positions_map.items():
            if info["direction"] is None or info["volume"] == 0:
                continue
            model = _parse_model_from_comment(info["comment"])
            result.append({
                "ticket": pid, "model": model, "direction": info["direction"],
                "profit": info["profit"], "volume": info["volume"],
                "time_open": info["time_open"], "time_close": info["time_close"],
            })
        return result
    except Exception:
        log_error(f"fetch_history: {traceback.format_exc()}")
        return []


def compute_stats(trades):
    """Hitung statistik dari list trades."""
    stats = {"total": len(trades), "wins": 0, "losses": 0, "be": 0,
             "profit_total": 0.0, "profit_wins": 0.0, "profit_losses": 0.0,
             "winrate": 0.0, "avg_win": 0.0, "avg_loss": 0.0, "profit_factor": 0.0}
    for t in trades:
        p = t["profit"]
        stats["profit_total"] += p
        if p > 0.01:
            stats["wins"] += 1
            stats["profit_wins"] += p
        elif p < -0.01:
            stats["losses"] += 1
            stats["profit_losses"] += abs(p)
        else:
            stats["be"] += 1
    if stats["total"] > 0:
        stats["winrate"] = (stats["wins"] / stats["total"]) * 100
    if stats["wins"] > 0:
        stats["avg_win"] = stats["profit_wins"] / stats["wins"]
    if stats["losses"] > 0:
        stats["avg_loss"] = stats["profit_losses"] / stats["losses"]
    if stats["profit_losses"] > 0:
        stats["profit_factor"] = stats["profit_wins"] / stats["profit_losses"]
    elif stats["profit_wins"] > 0:
        stats["profit_factor"] = 999.0
    return stats


def stats_per_model(trades):
    """Group stats by model."""
    by_model = {}
    for t in trades:
        m = t["model"]
        by_model.setdefault(m, []).append(t)
    return {m: compute_stats(ts) for m, ts in by_model.items()}


STATS_CACHE = {"trades": [], "global": {}, "per_model": {}, "last_refresh": 0}
STATS_REFRESH_INTERVAL = 30


def refresh_stats(force=False):
    """Refresh stats cache."""
    now = time.time()
    if not force and (now - STATS_CACHE["last_refresh"]) < STATS_REFRESH_INTERVAL:
        return
    try:
        trades = fetch_trade_history()
        STATS_CACHE["trades"] = trades
        STATS_CACHE["global"] = compute_stats(trades)
        STATS_CACHE["per_model"] = stats_per_model(trades)
        STATS_CACHE["last_refresh"] = now
    except Exception:
        log_error(f"refresh_stats: {traceback.format_exc()}")


# ===================== UI HELPERS =====================
def rich_status(value, on_color="green", off_color="red"):
    return Text("ON", style=on_color) if value else Text("OFF", style=off_color)


def rich_direction(value):
    if value in ("BULLISH", "BUY"):
        return Text(str(value), style="green")
    if value in ("BEARISH", "SELL"):
        return Text(str(value), style="red")
    return Text(str(value), style="yellow")


def _style_pnl(value):
    return "green" if value > 0 else ("red" if value < 0 else "white")


def _yes_no(value, color_on="green", color_off="dim"):
    return Text("Y", style=color_on) if value else Text("N", style=color_off)


def render_stats_panel():
    """Panel STATS."""
    g = STATS_CACHE["global"]
    per = STATS_CACHE["per_model"]
    tbl = Table.grid(expand=True, padding=(0, 1))
    tbl.add_column(style="cyan", no_wrap=True)
    tbl.add_column(ratio=1)
    if g.get("total", 0) == 0:
        tbl.add_row("Stats", Text(f"No trades ({CONFIG.get('STATS_LOOKBACK_DAYS', 7)}d)", style="dim"))
        return tbl
    tbl.add_row("Total", Text(f"{g['total']} trades", style="bold white"))
    wr_style = "green" if g["winrate"] >= 50 else ("yellow" if g["winrate"] >= 40 else "red")
    tbl.add_row("WinRate", Text(f"{g['winrate']:.1f}%  ({g['wins']}W / {g['losses']}L / {g['be']}BE)", style=wr_style))
    tbl.add_row("Total P/L", Text(f"${g['profit_total']:.2f}", style=_style_pnl(g["profit_total"])))
    pf = g["profit_factor"]
    pf_style = "green" if pf >= 1.5 else ("yellow" if pf >= 1.0 else "red")
    pf_txt = "inf" if pf >= 999 else f"{pf:.2f}"
    tbl.add_row("PF", Text(pf_txt, style=pf_style))
    if g["wins"] > 0:
        tbl.add_row("Avg Win", Text(f"${g['avg_win']:.2f}", style="green"))
    if g["losses"] > 0:
        tbl.add_row("Avg Loss", Text(f"${g['avg_loss']:.2f}", style="red"))
    tbl.add_row("", Text("-" * 20, style="dim"))
    for model in ("CONTINUATION", "REVERSAL", "SWEEP", "MANUAL"):
        if model in per:
            s = per[model]
            style = "green" if s["profit_total"] >= 0 else "red"
            wr_s = "green" if s["winrate"] >= 50 else "yellow"
            line = Text()
            line.append(f"{model[:4]} ", style="bold cyan")
            line.append(f"{s['total']}t ", style="white")
            line.append(f"{s['winrate']:.0f}% ", style=wr_s)
            line.append(f"${s['profit_total']:.1f}", style=style)
            tbl.add_row("", line)
        else:
            tbl.add_row("", Text(f"{model[:4]} - no trades", style="dim"))
    return tbl


best_model_global = {}


def render_profile_preview():
    """Panel MODEL PROFILE preview."""
    tbl = Table.grid(expand=True, padding=(0, 1))
    tbl.add_column(style="cyan", no_wrap=True)
    for _ in ("CONT", "REVE", "SWEE", "MANU"):
        tbl.add_column(ratio=1, no_wrap=True, justify="center")
    if not USE_MODEL_PROFILES:
        tbl.add_row("Mode", Text("MANUAL", style="yellow"), "", "", "")
        return tbl

    def _col_header(label, m):
        is_act = (best_model_global.get("model") == m) or \
                 (m == "MANUAL" and best_model_global.get("model") == "MANUAL")
        t = Text()
        t.append(label, style="bold yellow" if is_act else "bold cyan")
        if is_act:
            t.append(" <", style="bold yellow")
        return t

    tbl.add_row("", _col_header("CONT", "CONTINUATION"), _col_header("REVE", "REVERSAL"),
                _col_header("SWEE", "SWEEP"), _col_header("MANU", "MANUAL"))

    def _row(label, key, fmt=None):
        cells = []
        for m in ("CONTINUATION", "REVERSAL", "SWEEP", "MANUAL"):
            v = get_model_setting(m, key, None)
            if v is None:
                cells.append(Text("-", style="dim"))
            elif fmt == "bool":
                cells.append(_yes_no(bool(v)))
            elif fmt == "pct":
                try:
                    cells.append(Text(f"{int(float(v)*100)}%", style="cyan"))
                except (ValueError, TypeError):
                    cells.append(Text(str(v)))
            elif fmt == "pct_int":
                cells.append(Text(f"{v}%", style="cyan"))
            else:
                cells.append(Text(str(v), style="white"))
        tbl.add_row(Text(label, style="dim"), *cells)

    _row("TP Mode", "TP_MODE")
    _row("SL Source", "SL_SOURCE")
    _row("FakeBrk", "USE_FAKE_BREAK_FILTER", "bool")
    _row("BE", "USE_BREAK_EVEN", "bool")
    _row("BE R", "BE_TRIGGER_R")
    _row("Trailing", "USE_TRAILING_SL", "bool")
    _row("TrailMode", "USE_ATR_TRAIL_START", "bool")
    _row("Trail%", "TRAIL_START_PERCENT", "pct")
    _row("Secure%", "TRAIL_SECURE_PERCENT", "pct_int")
    return tbl


def render_diagnostic_panel():
    """Panel DIAGNOSTIC — kenapa model gagal."""
    tbl = Table.grid(expand=True, padding=(0, 1))
    tbl.add_column(style="cyan", no_wrap=True)
    tbl.add_column(ratio=1)
    gate_ok = lambda b: Text("OK" if b else "X", style="green" if b else "red")
    tbl.add_row("Swing BUY", gate_ok(DIAG_STATE["swing_buy"]))
    tbl.add_row("Swing SELL", gate_ok(DIAG_STATE["swing_sell"]))
    tbl.add_row("Demand Zones", Text(f"{DIAG_STATE['demand_zones']}", style="cyan" if DIAG_STATE['demand_zones'] > 0 else "red"))
    tbl.add_row("Supply Zones", Text(f"{DIAG_STATE['supply_zones']}", style="cyan" if DIAG_STATE['supply_zones'] > 0 else "red"))
    htf = DIAG_STATE["htf_trend"]
    tbl.add_row("HTF Trend", Text(htf, style="green" if htf in ("BULLISH", "BEARISH") else "red"))
    choch = DIAG_STATE["choch"] or "-"
    tbl.add_row("CHoCH", Text(choch, style="green" if choch != "-" else "dim"))
    wick = DIAG_STATE["rej_wick"] or "-"
    tbl.add_row("RejWick", Text(wick, style="green" if wick != "-" else "dim"))
    tbl.add_row("Sweep BUY", gate_ok(DIAG_STATE["sweep_buy"]))
    tbl.add_row("Sweep SELL", gate_ok(DIAG_STATE["sweep_sell"]))
    tbl.add_row("In Demand", gate_ok(DIAG_STATE["in_demand"]))
    tbl.add_row("In Supply", gate_ok(DIAG_STATE["in_supply"]))
    tbl.add_row("", Text("-" * 20, style="dim"))
    notes_txt = " | ".join(DIAG_STATE["notes"][:6]) if DIAG_STATE["notes"] else "(all OK)"
    tbl.add_row("Notes", Text(notes_txt, style="yellow", overflow="fold"))
    return tbl


def render_model_scores_panel():
    """Panel MODEL SCORES — lengkap per model."""
    tbl = Table.grid(expand=True, padding=(0, 1))
    tbl.add_column(style="cyan", no_wrap=True)
    tbl.add_column(ratio=1, justify="center")
    tbl.add_column(ratio=1, justify="center")
    tbl.add_column(ratio=1, justify="center")

    def _header_col(m):
        is_active = best_model_global.get("model") == m
        t = Text()
        t.append(m[:4], style="bold yellow" if is_active else "bold cyan")
        if is_active:
            t.append(" <", style="bold yellow")
        return t

    tbl.add_row("", _header_col("CONTINUATION"), _header_col("REVERSAL"), _header_col("SWEEP"))

    row_bonus = [Text("Bonus", style="dim")]
    row_rr = [Text("RR", style="dim")]
    row_fib = [Text("Fib", style="dim")]
    row_dir = [Text("Dir", style="dim")]
    row_valid = [Text("Valid", style="dim")]
    row_slsrc = [Text("SL Src", style="dim")]
    row_tpmod = [Text("TP Mod", style="dim")]

    for m in ("CONTINUATION", "REVERSAL", "SWEEP"):
        s = MODEL_SCORES.get(m, {})
        bonus = s.get("bonus", 0)
        bonus_style = "bold green" if bonus >= 9 else ("yellow" if bonus >= 4 else "white")
        row_bonus.append(Text(f"{bonus} pts", style=bonus_style))
        rr = s.get("rr", 0.0)
        if rr > HARD_MAX_RR_TP3:
            rr_style = "red"
        elif rr > MAX_RR_TP3:
            rr_style = "yellow"
        elif rr >= 2.0:
            rr_style = "green"
        elif rr >= 1.2:
            rr_style = "cyan"
        else:
            rr_style = "dim"
        row_rr.append(Text(f"1:{rr:.1f}", style=rr_style))
        fib_ok = s.get("fib_ok", False)
        row_fib.append(Text("Y" if fib_ok else "N", style="green" if fib_ok else "red"))
        d = s.get("dir", "-")
        d_style = "green" if d == "BUY" else ("red" if d == "SELL" else "dim")
        row_dir.append(Text(d, style=d_style))
        valid = s.get("valid", False)
        row_valid.append(Text("Y" if valid else "N", style="green" if valid else "red"))

        # SL Source per model
        sl_src = get_model_setting(m, "SL_SOURCE", SL_MODEL_MAPPING.get(m, "ATR"))
        sl_src_style = "green" if sl_src == "FIB" else "yellow"
        row_slsrc.append(Text(str(sl_src), style=sl_src_style))

        # TP Mode per model
        tp_mod = get_model_setting(m, "TP_MODE", CONFIG.get("TP_MODE", "FIB"))
        tp_mod_style = "magenta" if tp_mod == "FIB" else ("cyan" if tp_mod == "LIQUIDITY" else "white")
        row_tpmod.append(Text(str(tp_mod), style=tp_mod_style))

    tbl.add_row(*row_bonus)
    tbl.add_row(*row_rr)
    tbl.add_row(*row_fib)
    tbl.add_row(*row_dir)
    tbl.add_row(*row_valid)
    tbl.add_row(*row_slsrc)
    tbl.add_row(*row_tpmod)

    for m in ("CONTINUATION", "REVERSAL", "SWEEP"):
        s = MODEL_SCORES.get(m, {})
        if s.get("met"):
            tags = ", ".join(s["met"][:4])
            is_active = best_model_global.get("model") == m
            tbl.add_row(Text(f"{m[:4]} tags", style="bold yellow" if is_active else "dim"),
                        Text(tags, style="green", overflow="fold"), "", "")
    return tbl


def render_rich_dashboard(*, account, positions, bid, ask, price_direction,
                          current_sl_points, current_session, session_trade_allowed,
                          trend, htf_trend, current_bias,
                          atr_val, atr_ok, buy_ready, sell_ready, buy_score, sell_score,
                          choch, daily_pnl, daily_loss_percent, trading_disabled_today,
                          is_locked, locked_signal, locked_buy_score, locked_sell_score,
                          active_model, active_fib_ok, best_model, fakeout):
    """Render seluruh dashboard v4.8 (top 2 kolom + session lengkap)."""
    global best_model_global
    best_model_global = best_model or {}

    now = datetime.now(WIB).strftime("%H:%M:%S WIB")
    trade_txt = Text("ON", style="bold green") if USE_AUTO_TRADE else Text("OFF", style="bold red")
    session_txt = Text(current_session, style="bold green" if session_trade_allowed else "bold yellow")

    header = Table.grid(expand=True)
    header.add_column(ratio=1)
    header.add_column(justify="center", ratio=1)
    header.add_column(justify="right", ratio=1)
    title = Text("WEENfx PRO - SMC + FIB (v4.8)", style="bold cyan")
    symbol = Text(SYMBOL, style="bold white")
    right = Text()
    right.append(now, style="white")
    right.append("  TRADE ", style="dim")
    right.append(trade_txt)
    header.add_row(title, symbol, right)

    # ===== PRICE BAR =====
    price = Text()
    price.append("PRICE ", style="bold cyan")
    if bid is not None:
        pc = "green" if price_direction == "UP" else "red" if price_direction == "DN" else "yellow"
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
    price.append("ALLOWED" if session_trade_allowed else "BLOCKED",
                 style="bold green" if session_trade_allowed else "bold red")

    # ===== MARKET PANEL =====
    market = Table.grid(expand=True, padding=(0, 1))
    market.add_column(style="cyan", no_wrap=True)
    market.add_column(ratio=1)
    market.add_row("Bias", rich_direction(current_bias))
    market.add_row("Trend", rich_direction(trend))
    market.add_row("HTF", rich_direction(htf_trend) if USE_CONFLUENCE_CHECK else Text("OFF", style="dim"))
    market.add_row("ATR", Text(f"{atr_val:.2f}  {'OK' if atr_ok else 'LOW'}", style="green" if atr_ok else "red"))
    market.add_row("Session", session_txt)
    market.add_row("Trading", Text("ALLOWED" if session_trade_allowed else "BLOCKED",
                                   style="bold green" if session_trade_allowed else "bold red"))

    # ===== SIGNAL PANEL =====
    signal = Table.grid(expand=True, padding=(0, 1))
    signal.add_column(style="cyan", no_wrap=True)
    signal.add_column(ratio=1)
    if is_locked and locked_signal:
        signal.add_row("STATUS", Text("LOCKED", style="bold yellow"))
        if locked_signal == "BUY":
            signal.add_row("LOCKED", Text(f"BUY bonus {locked_buy_score}", style="bold green"))
        else:
            signal.add_row("LOCKED", Text(f"SELL bonus {locked_sell_score}", style="bold red"))
    else:
        signal.add_row("STATUS", Text("ANALYZING", style="cyan"))
    signal.add_row("BUY", Text(f"{'Y' if buy_ready else 'N'} bonus {buy_score}",
                                style="bold green" if buy_ready else "yellow"))
    signal.add_row("SELL", Text(f"{'Y' if sell_ready else 'N'} bonus {sell_score}",
                                 style="bold red" if sell_ready else "yellow"))
    signal.add_row("Tier", Text(f"<=3->{BONUS_LOT_TIER_1} 4-8->{BONUS_LOT_TIER_2} 9+->{BONUS_LOT_TIER_3}",
                                 style="dim"))
    signal.add_row("Profiles", Text("AUTO" if USE_MODEL_PROFILES else "MANUAL",
                                     style="bold green" if USE_MODEL_PROFILES else "yellow"))

    # ===== TOP ROW: MARKET + SIGNAL (2 kolom, lega) =====
    top = Table.grid(expand=True, padding=0, pad_edge=False)
    top.add_column(ratio=1, overflow="fold")
    top.add_column(ratio=1, overflow="fold")
    top.add_row(
        Panel(market, title="MARKET", border_style="cyan", expand=True),
        Panel(signal, title="SIGNAL", border_style="yellow", expand=True),
    )

    # ===== DIAGNOSTIC + MODEL SCORES =====
    if SHOW_DIAGNOSTIC_PANEL:
        try:
            diag_panel = Panel(render_diagnostic_panel(), title="DIAGNOSTIC",
                                border_style="yellow", expand=True)
        except Exception as e:
            diag_panel = Panel(Text(f"diag error: {e}", style="red"), border_style="red")
    else:
        diag_panel = Panel(Text("Diagnostic OFF", style="dim"), border_style="dim")

    try:
        scores_panel = Panel(render_model_scores_panel(),
                             title=f"MODEL SCORES  [RR: {CONFIG.get('MIN_RR_TP3',1.2)}-{MAX_RR_TP3} soft/{HARD_MAX_RR_TP3} hard]",
                             border_style="cyan", expand=True)
    except Exception:
        scores_panel = Panel(Text("scores error", style="red"), border_style="red")

    diag_profile_row = Table.grid(expand=True, padding=0, pad_edge=False)
    diag_profile_row.add_column(ratio=1, overflow="fold")
    diag_profile_row.add_column(ratio=1, overflow="fold")
    diag_profile_row.add_row(diag_panel, scores_panel)

    # ===== MODEL PROFILE =====
    try:
        profile_panel = Panel(render_profile_preview(),
                              title=f"MODEL PROFILE  [{'AUTO' if USE_MODEL_PROFILES else 'MANUAL'}]",
                              border_style="blue", expand=True)
    except Exception:
        profile_panel = Panel(Text("profile error", style="red"), border_style="red")

    # ===== POSITIONS TABLE =====
    pos_table = Table(expand=True, show_header=True, header_style="bold cyan",
                      box=None, padding=(0, 1), pad_edge=False)
    pos_table.add_column("#", justify="center", width=4, no_wrap=True)
    pos_table.add_column("TYPE", justify="center", width=8, no_wrap=True)
    pos_table.add_column("LOT", justify="right", width=9, no_wrap=True)
    pos_table.add_column("ENTRY", justify="right", ratio=2, no_wrap=True)
    pos_table.add_column("CURRENT", justify="right", ratio=2, no_wrap=True)
    pos_table.add_column("SL", justify="right", ratio=2, no_wrap=True)
    pos_table.add_column("TP", justify="right", ratio=2, no_wrap=True)
    pos_table.add_column("P/L", justify="right", ratio=2, no_wrap=True)
    pos_table.add_column("MODEL", justify="left", width=14, no_wrap=True)
    pos_table.add_column("PART", justify="left", width=14, no_wrap=True)
    pos_table.add_column("STATUS", justify="left", ratio=2, no_wrap=True)

    if positions:
        for i, pos in enumerate(positions, 1):
            ptype = "BUY" if pos.type == 0 else "SELL"
            pstyle = "green" if pos.type == 0 else "red"
            tick_price = (bid if pos.type == 0 else ask) if (bid is not None and ask is not None) else pos.price_current
            pnl = float(pos.profit)
            meta = POSITION_META.get(pos.ticket, {})
            model_tag = meta.get("model", "?")
            if pos.magic != 777777 and model_tag == "?":
                model_tag = "MANUAL"

            status = "OPEN"
            plan = PARTIAL_STATE.get(pos.ticket)
            part_display = "-"
            if plan:
                tp1_done = plan.get("tp1_done", False)
                tp2_done = plan.get("tp2_done", False)
                tp3_done = plan.get("tp3_done", False)
                tp1_en = plan.get("tp1_enabled", False)
                tp2_en = plan.get("tp2_enabled", False)
                tp3_en = plan.get("tp3_enabled", False)

                if not (tp1_en or tp2_en or tp3_en):
                    part_display = "NO-PART"
                    status = "SINGLE-TP"
                else:
                    marks = []
                    if tp1_en: marks.append("Y" if tp1_done else "N")
                    if tp2_en: marks.append("Y" if tp2_done else "N")
                    if tp3_en: marks.append("Y" if tp3_done else "N")
                    part_display = "1-2-3:" + ",".join(marks)
                    if tp2_done:
                        status = "TP2 DONE"
                    elif tp1_done:
                        status = "TP1 DONE"
                    else:
                        p_str = ''.join(['1' if tp1_en else '', '2' if tp2_en else '', '3' if tp3_en else ''])
                        status = f"P:{p_str}"

            if pos.sl and ((pos.type == 0 and pos.sl >= pos.price_open) or
                           (pos.type == 1 and pos.sl <= pos.price_open)):
                status = "BE ACTIVE"
            if pos.sl == 0 and pos.tp == 0:
                status = "NO SL/TP"
            tp_display = f"{pos.tp:.2f}" if pos.tp and pos.tp > 0 else "-"
            pos_table.add_row(
                str(i), Text(ptype, style=f"bold {pstyle}"), f"{pos.volume:g}",
                f"{pos.price_open:.2f}", f"{tick_price:.2f}", f"{pos.sl:.2f}",
                tp_display, Text(f"${pnl:.2f}", style="green" if pnl >= 0 else "red"),
                Text(model_tag[:10], style="cyan"),
                Text(part_display, style="yellow"),
                Text(status, style="green" if status != "OPEN" else "yellow"))
    else:
        pos_table.add_row("-", "-", "-", "-", "-", "-", "-", Text("$0.00"), "-", "-", "NO POSITIONS")

    total_pnl = sum(float(p.profit) for p in positions) if positions else 0.0
    total_lot = sum(float(p.volume) for p in positions) if positions else 0.0
    buys = sum(1 for p in positions if p.type == 0) if positions else 0
    sells = sum(1 for p in positions if p.type == 1) if positions else 0
    maxpos = "inf" if MAX_OPEN_POSITIONS == 0 else str(MAX_OPEN_POSITIONS)
    pos_summary = Text()
    pos_summary.append(f"TOTAL P/L ${total_pnl:.2f}", style="green" if total_pnl >= 0 else "red")
    pos_summary.append(f"  | BUY {buys} | SELL {sells} | LOT {total_lot:g} | {len(positions) if positions else 0}/{maxpos}")
    pos_group = Group(pos_table, pos_summary)

    # ===== SL/TP MANAGEMENT PANEL =====
    sl_panel = Table.grid(expand=True, padding=(0, 1))
    sl_panel.add_column(style="cyan", no_wrap=True)
    sl_panel.add_column(ratio=1)
    sl_panel.add_row("L1 Initial", Text("FIB 0.786" if USE_FIB_SL else f"ATR {current_sl_points:.2f}",
                                        style="bold green" if USE_FIB_SL else "cyan"))
    if best_model:
        m = best_model["model"]
        use_be = get_model_setting(m, "USE_BREAK_EVEN", USE_BREAK_EVEN)
        be_r = get_model_setting(m, "BE_TRIGGER_R", BE_TRIGGER_R)
        sl_panel.add_row("L2 BreakEven", Text(f"ON ({be_r}R)" if use_be else "OFF",
                                                style="green" if use_be else "dim"))
        use_trail = get_model_setting(m, "USE_TRAILING_SL", USE_TRAILING_SL)
        use_atr = get_model_setting(m, "USE_ATR_TRAIL_START", USE_ATR_TRAIL_START)
        tp_val = get_model_setting(m, "TRAIL_START_PERCENT", TRAIL_START_PERCENT)
        if use_trail:
            mode_txt = f"ATR {int(tp_val*100)}%" if use_atr else f"${TRAIL_START_PROFIT}"
            sl_panel.add_row("L3 Trailing", Text(f"ON ({mode_txt})", style="green"))
        else:
            sl_panel.add_row("L3 Trailing", Text("OFF", style="dim"))
    sl_panel.add_row("", Text("-" * 20, style="dim"))
    sl_panel.add_row("RR Guard", Text(f"min 1:{CONFIG.get('MIN_RR_TP3',1.2)} / soft 1:{MAX_RR_TP3} / hard 1:{HARD_MAX_RR_TP3}",
                                       style="green"))
    sl_panel.add_row("Partial Thr", Text(f"<{PARTIAL_LOT_THRESHOLD_1} off | {PARTIAL_LOT_THRESHOLD_1}-{PARTIAL_LOT_THRESHOLD_2} TP1+2 | >={PARTIAL_LOT_THRESHOLD_2} TP1+2+3",
                                          style="cyan"))

    # ===== RISK PANEL =====
    risk = Table.grid(expand=True, padding=(0, 1))
    risk.add_column(style="cyan")
    risk.add_column(ratio=1)
    risk.add_row("AutoTrade", rich_status(USE_AUTO_TRADE))
    risk.add_row("Sizing", Text("BONUS" if USE_BONUS_SIZING else ("DYNAMIC" if USE_DYNAMIC_LOT else "FIXED")))
    risk.add_row("Lot Cap", Text(f"{MIN_LOT_SIZE} - {MAX_LOT_SIZE}", style="cyan"))
    risk.add_row("Daily", Text(f"${daily_pnl:.2f} / {daily_loss_percent:.2f}%"))
    risk.add_row("CandleLock", rich_status(USE_CLOSED_CANDLE_LOCK))
    risk.add_row("Cooldown", Text(f"{SIGNAL_COOLDOWN}s", style="cyan"))
    risk.add_row("FakeBrk", Text("FAKE!" if fakeout else "clear",
                                  style="red" if fakeout else "green"))

    mid_row = Table.grid(expand=True, padding=0, pad_edge=False)
    mid_row.add_column(ratio=1, overflow="fold")
    mid_row.add_column(ratio=1, overflow="fold")
    mid_row.add_column(ratio=1, overflow="fold")
    mid_row.add_row(
        Panel(risk, title="RISK", border_style="green", expand=True),
        Panel(sl_panel, title="SL / TP MANAGEMENT", border_style="red", expand=True),
        Panel(Text(f"Balance ${float(account.balance) if account else 0:.2f}\n"
                   f"Equity ${float(account.equity) if account else 0:.2f}\n"
                   f"Daily ${daily_pnl:.2f}", style="white"),
              title="ACCOUNT", border_style="cyan", expand=True),
    )

    # ===== BOTTOM ROW: SESSION (lengkap) + STATS =====
    stats_grid = render_stats_panel()

    # SESSION panel — LENGKAP (4 sesi dengan jam)
    sess = Table.grid(expand=True, padding=(0, 1))
    sess.add_column(style="cyan", no_wrap=True)
    sess.add_column(ratio=1)
    for key, label in (("ASIA", "ASIA"), ("LONDON", "LONDON"),
                       ("NEW_YORK", "NEW YORK"), ("LONDON_NEW_YORK_OVERLAP", "OVERLAP")):
        cfg = SESSION_CONFIG.get(key, {})
        active = key in detect_sessions()
        enabled = cfg.get("ENABLED", False)
        state = "ACTIVE" if active else ("ENABLED" if enabled else "OFF")
        style = "bold green" if active and enabled else "green" if enabled else "dim"
        sess.add_row(label, Text(f"{cfg.get('START', '--:--')}-{cfg.get('END', '--:--')}  {state}", style=style))

    bot_row = Table.grid(expand=True, padding=0, pad_edge=False)
    bot_row.add_column(ratio=1, overflow="fold")
    bot_row.add_column(ratio=2, overflow="fold")
    bot_row.add_row(
        Panel(sess, title="SESSION", border_style="yellow", expand=True),
        Panel(stats_grid, title=f"STATS ({CONFIG.get('STATS_LOOKBACK_DAYS', 7)}d)",
              border_style="cyan", expand=True),
    )

    # ===== STATUS BAR =====
    status_text = Text()
    status = "MONITORING" if positions else "WAITING MODEL"
    if trading_disabled_today:
        status = "DISABLED (daily loss)"
    elif not session_trade_allowed and USE_SESSION_FILTER:
        status = f"OUTSIDE SESSION"
    if is_locked and locked_signal:
        status += f" LOCKED:{locked_signal}"
    status_text.append("* " + status, style="bold green" if positions else "bold yellow")
    status_text.append(f" | Bias {current_bias} | HTF {htf_trend}")

    parts = [
        Panel(header, border_style="cyan", padding=(0, 1)),
        Panel(price, border_style="cyan", padding=(0, 1)),
        top,
        diag_profile_row,
        profile_panel,
        Panel(pos_group, title=f"POSITIONS  {len(positions) if positions else 0}/{maxpos}",
              border_style="white", padding=(0, 1)),
        mid_row,
        bot_row,
        Panel(status_text, border_style="cyan", padding=(0, 1)),
    ]
    if runtime_message_text:
        status_line = Text()
        status_line.append("EVENT ", style="bold cyan")
        status_line.append(runtime_message_text, style="white")
        parts.append(Panel(status_line, border_style="dim", padding=(0, 1)))
    return Group(*parts)


# ===================== STARTUP =====================
print("=" * 60)
print("Starting v4.8 (Dashboard Rapi + Session Lengkap)...")
print(f"   Symbol: {SYMBOL} | Entry TF: {TIMEFRAME_ENTRY}")
print(f"   Auto Trade: {'ON' if USE_AUTO_TRADE else 'OFF'}")
print(f"   Sizing: {'BONUS' if USE_BONUS_SIZING else 'FIXED'}")
print(f"   Lot Cap: {MIN_LOT_SIZE} - {MAX_LOT_SIZE}")
print(f"   Partial Threshold: <{PARTIAL_LOT_THRESHOLD_1} off | "
      f"{PARTIAL_LOT_THRESHOLD_1}-{PARTIAL_LOT_THRESHOLD_2} TP1+2 | "
      f">={PARTIAL_LOT_THRESHOLD_2} TP1+2+3")
print("=" * 60)

time.sleep(2)
console.clear()

# ===================== MAIN LOOP VARIABLES =====================
demand_zones = []
supply_zones = []
last_bid = None
price_direction = ""
last_smc_update = time.time()
last_buy_time = 0
last_sell_time = 0
last_sl_update = time.time()
last_manual_recovery = time.time()
last_candle_time = get_last_closed_candle_time(TIMEFRAME_ENTRY)
active_model = "-"
active_fib_ok = False
best_model = None

refresh_stats(force=True)


# ===================== MAIN LOOP =====================
with Live(console=console, refresh_per_second=4, screen=True, transient=False) as live:
    # ===== STARTUP INITIALIZATION =====
    try:
        df_smc = get_closed_data(TIMEFRAME_SMC, bars=500)
        if df_smc is not None and not df_smc.empty:
            demand_zones = detect_demand_zones(df_smc, SMC_ZONE_SENSITIVITY)
            supply_zones = detect_supply_zones(df_smc, SMC_ZONE_SENSITIVITY)
        if ATR_SL_UPDATE_ON_STARTUP and USE_ATR_SL_EXISTING:
            update_existing_positions_sl()
        if CONFIG.get("USE_MANUAL_RECOVERY", True):
            try:
                recover_manual_entries()
            except Exception as e:
                runtime_message(f"Startup manual recovery: {e}")
        try:
            rebuild_partial_plans()
        except Exception as e:
            runtime_message(f"Rebuild partial: {e}")
    except Exception as e:
        runtime_message(f"Startup: {e}")

    # ===== MAIN LOOP =====
    while True:
        try:
            current_time = time.time()

            # === Reconnect MT5 kalau disconnect ===
            if not mt5.account_info():
                runtime_message("Reconnecting MT5...")
                mt5.initialize()
                time.sleep(3)
                continue

            # === Ambil data entry ===
            df = get_closed_data(TIMEFRAME_ENTRY)
            if df is None or df.empty:
                runtime_message("Waiting data...")
                time.sleep(2)
                continue

            # === Update price direction ===
            bid, ask = get_live_price()
            if bid and last_bid:
                if bid > last_bid:
                    price_direction = "UP"
                elif bid < last_bid:
                    price_direction = "DN"
                else:
                    price_direction = "="
            last_bid = bid

            new_candle = is_new_candle_mt5(TIMEFRAME_ENTRY)
            session_ok = in_session()

            # === Update SMC zones periodically ===
            if USE_SMC_SUPPLY_DEMAND and (current_time - last_smc_update > 60):
                df_smc = get_closed_data(TIMEFRAME_SMC, bars=500)
                if df_smc is not None and not df_smc.empty:
                    demand_zones = detect_demand_zones(df_smc, SMC_ZONE_SENSITIVITY)
                    supply_zones = detect_supply_zones(df_smc, SMC_ZONE_SENSITIVITY)
                last_smc_update = current_time

            # === Update SL existing ===
            if USE_ATR_SL_EXISTING and (current_time - last_sl_update > 60):
                update_existing_positions_sl()
                last_sl_update = current_time

            # === Manual recovery periodic ===
            if CONFIG.get("USE_MANUAL_RECOVERY", True):
                interval = float(MANUAL_PROFILE.get("CHECK_INTERVAL", 30))
                if current_time - last_manual_recovery > interval:
                    recover_manual_entries()
                    last_manual_recovery = current_time

            # === Refresh stats ===
            refresh_stats()

            # === Cleanup POSITION_META untuk posisi yang sudah close ===
            current_positions = mt5.positions_get(symbol=SYMBOL)
            active_tickets = {p.ticket for p in current_positions} if current_positions else set()
            for tk in list(POSITION_META.keys()):
                if tk not in active_tickets:
                    POSITION_META.pop(tk, None)
            persist_state()

            # === Analisis trend & indikator ===
            trend = trend_m5()
            htf_trend = get_higher_timeframe_trend() if USE_CONFLUENCE_CHECK else "SIDEWAYS"

            atr_raw = atr_value(df)
            atr_val = round(atr_raw, 2) if atr_raw is not None else 0.0
            atr_ok = atr_raw is not None and atr_raw >= MIN_ATR_VALUE

            choch = detect_choch(df, SWING_STRICTNESS) if USE_CHOCH else None
            current_bias, bias_just_changed = update_market_bias(choch, trend)

            if USE_SMC_SUPPLY_DEMAND:
                zone_check_price = df['close'].iloc[-1]
                signal_in_demand_zone, _ = price_in_smc_zone(zone_check_price, demand_zones, "DEMAND")
                signal_in_supply_zone, _ = price_in_smc_zone(zone_check_price, supply_zones, "SUPPLY")
            else:
                signal_in_demand_zone = signal_in_supply_zone = False

            smart_sweep_buy = smart_liquidity_sweep(df, "BUY") if USE_SMART_SWEEP else False
            smart_sweep_sell = smart_liquidity_sweep(df, "SELL") if USE_SMART_SWEEP else False
            fakeout = fake_breakout_filter(df)
            wick_status = detect_rejection_wick(df) if USE_REJECTION_WICK else None

            daily_pnl, daily_loss_percent = check_daily_loss()

            # === Update DIAG_STATE ===
            swing_buy_ok = find_last_swing_for_fib(df, "BUY")[0] is not None
            swing_sell_ok = find_last_swing_for_fib(df, "SELL")[0] is not None
            DIAG_STATE["swing_buy"] = swing_buy_ok
            DIAG_STATE["swing_sell"] = swing_sell_ok
            DIAG_STATE["demand_zones"] = len(demand_zones)
            DIAG_STATE["supply_zones"] = len(supply_zones)
            DIAG_STATE["htf_trend"] = htf_trend
            DIAG_STATE["choch"] = choch
            DIAG_STATE["rej_wick"] = wick_status
            DIAG_STATE["in_demand"] = signal_in_demand_zone
            DIAG_STATE["in_supply"] = signal_in_supply_zone
            DIAG_STATE["sweep_buy"] = smart_sweep_buy
            DIAG_STATE["sweep_sell"] = smart_sweep_sell
            DIAG_STATE["notes"] = []

            # === Deteksi 3 model ===
            df_htf = get_closed_data(CONFLUENCE_TF, bars=100)
            model_candidates = []
            m1 = detect_model_continuation(df, df_htf, demand_zones, supply_zones, htf_trend)
            if m1: model_candidates.append(m1)
            m2 = detect_model_reversal(df, df_htf, demand_zones, supply_zones)
            if m2: model_candidates.append(m2)
            m3 = detect_model_sweep(df, demand_zones, supply_zones)
            if m3: model_candidates.append(m3)

            # Reset MODEL_SCORES
            for k in MODEL_SCORES:
                MODEL_SCORES[k] = {"bonus": 0, "rr": 0.0, "fib_ok": False, "dir": "-",
                                   "valid": False, "met": []}

            # === Score setiap model ===
            scored_models = []
            for md in model_candidates:
                entry = df['close'].iloc[-1]
                sl_price, sl_source = resolve_initial_sl(md, entry, atr_raw=atr_raw, digits=2)
                tp_plan = resolve_tp(md["swing_low"], md["swing_high"], md["direction"],
                                     entry, sl_price, df, md["model"])
                tp_valid, rr_est, tp_plan = validate_tp(tp_plan, entry, sl_price, md["direction"])
                pts, met = calculate_bonus_points(md, df, session_ok, rr_estimate=rr_est)
                md["bonus"] = pts
                md["bonus_met"] = met
                md["rr"] = rr_est
                md["tp_plan"] = tp_plan
                md["tp_valid"] = tp_valid
                md["sl_price"] = sl_price
                md["sl_source"] = sl_source
                scored_models.append(md)

                MODEL_SCORES[md["model"]] = {
                    "bonus": pts, "rr": rr_est, "fib_ok": md["fib_zone_ok"],
                    "dir": md["direction"], "valid": tp_valid, "met": met,
                }

            # === Filter valid models ===
            valid_models = []
            for md in scored_models:
                if CONFIG.get("USE_TP_RR_GUARD", True) and not md.get("tp_valid", True):
                    continue
                if USE_ATR_FILTER and not atr_ok:
                    continue
                if USE_SESSION_FILTER and not session_ok:
                    continue
                use_fb = get_model_setting(md["model"], "USE_FAKE_BREAK_FILTER", USE_FAKE_BREAK_FILTER)
                if use_fb and fakeout:
                    continue
                valid_models.append(md)

            best_model = max(valid_models, key=lambda m: m["bonus"]) if valid_models else None

            buy_ready = bool(best_model and best_model["direction"] == "BUY")
            sell_ready = bool(best_model and best_model["direction"] == "SELL")
            buy_score = best_model["bonus"] if best_model else 0
            sell_score = best_model["bonus"] if best_model else 0
            active_model = best_model["model"] if best_model else "-"
            active_fib_ok = best_model["fib_zone_ok"] if best_model else False

            current_sl_points = calculate_dynamic_sl(atr=atr_raw)

            # === Cooldown check ===
            if buy_ready and (current_time - last_buy_time < SIGNAL_COOLDOWN):
                buy_ready = False
                best_model = None
            if sell_ready and (current_time - last_sell_time < SIGNAL_COOLDOWN):
                sell_ready = False
                best_model = None

            # === Closed candle lock ===
            if USE_CLOSED_CANDLE_LOCK:
                if new_candle:
                    current_candle_time = get_last_closed_candle_time(TIMEFRAME_ENTRY)
                    if best_model:
                        locked_signal = best_model["direction"]
                        locked_buy_score = buy_score
                        locked_sell_score = sell_score
                        locked_candle_time = current_candle_time
                        is_locked = True
                        rr_val = best_model.get("rr", 0)
                        warn = f" WARN-RR1:{rr_val:.1f}" if rr_val > MAX_RR_TP3 else ""
                        runtime_message(f"LOCKED {locked_signal} [{best_model['model']}] B{best_model['bonus']}{warn}")
                    else:
                        is_locked = False
                        locked_signal = None

            # === Execution ===
            if USE_CLOSED_CANDLE_LOCK:
                if is_locked and locked_signal and best_model:
                    if not trading_disabled_today and USE_AUTO_TRADE and session_ok:
                        last_t = last_buy_time if locked_signal == "BUY" else last_sell_time
                        if current_time - last_t >= SIGNAL_COOLDOWN:
                            runtime_message(f"EXEC {best_model['model']} {locked_signal}")
                            open_trade_model(best_model, best_model["bonus"])
                            if locked_signal == "BUY":
                                last_buy_time = current_time
                            else:
                                last_sell_time = current_time
                            is_locked = False
                            locked_signal = None
            else:
                if not trading_disabled_today and USE_AUTO_TRADE and session_ok and best_model:
                    runtime_message(f"{best_model['model']} {best_model['direction']}")
                    open_trade_model(best_model, best_model["bonus"])
                    if best_model["direction"] == "BUY":
                        last_buy_time = current_time
                    else:
                        last_sell_time = current_time

            # === SL/TP MANAGEMENT ===
            manage_partial_close_fib()
            manage_trailing_sl()
            manage_break_even()

            # === Update dashboard ===
            account = mt5.account_info()
            positions = mt5.positions_get(symbol=SYMBOL)
            current_session, _, session_trade_allowed = get_session_status_text()

            live.update(render_rich_dashboard(
                account=account, positions=positions, bid=bid, ask=ask,
                price_direction=price_direction, current_sl_points=current_sl_points,
                current_session=current_session, session_trade_allowed=session_trade_allowed,
                trend=trend, htf_trend=htf_trend, current_bias=current_bias,
                atr_val=atr_val, atr_ok=atr_ok,
                buy_ready=buy_ready, sell_ready=sell_ready, buy_score=buy_score,
                sell_score=sell_score, choch=choch,
                daily_pnl=daily_pnl, daily_loss_percent=daily_loss_percent,
                trading_disabled_today=trading_disabled_today,
                is_locked=is_locked, locked_signal=locked_signal,
                locked_buy_score=locked_buy_score, locked_sell_score=locked_sell_score,
                active_model=active_model, active_fib_ok=active_fib_ok,
                best_model=best_model, fakeout=fakeout,
            ))

            time.sleep(1)

        except KeyboardInterrupt:
            break
        except Exception as e:
            log_error(f"main loop: {traceback.format_exc()}")
            runtime_message(f"ERROR: {e}")
            time.sleep(3)
