# ========= AUTO-INSTALL (ONLY DHAN, OPTIONAL) =========
import subprocess, sys

def ensure_package(pkg_name: str):
    try:
        __import__(pkg_name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg_name])

try:
    ensure_package("dhanhq")
except Exception:
    pass

# ========= IMPORTS =========
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import ta
from datetime import datetime
from typing import Dict, List, Optional
import pytz
import requests
import os
import json
from pathlib import Path

from streamlit_local_storage import LocalStorage

# Dhan
try:
    from dhanhq import dhanhq
except ImportError:
    dhanhq = None

# ========= CONFIG FILE (SERVER-SIDE BACKUP) =========
CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "dhan_client_id": "",
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "notify_enabled": False
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        cfg = DEFAULT_CONFIG.copy()
        cfg.update(data)
        return cfg
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config_from_state():
    cfg = {
        "dhan_client_id": st.session_state.get("dhan_client_id", ""),
        "telegram_bot_token": st.session_state.get("telegram_bot_token", ""),
        "telegram_chat_id": st.session_state.get("telegram_chat_id", ""),
        "notify_enabled": st.session_state.get("notify_enabled", False),
    }
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        st.warning(f"Could not save config: {e}")

# ========= PAGE CONFIG & CSS =========
st.set_page_config(
    page_title="🚀 AI Stock Bot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Global Reset & Base Styles */
    * {
        box-sizing: border-box;
    }
    
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, sans-serif;
    }
    
    .main .block-container {
        padding: 1rem clamp(1rem, 3vw, 2rem);
        max-width: 100%;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e1b4b 0%, #312e81 50%, #4c1d95 100%);
        padding: 1rem;
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: #f3f4f6;
    }
    
    /* Sidebar Navigation Buttons */
    [data-testid="stSidebar"] .stButton > button {
        background: rgba(255,255,255,0.1) !important;
        color: #f3f4f6 !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 0.75rem 1rem !important;
        width: 100% !important;
        text-align: left !important;
        transition: all 0.3s ease !important;
        margin-bottom: 0.5rem !important;
    }
    
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255,255,255,0.2) !important;
        border-color: rgba(255,255,255,0.4) !important;
        transform: translateX(5px);
    }
    
    [data-testid="stSidebar"] .stButton > button:active,
    [data-testid="stSidebar"] .stButton > button:focus {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        border-color: rgba(255,255,255,0.3) !important;
        box-shadow: 0 4px 12px rgba(102,126,234,0.4) !important;
    }
    
    /* Sidebar Headers */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #f3f4f6;
        font-weight: 700;
    }
    
    /* Sidebar Divider */
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.2);
        margin: 1.5rem 0;
    }
    
    /* Main Header - Responsive */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        padding: clamp(1rem, 3vw, 2rem) clamp(1rem, 3vw, 2rem);
        border-radius: 20px;
        text-align: center;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        position: relative;
        overflow: hidden;
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: radial-gradient(circle at 30% 50%, rgba(255,255,255,0.1) 0%, transparent 50%);
        pointer-events: none;
    }
    
    .main-header h1 {
        margin: 0;
        font-size: clamp(1.5rem, 4vw, 2.5rem);
        font-weight: 800;
        text-shadow: 2px 2px 8px rgba(0,0,0,0.3);
        position: relative;
        z-index: 1;
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        font-size: clamp(0.85rem, 2vw, 1rem);
        opacity: 0.95;
        position: relative;
        z-index: 1;
    }
    
    .status-badge {
        display: inline-block;
        padding: 0.4rem 1rem;
        border-radius: 50px;
        font-size: clamp(0.65rem, 1.5vw, 0.75rem);
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        background: rgba(255,255,255,0.25);
        backdrop-filter: blur(10px);
        margin-top: 0.8rem;
        border: 1px solid rgba(255,255,255,0.3);
        position: relative;
        z-index: 1;
    }
    

    
    /* Enhanced Metric Cards with Flash Effect */
    .metric-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(255,255,255,0.95) 100%);
        backdrop-filter: blur(20px);
        padding: clamp(1.2rem, 2.5vw, 1.8rem);
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.12);
        margin-bottom: 1.2rem;
        border: 1px solid rgba(255,255,255,0.6);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
        animation: cardFadeIn 0.6s ease-out;
    }
    
    @keyframes cardFadeIn {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 5px;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        background-size: 200% 100%;
        animation: gradientShift 3s ease infinite;
    }
    
    @keyframes gradientShift {
        0%, 100% {
            background-position: 0% 50%;
        }
        50% {
            background-position: 100% 50%;
        }
    }
    
    .metric-card::after {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(102,126,234,0.1) 0%, transparent 70%);
        opacity: 0;
        transition: opacity 0.4s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 16px 48px rgba(102,126,234,0.25);
        border-color: rgba(102,126,234,0.4);
    }
    
    .metric-card:hover::after {
        opacity: 1;
        animation: pulse 2s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% {
            transform: scale(1) rotate(0deg);
        }
        50% {
            transform: scale(1.1) rotate(180deg);
        }
    }
    
    .metric-card h3 {
        font-size: clamp(1.1rem, 2.5vw, 1.4rem);
        color: #1e293b;
        margin: 0 0 1rem 0;
        font-weight: 800;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.8rem;
        flex-wrap: wrap;
        position: relative;
        z-index: 1;
    }
    
    .stock-symbol {
        font-size: clamp(1.3rem, 3vw, 1.6rem);
        font-weight: 900;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -0.5px;
    }
    
    .metric-card .value {
        font-size: clamp(1.2rem, 3vw, 1.5rem);
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.8rem;
        line-height: 1.5;
        position: relative;
        z-index: 1;
        display: flex;
        align-items: center;
        gap: 1rem;
        flex-wrap: wrap;
    }
    
    .price-tag {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.4rem 0.8rem;
        background: linear-gradient(135deg, rgba(102,126,234,0.1) 0%, rgba(118,75,162,0.1) 100%);
        border-radius: 12px;
        border: 1px solid rgba(102,126,234,0.2);
    }
    
    .target-tag {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.4rem 0.8rem;
        background: linear-gradient(135deg, rgba(72,187,120,0.15) 0%, rgba(56,161,105,0.15) 100%);
        border-radius: 12px;
        border: 1px solid rgba(72,187,120,0.3);
        color: #166534;
        font-weight: 700;
    }
    
    .metric-card .sub {
        font-size: clamp(0.8rem, 2vw, 0.9rem);
        color: #4a5568;
        line-height: 1.6;
        margin-top: 0.5rem;
    }
    
    .metric-card .profit {
        color: #48bb78;
        font-weight: 700;
    }
    
    .metric-card .loss {
        color: #f56565;
        font-weight: 700;
    }
    
    /* Enhanced Chip Row with Better Styling */
    .chip-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.6rem;
        margin-top: 1rem;
    }
    
    .chip {
        padding: 0.4rem 1rem;
        border-radius: 50px;
        font-size: clamp(0.75rem, 1.8vw, 0.85rem);
        background: linear-gradient(135deg, rgba(102,126,234,0.12) 0%, rgba(118,75,162,0.12) 100%);
        border: 1.5px solid rgba(102,126,234,0.35);
        color: #5a67d8;
        font-weight: 700;
        white-space: nowrap;
        transition: all 0.3s ease;
    }
    
    .chip:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102,126,234,0.25);
        border-color: #667eea;
    }
    
    .profit-box {
        background: linear-gradient(135deg, rgba(16,185,129,0.15) 0%, rgba(5,150,105,0.15) 100%);
        border: 2px solid rgba(16,185,129,0.4);
        padding: 0.8rem 1.2rem;
        border-radius: 15px;
        margin-top: 1rem;
        display: inline-block;
    }
    
    .profit-box .profit-label {
        font-size: clamp(0.85rem, 2vw, 0.95rem);
        color: #065f46;
        font-weight: 800;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .reason-box {
        background: linear-gradient(135deg, rgba(59,130,246,0.08) 0%, rgba(37,99,235,0.08) 100%);
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        border-radius: 12px;
        margin-top: 1rem;
    }
    
    .reason-box .reason-text {
        font-size: clamp(0.85rem, 2vw, 0.95rem);
        color: #1e40af;
        font-weight: 600;
        line-height: 1.6;
    }
    
    /* Enhanced Signal Strength Badges with Glow */
    .signal-strong-buy {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 50px;
        font-size: clamp(0.7rem, 1.8vw, 0.85rem);
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        display: inline-block;
        box-shadow: 0 4px 15px rgba(16,185,129,0.4);
        animation: glowGreen 2s ease-in-out infinite;
    }
    
    @keyframes glowGreen {
        0%, 100% {
            box-shadow: 0 4px 15px rgba(16,185,129,0.4);
        }
        50% {
            box-shadow: 0 6px 25px rgba(16,185,129,0.6);
        }
    }
    
    .signal-buy {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 50px;
        font-size: clamp(0.7rem, 1.8vw, 0.85rem);
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        display: inline-block;
        box-shadow: 0 4px 15px rgba(59,130,246,0.4);
        animation: glowBlue 2s ease-in-out infinite;
    }
    
    @keyframes glowBlue {
        0%, 100% {
            box-shadow: 0 4px 15px rgba(59,130,246,0.4);
        }
        50% {
            box-shadow: 0 6px 25px rgba(59,130,246,0.6);
        }
    }
    
    .signal-hold {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 50px;
        font-size: clamp(0.7rem, 1.8vw, 0.85rem);
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        display: inline-block;
        box-shadow: 0 4px 15px rgba(245,158,11,0.4);
    }
    
    /* Primary Buttons */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        font-size: clamp(0.9rem, 2.2vw, 1rem) !important;
        padding: 0.8rem 1.5rem !important;
        box-shadow: 0 4px 15px rgba(102,126,234,0.4) !important;
        transition: all 0.3s ease !important;
        min-height: 48px !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102,126,234,0.5) !important;
    }
    
    .stButton > button[kind="primary"]:active {
        transform: translateY(0);
    }
    
    /* Secondary Buttons */
    .stButton > button:not([kind="primary"]) {
        background: rgba(255,255,255,0.9) !important;
        color: #667eea !important;
        border: 2px solid rgba(102,126,234,0.3) !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-size: clamp(0.85rem, 2vw, 0.95rem) !important;
        transition: all 0.3s ease !important;
        min-height: 44px !important;
    }
    
    .stButton > button:not([kind="primary"]):hover {
        background: rgba(102,126,234,0.1) !important;
        border-color: #667eea !important;
    }
    
    /* Info/Success/Error Messages */
    .stAlert {
        border-radius: 15px;
        border: none;
        padding: 1rem;
        backdrop-filter: blur(10px);
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background: rgba(255,255,255,0.9);
        border-radius: 12px;
        font-weight: 600;
        color: #667eea;
        padding: 1rem;
        border: 1px solid rgba(102,126,234,0.2);
    }
    
    .streamlit-expanderHeader:hover {
        background: rgba(255,255,255,1);
        border-color: #667eea;
    }
    
    /* DataFrames */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }
    
    /* Text Inputs */
    .stTextInput > div > div > input {
        border-radius: 10px;
        border: 2px solid rgba(102,126,234,0.2);
        padding: 0.8rem;
        font-size: 0.95rem;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 2px rgba(102,126,234,0.2);
    }
    
    /* Checkboxes */
    .stCheckbox {
        font-size: 1rem;
        font-weight: 600;
        color: #2d3748;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: clamp(1.2rem, 3vw, 1.5rem);
        font-weight: 700;
        color: #667eea;
    }
    
    /* File Uploader */
    .stFileUploader {
        background: rgba(255,255,255,0.9);
        border-radius: 15px;
        padding: 1.5rem;
        border: 2px dashed rgba(102,126,234,0.3);
    }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Tablet Styles */
    @media (min-width: 769px) and (max-width: 1024px) {
        .main .block-container {
            padding: 1.5rem 2rem;
        }
        
        .metric-card {
            padding: 1.2rem;
        }
    }
    
    /* Mobile Styles */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 0.5rem 1rem;
        }
        
        .main-header {
            border-radius: 15px;
            margin-bottom: 1rem;
        }
        
        .top-nav {
            margin: 0.5rem 0;
            padding: 0.3rem 0;
        }
        
        .metric-card {
            border-radius: 15px;
            margin-bottom: 0.8rem;
        }
        
        .metric-card h3 {
            font-size: 1rem;
        }
        
        .chip-row {
            gap: 0.4rem;
        }
        
        /* Stack columns on mobile */
        .row-widget.stHorizontal {
            flex-direction: column;
        }
        
        .row-widget.stHorizontal > div {
            width: 100% !important;
        }
    }
    
    /* Large Desktop */
    @media (min-width: 1400px) {
        .main .block-container {
            max-width: 1400px;
            margin: 0 auto;
        }
    }
    
    /* Print Styles */
    @media print {
        .top-nav,
        .stButton {
            display: none;
        }
    }
</style>
""", unsafe_allow_html=True)

IST = pytz.timezone('Asia/Kolkata')

# ========= LOAD CONFIG & SESSION STATE =========
_cfg = load_config()
localS = LocalStorage()

if 'last_analysis_time' not in st.session_state:
    st.session_state['last_analysis_time'] = None
if 'last_auto_scan' not in st.session_state:
    st.session_state['last_auto_scan'] = None
if 'recommendations' not in st.session_state:
    st.session_state['recommendations'] = {'BTST': [], 'Intraday': [], 'Weekly': [], 'Monthly': []}
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = "🔥 Top Stocks"

# Dhan state
for key, default in [
    ('dhan_enabled', False),
    ('dhan_client_id', _cfg.get('dhan_client_id', '')),
    ('dhan_access_token', ''),
    ('dhan_client', None),
    ('dhan_login_msg', 'Not configured'),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# Telegram state
for key, default in [
    ('notify_enabled', _cfg.get('notify_enabled', False)),
    ('telegram_bot_token', _cfg.get('telegram_bot_token', '')),
    ('telegram_chat_id', _cfg.get('telegram_chat_id', '')),
    ('last_pnl_notify', None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ========= NIFTY 200 FROM CSV =========
DATA_DIR = Path(__file__).parent / "data"
NIFTY200_CSV = DATA_DIR / "nifty200_yahoo.csv"
MASTER_NIFTY200 = DATA_DIR / "ind_nifty200list.csv"

@st.cache_data
def load_nifty200_universe():
    if not NIFTY200_CSV.exists():
        st.error(f"Universe file not found: {NIFTY200_CSV}")
        return [], {}
    df = pd.read_csv(NIFTY200_CSV)
    if "SYMBOL" not in df.columns or "YF_TICKER" not in df.columns:
        st.error("nifty200_yahoo.csv must have columns: SYMBOL, YF_TICKER")
        return [], {}
    df["SYMBOL"] = df["SYMBOL"].astype(str).str.strip().str.upper()
    df["YF_TICKER"] = df["YF_TICKER"].astype(str).str.strip()
    symbols = df["SYMBOL"].dropna().unique().tolist()
    mapping = dict(zip(df["SYMBOL"], df["YF_TICKER"]))
    return symbols, mapping

STOCK_UNIVERSE, NIFTY_YF_MAP = load_nifty200_universe()

def regenerate_nifty200_csv_from_master():
    if not MASTER_NIFTY200.exists():
        st.error(f"Master list not found: {MASTER_NIFTY200}")
        return False
    df_src = pd.read_csv(MASTER_NIFTY200)
    if "Symbol" not in df_src.columns:
        st.error("ind_nifty200list.csv must have a 'Symbol' column")
        return False
    df_out = pd.DataFrame()
    df_out["SYMBOL"] = df_src["Symbol"].astype(str).str.strip().str.upper()
    df_out["YF_TICKER"] = df_out["SYMBOL"].apply(lambda s: f"{s}.NS")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(NIFTY200_CSV, index=False)
    load_nifty200_universe.clear()
    global STOCK_UNIVERSE, NIFTY_YF_MAP
    STOCK_UNIVERSE, NIFTY_YF_MAP = load_nifty200_universe()
    return True

# ========= SYMBOL HELPERS =========
def nse_yf_symbol(sym: str) -> str:
    if not sym:
        return ""
    s = sym.strip().upper()
    if s in NIFTY_YF_MAP:
        return NIFTY_YF_MAP[s]
    return s if s.endswith(".NS") else f"{s}.NS"

# ========= DHAN HELPERS =========
def dhan_login(client_id: str, access_token: str):
    if not dhanhq:
        st.session_state['dhan_client'] = None
        st.session_state['dhan_login_msg'] = "dhanhq not installed"
        return
    try:
        d = dhanhq(client_id, access_token)
        _ = d.get_holdings()
        st.session_state['dhan_client'] = d
        st.session_state['dhan_login_msg'] = "✅ Dhan client configured"
    except Exception as e:
        st.session_state['dhan_client'] = None
        st.session_state['dhan_login_msg'] = f"❌ Dhan error: {e}"

def dhan_logout():
    st.session_state['dhan_client'] = None
    st.session_state['dhan_login_msg'] = "Logged out"

def get_dhan_raw():
    d = st.session_state.get('dhan_client')
    if not d:
        return pd.DataFrame(), pd.DataFrame()
    try:
        h = d.get_holdings()
        holdings = h.get("data", []) if isinstance(h, dict) else h
    except Exception:
        holdings = []
    try:
        p = d.get_positions()
        positions = p.get("data", []) if isinstance(p, dict) else p
    except Exception:
        positions = []
    return pd.DataFrame(holdings), pd.DataFrame(positions)

def format_dhan_portfolio_table():
    h_df, p_df = get_dhan_raw()
    if h_df.empty and p_df.empty:
        return pd.DataFrame(), 0.0
    if not h_df.empty:
        name_col = next((c for c in ['securityName', 'tradingSymbol', 'symbol'] if c in h_df.columns), None)
        qty_col = next((c for c in ['quantity', 'netQty', 'buyQty', 'totalQty'] if c in h_df.columns), None)
        avg_col = next((c for c in ['averagePrice', 'buyAvg', 'avgCostPrice'] if c in h_df.columns), None)
        cmp_col = next((c for c in ['ltp', 'lastTradedPrice', 'lastPrice'] if c in h_df.columns), None)
        h_df['_name'] = h_df[name_col] if name_col else ""
        h_df['_qty'] = pd.to_numeric(h_df[qty_col], errors='coerce').fillna(0.0) if qty_col else 0.0
        h_df['_avg'] = pd.to_numeric(h_df[avg_col], errors='coerce').fillna(0.0) if avg_col else 0.0
        h_df['_cmp'] = pd.to_numeric(h_df[cmp_col], errors='coerce') if cmp_col else np.nan
        h_df['_total_cost'] = h_df['_qty'] * h_df['_avg']
        h_df['_total_price'] = h_df['_qty'] * h_df['_cmp']
        h_df['_pnl'] = h_df['_total_price'] - h_df['_total_cost']
        portfolio = h_df[['_name', '_qty', '_avg', '_total_cost', '_cmp', '_total_price', '_pnl']].rename(
            columns={
                '_name': 'Stock',
                '_qty': 'Quantity',
                '_avg': 'Avg Cost',
                '_total_cost': 'Total Cost',
                '_cmp': 'CMP',
                '_total_price': 'Total Value',
                '_pnl': 'P&L'
            }
        )
    else:
        name_col = next((c for c in ['tradingSymbol', 'securityName', 'symbol'] if c in p_df.columns), None)
        p_df['_name'] = p_df[name_col] if name_col else ""
        p_df['_qty'] = pd.to_numeric(p_df['netQty'], errors='coerce').fillna(0.0)
        p_df['_avg'] = pd.to_numeric(p_df['avgPrice'], errors='coerce').fillna(0.0)
        p_df['_cmp'] = pd.to_numeric(p_df['ltp'], errors='coerce').fillna(0.0)
        p_df['_total_cost'] = p_df['_qty'] * p_df['_avg']
        p_df['_total_price'] = p_df['_qty'] * p_df['_cmp']
        p_df['_pnl'] = p_df['_total_price'] - p_df['_total_cost']
        portfolio = p_df[['_name', '_qty', '_avg', '_total_cost', '_cmp', '_total_price', '_pnl']].rename(
            columns={
                '_name': 'Stock',
                '_qty': 'Quantity',
                '_avg': 'Avg Cost',
                '_total_cost': 'Total Cost',
                '_cmp': 'CMP',
                '_total_price': 'Total Value',
                '_pnl': 'P&L'
            }
        )
    total_pnl = float(portfolio['P&L'].fillna(0).sum())
    return portfolio, total_pnl

# ========= TELEGRAM HELPER =========
def send_telegram_message(text: str):
    token = st.session_state.get('telegram_bot_token', '')
    chat_id = st.session_state.get('telegram_chat_id', '')
    if not token or not chat_id:
        return {"ok": False, "error": "Missing Telegram config"}
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.get(url, params={"chat_id": chat_id, "text": text})
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ========= TA & ANALYSIS =========
def safe_extract(df, col):
    if df is None or df.empty or col not in df.columns:
        return pd.Series(dtype=float)
    s = df[col]
    if isinstance(s, pd.DataFrame):
        s = s.squeeze()
    return pd.Series(s) if not isinstance(s, pd.Series) else s

def safe_scalar(x):
    try:
        if pd.isna(x):
            return np.nan
        if isinstance(x, (pd.Series, list, np.ndarray)):
            x = np.ravel(x)[-1]
        return float(x)
    except Exception:
        return np.nan

class TechnicalAnalysis:
    @staticmethod
    def rsi_signal(df):
        c = safe_extract(df, 'Close')
        if len(c) < 15:
            return False, None, 0
        rsi = ta.momentum.RSIIndicator(c, window=14).rsi()
        v = safe_scalar(rsi.iloc[-1])
        if v < 30:
            return True, f"RSI Oversold ({v:.1f})", 35
        if v < 40:
            return True, f"RSI Strong Buy Zone ({v:.1f})", 25
        return False, None, 0

    @staticmethod
    def macd_signal(df):
        c = safe_extract(df, 'Close')
        if len(c) < 35:
            return False, None, 0
        macd = ta.trend.MACD(c)
        m = safe_scalar(macd.macd().iloc[-1])
        s = safe_scalar(macd.macd_signal().iloc[-1])
        h = safe_scalar(macd.macd_diff().iloc[-1])
        if m > s and h > 0:
            return True, "MACD Bullish Crossover", 30
        return False, None, 0

    @staticmethod
    def stochastic_signal(df):
        h, l, c = safe_extract(df, 'High'), safe_extract(df, 'Low'), safe_extract(df, 'Close')
        if len(c) < 14:
            return False, None, 0
        stoch = ta.momentum.StochasticOscillator(h, l, c, window=14, smooth_window=3)
        k = safe_scalar(stoch.stoch().iloc[-1])
        d = safe_scalar(stoch.stoch_signal().iloc[-1])
        if k < 20 and k > d:
            return True, "Stochastic Oversold Reversal", 25
        return False, None, 0

    @staticmethod
    def adx_trend_strength(df):
        h, l, c = safe_extract(df, 'High'), safe_extract(df, 'Low'), safe_extract(df, 'Close')
        if len(c) < 25:
            return False, None, 0
        adx = ta.trend.ADXIndicator(h, l, c, window=14)
        adx_val = safe_scalar(adx.adx().iloc[-1])
        plus_di = safe_scalar(adx.adx_pos().iloc[-1])
        minus_di = safe_scalar(adx.adx_neg().iloc[-1])
        if adx_val > 25 and plus_di > minus_di:
            return True, f"Strong Uptrend (ADX: {adx_val:.1f})", 30
        return False, None, 0

    @staticmethod
    def bollinger_squeeze(df):
        c = safe_extract(df, 'Close')
        if len(c) < 20:
            return False, None, 0
        bb = ta.volatility.BollingerBands(c, window=20, window_dev=2)
        lower = safe_scalar(bb.bollinger_lband().iloc[-1])
        upper = safe_scalar(bb.bollinger_hband().iloc[-1])
        price = safe_scalar(c.iloc[-1])
        bandwidth = (upper - lower) / price * 100
        if price < lower * 1.02 and bandwidth < 10:
            return True, "BB Squeeze Breakout Setup", 25
        return False, None, 0

    @staticmethod
    def volume_price_confirmation(df):
        v = safe_extract(df, 'Volume')
        c = safe_extract(df, 'Close')
        if len(v) < 20:
            return False, None, 0
        avg_vol = v.rolling(20).mean().iloc[-1]
        cur_vol = v.iloc[-1]
        chg = ((c.iloc[-1] - c.iloc[-2]) / c.iloc[-2]) * 100
        if cur_vol > avg_vol * 1.5 and chg > 1:
            return True, f"Volume Spike with Price Up ({chg:.1f}%)", 30
        return False, None, 0

    @staticmethod
    def ema_crossover(df):
        c = safe_extract(df, 'Close')
        if len(c) < 50:
            return False, None, 0
        ema9 = ta.trend.EMAIndicator(c, window=9).ema_indicator()
        ema21 = ta.trend.EMAIndicator(c, window=21).ema_indicator()
        if safe_scalar(ema9.iloc[-1]) > safe_scalar(ema21.iloc[-1]) and safe_scalar(ema9.iloc[-2]) <= safe_scalar(ema21.iloc[-2]):
            return True, "EMA 9/21 Golden Cross", 28
        return False, None, 0

    @staticmethod
    def obv_divergence(df):
        c = safe_extract(df, 'Close')
        v = safe_extract(df, 'Volume')
        if len(c) < 20:
            return False, None, 0
        obv = ta.volume.OnBalanceVolumeIndicator(c, v).on_balance_volume()
        obv_sma = obv.rolling(10).mean()
        if safe_scalar(obv.iloc[-1]) > safe_scalar(obv_sma.iloc[-1]):
            return True, "OBV Accumulation Phase", 22
        return False, None, 0

    @staticmethod
    def calculate_targets(df, price):
        h, l, c = safe_extract(df, 'High'), safe_extract(df, 'Low'), safe_extract(df, 'Close')
        if len(c) < 14:
            return {}
        atr = ta.volatility.AverageTrueRange(h, l, c, window=14).average_true_range()
        atr_v = safe_scalar(atr.iloc[-1])
        return {
            'atr': float(round(atr_v, 2)),
            'stop_loss': float(round(price - (atr_v * 2), 2)),
            'target_1': float(round(price + (atr_v * 2), 2)),
            'target_2': float(round(price + (atr_v * 3), 2)),
            'target_3': float(round(price + (atr_v * 4), 2)),
            'risk_reward': '1:2-4'
        }

def analyze_stock(ticker: str, period_type: str) -> Optional[Dict]:
    cfgs = {
        'BTST': {'period': '10d', 'interval': '15m'},
        'Intraday': {'period': '5d', 'interval': '15m'},
        'Weekly': {'period': '90d', 'interval': '1d'},
        'Monthly': {'period': '1y', 'interval': '1d'}
    }
    cfg = cfgs[period_type]
    try:
        t = yf.Ticker(nse_yf_symbol(ticker))
        df = t.history(period=cfg['period'], interval=cfg['interval'], auto_adjust=True)
        if df is None or df.empty or len(df) < 30:
            return None
        df = df.reset_index()
        df.columns = [str(c).capitalize() for c in df.columns]
        strategies = [
            (TechnicalAnalysis.rsi_signal, 'RSI'),
            (TechnicalAnalysis.macd_signal, 'MACD'),
            (TechnicalAnalysis.stochastic_signal, 'Stochastic'),
            (TechnicalAnalysis.adx_trend_strength, 'ADX'),
            (TechnicalAnalysis.bollinger_squeeze, 'Bollinger'),
            (TechnicalAnalysis.volume_price_confirmation, 'Volume'),
            (TechnicalAnalysis.ema_crossover, 'EMA'),
            (TechnicalAnalysis.obv_divergence, 'OBV')
        ]
        signals, reasons, score = [], [], 0
        for func, name in strategies:
            sig, reason, s_ = func(df)
            if sig:
                signals.append(name)
                if reason:
                    reasons.append(reason)
                score += s_
        if len(signals) < 3:
            return None
        price = float(df['Close'].iloc[-1])
        targets = TechnicalAnalysis.calculate_targets(df, price)
        strength = "STRONG BUY" if score >= 90 else "BUY" if score >= 60 else "HOLD"
        timeframe_map = {
            'BTST': '1–3 days (BTST)',
            'Intraday': 'Same day',
            'Weekly': 'Up to 1 week',
            'Monthly': '2–4 weeks'
        }
        timeframe = timeframe_map.get(period_type, '1–5 days')
        return {
            'ticker': ticker,
            'price': round(price, 2),
            'signals_count': len(signals),
            'strategies': ", ".join(signals),
            'score': score,
            'reasons': " | ".join(reasons),
            'signal_strength': strength,
            'period': period_type,
            'timeframe': timeframe,
            **targets
        }
    except Exception:
        return None

def analyze_multiple_stocks(tickers: List[str], period_type: str, max_results: int = 10) -> List[Dict]:
    out = []
    if not tickers:
        return out
    bar = st.progress(0.0)
    txt = st.empty()
    for i, tck in enumerate(tickers):
        txt.text(f"🔍 Analyzing {period_type}: {tck} ({i+1}/{len(tickers)})")
        bar.progress((i + 1) / len(tickers))
        res = analyze_stock(tck, period_type)
        if res:
            out.append(res)
    bar.empty()
    txt.empty()
    return sorted(out, key=lambda x: x['score'], reverse=True)[:max_results]

def run_analysis():
    now = datetime.now(IST)
    st.session_state['last_analysis_time'] = now
    st.session_state['last_auto_scan'] = now
    for p in ['BTST', 'Intraday', 'Weekly', 'Monthly']:
        st.session_state['recommendations'][p] = analyze_multiple_stocks(STOCK_UNIVERSE, p, max_results=20)

def market_hours_window(dt: datetime):
    start = dt.replace(hour=9, minute=10, second=0, microsecond=0)
    end = dt.replace(hour=15, minute=40, second=0, microsecond=0)
    return start <= dt <= end

def auto_scan_if_due():
    now = datetime.now(IST)
    last = st.session_state.get('last_auto_scan')
    if not market_hours_window(now):
        return
    should_run = False
    if last is None:
        should_run = True
    else:
        try:
            if (now - last).total_seconds() >= 20 * 60:
                should_run = True
        except Exception:
            should_run = True
    if should_run:
        run_analysis()

def get_top_stocks(limit: int = 10):
    all_recs = []
    for period in ['BTST', 'Intraday', 'Weekly', 'Monthly']:
        for r in st.session_state['recommendations'].get(period, []):
            rec = dict(r)
            rec['period'] = period
            all_recs.append(rec)
    if not all_recs:
        return []
    df_all = pd.DataFrame(all_recs).sort_values("score", ascending=False)
    seen = set()
    unique_rows = []
    for _, row in df_all.iterrows():
        t = row.get('ticker')
        if t not in seen:
            seen.add(t)
            unique_rows.append(row)
        if len(unique_rows) >= limit:
            break
    if not unique_rows:
        return []
    return pd.DataFrame(unique_rows).to_dict(orient="records")

def analyze_groww_portfolio(df: pd.DataFrame):
    cols = {c.lower(): c for c in df.columns}
    required = [
        "stock name",
        "isin",
        "quantity",
        "average buy price per share",
        "total investment",
        "total cmp",
        "total p&l",
    ]
    for r in required:
        if r not in cols:
            return {"error": "Columns must match the Groww template exactly."}
    qcol = cols["quantity"]
    invcol = cols["total investment"]
    pnlcol = cols["total p&l"]

    df_use = df.copy()
    df_use["_qty"] = pd.to_numeric(df_use[qcol], errors="coerce").fillna(0.0)
    df_use["_inv"] = pd.to_numeric(df_use[invcol], errors="coerce").fillna(0.0)
    df_use["_pnl"] = pd.to_numeric(df_use[pnlcol], errors="coerce").fillna(0.0)

    total_inv = float(df_use["_inv"].sum())
    total_pnl = float(df_use["_pnl"].sum())
    positions = int((df_use["_qty"] > 0).sum())
    top = (
        df_use.sort_values("_inv", ascending=False)[[cols["stock name"], cols["quantity"], invcol, pnlcol]]
        .head(10)
        .rename(columns={cols["stock name"]: "Stock Name", cols["quantity"]: "Quantity"})
    )
    return {
        "total_investment": total_inv,
        "total_pnl": total_pnl,
        "positions": positions,
        "top_holdings": top,
    }

def render_reco_cards(recs: List[Dict], label: str):
    if not recs:
        st.info(f"🎯 Tap **Run Full Scan** to generate {label} recommendations")
        return
    df = pd.DataFrame(recs).sort_values("score", ascending=False).head(10)
    
    for idx, (_, rec) in enumerate(df.iterrows(), 1):
        cmp_ = rec.get('price', 0.0)
        tgt = rec.get('target_1', np.nan)
        diff = tgt - cmp_ if tgt is not None and not np.isnan(tgt) else np.nan
        profit_pct = (diff / cmp_ * 100) if cmp_ and not np.isnan(diff) else np.nan
        reason = rec.get('reasons', '')
        strength = rec.get('signal_strength', 'BUY')
        
        badge_class = 'signal-strong-buy' if strength == 'STRONG BUY' else 'signal-buy' if strength == 'BUY' else 'signal-hold'
        
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        
        # Header with rank, symbol and badge
        st.markdown(
            f"""<h3>
                <span style='color: #94a3b8; font-size: 0.9em; margin-right: 0.5rem;'>#{idx}</span>
                <span class='stock-symbol'>{rec.get('ticker','')}</span>
                <span class='{badge_class}'>{strength}</span>
            </h3>""",
            unsafe_allow_html=True
        )
        
        # Price and Target
        st.markdown(
            f"""<div class='value'>
                <span class='price-tag'>💰 ₹{cmp_:.2f}</span>
                <span class='target-tag'>🎯 Target: ₹{tgt:.2f}</span>
            </div>""",
            unsafe_allow_html=True
        )
        
        # Chips for metadata
        chip_html = "<div class='chip-row'>"
        chip_html += f"<span class='chip'>⭐ Score: {int(rec.get('score',0))}</span>"
        chip_html += f"<span class='chip'>⏱️ {rec.get('timeframe','')}</span>"
        chip_html += f"<span class='chip'>📊 {rec.get('period',label)}</span>"
        chip_html += "</div>"
        st.markdown(chip_html, unsafe_allow_html=True)
        
        # Profit box
        if not np.isnan(diff):
            profit_emoji = "📈" if diff > 0 else "📉"
            st.markdown(
                f"""<div class='profit-box'>
                    <div class='profit-label'>
                        {profit_emoji} Expected Profit: <strong>₹{diff:.2f}</strong> 
                        (<strong>{profit_pct:.2f}%</strong>)
                    </div>
                </div>""",
                unsafe_allow_html=True
            )
        
        # Reason box
        if reason:
            st.markdown(
                f"""<div class='reason-box'>
                    <div class='reason-text'>💡 <strong>Analysis:</strong> {reason}</div>
                </div>""",
                unsafe_allow_html=True
            )
        
        st.markdown("</div>", unsafe_allow_html=True)

NAV_PAGES = [
    "🔥 Top Stocks",
    "🌙 BTST",
    "⚡ Intraday",
    "📆 Weekly",
    "📅 Monthly",
    "📊 Groww",
    "🤝 Dhan",
    "⚙️ Configuration",
]

def sidebar_nav():
    with st.sidebar:
        st.markdown("### 📂 Navigation")
        st.markdown("---")
        
        for page in NAV_PAGES:
            if st.button(page, key=f"nav_{page}", use_container_width=True):
                st.session_state['current_page'] = page
                st.rerun()
        
        st.markdown("---")
        st.caption("🤖 AI Stock Analysis Bot")
        st.caption(f"📦 Tracking {len(STOCK_UNIVERSE)} stocks")

def main():
    st.markdown("""
    <div class='main-header'>
        <h1>🚀 AI Stock Analysis Bot</h1>
        <p>✨ Multi-timeframe Scanner • 📊 Portfolio Analyzer • 🤖 Smart Recommendations</p>
        <div class="status-badge">🟢 Live • IST</div>
    </div>
    """, unsafe_allow_html=True)

    auto_scan_if_due()
    sidebar_nav()

    c1, c2, c3 = st.columns([3, 1.5, 1])
    with c1:
        if st.button("🚀 Run Full Scan", type="primary", use_container_width=True):
            run_analysis()
            st.success("✅ Scan completed!")
    with c2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    with c3:
        st.metric("📦", len(STOCK_UNIVERSE))

    if st.session_state['last_analysis_time']:
        st.caption(f"⏱️ Last Scan: {st.session_state['last_analysis_time'].strftime('%d-%m-%Y %I:%M %p')}")

    st.markdown("---")

    page = st.session_state['current_page']

    if page == "🔥 Top Stocks":
        st.subheader("🔥 Top 10 Stocks Across All Setups")
        st.caption("💎 Best opportunities ranked by technical score")
        top_recs = get_top_stocks(limit=10)
        render_reco_cards(top_recs, "Top")
        
    elif page == "🌙 BTST":
        st.subheader("🌙 BTST Opportunities")
        st.caption("📈 Buy Today, Sell Tomorrow setups")
        recs = st.session_state['recommendations'].get('BTST', [])
        for r in recs:
            r.setdefault("period", "BTST")
        render_reco_cards(recs, "BTST")
        
    elif page == "⚡ Intraday":
        st.subheader("⚡ Intraday Signals")
        st.caption("🎯 Same-day trading opportunities")
        recs = st.session_state['recommendations'].get('Intraday', [])
        for r in recs:
            r.setdefault("period", "Intraday")
        render_reco_cards(recs, "Intraday")
        
    elif page == "📆 Weekly":
        st.subheader("📆 Weekly Swing Ideas")
        st.caption("📊 Week-long position trades")
        recs = st.session_state['recommendations'].get('Weekly', [])
        for r in recs:
            r.setdefault("period", "Weekly")
        render_reco_cards(recs, "Weekly")
        
    elif page == "📅 Monthly":
        st.subheader("📅 Monthly Position Trades")
        st.caption("🎪 Long-term swing opportunities")
        recs = st.session_state['recommendations'].get('Monthly', [])
        for r in recs:
            r.setdefault("period", "Monthly")
        render_reco_cards(recs, "Monthly")
        
    elif page == "📊 Groww":
        st.subheader("📊 Groww Portfolio Analysis")
        with st.expander("📋 CSV Template Format", expanded=False):
            st.code(
                "Stock Name\tISIN\tQuantity\tAverage buy price per share\t"
                "Total Investment\tTotal CMP\tTOTAL P&L",
                language="text"
            )
        
        uploaded = st.file_uploader(
            "📂 Upload Groww Portfolio CSV", type=["csv"], key="groww_csv_upload"
        )
        
        if uploaded is not None:
            try:
                df_up = pd.read_csv(uploaded, sep=None, engine="python")
                st.write("👀 Preview:")
                st.dataframe(df_up.head(), use_container_width=True, hide_index=True)
                
                analysis = analyze_groww_portfolio(df_up)
                if "error" in analysis:
                    st.error(f"❌ {analysis['error']}")
                else:
                    st.markdown("##### 📊 Portfolio Summary")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("💰 Total Investment", f"₹{analysis['total_investment']:,.2f}")
                    with c2:
                        st.metric("📈 Total P&L", f"₹{analysis['total_pnl']:,.2f}")
                    with c3:
                        st.metric("🎯 Positions", analysis["positions"])
                    
                    st.markdown("##### 🏆 Top Holdings")
                    st.dataframe(analysis["top_holdings"], use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"❌ Error: {e}")
        else:
            st.info("📤 Upload your Groww CSV to see analysis")
            
    elif page == "🤝 Dhan":
        st.subheader("🤝 Dhan Portfolio")
        
        with st.expander("🔑 Connection Settings", expanded=True):
            dhan_store = localS.getItem("dhan_config") or {}
            if dhan_store:
                st.session_state['dhan_client_id'] = dhan_store.get("client_id", st.session_state['dhan_client_id'])

            dhan_enable = st.checkbox("✅ Enable Dhan", value=st.session_state.get('dhan_enabled', False))
            st.session_state['dhan_enabled'] = dhan_enable
            
            if dhan_enable:
                dcid = st.text_input("🆔 Client ID", value=st.session_state.get('dhan_client_id', ''), key="dhan_client_main")
                dtoken = st.text_input("🔐 Access Token", value=st.session_state.get('dhan_access_token', ''), type="password", key="dhan_token_main")
                st.session_state['dhan_client_id'] = dcid
                st.session_state['dhan_access_token'] = dtoken
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("🔑 Connect", use_container_width=True, key="btn_connect_dhan_main"):
                        dhan_login(dcid, dtoken)
                        localS.setItem("dhan_config", {"client_id": dcid})
                        st.rerun()
                with c2:
                    if st.button("🚪 Logout", use_container_width=True, key="btn_logout_dhan_main"):
                        dhan_logout()
                        st.rerun()
                
                st.caption(st.session_state['dhan_login_msg'])

        df_port, total_pnl = format_dhan_portfolio_table()
        if df_port is None or df_port.empty:
            st.info("📭 No holdings found. Connect your account above.")
        else:
            c1, c2 = st.columns([3, 1])
            with c1:
                st.dataframe(df_port, use_container_width=True, hide_index=True)
            with c2:
                pnl_emoji = "📈" if total_pnl >= 0 else "📉"
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.markdown(f"<h3>{pnl_emoji} Total P&L</h3>", unsafe_allow_html=True)
                pnl_class = 'profit' if total_pnl >= 0 else 'loss'
                st.markdown(f"<div class='value {pnl_class}'>₹{total_pnl:,.2f}</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
    elif page == "⚙️ Configuration":
        st.subheader("⚙️ App Configuration")

        with st.expander("📱 Telegram Notifications", expanded=True):
            tg_store = localS.getItem("telegram_config") or {}
            if tg_store:
                st.session_state['telegram_bot_token'] = tg_store.get("bot_token", st.session_state['telegram_bot_token'])
                st.session_state['telegram_chat_id'] = tg_store.get("chat_id", st.session_state['telegram_chat_id'])

            notify_toggle = st.checkbox("✅ Enable P&L notifications", value=st.session_state['notify_enabled'], key="cfg_notify_toggle")
            st.session_state['notify_enabled'] = notify_toggle
            
            tg_token = st.text_input("🤖 Bot Token", value=st.session_state['telegram_bot_token'], key="cfg_tg_token")
            tg_chat = st.text_input("💬 Chat ID", value=st.session_state['telegram_chat_id'], key="cfg_tg_chat")
            st.session_state['telegram_bot_token'] = tg_token
            st.session_state['telegram_chat_id'] = tg_chat

            c1, c2 = st.columns(2)
            with c1:
                if st.button("💾 Save Settings", use_container_width=True, key="btn_save_settings"):
                    save_config_from_state()
                    localS.setItem("telegram_config", {"bot_token": tg_token, "chat_id": tg_chat})
                    st.success("✅ Saved!")
            with c2:
                if st.button("📤 Test Message", use_container_width=True, key="btn_send_pnl"):
                    text = "📊 Test message from AI Stock Bot"
                    tg_resp = send_telegram_message(text) if tg_token and tg_chat else {"info": "Not configured"}
                    st.success("✅ Sent!")
                    st.json(tg_resp)

        with st.expander("📊 Nifty 200 Universe", expanded=False):
            if st.button("🔁 Regenerate CSV", use_container_width=True, key="btn_regen_nifty"):
                ok = regenerate_nifty200_csv_from_master()
                if ok:
                    st.success("✅ Regenerated successfully!")
                else:
                    st.error("❌ Failed to regenerate")

if __name__ == "__main__":
    main()
