import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pulp
import io
import datetime
import re
import json
import urllib.error
import urllib.request
import streamlit.components.v1 as components
from supabase import create_client, Client

# ==========================================
# ๐” SUPABASE CONNECTION INITIALIZATION
# ==========================================
# เธฅเนเธฒเธเธเนเธญเธเธงเนเธฒเธเธเนเธฒเธข-เธเธงเธฒเธญเธญเธเธ”เนเธงเธข .strip() เธเนเธญเธเธเธฑเธเธเนเธญเธเธดเธ”เธเธฅเธฒเธ”เน€เธเนเธ•เน€เธงเธดเธฃเนเธเธซเธฒเน€เธชเนเธเธ—เธฒเธเนเธกเนเน€เธเธญ (Name or service not known)
SUPABASE_URL = "https://nxyncxqbtntlpzqessou.supabase.co".strip()
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im54eW5jeHFidG50bHB6cWVzc291Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA5NDQ2MjYsImV4cCI6MjA5NjUyMDYyNn0.JI4UcB-iVVsD4QLWC0IvOijApWG5A7q3hv6ORxtcXtI".strip()
APP_URL = "https://poultry-enterprise-zgl4fdafvrzk6rmgmearig.streamlit.app".strip()

PASSWORD_RESET_REDIRECT_URL = st.secrets.get("PASSWORD_RESET_REDIRECT_URL", f"{APP_URL}?auth_action=reset_password")

if SUPABASE_URL:
    PASSWORD_RESET_FUNCTION_URL = st.secrets.get("PASSWORD_RESET_FUNCTION_URL", f"{SUPABASE_URL}/functions/v1/reset-password-by-phone")
else:
    PASSWORD_RESET_FUNCTION_URL = None

@st.cache_resource
def init_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("โ เธ•เธฃเธงเธเธเธเธเนเธญเธเธดเธ”เธเธฅเธฒเธ”: เธเธฃเธธเธ“เธฒเธเธฃเธญเธ SUPABASE_URL เนเธฅเธฐ SUPABASE_KEY เนเธซเนเธ–เธนเธเธ•เนเธญเธเธชเธกเธเธนเธฃเธ“เน")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = init_supabase()
except Exception as e:
    error_msg = str(e).lower()
    if "name or service not known" in error_msg or "temporary failure in name resolution" in error_msg:
        st.error("๐ [เธเนเธญเธเธดเธ”เธเธฅเธฒเธ”เธฃเธฐเธเธเน€เธเธฃเธทเธญเธเนเธฒเธข]: เนเธกเนเธชเธฒเธกเธฒเธฃเธ–เธเนเธเธซเธฒเธ—เธตเนเธญเธขเธนเนเธเธญเธเน€เธเธดเธฃเนเธเน€เธงเธญเธฃเนเธเธฒเธเธเนเธญเธกเธนเธฅเนเธ”เน (Name or service not known) เธเธฃเธธเธ“เธฒเธ•เธฃเธงเธเธชเธญเธเธญเธดเธเน€เธ—เธญเธฃเนเน€เธเนเธ•เธเธญเธเน€เธเธฃเธทเนเธญเธ เธซเธฃเธทเธญ Reboot App เธเธเธฃเธฐเธเธเธเธฅเธฒเธงเธ”เน")
    else:
        st.error(f"โ เนเธกเนเธชเธฒเธกเธฒเธฃเธ–เน€เธเธทเนเธญเธกเธ•เนเธญเธเธฑเธเน€เธเธดเธฃเนเธเน€เธงเธญเธฃเน Supabase เนเธ”เนเธ•เธฑเนเธเนเธ•เนเน€เธฃเธดเนเธกเธ•เนเธ: {e}")

# ==========================================
# ๐”ฑ 1. INITIAL APP CONFIGURATION & THEME
# ==========================================
st.set_page_config(
    page_title="เธฃเธฐเธเธเธเธณเธเธงเธ“เนเธ เธเธเธฒเธเธฒเธฃเนเธฅเธฐเธเธฑเธ”เธเธฒเธฃเธชเธฒเธขเธเธฑเธเธเธธเนเนเธเนเนเธเน (Layer Nutrition Studio Pro)", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(
    """
    <style>
    [data-testid="collapsedControl"] { display: none; }
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), 
                          url("https://images.unsplash.com/photo-1548550023-2bdb3c5beed7?q=80&w=1920");
        background-size: cover; background-position: center;
        background-repeat: no-repeat; background-attachment: fixed;
    }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, [data-testid="stHeader"] {
        color: #ffffff !important;
        text-shadow: 2px 2px 5px rgba(0, 0, 0, 0.95) !important;
    }
    
    div[data-testid="stSelectbox"] > label {
        font-size: 1.15rem !important;
        font-weight: 800 !important;
        color: #ffb703 !important;
        margin-bottom: 6px !important;
        display: block;
    }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] {
        font-size: 1.1rem !important; 
        font-weight: bold !important;
        background-color: rgba(26, 26, 26, 0.9) !important;
        border: 2px solid #ffb703 !important; 
        border-radius: 10px !important;
        color: white !important;
    }
    
    .divider-line {
        border-top: 1px solid rgba(255, 255, 255, 0.18);
        margin: 22px 0;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(255, 255, 255, 0.1) !important;
        padding: 8px; border-radius: 10px; backdrop-filter: blur(10px);
    }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-weight: bold !important; font-size:1.05rem !important; }
    .content-card {
        background-color: rgba(0, 0, 0, 0.90) !important; padding: 30px;
        border-radius: 18px; border: 1px solid rgba(255, 255, 255, 0.18);
        backdrop-filter: blur(10px); margin-bottom: 25px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem !important; color: #ffb703 !important;
    }
    [data-testid="stDataFrame"] { background-color: rgba(255,255,255,0.95) !important; border-radius: 8px; padding: 5px; }
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================================
# ๐” 2. SECURITY & STATE INITIALIZATION
# ==========================================
states = {
    "is_authenticated": False,
    "auth_page_mode": "login",
    "user_role": "user",
    "user_email": "",
    "current_user_key": "",  # เน€เธเนเธเธเธฑเธเธเธตเธญเธตเน€เธกเธฅเน€เธเธทเนเธญเนเธเนเนเธเนเธเนเธขเธเธ•เธฑเธงเนเธเธฃเธ•เธฑเธงเธกเธฑเธเธเธเธเธฅเธฒเธงเธ”เน
    "saved_formulas": [],
    "daily_logs": [],
    "current_weights": {},
    "db_ingredients": {}  
}

for key, value in states.items():
    if key not in st.session_state:
        st.session_state[key] = value

def check_password_strength(password):
    if len(password) < 8: return False, "โ เธฃเธซเธฑเธชเธเนเธฒเธเธ•เนเธญเธเธกเธตเธเธงเธฒเธกเธขเธฒเธงเธญเธขเนเธฒเธเธเนเธญเธข 8 เธ•เธฑเธงเธญเธฑเธเธฉเธฃ"
    if not re.search("[a-z]", password): return False, "โ เธฃเธซเธฑเธชเธเนเธฒเธเธ•เนเธญเธเธกเธตเธญเธฑเธเธฉเธฃเธเธดเธกเธเนเน€เธฅเนเธ (a-z) เธญเธขเนเธฒเธเธเนเธญเธข 1 เธ•เธฑเธง"
    if not re.search("[A-Z]", password): return False, "โ เธฃเธซเธฑเธชเธเนเธฒเธเธ•เนเธญเธเธกเธตเธญเธฑเธเธฉเธฃเธเธดเธกเธเนเนเธซเธเน (A-Z) เธญเธขเนเธฒเธเธเนเธญเธข 1 เธ•เธฑเธง"
    if not re.search("[0-9]", password): return False, "โ เธฃเธซเธฑเธชเธเนเธฒเธเธ•เนเธญเธเธกเธตเธ•เธฑเธงเน€เธฅเธ (0-9) เธญเธขเนเธฒเธเธเนเธญเธข 1 เธ•เธฑเธง"
    if not re.search("[_@$!%*#?&.]", password): return False, "โ เธฃเธซเธฑเธชเธเนเธฒเธเธ•เนเธญเธเธกเธตเธญเธฑเธเธเธฃเธฐเธเธดเน€เธจเธฉเธญเธขเนเธฒเธเธเนเธญเธข 1 เธ•เธฑเธง"
    return True, "๐ข เธฃเธซเธฑเธชเธเนเธฒเธเธกเธตเธเธงเธฒเธกเธเธฅเธญเธ”เธ เธฑเธขเธชเธนเธเธ•เธฒเธกเธกเธฒเธ•เธฃเธเธฒเธ"

def reset_password_with_email_and_phone(email, phone, new_password):
    payload = json.dumps({
        "email": email.strip(),
        "phone": phone.strip(),
        "new_password": new_password,
    }).encode("utf-8")
    request = urllib.request.Request(
        PASSWORD_RESET_FUNCTION_URL,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "apikey": SUPABASE_KEY,
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            result = json.loads(error.read().decode("utf-8"))
        except Exception:
            result = {"error": str(error)}
        raise Exception(result.get("error", "เนเธกเนเธชเธฒเธกเธฒเธฃเธ–เธฃเธตเน€เธเนเธ•เธฃเธซเธฑเธชเธเนเธฒเธเนเธ”เน"))
    except Exception as error:
        raise Exception(f"เน€เธเธทเนเธญเธกเธ•เนเธญเธฃเธฐเธเธเธฃเธตเน€เธเนเธ•เธฃเธซเธฑเธชเธเนเธฒเธเนเธกเนเนเธ”เน: {error}")

    if not result.get("ok"):
        raise Exception(result.get("error", "เนเธกเนเธชเธฒเธกเธฒเธฃเธ–เธฃเธตเน€เธเนเธ•เธฃเธซเธฑเธชเธเนเธฒเธเนเธ”เน"))
    return result

# --- เธเธณเธซเธเธ”เธเนเธฒเน€เธฃเธดเนเธกเธ•เนเธเน€เธเนเธ List/Dict เธงเนเธฒเธ เน€เธเธทเนเธญเธฃเธญเธเธฒเธฃเนเธซเธฅเธ”เธเธฒเธ Database 100% ---
if "db_groups" not in st.session_state:
    st.session_state.db_groups = []

if "db_breeds" not in st.session_state:
    st.session_state.db_breeds = []

if "db_targets" not in st.session_state:
    st.session_state.db_targets = {}

if "db_nutrient_keys" not in st.session_state:
    st.session_state.db_nutrient_keys = {
        "price": {"label": "เธฃเธฒเธเธฒเธเธฅเธฒเธ (เธเธฒเธ—/เธเธ.)", "step": 0.1, "default": 0.0},
        "protein": {"label": "เนเธเธฃเธ•เธตเธเธ”เธดเธ (% CP)", "step": 0.1, "default": 0.0},
        "me": {"label": "เธเธฅเธฑเธเธเธฒเธเนเธเนเธเธฃเธฐเนเธขเธเธเนเนเธ”เน (ME kcal/kg)", "step": 10.0, "default": 0.0},
        "calcium": {"label": "เนเธเธฅเน€เธเธตเธขเธก (% Ca)", "step": 0.01, "default": 0.0},
        "phos": {"label": "เธเธญเธชเธเธญเธฃเธฑเธชเน€เธเนเธเธเธฃเธฐเนเธขเธเธเน (% Avail. P)", "step": 0.01, "default": 0.0},
        "lysine": {"label": "เธญเธฐเธกเธดเนเธ เนเธฅเธเธตเธ (% Lys)", "step": 0.01, "default": 0.0},
        "methionine": {"label": "เธญเธฐเธกเธดเนเธ เน€เธกเธ—เนเธเนเธญเธเธตเธ (% Met)", "step": 0.01, "default": 0.0},
        "fiber": {"label": "เน€เธขเธทเนเธญเนเธข (% Fiber)", "step": 0.1, "default": 0.0},
    }

FALLBACK_INGREDIENTS = [
    {"id": 5, "name": "เธเนเธฒเธงเนเธเธ”เธเธ” (Yellow Corn)", "price": 12.50, "protein": 8.00, "me": 3370.0, "calcium": 0.02, "phos": 0.08, "owner_email": "system_default", "lysine": 0.24, "methionine": 0.18, "fiber": 2.00, "min_limit": 30.0, "max_limit": 70.0},
    {"id": 6, "name": "เธเธฒเธเธ–เธฑเนเธงเน€เธซเธฅเธทเธญเธ (Soybean Meal 44%)", "price": 22.00, "protein": 44.00, "me": 2230.0, "calcium": 0.29, "phos": 0.20, "owner_email": "system_default", "lysine": 2.69, "methionine": 0.62, "fiber": 6.00, "min_limit": 10.0, "max_limit": 35.0},
    {"id": 7, "name": "เธฃเธณเธฅเธฐเน€เธญเธตเธขเธ” (Rice Bran)", "price": 10.50, "protein": 12.00, "me": 2860.0, "calcium": 0.05, "phos": 0.15, "owner_email": "system_default", "lysine": 0.54, "methionine": 0.24, "fiber": 6.50, "min_limit": 0.0, "max_limit": 20.0},
    {"id": 8, "name": "เธเธฅเธฒเธขเธเนเธฒเธง (Broken Rice)", "price": 14.00, "protein": 7.50, "me": 3400.0, "calcium": 0.03, "phos": 0.04, "owner_email": "system_default", "lysine": 0.20, "methionine": 0.15, "fiber": 1.00, "min_limit": 0.0, "max_limit": 30.0},
    {"id": 9, "name": "เธเธฅเธฒเธเนเธ (Fish Meal 60%)", "price": 35.00, "protein": 60.00, "me": 2900.0, "calcium": 5.00, "phos": 2.80, "owner_email": "system_default", "lysine": 4.50, "methionine": 1.60, "fiber": 1.00, "min_limit": 2.0, "max_limit": 8.0}
]

DEFAULT_INGREDIENT_OWNER = "system_default"
MASTER_TABLE_CANDIDATES = {
    "groups": ["db_groups", "groups"],
    "breeds": ["db_breeds", "breeds"],
    "targets": ["db_targets", "targets"],
}

def get_ingredient_owner_for_write(existing_ingredient=None):
    if isinstance(existing_ingredient, dict) and existing_ingredient.get("owner_email"):
        return existing_ingredient["owner_email"]
    if st.session_state.get("user_role") == "admin":
        return DEFAULT_INGREDIENT_OWNER
    return st.session_state.get("current_user_key") or DEFAULT_INGREDIENT_OWNER

def fetch_first_available_table(table_key):
    if "master_load_debug" not in st.session_state:
        st.session_state.master_load_debug = []

    for table_name in MASTER_TABLE_CANDIDATES.get(table_key, []):
        try:
            try:
                response = supabase.table(table_name).select("*").order("id").execute()
            except Exception:
                response = supabase.table(table_name).select("*").execute()
            if response.data:
                st.session_state[f"{table_key}_table_source"] = table_name
                st.session_state.master_load_debug.append(
                    {"table_key": table_key, "table_name": table_name, "status": "loaded", "rows": len(response.data)}
                )
                return response.data
        except Exception as table_err:
            st.session_state.master_load_debug.append(
                {"table_key": table_key, "table_name": table_name, "status": "error", "rows": 0, "error": str(table_err)}
            )
            continue
    st.session_state[f"{table_key}_table_source"] = ""
    return []

def fetch_master_data_from_supabase():
    """ เธ”เธถเธเธเนเธญเธกเธนเธฅเธเธฒเธ Database 100% เธชเธญเธ”เธเธฅเนเธญเธเธ•เธฒเธกเธเธทเนเธญเธเธญเธฅเธฑเธกเธเนเธเธฃเธดเธเนเธ Supabase """
    try:
        st.session_state.master_load_debug = []
        
        # 1. เธ”เธถเธเธเนเธญเธกเธนเธฅเธเธฅเธธเนเธกเธชเธฒเธขเธเธฑเธเธเธธเน (db_groups)
        groups = fetch_first_available_table("groups")
        if groups:
            st.session_state.db_groups = [
                {
                    "id": item.get("id"),
                    "group_name": item.get("group_name"),
                    "bg_color": item.get("bg_color", "#0284c7"),
                }
                for item in groups if item.get("group_name")
            ]

        # 2. เธ”เธถเธเธเนเธญเธกเธนเธฅเธชเธฒเธขเธเธฑเธเธเธธเน (db_breeds)
        breeds = fetch_first_available_table("breeds")
        if breeds:
            st.session_state.db_breeds = [
                {
                    "id": item.get("id"),
                    "group_name": item.get("group_name", ""),
                    "breed_name": item.get("breed_name"),
                    "egg_color": item.get("egg_color", ""),
                    "default_feed": float(item.get("default_feed", 114.0)),
                }
                for item in breeds if item.get("breed_name")
            ]

        # 3. เธ”เธถเธเธเนเธญเธกเธนเธฅเธเนเธงเธเธญเธฒเธขเธธ/เธฃเธฐเธขเธฐเธเธฒเธฃเน€เธเธฃเธดเธเน€เธ•เธดเธเนเธ• (db_targets)
        targets = fetch_first_available_table("targets")
        if targets:
            normalized_targets = {}
            for item in targets:
                stage_key = item.get("stage_key")
                if stage_key:
                    normalized_item = item.copy()
                    normalized_item["stage_key"] = stage_key
                    normalized_item["stage_name"] = item.get("stage_name")
                    normalized_targets[stage_key] = normalized_item
            st.session_state.db_targets = normalized_targets

    except Exception as e:
        st.error(f"เน€เธเธดเธ”เธเนเธญเธเธดเธ”เธเธฅเธฒเธ”เนเธเธเธฒเธฃเนเธซเธฅเธ”เธเนเธญเธกเธนเธฅเธเธฒเธ Database: {e}")

def safe_float(value, default=0.0):
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def normalize_phase_name(value):
    text = str(value or "").strip()
    text = text.split("(")[0].strip()
    text = re.sub(r"\s+", "", text)
    text = text.replace("เธฃเธฐเธขเธฐเธฅเธนเธเนเธเนเนเธเน", "เธฃเธฐเธขเธฐเธฅเธนเธเนเธเน")
    return text

PHASE_NAME_BY_STAGE_KEY = {
    "starter": "เธฃเธฐเธขเธฐเธฅเธนเธเนเธเน",
    "grower": "เธฃเธฐเธขเธฐเนเธเนเธฃเธธเนเธ",
    "developer": "เธฃเธฐเธขเธฐเนเธเนเธชเธฒเธงเธเธฑเธ’เธเธฒเนเธเธฃเธเธชเธฃเนเธฒเธ",
    "prelay": "เธฃเธฐเธขเธฐเธเนเธญเธเนเธซเนเนเธเน",
    "layer_phase_1": "เธฃเธฐเธขเธฐเนเธเนเธเธตเธ",
    "layer_phase_2": "เธฃเธฐเธขเธฐเนเธเนเธเธเธ•เธฑเธง",
    "late_layer": "เธฃเธฐเธขเธฐเธ—เนเธฒเธขเธฃเธธเนเธ/เน€เธเธฅเธทเธญเธเธเธฒเธ",
}

def fetch_nutrition_standards(breed_id, stage_key, phase_name=None):
    """ 
    เธ”เธถเธเธกเธฒเธ•เธฃเธเธฒเธเนเธ เธเธเธฒเธเธฒเธฃเนเธเนเนเธเนเธฃเธฒเธขเธชเธฒเธขเธเธฑเธเธเธธเนเธ•เธฃเธเธเธฒเธเธเธฒเธเธเนเธญเธกเธนเธฅ 100%
    เน€เธเธทเนเธญเธเธณเนเธเธเนเธญเธเน€เธเนเธ Constraints เนเธซเนเธเธฑเธเธ•เธฑเธง Solver
    """
    try:
        # เธ”เธถเธเธ”เนเธงเธข breed_id เธเธถเนเธเน€เธเนเธเธเธญเธฅเธฑเธกเธเนเธญเธฑเธเธเธคเธฉ เนเธฅเนเธงเน€เธฅเธทเธญเธเนเธ–เธงเธ”เนเธงเธข stage_key เนเธ Python
        # เน€เธเธทเนเธญเนเธกเนเธ•เนเธญเธเธเธถเนเธเธเธฒเธฃเธเนเธเธซเธฒเธเนเธญเธเธงเธฒเธกเธ เธฒเธฉเธฒเนเธ—เธขเธ—เธตเนเธญเธฒเธเธกเธตเธฃเธนเธเนเธเธเธ•เนเธฒเธเธเธฑเธ
        res = supabase.table("เธกเธฒเธ•เธฃเธเธฒเธเนเธ เธเธเธฒเธเธฒเธฃเนเธเนเนเธเน") \
            .select("*") \
            .eq("breed_id", int(breed_id)) \
            .execute()
            
        if res.data:
            expected_stage_key = str(stage_key or "").strip()
            expected_phase = normalize_phase_name(
                phase_name or PHASE_NAME_BY_STAGE_KEY.get(expected_stage_key, "")
            )

            data = None
            if expected_stage_key:
                data = next(
                    (
                        row for row in res.data
                        if str(row.get("stage_key") or "").strip() == expected_stage_key
                    ),
                    None,
                )

            if not data and expected_phase:
                data = next(
                    (
                        row for row in res.data
                        if normalize_phase_name(row.get("เธเนเธงเธเธญเธฒเธขเธธเธเธฒเธฃเน€เธฅเธตเนเธขเธ_phase_name")) == expected_phase
                    ),
                    None,
                )

            if not data:
                return None

            return {
                "min_protein": safe_float(data.get("เนเธเธฃเธ•เธตเธเธ•เนเธณเธชเธธเธ”_min_protein"), 0.0),
                "min_me": safe_float(data.get("เธเธฅเธฑเธเธเธฒเธเธ•เนเธณเธชเธธเธ”_min_me"), 0.0),
                "min_calcium": safe_float(data.get("เนเธเธฅเน€เธเธตเธขเธกเธ•เนเธณเธชเธธเธ”_min_calcium"), 0.0),
                "max_calcium": safe_float(data.get("เนเธเธฅเน€เธเธตเธขเธกเธชเธนเธเธชเธธเธ”_max_calcium"), 5.5),
                "min_phosphorus": safe_float(data.get("เธเธญเธชเธเธญเธฃเธฑเธชเธ•เนเธณเธชเธธเธ”_min_phosphorus"), 0.0),
                "min_lysine": safe_float(data.get("เนเธฅเธเธตเธเธ•เนเธณเธชเธธเธ”_min_lysine"), 0.0),
                "min_methionine": safe_float(data.get("เน€เธกเธ—เธดเนเธญเธเธตเธเธ•เนเธณเธชเธธเธ”_min_methionine"), 0.0),
                "max_fiber": 5.0 # เธเนเธฒเธ•เธฑเนเธเธ•เนเธเธชเธณเธซเธฃเธฑเธเน€เธขเธทเนเธญเนเธขเธชเธนเธเธชเธธเธ”
            }
    except Exception as e:
        st.error(f"โ ๏ธ เน€เธเธดเธ”เธเนเธญเธเธดเธ”เธเธฅเธฒเธ”เนเธเธเธฒเธฃเธ”เธถเธเธกเธฒเธ•เธฃเธเธฒเธเนเธ เธเธเธฒเธเธฒเธฃเธเธฒเธ Supabase: {e}")
    return None

def fetch_ingredients_from_supabase():
    try:
        rows = []
        if st.session_state.is_authenticated and st.session_state.current_user_key:
            user_email = st.session_state.current_user_key
            default_response = supabase.table("ingredients").select("*").eq("owner_email", DEFAULT_INGREDIENT_OWNER).execute()
            user_response = supabase.table("ingredients").select("*").eq("owner_email", user_email).execute()
            rows.extend(default_response.data or [])
            rows.extend(user_response.data or [])
        else:
            response = supabase.table("ingredients").select("*").execute()
            rows = response.data or []
            
        if rows:
            ingredients_dict = {item["name"]: item for item in rows}
            st.session_state.db_ingredients = ingredients_dict
            return ingredients_dict
        else:
            fallback_dict = {item["name"]: item for item in FALLBACK_INGREDIENTS}
            st.session_state.db_ingredients = fallback_dict
            return fallback_dict
    except Exception as e:
        fallback_dict = {item["name"]: item for item in FALLBACK_INGREDIENTS}
        st.session_state.db_ingredients = fallback_dict
        return fallback_dict

# =========================================================================
# ๐” FUNCTIONS: เธเธฑเธ”เธเธฒเธฃเธเนเธญเธกเธนเธฅเธชเธนเธ•เธฃเธญเธฒเธซเธฒเธฃ เนเธฅเธฐเธเธฑเธเธ—เธถเธเธเธฒเธฃเนเธกเธฃเธฒเธขเธงเธฑเธเธ•เธฑเธงเนเธเธฃเธ•เธฑเธงเธกเธฑเธ
# =========================================================================

def fetch_saved_formulas_from_supabase():
    """เธ”เธถเธเธชเธนเธ•เธฃเธญเธฒเธซเธฒเธฃเน€เธเธเธฒเธฐเธเธญเธเธเธนเนเนเธเนเธเธฒเธเธ—เธตเนเธฅเนเธญเธเธญเธดเธเธญเธขเธนเนเธเธฑเธเธเธธเธเธฑเธ"""
    try:
        if st.session_state.is_authenticated and st.session_state.current_user_key:
            user_email = st.session_state.current_user_key
            response = supabase.table("saved_formulas").select("*").eq("owner_email", user_email).execute()
            if response.data:
                st.session_state.saved_formulas = response.data
                return response.data
        st.session_state.saved_formulas = []
        return []
    except Exception as e:
        st.warning(f"โ ๏ธ เนเธกเนเธชเธฒเธกเธฒเธฃเธ–เธ”เธถเธเธชเธนเธ•เธฃเธญเธฒเธซเธฒเธฃเธชเนเธงเธเธ•เธฑเธงเธเธฒเธเธเธฅเธฒเธงเธ”เนเนเธ”เน: {e}")
        return []

def save_formula_to_supabase(formula_data):
    """เธเธฑเธเธ—เธถเธเธชเธนเธ•เธฃเธญเธฒเธซเธฒเธฃเนเธซเธกเน เธเธนเธเน€เธเนเธฒเธเธญเธเธ”เนเธงเธข owner_email เธ—เธธเธเธเธฃเธฑเนเธ"""
    try:
        if st.session_state.is_authenticated and st.session_state.current_user_key:
            formula_data["owner_email"] = st.session_state.current_user_key
            supabase.table("saved_formulas").insert(formula_data).execute()
            st.success("๐ เธเธฑเธเธ—เธถเธเธชเธนเธ•เธฃเธญเธฒเธซเธฒเธฃเธฅเธเธเธทเนเธเธ—เธตเนเธชเนเธงเธเธ•เธฑเธงเธเธญเธเธเธธเธ“เน€เธฃเธตเธขเธเธฃเนเธญเธขเนเธฅเนเธง!")
            fetch_saved_formulas_from_supabase()
            return True
        else:
            st.error("โ เธเธฃเธธเธ“เธฒเน€เธเนเธฒเธชเธนเนเธฃเธฐเธเธเธเนเธญเธเธ—เธณเธเธฒเธฃเธเธฑเธเธ—เธถเธเธเนเธญเธกเธนเธฅ")
            return False
    except Exception as e:
        st.error(f"โ เนเธกเนเธชเธฒเธกเธฒเธฃเธ–เธเธฑเธเธ—เธถเธเธชเธนเธ•เธฃเธฅเธเธเธฅเธฒเธงเธ”เนเนเธ”เน: {e}")
        return False

def fetch_daily_logs_from_supabase():
    """เธ”เธถเธเธชเธกเธธเธ”เธเธฑเธเธ—เธถเธเธเธดเธเธเธฃเธฃเธกเธเธฒเธฃเนเธกเธฃเธฒเธขเธงเธฑเธเน€เธเธเธฒเธฐเธเธญเธเธ•เธเน€เธญเธ"""
    try:
        if st.session_state.is_authenticated and st.session_state.current_user_key:
            user_email = st.session_state.current_user_key
            response = supabase.table("daily_logs").select("*").eq("owner_email", user_email).order("date").execute()
            if response.data:
                st.session_state.daily_logs = response.data
                return response.data
        st.session_state.daily_logs = []
        return []
    except Exception as e:
        st.warning(f"โ ๏ธ เนเธกเนเธชเธฒเธกเธฒเธฃเธ–เธ”เธถเธเธเธฑเธเธ—เธถเธเธเธดเธเธเธฃเธฃเธกเธเธฒเธฃเนเธกเธเธฒเธเธเธฅเธฒเธงเธ”เนเนเธ”เน: {e}")
        return []

def save_daily_log_to_supabase(log_data):
    """เธเธฑเธเธ—เธถเธเธเนเธญเธกเธนเธฅเธเธดเธเธเธฃเธฃเธกเธเธฒเธฃเนเธกเธเธฃเธฐเธเธณเธงเธฑเธ เธเธนเธเน€เธเนเธฒเธเธฑเธเธฃเธฐเธเธเธเธฑเธเธเธตเธเธนเนเนเธเนเธเธฃเธดเธ"""
    try:
        if st.session_state.is_authenticated and st.session_state.current_user_key:
            log_data["owner_email"] = st.session_state.current_user_key
            supabase.table("daily_logs").insert(log_data).execute()
            st.success("๐ เธเธฑเธเธ—เธถเธเธเธฃเธฐเธงเธฑเธ•เธดเธเธดเธเธเธฃเธฃเธกเธเธฒเธฃเนเธกเธเธฃเธฐเธเธณเธงเธฑเธเธชเธณเน€เธฃเนเธ!")
            fetch_daily_logs_from_supabase()
            return True
        else:
            st.error("โ เธเธฃเธธเธ“เธฒเน€เธเนเธฒเธชเธนเนเธฃเธฐเธเธเธเนเธญเธเธ—เธณเธเธฒเธฃเธเธฑเธเธ—เธถเธเธเนเธญเธกเธนเธฅ")
            return False
    except Exception as e:
        st.error(f"โ เนเธกเนเธชเธฒเธกเธฒเธฃเธ–เธเธฑเธเธ—เธถเธเธเนเธญเธกเธนเธฅเธเธฒเธฃเนเธกเธฃเธฒเธขเธงเธฑเธเนเธ”เน: {e}")
        return False


# ==========================================
# ๐งฎ 3. CORE AI SOLVER ENGINE
# ==========================================
def run_ai_solver(nutrient_targets):
    """
    เธชเธกเธญเธเธเธฅเธเธณเธเธงเธ“เธชเธนเธ•เธฃเธญเธฒเธซเธฒเธฃเธ•เนเธเธ—เธธเธเธ•เนเธณเธชเธธเธ” (Linear Programming)
    เนเธ”เธขเธ”เธถเธเธเนเธญเธเธณเธเธฑเธ” (Constraints) เธกเธฒเธเธฒเธเธ•เธฒเธฃเธฒเธเธกเธฒเธ•เธฃเธเธฒเธเนเธ เธเธเธฒเธเธฒเธฃเธเธ Supabase 100%
    """
    if not nutrient_targets:
        st.error("โ เนเธกเนเธชเธฒเธกเธฒเธฃเธ–เธเธณเธเธงเธ“เนเธ”เนเน€เธเธทเนเธญเธเธเธฒเธเนเธกเนเธกเธตเธเนเธญเธกเธนเธฅเน€เธเธ“เธ‘เนเน€เธเนเธฒเธซเธกเธฒเธขเนเธ เธเธเธฒเธเธฒเธฃ")
        return {}

    prob = pulp.LpProblem("AI_Layer_Nutrition_Solver", pulp.LpMinimize)
    
    # เธ”เธถเธเธงเธฑเธ•เธ–เธธเธ”เธดเธเธเธฑเธเธเธธเธเธฑเธเธเธฒเธเธเธฅเธฑเธเนเธ Supabase
    current_ingredients = fetch_ingredients_from_supabase()
    if not current_ingredients:
        st.error("โ เนเธกเนเธเธเธเนเธญเธกเธนเธฅเธงเธฑเธ•เธ–เธธเธ”เธดเธเนเธเธฃเธฐเธเธ Supabase เนเธกเนเธชเธฒเธกเธฒเธฃเธ–เธเธณเธเธงเธ“เนเธ”เน")
        return {}

    # เธเธณเธซเธเธ”เธ•เธฑเธงเนเธเธฃเธชเธณเธซเธฃเธฑเธเธชเธฑเธ”เธชเนเธงเธเธเธชเธกเธงเธฑเธ•เธ–เธธเธ”เธดเธเนเธ•เนเธฅเธฐเธเธเธดเธ” (LowBound - UpBound เธญเธดเธเธ•เธฒเธกเธ—เธตเนเธ•เธฑเนเธเนเธงเนเนเธเธเธฒเธเธเนเธญเธกเธนเธฅ)
    ing_vars = {
        name: pulp.LpVariable(
            name.replace(" ", "_").replace("(", "").replace(")", ""), 
            lowBound=float(d.get("min_limit", 0)) / 100.0, 
            upBound=float(d.get("max_limit", 100)) / 100.0
        ) 
        for name, d in current_ingredients.items()
    }
    
    # เธ•เธฑเธงเนเธเธฃเน€เธชเธฃเธดเธกเธเธ”เน€เธเธขเน€เธเธทเนเธญเธเนเธญเธเธเธฑเธเธชเธกเธญเธเธเธฅเธซเธฒเธ—เธฒเธเธญเธญเธเนเธกเนเนเธ”เน (Slack Variables)
    s_p = pulp.LpVariable("slack_protein", lowBound=0)
    s_m = pulp.LpVariable("slack_me", lowBound=0)
    s_c = pulp.LpVariable("slack_calcium", lowBound=0)
    
    # Objective Function: เธเธณเธเธงเธ“เธฃเธฒเธเธฒเธงเธฑเธ•เธ–เธธเธ”เธดเธเนเธซเนเธกเธตเธ•เนเธเธ—เธธเธเธฃเธงเธกเธ•เนเธณเธ—เธตเนเธชเธธเธ”เธชเธธเธ—เธเธด
    prob += pulp.lpSum([ing_vars[name.replace(" ", "_").replace("(", "").replace(")", "")] * float(d["price"]) for name, d in current_ingredients.items()]) + (10000.0 * s_p) + (10.0 * s_m) + (10000.0 * s_c), "Total_Cost"
    
    # Constraint 1: เธชเธฑเธ”เธชเนเธงเธเธเธชเธกเธเธญเธเธงเธฑเธ•เธ–เธธเธ”เธดเธเธ—เธธเธเธเธเธดเธ”เธฃเธงเธกเธเธฑเธเธ•เนเธญเธเนเธ”เน 100% เธเธญเธ”เธต
    prob += pulp.lpSum([ing_vars[name.replace(" ", "_").replace("(", "").replace(")", "")] for name in current_ingredients.keys()]) == 1.0, "Total_Weight_100_Percent"
    
    # Constraints 2-8: เธเธนเธเธเนเธญเธเธณเธเธฑเธ”เธชเธฒเธฃเธญเธฒเธซเธฒเธฃเธ•เธฒเธกเธเนเธฒเธ—เธตเนเธ”เธถเธเธกเธฒเธเธฒเธ Supabase เธเธฃเธดเธ
    prob += pulp.lpSum([ing_vars[name.replace(" ", "_").replace("(", "").replace(")", "")] * float(d["protein"]) for name, d in current_ingredients.items()]) + s_p >= nutrient_targets["min_protein"]
    prob += pulp.lpSum([ing_vars[name.replace(" ", "_").replace("(", "").replace(")", "")] * float(d["me"]) for name, d in current_ingredients.items()]) + s_m >= nutrient_targets["min_me"]
    
    # เนเธเธฅเน€เธเธตเธขเธก (เธ•เธฃเธงเธเน€เธเธ“เธ‘เนเธเธฑเนเธเธ•เนเธณ เนเธฅเธฐเธเธฑเนเธเธชเธนเธเธชเธธเธ”เธ•เธฒเธกเธชเธฒเธขเธเธฑเธเธเธธเน)
    prob += pulp.lpSum([ing_vars[name.replace(" ", "_").replace("(", "").replace(")", "")] * float(d["calcium"]) for name, d in current_ingredients.items()]) + s_c >= nutrient_targets["min_calcium"]
    prob += pulp.lpSum([ing_vars[name.replace(" ", "_").replace("(", "").replace(")", "")] * float(d["calcium"]) for name, d in current_ingredients.items()]) <= nutrient_targets["max_calcium"]
    
    # เธเธญเธชเธเธญเธฃเธฑเธช, เนเธฅเธเธตเธ, เน€เธกเธ—เธดเนเธญเธเธตเธ เนเธฅเธฐเน€เธขเธทเนเธญเนเธขเธชเธนเธเธชเธธเธ”
    prob += pulp.lpSum([ing_vars[name.replace(" ", "_").replace("(", "").replace(")", "")] * float(d["phos"]) for name, d in current_ingredients.items()]) >= nutrient_targets["min_phosphorus"]
    prob += pulp.lpSum([ing_vars[name.replace(" ", "_").replace("(", "").replace(")", "")] * float(d["lysine"]) for name, d in current_ingredients.items()]) >= nutrient_targets["min_lysine"]
    prob += pulp.lpSum([ing_vars[name.replace(" ", "_").replace("(", "").replace(")", "")] * float(d["methionine"]) for name, d in current_ingredients.items()]) >= nutrient_targets["min_methionine"]
    prob += pulp.lpSum([ing_vars[name.replace(" ", "_").replace("(", "").replace(")", "")] * float(d.get("fiber", 0.0)) for name, d in current_ingredients.items()]) <= nutrient_targets["max_fiber"]
    
    # เน€เธฃเธดเนเธกเธชเธฑเนเธเน€เธเธดเธ”เธฃเธฐเธเธ Solver เธเธณเธเธงเธ“เธซเธฒเธ—เธฒเธเธญเธญเธเธ—เธตเนเธ”เธตเธ—เธตเนเธชเธธเธ”
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    
    res = {}
    for name in current_ingredients.keys():
        var_key = name.replace(" ", "_").replace("(", "").replace(")", "")
        res[name] = round((ing_vars[var_key].varValue if ing_vars[var_key].varValue is not None else 0.0) * 100.0, 1)
    return res

# ==========================================
# ๐”’ 4. SECURITY GATEWAY (SUPABASE AUTH INTEGRATION)
# ==========================================
def get_query_param(name):
    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value

def normalize_recovery_link_params():
    components.html(
        """
        <script>
        const hash = window.location.hash;
        const search = window.location.search;
        if (hash && hash.includes('access_token') && !search.includes('access_token')) {
            const params = new URLSearchParams(hash.substring(1));
            const target = new URL(window.location.href);
            params.forEach((value, key) => target.searchParams.set(key, value));
            target.hash = '';
            window.location.replace(target.toString());
        }
        </script>
        """,
        height=0,
    )

def detect_password_recovery_session():
    access_token = get_query_param("access_token")
    refresh_token = get_query_param("refresh_token")
    recovery_type = get_query_param("type")
    recovery_code = get_query_param("code")
    auth_action = get_query_param("auth_action")

    if auth_action == "forgot_password":
        st.session_state.auth_page_mode = "forgot"
    elif auth_action == "reset_password":
        st.session_state.auth_page_mode = "reset_password"

    if access_token and refresh_token and recovery_type == "recovery":
        try:
            supabase.auth.set_session(access_token, refresh_token)
            st.session_state.auth_page_mode = "reset_password"
            st.session_state.password_recovery_ready = True
        except Exception as error:
            st.error(f"เนเธกเนเธชเธฒเธกเธฒเธฃเธ–เน€เธเธดเธ”เธซเธเนเธฒเธ•เธฑเนเธเธฃเธซเธฑเธชเธเนเธฒเธเนเธซเธกเนเนเธ”เน: {error}")
    elif recovery_code and not st.session_state.get("password_recovery_ready"):
        try:
            supabase.auth.exchange_code_for_session(recovery_code)
            st.session_state.auth_page_mode = "reset_password"
            st.session_state.password_recovery_ready = True
        except Exception as error:
            st.error(f"เนเธกเนเธชเธฒเธกเธฒเธฃเธ–เธขเธทเธเธขเธฑเธเธฅเธดเธเธเนเธ•เธฑเนเธเธฃเธซเธฑเธชเธเนเธฒเธเนเธซเธกเนเนเธ”เน: {error}")

normalize_recovery_link_params()
detect_password_recovery_session()

if "user_database" not in st.session_state:
    st.session_state.user_database = {}

if not st.session_state.is_authenticated:

    # --- 4.0 เธซเธเนเธฒ RESET PASSWORD เธซเธฅเธฑเธเธเธฒเธเธเธ”เธฅเธดเธเธเนเนเธเธญเธตเน€เธกเธฅ ---
    if st.session_state.auth_page_mode == "reset_password":
        st.markdown("<div class='content-card' style='max-width: 550px; margin: 60px auto 0 auto;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #38bdf8 !important;'>๐”‘ เธ•เธฑเนเธเธฃเธซเธฑเธชเธเนเธฒเธเนเธซเธกเน</h2>", unsafe_allow_html=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)

        if not st.session_state.get("password_recovery_ready"):
            st.warning("เธซเธเนเธฒเธเธตเนเนเธเนเธชเธณเธซเธฃเธฑเธเธ•เธฑเนเธเธฃเธซเธฑเธชเธเนเธฒเธเนเธซเธกเนเธซเธฅเธฑเธเธเธฒเธเธเธ”เธฅเธดเธเธเนเนเธเธญเธตเน€เธกเธฅเน€เธ—เนเธฒเธเธฑเนเธ")
            st.info("เธ–เนเธฒเธเธธเธ“เธ•เนเธญเธเธเธฒเธฃเธเธนเนเธเธทเธเธฃเธซเธฑเธชเธเนเธฒเธ เนเธซเนเธเธฅเธฑเธเนเธเธซเธเนเธฒเน€เธเนเธฒเธชเธนเนเธฃเธฐเธเธเนเธฅเนเธงเธเธ”เธเธธเนเธกเธฅเธทเธกเธฃเธซเธฑเธชเธเนเธฒเธ เธฃเธฐเธเธเธเธฐเธชเนเธเธฅเธดเธเธเนเธกเธฒเธขเธฑเธเธญเธตเน€เธกเธฅเธเธญเธเธเธธเธ“")
            if st.button("เธเธฅเธฑเธเนเธเธซเธเนเธฒเน€เธเนเธฒเธชเธนเนเธฃเธฐเธเธ", use_container_width=True):
                st.session_state.auth_page_mode = "login"
                st.query_params.clear()
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            st.stop()

        new_pass = st.text_input("เธฃเธซเธฑเธชเธเนเธฒเธเนเธซเธกเน:", type="password", key="reset_new_pass")
        new_pass_conf = st.text_input("เธขเธทเธเธขเธฑเธเธฃเธซเธฑเธชเธเนเธฒเธเนเธซเธกเน:", type="password", key="reset_new_pass_conf")
        is_reset_strong, reset_pass_msg = check_password_strength(new_pass) if new_pass else (False, "")

        if new_pass:
            if is_reset_strong:
                st.success(reset_pass_msg)
            else:
                st.warning(reset_pass_msg)

        if st.button("๐’พ เธเธฑเธเธ—เธถเธเธฃเธซเธฑเธชเธเนเธฒเธเนเธซเธกเน", type="primary", use_container_width=True):
            if not new_pass or not new_pass_conf:
                st.warning("เธเธฃเธธเธ“เธฒเธเธฃเธญเธเธฃเธซเธฑเธชเธเนเธฒเธเนเธซเธกเนเนเธซเนเธเธฃเธเธ—เธฑเนเธเธชเธญเธเธเนเธญเธ")
            elif new_pass != new_pass_conf:
                st.error("เธฃเธซเธฑเธชเธเนเธฒเธเนเธซเธกเนเนเธฅเธฐเธเนเธญเธเธขเธทเธเธขเธฑเธเนเธกเนเธ•เธฃเธเธเธฑเธ")
            elif not is_reset_strong:
                st.error("เธฃเธซเธฑเธชเธเนเธฒเธเนเธซเธกเนเธขเธฑเธเนเธกเนเธเนเธฒเธเน€เธเธทเนเธญเธเนเธเธเธงเธฒเธกเธเธฅเธญเธ”เธ เธฑเธข")
            else:
                try:
                    supabase.auth.update_user({"password": new_pass})
                    try:
                        supabase.auth.sign_out()
                    except Exception:
                        pass
                    st.session_state.is_authenticated = False
                    st.session_state.auth_page_mode = "login"
                    st.session_state.password_recovery_ready = False
                    st.query_params.clear()
                    st.success("เน€เธเธฅเธตเนเธขเธเธฃเธซเธฑเธชเธเนเธฒเธเธชเธณเน€เธฃเนเธ เธเธฃเธธเธ“เธฒเน€เธเนเธฒเธชเธนเนเธฃเธฐเธเธเธ”เนเธงเธขเธฃเธซเธฑเธชเธเนเธฒเธเนเธซเธกเน")
                    st.rerun()
                except Exception as error:
                    st.error(f"เนเธกเนเธชเธฒเธกเธฒเธฃเธ–เน€เธเธฅเธตเนเธขเธเธฃเธซเธฑเธชเธเนเธฒเธเนเธ”เน: {error}")

        if st.button("เธเธฅเธฑเธเนเธเธซเธเนเธฒเน€เธเนเธฒเธชเธนเนเธฃเธฐเธเธ", use_container_width=True):
            st.session_state.auth_page_mode = "login"
            st.query_params.clear()
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    # --- 4.1 เธซเธเนเธฒ LOGIN ---
    if st.session_state.auth_page_mode == "login":
        st.markdown("<div class='content-card' style='max-width: 550px; margin: 60px auto 0 auto;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #ffb703 !important;'>๐” เน€เธเนเธฒเธชเธนเนเธฃเธฐเธเธ Layer Nutrition Studio Pro</h2>", unsafe_allow_html=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)

        email_login = st.text_input("๐“ง เธญเธตเน€เธกเธฅเน€เธเนเธฒเนเธเนเธเธฒเธ:", key="login_email")
        pass_login = st.text_input("๐”‘ เธฃเธซเธฑเธชเธเนเธฒเธเน€เธเนเธฒเนเธเนเธเธฒเธ:", type="password", key="login_pass")

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("เน€เธเนเธฒเธชเธนเนเธฃเธฐเธเธ (Log In)", type="primary", use_container_width=True):
                if not email_login.strip() or not pass_login:
                    st.warning("โ ๏ธ เธเธฃเธธเธ“เธฒเธเธฃเธญเธเธญเธตเน€เธกเธฅเนเธฅเธฐเธฃเธซเธฑเธชเธเนเธฒเธเนเธซเนเธเธฃเธเธ–เนเธงเธ")
                else:
                    try:
                        auth_res = supabase.auth.sign_in_with_password({
                            "email": email_login.strip(),
                            "password": pass_login
                        })

                        if auth_res.user:
                            st.session_state.is_authenticated = True
                            st.session_state.current_user_key = email_login.strip()

                            if email_login.strip().lower() == "222@gmail.com":
                                st.session_state.user_role = "admin"
                            else:
                                st.session_state.user_role = "user"

                            st.session_state.user_email = f"{email_login.strip().split('@')[0]} [{st.session_state.user_role.upper()}]"
                            
                            # ๐”ฅ [เน€เธเธดเนเธกเธเธณเธชเธฑเนเธเนเธซเธฅเธ”เธเนเธญเธกเธนเธฅเธเธญเธ USER เธ—เธฑเธเธ—เธตเธ—เธตเนเธฅเนเธญเธเธญเธดเธเธเนเธฒเธ]
                            fetch_master_data_from_supabase()
                            fetch_ingredients_from_supabase()
                            fetch_saved_formulas_from_supabase() # เนเธซเธฅเธ”เธชเธนเธ•เธฃเธญเธฒเธซเธฒเธฃเธชเนเธงเธเธ•เธฑเธง
                            fetch_daily_logs_from_supabase()    # เนเธซเธฅเธ”เธชเธกเธธเธ”เธเธฒเธฃเนเธกเธฃเธฒเธขเธงเธฑเธเธชเนเธงเธเธ•เธฑเธง
                            
                            st.success("๐ เน€เธเนเธฒเธชเธนเนเธฃเธฐเธเธเธชเธณเน€เธฃเนเธ เธฃเธฐเธเธเธเธณเธฅเธฑเธเธเธณเธเธธเธ“เน€เธเนเธฒเธชเธนเนเธซเธเนเธฒเธซเธฅเธฑเธ...")
                            st.rerun()

                    except Exception as error:
                        error_msg = str(error).lower()
                        if "name or service not known" in error_msg or "temporary failure in name resolution" in error_msg:
                            st.error("๐ เนเธกเนเธชเธฒเธกเธฒเธฃเธ–เน€เธเธทเนเธญเธกเธ•เนเธญเธญเธดเธเน€เธ—เธญเธฃเนเน€เธเนเธ•เธซเธฃเธทเธญเน€เธเธดเธฃเนเธเน€เธงเธญเธฃเนเธเธฒเธเธเนเธญเธกเธนเธฅเนเธ”เน เธเธฃเธธเธ“เธฒเธ•เธฃเธงเธเธชเธญเธเธเธฒเธฃเน€เธเธทเนเธญเธกเธ•เนเธญ")
                        elif "invalid login credentials" in error_msg or "bad credentials" in error_msg:
                            st.error("โ เธญเธตเน€เธกเธฅเธซเธฃเธทเธญเธฃเธซเธฑเธชเธเนเธฒเธเนเธกเนเธ–เธนเธเธ•เนเธญเธ เธเธฃเธธเธ“เธฒเธ•เธฃเธงเธเธชเธญเธเธเนเธญเธกเธนเธฅเธญเธตเธเธเธฃเธฑเนเธ")
                        else:
                            st.error(f"โ เนเธกเนเธชเธฒเธกเธฒเธฃเธ–เน€เธเนเธฒเธชเธนเนเธฃเธฐเธเธเนเธ”เนเน€เธเธทเนเธญเธเธเธฒเธเน€เธเธดเธ”เธเนเธญเธเธดเธ”เธเธฅเธฒเธ”: {error}")
        with col_btn2:
            if st.button("๐• เธชเธกเธฑเธเธฃเธชเธกเธฒเธเธดเธเนเธซเธกเนเธ—เธตเนเธเธตเน", use_container_width=True):
                st.session_state.auth_page_mode = "signup"
                st.rerun()

        st.markdown("<div style='text-align: center; margin-top: 15px;'>", unsafe_allow_html=True)
        if st.button("โ“ เธฅเธทเธกเธฃเธซเธฑเธชเธเนเธฒเธเนเธเนเธซเธฃเธทเธญเนเธกเน?", type="secondary"):
            st.query_params["auth_action"] = "forgot_password"
            st.session_state.auth_page_mode = "forgot"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    # --- 4.2 เธซเธเนเธฒ SIGN UP ---
    elif st.session_state.auth_page_mode == "signup":
        st.markdown("<div class='content-card' style='max-width: 600px; margin: 40px auto 0 auto;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #38bdf8 !important;'>๐“ เธชเธกเธฑเธเธฃเธชเธกเธฒเธเธดเธเธเธฒเธฃเนเธกเนเธซเธกเน (Sign Up)</h2>", unsafe_allow_html=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)

        su_name = st.text_input("๐‘ค เธเธทเนเธญเธเธฃเธดเธ:")
        su_surname = st.text_input("๐‘ค เธเธฒเธกเธชเธเธธเธฅ:")
        su_tel = st.text_input("๐“ เน€เธเธญเธฃเนเนเธ—เธฃเธจเธฑเธเธ—เนเธ•เธดเธ”เธ•เนเธญ:")
        su_email = st.text_input("๐“ง เธญเธตเน€เธกเธฅเธเธฑเธเธเธตเธเธนเนเนเธเน (เนเธเนเน€เธเนเธเนเธญเธ”เธตเธชเธณเธซเธฃเธฑเธ Log In):")
        st.markdown(
            "<div style='background-color:#1e293b; padding:12px; border-radius:8px; margin-bottom:10px; font-size:0.85rem; color:#94a3b8;'>"
            "๐”’ <b>เธเนเธญเธเธณเธซเธเธ”เธฃเธซเธฑเธชเธเนเธฒเธเธเธงเธฒเธกเธเธฅเธญเธ”เธ เธฑเธขเธชเธนเธ:</b><br>"
            "- เธเธงเธฒเธกเธขเธฒเธงเนเธกเนเธเนเธญเธขเธเธงเนเธฒ 8 เธ•เธฑเธงเธญเธฑเธเธฉเธฃ<br>"
            "- เธกเธตเธญเธฑเธเธฉเธฃเธเธดเธกเธเนเนเธซเธเน (A-Z) เนเธฅเธฐเธเธดเธกเธเนเน€เธฅเนเธ (a-z)<br>"
            "- เธกเธตเธ•เธฑเธงเน€เธฅเธ (0-9) เนเธฅเธฐเธญเธฑเธเธเธฃเธฐเธเธดเน€เธจเธฉเธญเธขเนเธฒเธเธเนเธญเธข 1 เธ•เธฑเธง (@, #, $, %, !, ., _)"
            "</div>", unsafe_allow_html=True
        )
        su_pass = st.text_input("๐”‘ เธ•เธฑเนเธเธฃเธซเธฑเธชเธเนเธฒเธเธเธงเธฒเธกเธเธฅเธญเธ”เธ เธฑเธขเธชเธนเธ:", type="password")
        su_pass_conf = st.text_input("๐” เธเธดเธกเธเนเธขเธทเธเธขเธฑเธเธฃเธซเธฑเธชเธเนเธฒเธเธญเธตเธเธเธฃเธฑเนเธ:", type="password")
        is_strong, pass_msg = check_password_strength(su_pass) if su_pass else (False, "")

        if su_pass:
            if is_strong:
                st.success(pass_msg)
            else:
                st.warning(pass_msg)

        col_su1, col_su2 = st.columns(2)
        with col_su1:
            if st.button("โ… เธขเธทเธเธขเธฑเธเธเธฒเธฃเธฅเธเธ—เธฐเน€เธเธตเธขเธ", type="primary", use_container_width=True):
                if su_email and su_pass and su_name and su_tel:
                    if su_pass != su_pass_conf:
                        st.error("โ เธฃเธซเธฑเธชเธเนเธฒเธเธ—เธตเนเธขเธทเธเธขเธฑเธ เนเธกเนเธ•เธฃเธเธเธฑเธเธฃเธซเธฑเธชเธเนเธฒเธเธ•เธฑเนเธเธ•เนเธ!")
                    elif not is_strong:
                        st.error("โ เนเธกเนเธชเธฒเธกเธฒเธฃเธ–เธฅเธเธ—เธฐเน€เธเธตเธขเธเนเธ”เน เน€เธเธทเนเธญเธเธเธฒเธเธฃเธซเธฑเธชเธเนเธฒเธเนเธกเนเธเธฅเธญเธ”เธ เธฑเธขเธ•เธฒเธกเธกเธฒเธ•เธฃเธเธฒเธ")
                    else:
                        try:
                            auth_res = supabase.auth.sign_up({
                                "email": su_email,
                                "password": su_pass,
                                "options": {
                                    "data": {
                                        "first_name": su_name,
                                        "last_name": su_surname,
                                        "phone": su_tel
                                    }
                                }
                            })
                            st.session_state.user_database[su_email] = {
                                "name": su_name,
                                "surname": su_surname,
                                "tel": su_tel,
                                "role": "user",
                                "reg_date": str(datetime.date.today())
                            }
                            st.success("๐ เธชเธกเธฑเธเธฃเธชเธกเธฒเธเธดเธเธชเธณเน€เธฃเนเธเนเธฅเธฐเน€เธเนเธฒเธชเธนเนเธฃเธฐเธเธเนเธฅเนเธง")
                            st.session_state.is_authenticated = True
                            st.session_state.current_user_key = su_email
                            st.session_state.user_role = "user"
                            st.session_state.user_email = f"{su_email.split('@')[0]} [USER]"
                            
                            # ๐”ฅ [เน€เธเธดเนเธกเธเธณเธชเธฑเนเธเนเธซเธฅเธ”เธเนเธญเธกเธนเธฅเธเธญเธ USER เนเธซเธกเนเธ—เธตเนเธชเธกเธฑเธเธฃเน€เธชเธฃเนเธ]
                            fetch_master_data_from_supabase()
                            fetch_ingredients_from_supabase()
                            fetch_saved_formulas_from_supabase() # เธ”เธถเธเธ•เธฒเธฃเธฒเธเธชเธนเธ•เธฃ
                            fetch_daily_logs_from_supabase()    # เธ”เธถเธเธ•เธฒเธฃเธฒเธเธชเธกเธธเธ”เธเธฃเธฐเธเธณเธงเธฑเธ
                            
                            st.rerun()
                        except Exception as error:
                            st.error(f"โ เธฅเธเธ—เธฐเน€เธเธตเธขเธเธฅเนเธกเน€เธซเธฅเธง: {error}")
                else:
                    st.warning("โ ๏ธ เธเธฃเธธเธ“เธฒเธเธฃเธญเธเธเนเธญเธกเธนเธฅเนเธเธเนเธญเธเธเธณเน€เธเนเธเนเธซเนเธเธฃเธเธ–เนเธงเธ")
        with col_su2:
            if st.button("โฌ…๏ธ เธขเนเธญเธเธเธฅเธฑเธเนเธเธซเธเนเธฒเธฅเนเธญเธเธญเธดเธ", use_container_width=True):
                st.session_state.auth_page_mode = "login"
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

# ๐”ฅ เนเธซเธฅเธ”เธเนเธญเธกเธนเธฅเธงเธฑเธ•เธ–เธธเธ”เธดเธเน€เธฃเธดเนเธกเธ•เนเธเธซเธฅเธฑเธเธเธฒเธเธเธนเนเนเธเนเธเธฒเธเธเนเธฒเธเธเธฃเธฐเธ•เธนเธเธงเธฒเธกเธเธฅเธญเธ”เธ เธฑเธขเน€เธเนเธฒเธชเธนเนเธฃเธฐเธเธเน€เธฃเธตเธขเธเธฃเนเธญเธขเนเธฅเนเธง เน€เธ—เนเธฒเธเธฑเนเธ
fetch_master_data_from_supabase()
ingredients = fetch_ingredients_from_supabase()

# ==========================================
# ๐ 5. HEADER CONTROL PANEL
# ==========================================
col_h1, col_h2 = st.columns([7.5, 2.5])
with col_h1:
    st.markdown(f"# ๐” Layer Nutrition Studio Pro <span style='font-size:1.1rem; color:#38bdf8;'>[เธชเธดเธ—เธเธดเนเธเธฒเธฃเนเธเนเธเธฒเธ: {st.session_state.user_email}]</span>", unsafe_allow_html=True)
with col_h2:
    cc1, cc2 = st.columns(2)
    with cc1:
        if "admin" in st.session_state.user_email.lower() or st.session_state.user_role == "admin":
            if st.session_state.user_role == "user":
                if st.button("๐” เธซเธเนเธฒ Admin", use_container_width=True):
                    st.session_state.user_role = "admin"
                    st.rerun()
            else:
                if st.button("๐” เธซเธเนเธฒ User", use_container_width=True):
                    st.session_state.user_role = "user"
                    st.rerun()
    with cc2:
        if st.button("๐”ด เธญเธญเธเธเธฒเธเธฃเธฐเธเธ", use_container_width=True):
            try:
                supabase.auth.sign_out()
            except:
                pass
            st.session_state.is_authenticated = False
            st.session_state.current_weights = {}
            st.session_state.auth_page_mode = "login"
            st.rerun()
st.markdown("---")
# ==========================================
# ๐ ๏ธ 6. MAIN ROUTER & DASHBOARD INTERFACE (UX/UI PREMIUM VERSION)
# ==========================================
if st.session_state.user_role == "admin":
    st.title("๐’ป Admin Master Data Control")
    st.caption("เธฃเธฐเธเธเธเธฑเธ”เธเธฒเธฃเนเธเธฃเธเธชเธฃเนเธฒเธเธชเธฒเธฃเธญเธฒเธซเธฒเธฃ เธงเธฑเธ•เธ–เธธเธ”เธดเธ เธชเธฒเธขเธเธฑเธเธเธธเน เนเธฅเธฐเธเธนเนเนเธเนเธเธฒเธเนเธเธ Dynamic เธฃเนเธงเธกเธเธฑเธเธเธฅเธฒเธงเธ”เน")
    
    admin_tabs = st.tabs([
        "โ๏ธ เธ•เธฑเนเธเธเนเธฒเธซเธฑเธงเธเนเธญเธชเธฒเธฃเธญเธฒเธซเธฒเธฃ",
        "๐ฝ เธเธฅเธฑเธเธงเธฑเธ•เธ–เธธเธ”เธดเธ & เธชเธฒเธฃเธญเธฒเธซเธฒเธฃ", 
        "๐“ เธ—เธณเน€เธเธตเธขเธเธชเธฒเธขเธเธฑเธเธเธธเนเนเธเนเนเธเน", 
        "๐งฌ เน€เธเธ“เธ‘เนเนเธ เธเธเธฒเธเธฒเธฃเธ•เธฒเธกเธเนเธงเธเธญเธฒเธขเธธ", 
        "๐‘ค เธเธฒเธฃเธเธฑเธ”เธเธฒเธฃเธชเธดเธ—เธเธดเนเธเธนเนเนเธเนเธเธฒเธ"
    ])
    
    # --- เนเธ—เนเธเธ—เธตเน 0: เน€เธเธดเนเธก/เธฅเธ เธชเธฒเธฃเธญเธฒเธซเธฒเธฃเธ”เนเธงเธขเธ•เธฑเธงเน€เธญเธ ---
    with admin_tabs[0]:
        st.subheader("โ๏ธ เธชเธฒเธฃเธญเธฒเธซเธฒเธฃเธ—เธตเนเธกเธตเนเธเธฃเธฐเธเธเธเธฑเธเธเธธเธเธฑเธ")
        
        with st.expander("๐“ เธ”เธนเนเธเธฃเธเธชเธฃเนเธฒเธเธชเธฒเธฃเธญเธฒเธซเธฒเธฃเธ—เธตเนเนเธเนเธเธฒเธเธญเธขเธนเนเธ—เธฑเนเธเธซเธกเธ”", expanded=True):
            df_nutrients = pd.DataFrame([
                {"เธฃเธซเธฑเธชเธฃเธฐเธเธ (Key)": k, "เธเธทเนเธญเธ•เธฑเธงเธเธตเนเธงเธฑเธ” (Label)": v["label"], "เธเธงเธฒเธกเธฅเธฐเน€เธญเธตเธขเธ” (Step)": v["step"]} 
                for k, v in st.session_state.db_nutrient_keys.items()
            ])
            st.dataframe(df_nutrients, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        n_col1, n_col2 = st.columns(2, gap="large")
        
        with n_col1:
            st.markdown("### โ• เน€เธเธดเนเธกเธชเธฒเธฃเธญเธฒเธซเธฒเธฃเนเธซเธกเน")
            with st.container(border=True):
                new_nut_key = st.text_input("เธฃเธซเธฑเธชเธญเธฑเธเธเธคเธฉ (เน€เธเนเธ fat, ash):", placeholder="เธเธฃเธญเธเธเธดเธกเธเนเน€เธฅเนเธเธซเนเธฒเธกเธกเธตเธเนเธญเธเธงเนเธฒเธ", key="add_nut_key").strip().lower()
                new_nut_label = st.text_input("เธเธทเนเธญเธ เธฒเธฉเธฒเนเธ—เธขเธ—เธตเนเนเธชเธ”เธ (เน€เธเนเธ เนเธเธกเธฑเธเธ”เธดเธ (%)):", placeholder="เน€เธเนเธ เธงเธดเธ•เธฒเธกเธดเธเธญเธต (mg/kg)", key="add_nut_label")
                new_nut_step = st.number_input("เธเธงเธฒเธกเธฅเธฐเน€เธญเธตเธขเธ”เนเธเธเธฒเธฃเธเธ”เธเธธเนเธกเน€เธเธดเนเธก/เธฅเธ”เธเนเธฒ:", min_value=0.001, max_value=100.0, value=0.1, format="%.3f", key="add_nut_step")
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("โจ เธขเธทเธเธขเธฑเธเธชเธฃเนเธฒเธเธซเธฑเธงเธเนเธญเธชเธฒเธฃเธญเธฒเธซเธฒเธฃ", type="primary", use_container_width=True):
                    if not new_nut_key or not new_nut_label:
                        st.error("โ เธเธฃเธธเธ“เธฒเธเธฃเธญเธเธเนเธญเธกเธนเธฅเนเธซเนเธเธฃเธเธ—เธฑเนเธเธชเธญเธเธเนเธญเธ")
                    elif new_nut_key in st.session_state.db_nutrient_keys or new_nut_key in ["name", "min_limit", "max_limit"]:
                        st.error("โ เธฃเธซเธฑเธชเธเธตเนเธเนเธณเธซเธฃเธทเธญเน€เธเนเธเธเธณเธ•เนเธญเธเธซเนเธฒเธกเธเธญเธเธฃเธฐเธเธ")
                    else:
                        # 1. เน€เธเธดเนเธกเน€เธเนเธฒ Local Session State
                        st.session_state.db_nutrient_keys[new_nut_key] = {"label": new_nut_label, "step": new_nut_step, "default": 0.0}
                        
                        # 2. เธ—เธณเธเธฒเธฃเธญเธฑเธเน€เธ”เธ• Schema เธงเธฑเธ•เธ–เธธเธ”เธดเธเน€เธ”เธดเธกเนเธซเนเธฃเธญเธเธฃเธฑเธ Key เนเธซเธกเน (เธเนเธญเธเธเธฑเธเธเธฑเนเธ KeyError)
                        for ing_name in st.session_state.db_ingredients.keys():
                            if new_nut_key not in st.session_state.db_ingredients[ing_name]:
                                st.session_state.db_ingredients[ing_name][new_nut_key] = 0.0
                        
                        st.success(f"๐ เน€เธเธดเนเธกเนเธเธฃเธเธชเธฃเนเธฒเธเธซเธฑเธงเธเนเธญเธชเธฒเธฃเธญเธฒเธซเธฒเธฃ '{new_nut_label}' เน€เธฃเธตเธขเธเธฃเนเธญเธขเนเธฅเนเธง!")
                        st.rerun()
                        
        with n_col2:
            st.markdown("### โ เธฅเธเธชเธฒเธฃเธญเธฒเธซเธฒเธฃ")
            with st.container(border=True):
                removable_keys = [k for k in st.session_state.db_nutrient_keys.keys() if k != "price"]
                
                if removable_keys:
                    nut_to_del = st.selectbox("เน€เธฅเธทเธญเธเธชเธฒเธฃเธญเธฒเธซเธฒเธฃเธ—เธตเนเธ•เนเธญเธเธเธฒเธฃเธ–เธญเธ”เธ–เธญเธ:", removable_keys, format_func=lambda x: st.session_state.db_nutrient_keys[x]["label"], key="del_nut_select")
                    st.markdown("<br><br><br>", unsafe_allow_html=True)
                    
                    if st.button("๐—‘๏ธ เธขเธทเธเธขเธฑเธเธฅเธเธญเธญเธเธเธฒเธเธฃเธฐเธเธเธ–เธฒเธงเธฃ", type="secondary", use_container_width=True):
                        del_label = st.session_state.db_nutrient_keys[nut_to_del]["label"]
                        
                        # เธฅเธเธญเธญเธเธเธฒเธเนเธเธฃเธเธชเธฃเนเธฒเธเธซเธฅเธฑเธเนเธฅเธฐเธงเธฑเธ•เธ–เธธเธ”เธดเธเธ—เธธเธเธ•เธฑเธงเธเนเธญเธเธเธฑเธเธเนเธญเธกเธนเธฅเธเธขเธฐเธเนเธฒเธเธเธฑเนเธ
                        del st.session_state.db_nutrient_keys[nut_to_del]
                        for ing_name in st.session_state.db_ingredients.keys():
                            if nut_to_del in st.session_state.db_ingredients[ing_name]:
                                del st.session_state.db_ingredients[ing_name][nut_to_del]
                                
                        st.success(f"๐”ฅ เธฅเธเธชเธฒเธฃเธญเธฒเธซเธฒเธฃ '{del_label}' เธชเธณเน€เธฃเนเธ")
                        st.rerun()
                else:
                    st.warning("โ ๏ธ เนเธกเนเธกเธตเธชเธฒเธฃเธญเธฒเธซเธฒเธฃเธญเธทเนเธเธเธญเธเน€เธซเธเธทเธญเธเธฒเธเธฃเธฒเธเธฒเธ—เธตเนเธชเธฒเธกเธฒเธฃเธ–เธฅเธเนเธ”เน")

    # --- เนเธ—เนเธเธ—เธตเน 1: เธเธฑเธ”เธเธฒเธฃเนเธฅเธฐเนเธเนเนเธเธงเธฑเธ•เธ–เธธเธ”เธดเธ/เธชเธฒเธฃเธญเธฒเธซเธฒเธฃ ---
    with admin_tabs[1]:
        with st.expander("๐“ เน€เธเธดเธ”เธ”เธนเธเธฅเธฑเธเธงเธฑเธ•เธ–เธธเธ”เธดเธเนเธฅเธฐเธฃเธฒเธเธฒเธเธฑเธเธเธธเธเธฑเธเนเธเธฃเธฐเธเธ", expanded=False):
            if st.session_state.db_ingredients:
                st.dataframe(pd.DataFrame.from_dict(st.session_state.db_ingredients, orient='index'), use_container_width=True)
            else:
                st.info("เธเธฅเธฑเธเธงเธฑเธ•เธ–เธธเธ”เธดเธเธงเนเธฒเธเน€เธเธฅเนเธฒ")
        
        crud_mode = st.segmented_control(
            "เน€เธฅเธทเธญเธเธเธฑเธเธเนเธเธฑเธเธเธฑเธ”เธเธฒเธฃเธเธฅเธฑเธเธงเธฑเธ•เธ–เธธเธ”เธดเธ:", 
            ["โ๏ธ เนเธเนเนเธเธเนเธญเธกเธนเธฅเธงเธฑเธ•เธ–เธธเธ”เธดเธเน€เธ”เธดเธก", "โ• เน€เธเธดเนเธกเธงเธฑเธ•เธ–เธธเธ”เธดเธเนเธซเธกเน", "๐—‘๏ธ เธฅเธเธงเธฑเธ•เธ–เธธเธ”เธดเธเธญเธญเธ"],
            default="โ๏ธ เนเธเนเนเธเธเนเธญเธกเธนเธฅเธงเธฑเธ•เธ–เธธเธ”เธดเธเน€เธ”เธดเธก"
        )
        st.markdown("---")

        if crud_mode == "โ๏ธ เนเธเนเนเธเธเนเธญเธกเธนเธฅเธงเธฑเธ•เธ–เธธเธ”เธดเธเน€เธ”เธดเธก" and st.session_state.db_ingredients:
            selected_ing_edit = st.selectbox("เน€เธฅเธทเธญเธเธงเธฑเธ•เธ–เธธเธ”เธดเธเธ—เธตเนเธเธฐเธเธฃเธฑเธเธเธฃเธธเธเธเนเธญเธกเธนเธฅ:", list(st.session_state.db_ingredients.keys()))
            target_ing = st.session_state.db_ingredients[selected_ing_edit]
            
            with st.form(key=f"form_edit_{selected_ing_edit}"):
                st.markdown(f"#### ๐“ เนเธเนเนเธเธเนเธญเธกเธนเธฅเธชเธฒเธฃเธญเธฒเธซเธฒเธฃเธเธญเธ: **{selected_ing_edit}**")
                
                c_limits = st.columns(2)
                with c_limits[0]:
                    edit_ing_min = st.number_input("เธชเธฑเธ”เธชเนเธงเธเธเธฑเนเธเธ•เนเธณเธ—เธตเนเธ•เนเธญเธเนเธเนเนเธเธชเธนเธ•เธฃ (% Min):", min_value=0.0, max_value=100.0, value=float(target_ing.get("min_limit", 0.0)), step=0.1)
                with c_limits[1]:
                    edit_ing_max = st.number_input("เธชเธฑเธ”เธชเนเธงเธเธชเธนเธเธชเธธเธ”เธ—เธตเนเธซเนเธฒเธกเน€เธเธดเธเนเธเธชเธนเธ•เธฃ (% Max):", min_value=0.0, max_value=100.0, value=float(target_ing.get("max_limit", 100.0)), step=0.1)
                
                st.markdown("**๐“ เธเนเธฒเนเธ เธเธเธฒเธเธฒเธฃเนเธฅเธฐเธชเธฒเธฃเธญเธฒเธซเธฒเธฃ**")
                edited_values = {}
                ec = st.columns(3)
                for idx, (nut_key, nut_info) in enumerate(st.session_state.db_nutrient_keys.items()):
                    with ec[idx % 3]:
                        # เธเนเธญเธเธเธฑเธเธเธฑเนเธ KeyError เธ”เนเธงเธขเธเธฒเธฃเนเธเน .get() เนเธฅเธฐเน€เธฃเธตเธขเธเนเธเนเธเนเธฒ default เน€เธเธทเนเธญเนเธงเน
                        current_val = float(target_ing.get(nut_key, nut_info.get("default", 0.0)))
                        edited_values[nut_key] = st.number_input(f"{nut_info['label']}:", min_value=0.0, value=current_val, step=nut_info["step"])
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("๐’พ เธเธฑเธเธ—เธถเธเธเธฒเธฃเน€เธเธฅเธตเนเธขเธเนเธเธฅเธเธ—เธฑเนเธเธซเธกเธ”", type="primary", use_container_width=True):
                    if edit_ing_min > edit_ing_max:
                        st.error("โ เธเนเธญเธเธดเธ”เธเธฅเธฒเธ”: เธชเธฑเธ”เธชเนเธงเธเธ•เนเธณเธชเธธเธ” (% Min) เธซเนเธฒเธกเธกเธฒเธเธเธงเนเธฒเธชเธฑเธ”เธชเนเธงเธเธชเธนเธเธชเธธเธ” (% Max)")
                    else:
                        # เธญเธฑเธเน€เธ”เธ•เธเนเธญเธกเธนเธฅเธฅเธ Local State
                        st.session_state.db_ingredients[selected_ing_edit].update(edited_values)
                        st.session_state.db_ingredients[selected_ing_edit].update({"min_limit": edit_ing_min, "max_limit": edit_ing_max})
                        
                        # โก เธเธดเธเธเนเธเธงเธฒเธกเธ–เธฒเธงเธฃเธฅเธ Supabase Cloud Database เนเธเธเน€เธฃเธตเธขเธฅเนเธ—เธกเน
                        try:
                            owner_email = get_ingredient_owner_for_write(target_ing)
                            payload = {"name": selected_ing_edit, "min_limit": edit_ing_min, "max_limit": edit_ing_max, "owner_email": owner_email}
                            payload.update(edited_values)
                            st.session_state.db_ingredients[selected_ing_edit]["owner_email"] = owner_email
                            supabase.table("ingredients").upsert(payload).execute()
                            st.success(f"๐ เธเธฃเธฑเธเธเธฃเธธเธเธเนเธญเธกเธนเธฅเธชเธฒเธฃเธญเธฒเธซเธฒเธฃเธเธญเธ '{selected_ing_edit}' เธฅเธเธฃเธฐเธเธเธเธฅเธฒเธงเธ”เนเน€เธฃเธตเธขเธเธฃเนเธญเธขเนเธฅเนเธง")
                            st.rerun()
                        except Exception as cloud_err:
                            st.warning(f"โ ๏ธ เธเธฑเธเธ—เธถเธเนเธเธฃเธฐเธเธเธเธณเธฅเธญเธเธชเธณเน€เธฃเนเธ เนเธ•เนเนเธกเนเธชเธฒเธกเธฒเธฃเธ–เธเธดเธเธเนเธเธถเนเธ Cloud เนเธ”เน: {cloud_err}")

        elif crud_mode == "โ• เน€เธเธดเนเธกเธงเธฑเธ•เธ–เธธเธ”เธดเธเนเธซเธกเน":
            with st.form(key="form_add_new_ingredient"):
                st.markdown("#### โ• เธฅเธเธ—เธฐเน€เธเธตเธขเธเธงเธฑเธ•เธ–เธธเธ”เธดเธเธ•เธฑเธงเนเธซเธกเนเน€เธเนเธฒเธเธฅเธฑเธเธเธฅเธฒเธ")
                ing_name = st.text_input("๐“ เธฃเธฐเธเธธเธเธทเนเธญเธงเธฑเธ•เธ–เธธเธ”เธดเธเนเธซเธกเน:", placeholder="เน€เธเนเธ เธฃเธณเธเนเธฒเธงเธซเธญเธกเธกเธฐเธฅเธดเธเธ”เธฅเธฐเน€เธญเธตเธขเธ”")
                
                c_limits = st.columns(2)
                with c_limits[0]:
                    ing_min = st.number_input("เธชเธฑเธ”เธชเนเธงเธเธเธฑเนเธเธ•เนเธณเธ—เธตเนเธ•เนเธญเธเนเธเนเนเธเธชเธนเธ•เธฃ (% Min):", min_value=0.0, value=0.0)
                with c_limits[1]:
                    ing_max = st.number_input("เธชเธฑเธ”เธชเนเธงเธเธชเธนเธเธชเธธเธ”เธ—เธตเนเธซเนเธฒเธกเน€เธเธดเธเนเธเธชเธนเธ•เธฃ (% Max):", min_value=0.0, value=100.0)
                
                st.markdown("**๐“ เธฃเธฐเธเธธเธชเธฒเธฃเธญเธฒเธซเธฒเธฃเธ•เธฑเนเธเธ•เนเธ**")
                new_material_data = {}
                ac = st.columns(3)
                for idx, (nut_key, nut_info) in enumerate(st.session_state.db_nutrient_keys.items()):
                    with ac[idx % 3]:
                        new_material_data[nut_key] = st.number_input(f"{nut_info['label']}:", min_value=0.0, value=nut_info.get("default", 0.0), step=nut_info["step"])
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("โ• เธเธฑเธเธ—เธถเธเน€เธเธดเนเธกเน€เธเนเธฒเธเธฅเธฑเธเธชเธดเธเธเนเธฒเธเธฅเธฒเธ", type="primary", use_container_width=True):
                    if not ing_name.strip():
                        st.error("โ เธเธฃเธธเธ“เธฒเธเธฃเธญเธเธเธทเนเธญเธงเธฑเธ•เธ–เธธเธ”เธดเธเธ”เนเธงเธขเธเธฃเธฑเธ")
                    elif ing_name in st.session_state.db_ingredients:
                        st.error(f"โ เธฃเธฒเธขเธเธฒเธฃ '{ing_name}' เธกเธตเนเธเธฃเธฐเธเธเธญเธขเธนเนเนเธฅเนเธง")
                    elif ing_min > ing_max:
                        st.error("โ เธเนเธญเธเธดเธ”เธเธฅเธฒเธ”: เธเนเธฒเธ•เนเธณเธชเธธเธ”เธซเนเธฒเธกเธกเธฒเธเธเธงเนเธฒเธเนเธฒเธชเธนเธเธชเธธเธ”")
                    else:
                        owner_email = get_ingredient_owner_for_write()
                        base_data = {"name": ing_name, "min_limit": ing_min, "max_limit": ing_max, "owner_email": owner_email}
                        base_data.update(new_material_data)
                        
                        # เธเธฑเธเธ—เธถเธเธฅเธเน€เธเธฃเธทเนเธญเธเนเธฅเธฐเธขเธดเธเธเธถเนเธเธเธฒเธเธเนเธญเธกเธนเธฅเธเธฅเธฒเธงเธ”เน Supabase
                        st.session_state.db_ingredients[ing_name] = base_data
                        try:
                            supabase.table("ingredients").insert(base_data).execute()
                            st.success(f"๐ เธเธณเน€เธเนเธฒ '{ing_name}' เธชเธนเนเธเธฅเธฒเธงเธ”เนเธเธฒเธเธเนเธญเธกเธนเธฅเน€เธฃเธตเธขเธเธฃเนเธญเธข!")
                            st.rerun()
                        except Exception as cloud_err:
                            st.success(f"๐ เธเธฑเธเธ—เธถเธเธเธฑเนเธงเธเธฃเธฒเธงเธชเธณเน€เธฃเนเธ (Cloud Error: {cloud_err})")

        elif crud_mode == "๐—‘๏ธ เธฅเธเธงเธฑเธ•เธ–เธธเธ”เธดเธเธญเธญเธ" and st.session_state.db_ingredients:
            st.markdown("#### ๐—‘๏ธ เธฅเธเธฃเธฒเธขเธเธฒเธฃเธงเธฑเธ•เธ–เธธเธ”เธดเธ")
            to_del = st.selectbox("เน€เธฅเธทเธญเธเธงเธฑเธ•เธ–เธธเธ”เธดเธเธ—เธตเนเธเธฐเธเธณเธญเธญเธเธเธฒเธเธฃเธฐเธเธเธ–เธฒเธงเธฃ:", list(st.session_state.db_ingredients.keys()))
            if st.button("๐—‘๏ธ เธขเธทเธเธขเธฑเธเธเธณเธชเธฑเนเธเธฅเธเธงเธฑเธ•เธ–เธธเธ”เธดเธเธญเธญเธเธเธฒเธเธฃเธฐเธเธ", type="primary", use_container_width=True):
                owner_email = get_ingredient_owner_for_write(st.session_state.db_ingredients.get(to_del, {}))
                try:
                    supabase.table("ingredients").delete().eq("name", to_del).eq("owner_email", owner_email).execute()
                except:
                    pass
                del st.session_state.db_ingredients[to_del]
                st.success(f"๐”ฅ เธฅเธ '{to_del}' เธญเธญเธเธเธฒเธเธเธฅเธฑเธเน€เธฃเธตเธขเธเธฃเนเธญเธขเนเธฅเนเธง")
                st.rerun()

    # --- เนเธ—เนเธเธ—เธตเน 2: เธเธฑเธ”เธเธฒเธฃเธ—เธณเน€เธเธตเธขเธเธชเธฒเธขเธเธฑเธเธเธธเน ---
    with admin_tabs[2]:
        with st.expander("๐“ เน€เธเธดเธ”เธ”เธนเธ—เธณเน€เธเธตเธขเธเธชเธฒเธขเธเธฑเธเธเธธเนเนเธเนเนเธเนเนเธเธฃเธฐเธเธเธ—เธฑเนเธเธซเธกเธ”", expanded=True):
            st.dataframe(pd.DataFrame(st.session_state.db_breeds), use_container_width=True, hide_index=True)
            
        st.markdown("---")
        bc1, bc2 = st.columns(2, gap="large")
        
        with bc1:
            st.markdown("### โ• เน€เธเธดเนเธกเธชเธฒเธขเธเธฑเธเธเธธเนเนเธซเธกเน")
            with st.container(border=True):
                b_group = st.selectbox("เธเธฅเธธเนเธกเธชเธฒเธขเธเธฑเธเธเธธเนเธซเธฅเธฑเธ:", [g["group_name"] for g in st.session_state.db_groups])
                b_name = st.text_input("เธเธทเนเธญเธ—เธฒเธเธเธฒเธฃเธเนเธฒ (Breed Name):", placeholder="เน€เธเนเธ เนเธฎ-เน€เธเนเธเธเน เธเธฃเธฒเธงเธเน")
                b_egg = st.text_input("เธฅเธฑเธเธฉเธ“เธฐเน€เธ”เนเธ/เธชเธตเธเธญเธเน€เธเธฅเธทเธญเธเนเธเน:", placeholder="เน€เธเนเธ เน€เธเธฅเธทเธญเธเนเธเนเธชเธตเธเนเธณเธ•เธฒเธฅเน€เธเนเธก")
                b_feed = st.number_input("เธญเธฑเธ•เธฃเธฒเธเธดเธเธญเธฒเธซเธฒเธฃเธ•เธฒเธกเธเธนเนเธกเธทเธญ (เธเธฃเธฑเธก/เธ•เธฑเธง/เธงเธฑเธ):", value=115.0, step=1.0)
                if st.button("โ• เธเธฑเธเธ—เธถเธเธชเธฒเธขเธเธฑเธเธเธธเนเนเธซเธกเน", use_container_width=True, type="primary"):
                    if b_name.strip():
                        breed_payload = {"group_name": b_group, "breed_name": b_name, "egg_color": b_egg, "default_feed": b_feed}
                        st.session_state.db_breeds.append(breed_payload)
                        try:
                            supabase.table("db_breeds").insert(breed_payload).execute()
                        except Exception as cloud_err:
                            st.warning(f"เธเธฑเธเธ—เธถเธเธชเธฒเธขเธเธฑเธเธเธธเนเนเธเธซเธเนเธงเธขเธเธงเธฒเธกเธเธณเนเธฅเนเธง เนเธ•เนเธขเธฑเธเธชเนเธเธเธถเนเธ Supabase เนเธกเนเธชเธณเน€เธฃเนเธ: {cloud_err}")
                        st.success(f"๐ เน€เธเธดเนเธกเธชเธฒเธขเธเธฑเธเธเธธเน '{b_name}' เธชเธณเน€เธฃเนเธ")
                        st.rerun()
                    else: st.warning("โ ๏ธ เธเธฃเธธเธ“เธฒเธเธฃเธญเธเธเธทเนเธญเธชเธฒเธขเธเธฑเธเธเธธเน")
        with bc2:
            st.markdown("### โ เธฅเธเธเนเธญเธกเธนเธฅเธชเธฒเธขเธเธฑเธเธเธธเน")
            with st.container(border=True):
                if st.session_state.db_breeds:
                    b_del = st.selectbox("เน€เธฅเธทเธญเธเธชเธฒเธขเธเธฑเธเธเธธเนเธ—เธตเนเธ•เนเธญเธเธเธฒเธฃเธฅเธ:", [b["breed_name"] for b in st.session_state.db_breeds])
                    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
                    if st.button("๐—‘๏ธ เธขเธทเธเธขเธฑเธเธฅเธเธญเธญเธเธเธฒเธเธ—เธณเน€เธเธตเธขเธ", type="primary", use_container_width=True):
                        try:
                            supabase.table("db_breeds").delete().eq("breed_name", b_del).execute()
                        except Exception as cloud_err:
                            st.warning(f"เธฅเธเธญเธญเธเธเธฒเธเธซเธเนเธฒเธเธญเนเธฅเนเธง เนเธ•เนเธขเธฑเธเธฅเธเธเธฒเธ Supabase เนเธกเนเธชเธณเน€เธฃเนเธ: {cloud_err}")
                        st.session_state.db_breeds = [b for b in st.session_state.db_breeds if b["breed_name"] != b_del]
                        st.success(f"๐”ฅ เธฅเธเธชเธฒเธขเธเธฑเธเธเธธเน '{b_del}' เน€เธฃเธตเธขเธเธฃเนเธญเธขเนเธฅเนเธง")
                        st.rerun()
                else: st.info("เนเธกเนเธกเธตเธเนเธญเธกเธนเธฅเธชเธฒเธขเธเธฑเธเธเธธเนเนเธเธฃเธฐเธเธ")

    # --- เนเธ—เนเธเธ—เธตเน 3: เนเธเนเนเธเน€เธเนเธฒเธซเธกเธฒเธขเธเธงเธฒเธกเธ•เนเธญเธเธเธฒเธฃเนเธ เธเธเธฒเธเธฒเธฃเธชเธฑเธ•เธงเนเนเธขเธเธ•เธฒเธกเธญเธฒเธขเธธ ---
    with admin_tabs[3]:
        with st.expander("๐“ เน€เธเธดเธ”เธ”เธนเธเนเธฒเน€เธเธ“เธ‘เนเธกเธฒเธ•เธฃเธเธฒเธเนเธ เธเธเธฒเธเธฒเธฃเธชเธฑเธ•เธงเน เธ“ เธเธฑเธเธเธธเธเธฑเธ", expanded=False):
            st.dataframe(pd.DataFrame.from_dict(st.session_state.db_targets, orient='index'), use_container_width=True)
        
        st.markdown("### โ๏ธ เธเธฃเธฑเธเน€เธเธฅเธตเนเธขเธเน€เธเธ“เธ‘เนเธเนเธญเธเธณเธซเธเธ”เธชเธฒเธฃเธญเธฒเธซเธฒเธฃเธเธฑเนเธเธ•เนเธณเธเธฃเธฐเธเธณเธเนเธงเธเธญเธฒเธขเธธ")
        select_stage_crud = st.selectbox("เน€เธฅเธทเธญเธเธเนเธงเธเธฃเธฐเธขเธฐเธเธฅเธดเธ•เธเธญเธเนเธเนเนเธเนเธ—เธตเนเธ•เนเธญเธเธเธฒเธฃเนเธเนเนเธเน€เธเธ“เธ‘เน:", list(st.session_state.db_targets.keys()), format_func=lambda x: st.session_state.db_targets[x]["stage_name"])
        
        with st.form(key=f"form_target_{select_stage_crud}"):
            st.markdown(f"๐“ เธ•เธฑเนเธเธเนเธฒเน€เธเธ“เธ‘เนเธเธฑเนเธเธ•เนเธณเธชเธณเธซเธฃเธฑเธเธเนเธงเธเธญเธฒเธขเธธ: **{st.session_state.db_targets[select_stage_crud]['stage_name']}**")
            
            sc = st.columns(3)
            updated_target_values = {}
            target_nut_keys = [k for k in st.session_state.db_nutrient_keys.keys() if k != "price"]
            
            for idx, nut_key in enumerate(target_nut_keys):
                nut_info = st.session_state.db_nutrient_keys[nut_key]
                with sc[idx % 3]:
                    raw_val = st.session_state.db_targets[select_stage_crud].get(nut_key, 0.0)
                    current_target_val = float(raw_val) if raw_val is not None else 0.0
                    updated_target_values[nut_key] = st.number_input(f"เธเธฑเนเธเธ•เนเธณเธเธญเธ {nut_info['label']}:", value=current_target_val, step=nut_info["step"])
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("๐’พ เธขเธทเธเธขเธฑเธเธญเธฑเธเน€เธ”เธ•เน€เธเธ“เธ‘เนเนเธ เธเธเธฒเธเธฒเธฃเธเนเธงเธเธญเธฒเธขเธธเธเธตเน", type="primary", use_container_width=True):
                st.session_state.db_targets[select_stage_crud].update(updated_target_values)
                try:
                    supabase.table("db_targets").update(updated_target_values).eq("stage_key", select_stage_crud).execute()
                except Exception as cloud_err:
                    st.warning(f"เธญเธฑเธเน€เธ”เธ•เนเธเธซเธเนเธฒเธเธญเนเธฅเนเธง เนเธ•เนเธขเธฑเธเธชเนเธเธเธถเนเธ Supabase เนเธกเนเธชเธณเน€เธฃเนเธ: {cloud_err}")
                st.success("๐ เธญเธฑเธเน€เธ”เธ•เน€เธเธ“เธ‘เนเธกเธฒเธ•เธฃเธเธฒเธเธเธงเธฒเธกเธ•เนเธญเธเธเธฒเธฃเธ—เธฒเธเนเธ เธเธเธฒเธเธฒเธฃเน€เธฃเธตเธขเธเธฃเนเธญเธขเนเธฅเนเธง!")
                st.rerun()

    # --- เนเธ—เนเธเธ—เธตเน 4: เธเธฑเธ”เธเธฒเธฃเธชเธกเธฒเธเธดเธเธเธนเนเนเธเนเธเธฒเธ ---
    with admin_tabs[4]:
        st.subheader("๐‘ค เธชเธฃเธธเธเธเธฑเธเธเธตเธเธนเนเนเธเนเธเธฒเธเนเธเธฃเธฐเธเธ")
        
        users_list = []
        for email, info in st.session_state.user_database.items():
            role_badge = "๐”‘ ADMIN" if info.get("role") == "admin" else "๐‘ค USER"
            users_list.append({
                "Email ID / Username": email,
                "เธเธทเนเธญ-เธเธฒเธกเธชเธเธธเธฅ": f"{info.get('name', '-')} {info.get('surname', '-')}",
                "เน€เธเธญเธฃเนเนเธ—เธฃเธจเธฑเธเธ—เน": info.get("tel", "-"),
                "เธฃเธฐเธ”เธฑเธเธชเธดเธ—เธเธดเน (Role)": role_badge,
                "เธงเธฑเธเธ—เธตเนเธฅเธเธ—เธฐเน€เธเธตเธขเธ": info.get("reg_date", "2026-01-01")
            })
            
        if users_list:
            st.dataframe(pd.DataFrame(users_list), use_container_width=True, hide_index=True)
        else:
            st.info("โน๏ธ เธเธฑเธเธเธธเธเธฑเธเนเธเนเธฃเธฐเธเธเธ—เธ”เธชเธญเธเธเธณเธฅเธญเธ (เนเธกเนเธกเธตเธเธฃเธฐเธงเธฑเธ•เธดเธเธฑเธเธเธตเธเธนเนเนเธเนเธญเธทเนเธเนเธเธ•เธฒเธฃเธฒเธเธเธฑเนเธงเธเธฃเธฒเธง)")
            
        st.markdown("---")
        uc1, uc2 = st.columns(2, gap="large")
        with uc1:
            st.markdown("### โ๏ธ เน€เธเธฅเธตเนเธขเธเนเธเธฅเธเธชเธดเธ—เธเธดเนเธเธญเธเธชเธกเธฒเธเธดเธ")
            with st.container(border=True):
                user_keys = list(st.session_state.get("user_database", {}).keys())
                if not user_keys:
                    st.warning("เธขเธฑเธเนเธกเนเธกเธตเธเนเธญเธกเธนเธฅเธชเธกเธฒเธเธดเธเนเธเธฃเธฐเธเธเธซเธเนเธงเธขเธเธงเธฒเธกเธเธณเธเธฑเนเธงเธเธฃเธฒเธง")
                else:
                    selected_user_email = st.selectbox("เน€เธฅเธทเธญเธเธเธฑเธเธเธตเธญเธตเน€เธกเธฅเธ—เธตเนเธ•เนเธญเธเธเธฒเธฃเนเธเนเนเธ:", user_keys)
                    current_user_role = st.session_state.user_database[selected_user_email]["role"]
                    new_role = st.selectbox("เธฃเธฐเธเธธเธชเธดเธ—เธเธดเนเนเธซเธกเนเธ—เธตเนเธ•เนเธญเธเธเธฒเธฃเธกเธญเธเนเธซเน:", ["user", "admin"], index=0 if current_user_role == "user" else 1)
                    
                    if st.button("๐’พ เธเธฑเธเธ—เธถเธเธเธฒเธฃเน€เธเธฅเธตเนเธขเธเธชเธดเธ—เธเธดเน", use_container_width=True, type="primary"):
                        st.session_state.user_database[selected_user_email]["role"] = new_role
                        st.success(f"๐ เธญเธฑเธเน€เธ”เธ•เธชเธดเธ—เธเธดเนเธเธญเธ {selected_user_email} เน€เธเนเธ {new_role.upper()} เธชเธณเน€เธฃเนเธ")
                        st.rerun()
                
        with uc2:
            st.markdown("### โ เธฃเธฐเธเธฑเธเนเธฅเธฐเธฅเธเธเธฑเธเธเธต")
            with st.container(border=True):
                user_to_delete = st.selectbox("เน€เธฅเธทเธญเธเธเธฑเธเธเธตเธ—เธตเนเธเธฐเธฅเธเธญเธญเธเธเธฒเธเธฃเธฐเธเธเธ–เธฒเธงเธฃ:", ["-- เน€เธฅเธทเธญเธเธเธฑเธเธเธต --"] + list(st.session_state.user_database.keys()))
                if st.button("๐—‘๏ธ เธขเธทเธเธขเธฑเธเธเธณเธชเธฑเนเธเธฅเธเธเธฑเธเธเธตเธเธนเนเนเธเน", type="primary", use_container_width=True):
                    current_user = st.session_state.get("current_user_key", "").lower().strip()
                    
                    if user_to_delete == "-- เน€เธฅเธทเธญเธเธเธฑเธเธเธต --":
                        st.warning("โ ๏ธ เธเธฃเธธเธ“เธฒเน€เธฅเธทเธญเธเธเธฑเธเธเธตเธเธนเนเนเธเนเธเนเธญเธเธเธ”เธขเธทเธเธขเธฑเธ")
                    # เธเธฃเธฑเธเธเธฃเธธเธเนเธซเนเธ•เธฃเธงเธเธชเธญเธเธญเธตเน€เธกเธฅเนเธเธเน€เธ•เนเธกเธชเน€เธเธฅ เธเนเธญเธเธเธฑเธเนเธญเธ”เธกเธดเธเธฅเธเธ•เธฑเธงเน€เธญเธ
                    elif "222@gmail.com" in user_to_delete.lower() or "admin" in user_to_delete.lower():
                        st.error("โ เธเธฑเธเธเธต Root Account เธซเธฅเธฑเธเธเธญเธเธเธฒเธฃเนเธก เนเธกเนเธชเธฒเธกเธฒเธฃเธ–เธฅเธเนเธ”เน")
                    elif user_to_delete.lower().strip() == current_user:
                        st.error("โ เธเธธเธ“เนเธกเนเธชเธฒเธกเธฒเธฃเธ–เธชเธฑเนเธเธฅเธเธเธฑเธเธเธตเธ•เธฑเธงเน€เธญเธเธ—เธตเนเธเธณเธฅเธฑเธเนเธเนเธเธฒเธเธฅเนเธญเธเธญเธดเธเธญเธขเธนเนเนเธ”เน")
                    else:
                        del st.session_state.user_database[user_to_delete]
                        st.success(f"๐”ฅ เธฅเธเธเธฑเธเธเธต {user_to_delete} เน€เธฃเธตเธขเธเธฃเนเธญเธข")
                        st.rerun()
        
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("๐” เธชเธฅเธฑเธเธเธ—เธเธฒเธ—เธเธฅเธฑเธเนเธเนเธซเธกเธ”เธเธนเนเนเธเนเธเธฒเธเธ—เธฑเนเธงเนเธ (User Dashboard)", use_container_width=True):
        st.session_state.user_role = "user"
        st.rerun()
       
else:
    # ==========================================
    # ๐จ CUSTOM UI/UX FOR ALL AGES (BIG FONT & HIGH CONTRAST)
    # ==========================================
    st.markdown(
        """
        <style>
            /* เธเธขเธฒเธขเธเธเธฒเธ”เธเธญเธเธ•เนเธเธญเธเธซเธฑเธงเธเนเธญเนเธ—เนเธ */
            .stTabs [data-baseweb="tab-list"] button {
                font-size: 22px !important;
                font-weight: bold !important;
                height: 60px !important;
            }
            /* เธเธขเธฒเธขเธเธญเธเธ•เนเนเธฅเธฐเธเนเธญเธเธเธดเธกเธเนเธเนเธญเธกเธนเธฅเธ—เธฑเนเธเธซเธกเธ” */
            .stNumberInput input, .stSelectbox div, .stSlider div {
                font-size: 20px !important;
                font-weight: bold !important;
            }
            label {
                font-size: 20px !important;
                font-weight: bold !important;
                color: #f1f5f9 !important;
            }
            /* เธเธฃเธฑเธเนเธ•เนเธเธเธธเนเธกเธเธ”เนเธซเนเนเธซเธเนเน€เธเธดเนเธก เธเธดเนเธกเธเนเธฒเธขเนเธกเนเธเธฅเธฒเธ” */
            .stButton button {
                font-size: 22px !important;
                font-weight: bold !important;
                padding: 15px 20px !important;
                border-radius: 12px !important;
                min-height: 55px !important;
            }
            /* เธเธฅเนเธญเธเธเธฒเธฃเนเธ”เน€เธเนเธเธเนเธญเธเธงเธฒเธกเนเธซเนเธญเนเธฒเธเธเนเธฒเธข */
            .farmer-card {
                background-color: #1e293b;
                border: 2px solid #475569;
                padding: 22px;
                border-radius: 14px;
                margin-bottom: 20px;
            }
            /* เธชเนเธ•เธฅเนเธ•เธฑเธงเน€เธฅเธเนเธ”เธเธเธญเธฃเนเธ”เธเธเธฒเธ”เนเธซเธเนเธเธดเน€เธจเธฉ */
            .big-metric-value {
                font-size: 32px !important;
                font-weight: bold !important;
                color: #38bdf8;
            }
            .big-metric-label {
                font-size: 18px !important;
                color: #94a3b8;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    # ==========================================
    # ๐‘‘ USER ROUTE: ACCESSIBLE INTERFACE
    # ==========================================
    page_tabs = st.tabs(
        [
            "๐ฅฃ 1. เธชเธนเธ•เธฃเธญเธฒเธซเธฒเธฃ & เธเธฅเธฑเธเธชเธนเธ•เธฃเน€เธเนเธฒ",
            "๐’ฐ 2. เธเธฑเธเธ—เธถเธเธฃเธฒเธขเธงเธฑเธ & เธเธฑเธเธเธตเธเธฒเธฃเนเธก",
            "๐“ 3. เนเธเธชเธฑเนเธเธเธชเธกเธญเธฒเธซเธฒเธฃ (เธชเธณเธซเธฃเธฑเธเธเธเธเธฒเธ)",
        ]
    )

# ------------------------------------------
# ------------------------------------------
    # TAB 1: MANAGEMENT & FORMULA MATRIX
    # ------------------------------------------
    with page_tabs[0]:
        # --- เธชเนเธงเธเธ—เธตเน 1: เธ”เธถเธเธชเธนเธ•เธฃเน€เธเนเธฒ ---
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("### ๐“ [เธเธธเนเธกเธ—เธฒเธเธฅเธฑเธ”] เน€เธฃเธตเธขเธเนเธเนเธชเธนเธ•เธฃเน€เธเนเธฒเธ—เธตเนเน€เธเธขเน€เธเธเนเธงเน")
        if not st.session_state.saved_formulas:
            st.info("๐’ก เธ•เธญเธเธเธตเนเธขเธฑเธเนเธกเนเธกเธตเธชเธนเธ•เธฃเธญเธฒเธซเธฒเธฃเธ—เธตเนเธเธฑเธเธ—เธถเธเนเธงเน")
        else:
            col_load1, col_load2 = st.columns([7, 3])
            with col_load1:
                selected_f_name = st.selectbox(
                    "๐” เน€เธฅเธทเธญเธเธเธทเนเธญเธชเธนเธ•เธฃเน€เธเนเธฒเธ—เธตเนเธ•เนเธญเธเธเธฒเธฃเธ”เธน:",
                    [f["name"] for f in st.session_state.saved_formulas],
                )
            with col_load2:
                st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                if st.button("๐” เธ”เธถเธเธชเธนเธ•เธฃเธเธตเนเธกเธฒเนเธเน", use_container_width=True):
                    target_f = next(
                        f
                        for f in st.session_state.saved_formulas
                        if f["name"] == selected_f_name
                    )
                    st.session_state.current_weights = target_f["weights"].copy()
                    st.success(f"เธ”เธถเธเธเนเธญเธกเธนเธฅ '{selected_f_name}' เธกเธฒเนเธเนเธเธฒเธเนเธฅเนเธง!")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        # --- เธชเนเธงเธเธ—เธตเน 2: เน€เธฅเธทเธญเธเธชเธฒเธขเธเธฑเธเธเธธเน เนเธฅเธฐ เธ•เธฑเนเธเธเนเธฒเนเธ เธเธเธฒเธเธฒเธฃเน€เธเนเธฒเธซเธกเธฒเธขเธเธฒเธ Supabase ---
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("### ๐“ เน€เธฅเธทเธญเธเธชเธฒเธขเธเธฑเธเธเธธเนเนเธฅเธฐเนเธ เธเธเธฒเธเธฒเธฃเน€เธเนเธฒเธซเธกเธฒเธข")

        col_br1, col_br2, col_br3 = st.columns(3)
        with col_br1:
            list_groups = [g["group_name"] for g in st.session_state.db_groups]
            selected_g = st.selectbox("๐“ เน€เธฅเธทเธญเธเธเธฅเธธเนเธกเธชเธฒเธขเธเธฑเธเธเธธเนเธซเธฅเธฑเธ:", list_groups)

            # เธเธฃเธญเธเธชเธฒเธขเธเธฑเธเธเธธเนเธ•เธฒเธกเธเธฅเธธเนเธกเธ—เธตเนเน€เธฅเธทเธญเธ
            filtered_breeds = [
                b for b in st.session_state.db_breeds if b["group_name"] == selected_g
            ]
            breed_names = (
                [b["breed_name"] for b in filtered_breeds] if filtered_breeds else ["เนเธกเนเธกเธตเธเนเธญเธกเธนเธฅ"]
            )

        with col_br2:
            selected_b_name = st.selectbox("๐” เน€เธฅเธทเธญเธเธชเธฒเธขเธเธฑเธเธเธธเนเนเธเนเนเธเน:", breed_names)

            # เธ”เธถเธเธเนเธญเธกเธนเธฅเธชเธฒเธขเธเธฑเธเธเธธเนเนเธฅเธฐเน€เธเธเน€เธเนเธฒ session_state เน€เธเธทเนเธญเนเธเนเธเธฒเธเธเนเธฒเธกเนเธ—เนเธ
            current_breed_data = next(
                (b for b in filtered_breeds if b["breed_name"] == selected_b_name),
                {"id": 1, "default_feed": 114.0, "egg_color": "เนเธกเนเธฃเธฐเธเธธ"},
            )
            selected_breed_id = current_breed_data.get("id", 1)
            st.session_state["current_breed_default_feed"] = float(current_breed_data.get("default_feed", 114.0))

        with col_br3:
            # เธ”เธถเธเธ•เธฑเธงเน€เธฅเธทเธญเธเธฃเธฐเธขเธฐเธเธฒเธฃเน€เธฅเธตเนเธขเธเธเธฒเธเธเธฒเธเธเนเธญเธกเธนเธฅ db_targets
            stage_options = {
                s["stage_name"]: s["stage_key"] for s in st.session_state.db_targets.values()
            }
            selected_stage_label = st.selectbox(
                "๐“ เน€เธฅเธทเธญเธเธเนเธงเธเธฃเธฐเธขเธฐเธเธฒเธฃเนเธซเนเนเธเน:", list(stage_options.keys())
            )
            
            selected_stage_key = stage_options.get(selected_stage_label, "")
            phase_query_name = PHASE_NAME_BY_STAGE_KEY.get(
                selected_stage_key,
                selected_stage_label.split("(")[0].strip().replace("เธฃเธฐเธขเธฐเธฅเธนเธเนเธเนเนเธเน", "เธฃเธฐเธขเธฐเธฅเธนเธเนเธเน"),
            )

        # --- [เนเธเนเนเธเนเธฅเนเธง] เน€เธฃเธตเธขเธเนเธเนเธเธฒเธเธเธฑเธเธเนเธเธฑเธเธ”เธถเธเธเนเธฒเน€เธเธ“เธ‘เนเนเธ เธเธเธฒเธเธฒเธฃเธเธฒเธ Supabase เนเธเธ Real-time ---
        # ๐’ก เธเธฑเธเธเนเธเธฑเธเธ”เนเธฒเธเนเธเนเธ”เนเธฃเธฑเธเธเธฒเธฃเนเธเนเนเธเธชเธฅเธฑเธเธ•เธณเนเธซเธเนเธ .eq("เธเนเธงเธเธฃเธฐเธขเธฐเธเธฒเธฃเนเธซเนเนเธเน", selected_stage) เน€เธฃเธตเธขเธเธฃเนเธญเธขเนเธฅเนเธง
        nutrient_targets = fetch_nutrition_standards(selected_breed_id, selected_stage_key, phase_query_name)

        if nutrient_targets:
            # เธ•เธฃเธงเธเธชเธญเธเนเธฅเธฐเธ•เธฑเนเธเธเนเธฒ Default เธฅเธเนเธ session_state เธซเธฒเธเธขเธฑเธเนเธกเนเธกเธตเธเนเธญเธกเธนเธฅ
            if "base_req_protein" not in st.session_state or st.get_option("browser.gatherUsageStats") == False: 
                st.session_state["base_req_protein"] = nutrient_targets["min_protein"]
                st.session_state["base_req_me"] = nutrient_targets["min_me"]
                st.session_state["base_req_calcium"] = nutrient_targets["min_calcium"]
                st.session_state["base_req_phos"] = nutrient_targets["min_phosphorus"]

            # เธชเธฃเนเธฒเธเธเธญเธฃเนเธกเนเธซเนเธเธนเนเนเธเนเธชเธฒเธกเธฒเธฃเธ–เธเธฃเธฑเธเนเธ•เนเธเธเนเธฒเน€เธเนเธฒเธซเธกเธฒเธขเนเธ”เนเน€เธญเธเนเธ”เธขเธญเธดเธเธเนเธฒเน€เธฃเธดเนเธกเธ•เนเธเธเธฒเธ Supabase
            col_inp1, col_inp2, col_inp3, col_inp4 = st.columns(4)
            with col_inp1:
                edit_p = st.number_input("๐ฏ เนเธเธฃเธ•เธตเธเน€เธเนเธฒเธซเธกเธฒเธข (%):", min_value=5.0, value=float(st.session_state["base_req_protein"]), step=0.1)
            with col_inp2:
                edit_m = st.number_input("๐ฏ เธเธฅเธฑเธเธเธฒเธเน€เธเนเธฒเธซเธกเธฒเธข (kcal/kg):", min_value=1000.0, value=float(st.session_state["base_req_me"]), step=25.0)
            with col_inp3:
                edit_c = st.number_input("๐ฏ เนเธเธฅเน€เธเธตเธขเธกเน€เธเนเธฒเธซเธกเธฒเธข (%):", min_value=0.5, value=float(st.session_state["base_req_calcium"]), step=0.05)
            with col_inp4:
                edit_ph = st.number_input("๐ฏ เธเธญเธชเธเธญเธฃเธฑเธชเน€เธเนเธฒเธซเธกเธฒเธข (%):", min_value=0.1, value=float(st.session_state["base_req_phos"]), step=0.02)

            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            if st.button("โก เธชเธฑเนเธ AI เธเธณเธเธงเธ“เธชเธนเธ•เธฃเธ”เนเธงเธ", type="primary", use_container_width=True):
                with st.spinner("AI เธเธณเธฅเธฑเธเธเธฑเธ”เธชเธนเธ•เธฃ..."):
                    # เธเธฃเธฑเธเธเธธเธ”เน€เธเนเธฒเธซเธกเธฒเธขเธชเธฒเธฃเธญเธฒเธซเธฒเธฃเธชเนเธเน€เธเนเธฒ Solver เธ•เธฒเธกเธ—เธตเนเธเธนเนเนเธเนเนเธเนเนเธเน€เธเธดเนเธกเน€เธ•เธดเธก
                    custom_targets = nutrient_targets.copy()
                    custom_targets["min_protein"] = edit_p
                    custom_targets["min_me"] = edit_m
                    custom_targets["min_calcium"] = edit_c
                    custom_targets["min_phosphorus"] = edit_ph
                    
                    st.session_state.current_weights = run_ai_solver(custom_targets)
                    st.rerun()
        else:
            st.error(f"โ เนเธกเนเธเธเน€เธเธ“เธ‘เนเธกเธฒเธ•เธฃเธเธฒเธเนเธ เธเธเธฒเธเธฒเธฃเธชเธณเธซเธฃเธฑเธเธชเธฒเธขเธเธฑเธเธเธธเน {selected_b_name} เธฃเธฐเธขเธฐ {phase_query_name} เธเธเธเธฒเธเธเนเธญเธกเธนเธฅ")
        st.markdown("</div>", unsafe_allow_html=True)

        # --- เธชเนเธงเธเธ—เธตเน 3: เธเธธเนเธกเธฅเธฑเธ”เธ•เธฒเธกเธชเธ–เธฒเธเธเธฒเธฃเธ“เนเธฃเธฒเธเธฒเธ•เธฅเธฒเธ” ---
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("### โก [เธเธ”เธ”เนเธงเธ] เธเธธเนเธกเธฅเธฑเธ”เธชเธฅเธฑเธเธชเธนเธ•เธฃเธญเธฒเธซเธฒเธฃเธ•เธฒเธกเธชเธ–เธฒเธเธเธฒเธฃเธ“เนเธฃเธฒเธเธฒเธ•เธฅเธฒเธ”")
        sc_col1, sc_col2, sc_col3 = st.columns(3)

        if not st.session_state.current_weights and nutrient_targets:
            st.session_state.current_weights = run_ai_solver(nutrient_targets)

        with sc_col1:
            if st.button("๐ข เนเธซเธกเธ”เธเธเธ•เธด / เน€เธเนเธเธ–เธนเธเธชเธธเธ”", use_container_width=True) and nutrient_targets:
                st.session_state.current_weights = run_ai_solver(nutrient_targets)
                st.rerun()
        with sc_col2:
            if st.button("๐พ เนเธซเธกเธ”เธเนเธฒเธงเนเธเธ” / เธฃเธณเธเนเธฒเธงเนเธเธ", use_container_width=True) and nutrient_targets:
                raw_weights = run_ai_solver(nutrient_targets)
                if "เธเนเธฒเธงเนเธเธ”" in raw_weights:
                    raw_weights["เธเนเธฒเธงเนเธเธ”"] = max(0.0, raw_weights["เธเนเธฒเธงเนเธเธ”"] - 20.0)
                if "เธฃเธณเธเนเธฒเธงเธฅเธฐเน€เธญเธตเธขเธ”" in raw_weights:
                    raw_weights["เธฃเธณเธเนเธฒเธงเธฅเธฐเน€เธญเธตเธขเธ”"] = max(0.0, raw_weights["เธฃเธณเธเนเธฒเธงเธฅเธฐเน€เธญเธตเธขเธ”"] - 10.0)
                if "เธเธฅเธฒเธขเธเนเธฒเธง" in raw_weights:
                    raw_weights["เธเธฅเธฒเธขเธเนเธฒเธง"] += 15.0
                if "เธกเธฑเธเน€เธชเนเธ" in raw_weights:
                    raw_weights["เธกเธฑเธเน€เธชเนเธ"] += 15.0
                st.session_state.current_weights = raw_weights
                st.rerun()
        with sc_col3:
            if st.button("๐ฅ เนเธซเธกเธ”เน€เธฃเนเธเนเธเนเนเธซเธเน / เน€เธเธฅเธทเธญเธเธซเธเธฒ", use_container_width=True) and nutrient_targets:
                # เธเธฃเธฑเธเน€เธเธดเนเธกเน€เธเธ“เธ‘เนเนเธเธฃเธ•เธตเธเนเธฅเธฐเนเธเธฅเน€เธเธตเธขเธกเธเธฑเนเธงเธเธฃเธฒเธงเธชเธณเธซเธฃเธฑเธเนเธซเธกเธ”เน€เธฃเนเธเนเธเน
                boosted_targets = nutrient_targets.copy()
                boosted_targets["min_protein"] += 0.5
                boosted_targets["min_calcium"] += 0.3
                raw_weights = run_ai_solver(boosted_targets)
                if "เธเนเธณเธกเธฑเธเธเธฒเธฅเนเธก" in raw_weights:
                    raw_weights["เธเนเธณเธกเธฑเธเธเธฒเธฅเนเธก"] = max(2.0, raw_weights["เธเนเธณเธกเธฑเธเธเธฒเธฅเนเธก"])
                if "เน€เธเธฅเธทเธญเธเธซเธญเธขเธเธ”" in raw_weights:
                    raw_weights["เน€เธเธฅเธทเธญเธเธซเธญเธขเธเธ”"] = max(8.0, raw_weights["เน€เธเธฅเธทเธญเธเธซเธญเธขเธเธ”"])
                st.session_state.current_weights = raw_weights
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        # --- เธชเนเธงเธเธ—เธตเน 4: เนเธ–เธเธเธฃเธฑเธเธชเธฑเธ”เธชเนเธงเธเธญเธฒเธซเธฒเธฃเนเธเธ 2 เธเธญเธฅเธฑเธกเธเนเธขเนเธญเธข เนเธฅเธฐเธ•เธฒเธฃเธฒเธเธเธฅเธฅเธฑเธเธเน ---
        col_left, col_right = st.columns([1.1, 0.9])

        # เธเธณเธเธงเธ“เธ•เนเธเธ—เธธเธเธฅเนเธงเธเธซเธเนเธฒเน€เธเธทเนเธญเนเธซเนเธเธฅเนเธญเธเธ”เนเธฒเธเธเนเธฒเธข/เธเธงเธฒเธชเธฒเธกเธฒเธฃเธ–เน€เธเนเธฒเธ–เธถเธเธ•เธฑเธงเนเธเธฃ net_cost เนเธ”เนเธญเธขเนเธฒเธเธ–เธนเธเธ•เนเธญเธ
        net_cost = 0.0
        act_nut = {"protein": 0.0, "me": 0.0, "calcium": 0.0, "phos": 0.0}
        total_w = sum(st.session_state.current_weights.values())
        divisor = total_w if total_w > 0 else 1.0

        for name, w in st.session_state.current_weights.items():
            if name in st.session_state.db_ingredients:
                ratio = w / divisor
                net_cost += ratio * float(st.session_state.db_ingredients[name]["price"])
                for k in act_nut.keys():
                    act_nut[k] += ratio * float(
                        st.session_state.db_ingredients[name].get(k, 0.0)
                    )

        with col_left:
            st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
            cl_title, cl_reset = st.columns([6, 4])
            with cl_title:
                st.markdown("### ๐ฅฃ เนเธ–เธเธเธฃเธฑเธเธชเธฑเธ”เธชเนเธงเธเธงเธฑเธ•เธ–เธธเธ”เธดเธ (%)")
            with cl_reset:
                if st.button("๐” เธฃเธตเน€เธเนเธ•เธเนเธฒเนเธซเธกเนเธ—เธฑเนเธเธซเธกเธ”", use_container_width=True) and nutrient_targets:
                    st.session_state.current_weights = run_ai_solver(nutrient_targets)
                    st.rerun()

            temp_weights = {}
            running_total = 0.0
            inclusion_limits = {
                "เธเธฒเธเน€เธเธตเธขเธฃเนเนเธซเนเธ": 10.0,
                "เธเธฒเธเธเนเธณเธ•เธฒเธฅ": 5.0,
                "เธเนเธณเธกเธฑเธเธเธฒเธฅเนเธก": 4.0,
                "เธเนเธณเธกเธฑเธเธ–เธฑเนเธงเน€เธซเธฅเธทเธญเธ": 4.0,
                "เธเนเธฒเธงเธเธ": 15.0,
                "เธเธฒเธเธ”เธตเธ”เธตเธเธตเน€เธญเธช": 15.0,
                "DDGS": 15.0,
            }

            # เธเธฃเธฑเธเนเธเนเธเธ•เธฑเธง Slider เธงเธฑเธ•เธ–เธธเธ”เธดเธเธญเธญเธเน€เธเนเธ 2 เธเธญเธฅเธฑเธกเธเนเธขเนเธญเธข
            ing_keys = list(st.session_state.db_ingredients.keys())
            ing_col1, ing_col2 = st.columns(2)

            for idx, name in enumerate(ing_keys):
                d = st.session_state.db_ingredients[name]
                saved_w = float(st.session_state.current_weights.get(name, 0.0))
                saved_w = max(0.0, min(100.0, saved_w))

                target_col = ing_col1 if idx % 2 == 0 else ing_col2
                with target_col:
                    user_val = st.slider(
                        f"๐ฝ {name} ({d['price']} เธ.)",
                        min_value=0.0,
                        max_value=100.0,
                        value=saved_w,
                        step=0.1,
                        key=f"sld_user_{name}",
                    )
                    if name in inclusion_limits and user_val > inclusion_limits[name]:
                        st.markdown(
                            f"<p style='color:#f87171; font-size:14px; font-weight:bold; margin:-8px 0px 10px 0px;'>โ ๏ธ เธซเนเธฒเธกเน€เธเธดเธ {inclusion_limits[name]}% เนเธเนเธเธฐเธ—เนเธญเธเน€เธชเธตเธข</p>",
                            unsafe_allow_html=True,
                        )

                temp_weights[name] = user_val
                running_total += user_val

            st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
            if abs(running_total - 100.0) > 0.1:
                st.markdown(
                    f"<div style='background-color:#991b1b; padding:15px; border-radius:8px; font-size:18px; font-weight:bold; text-align:center;'>โ ๏ธ เธชเธฑเธ”เธชเนเธงเธเธญเธฒเธซเธฒเธฃเธฃเธงเธกเนเธ”เน: {running_total:.1f}% (เธเธฃเธธเธ“เธฒเธเธฃเธฑเธเนเธซเนเธเธฃเธ 100%)</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div style='background-color:#065f46; padding:15px; border-radius:8px; font-size:18px; font-weight:bold; text-align:center;'>๐ข เธชเนเธงเธเธเธชเธกเธเธฃเธเธ–เนเธงเธเธชเธกเธเธนเธฃเธ“เน 100%</div>",
                    unsafe_allow_html=True,
                )

            st.session_state.current_weights = temp_weights
            st.markdown("</div>", unsafe_allow_html=True)

        with col_right:
            st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
            st.markdown("### ๐งช เธเธฅเธฅเธฑเธเธเนเนเธ เธเธเธฒเธเธฒเธฃเธเธฃเธดเธเนเธเธชเธนเธ•เธฃ")

            # เนเธชเธ”เธเน€เธเธฃเธตเธขเธเน€เธ—เธตเธขเธเธเนเธฒเน€เธเนเธฒเธซเธกเธฒเธขเธ—เธตเนเธ”เธถเธเธกเธฒเธเธฒเธเธเธธเธ”เธเนเธญเธกเธนเธฅ Supabase เธเธฃเธดเธ
            target_p_val = edit_p if nutrient_targets else 16.5
            target_m_val = edit_m if nutrient_targets else 2750

            comparison_table = [
                {
                    "เนเธ เธเธเธฒเธเธฒเธฃเธชเธณเธเธฑเธ": "เนเธเธฃเธ•เธตเธเธ”เธดเธ (% CP)",
                    "เน€เธเนเธฒเธซเธกเธฒเธข": f"{target_p_val:.2f} %",
                    "เนเธ”เนเธเธฃเธดเธเนเธเธชเธนเธ•เธฃ": f"{act_nut['protein']:.2f} %",
                },
                {
                    "เนเธ เธเธเธฒเธเธฒเธฃเธชเธณเธเธฑเธ": "เธเธฅเธฑเธเธเธฒเธเนเธเนเธเธฃเธฐเนเธขเธเธเน (ME)",
                    "เน€เธเนเธฒเธซเธกเธฒเธข": f"{target_m_val:.0f}",
                    "เนเธ”เนเธเธฃเธดเธเนเธเธชเธนเธ•เธฃ": f"{act_nut['me']:.0f}",
                },
                {
                    "เนเธ เธเธเธฒเธเธฒเธฃเธชเธณเธเธฑเธ": "เนเธเธฅเน€เธเธตเธขเธก (% Ca)",
                    "เน€เธเนเธฒเธซเธกเธฒเธข": f"{edit_c:.2f} %" if nutrient_targets else "3.80 %",
                    "เนเธ”เนเธเธฃเธดเธเนเธเธชเธนเธ•เธฃ": f"{act_nut['calcium']:.2f} %",
                },
                {
                    "เนเธ เธเธเธฒเธเธฒเธฃเธชเธณเธเธฑเธ": "เธเธญเธชเธเธญเธฃเธฑเธช (% P)",
                    "เน€เธเนเธฒเธซเธกเธฒเธข": f"{edit_ph:.2f} %" if nutrient_targets else "0.45 %",
                    "เนเธ”เนเธเธฃเธดเธเนเธเธชเธนเธ•เธฃ": f"{act_nut['phos']:.2f} %",
                },
            ]
            st.dataframe(
                pd.DataFrame(comparison_table), use_container_width=True, hide_index=True
            )

            st.markdown(
                f"<div style='background-color:#1e293b; padding:15px; border-radius:10px; border:2px solid #38bdf8; text-align:center; font-size:24px; font-weight:bold; margin: 15px 0;'>๐’ฐ เธ•เนเธเธ—เธธเธเธเนเธฒเธญเธฒเธซเธฒเธฃเธชเธนเธ•เธฃเธเธตเน: {net_cost:.2f} เธเธฒเธ—/เธเธ.</div>",
                unsafe_allow_html=True,
            )

            breed_display_name = (
                selected_b_name.split()[-1]
                if len(selected_b_name.split()) > 1
                else selected_b_name
            )
            save_name_input = st.text_input(
                "๐’พ เธ•เธฑเนเธเธเธทเนเธญเน€เธฅเนเธเธชเธนเธ•เธฃเธญเธฒเธซเธฒเธฃเน€เธเธทเนเธญเธเธ”เน€เธเธ:",
                value=f"เธชเธนเธ•เธฃ {breed_display_name} {net_cost:.1f} เธเธฒเธ—",
            )
            if st.button("๐“ฅ เธขเธทเธเธขเธฑเธเธเธ”เธเธฑเธเธ—เธถเธเธชเธนเธ•เธฃเธญเธฒเธซเธฒเธฃเธฅเธเธเธฅเธฑเธ", use_container_width=True):
                formula_data = {
                    "date": str(datetime.date.today()),
                    "name": save_name_input,
                    "cost": round(net_cost, 2),
                    "breed": selected_b_name,
                    "stage": selected_stage_label,
                    "protein": round(act_nut["protein"], 2),
                    "me": round(act_nut["me"], 0),
                    "calcium": round(act_nut["calcium"], 2),
                    "weights": st.session_state.current_weights.copy(),
                }
                if save_formula_to_supabase(formula_data):
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------
    # TAB 2: DAILY LOG & CASHFLOW
    # ------------------------------------------
    with page_tabs[1]:
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown(
            "<h2>โ€๏ธ เธเธฑเธเธ—เธถเธเธ•เธฑเธงเธเธตเนเธงเธฑเธ”เธเธฒเธฃเนเธก & เธฃเธฒเธขเธฃเธฑเธ-เธฃเธฒเธขเธเนเธฒเธขเธเธฃเธฐเธเธณเธงเธฑเธ</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='border-bottom: 2px solid #475569; margin:15px 0;'></div>",
            unsafe_allow_html=True,
        )

        if st.session_state.daily_logs:
            if st.button(
                "๐“ เธ”เธถเธเธเนเธญเธกเธนเธฅเธเธฒเธเธเธฃเธฐเธงเธฑเธ•เธดเธฅเนเธฒเธชเธธเธ” (เนเธกเนเธ•เนเธญเธเธเธดเธกเธเนเนเธซเธกเนเธซเธกเธ”)", use_container_width=True
            ):
                last_log = st.session_state.daily_logs[-1]
                st.session_state["shortcut_birds"] = last_log["เธเธณเธเธงเธเนเธเน (เธ•เธฑเธง)"]
                st.session_state["shortcut_price"] = (
                    last_log["เธฃเธฒเธขเนเธ”เนเธเธฒเธขเนเธเน (เธเธฒเธ—)"] / last_log["เนเธเนเธ—เธตเนเน€เธเนเธเนเธ”เน (เธเธญเธ)"]
                    if last_log["เนเธเนเธ—เธตเนเน€เธเนเธเนเธ”เน (เธเธญเธ)"] > 0
                    else 4.10
                )
                st.success("เธ”เธถเธเธเนเธญเธกเธนเธฅเน€เธ”เธดเธกเน€เธฃเธตเธขเธเธฃเนเธญเธข! เธเธฃเธธเธ“เธฒเธ•เธฃเธงเธเธชเธญเธเนเธฅเธฐเธญเธฑเธเน€เธ”เธ•เธเธณเธเธงเธเนเธเนเธเธฃเธฐเธเธณเธงเธฑเธเธเธตเน")

        log_col1, log_col2 = st.columns(2)
        with log_col1:
            st.markdown("#### ๐“ เธชเนเธงเธเธ—เธตเน 1: เธเนเธญเธกเธนเธฅเธเธนเธเนเธเนเธงเธฑเธเธเธตเน")
            log_date = st.date_input(
                "เธงเธฑเธเธ—เธตเนเธเธฑเธเธ—เธถเธเธเนเธญเธกเธนเธฅ:", datetime.date.today(), key="farm_log_date"
            )
            flock_age_weeks = st.number_input(
                "๐ฃ เธญเธฒเธขเธธเธเธนเธเนเธเนเธเธฑเธเธเธธเธเธฑเธ (เธชเธฑเธเธ”เธฒเธซเน):", min_value=1, max_value=100, value=25, step=1
            )

            default_birds = st.session_state.get("shortcut_birds", 1000)
            bird_count = st.number_input(
                "เธเธณเธเธงเธเนเธเนเนเธเนเธ—เธฑเนเธเธซเธกเธ”เนเธเน€เธฅเนเธฒเธงเธฑเธเธเธตเน (เธ•เธฑเธง):",
                min_value=1,
                value=int(default_birds),
                step=100,
            )
            env_temp = st.slider(
                "๐ก๏ธ เธญเธธเธ“เธซเธ เธนเธกเธดเธชเธนเธเธชเธธเธ”เนเธเน€เธฅเนเธฒเธงเธฑเธเธเธตเน (ยฐC):",
                15.0,
                45.0,
                28.0,
                step=0.5,
                key="temp_slider",
            )

            # เธ”เธถเธเธเนเธฒเนเธเธฐเธเธณเธเธฃเธดเธกเธฒเธ“เธญเธฒเธซเธฒเธฃเธเธฃเธดเธเนเธเธ Dynamic เธเธฒเธเธฃเธฒเธขเธชเธฒเธขเธเธฑเธเธเธธเนเธ—เธตเนเน€เธฅเธทเธญเธเนเธงเนเนเธเธ•เธฒเธฃเธฒเธ Supabase
            breed_default_feed = st.session_state.get("current_breed_default_feed", 114.0)
            recommended_feed = float(bird_count * breed_default_feed / 1000.0)
            st.markdown(
                f"<p style='color:#6366f1; font-size:16px; font-weight:bold; margin-bottom:-5px;'>๐’ก เธเธฃเธดเธกเธฒเธ“เธญเธฒเธซเธฒเธฃเนเธเธฐเธเธณเธ•เธฒเธกเธชเธฒเธขเธเธฑเธเธเธธเน {selected_b_name}: {recommended_feed:,.1f} เธเธ. ({breed_default_feed} เธเธฃเธฑเธก/เธ•เธฑเธง/เธงเธฑเธ)</p>",
                unsafe_allow_html=True,
            )
            actual_feed_given_kg = st.number_input(
                "๐ฝ๏ธ เธเนเธณเธซเธเธฑเธเธญเธฒเธซเธฒเธฃเธ—เธตเนเนเธซเนเนเธเนเธเธดเธเธฃเธงเธกเธงเธฑเธเธเธตเน (เธเธดเนเธฅเธเธฃเธฑเธก):",
                min_value=10.0,
                value=recommended_feed,
                step=10.0,
            )

        with log_col2:
            st.markdown("#### ๐’ฐ เธชเนเธงเธเธ—เธตเน 2: เธเธณเธเธงเธเนเธเนเนเธฅเธฐเธฃเธฒเธเธฒเธชเนเธเธงเธฑเธเธเธตเน")
            collected_eggs = st.number_input(
                "เธเธณเธเธงเธเธเธญเธเนเธเนเธ—เธตเนเน€เธเนเธเนเธ”เนเธเธฃเธดเธเธงเธฑเธเธเธตเน (เธเธญเธ):", min_value=0, value=850
            )

            default_price = st.session_state.get("shortcut_price", 4.10)
            egg_sale_price = st.number_input(
                "๐’ต เธฃเธฒเธเธฒเธฃเธฑเธเธเธทเนเธญเนเธเนเธซเธเนเธฒเธเธฒเธฃเนเธกเธงเธฑเธเธเธตเน (เธเธฒเธ—/เธเธญเธ):",
                min_value=1.0,
                value=float(default_price),
                step=0.1,
            )
            dead_birds = st.number_input(
                "เธเธณเธเธงเธเนเธเนเธ•เธฒเธข/เธเธฑเธ”เธ—เธดเนเธเธงเธฑเธเธเธตเน (เธ•เธฑเธง):", min_value=0, value=1
            )
            avg_egg_weight_g = st.number_input(
                "โ–๏ธ เธเนเธณเธซเธเธฑเธเนเธเนเน€เธเธฅเธตเนเธขเธงเธฑเธเธเธตเน (เธเธฃเธฑเธก/เธเธญเธ):",
                min_value=30.0,
                max_value=80.0,
                value=62.0,
                step=0.5,
                key="avg_egg_weight_g_input"
            )

            if env_temp <= 20.0:
                water_per_bird_ml = 160.0
            elif env_temp <= 28.0:
                water_per_bird_ml = 200.0 + (env_temp - 20.0) * 7.5
            elif env_temp <= 32.0:
                water_per_bird_ml = 260.0 + (env_temp - 28.0) * 15.0
            else:
                water_per_bird_ml = 320.0 + (env_temp - 32.0) * 25.0
            total_water_needed_liters = (water_per_bird_ml * bird_count) / 1000.0

        # ๐“ เธฃเธฐเธเธเธเธเธดเธ—เธดเธเน€เธ•เธทเธญเธเธเธงเธฒเธกเธเธณเธงเธฑเธเธเธตเธเนเธฅเธฐเธเธฒเธเธฃเธนเธ—เธตเธเธ•เธฒเธกเธเนเธงเธเธญเธฒเธขเธธเนเธเน
        st.markdown(
            "<div style='background-color:#1e1b4b; padding:20px; border-radius:12px; border:2px solid #6366f1; margin: 20px 0;'>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"### ๐“ เธเธเธดเธ—เธดเธเน€เธ•เธทเธญเธเธเธฒเธเธชเธณเธเธฑเธเธชเธณเธซเธฃเธฑเธเนเธเนเธญเธฒเธขเธธ {flock_age_weeks} เธชเธฑเธเธ”เธฒเธซเน:"
        )
        if flock_age_weeks <= 3:
            st.markdown("<p style='color:#38bdf8; font-size:22px; font-weight:bold;'>โ€ข เธ•เนเธญเธเธ—เธณเธงเธฑเธเธเธตเธเธเธดเธงเธเธฒเธชเน€เธเธดเธฅ + เธซเธฅเธญเธ”เธฅเธกเธญเธฑเธเน€เธชเธ เนเธฅเธฐเธ•เธฃเธงเธเน€เธเนเธเธฃเธฐเธเธเนเธเธเธ</p>", unsafe_allow_html=True)
        elif flock_age_weeks <= 8:
            st.markdown("<p style='color:#38bdf8; font-size:22px; font-weight:bold;'>โ€ข เธ•เนเธญเธเธ—เธณเธงเธฑเธเธเธตเธเธเธตเธ”เธฒเธฉ เนเธฅเธฐเธ—เธณเธงเธฑเธเธเธตเธเธญเธซเธดเธงเธฒเธ•เนเนเธเนเธฃเธญเธเธ—เธตเน 1</p>", unsafe_allow_html=True)
        elif flock_age_weeks <= 16:
            st.markdown("<p style='color:#38bdf8; font-size:22px; font-weight:bold;'>โ€ข เธ•เนเธญเธเธ–เนเธฒเธขเธเธขเธฒเธเธดเนเธเนเธเนเธญเธเธขเนเธฒเธขเน€เธเนเธฒเธเธฃเธเธ•เธฑเธ เนเธฅเธฐเธ—เธณเธงเธฑเธเธเธตเธเธฃเธงเธกเธเนเธญเธเน€เธฃเธดเนเธกเนเธเน</p>", unsafe_allow_html=True)
        elif flock_age_weeks <= 24:
            st.markdown("<p style='color:#fbbf24; font-size:22px; font-weight:bold;'>โ€ข เนเธเนเน€เธฃเธดเนเธกเนเธเนเนเธฅเนเธง: [เธฃเธฐเธงเธฑเธ] เธซเนเธฒเธกเธฅเธ”เนเธชเธเธชเธงเนเธฒเธเนเธเน€เธฅเนเธฒเน€เธ”เนเธ”เธเธฒเธ”! เนเธงเธเนเธชเธเธ•เนเธญเธเธชเธกเนเธณเน€เธชเธกเธญ</p>", unsafe_allow_html=True)
        elif flock_age_weeks <= 60:
            st.markdown("<p style='color:#10b981; font-size:22px; font-weight:bold;'>โ€ข เธเนเธงเธเนเธเนเธ”เธ: เธชเธธเนเธกเน€เธเนเธเธเธงเธฒเธกเธซเธเธฒเน€เธเธฅเธทเธญเธเนเธเน เนเธฅเธฐเธฅเนเธฒเธเธ—เธณเธเธงเธฒเธกเธชเธฐเธญเธฒเธ”เธซเธฑเธงเธเธดเธเน€เธเธดเนเธฅเธเนเธณเธ—เธธเธเธชเธฑเธเธ”เธฒเธซเน</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p style='color:#f87171; font-size:22px; font-weight:bold;'>โ€ข เนเธเนเนเธเนเธ—เนเธฒเธขเธเธธเธ”: เนเธซเนเธเธเธเธฒเธเน€เธชเธฃเธดเธกเน€เธเธฅเธทเธญเธเธซเธญเธขเธเธ”เนเธเธฃเธฒเธเธเนเธงเธเน€เธขเนเธ เธเนเธญเธเธเธฑเธเนเธเนเน€เธเธฅเธทเธญเธเธเธฒเธเนเธ•เธเธซเธฑเธ</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            "<div style='border-bottom: 2px dashed #475569; margin:20px 0;'></div>",
            unsafe_allow_html=True,
        )

        # ๐’ฐ เน€เธกเธ—เธฃเธดเธเธเนเธเธณเธเธงเธ“เธ•เนเธเธ—เธธเธเธเธฒเธฃเน€เธเธดเธเธซเธเนเธฒเธเธฒเธฃเนเธกเธชเธธเธ—เธเธด
        total_revenue = collected_eggs * egg_sale_price
        total_feed_cost = actual_feed_given_kg * net_cost
        net_profit_day = total_revenue - total_feed_cost

        henday_pct = (collected_eggs / bird_count) * 100.0 if bird_count > 0 else 0.0
        total_egg_mass_kg = (collected_eggs * avg_egg_weight_g) / 1000.0
        fcr_ratio = (
            actual_feed_given_kg / total_egg_mass_kg if total_egg_mass_kg > 0 else 0.0
        )
        cost_per_egg = total_feed_cost / collected_eggs if collected_eggs > 0 else 0.0

        # ๐จ SAFETY GUARDRAILS: เธ•เธฃเธงเธเธเธฑเธเธชเธฑเธเธเธฒเธ“เธญเธฑเธเธ•เธฃเธฒเธขเธซเธเนเธฒเธเธฒเธฃเนเธกเธญเธฑเธ•เนเธเธกเธฑเธ•เธด
        if henday_pct < 65.0 and henday_pct > 0:
            st.markdown(
                f"<div style='background-color:#7c2d12; padding:15px; border-radius:8px; font-size:18px; font-weight:bold; margin-bottom:15px;'>โ ๏ธ เน€เธ•เธทเธญเธ: เน€เธเธญเธฃเนเน€เธเนเธเธ•เนเธเธฒเธฃเนเธเนเธ•เนเธณเธเธงเนเธฒเน€เธเธ“เธ‘เนเธกเธฒเธ•เธฃเธเธฒเธ ({henday_pct:.1f}%) เธ•เธฃเธงเธเน€เธเนเธเธเธคเธ•เธดเธเธฃเธฃเธกเธเธฒเธฃเธเธดเธเนเธฅเธฐเธชเธธเนเธกเธเธฑเธ”เนเธเนเธเนเธงเธขเธ”เนเธงเธ</div>",
                unsafe_allow_html=True,
            )
        if dead_birds > (bird_count * 0.001):
            st.markdown(
                f"<div style='background-color:#991b1b; padding:15px; border-radius:8px; font-size:18px; font-weight:bold; margin-bottom:15px;'>๐จ เธงเธดเธเธคเธ•: เธงเธฑเธเธเธตเนเนเธเนเธ•เธฒเธขเธเธดเธ”เธเธเธ•เธด ({dead_birds} เธ•เธฑเธง) เธชเธนเธเน€เธเธดเธเน€เธเธ“เธ‘เน เธฃเธฐเธงเธฑเธเธชเธ เธฒเธเธญเธฒเธเธฒเธจเธฃเนเธญเธเธเธฑเธ”เธซเธฃเธทเธญเนเธฃเธเธฃเธฐเธเธฒเธ”เธ•เธดเธ”เธ•เนเธญ!</div>",
                unsafe_allow_html=True,
            )
        if env_temp >= 32.0:
            st.error(
                f"๐จ เน€เธฅเนเธฒเธฃเนเธญเธเธเธฑเธ” ({env_temp}ยฐC) เนเธเนเน€เธชเธตเนเธขเธเธเนเธญเธเธ•เธฒเธข! เธเธเธเธฒเธเธ•เนเธญเธเน€เธเธดเธ”เธฃเธฐเธเธเธเนเธเธซเธกเธญเธเนเธฅเธฐเน€เธฃเนเธเธเธฑเธ”เธฅเธกเธ—เธฑเธเธ—เธต (เธเธฃเธดเธกเธฒเธ“เธเนเธณเธ—เธตเนเธเธนเธเนเธเนเธ•เนเธญเธเธเธดเธเธเธฑเนเธเธ•เนเธณ: {total_water_needed_liters:,.1f} เธฅเธดเธ•เธฃ)"
            )

        st.markdown("### ๐“ เธชเธฃเธธเธเธเธฅเธเธณเนเธฃเธชเธธเธ—เธเธดเนเธฅเธฐเธ•เธฑเธงเธเธตเนเธงเธฑเธ”เธงเธฑเธเธเธตเน")
        profit_box_color = "#065f46" if net_profit_day >= 0 else "#991b1b"
        st.markdown(
            f"<div style='background-color:{profit_box_color}; padding:20px; border-radius:12px; text-align:center; font-size:26px; font-weight:bold; margin-bottom:20px;'>๐’ธ เน€เธเธดเธเธเธณเนเธฃเธชเธธเธ—เธเธดเธเธฃเธฐเธเธณเธงเธฑเธ (เธซเธฑเธเธเนเธฒเธญเธฒเธซเธฒเธฃเนเธฅเนเธง): {net_profit_day:,.2f} เธเธฒเธ—</div>",
            unsafe_allow_html=True,
        )

        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.markdown(
                f"<div style='background-color:#0f172a; padding:15px; border-radius:10px; border:1px solid #334155; text-align:center;'><span class='big-metric-label'>๐ฅ เน€เธเธญเธฃเนเน€เธเนเธเธ•เนเธเธฒเธฃเนเธเน</span><br><span class='big-metric-value'>{henday_pct:.1f} %</span></div>",
                unsafe_allow_html=True,
            )
        with m_col2:
            st.markdown(
                f"<div style='background-color:#0f172a; padding:15px; border-radius:10px; border:1px solid #334155; text-align:center;'><span class='big-metric-label'>๐ฅฃ เธญเธฑเธ•เธฃเธฒเนเธฅเธเนเธเน (FCR)</span><br><span class='big-metric-value'>{fcr_ratio:.2f}</span></div>",
                unsafe_allow_html=True,
            )
        with m_col3:
            st.markdown(
                f"<div style='background-color:#0f172a; padding:15px; border-radius:10px; border:1px solid #334155; text-align:center;'><span class='big-metric-label'>๐ฅ เธเนเธฒเธญเธฒเธซเธฒเธฃเธ•เนเธญเนเธเน 1 เธเธญเธ</span><br><span class='big-metric-value'>{cost_per_egg:.2f} เธเธฒเธ—</span></div>",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)

        if st.button("๐’พ เธเธ”เธเธธเนเธกเธเธตเนเน€เธเธทเนเธญเธเธฑเธเธ—เธถเธเธเธฃเธฐเธงเธฑเธ•เธดเธเธฃเธฐเธเธณเธงเธฑเธ", use_container_width=True):
            st.session_state.daily_logs.append(
                {
                    "เธงเธฑเธเธ—เธตเน": str(log_date),
                    "เธญเธฒเธขเธธเธเธนเธ (เธชเธฑเธเธ”เธฒเธซเน)": flock_age_weeks,
                    "เธเธณเธเธงเธเนเธเน (เธ•เธฑเธง)": bird_count,
                    "เธญเธธเธ“เธซเธ เธนเธกเธด (ยฐC)": env_temp,
                    "เธญเธฒเธซเธฒเธฃเธ—เธตเนเธเธดเธ (KG)": actual_feed_given_kg,
                    "เนเธเนเธ—เธตเนเน€เธเนเธเนเธ”เน (เธเธญเธ)": collected_eggs,
                    "เธฃเธฒเธขเนเธ”เนเธเธฒเธขเนเธเน (เธเธฒเธ—)": round(total_revenue, 2),
                    "เธ•เนเธเธ—เธธเธเธญเธฒเธซเธฒเธฃ (เธเธฒเธ—)": round(total_feed_cost, 2),
                    "เธเธณเนเธฃเธชเธธเธ—เธเธด (เธเธฒเธ—)": round(net_profit_day, 2),
                    "เธญเธฑเธ•เธฃเธฒเนเธเน (%)": round(henday_pct, 1),
                    "FCR": round(fcr_ratio, 2),
                }
            )
            st.success("เธเธฑเธเธ—เธถเธเธเนเธญเธกเธนเธฅเน€เธฃเธตเธขเธเธฃเนเธญเธข!")
            st.rerun()

        st.markdown(
            "<div style='border-bottom: 2px dashed #475569; margin:25px 0;'></div>",
            unsafe_allow_html=True,
        )
        st.markdown("### ๐“ เธ•เธฒเธฃเธฒเธเธเธฃเธฐเธงเธฑเธ•เธดเธเธฒเธฃเนเธกเธขเนเธญเธเธซเธฅเธฑเธ")
        if not st.session_state.daily_logs:
            st.info("๐’ก เธขเธฑเธเนเธกเนเธกเธตเธเนเธญเธกเธนเธฅเธขเนเธญเธเธซเธฅเธฑเธ")
        else:
            st.dataframe(
                pd.DataFrame(st.session_state.daily_logs),
                use_container_width=True,
                hide_index=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------
    # TAB 3: PROCUREMENT & WORKER SHEET
    # ------------------------------------------
    with page_tabs[2]:
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown(
            "<h2>๐“ เนเธเธชเธฑเนเธเธเธฒเธเธเธชเธกเธญเธฒเธซเธฒเธฃเธชเธฑเธ•เธงเน (เธชเธณเธซเธฃเธฑเธเธขเธทเนเธเนเธซเนเธเธเธเธฒเธเธ•เธฑเธเธเธญเธ)</h2>",
            unsafe_allow_html=True,
        )
        total_tonnage = st.number_input(
            "๐“ฆ เนเธชเนเธเธณเธเธงเธเธเธดเนเธฅเธเธฃเธฑเธกเธญเธฒเธซเธฒเธฃเธฃเธงเธกเธ—เธตเนเธ•เนเธญเธเธเธฒเธฃเธเธฐเธเธชเธกเนเธเธฃเธญเธเธเธตเน (KG):",
            min_value=100,
            value=1000,
            step=100,
        )

        po_buffer = []
        total_po_cost = 0
        total_w = sum(st.session_state.current_weights.values())
        divisor = total_w if total_w > 0 else 1.0

        for ing_name, w_pct in st.session_state.current_weights.items():
            actual_pct = (w_pct / divisor) * 100.0
            if actual_pct > 0.01:
                if ing_name in st.session_state.db_ingredients:
                    weight_kg = (actual_pct / 100.0) * total_tonnage
                    cost_item = weight_kg * float(
                        st.session_state.db_ingredients[ing_name]["price"]
                    )
                    total_po_cost += cost_item

                    bags = int(weight_kg // 50)
                    rem_kg = weight_kg % 50

                    bag_txt = (
                        f"๐ข เธขเธ {bags} เธเธฃเธฐเธชเธญเธ + โ–๏ธ เธ•เธฑเธเน€เธจเธฉ {rem_kg:.1f} เธเธ."
                        if bags > 0
                        else f"โ–๏ธ เธ•เธฑเธเน€เธจเธฉเธชเธธเธ—เธเธด {rem_kg:.1f} เธเธดเนเธฅเธเธฃเธฑเธก"
                    )

                    po_buffer.append(
                        {
                            "เธฃเธฒเธขเธเธฒเธฃเธงเธฑเธ•เธ–เธธเธ”เธดเธ": ing_name,
                            "เธชเธฑเธ”เธชเนเธงเธเธเธชเธก (%)": round(actual_pct, 1),
                            "เธเนเธณเธซเธเธฑเธเธฃเธงเธกเธ—เธตเนเธ•เนเธญเธเนเธเน (KG)": round(weight_kg, 1),
                            "๐“ข เธงเธดเธเธตเธ•เธฑเธเธซเธเนเธฒเธเธฒเธ (เธเธฃเธฐเธชเธญเธเธฅเธฐ 50kg)": bag_txt,
                            "เธฃเธฒเธเธฒเธ—เธธเธ (เธเธฒเธ—)": round(cost_item, 0),
                        }
                    )

        if po_buffer:
            df_po = pd.DataFrame(po_buffer)
            st.dataframe(df_po, use_container_width=True, hide_index=True)

            st.markdown(
                f"<div style='background-color:#1e293b; padding:15px; border-radius:10px; border:2px dashed #10b981; font-size:24px; font-weight:bold; text-align:center; margin:15px 0;'>๐’ต เธเธเธเธฃเธฐเธกเธฒเธ“เธเนเธฒเธงเธฑเธ•เธ–เธธเธ”เธดเธเธฃเธงเธกเธฃเธญเธเธเธตเน: {total_po_cost:,.2f} เธเธฒเธ—</div>",
                unsafe_allow_html=True,
            )

            # --- เธเธตเน€เธเธญเธฃเน: เธเธธเนเธกเธ”เนเธงเธเธชเธณเธซเธฃเธฑเธเธเนเธญเธเธเธตเนเธเนเธญเธเธงเธฒเธกเธ เธฒเธฉเธฒเนเธ—เธขเธชเนเธเน€เธเนเธฒเธเธฅเธธเนเธก LINE ---
            line_text = f"๐“ *เนเธเธชเธฑเนเธเธเธชเธกเธญเธฒเธซเธฒเธฃเธชเธฑเธ•เธงเนเธฃเธงเธก: {total_tonnage:,} เธเธ.*\n"
            line_text += f"เธชเธนเธ•เธฃเธชเธณเธซเธฃเธฑเธ: {selected_b_name} ({selected_stage_label})\n"
            line_text += "--------------------------------------\n"
            for item in po_buffer:
                line_text += f"๐”น {item['เธฃเธฒเธขเธเธฒเธฃเธงเธฑเธ•เธ–เธธเธ”เธดเธ']}: {item['๐“ข เธงเธดเธเธตเธ•เธฑเธเธซเธเนเธฒเธเธฒเธ (เธเธฃเธฐเธชเธญเธเธฅเธฐ 50kg)']}\n"
            line_text += "--------------------------------------\n"
            line_text += f"๐’ฐ เธเธเธเธฃเธฐเธกเธฒเธ“เธฃเธงเธกเธฃเธญเธเธเธตเน: {total_po_cost:,.0f} เธเธฒเธ—"

            st.markdown("### ๐“ฑ เธเนเธญเธเธงเธฒเธกเธ”เนเธงเธเธชเธณเธซเธฃเธฑเธเธเนเธญเธเธเธตเนเธชเนเธ LINE (เธเธเธเธฒเธเน€เธเธดเธ”เธญเนเธฒเธเธเนเธฒเธข)")
            # [เนเธเนเนเธเนเธฅเนเธง] เธฅเธเธญเธฑเธเธเธฃเธฐ Escape Backslimport streamlit as st
