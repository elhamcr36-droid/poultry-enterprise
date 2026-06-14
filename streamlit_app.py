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

def get_log_value(log_data, key, default=None):
    if isinstance(log_data, dict):
        return log_data.get(key, default)
    return default

def sort_daily_logs_latest_first(logs):
    def sort_key(row):
        try:
            row_id = int(row.get("id") or 0)
        except Exception:
            row_id = 0
        return (
            str(row.get("date") or ""),
            str(row.get("created_at") or ""),
            row_id,
        )

    return sorted(logs or [], key=sort_key, reverse=True)

def render_big_menu(state_key, options, columns_per_row=3):
    if state_key not in st.session_state:
        st.session_state[state_key] = options[0]["id"]

    for row_start in range(0, len(options), columns_per_row):
        cols = st.columns(columns_per_row)
        for col, option in zip(cols, options[row_start:row_start + columns_per_row]):
            selected = st.session_state[state_key] == option["id"]
            with col:
                if st.button(
                    f"✅ {option['label']}" if selected else option["label"],
                    key=f"{state_key}_{option['id']}",
                    type="secondary",
                    use_container_width=True,
                ):
                    st.session_state[state_key] = option["id"]
                    st.rerun()

    return st.session_state[state_key]

def calculate_current_feed_cost():
    weights = st.session_state.get("current_weights", {})
    ingredients = st.session_state.get("db_ingredients", {})
    if not weights or not ingredients:
        return 0.0

    total_w = sum(float(value or 0.0) for value in weights.values())
    divisor = total_w if total_w > 0 else 1.0
    feed_cost = 0.0

    for name, weight_pct in weights.items():
        if name in ingredients:
            ratio = float(weight_pct or 0.0) / divisor
            feed_cost += ratio * float(ingredients[name].get("price", 0.0))

    return round(feed_cost, 2)

def build_daily_logs_display(logs):
    if not logs:
        return pd.DataFrame()

    df = pd.DataFrame(logs).copy()
    sort_cols = [col for col in ["date", "created_at", "id"] if col in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols, ascending=False, na_position="last")

    display_columns = {
        "date": "วันที่",
        "flock_age_weeks": "อายุฝูง (สัปดาห์)",
        "bird_count": "จำนวนไก่",
        "env_temp": "อุณหภูมิ (°C)",
        "actual_feed_given_kg": "อาหารที่ให้ (กก.)",
        "collected_eggs": "ไข่ที่เก็บได้",
        "egg_sale_price": "ราคาไข่/ฟอง",
        "dead_birds": "ไก่ตาย/คัดทิ้ง",
        "total_revenue": "รายได้",
        "total_feed_cost": "ต้นทุนอาหาร",
        "net_profit_day": "กำไรสุทธิ",
        "henday_pct": "อัตราไข่ (%)",
        "fcr_ratio": "FCR",
    }

    for source_col in display_columns:
        if source_col not in df.columns:
            df[source_col] = None

    df = df[list(display_columns.keys())].rename(columns=display_columns)

    numeric_cols = [
        "อาหารที่ให้ (กก.)",
        "ราคาไข่/ฟอง",
        "รายได้",
        "ต้นทุนอาหาร",
        "กำไรสุทธิ",
        "อัตราไข่ (%)",
        "FCR",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").round(2)

    for col in ["จำนวนไก่", "ไข่ที่เก็บได้", "ไก่ตาย/คัดทิ้ง"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    df["วันที่"] = pd.to_datetime(df["วันที่"], errors="coerce").dt.strftime("%Y-%m-%d")
    return df

def build_daily_logs_analysis(logs):
    df = pd.DataFrame(logs or [])
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df.get("date"), errors="coerce")
    numeric_cols = [
        "flock_age_weeks",
        "bird_count",
        "env_temp",
        "actual_feed_given_kg",
        "collected_eggs",
        "egg_sale_price",
        "dead_birds",
        "avg_egg_weight_g",
        "total_revenue",
        "total_feed_cost",
        "net_profit_day",
        "henday_pct",
        "fcr_ratio",
    ]
    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["cost_per_egg"] = df.apply(
        lambda row: (row["total_feed_cost"] / row["collected_eggs"]) if row["collected_eggs"] > 0 else 0,
        axis=1,
    )
    sort_cols = [col for col in ["date", "created_at", "id"] if col in df.columns]
    return df.sort_values(sort_cols, ascending=True, na_position="last") if sort_cols else df

def render_comparison_metric(label, left_value, right_value, suffix="", decimals=2, lower_is_better=False):
    diff = right_value - left_value
    good = diff <= 0 if lower_is_better else diff >= 0
    color = "#22c55e" if good else "#f87171"
    sign = "+" if diff > 0 else ""
    st.markdown(
        f"""
        <div class="status-panel">
            <b>{label}</b><br>
            <span style="color:#cbd5e1;">วันแรก: {left_value:,.{decimals}f}{suffix}</span><br>
            <span style="color:#cbd5e1;">วันเทียบ: {right_value:,.{decimals}f}{suffix}</span><br>
            <span style="color:{color}; font-weight:800;">ผลต่าง: {sign}{diff:,.{decimals}f}{suffix}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_readable_table(data, *, column_order=None, column_labels=None, column_config=None, height=None):
    """Show tables with farmer-friendly Thai column names instead of database field names."""
    if isinstance(data, pd.DataFrame):
        df = data.copy()
    else:
        df = pd.DataFrame(data)

    if df.empty:
        st.info("ยังไม่มีข้อมูลในตารางนี้")
        return df

    column_labels = column_labels or {}
    if column_order:
        visible_cols = [col for col in column_order if col in df.columns]
        df = df[visible_cols]

    df = df.rename(columns=column_labels)
    dataframe_options = {
        "use_container_width": True,
        "hide_index": True,
        "column_config": column_config,
    }
    if height is not None:
        dataframe_options["height"] = height

    st.dataframe(df, **dataframe_options)
    return df

def build_ingredients_display():
    rows = []
    for name, data in st.session_state.get("db_ingredients", {}).items():
        rows.append({
            "วัตถุดิบ": name,
            "ราคา/กก.": float(data.get("price", 0) or 0),
            "โปรตีน (%)": float(data.get("protein", 0) or 0),
            "พลังงาน ME": float(data.get("me", 0) or 0),
            "แคลเซียม (%)": float(data.get("calcium", 0) or 0),
            "ฟอสฟอรัส (%)": float(data.get("phos", 0) or 0),
            "ใช้ขั้นต่ำ (%)": float(data.get("min_limit", 0) or 0),
            "ใช้สูงสุด (%)": float(data.get("max_limit", 100) or 100),
        })
    return pd.DataFrame(rows).sort_values("วัตถุดิบ") if rows else pd.DataFrame()

def build_targets_display():
    rows = []
    for stage_key, data in st.session_state.get("db_targets", {}).items():
        rows.append({
            "ช่วงอายุ/ระยะผลิต": data.get("stage_name", stage_key),
            "โปรตีนขั้นต่ำ (%)": data.get("protein", 0),
            "พลังงานขั้นต่ำ ME": data.get("me", 0),
            "แคลเซียมขั้นต่ำ (%)": data.get("calcium", 0),
            "ฟอสฟอรัสขั้นต่ำ (%)": data.get("phos", 0),
        })
    return pd.DataFrame(rows)

def build_breeds_display():
    df = pd.DataFrame(st.session_state.get("db_breeds", []))
    if df.empty:
        return df
    return df.rename(columns={
        "group_name": "กลุ่มสายพันธุ์",
        "breed_name": "ชื่อสายพันธุ์",
        "egg_color": "ลักษณะไข่",
        "default_feed": "อาหารแนะนำ (กรัม/ตัว/วัน)",
    })

def update_daily_log_in_supabase(log_id, log_data):
    try:
        if not log_id:
            st.error("ไม่พบรหัสรายการที่จะบันทึก")
            return False
        log_data[DAILY_LOG_USER_COLUMN] = st.session_state.current_user_key
        supabase.table(DAILY_LOGS_TABLE).update(log_data).eq("id", log_id).eq(DAILY_LOG_USER_COLUMN, st.session_state.current_user_key).execute()
        st.success("บันทึกการแก้ไขประวัติฟาร์มเรียบร้อยแล้ว")
        fetch_daily_logs_from_supabase()
        return True
    except Exception as e:
        st.error(f"แก้ไขประวัติฟาร์มไม่สำเร็จ: {e}")
        return False

def delete_daily_log_from_supabase(log_id):
    try:
        if not log_id:
            st.error("ไม่พบรหัสรายการที่จะลบ")
            return False
        supabase.table(DAILY_LOGS_TABLE).delete().eq("id", log_id).eq(DAILY_LOG_USER_COLUMN, st.session_state.current_user_key).execute()
        st.success("ลบประวัติฟาร์มรายการนี้แล้ว")
        fetch_daily_logs_from_supabase()
        return True
    except Exception as e:
        st.error(f"ลบประวัติฟาร์มไม่สำเร็จ: {e}")
        return False

# ==========================================
# 🔌 SUPABASE CONNECTION INITIALIZATION
# ==========================================
# ล้างช่องว่างซ้าย-ขวาออกด้วย .strip() ป้องกันข้อผิดพลาดเน็ตเวิร์กหาเส้นทางไม่เจอ (Name or service not known)
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
        raise ValueError("❌ ตรวจพบข้อผิดพลาด: กรุณากรอก SUPABASE_URL และ SUPABASE_KEY ให้ถูกต้องสมบูรณ์")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = init_supabase()
except Exception as e:
    error_msg = str(e).lower()
    if "name or service not known" in error_msg or "temporary failure in name resolution" in error_msg:
        st.error("🌐 [ข้อผิดพลาดระบบเครือข่าย]: ไม่สามารถค้นหาที่อยู่ของเซิร์ฟเวอร์ฐานข้อมูลได้ (Name or service not known) กรุณาตรวจสอบอินเทอร์เน็ตของเครื่อง หรือ Reboot App บนระบบคลาวด์")
    else:
        st.error(f"❌ ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ Supabase ได้ตั้งแต่เริ่มต้น: {e}")

# ==========================================
# 🔱 1. INITIAL APP CONFIGURATION & THEME
# ==========================================
st.set_page_config(
    page_title="ระบบจัดการโภชนาการและฟาร์มไก่ไข่", 
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
    [data-testid="stDataFrame"] {
        background-color: rgba(15, 23, 42, 0.94) !important;
        border: 1px solid rgba(255, 255, 255, 0.16);
        border-radius: 10px;
        padding: 8px;
        overflow: hidden;
    }
    [data-testid="stDataFrame"] * {
        font-size: 1rem !important;
    }
    .block-container {
        max-width: 1220px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }
    div[data-testid="stButton"] > button {
        min-height: 58px;
        border-radius: 10px !important;
        border: 1px solid rgba(255, 255, 255, 0.20) !important;
        background: rgba(15, 23, 42, 0.92) !important;
        color: #ffffff !important;
        font-size: 1.05rem !important;
        font-weight: 800 !important;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.24);
    }
    div[data-testid="stButton"] > button:hover {
        border-color: #fbbf24 !important;
        background: rgba(30, 41, 59, 0.98) !important;
        transform: translateY(-1px);
    }
    div[data-testid="stHorizontalBlock"]:has(div[data-testid="stButton"]) {
        justify-content: center;
    }
    .app-main-title {
        text-align: center;
        margin: 4px 0 10px 0;
        padding: 18px 20px;
        border-radius: 10px;
        background: rgba(2, 6, 23, 0.72);
        border: 1px solid rgba(148, 163, 184, 0.26);
    }
    .app-main-title h1 {
        margin: 0 !important;
        font-size: 2rem !important;
    }
    .app-main-title p {
        margin: 8px 0 0 0 !important;
        color: #cbd5e1 !important;
    }
    .center-menu-wrap {
        max-width: 860px;
        margin: 0 auto;
    }
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stDateInput"] input {
        min-height: 50px !important;
        font-size: 1.05rem !important;
        border-radius: 8px !important;
    }
    .farm-page-card {
        background: rgba(2, 6, 23, 0.76);
        border: 1px solid rgba(255, 255, 255, 0.16);
        border-left: 5px solid #fbbf24;
        border-radius: 10px;
        padding: 18px 20px;
        margin: 16px 0 20px 0;
    }
    .farm-page-card h2 {
        margin: 0 0 6px 0 !important;
        font-size: 1.55rem !important;
    }
    .farm-page-card p {
        margin: 0 !important;
        color: #cbd5e1 !important;
        font-size: 1.02rem;
    }
    .farmer-card {
        background-color: rgba(2, 6, 23, 0.82) !important;
        padding: 22px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.15);
        margin-bottom: 18px;
    }
    @media (max-width: 760px) {
        .block-container { padding-left: 0.8rem; padding-right: 0.8rem; }
        div[data-testid="stButton"] > button {
            min-height: 64px;
            font-size: 1rem !important;
        }
        h1 { font-size: 2rem !important; }
        .farm-page-card { padding: 14px 16px; }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================================
# 🔐 2. SECURITY & STATE INITIALIZATION
# ==========================================
states = {
    "is_authenticated": False,
    "auth_page_mode": "login",
    "user_role": "user",
    "user_email": "",
    "current_user_key": "",  # เก็บบัญชีอีเมลเพื่อใช้แบ่งแยกตัวใครตัวมันบนคลาวด์
    "saved_formulas": [],
    "daily_logs": [],
    "current_weights": {},
    "db_ingredients": {}  
}

for key, value in states.items():
    if key not in st.session_state:
        st.session_state[key] = value

def check_password_strength(password):
    if len(password) < 8: return False, "❌ รหัสผ่านต้องมีความยาวอย่างน้อย 8 ตัวอักษร"
    if not re.search("[a-z]", password): return False, "❌ รหัสผ่านต้องมีอักษรพิมพ์เล็ก (a-z) อย่างน้อย 1 ตัว"
    if not re.search("[A-Z]", password): return False, "❌ รหัสผ่านต้องมีอักษรพิมพ์ใหญ่ (A-Z) อย่างน้อย 1 ตัว"
    if not re.search("[0-9]", password): return False, "❌ รหัสผ่านต้องมีตัวเลข (0-9) อย่างน้อย 1 ตัว"
    if not re.search("[_@$!%*#?&.]", password): return False, "❌ รหัสผ่านต้องมีอักขระพิเศษอย่างน้อย 1 ตัว"
    return True, "🟢 รหัสผ่านมีความปลอดภัยสูงตามมาตรฐาน"

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
        raise Exception(result.get("error", "ไม่สามารถรีเซ็ตรหัสผ่านได้"))
    except Exception as error:
        raise Exception(f"เชื่อมต่อระบบรีเซ็ตรหัสผ่านไม่ได้: {error}")

    if not result.get("ok"):
        raise Exception(result.get("error", "ไม่สามารถรีเซ็ตรหัสผ่านได้"))
    return result

# --- กำหนดค่าเริ่มต้นเป็น List/Dict ว่าง เพื่อรอการโหลดจาก Database 100% ---
if "db_groups" not in st.session_state:
    st.session_state.db_groups = []

if "db_breeds" not in st.session_state:
    st.session_state.db_breeds = []

if "db_targets" not in st.session_state:
    st.session_state.db_targets = {}

if "db_nutrient_keys" not in st.session_state:
    st.session_state.db_nutrient_keys = {
        "price": {"label": "ราคากลาง (บาท/กก.)", "step": 0.1, "default": 0.0},
        "protein": {"label": "โปรตีนดิบ (% CP)", "step": 0.1, "default": 0.0},
        "me": {"label": "พลังงานใช้ประโยชน์ได้ (ME kcal/kg)", "step": 10.0, "default": 0.0},
        "calcium": {"label": "แคลเซียม (% Ca)", "step": 0.01, "default": 0.0},
        "phos": {"label": "ฟอสฟอรัสเป็นประโยชน์ (% Avail. P)", "step": 0.01, "default": 0.0},
        "lysine": {"label": "อะมิโน ไลซีน (% Lys)", "step": 0.01, "default": 0.0},
        "methionine": {"label": "อะมิโน เมทไธโอนีน (% Met)", "step": 0.01, "default": 0.0},
        "fiber": {"label": "เยื่อใย (% Fiber)", "step": 0.1, "default": 0.0},
    }

FALLBACK_INGREDIENTS = [
    {"id": 5, "name": "ข้าวโพดบด (Yellow Corn)", "price": 12.50, "protein": 8.00, "me": 3370.0, "calcium": 0.02, "phos": 0.08, "owner_email": "system_default", "lysine": 0.24, "methionine": 0.18, "fiber": 2.00, "min_limit": 30.0, "max_limit": 70.0},
    {"id": 6, "name": "กากถั่วเหลือง (Soybean Meal 44%)", "price": 22.00, "protein": 44.00, "me": 2230.0, "calcium": 0.29, "phos": 0.20, "owner_email": "system_default", "lysine": 2.69, "methionine": 0.62, "fiber": 6.00, "min_limit": 10.0, "max_limit": 35.0},
    {"id": 7, "name": "รำละเอียด (Rice Bran)", "price": 10.50, "protein": 12.00, "me": 2860.0, "calcium": 0.05, "phos": 0.15, "owner_email": "system_default", "lysine": 0.54, "methionine": 0.24, "fiber": 6.50, "min_limit": 0.0, "max_limit": 20.0},
    {"id": 8, "name": "ปลายข้าว (Broken Rice)", "price": 14.00, "protein": 7.50, "me": 3400.0, "calcium": 0.03, "phos": 0.04, "owner_email": "system_default", "lysine": 0.20, "methionine": 0.15, "fiber": 1.00, "min_limit": 0.0, "max_limit": 30.0},
    {"id": 9, "name": "ปลาป่น (Fish Meal 60%)", "price": 35.00, "protein": 60.00, "me": 2900.0, "calcium": 5.00, "phos": 2.80, "owner_email": "system_default", "lysine": 4.50, "methionine": 1.60, "fiber": 1.00, "min_limit": 2.0, "max_limit": 8.0}
]

DEFAULT_INGREDIENT_OWNER = "system_default"
SAVED_FORMULAS_TABLE = "saved_formulas"
DAILY_LOGS_TABLE = "daily_logs"
DAILY_LOG_USER_COLUMN = "user_id"
USER_PROFILES_TABLE = "user_profiles"
NUTRIENT_DEFINITIONS_TABLE = "nutrient_definitions"
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

def require_supabase_rows(response, action_label):
    rows = getattr(response, "data", None)
    return rows or []

def table_mutation(table_name, action, payload=None, filters=None):
    query = supabase.table(table_name)
    if action == "insert":
        query = query.insert(payload)
    elif action == "update":
        query = query.update(payload)
    elif action == "delete":
        query = query.delete()
    else:
        raise ValueError(f"Unsupported table action: {action}")

    for column, value in (filters or {}).items():
        if value is not None and value != "":
            query = query.eq(column, value)
    return query.execute()

def fetch_nutrient_definitions_from_supabase():
    try:
        response = supabase.table(NUTRIENT_DEFINITIONS_TABLE).select("*").eq("is_active", True).order("display_order").execute()
        rows = response.data or []
        st.session_state.nutrient_definitions_loaded_from_db = True
        st.session_state.nutrient_definitions_error = ""
        if rows:
            st.session_state.db_nutrient_keys = {
                row["nutrient_key"]: {
                    "label": row.get("label", row["nutrient_key"]),
                    "step": float(row.get("step", 0.1) or 0.1),
                    "default": float(row.get("default_value", 0.0) or 0.0),
                    "id": row.get("id"),
                    "is_core": bool(row.get("is_core", False)),
                }
                for row in rows
                if row.get("nutrient_key")
            }
        return rows
    except Exception as e:
        st.session_state.nutrient_definitions_loaded_from_db = False
        st.session_state.nutrient_definitions_error = str(e)
        return []

def add_nutrient_definition_to_supabase(nutrient_key, label, step, default_value=0.0):
    payload = {
        "nutrient_key": nutrient_key.strip().lower(),
        "label": label.strip(),
        "step": float(step),
        "default_value": float(default_value),
        "is_active": True,
        "is_core": False,
        "display_order": len(st.session_state.get("db_nutrient_keys", {})) + 1,
    }
    table_mutation(NUTRIENT_DEFINITIONS_TABLE, "insert", payload)
    fetch_nutrient_definitions_from_supabase()
    return True

def delete_nutrient_definition_from_supabase(nutrient_key):
    data = st.session_state.db_nutrient_keys.get(nutrient_key, {})
    filters = {"id": data.get("id")} if data.get("id") else {"nutrient_key": nutrient_key}
    table_mutation(NUTRIENT_DEFINITIONS_TABLE, "delete", filters=filters)
    fetch_nutrient_definitions_from_supabase()
    return True

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
    """ ดึงข้อมูลจาก Database 100% สอดคล้องตามชื่อคอลัมน์จริงใน Supabase """
    try:
        st.session_state.master_load_debug = []
        
        # 1. ดึงข้อมูลกลุ่มสายพันธุ์ (db_groups)
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

        # 2. ดึงข้อมูลสายพันธุ์ (db_breeds)
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

        # 3. ดึงข้อมูลช่วงอายุ/ระยะการเจริญเติบโต (db_targets)
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
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลจาก Database: {e}")

NUTRITION_STANDARD_COLUMNS = {
    "min_protein": ["min_protein", "โปรตีนต่ำสุด_min_protein"],
    "min_me": ["min_me", "พลังงานต่ำสุด_min_me"],
    "min_calcium": ["min_calcium", "แคลเซียมต่ำสุด_min_calcium"],
    "max_calcium": ["max_calcium", "แคลเซียมสูงสุด_max_calcium"],
    "min_phosphorus": ["min_phosphorus", "ฟอสฟอรัสต่ำสุด_min_phosphorus"],
    "min_lysine": ["min_lysine", "ไลซีนต่ำสุด_min_lysine"],
    "min_methionine": ["min_methionine", "เมทิโอนีนต่ำสุด_min_methionine"],
    "max_fiber": ["max_fiber"],
}

PHASE_NAME_ALIASES = {
    "chick": ["Chick", "Starter", "Chick Starter", "ระยะลูกไก่"],
    "starter": ["Starter", "Chick", "Chick Starter", "ระยะลูกไก่"],
    "grower": ["Grower", "Pullet Grower", "ระยะรุ่น"],
    "developer": ["Developer", "Pullet Developer", "ระยะไก่รุ่น"],
    "pullet": ["Pullet", "Developer", "Grower", "ระยะไก่สาว"],
    "prelay": ["Pre-Lay", "Pre Lay", "Prelay", "ระยะก่อนให้ไข่"],
    "pre_lay": ["Pre-Lay", "Pre Lay", "Prelay", "ระยะก่อนให้ไข่"],
    "layer": ["Layer", "Laying", "Production", "ระยะให้ไข่"],
    "peak": ["Peak", "Peak Production", "ระยะพีค"],
    "post_peak": ["Post Peak", "Post-Peak", "Late Layer", "ระยะหลังพีค"],
}

def unique_values(values):
    seen = set()
    result = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text.lower() not in seen:
            result.append(text)
            seen.add(text.lower())
    return result

def build_phase_candidates(phase_name, phase_key=None):
    raw_values = [phase_name, phase_key]
    for value in [phase_name, phase_key]:
        if not value:
            continue
        normalized = str(value).strip().lower().replace(" ", "_").replace("-", "_")
        raw_values.append(normalized)
        raw_values.append(normalized.replace("_", " ").title())
        raw_values.extend(PHASE_NAME_ALIASES.get(normalized, []))
    return unique_values(raw_values)

def read_first_available_float(data, column_names, default=0.0):
    for column_name in column_names:
        value = data.get(column_name)
        if value is not None:
            return float(value)
    return float(default)

def format_nutrition_standard_row(data):
    return {
        "phase_key": data.get("phase_key") or data.get("stage_key") or "",
        "phase_name": data.get("phase_name") or data.get("stage_name") or data.get("ช่วงอายุการเลี้ยง_phase_name") or "",
        "min_protein": read_first_available_float(data, NUTRITION_STANDARD_COLUMNS["min_protein"]),
        "min_me": read_first_available_float(data, NUTRITION_STANDARD_COLUMNS["min_me"]),
        "min_calcium": read_first_available_float(data, NUTRITION_STANDARD_COLUMNS["min_calcium"]),
        "max_calcium": read_first_available_float(data, NUTRITION_STANDARD_COLUMNS["max_calcium"], 5.5),
        "min_phosphorus": read_first_available_float(data, NUTRITION_STANDARD_COLUMNS["min_phosphorus"]),
        "min_lysine": read_first_available_float(data, NUTRITION_STANDARD_COLUMNS["min_lysine"]),
        "min_methionine": read_first_available_float(data, NUTRITION_STANDARD_COLUMNS["min_methionine"]),
        "max_fiber": read_first_available_float(data, NUTRITION_STANDARD_COLUMNS["max_fiber"], 5.0),
    }

def query_nutrition_standard(table_name, breed_id, phase_column, phase_value):
    query = supabase.table(table_name).select("*").eq(phase_column, phase_value)
    if breed_id is not None:
        query = query.eq("breed_id", int(breed_id))
    return query.execute()

def fetch_nutrition_standards(breed_id, phase_name, phase_key=None):
    """ 
    Load breed nutrition standards from the English Supabase view first.
    Falls back to the old Thai table/columns while the database migration is being applied.
    """
    phase_candidates = build_phase_candidates(phase_name, phase_key)
    table_candidates = [
        {
            "table": "nutrition_standards",
            "phase_columns": ["phase_key", "phase_name"],
        },
        {
            "table": "มาตรฐานโภชนาการไก่ไข่",
            "phase_columns": ["ช่วงอายุการเลี้ยง_phase_name"],
        },
    ]

    try:
        for table_info in table_candidates:
            for phase_column in table_info["phase_columns"]:
                for phase_candidate in phase_candidates:
                    try:
                        res = query_nutrition_standard(table_info["table"], breed_id, phase_column, phase_candidate)
                    except Exception:
                        continue

                    if res.data:
                        return format_nutrition_standard_row(res.data[0])

        for table_info in table_candidates:
            for phase_column in table_info["phase_columns"]:
                for phase_candidate in phase_candidates:
                    try:
                        res = query_nutrition_standard(table_info["table"], None, phase_column, phase_candidate)
                    except Exception:
                        continue

                    if res.data:
                        st.warning("ใช้เกณฑ์โภชนาการกลางของระยะนี้ชั่วคราว เพราะสายพันธุ์ที่เลือกยังไม่มีเกณฑ์เฉพาะในฐานข้อมูล")
                        return format_nutrition_standard_row(res.data[0])
    except Exception as e:
        st.error(f"⚠️ เกิดข้อผิดพลาดในการดึงมาตรฐานโภชนาการจาก Supabase: {e}")
    return None

def fetch_nutrition_standard_phase_options(breed_id=None):
    """
    Use the phase labels from nutrition_standards so the displayed language
    always matches the database rows used for breed-specific nutrient standards.
    """
    fallback_options = [
        {
            "phase_key": str(target.get("stage_key") or key),
            "phase_name": str(target.get("stage_name") or target.get("stage_key") or key),
        }
        for key, target in st.session_state.db_targets.items()
        if target.get("stage_key") or target.get("stage_name")
    ]

    try:
        query = supabase.table("nutrition_standards").select("phase_key, phase_name, id")
        if breed_id is not None:
            query = query.eq("breed_id", int(breed_id))
        response = query.order("id").execute()
        rows = response.data or []

        phase_options = []
        seen = set()
        for row in rows:
            phase_key = str(row.get("phase_key") or "").strip()
            phase_name = str(row.get("phase_name") or phase_key).strip()
            if not phase_key or phase_key in seen:
                continue
            phase_options.append({"phase_key": phase_key, "phase_name": phase_name})
            seen.add(phase_key)

        return phase_options or fallback_options
    except Exception as phase_err:
        st.warning(f"ยังดึงรายชื่อช่วงโภชนาการจาก nutrition_standards ไม่สำเร็จ จึงใช้รายการช่วงสำรอง: {phase_err}")
        return fallback_options

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
# 🔄 FUNCTIONS: จัดการข้อมูลสูตรอาหาร และบันทึกฟาร์มรายวันตัวใครตัวมัน
# =========================================================================

def fetch_saved_formulas_from_supabase():
    """ดึงสูตรอาหารเฉพาะของผู้ใช้งานที่ล็อกอินอยู่ปัจจุบัน"""
    try:
        if st.session_state.is_authenticated and st.session_state.current_user_key:
            user_email = st.session_state.current_user_key
            response = supabase.table(SAVED_FORMULAS_TABLE).select("*").eq("owner_email", user_email).execute()
            if response.data:
                st.session_state.saved_formulas = response.data
                return response.data
        st.session_state.saved_formulas = []
        return []
    except Exception as e:
        st.warning(f"⚠️ ไม่สามารถดึงสูตรอาหารส่วนตัวจากคลาวด์ได้: {e}")
        return []

def normalize_formula_weights(weights):
    if isinstance(weights, dict):
        return weights.copy()
    if isinstance(weights, str):
        try:
            parsed_weights = json.loads(weights)
            if isinstance(parsed_weights, dict):
                return parsed_weights
        except Exception:
            pass
    return {}

def save_formula_to_supabase(formula_data):
    """บันทึกสูตรอาหารใหม่ ผูกเจ้าของด้วย owner_email ทุกครั้ง"""
    try:
        if st.session_state.is_authenticated and st.session_state.current_user_key:
            formula_data["owner_email"] = st.session_state.current_user_key
            supabase.table(SAVED_FORMULAS_TABLE).insert(formula_data).execute()
            st.success("🎉 บันทึกสูตรอาหารลงพื้นที่ส่วนตัวของคุณเรียบร้อยแล้ว!")
            fetch_saved_formulas_from_supabase()
            return True
        else:
            st.error("❌ กรุณาเข้าสู่ระบบก่อนทำการบันทึกข้อมูล")
            return False
    except Exception as e:
        st.error(f"❌ ไม่สามารถบันทึกสูตรลงคลาวด์ได้: {e}")
        return False

def delete_formula_from_supabase(formula_id):
    try:
        if not formula_id:
            st.error("❌ ไม่พบรหัสสูตรอาหารที่ต้องการลบ")
            return False
        supabase.table(SAVED_FORMULAS_TABLE).delete().eq("id", formula_id).eq("owner_email", st.session_state.current_user_key).execute()
        st.success("🗑️ ลบสูตรอาหารที่บันทึกไว้เรียบร้อยแล้ว")
        fetch_saved_formulas_from_supabase()
        return True
    except Exception as e:
        st.error(f"❌ ไม่สามารถลบสูตรอาหารได้: {e}")
        return False

def fetch_daily_logs_from_supabase():
    """ดึงสมุดบันทึกกิจกรรมฟาร์มรายวันเฉพาะของตนเอง"""
    try:
        if st.session_state.is_authenticated and st.session_state.current_user_key:
            user_email = st.session_state.current_user_key
            response = supabase.table(DAILY_LOGS_TABLE).select("*").eq(DAILY_LOG_USER_COLUMN, user_email).order("date", desc=True).order("created_at", desc=True).order("id", desc=True).execute()
            if response.data:
                st.session_state.daily_logs = response.data
                return response.data
        st.session_state.daily_logs = []
        return []
    except Exception as e:
        st.warning(f"⚠️ ไม่สามารถดึงบันทึกกิจกรรมฟาร์มจากคลาวด์ได้: {e}")
        return []

def save_daily_log_to_supabase(log_data):
    """บันทึกข้อมูลกิจกรรมฟาร์มประจำวัน ผูกเข้ากับระบบบัญชีผู้ใช้จริง"""
    try:
        if st.session_state.is_authenticated and st.session_state.current_user_key:
            log_data[DAILY_LOG_USER_COLUMN] = st.session_state.current_user_key
            supabase.table(DAILY_LOGS_TABLE).insert(log_data).execute()
            st.success("🎉 บันทึกประวัติกิจกรรมฟาร์มประจำวันสำเร็จ!")
            fetch_daily_logs_from_supabase()
            return True
        else:
            st.error("❌ กรุณาเข้าสู่ระบบก่อนทำการบันทึกข้อมูล")
            return False
    except Exception as e:
        st.error(f"❌ ไม่สามารถบันทึกข้อมูลฟาร์มรายวันได้: {e}")
        return False

def fetch_user_profiles_from_supabase():
    try:
        response = supabase.table(USER_PROFILES_TABLE).select("*").order("created_at", desc=True).execute()
        profiles = response.data or []
        st.session_state.user_database = {
            item.get("email"): {
                "name": item.get("first_name", "") or "",
                "surname": item.get("last_name", "") or "",
                "tel": item.get("phone", "") or "",
                "role": item.get("role", "user") or "user",
                "reg_date": str(item.get("created_at", ""))[:10] or "-",
                "status": item.get("status", "active") or "active",
            }
            for item in profiles
            if item.get("email")
        }
        return profiles
    except Exception as e:
        st.warning(f"⚠️ ไม่สามารถดึงรายชื่อผู้ใช้งานจาก Supabase ได้: {e}")
        return []

def upsert_user_profile(email, first_name="", last_name="", phone="", role="user"):
    if not email:
        return False
    payload = {
        "email": email.strip().lower(),
        "role": role,
        "status": "active",
        "updated_at": datetime.datetime.utcnow().isoformat(),
    }
    if first_name:
        payload["first_name"] = first_name
    if last_name:
        payload["last_name"] = last_name
    if phone:
        payload["phone"] = phone
    try:
        supabase.table(USER_PROFILES_TABLE).upsert(payload, on_conflict="email").execute()
        fetch_user_profiles_from_supabase()
        return True
    except Exception as e:
        st.warning(f"⚠️ บันทึกข้อมูลโปรไฟล์ผู้ใช้ไม่สำเร็จ: {e}")
        return False

def get_user_role_from_supabase(email):
    if not email:
        return "user"
    if email.strip().lower() == "222@gmail.com":
        return "admin"
    try:
        response = supabase.table(USER_PROFILES_TABLE).select("role,status").eq("email", email.strip().lower()).limit(1).execute()
        if response.data:
            profile = response.data[0]
            if profile.get("status") == "disabled":
                return "disabled"
            return profile.get("role", "user") or "user"
    except Exception:
        pass
    return "user"

def update_user_profile_role(email, role):
    try:
        supabase.table(USER_PROFILES_TABLE).update({
            "role": role,
            "updated_at": datetime.datetime.utcnow().isoformat(),
        }).eq("email", email.strip().lower()).execute()
        fetch_user_profiles_from_supabase()
        return True
    except Exception as e:
        st.error(f"❌ อัปเดตสิทธิ์ผู้ใช้ไม่สำเร็จ: {e}")
        return False

def disable_user_profile(email):
    try:
        supabase.table(USER_PROFILES_TABLE).update({
            "status": "disabled",
            "updated_at": datetime.datetime.utcnow().isoformat(),
        }).eq("email", email.strip().lower()).execute()
        fetch_user_profiles_from_supabase()
        return True
    except Exception as e:
        st.error(f"❌ ระงับบัญชีไม่สำเร็จ: {e}")
        return False


# ==========================================
# 🧮 3. CORE AI SOLVER ENGINE
# ==========================================
def run_ai_solver(nutrient_targets):
    """
    สมองกลคำนวณสูตรอาหารต้นทุนต่ำสุด (Linear Programming)
    โดยดึงข้อจำกัด (Constraints) มาจากตารางมาตรฐานโภชนาการบน Supabase 100%
    """
    if not nutrient_targets:
        st.error("❌ ไม่สามารถคำนวณได้เนื่องจากไม่มีข้อมูลเกณฑ์เป้าหมายโภชนาการ")
        return {}

    prob = pulp.LpProblem("AI_Layer_Nutrition_Solver", pulp.LpMinimize)
    
    # ดึงวัตถุดิบปัจจุบันจากคลังใน Supabase
    current_ingredients = fetch_ingredients_from_supabase()
    if not current_ingredients:
        st.error("❌ ไม่พบข้อมูลวัตถุดิบในระบบ Supabase ไม่สามารถคำนวณได้")
        return {}

    def make_lp_var_name(name):
        safe_name = re.sub(r"[^0-9A-Za-z_]+", "_", str(name)).strip("_")
        return safe_name or "ingredient"

    # กำหนดตัวแปรสำหรับสัดส่วนผสมวัตถุดิบแต่ละชนิด (LowBound - UpBound อิงตามที่ตั้งไว้ในฐานข้อมูล)
    ing_vars = {
        name: pulp.LpVariable(
            f"ing_{idx}_{make_lp_var_name(name)}",
            lowBound=float(d.get("min_limit", 0)) / 100.0, 
            upBound=float(d.get("max_limit", 100)) / 100.0
        ) 
        for idx, (name, d) in enumerate(current_ingredients.items())
    }
    
    # ตัวแปรเสริมชดเชยเพื่อป้องกันสมองกลหาทางออกไม่ได้ (Slack Variables)
    s_p = pulp.LpVariable("slack_protein", lowBound=0)
    s_m = pulp.LpVariable("slack_me", lowBound=0)
    s_c = pulp.LpVariable("slack_calcium", lowBound=0)
    
    # Objective Function: คำนวณราคาวัตถุดิบให้มีต้นทุนรวมต่ำที่สุดสุทธิ
    prob += pulp.lpSum([ing_vars[name] * float(d["price"]) for name, d in current_ingredients.items()]) + (10000.0 * s_p) + (10.0 * s_m) + (10000.0 * s_c), "Total_Cost"
    
    # Constraint 1: สัดส่วนผสมของวัตถุดิบทุกชนิดรวมกันต้องได้ 100% พอดี
    prob += pulp.lpSum([ing_vars[name] for name in current_ingredients.keys()]) == 1.0, "Total_Weight_100_Percent"
    
    # Constraints 2-8: ผูกข้อจำกัดสารอาหารตามค่าที่ดึงมาจาก Supabase จริง
    prob += pulp.lpSum([ing_vars[name] * float(d["protein"]) for name, d in current_ingredients.items()]) + s_p >= nutrient_targets["min_protein"]
    prob += pulp.lpSum([ing_vars[name] * float(d["me"]) for name, d in current_ingredients.items()]) + s_m >= nutrient_targets["min_me"]
    
    # แคลเซียม (ตรวจเกณฑ์ขั้นต่ำ และขั้นสูงสุดตามสายพันธุ์)
    prob += pulp.lpSum([ing_vars[name] * float(d["calcium"]) for name, d in current_ingredients.items()]) + s_c >= nutrient_targets["min_calcium"]
    prob += pulp.lpSum([ing_vars[name] * float(d["calcium"]) for name, d in current_ingredients.items()]) <= nutrient_targets["max_calcium"]
    
    # ฟอสฟอรัส, ไลซีน, เมทิโอนีน และเยื่อใยสูงสุด
    prob += pulp.lpSum([ing_vars[name] * float(d["phos"]) for name, d in current_ingredients.items()]) >= nutrient_targets["min_phosphorus"]
    prob += pulp.lpSum([ing_vars[name] * float(d["lysine"]) for name, d in current_ingredients.items()]) >= nutrient_targets["min_lysine"]
    prob += pulp.lpSum([ing_vars[name] * float(d["methionine"]) for name, d in current_ingredients.items()]) >= nutrient_targets["min_methionine"]
    prob += pulp.lpSum([ing_vars[name] * float(d.get("fiber", 0.0)) for name, d in current_ingredients.items()]) <= nutrient_targets["max_fiber"]
    
    # เริ่มสั่งเปิดระบบ Solver คำนวณหาทางออกที่ดีที่สุด
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    
    res = {}
    for name in current_ingredients.keys():
        res[name] = round((ing_vars[name].varValue if ing_vars[name].varValue is not None else 0.0) * 100.0, 1)
    return res

# ==========================================
# 🔒 4. SECURITY GATEWAY (SUPABASE AUTH INTEGRATION)
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
        if (hash && (hash.includes('access_token') || hash.includes('error')) && !search.includes('access_token') && !search.includes('error')) {
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
    recovery_error = get_query_param("error")
    recovery_error_code = get_query_param("error_code")
    recovery_error_description = get_query_param("error_description")

    if auth_action == "forgot_password":
        st.session_state.auth_page_mode = "forgot"
    elif auth_action == "reset_password":
        st.session_state.auth_page_mode = "reset_password"

    if recovery_error or recovery_error_code:
        st.session_state.auth_page_mode = "reset_password"
        st.session_state.password_recovery_ready = False
        st.session_state.password_recovery_error = {
            "error": recovery_error or "",
            "code": recovery_error_code or "",
            "description": recovery_error_description or "",
        }
    elif access_token and refresh_token and recovery_type == "recovery":
        try:
            supabase.auth.set_session(access_token, refresh_token)
            st.session_state.auth_page_mode = "reset_password"
            st.session_state.password_recovery_ready = True
            st.session_state.password_recovery_error = None
        except Exception as error:
            st.error(f"ไม่สามารถเปิดหน้าตั้งรหัสผ่านใหม่ได้: {error}")
    elif recovery_code and not st.session_state.get("password_recovery_ready"):
        try:
            supabase.auth.exchange_code_for_session(recovery_code)
            st.session_state.auth_page_mode = "reset_password"
            st.session_state.password_recovery_ready = True
            st.session_state.password_recovery_error = None
        except Exception as error:
            st.session_state.password_recovery_error = {
                "error": "access_denied",
                "code": "invalid_or_expired_link",
                "description": str(error),
            }
            st.error(f"ไม่สามารถยืนยันลิงก์ตั้งรหัสผ่านใหม่ได้: {error}")

normalize_recovery_link_params()
detect_password_recovery_session()

if st.session_state.get("auth_page_mode") in ["forgot", "reset_password"]:
    st.session_state.is_authenticated = False

if "user_database" not in st.session_state:
    st.session_state.user_database = {}

if not st.session_state.is_authenticated:

    # --- 4.0 หน้า RESET PASSWORD หลังจากกดลิงก์ในอีเมล ---
    if st.session_state.auth_page_mode == "reset_password":
        st.markdown("<div class='content-card' style='max-width: 550px; margin: 60px auto 0 auto;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #38bdf8 !important;'>🔑 ตั้งรหัสผ่านใหม่</h2>", unsafe_allow_html=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)

        if not st.session_state.get("password_recovery_ready"):
            recovery_error = st.session_state.get("password_recovery_error") or {}
            error_code = recovery_error.get("code", "")
            error_description = recovery_error.get("description", "")
            if error_code == "otp_expired" or "expired" in error_description.lower() or "invalid" in error_description.lower():
                st.error("ลิงก์ตั้งรหัสผ่านหมดอายุหรือถูกใช้ไปแล้ว")
                st.info("คุณสามารถตั้งรหัสผ่านใหม่จากหน้านี้ได้เลย โดยกรอกอีเมลและเบอร์โทรที่ใช้สมัครไว้")
            elif recovery_error:
                st.error(f"ไม่สามารถใช้ลิงก์ตั้งรหัสผ่านนี้ได้: {error_description or error_code}")
                st.info("คุณสามารถตั้งรหัสผ่านใหม่จากหน้านี้ได้เลย โดยกรอกอีเมลและเบอร์โทรที่ใช้สมัครไว้")
            else:
                st.warning("หน้านี้ใช้สำหรับตั้งรหัสผ่านใหม่หลังจากกดลิงก์ในอีเมลเท่านั้น")
                st.info("ถ้าลิงก์หมดอายุหรือเข้าอีเมลไม่ได้ ให้กรอกข้อมูลด้านล่างเพื่อเปลี่ยนรหัสผ่านโดยยืนยันกับฐานข้อมูล")

            direct_reset_email = st.text_input("📧 อีเมลบัญชีผู้ใช้:", key="reset_direct_email").strip().lower()
            direct_reset_phone = st.text_input("📞 เบอร์โทรศัพท์ที่ใช้สมัคร:", key="reset_direct_phone")
            direct_new_pass = st.text_input("🔑 รหัสผ่านใหม่:", type="password", key="reset_direct_new_pass")
            direct_new_pass_conf = st.text_input("🔄 ยืนยันรหัสผ่านใหม่:", type="password", key="reset_direct_new_pass_conf")
            is_direct_reset_strong, direct_reset_msg = check_password_strength(direct_new_pass) if direct_new_pass else (False, "")

            if direct_new_pass:
                if is_direct_reset_strong:
                    st.success(direct_reset_msg)
                else:
                    st.warning(direct_reset_msg)

            if st.button("💾 เปลี่ยนรหัสผ่านใหม่ทันที", type="primary", use_container_width=True):
                if not direct_reset_email or not direct_reset_phone or not direct_new_pass or not direct_new_pass_conf:
                    st.warning("กรุณากรอกอีเมล เบอร์โทร รหัสผ่านใหม่ และยืนยันรหัสผ่านให้ครบ")
                elif direct_new_pass != direct_new_pass_conf:
                    st.error("รหัสผ่านใหม่และยืนยันรหัสผ่านใหม่ไม่ตรงกัน")
                elif not is_direct_reset_strong:
                    st.error("รหัสผ่านใหม่ยังไม่ผ่านเงื่อนไขความปลอดภัย")
                elif not PASSWORD_RESET_FUNCTION_URL:
                    st.error("ยังไม่ได้ตั้งค่า PASSWORD_RESET_FUNCTION_URL สำหรับเชื่อมระบบเปลี่ยนรหัสผ่าน")
                else:
                    try:
                        reset_password_with_email_and_phone(direct_reset_email, direct_reset_phone, direct_new_pass)
                        st.success("เปลี่ยนรหัสผ่านสำเร็จแล้ว กรุณาเข้าสู่ระบบด้วยรหัสผ่านใหม่")
                        st.session_state.auth_page_mode = "login"
                        st.session_state.password_recovery_error = None
                        st.query_params.clear()
                        st.rerun()
                    except Exception as error:
                        st.error(f"เปลี่ยนรหัสผ่านไม่สำเร็จ: {error}")

            st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
            if st.button("กลับไปหน้าเข้าสู่ระบบ", use_container_width=True):
                st.session_state.auth_page_mode = "login"
                st.session_state.password_recovery_error = None
                st.query_params.clear()
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            st.stop()

        new_pass = st.text_input("รหัสผ่านใหม่:", type="password", key="reset_new_pass")
        new_pass_conf = st.text_input("ยืนยันรหัสผ่านใหม่:", type="password", key="reset_new_pass_conf")
        is_reset_strong, reset_pass_msg = check_password_strength(new_pass) if new_pass else (False, "")

        if new_pass:
            if is_reset_strong:
                st.success(reset_pass_msg)
            else:
                st.warning(reset_pass_msg)

        if st.button("💾 บันทึกรหัสผ่านใหม่", type="primary", use_container_width=True):
            if not new_pass or not new_pass_conf:
                st.warning("กรุณากรอกรหัสผ่านใหม่ให้ครบทั้งสองช่อง")
            elif new_pass != new_pass_conf:
                st.error("รหัสผ่านใหม่และช่องยืนยันไม่ตรงกัน")
            elif not is_reset_strong:
                st.error("รหัสผ่านใหม่ยังไม่ผ่านเงื่อนไขความปลอดภัย")
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
                    st.success("เปลี่ยนรหัสผ่านสำเร็จ กรุณาเข้าสู่ระบบด้วยรหัสผ่านใหม่")
                    st.rerun()
                except Exception as error:
                    st.error(f"ไม่สามารถเปลี่ยนรหัสผ่านได้: {error}")

        if st.button("กลับไปหน้าเข้าสู่ระบบ", use_container_width=True):
            st.session_state.auth_page_mode = "login"
            st.query_params.clear()
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    # --- 4.0.5 หน้า FORGOT PASSWORD แยกจากหน้าหลัก ---
    if st.session_state.auth_page_mode == "forgot":
        st.session_state.is_authenticated = False
        st.markdown("<div class='content-card' style='max-width: 620px; margin: 60px auto 0 auto;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #ffb703 !important;'>❓ ลืมรหัสผ่าน</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#cbd5e1 !important;'>กรอกอีเมล เบอร์โทร และรหัสผ่านใหม่ ระบบจะเปลี่ยนรหัสผ่านให้ทันที</p>", unsafe_allow_html=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)

        forgot_email = st.text_input("📧 อีเมลบัญชีผู้ใช้:", key="forgot_email_input").strip().lower()
        forgot_phone = st.text_input("📞 เบอร์โทรศัพท์ที่ใช้สมัคร:", key="forgot_phone_input")
        new_direct_pass = st.text_input("🔑 รหัสผ่านใหม่:", type="password", key="forgot_direct_new_pass")
        new_direct_pass_conf = st.text_input("🔄 ยืนยันรหัสผ่านใหม่:", type="password", key="forgot_direct_new_pass_conf")
        is_direct_strong, direct_pass_msg = check_password_strength(new_direct_pass) if new_direct_pass else (False, "")

        if new_direct_pass:
            if is_direct_strong:
                st.success(direct_pass_msg)
            else:
                st.warning(direct_pass_msg)

        if st.button("💾 ยืนยันและเปลี่ยนรหัสผ่าน", type="primary", use_container_width=True):
            if not forgot_email or not forgot_phone or not new_direct_pass or not new_direct_pass_conf:
                st.warning("กรุณากรอกอีเมล เบอร์โทร และรหัสผ่านใหม่ให้ครบ")
            elif new_direct_pass != new_direct_pass_conf:
                st.error("รหัสผ่านใหม่และช่องยืนยันไม่ตรงกัน")
            elif not is_direct_strong:
                st.error("รหัสผ่านใหม่ยังไม่ผ่านเงื่อนไขความปลอดภัย")
            elif not PASSWORD_RESET_FUNCTION_URL:
                st.error("ยังไม่ได้ตั้งค่า PASSWORD_RESET_FUNCTION_URL สำหรับรีเซ็ตด้วยเบอร์โทร")
            else:
                try:
                    reset_password_with_email_and_phone(forgot_email, forgot_phone, new_direct_pass)
                    st.success("เปลี่ยนรหัสผ่านสำเร็จ กรุณากลับไปเข้าสู่ระบบด้วยรหัสผ่านใหม่")
                    st.session_state.auth_page_mode = "login"
                    st.query_params.clear()
                    st.rerun()
                except Exception as error:
                    st.error(f"เปลี่ยนรหัสผ่านไม่สำเร็จ: {error}")

        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        if st.button("⬅️ กลับไปหน้าเข้าสู่ระบบ", use_container_width=True):
            st.session_state.auth_page_mode = "login"
            st.query_params.clear()
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    # --- 4.1 หน้า LOGIN ---
    if st.session_state.auth_page_mode == "login":
        st.markdown("<div class='content-card' style='max-width: 550px; margin: 60px auto 0 auto;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #ffb703 !important;'>🔐 เข้าสู่ระบบจัดการโภชนาการและฟาร์มไก่ไข่</h2>", unsafe_allow_html=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)

        email_login = st.text_input("📧 อีเมลเข้าใช้งาน:", key="login_email")
        pass_login = st.text_input("🔑 รหัสผ่านเข้าใช้งาน:", type="password", key="login_pass")

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("เข้าสู่ระบบ (Log In)", type="primary", use_container_width=True):
                if not email_login.strip() or not pass_login:
                    st.warning("⚠️ กรุณากรอกอีเมลและรหัสผ่านให้ครบถ้วน")
                else:
                    try:
                        auth_res = supabase.auth.sign_in_with_password({
                            "email": email_login.strip(),
                            "password": pass_login
                        })

                        if auth_res.user:
                            st.session_state.is_authenticated = True
                            login_email = email_login.strip().lower()
                            st.session_state.current_user_key = login_email

                            user_role = get_user_role_from_supabase(login_email)
                            if user_role == "disabled":
                                supabase.auth.sign_out()
                                st.session_state.is_authenticated = False
                                st.error("❌ บัญชีนี้ถูกระงับการใช้งาน กรุณาติดต่อผู้ดูแลระบบ")
                                st.stop()
                            if user_role == "admin":
                                st.session_state.user_role = "admin"
                            else:
                                st.session_state.user_role = "user"
                            st.session_state.user_email = f"{login_email.split('@')[0]} [{st.session_state.user_role.upper()}]"
                            
                            # 🔥 [เพิ่มคำสั่งโหลดข้อมูลของ USER ทันทีที่ล็อกอินผ่าน]
                            fetch_master_data_from_supabase()
                            fetch_ingredients_from_supabase()
                            fetch_saved_formulas_from_supabase() # โหลดสูตรอาหารส่วนตัว
                            fetch_daily_logs_from_supabase()    # โหลดสมุดฟาร์มรายวันส่วนตัว
                            
                            st.success("🎉 เข้าสู่ระบบสำเร็จ ระบบกำลังนำคุณเข้าสู่หน้าหลัก...")
                            st.rerun()

                    except Exception as error:
                        error_msg = str(error).lower()
                        if "name or service not known" in error_msg or "temporary failure in name resolution" in error_msg:
                            st.error("🌐 ไม่สามารถเชื่อมต่ออินเทอร์เน็ตหรือเซิร์ฟเวอร์ฐานข้อมูลได้ กรุณาตรวจสอบการเชื่อมต่อ")
                        elif "invalid login credentials" in error_msg or "bad credentials" in error_msg:
                            st.error("❌ อีเมลหรือรหัสผ่านไม่ถูกต้อง กรุณาตรวจสอบข้อมูลอีกครั้ง")
                        else:
                            st.error(f"❌ ไม่สามารถเข้าสู่ระบบได้เนื่องจากเกิดข้อผิดพลาด: {error}")
        with col_btn2:
            if st.button("🆕 สมัครสมาชิกใหม่ที่นี่", use_container_width=True):
                st.session_state.auth_page_mode = "signup"
                st.rerun()

        st.markdown("<div style='text-align: center; margin-top: 15px;'>", unsafe_allow_html=True)
        if st.button("❓ ลืมรหัสผ่านใช่หรือไม่?", type="secondary"):
            st.session_state.is_authenticated = False
            st.session_state.auth_page_mode = "forgot"
            st.query_params.clear()
            st.query_params["auth_action"] = "forgot_password"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    # --- 4.2 หน้า SIGN UP ---
    elif st.session_state.auth_page_mode == "signup":
        st.markdown("<div class='content-card' style='max-width: 600px; margin: 40px auto 0 auto;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #38bdf8 !important;'>📝 สมัครสมาชิกฟาร์มใหม่ (Sign Up)</h2>", unsafe_allow_html=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)

        su_name = st.text_input("👤 ชื่อจริง:")
        su_surname = st.text_input("👤 นามสกุล:")
        su_tel = st.text_input("📞 เบอร์โทรศัพท์ติดต่อ:")
        su_email = st.text_input("📧 อีเมลบัญชีผู้ใช้ (ใช้เป็นไอดีสำหรับ Log In):")
        st.markdown(
            "<div style='background-color:#1e293b; padding:12px; border-radius:8px; margin-bottom:10px; font-size:0.85rem; color:#94a3b8;'>"
            "🔒 <b>ข้อกำหนดรหัสผ่านความปลอดภัยสูง:</b><br>"
            "- ความยาวไม่น้อยกว่า 8 ตัวอักษร<br>"
            "- มีอักษรพิมพ์ใหญ่ (A-Z) และพิมพ์เล็ก (a-z)<br>"
            "- มีตัวเลข (0-9) และอักขระพิเศษอย่างน้อย 1 ตัว (@, #, $, %, !, ., _)"
            "</div>", unsafe_allow_html=True
        )
        su_pass = st.text_input("🔑 ตั้งรหัสผ่านความปลอดภัยสูง:", type="password")
        su_pass_conf = st.text_input("🔄 พิมพ์ยืนยันรหัสผ่านอีกครั้ง:", type="password")
        is_strong, pass_msg = check_password_strength(su_pass) if su_pass else (False, "")

        if su_pass:
            if is_strong:
                st.success(pass_msg)
            else:
                st.warning(pass_msg)

        col_su1, col_su2 = st.columns(2)
        with col_su1:
            if st.button("✅ ยืนยันการลงทะเบียน", type="primary", use_container_width=True):
                if su_email and su_pass and su_name and su_tel:
                    if su_pass != su_pass_conf:
                        st.error("❌ รหัสผ่านที่ยืนยัน ไม่ตรงกับรหัสผ่านตั้งต้น!")
                    elif not is_strong:
                        st.error("❌ ไม่สามารถลงทะเบียนได้ เนื่องจากรหัสผ่านไม่ปลอดภัยตามมาตรฐาน")
                    else:
                        try:
                            auth_res = supabase.auth.sign_up({
                                "email": su_email.strip().lower(),
                                "password": su_pass,
                                "options": {
                                    "data": {
                                        "first_name": su_name,
                                        "last_name": su_surname,
                                        "phone": su_tel
                                    }
                                }
                            })
                            su_email_clean = su_email.strip().lower()
                            upsert_user_profile(su_email_clean, su_name, su_surname, su_tel, "user")
                            st.session_state.user_database[su_email_clean] = {
                                "name": su_name,
                                "surname": su_surname,
                                "tel": su_tel,
                                "role": "user",
                                "reg_date": str(datetime.date.today())
                            }
                            st.success("🎉 สมัครสมาชิกสำเร็จและเข้าสู่ระบบแล้ว")
                            st.session_state.is_authenticated = True
                            st.session_state.current_user_key = su_email_clean
                            st.session_state.user_role = "user"
                            st.session_state.user_email = f"{su_email_clean.split('@')[0]} [USER]"
                            
                            # 🔥 [เพิ่มคำสั่งโหลดข้อมูลของ USER ใหม่ที่สมัครเสร็จ]
                            fetch_master_data_from_supabase()
                            fetch_ingredients_from_supabase()
                            fetch_saved_formulas_from_supabase() # ดึงตารางสูตร
                            fetch_daily_logs_from_supabase()    # ดึงตารางสมุดประจำวัน
                            
                            st.rerun()
                        except Exception as error:
                            st.error(f"❌ ลงทะเบียนล้มเหลว: {error}")
                else:
                    st.warning("⚠️ กรุณากรอกข้อมูลในช่องจำเป็นให้ครบถ้วน")
        with col_su2:
            if st.button("⬅️ ย้อนกลับไปหน้าล็อกอิน", use_container_width=True):
                st.session_state.auth_page_mode = "login"
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

# 🔥 โหลดข้อมูลวัตถุดิบเริ่มต้นหลังจากผู้ใช้งานผ่านประตูความปลอดภัยเข้าสู่ระบบเรียบร้อยแล้ว เท่านั้น
fetch_master_data_from_supabase()
ingredients = fetch_ingredients_from_supabase()
fetch_nutrient_definitions_from_supabase()

# ==========================================
# 🎉 5. HEADER CONTROL PANEL
# ==========================================
col_h1, col_h2 = st.columns([7.5, 2.5])
with col_h1:
    st.markdown(
        f"""
        <div class="app-main-title">
            <h1>ระบบจัดการโภชนาการและฟาร์มไก่ไข่</h1>
            <p>ผู้ใช้งาน: {st.session_state.user_email}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col_h2:
    cc1, cc2 = st.columns(2)
    with cc1:
        if "admin" in st.session_state.user_email.lower() or st.session_state.user_role == "admin":
            if st.session_state.user_role == "user":
                if st.button("หน้าผู้ดูแล", use_container_width=True):
                    st.session_state.user_role = "admin"
                    st.rerun()
            else:
                if st.button("หน้าผู้ใช้", use_container_width=True):
                    st.session_state.user_role = "user"
                    st.rerun()
    with cc2:
        if st.button("🔴 ออกจากระบบ", use_container_width=True):
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
# 🛠️ 6. MAIN ROUTER & DASHBOARD INTERFACE (UX/UI PREMIUM VERSION)
# ==========================================
if st.session_state.user_role == "admin":
    st.markdown(
        """
        <div class="farm-page-card" style="text-align:center; border-left:1px solid rgba(255,255,255,0.16);">
            <h2>หน้าผู้ดูแลระบบ</h2>
            <p>จัดการข้อมูลกลาง วัตถุดิบ สายพันธุ์ เกณฑ์อาหาร และสิทธิ์ผู้ใช้งาน</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    verified_admin_role = get_user_role_from_supabase(st.session_state.get("current_user_key", ""))
    if verified_admin_role != "admin":
        st.error("บัญชีนี้ยังไม่ได้รับสิทธิ์ admin ในตาราง user_profiles จึงอาจเพิ่ม/แก้/ลบข้อมูลกลางไม่ได้")
    with st.expander("สถานะการเชื่อมต่อฐานข้อมูลสำหรับผู้ดูแล", expanded=False):
        if st.button("รีเฟรชข้อมูลกลางจาก Supabase", use_container_width=True):
            fetch_master_data_from_supabase()
            fetch_ingredients_from_supabase()
            fetch_nutrient_definitions_from_supabase()
            fetch_user_profiles_from_supabase()
            st.success("โหลดข้อมูลล่าสุดจาก Supabase แล้ว")
            st.rerun()
        debug_rows = st.session_state.get("master_load_debug", [])
        if debug_rows:
            render_readable_table(pd.DataFrame(debug_rows))
        st.caption("ถ้ากดเพิ่ม/ลบ/แก้ไขแล้วยังไม่ได้ ให้รันไฟล์ supabase_admin_crud_policies.sql ใน Supabase SQL Editor ก่อน")
    
    st.markdown("<div class='center-menu-wrap'>", unsafe_allow_html=True)
    selected_admin_page = render_big_menu(
        "selected_admin_page",
        [
            {"id": "nutrients", "label": "สารอาหาร"},
            {"id": "ingredients", "label": "วัตถุดิบ"},
            {"id": "breeds", "label": "สายพันธุ์"},
            {"id": "targets", "label": "เกณฑ์อาหาร"},
            {"id": "users", "label": "ผู้ใช้งาน"},
        ],
        columns_per_row=3,
    )
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
    admin_page_info = {
        "nutrients": ("สารอาหาร", "เพิ่ม ลบ หรือดูหัวข้อสารอาหารที่ใช้ในสูตรอาหาร"),
        "ingredients": ("วัตถุดิบ", "จัดการวัตถุดิบ ราคา และค่าทางโภชนาการ"),
        "breeds": ("สายพันธุ์", "เพิ่มหรือแก้ไขข้อมูลสายพันธุ์ไก่ไข่"),
        "targets": ("เกณฑ์อาหาร", "ตั้งค่าเกณฑ์โภชนาการตามช่วงอายุ"),
        "users": ("ผู้ใช้งาน", "ดูรายชื่อและเปลี่ยนสิทธิ์ผู้ใช้งาน"),
    }
    admin_title, admin_subtitle = admin_page_info[selected_admin_page]
    st.markdown(
        f"<div class='farm-page-card'><h2>{admin_title}</h2><p>{admin_subtitle}</p></div>",
        unsafe_allow_html=True,
    )
    
    # --- แท็บที่ 0: ดูสารอาหารที่ระบบรองรับ ---
    if selected_admin_page == "nutrients":
        st.subheader("จัดการสารอาหาร")
        nutrient_error = st.session_state.get("nutrient_definitions_error")
        if nutrient_error:
            st.warning(f"ยังเชื่อมตารางสารอาหารไม่ได้: {nutrient_error}")
        elif st.session_state.get("nutrient_definitions_loaded_from_db"):
            st.success("เชื่อมต่อรายการสารอาหารจาก Supabase แล้ว")

        df_nutrients = pd.DataFrame([
            {
                "รหัสข้อมูล": k,
                "ชื่อที่แสดง": v["label"],
                "หน่วย/ความละเอียด": v["step"],
                "ประเภท": "สารอาหารหลัก" if v.get("is_core") else "เพิ่มเอง",
            }
            for k, v in st.session_state.db_nutrient_keys.items()
        ])
        render_readable_table(df_nutrients)

        n_col1, n_col2 = st.columns(2, gap="large")
        with n_col1:
            st.markdown("### เพิ่มสารอาหาร")
            with st.form("form_add_nutrient_definition"):
                new_nut_key = st.text_input("รหัสข้อมูล", placeholder="เช่น fat, ash, sodium").strip().lower()
                new_nut_label = st.text_input("ชื่อที่แสดง", placeholder="เช่น ไขมันดิบ (%)")
                new_nut_step = st.number_input("ความละเอียดในการกรอกค่า", min_value=0.001, max_value=1000.0, value=0.1, format="%.3f")
                new_nut_default = st.number_input("ค่าเริ่มต้น", min_value=0.0, value=0.0, step=0.1)
                add_nutrient = st.form_submit_button("บันทึกสารอาหารใหม่", type="primary", use_container_width=True)

            if add_nutrient:
                if not new_nut_key or not new_nut_label:
                    st.error("กรุณากรอกรหัสข้อมูลและชื่อที่แสดง")
                elif not re.match(r"^[a-z][a-z0-9_]*$", new_nut_key):
                    st.error("รหัสข้อมูลต้องเป็นภาษาอังกฤษตัวเล็ก ตัวเลข หรือ _ และต้องขึ้นต้นด้วยตัวอักษร")
                elif new_nut_key in st.session_state.db_nutrient_keys:
                    st.error("รหัสข้อมูลนี้มีอยู่แล้ว")
                else:
                    try:
                        add_nutrient_definition_to_supabase(new_nut_key, new_nut_label, new_nut_step, new_nut_default)
                        st.success(f"เพิ่มสารอาหาร '{new_nut_label}' แล้ว")
                        st.rerun()
                    except Exception as e:
                        st.error(f"เพิ่มสารอาหารไม่สำเร็จ: {e}")

        with n_col2:
            st.markdown("### ลบสารอาหาร")
            removable_nutrients = [
                key for key, data in st.session_state.db_nutrient_keys.items()
                if key
            ]
            if removable_nutrients:
                nutrient_to_delete = st.selectbox(
                    "เลือกสารอาหารที่ต้องการลบ",
                    removable_nutrients,
                    format_func=lambda key: st.session_state.db_nutrient_keys[key]["label"],
                )
                confirm_delete_nutrient = st.checkbox("ยืนยันว่าต้องการลบสารอาหารนี้ออกจาก Supabase ถาวร")
                if st.button("ลบสารอาหารจาก Supabase", type="secondary", use_container_width=True, disabled=not confirm_delete_nutrient):
                    try:
                        label = st.session_state.db_nutrient_keys[nutrient_to_delete]["label"]
                        delete_nutrient_definition_from_supabase(nutrient_to_delete)
                        st.success(f"ลบสารอาหาร '{label}' ออกจาก Supabase แล้ว")
                        st.rerun()
                    except Exception as e:
                        st.error(f"ลบสารอาหารไม่สำเร็จ: {e}")
            else:
                st.info("ยังไม่มีรายการสารอาหารให้ลบ")

    # --- แท็บที่ 1: จัดการและแก้ไขวัตถุดิบ/สารอาหาร ---
    if selected_admin_page == "ingredients":
        with st.expander("📊 เปิดดูคลังวัตถุดิบและราคาปัจจุบันในระบบ", expanded=False):
            if st.session_state.db_ingredients:
                render_readable_table(
                    build_ingredients_display(),
                    column_config={
                        "ราคา/กก.": st.column_config.NumberColumn(format="%.2f บาท"),
                        "โปรตีน (%)": st.column_config.NumberColumn(format="%.2f %%"),
                        "แคลเซียม (%)": st.column_config.NumberColumn(format="%.2f %%"),
                        "ฟอสฟอรัส (%)": st.column_config.NumberColumn(format="%.2f %%"),
                        "ใช้ขั้นต่ำ (%)": st.column_config.NumberColumn(format="%.1f %%"),
                        "ใช้สูงสุด (%)": st.column_config.NumberColumn(format="%.1f %%"),
                    },
                )
            else:
                st.info("คลังวัตถุดิบว่างเปล่า")
        
        crud_mode = st.segmented_control(
            "เลือกฟังก์ชันจัดการคลังวัตถุดิบ:", 
            ["✏️ แก้ไขข้อมูลวัตถุดิบเดิม", "➕ เพิ่มวัตถุดิบใหม่", "🗑️ ลบวัตถุดิบออก"],
            default="✏️ แก้ไขข้อมูลวัตถุดิบเดิม"
        )
        st.markdown("---")

        if crud_mode == "✏️ แก้ไขข้อมูลวัตถุดิบเดิม" and st.session_state.db_ingredients:
            selected_ing_edit = st.selectbox("เลือกวัตถุดิบที่จะปรับปรุงข้อมูล:", list(st.session_state.db_ingredients.keys()))
            target_ing = st.session_state.db_ingredients[selected_ing_edit]
            
            with st.form(key=f"form_edit_{selected_ing_edit}"):
                st.markdown(f"#### 📝 แก้ไขข้อมูลสารอาหารของ: **{selected_ing_edit}**")
                
                c_limits = st.columns(2)
                with c_limits[0]:
                    edit_ing_min = st.number_input("สัดส่วนขั้นต่ำที่ต้องใช้ในสูตร (% Min):", min_value=0.0, max_value=100.0, value=float(target_ing.get("min_limit", 0.0)), step=0.1)
                with c_limits[1]:
                    edit_ing_max = st.number_input("สัดส่วนสูงสุดที่ห้ามเกินในสูตร (% Max):", min_value=0.0, max_value=100.0, value=float(target_ing.get("max_limit", 100.0)), step=0.1)
                
                st.markdown("**📊 ค่าโภชนาการและสารอาหาร**")
                edited_values = {}
                ec = st.columns(3)
                for idx, (nut_key, nut_info) in enumerate(st.session_state.db_nutrient_keys.items()):
                    with ec[idx % 3]:
                        # ป้องกันบั๊ก KeyError ด้วยการใช้ .get() และเรียกใช้ค่า default เผื่อไว้
                        current_val = float(target_ing.get(nut_key, nut_info.get("default", 0.0)))
                        edited_values[nut_key] = st.number_input(f"{nut_info['label']}:", min_value=0.0, value=current_val, step=nut_info["step"])
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("💾 บันทึกการเปลี่ยนแปลงทั้งหมด", type="primary", use_container_width=True):
                    if edit_ing_min > edit_ing_max:
                        st.error("❌ ข้อผิดพลาด: สัดส่วนต่ำสุด (% Min) ห้ามมากกว่าสัดส่วนสูงสุด (% Max)")
                    else:
                        # ⚡ ซิงค์ความถาวรลง Supabase Cloud Database แบบเรียลไทม์
                        try:
                            owner_email = get_ingredient_owner_for_write(target_ing)
                            payload = {"name": selected_ing_edit, "min_limit": edit_ing_min, "max_limit": edit_ing_max, "owner_email": owner_email}
                            payload.update(edited_values)
                            filters = {"id": target_ing.get("id")} if target_ing.get("id") else {"name": selected_ing_edit, "owner_email": owner_email}
                            table_mutation("ingredients", "update", payload, filters)
                            fetch_ingredients_from_supabase()
                            st.session_state.pop("auto_formula_context", None)
                            st.session_state.current_weights = {}
                            st.success(f"🎉 ปรับปรุงข้อมูลสารอาหารของ '{selected_ing_edit}' ลงระบบคลาวด์เรียบร้อยแล้ว")
                            st.rerun()
                        except Exception as cloud_err:
                            st.error(f"❌ บันทึกวัตถุดิบไม่สำเร็จ: {cloud_err}")

        elif crud_mode == "➕ เพิ่มวัตถุดิบใหม่":
            with st.form(key="form_add_new_ingredient"):
                st.markdown("#### ➕ ลงทะเบียนวัตถุดิบตัวใหม่เข้าคลังกลาง")
                ing_name = st.text_input("📝 ระบุชื่อวัตถุดิบใหม่:", placeholder="เช่น รำข้าวหอมมะลิบดละเอียด")
                
                c_limits = st.columns(2)
                with c_limits[0]:
                    ing_min = st.number_input("สัดส่วนขั้นต่ำที่ต้องใช้ในสูตร (% Min):", min_value=0.0, value=0.0)
                with c_limits[1]:
                    ing_max = st.number_input("สัดส่วนสูงสุดที่ห้ามเกินในสูตร (% Max):", min_value=0.0, value=100.0)
                
                st.markdown("**📊 ระบุสารอาหารตั้งต้น**")
                new_material_data = {}
                ac = st.columns(3)
                for idx, (nut_key, nut_info) in enumerate(st.session_state.db_nutrient_keys.items()):
                    with ac[idx % 3]:
                        new_material_data[nut_key] = st.number_input(f"{nut_info['label']}:", min_value=0.0, value=nut_info.get("default", 0.0), step=nut_info["step"])
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("➕ บันทึกเพิ่มเข้าคลังสินค้ากลาง", type="primary", use_container_width=True):
                    if not ing_name.strip():
                        st.error("❌ กรุณากรอกชื่อวัตถุดิบด้วยครับ")
                    elif ing_name in st.session_state.db_ingredients:
                        st.error(f"❌ รายการ '{ing_name}' มีในระบบอยู่แล้ว")
                    elif ing_min > ing_max:
                        st.error("❌ ข้อผิดพลาด: ค่าต่ำสุดห้ามมากกว่าค่าสูงสุด")
                    else:
                        owner_email = get_ingredient_owner_for_write()
                        base_data = {"name": ing_name, "min_limit": ing_min, "max_limit": ing_max, "owner_email": owner_email}
                        base_data.update(new_material_data)
                        
                        try:
                            table_mutation("ingredients", "insert", base_data)
                            fetch_ingredients_from_supabase()
                            st.session_state.pop("auto_formula_context", None)
                            st.session_state.current_weights = {}
                            st.success(f"🎉 นำเข้า '{ing_name}' สู่คลาวด์ฐานข้อมูลเรียบร้อย!")
                            st.rerun()
                        except Exception as cloud_err:
                            st.error(f"❌ เพิ่มวัตถุดิบไม่สำเร็จ: {cloud_err}")

        elif crud_mode == "🗑️ ลบวัตถุดิบออก" and st.session_state.db_ingredients:
            st.markdown("#### 🗑️ ลบรายการวัตถุดิบ")
            to_del = st.selectbox("เลือกวัตถุดิบที่จะนำออกจากระบบถาวร:", list(st.session_state.db_ingredients.keys()))
            if st.button("🗑️ ยืนยันคำสั่งลบวัตถุดิบออกจากระบบ", type="primary", use_container_width=True):
                ingredient_to_delete = st.session_state.db_ingredients.get(to_del, {})
                owner_email = get_ingredient_owner_for_write(ingredient_to_delete)
                try:
                    filters = {"id": ingredient_to_delete.get("id")} if ingredient_to_delete.get("id") else {"name": to_del, "owner_email": owner_email}
                    table_mutation("ingredients", "delete", filters=filters)
                    fetch_ingredients_from_supabase()
                    st.session_state.pop("auto_formula_context", None)
                    st.session_state.current_weights = {}
                    st.success(f"🔥 ลบ '{to_del}' ออกจากคลังเรียบร้อยแล้ว")
                    st.rerun()
                except Exception as cloud_err:
                    st.error(f"❌ ลบวัตถุดิบไม่สำเร็จ: {cloud_err}")

    # --- แท็บที่ 2: จัดการทำเนียบสายพันธุ์ ---
    if selected_admin_page == "breeds":
        with st.expander("📊 เปิดดูทำเนียบสายพันธุ์ไก่ไข่ในระบบทั้งหมด", expanded=True):
            render_readable_table(build_breeds_display())
            
        st.markdown("---")
        bc1, bc2 = st.columns(2, gap="large")
        
        with bc1:
            st.markdown("### ➕ เพิ่มสายพันธุ์ใหม่")
            with st.container(border=True):
                b_group = st.selectbox("กลุ่มสายพันธุ์หลัก:", [g["group_name"] for g in st.session_state.db_groups])
                b_name = st.text_input("ชื่อทางการค้า (Breed Name):", placeholder="เช่น ไฮ-เซ็กซ์ บราวน์")
                b_egg = st.text_input("ลักษณะเด่น/สีของเปลือกไข่:", placeholder="เช่น เปลือกไข่สีน้ำตาลเข้ม")
                b_feed = st.number_input("อัตรากินอาหารตามคู่มือ (กรัม/ตัว/วัน):", value=115.0, step=1.0)
                if st.button("➕ บันทึกสายพันธุ์ใหม่", use_container_width=True, type="primary"):
                    if b_name.strip():
                        breed_payload = {"group_name": b_group, "breed_name": b_name, "egg_color": b_egg, "default_feed": b_feed}
                        try:
                            table_mutation("db_breeds", "insert", breed_payload)
                            fetch_master_data_from_supabase()
                            st.success(f"🎉 เพิ่มสายพันธุ์ '{b_name}' สำเร็จ")
                            st.rerun()
                        except Exception as cloud_err:
                            st.error(f"❌ เพิ่มสายพันธุ์ไม่สำเร็จ: {cloud_err}")
                    else: st.warning("⚠️ กรุณากรอกชื่อสายพันธุ์")
        with bc2:
            st.markdown("### ❌ ลบข้อมูลสายพันธุ์")
            with st.container(border=True):
                if st.session_state.db_breeds:
                    breed_delete_options = {
                        f"#{b.get('id', '-')}: {b['breed_name']}": b
                        for b in st.session_state.db_breeds
                    }
                    b_del_label = st.selectbox("เลือกสายพันธุ์ที่ต้องการลบ:", list(breed_delete_options.keys()))
                    b_del = breed_delete_options[b_del_label]
                    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
                    if st.button("🗑️ ยืนยันลบออกจากทำเนียบ", type="primary", use_container_width=True):
                        try:
                            filters = {"id": b_del.get("id")} if b_del.get("id") else {"breed_name": b_del.get("breed_name")}
                            table_mutation("db_breeds", "delete", filters=filters)
                            fetch_master_data_from_supabase()
                            st.success(f"🔥 ลบสายพันธุ์ '{b_del.get('breed_name')}' เรียบร้อยแล้ว")
                            st.rerun()
                        except Exception as cloud_err:
                            st.error(f"❌ ลบสายพันธุ์ไม่สำเร็จ: {cloud_err}")
                else: st.info("ไม่มีข้อมูลสายพันธุ์ในระบบ")

    # --- แท็บที่ 3: แก้ไขเป้าหมายความต้องการโภชนาการสัตว์แยกตามอายุ ---
    if selected_admin_page == "targets":
        with st.expander("📊 เปิดดูค่าเกณฑ์มาตรฐานโภชนาการสัตว์ ณ ปัจจุบัน", expanded=False):
            render_readable_table(build_targets_display())
        
        st.markdown("### ✏️ ปรับเปลี่ยนเกณฑ์ข้อกำหนดสารอาหารขั้นต่ำประจำช่วงอายุ")
        select_stage_crud = st.selectbox("เลือกช่วงระยะผลิตของไก่ไข่ที่ต้องการแก้ไขเกณฑ์:", list(st.session_state.db_targets.keys()), format_func=lambda x: st.session_state.db_targets[x]["stage_name"])
        
        with st.form(key=f"form_target_{select_stage_crud}"):
            st.markdown(f"📝 ตั้งค่าเกณฑ์ขั้นต่ำสำหรับช่วงอายุ: **{st.session_state.db_targets[select_stage_crud]['stage_name']}**")
            
            sc = st.columns(3)
            updated_target_values = {}
            target_nut_keys = [k for k in st.session_state.db_nutrient_keys.keys() if k != "price"]
            
            for idx, nut_key in enumerate(target_nut_keys):
                nut_info = st.session_state.db_nutrient_keys[nut_key]
                with sc[idx % 3]:
                    target_column = "fiber_max" if nut_key == "fiber" else nut_key
                    raw_val = st.session_state.db_targets[select_stage_crud].get(target_column, 0.0)
                    current_target_val = float(raw_val) if raw_val is not None else 0.0
                    updated_target_values[nut_key] = st.number_input(f"ขั้นต่ำของ {nut_info['label']}:", value=current_target_val, step=nut_info["step"])
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("💾 ยืนยันอัปเดตเกณฑ์โภชนาการช่วงอายุนี้", type="primary", use_container_width=True):
                db_target_update = {
                    ("fiber_max" if key == "fiber" else key): value
                    for key, value in updated_target_values.items()
                }
                try:
                    target_response = supabase.table("db_targets").update(db_target_update).eq("stage_key", select_stage_crud).execute()
                    require_supabase_rows(target_response, "อัปเดตเกณฑ์อาหารหลัก")
                    standard_update = {
                        "min_protein": updated_target_values.get("protein", 0.0),
                        "min_me": updated_target_values.get("me", 0.0),
                        "min_calcium": updated_target_values.get("calcium", 0.0),
                        "min_phosphorus": updated_target_values.get("phos", 0.0),
                        "min_lysine": updated_target_values.get("lysine", 0.0),
                        "min_methionine": updated_target_values.get("methionine", 0.0),
                    }
                    if "fiber" in updated_target_values:
                        standard_update["max_fiber"] = updated_target_values["fiber"]
                    standard_response = supabase.table("nutrition_standards").update(standard_update).eq("phase_key", select_stage_crud).execute()
                    require_supabase_rows(standard_response, "อัปเดตมาตรฐานโภชนาการหน้าคำนวณ")
                    fetch_master_data_from_supabase()
                    st.session_state.pop("auto_formula_context", None)
                    st.session_state.current_weights = {}
                    st.success("🎉 อัปเดตเกณฑ์มาตรฐานความต้องการทางโภชนาการเรียบร้อยแล้ว!")
                    st.rerun()
                except Exception as cloud_err:
                    st.error(f"❌ อัปเดตเกณฑ์โภชนาการไม่สำเร็จ: {cloud_err}")

    # --- แท็บที่ 4: จัดการสมาชิกผู้ใช้งาน ---
    if selected_admin_page == "users":
        st.subheader("👤 สรุปบัญชีผู้ใช้งานในระบบ")
        if st.button("🔄 โหลดรายชื่อผู้ใช้จาก Supabase", use_container_width=True):
            fetch_user_profiles_from_supabase()
            st.rerun()
        fetch_user_profiles_from_supabase()
        
        users_list = []
        for email, info in st.session_state.user_database.items():
            role_badge = "🔑 ADMIN" if info.get("role") == "admin" else "👤 USER"
            status_badge = "⛔ ระงับ" if info.get("status") == "disabled" else "✅ ใช้งาน"
            users_list.append({
                "Email ID / Username": email,
                "ชื่อ-นามสกุล": f"{info.get('name', '-')} {info.get('surname', '-')}",
                "เบอร์โทรศัพท์": info.get("tel", "-"),
                "ระดับสิทธิ์ (Role)": role_badge,
                "สถานะ": status_badge,
                "วันที่ลงทะเบียน": info.get("reg_date", "2026-01-01")
            })
            
        if users_list:
            render_readable_table(pd.DataFrame(users_list))
        else:
            st.info("ℹ️ ยังไม่มีข้อมูลในตาราง user_profiles กรุณารัน SQL sync_user_profiles.sql ใน Supabase ก่อน")
            
        st.markdown("---")
        uc1 = st.container()
        with uc1:
            st.markdown("### ✏️ เปลี่ยนแปลงสิทธิ์ของสมาชิก")
            with st.container(border=True):
                user_keys = list(st.session_state.get("user_database", {}).keys())
                if not user_keys:
                    st.warning("ยังไม่มีข้อมูลสมาชิกในตาราง user_profiles")
                else:
                    selected_user_email = st.selectbox("เลือกบัญชีอีเมลที่ต้องการแก้ไข:", user_keys)
                    current_user_role = st.session_state.user_database[selected_user_email]["role"]
                    new_role = st.selectbox("ระบุสิทธิ์ใหม่ที่ต้องการมอบให้:", ["user", "admin"], index=0 if current_user_role == "user" else 1)
                    
                    if st.button("💾 บันทึกการเปลี่ยนสิทธิ์", use_container_width=True, type="primary"):
                        if update_user_profile_role(selected_user_email, new_role):
                            st.success(f"🎉 อัปเดตสิทธิ์ของ {selected_user_email} เป็น {new_role.upper()} สำเร็จ")
                            st.rerun()
        
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("สลับกลับไปหน้าผู้ใช้งานทั่วไป", use_container_width=True):
        st.session_state.user_role = "user"
        st.rerun()
       
else:
    # ==========================================
    # 🎨 PROFESSIONAL FARM OPERATIONS UI
    # ==========================================
    st.markdown(
        """
        <style>
            .stNumberInput input, .stSelectbox div, .stSlider div {
                font-size: 1rem !important;
                font-weight: 650 !important;
            }
            label {
                font-size: 0.98rem !important;
                font-weight: 750 !important;
                color: #f1f5f9 !important;
            }
            .stButton button {
                font-size: 1rem !important;
                font-weight: 800 !important;
                padding: 12px 16px !important;
                border-radius: 8px !important;
                min-height: 48px !important;
            }
            .farmer-card {
                background: rgba(15, 23, 42, 0.86) !important;
                border: 1px solid rgba(148, 163, 184, 0.28) !important;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 16px;
                box-shadow: 0 16px 36px rgba(0, 0, 0, 0.18);
            }
            .big-metric-value {
                font-size: 1.9rem !important;
                font-weight: 850 !important;
                color: #38bdf8;
            }
            .big-metric-label {
                font-size: 0.92rem !important;
                color: #94a3b8;
                text-transform: uppercase;
                letter-spacing: 0.02em;
            }
            .ops-kpi {
                background: linear-gradient(180deg, rgba(15, 23, 42, 0.96), rgba(15, 23, 42, 0.78));
                border: 1px solid rgba(148, 163, 184, 0.28);
                border-radius: 8px;
                padding: 16px;
                min-height: 128px;
                margin-bottom: 18px;
            }
            .ops-kpi .label {
                color: #94a3b8 !important;
                font-size: 0.88rem;
                font-weight: 800;
                margin-bottom: 8px !important;
            }
            .ops-kpi .value {
                color: #f8fafc !important;
                font-size: 1.9rem;
                font-weight: 900;
                margin-bottom: 4px !important;
            }
            .ops-kpi .note {
                color: #cbd5e1 !important;
                font-size: 0.9rem;
                margin: 0 !important;
            }
            .section-title {
                margin: 4px 0 14px 0;
                padding-bottom: 8px;
                border-bottom: 1px solid rgba(148, 163, 184, 0.22);
            }
            .section-title h3 {
                margin: 0 !important;
                font-size: 1.18rem !important;
            }
            .status-panel {
                background: rgba(2, 6, 23, 0.58);
                border: 1px solid rgba(148, 163, 184, 0.24);
                border-radius: 8px;
                padding: 14px 16px;
                margin-bottom: 10px;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    # ==========================================
    # 👑 USER ROUTE: ACCESSIBLE INTERFACE
    # ==========================================
    st.markdown("<div class='center-menu-wrap'>", unsafe_allow_html=True)
    selected_user_page = render_big_menu(
        "selected_user_page",
        [
            {"id": "dashboard", "label": "ภาพรวมฟาร์ม"},
            {"id": "formula", "label": "คำนวณสูตรอาหาร"},
            {"id": "daily", "label": "บันทึกประจำวัน"},
            {"id": "mixing", "label": "ใบสั่งผสมอาหาร"},
        ],
        columns_per_row=4,
    )
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
    user_page_info = {
        "dashboard": ("ภาพรวมฟาร์ม", "ติดตามผลผลิต ต้นทุน และความเสี่ยงล่าสุดของฟาร์ม"),
        "formula": ("คำนวณสูตรอาหาร", "เลือกสายพันธุ์ ปรับวัตถุดิบ และตรวจเกณฑ์โภชนาการ"),
        "daily": ("บันทึกประจำวัน", "กรอกผลผลิต ต้นทุน และตัวชี้วัดประจำวัน"),
        "mixing": ("ใบสั่งผสมอาหาร", "สรุปวัตถุดิบที่ต้องใช้สำหรับงานผสมอาหาร"),
    }
    user_title, user_subtitle = user_page_info[selected_user_page]
    st.markdown(
        f"<div class='farm-page-card'><h2>{user_title}</h2><p>{user_subtitle}</p></div>",
        unsafe_allow_html=True,
    )

# ------------------------------------------
# ------------------------------------------
    # DASHBOARD: FARM OPERATIONS OVERVIEW
    # ------------------------------------------
    if selected_user_page == "dashboard":
        logs_sorted = sort_daily_logs_latest_first(st.session_state.get("daily_logs", []))
        latest_log = logs_sorted[0] if logs_sorted else {}
        current_feed_cost = float(st.session_state.get("current_net_cost", 0.0) or calculate_current_feed_cost() or 0.0)
        current_formula_name = st.session_state.get("selected_b_name", "ยังไม่ได้เลือกสูตร")

        kpi_cols = st.columns(4)
        with kpi_cols[0]:
            st.markdown(
                f"""
                <div class="ops-kpi">
                    <p class="label">ไข่ล่าสุด</p>
                    <p class="value">{int(latest_log.get('collected_eggs') or 0):,}</p>
                    <p class="note">ฟอง / วัน</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with kpi_cols[1]:
            st.markdown(
                f"""
                <div class="ops-kpi">
                    <p class="label">กำไรสุทธิล่าสุด</p>
                    <p class="value">{float(latest_log.get('net_profit_day') or 0):,.0f}</p>
                    <p class="note">บาท</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with kpi_cols[2]:
            st.markdown(
                f"""
                <div class="ops-kpi">
                    <p class="label">Hen-day</p>
                    <p class="value">{float(latest_log.get('henday_pct') or 0):,.1f}%</p>
                    <p class="note">อัตราการให้ไข่ล่าสุด</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with kpi_cols[3]:
            st.markdown(
                f"""
                <div class="ops-kpi">
                    <p class="label">ต้นทุนสูตรปัจจุบัน</p>
                    <p class="value">{current_feed_cost:,.2f}</p>
                    <p class="note">บาท / กก.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        dash_left, dash_right = st.columns([1.35, 0.85], gap="large")
        with dash_left:
            st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'><h3>แนวโน้มผลผลิตและกำไร</h3></div>", unsafe_allow_html=True)
            if logs_sorted:
                trend_df = build_daily_logs_analysis(logs_sorted).tail(30)
                trend_summary = (
                    trend_df.assign(day=trend_df["date"].dt.date)
                    .groupby("day", as_index=False)
                    .agg({
                        "collected_eggs": "sum",
                        "net_profit_day": "sum",
                    })
                    .sort_values("day")
                )
                trend_summary["day_label"] = pd.to_datetime(trend_summary["day"]).dt.strftime("%d/%m")

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=trend_summary["day_label"],
                    y=trend_summary["collected_eggs"],
                    mode="lines+markers",
                    name="ไข่รวม (ฟอง)",
                    line=dict(color="#38bdf8", width=3),
                    marker=dict(size=9),
                    hovertemplate="วันที่ %{x}<br>ไข่ %{y:,.0f} ฟอง<extra></extra>",
                ))
                fig.add_trace(go.Scatter(
                    x=trend_summary["day_label"],
                    y=trend_summary["net_profit_day"],
                    name="กำไรสุทธิ (บาท)",
                    mode="lines+markers",
                    line=dict(color="#22c55e", width=3),
                    marker=dict(size=9),
                    yaxis="y2",
                    hovertemplate="วันที่ %{x}<br>กำไร %{y:,.0f} บาท<extra></extra>",
                ))
                fig.update_layout(
                    height=340,
                    margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(15,23,42,0.35)",
                    font=dict(color="#e2e8f0"),
                    legend=dict(orientation="h", y=1.10),
                    hovermode="x unified",
                    xaxis=dict(title="วันที่", type="category", gridcolor="rgba(148,163,184,0.12)"),
                    yaxis=dict(title="ไข่ (ฟอง)", gridcolor="rgba(148,163,184,0.18)", rangemode="tozero"),
                    yaxis2=dict(title="กำไร (บาท)", overlaying="y", side="right", showgrid=False, zeroline=True, zerolinecolor="rgba(248,250,252,0.35)"),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("ยังไม่มีข้อมูลบันทึกประจำวันสำหรับสร้างกราฟ")
            st.markdown("</div>", unsafe_allow_html=True)

        with dash_right:
            st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'><h3>สถานะล่าสุด</h3></div>", unsafe_allow_html=True)
            if latest_log:
                alerts = []
                if float(latest_log.get("henday_pct") or 0) < 65:
                    alerts.append(("ต้องติดตาม", "Hen-day ต่ำกว่า 65% ควรตรวจอาหาร น้ำ และสุขภาพฝูง"))
                if float(latest_log.get("fcr_ratio") or 0) > 3:
                    alerts.append(("ต้นทุนสูง", "FCR สูง ควรตรวจน้ำหนักไข่และปริมาณอาหารที่ให้"))
                if int(latest_log.get("dead_birds") or 0) > max(1, int(latest_log.get("bird_count") or 0) * 0.001):
                    alerts.append(("ความเสี่ยงสุขภาพ", "จำนวนไก่ตาย/คัดทิ้งสูงกว่าปกติ"))

                if alerts:
                    for title, body in alerts:
                        st.markdown(
                            f"<div class='status-panel'><b>{title}</b><br><span style='color:#cbd5e1;'>{body}</span></div>",
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown(
                        "<div class='status-panel'><b>สถานะปกติ</b><br><span style='color:#cbd5e1;'>ตัวชี้วัดล่าสุดไม่พบสัญญาณเสี่ยงหลัก</span></div>",
                        unsafe_allow_html=True,
                    )

                st.markdown(
                    f"<div class='status-panel'><b>สูตร/สายพันธุ์ที่ใช้งาน</b><br><span style='color:#cbd5e1;'>{current_formula_name}</span></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.info("เริ่มจากบันทึกข้อมูลประจำวัน เพื่อให้ระบบแสดงสถานะฟาร์ม")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'><h3>บันทึกล่าสุด</h3></div>", unsafe_allow_html=True)
        if logs_sorted:
            render_readable_table(build_daily_logs_display(logs_sorted[:7]))
        else:
            st.info("ยังไม่มีประวัติฟาร์มย้อนหลัง")
        st.markdown("</div>", unsafe_allow_html=True)

    # TAB 1: MANAGEMENT & FORMULA MATRIX
    # ------------------------------------------
    if selected_user_page == "formula":
        # --- ส่วนที่ 1: ดึงสูตรเก่า ---
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'><h3>1. สูตรอาหารที่บันทึกไว้</h3></div>", unsafe_allow_html=True)
        if not st.session_state.saved_formulas:
            st.info("💡 ตอนนี้ยังไม่มีสูตรอาหารที่บันทึกไว้")
        else:
            col_load1, col_load2, col_load3 = st.columns([6, 2, 2])
            with col_load1:
                selected_f_name = st.selectbox(
                    "🔍 เลือกชื่อสูตรเก่าที่ต้องการดู:",
                    [f["name"] for f in st.session_state.saved_formulas],
                )
            with col_load2:
                st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                if st.button("🔄 ดึงสูตรนี้มาใช้", use_container_width=True):
                    target_f = next(
                        f
                        for f in st.session_state.saved_formulas
                        if f["name"] == selected_f_name
                    )
                    st.session_state.current_weights = normalize_formula_weights(target_f.get("weights", {}))
                    st.session_state["selected_b_name"] = target_f.get("breed", st.session_state.get("selected_b_name", "สูตรอาหารปัจจุบัน"))
                    st.session_state["selected_stage_label"] = target_f.get("stage", st.session_state.get("selected_stage_label", "ยังไม่ได้เลือกช่วงอายุ"))
                    st.session_state["current_net_cost"] = float(target_f.get("cost") or calculate_current_feed_cost())
                    st.success(f"ดึงข้อมูล '{selected_f_name}' มาใช้งานแล้ว!")
                    st.rerun()
            with col_load3:
                st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️ ลบสูตรนี้", use_container_width=True):
                    target_f = next(
                        f
                        for f in st.session_state.saved_formulas
                        if f["name"] == selected_f_name
                    )
                    if delete_formula_from_supabase(target_f.get("id")):
                        st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        # --- ส่วนที่ 2: เลือกสายพันธุ์ และ ตั้งค่าโภชนาการเป้าหมายจาก Supabase ---
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'><h3>2. ตั้งค่าเป้าหมายโภชนาการ</h3></div>", unsafe_allow_html=True)

        col_br1, col_br2, col_br3 = st.columns(3)
        with col_br1:
            list_groups = [g["group_name"] for g in st.session_state.db_groups]
            selected_g = st.selectbox("📁 เลือกกลุ่มสายพันธุ์หลัก:", list_groups)

            # กรองสายพันธุ์ตามกลุ่มที่เลือก
            filtered_breeds = [
                b for b in st.session_state.db_breeds if b["group_name"] == selected_g
            ]
            breed_names = (
                [b["breed_name"] for b in filtered_breeds] if filtered_breeds else ["ไม่มีข้อมูล"]
            )

        with col_br2:
            selected_b_name = st.selectbox("🐔 เลือกสายพันธุ์ไก่ไข่:", breed_names)
            st.session_state["selected_b_name"] = selected_b_name

            # ดึงข้อมูลสายพันธุ์และเซฟเข้า session_state เพื่อใช้งานข้ามแท็บ
            current_breed_data = next(
                (b for b in filtered_breeds if b["breed_name"] == selected_b_name),
                {"id": 1, "default_feed": 114.0, "egg_color": "ไม่ระบุ"},
            )
            selected_breed_id = current_breed_data.get("id", 1)
            st.session_state["current_breed_default_feed"] = float(current_breed_data.get("default_feed", 114.0))

        with col_br3:
            # ดึงตัวเลือกระยะการเลี้ยงจากตารางมาตรฐานโภชนาการ เพื่อให้ภาษา/ชื่อช่วงตรงกับ Database
            phase_options = fetch_nutrition_standard_phase_options(selected_breed_id)
            selected_stage_label = st.selectbox(
                "📋 เลือกช่วงระยะการให้ไข่:",
                phase_options,
                format_func=lambda item: item["phase_name"],
            )
            selected_stage_key = selected_stage_label["phase_key"]
            selected_stage_label = selected_stage_label["phase_name"]
            st.session_state["selected_stage_key"] = selected_stage_key
            st.session_state["selected_stage_label"] = selected_stage_label
            phase_query_name = selected_stage_key

        # --- [แก้ไขแล้ว] เรียกใช้งานฟังก์ชันดึงค่าเกณฑ์โภชนาการจาก Supabase แบบ Real-time ---
        nutrient_targets = fetch_nutrition_standards(selected_breed_id, selected_stage_label, selected_stage_key)

        if nutrient_targets:
            # ตรวจสอบและตั้งค่า Default ลงใน session_state หากยังไม่มีข้อมูล
            target_context = f"{selected_breed_id}:{selected_stage_key}"
            if st.session_state.get("nutrition_target_context") != target_context:
                st.session_state["nutrition_target_context"] = target_context
                st.session_state["base_req_protein"] = nutrient_targets["min_protein"]
                st.session_state["base_req_me"] = nutrient_targets["min_me"]
                st.session_state["base_req_calcium"] = nutrient_targets["min_calcium"]
                st.session_state["base_req_phos"] = nutrient_targets["min_phosphorus"]

            # สร้างฟอร์มให้ผู้ใช้สามารถปรับแต่งค่าเป้าหมายได้เองโดยอิงค่าเริ่มต้นจาก Supabase
            col_inp1, col_inp2, col_inp3, col_inp4 = st.columns(4)
            with col_inp1:
                edit_p = st.number_input("🎯 โปรตีนเป้าหมาย (%):", min_value=5.0, value=float(st.session_state["base_req_protein"]), step=0.1)
            with col_inp2:
                edit_m = st.number_input("🎯 พลังงานเป้าหมาย (kcal/kg):", min_value=1000.0, value=float(st.session_state["base_req_me"]), step=25.0)
            with col_inp3:
                edit_c = st.number_input("🎯 แคลเซียมเป้าหมาย (%):", min_value=0.5, value=float(st.session_state["base_req_calcium"]), step=0.05)
            with col_inp4:
                edit_ph = st.number_input("🎯 ฟอสฟอรัสเป้าหมาย (%):", min_value=0.1, value=float(st.session_state["base_req_phos"]), step=0.02)

            custom_targets = nutrient_targets.copy()
            custom_targets["min_protein"] = edit_p
            custom_targets["min_me"] = edit_m
            custom_targets["min_calcium"] = edit_c
            custom_targets["min_phosphorus"] = edit_ph

            auto_formula_context = (
                f"{selected_breed_id}:{selected_stage_key}:"
                f"{edit_p:.2f}:{edit_m:.0f}:{edit_c:.2f}:{edit_ph:.2f}"
            )
            if (
                st.session_state.get("auto_formula_context") != auto_formula_context
                or not st.session_state.current_weights
            ):
                with st.spinner("AI กำลังจัดสูตร..."):
                    st.session_state.current_weights = run_ai_solver(custom_targets)
                    st.session_state["auto_formula_context"] = auto_formula_context
        else:
            st.error(f"❌ ไม่พบเกณฑ์มาตรฐานโภชนาการสำหรับสายพันธุ์ {selected_b_name} ระยะ {selected_stage_label} ({selected_stage_key}) บนฐานข้อมูล")
        st.markdown("</div>", unsafe_allow_html=True)

        # --- ส่วนที่ 3: แถบปรับสัดส่วนอาหาร และตารางผลลัพธ์ด้านล่าง ---
        col_left = st.container()
        col_right = st.container()

        # คำนวณต้นทุนล่วงหน้าเพื่อให้กล่องด้านซ้าย/ขวาสามารถเข้าถึงตัวแปร net_cost ได้อย่างถูกต้อง
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
        st.session_state["current_net_cost"] = round(net_cost, 2)

        with col_left:
            st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
            cl_title, cl_reset = st.columns([6, 4])
            with cl_title:
                st.markdown("<div class='section-title'><h3>3. ปรับสัดส่วนวัตถุดิบ</h3></div>", unsafe_allow_html=True)
            with cl_reset:
                if st.button("🔄 รีเซ็ตค่าใหม่ทั้งหมด", use_container_width=True) and nutrient_targets:
                    st.session_state.current_weights = run_ai_solver(nutrient_targets)
                    st.rerun()

            current_total_pct = sum(float(value or 0.0) for value in st.session_state.current_weights.values())
            st.markdown(
                """
                <div class="status-panel">
                    <b>วิธีปรับสูตร</b><br>
                    <span style="color:#cbd5e1;">
                    ลากแถบของวัตถุดิบแต่ละตัวเพื่อเพิ่มหรือลดเปอร์เซ็นต์ ส่วนผสมรวมต้องเท่ากับ 100% ก่อนนำสูตรไปใช้จริง
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if abs(current_total_pct - 100.0) > 0.1:
                st.markdown(
                    f"<div style='background-color:#991b1b; padding:15px; border-radius:8px; font-size:18px; font-weight:bold; text-align:center; margin-bottom:16px;'>⚠️ สัดส่วนอาหารรวมได้: {current_total_pct:.1f}% (กรุณาลากแถบให้ครบ 100%)</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div style='background-color:#065f46; padding:15px; border-radius:8px; font-size:18px; font-weight:bold; text-align:center; margin-bottom:16px;'>ส่วนผสมครบถ้วน 100% พร้อมตรวจผลโภชนาการ</div>",
                    unsafe_allow_html=True,
                )

            temp_weights = {}
            running_total = 0.0
            inclusion_limits = {
                "กากเบียร์แห้ง": 10.0,
                "กากน้ำตาล": 5.0,
                "น้ำมันปาล์ม": 4.0,
                "น้ำมันถั่วเหลือง": 4.0,
                "ข้าวนก": 15.0,
                "กากดีดีจีเอส": 15.0,
                "DDGS": 15.0,
            }

            # ปรับแบ่งตัว Slider วัตถุดิบเป็นคอลัมน์ละไม่เกิน 10 รายการ
            ing_keys = list(st.session_state.db_ingredients.keys())
            ingredient_columns = st.columns(max(1, min(4, (len(ing_keys) + 9) // 10)))

            for idx, name in enumerate(ing_keys):
                d = st.session_state.db_ingredients[name]
                saved_w = float(st.session_state.current_weights.get(name, 0.0))
                saved_w = max(0.0, min(100.0, saved_w))

                target_col = ingredient_columns[min(idx // 10, len(ingredient_columns) - 1)]
                with target_col:
                    user_val = st.slider(
                        f"🌽 {name} ({d['price']} บ.)",
                        min_value=0.0,
                        max_value=100.0,
                        value=saved_w,
                        step=0.1,
                        key=f"sld_user_{name}",
                    )
                    if name in inclusion_limits and user_val > inclusion_limits[name]:
                        st.markdown(
                            f"<p style='color:#f87171; font-size:14px; font-weight:bold; margin:-8px 0px 10px 0px;'>⚠️ ห้ามเกิน {inclusion_limits[name]}% ไก่จะท้องเสีย</p>",
                            unsafe_allow_html=True,
                        )

                temp_weights[name] = user_val
                running_total += user_val

            st.session_state.current_weights = temp_weights

            net_cost = 0.0
            act_nut = {"protein": 0.0, "me": 0.0, "calcium": 0.0, "phos": 0.0}
            adjusted_total_w = sum(st.session_state.current_weights.values())
            adjusted_divisor = adjusted_total_w if adjusted_total_w > 0 else 1.0
            for name, w in st.session_state.current_weights.items():
                if name in st.session_state.db_ingredients:
                    ratio = w / adjusted_divisor
                    net_cost += ratio * float(st.session_state.db_ingredients[name].get("price", 0.0))
                    for k in act_nut.keys():
                        act_nut[k] += ratio * float(st.session_state.db_ingredients[name].get(k, 0.0))
            st.session_state["current_net_cost"] = round(net_cost, 2)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_right:
            st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'><h3>4. ตรวจผลโภชนาการและบันทึกสูตร</h3></div>", unsafe_allow_html=True)

            # แสดงเปรียบเทียบค่าเป้าหมายที่ดึงมาจากชุดข้อมูล Supabase จริง
            target_p_val = edit_p if nutrient_targets else 16.5
            target_m_val = edit_m if nutrient_targets else 2750
            target_c_val = edit_c if nutrient_targets else 3.80
            target_ph_val = edit_ph if nutrient_targets else 0.45
            max_c_val = float(nutrient_targets.get("max_calcium", 99.0)) if nutrient_targets else 99.0

            nutrition_alerts = []

            def nutrition_status(actual, minimum, unit="", maximum=None):
                if actual < minimum:
                    nutrition_alerts.append(f"{unit}ต่ำกว่าเป้าหมาย")
                    return "⚠️ ต่ำ"
                if maximum is not None and actual > maximum:
                    nutrition_alerts.append(f"{unit}สูงเกินเป้าหมาย")
                    return "⚠️ สูง"
                return "✅ ผ่าน"

            comparison_table = [
                {
                    "โภชนาการสำคัญ": "โปรตีนดิบ (% CP)",
                    "เป้าหมาย": f"{target_p_val:.2f} %",
                    "ได้จริงในสูตร": f"{act_nut['protein']:.2f} %",
                    "สถานะ": nutrition_status(act_nut["protein"], target_p_val, "โปรตีน"),
                },
                {
                    "โภชนาการสำคัญ": "พลังงานใช้ประโยชน์ (ME)",
                    "เป้าหมาย": f"{target_m_val:.0f}",
                    "ได้จริงในสูตร": f"{act_nut['me']:.0f}",
                    "สถานะ": nutrition_status(act_nut["me"], target_m_val, "พลังงาน"),
                },
                {
                    "โภชนาการสำคัญ": "แคลเซียม (% Ca)",
                    "เป้าหมาย": f"{target_c_val:.2f} %",
                    "ได้จริงในสูตร": f"{act_nut['calcium']:.2f} %",
                    "สถานะ": nutrition_status(act_nut["calcium"], target_c_val, "แคลเซียม", max_c_val),
                },
                {
                    "โภชนาการสำคัญ": "ฟอสฟอรัส (% P)",
                    "เป้าหมาย": f"{target_ph_val:.2f} %",
                    "ได้จริงในสูตร": f"{act_nut['phos']:.2f} %",
                    "สถานะ": nutrition_status(act_nut["phos"], target_ph_val, "ฟอสฟอรัส"),
                },
            ]
            render_readable_table(pd.DataFrame(comparison_table))
            if nutrition_alerts:
                st.warning("สูตรนี้ยังไม่ผ่านเกณฑ์: " + ", ".join(nutrition_alerts))
            else:
                st.success("สูตรนี้ผ่านเกณฑ์โภชนาการหลักแล้ว")

            st.markdown(
                f"<div style='background-color:#1e293b; padding:15px; border-radius:10px; border:2px solid #38bdf8; text-align:center; font-size:24px; font-weight:bold; margin: 15px 0;'>💰 ต้นทุนค่าอาหารสูตรนี้: {net_cost:.2f} บาท/กก.</div>",
                unsafe_allow_html=True,
            )

            breed_display_name = (
                selected_b_name.split()[-1]
                if len(selected_b_name.split()) > 1
                else selected_b_name
            )
            save_name_input = st.text_input(
                "💾 ตั้งชื่อเล่นสูตรอาหารเพื่อกดเซฟ:",
                value=f"สูตร {breed_display_name} {net_cost:.1f} บาท",
            )
            if st.button("📥 ยืนยันกดบันทึกสูตรอาหารลงคลัง", use_container_width=True):
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
    if selected_user_page == "daily":
        selected_b_name = st.session_state.get("selected_b_name", "สายพันธุ์ที่เลือก")
        selected_stage_label = st.session_state.get("selected_stage_label", "ช่วงอายุที่เลือก")
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown(
            "<h2>บันทึกตัวชี้วัดฟาร์มและผลประกอบการประจำวัน</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='border-bottom: 2px solid #475569; margin:15px 0;'></div>",
            unsafe_allow_html=True,
        )

        log_col1, log_col2 = st.columns(2)
        with log_col1:
            st.markdown("<div class='section-title'><h3>1. ข้อมูลฝูงวันนี้</h3></div>", unsafe_allow_html=True)
            log_date = st.date_input(
                "วันที่บันทึกข้อมูล:", datetime.date.today(), key="farm_log_date"
            )
            flock_age_weeks = st.number_input(
                "🐣 อายุฝูงไก่ปัจจุบัน (สัปดาห์):", min_value=1, max_value=100, value=25, step=1
            )

            default_birds = st.session_state.get("shortcut_birds", 1000)
            bird_count = st.number_input(
                "จำนวนไก่ไข่ทั้งหมดในเล้าวันนี้ (ตัว):",
                min_value=1,
                value=int(default_birds),
                step=100,
            )
            env_temp = st.slider(
                "🌡️ อุณหภูมิสูงสุดในเล้าวันนี้ (°C):",
                15.0,
                45.0,
                28.0,
                step=0.5,
                key="temp_slider",
            )

            # ดึงค่าแนะนำปริมาณอาหารจริงแบบ Dynamic จากรายสายพันธุ์ที่เลือกไว้ในตาราง Supabase
            breed_default_feed = st.session_state.get("current_breed_default_feed", 114.0)
            recommended_feed = float(bird_count * breed_default_feed / 1000.0)
            feed_input_value = max(10.0, recommended_feed)
            st.markdown(
                f"<p style='color:#6366f1; font-size:16px; font-weight:bold; margin-bottom:-5px;'>💡 ปริมาณอาหารแนะนำตามสายพันธุ์ {selected_b_name}: {recommended_feed:,.1f} กก. ({breed_default_feed} กรัม/ตัว/วัน)</p>",
                unsafe_allow_html=True,
            )
            actual_feed_given_kg = st.number_input(
                "🍽️ น้ำหนักอาหารที่ให้ไก่กินรวมวันนี้ (กิโลกรัม):",
                min_value=10.0,
                value=feed_input_value,
                step=10.0,
            )

        with log_col2:
            st.markdown("<div class='section-title'><h3>2. ผลผลิตและราคาไข่</h3></div>", unsafe_allow_html=True)
            collected_eggs = st.number_input(
                "จำนวนฟองไข่ที่เก็บได้จริงวันนี้ (ฟอง):", min_value=0, value=850
            )

            default_price = float(st.session_state.get("shortcut_price", 4.10) or 4.10)
            default_price = max(1.0, default_price)
            egg_sale_price = st.number_input(
                "💵 ราคารับซื้อไข่หน้าฟาร์มวันนี้ (บาท/ฟอง):",
                min_value=1.0,
                value=default_price,
                step=0.1,
            )
            dead_birds = st.number_input(
                "จำนวนไก่ตาย/คัดทิ้งวันนี้ (ตัว):", min_value=0, value=1
            )
            avg_egg_weight_g = st.number_input(
                "⚖️ น้ำหนักไข่เฉลี่ยวันนี้ (กรัม/ฟอง):",
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

        # 📋 ระบบปฏิทินเตือนความจำวัคซีนและงานรูทีนตามช่วงอายุไก่
        st.markdown(
            "<div style='background-color:#1e1b4b; padding:20px; border-radius:12px; border:2px solid #6366f1; margin: 20px 0;'>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"### 📋 ปฏิทินเตือนงานสำคัญสำหรับไก่อายุ {flock_age_weeks} สัปดาห์:"
        )
        if flock_age_weeks <= 3:
            st.markdown("<p style='color:#38bdf8; font-size:22px; font-weight:bold;'>• ต้องทำวัคซีนนิวคาสเซิล + หลอดลมอักเสบ และตรวจเช็กระบบไฟกก</p>", unsafe_allow_html=True)
        elif flock_age_weeks <= 8:
            st.markdown("<p style='color:#38bdf8; font-size:22px; font-weight:bold;'>• ต้องทำวัคซีนฝีดาษ และทำวัคซีนอหิวาต์ไก่รอบที่ 1</p>", unsafe_allow_html=True)
        elif flock_age_weeks <= 16:
            st.markdown("<p style='color:#38bdf8; font-size:22px; font-weight:bold;'>• ต้องถ่ายพยาธิไก่ก่อนย้ายเข้ากรงตับ และทำวัคซีนรวมก่อนเริ่มไข่</p>", unsafe_allow_html=True)
        elif flock_age_weeks <= 24:
            st.markdown("<p style='color:#fbbf24; font-size:22px; font-weight:bold;'>• ไก่เริ่มไข่แล้ว: [ระวัง] ห้ามลดแสงสว่างในเล้าเด็ดขาด! แวนแสงต้องสม่ำเสมอ</p>", unsafe_allow_html=True)
        elif flock_age_weeks <= 60:
            st.markdown("<p style='color:#10b981; font-size:22px; font-weight:bold;'>• ช่วงไข่ดก: สุ่มเช็กความหนาเปลือกไข่ และล้างทำความสะอาดหัวนิปเปิ้ลน้ำทุกสัปดาห์</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p style='color:#f87171; font-size:22px; font-weight:bold;'>• ไก่แก่ท้ายชุด: ให้คนงานเสริมเปลือกหอยบดในรางช่วงเย็น ป้องกันไข่เปลือกบางแตกหัก</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            "<div style='border-bottom: 2px dashed #475569; margin:20px 0;'></div>",
            unsafe_allow_html=True,
        )

        # 💰 เมทริกซ์คำนวณต้นทุนการเงินหน้าฟาร์มสุทธิ
        net_cost = float(st.session_state.get("current_net_cost", 0.0) or 0.0)
        if net_cost <= 0:
            net_cost = calculate_current_feed_cost()
            st.session_state["current_net_cost"] = net_cost
        if net_cost <= 0:
            st.warning("ยังไม่มีต้นทุนสูตรอาหาร กรุณาไปหน้า 'คำนวณสูตรอาหาร' แล้วคำนวณหรือดึงสูตรที่บันทึกไว้ก่อน")

        total_revenue = collected_eggs * egg_sale_price
        total_feed_cost = actual_feed_given_kg * net_cost
        net_profit_day = total_revenue - total_feed_cost

        henday_pct = (collected_eggs / bird_count) * 100.0 if bird_count > 0 else 0.0
        total_egg_mass_kg = (collected_eggs * avg_egg_weight_g) / 1000.0
        fcr_ratio = (
            actual_feed_given_kg / total_egg_mass_kg if total_egg_mass_kg > 0 else 0.0
        )
        cost_per_egg = total_feed_cost / collected_eggs if collected_eggs > 0 else 0.0

        # 🚨 SAFETY GUARDRAILS: ตรวจจับสัญญาณอันตรายหน้าฟาร์มอัตโนมัติ
        if henday_pct < 65.0 and henday_pct > 0:
            st.markdown(
                f"<div style='background-color:#7c2d12; padding:15px; border-radius:8px; font-size:18px; font-weight:bold; margin-bottom:15px;'>⚠️ เตือน: เปอร์เซ็นต์การไข่ต่ำกว่าเกณฑ์มาตรฐาน ({henday_pct:.1f}%) ตรวจเช็กพฤติกรรมการกินและสุ่มคัดไก่ป่วยด่วน</div>",
                unsafe_allow_html=True,
            )
        if dead_birds > (bird_count * 0.001):
            st.markdown(
                f"<div style='background-color:#991b1b; padding:15px; border-radius:8px; font-size:18px; font-weight:bold; margin-bottom:15px;'>🚨 วิกฤต: วันนี้ไก่ตายผิดปกติ ({dead_birds} ตัว) สูงเกินเกณฑ์ ระวังสภาพอากาศร้อนจัดหรือโรคระบาดติดต่อ!</div>",
                unsafe_allow_html=True,
            )
        if env_temp >= 32.0:
            st.error(
                f"🚨 เล้าร้อนจัด ({env_temp}°C) ไก่เสี่ยงช็อกตาย! คนงานต้องเปิดระบบพ่นหมอกและเร่งพัดลมทันที (ปริมาณน้ำที่ฝูงไก่ต้องกินขั้นต่ำ: {total_water_needed_liters:,.1f} ลิตร)"
            )

        st.markdown("<div class='section-title'><h3>3. สรุปผลวันนี้</h3></div>", unsafe_allow_html=True)
        profit_box_color = "#065f46" if net_profit_day >= 0 else "#991b1b"
        st.markdown(
            f"<div style='background-color:{profit_box_color}; padding:20px; border-radius:12px; text-align:center; font-size:26px; font-weight:bold; margin-bottom:20px;'>💸 เงินกำไรสุทธิประจำวัน (หักค่าอาหารแล้ว): {net_profit_day:,.2f} บาท</div>",
            unsafe_allow_html=True,
        )

        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.markdown(
                f"<div style='background-color:#0f172a; padding:15px; border-radius:10px; border:1px solid #334155; text-align:center;'><span class='big-metric-label'>🥚 เปอร์เซ็นต์การไข่</span><br><span class='big-metric-value'>{henday_pct:.1f} %</span></div>",
                unsafe_allow_html=True,
            )
        with m_col2:
            st.markdown(
                f"<div style='background-color:#0f172a; padding:15px; border-radius:10px; border:1px solid #334155; text-align:center;'><span class='big-metric-label'>🥣 อัตราแลกไข่ (FCR)</span><br><span class='big-metric-value'>{fcr_ratio:.2f}</span></div>",
                unsafe_allow_html=True,
            )
        with m_col3:
            st.markdown(
                f"<div style='background-color:#0f172a; padding:15px; border-radius:10px; border:1px solid #334155; text-align:center;'><span class='big-metric-label'>🥚 ค่าอาหารต่อไข่ 1 ฟอง</span><br><span class='big-metric-value'>{cost_per_egg:.2f} บาท</span></div>",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)

        if st.button("💾 กดปุ่มนี้เพื่อบันทึกประวัติประจำวัน", use_container_width=True):
            log_data = {
                "date": str(log_date),
                "flock_age_weeks": int(flock_age_weeks),
                "bird_count": int(bird_count),
                "env_temp": float(env_temp),
                "actual_feed_given_kg": round(float(actual_feed_given_kg), 2),
                "collected_eggs": int(collected_eggs),
                "egg_sale_price": round(float(egg_sale_price), 2),
                "dead_birds": int(dead_birds),
                "avg_egg_weight_g": round(float(avg_egg_weight_g), 2),
                "total_revenue": round(float(total_revenue), 2),
                "total_feed_cost": round(float(total_feed_cost), 2),
                "net_profit_day": round(float(net_profit_day), 2),
                "henday_pct": round(float(henday_pct), 1),
                "fcr_ratio": round(float(fcr_ratio), 2),
            }
            if save_daily_log_to_supabase(log_data):
                st.rerun()

        st.markdown(
            "<div style='border-bottom: 2px dashed #475569; margin:25px 0;'></div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div class='section-title'><h3>4. ประวัติฟาร์มย้อนหลัง</h3></div>", unsafe_allow_html=True)
        if not st.session_state.daily_logs:
            st.info("💡 ยังไม่มีข้อมูลย้อนหลัง")
        else:
            latest_logs = sort_daily_logs_latest_first(st.session_state.daily_logs)
            filtered_logs = latest_logs
            analysis_df = build_daily_logs_analysis(latest_logs)
            latest_log = latest_logs[0] if latest_logs else None
            if latest_log is not None:
                kpi1, kpi2, kpi3 = st.columns(3)
                with kpi1:
                    st.metric("ไข่ล่าสุด", f"{int(latest_log.get('collected_eggs') or 0):,} ฟอง")
                with kpi2:
                    st.metric("รายได้ล่าสุด", f"{float(latest_log.get('total_revenue') or 0):,.2f} บาท")
                with kpi3:
                    st.metric("กำไรสุทธิล่าสุด", f"{float(latest_log.get('net_profit_day') or 0):,.2f} บาท")

            st.markdown("#### วิเคราะห์ตามช่วงวันที่")
            date_values = analysis_df["date"].dropna()
            min_log_date = date_values.min().date() if not date_values.empty else datetime.date.today()
            max_log_date = date_values.max().date() if not date_values.empty else datetime.date.today()
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                history_start = st.date_input("ตั้งแต่วันที่", value=min_log_date, key="history_start_date")
            with filter_col2:
                history_end = st.date_input("ถึงวันที่", value=max_log_date, key="history_end_date")

            filtered_df = analysis_df[
                (analysis_df["date"].dt.date >= history_start)
                & (analysis_df["date"].dt.date <= history_end)
            ].copy()

            if filtered_df.empty:
                st.warning("ไม่พบข้อมูลในช่วงวันที่ที่เลือก")
                display_logs_df = pd.DataFrame()
            else:
                daily_summary = (
                    filtered_df.assign(day=filtered_df["date"].dt.date)
                    .groupby("day", as_index=False)
                    .agg({
                        "collected_eggs": "sum",
                        "total_revenue": "sum",
                        "net_profit_day": "sum",
                        "henday_pct": "mean",
                        "fcr_ratio": "mean",
                    })
                    .sort_values("day")
                )
                daily_summary["day_label"] = pd.to_datetime(daily_summary["day"]).dt.strftime("%d/%m")

                summary_cards = [
                    ("จำนวนวัน", f"{len(daily_summary):,}", "วัน"),
                    ("ไข่รวม", f"{daily_summary['collected_eggs'].sum():,.0f}", "ฟอง"),
                    ("รายได้รวม", f"{daily_summary['total_revenue'].sum():,.0f}", "บาท"),
                    ("กำไรรวม", f"{daily_summary['net_profit_day'].sum():,.0f}", "บาท"),
                    ("Hen-day เฉลี่ย", f"{daily_summary['henday_pct'].mean():,.1f}", "%"),
                ]
                summary_cols = st.columns(5)
                for idx, (label, value, unit) in enumerate(summary_cards):
                    with summary_cols[idx]:
                        st.markdown(
                            f"""
                            <div class="ops-kpi" style="min-height:104px; padding:14px;">
                                <p class="label">{label}</p>
                                <p class="value" style="font-size:1.55rem;">{value}</p>
                                <p class="note">{unit}</p>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

                history_fig = go.Figure()
                history_fig.add_trace(go.Scatter(
                    x=daily_summary["day_label"],
                    y=daily_summary["collected_eggs"],
                    mode="lines+markers",
                    name="ไข่รวม (ฟอง)",
                    line=dict(color="#38bdf8", width=3),
                    marker=dict(size=9),
                    hovertemplate="วันที่ %{x}<br>ไข่ %{y:,.0f} ฟอง<extra></extra>",
                ))
                history_fig.add_trace(go.Scatter(
                    x=daily_summary["day_label"],
                    y=daily_summary["net_profit_day"],
                    mode="lines+markers",
                    name="กำไรสุทธิ (บาท)",
                    line=dict(color="#22c55e", width=3),
                    marker=dict(size=9),
                    yaxis="y2",
                    hovertemplate="วันที่ %{x}<br>กำไร %{y:,.0f} บาท<extra></extra>",
                ))
                history_fig.update_layout(
                    height=340,
                    margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(15,23,42,0.35)",
                    font=dict(color="#e2e8f0"),
                    legend=dict(orientation="h", y=1.10),
                    hovermode="x unified",
                    xaxis=dict(title="วันที่", type="category", gridcolor="rgba(148,163,184,0.12)"),
                    yaxis=dict(title="ไข่ (ฟอง)", gridcolor="rgba(148,163,184,0.18)", rangemode="tozero"),
                    yaxis2=dict(title="กำไร (บาท)", overlaying="y", side="right", showgrid=False, zeroline=True, zerolinecolor="rgba(248,250,252,0.35)"),
                )
                st.plotly_chart(history_fig, use_container_width=True)

                health_fig = go.Figure()
                health_fig.add_trace(go.Scatter(
                    x=daily_summary["day_label"],
                    y=daily_summary["henday_pct"],
                    mode="lines+markers",
                    name="Hen-day (%)",
                    line=dict(color="#fbbf24", width=3),
                    marker=dict(size=8),
                ))
                health_fig.add_trace(go.Scatter(
                    x=daily_summary["day_label"],
                    y=daily_summary["fcr_ratio"],
                    mode="lines+markers",
                    name="FCR",
                    line=dict(color="#f97316", width=3),
                    marker=dict(size=8),
                    yaxis="y2",
                ))
                health_fig.update_layout(
                    height=240,
                    margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(15,23,42,0.35)",
                    font=dict(color="#e2e8f0"),
                    legend=dict(orientation="h", y=1.18),
                    hovermode="x unified",
                    xaxis=dict(title="วันที่", type="category", gridcolor="rgba(148,163,184,0.12)"),
                    yaxis=dict(title="Hen-day (%)", gridcolor="rgba(148,163,184,0.18)", rangemode="tozero"),
                    yaxis2=dict(title="FCR", overlaying="y", side="right", showgrid=False, rangemode="tozero"),
                )
                st.plotly_chart(health_fig, use_container_width=True)

                st.markdown("#### เปรียบเทียบวันต่อวัน")
                compare_options = {
                    f"#{row.get('id', idx)} | {row['date'].date()} | ไข่ {int(row['collected_eggs']):,} ฟอง | กำไร {row['net_profit_day']:,.0f} บาท": idx
                    for idx, row in filtered_df.sort_values("date", ascending=False).iterrows()
                }
                if len(compare_options) >= 2:
                    compare_col1, compare_col2 = st.columns(2)
                    option_labels = list(compare_options.keys())
                    with compare_col1:
                        compare_left_label = st.selectbox("เลือกวันแรก", option_labels, index=min(1, len(option_labels) - 1), key="compare_left_day")
                    with compare_col2:
                        compare_right_label = st.selectbox("เลือกวันเทียบ", option_labels, index=0, key="compare_right_day")

                    left_row = filtered_df.loc[compare_options[compare_left_label]]
                    right_row = filtered_df.loc[compare_options[compare_right_label]]
                    cmp_cols = st.columns(4)
                    with cmp_cols[0]:
                        render_comparison_metric("ไข่ที่เก็บได้", left_row["collected_eggs"], right_row["collected_eggs"], " ฟอง", 0)
                    with cmp_cols[1]:
                        render_comparison_metric("กำไรสุทธิ", left_row["net_profit_day"], right_row["net_profit_day"], " บาท", 2)
                    with cmp_cols[2]:
                        render_comparison_metric("Hen-day", left_row["henday_pct"], right_row["henday_pct"], "%", 1)
                    with cmp_cols[3]:
                        render_comparison_metric("FCR", left_row["fcr_ratio"], right_row["fcr_ratio"], "", 2, lower_is_better=True)
                else:
                    st.info("ต้องมีข้อมูลอย่างน้อย 2 วัน จึงจะเปรียบเทียบวันต่อวันได้")

                filtered_logs = filtered_df.sort_values("date", ascending=False).to_dict("records")
                display_logs_df = build_daily_logs_display(filtered_logs)
            render_readable_table(
                display_logs_df,
                column_config={
                    "รายได้": st.column_config.NumberColumn(format="%.2f บาท"),
                    "ต้นทุนอาหาร": st.column_config.NumberColumn(format="%.2f บาท"),
                    "กำไรสุทธิ": st.column_config.NumberColumn(format="%.2f บาท"),
                    "ราคาไข่/ฟอง": st.column_config.NumberColumn(format="%.2f บาท"),
                    "อัตราไข่ (%)": st.column_config.NumberColumn(format="%.1f %%"),
                    "FCR": st.column_config.NumberColumn(format="%.2f"),
                },
            )
            st.markdown("#### แก้ไขหรือลบประวัติย้อนหลัง")
            log_options = {
                f"#{item.get('id', '-')}: {item.get('date', '-')} | ไก่ {int(item.get('bird_count') or 0):,} ตัว | ไข่ {int(item.get('collected_eggs') or 0):,} ฟอง": item
                for item in filtered_logs
            }
            selected_log_label = st.selectbox("เลือกรายการที่ต้องการจัดการ:", list(log_options.keys()))
            selected_log = log_options[selected_log_label]
            selected_log_id = selected_log.get("id")

            try:
                selected_date = datetime.date.fromisoformat(str(selected_log.get("date")))
            except Exception:
                selected_date = datetime.date.today()

            with st.form(key=f"edit_daily_log_{selected_log_id}"):
                edit_col1, edit_col2, edit_col3 = st.columns(3)
                with edit_col1:
                    edit_date = st.date_input("วันที่", value=selected_date)
                    edit_age = st.number_input("อายุฝูง (สัปดาห์)", min_value=1, max_value=120, value=int(selected_log.get("flock_age_weeks") or 25), step=1)
                    edit_birds = st.number_input("จำนวนไก่ (ตัว)", min_value=1, value=int(selected_log.get("bird_count") or 1), step=50)
                with edit_col2:
                    edit_temp = st.number_input("อุณหภูมิ (°C)", min_value=0.0, max_value=60.0, value=float(selected_log.get("env_temp") or 28.0), step=0.5)
                    edit_feed = st.number_input("อาหารที่ให้ (กก.)", min_value=0.0, value=float(selected_log.get("actual_feed_given_kg") or 0.0), step=1.0)
                    edit_eggs = st.number_input("ไข่ที่เก็บได้ (ฟอง)", min_value=0, value=int(selected_log.get("collected_eggs") or 0), step=10)
                with edit_col3:
                    edit_price = st.number_input("ราคาไข่/ฟอง (บาท)", min_value=0.0, value=float(selected_log.get("egg_sale_price") or 0.0), step=0.1)
                    edit_dead = st.number_input("ไก่ตาย/คัดทิ้ง (ตัว)", min_value=0, value=int(selected_log.get("dead_birds") or 0), step=1)
                    edit_egg_weight = st.number_input("น้ำหนักไข่เฉลี่ย (กรัม)", min_value=0.0, value=float(selected_log.get("avg_egg_weight_g") or 62.0), step=0.5)

                edit_net_cost = float(st.session_state.get("current_net_cost", 0.0) or 0.0)
                edit_total_revenue = float(edit_eggs) * float(edit_price)
                edit_total_feed_cost = float(edit_feed) * edit_net_cost
                edit_net_profit = edit_total_revenue - edit_total_feed_cost
                edit_henday = (float(edit_eggs) / float(edit_birds)) * 100.0 if edit_birds > 0 else 0.0
                edit_egg_mass_kg = (float(edit_eggs) * float(edit_egg_weight)) / 1000.0
                edit_fcr = float(edit_feed) / edit_egg_mass_kg if edit_egg_mass_kg > 0 else 0.0

                st.caption(f"ระบบจะคำนวณใหม่ให้: รายได้ {edit_total_revenue:,.2f} บาท | ต้นทุนอาหาร {edit_total_feed_cost:,.2f} บาท | กำไร {edit_net_profit:,.2f} บาท")
                save_edit = st.form_submit_button("บันทึกการแก้ไขรายการนี้", type="primary", use_container_width=True)

            if save_edit:
                updated_log = {
                    "date": str(edit_date),
                    "flock_age_weeks": int(edit_age),
                    "bird_count": int(edit_birds),
                    "env_temp": round(float(edit_temp), 2),
                    "actual_feed_given_kg": round(float(edit_feed), 2),
                    "collected_eggs": int(edit_eggs),
                    "egg_sale_price": round(float(edit_price), 2),
                    "dead_birds": int(edit_dead),
                    "avg_egg_weight_g": round(float(edit_egg_weight), 2),
                    "total_revenue": round(float(edit_total_revenue), 2),
                    "total_feed_cost": round(float(edit_total_feed_cost), 2),
                    "net_profit_day": round(float(edit_net_profit), 2),
                    "henday_pct": round(float(edit_henday), 1),
                    "fcr_ratio": round(float(edit_fcr), 2),
                }
                if update_daily_log_in_supabase(selected_log_id, updated_log):
                    st.rerun()

            delete_confirm = st.checkbox("ยืนยันว่าต้องการลบรายการที่เลือก", key=f"delete_daily_log_confirm_{selected_log_id}")
            if st.button("ลบรายการประวัตินี้", type="secondary", use_container_width=True, disabled=not delete_confirm):
                if delete_daily_log_from_supabase(selected_log_id):
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------
    # TAB 3: PROCUREMENT & WORKER SHEET
    # ------------------------------------------
    if selected_user_page == "mixing":
        selected_b_name = st.session_state.get("selected_b_name", "สูตรอาหารปัจจุบัน")
        selected_stage_label = st.session_state.get("selected_stage_label", "ยังไม่ได้เลือกช่วงอายุ")
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown(
            "<h2>📊 ใบสั่งงานผสมอาหารสัตว์ (สำหรับยื่นให้คนงานตักของ)</h2>",
            unsafe_allow_html=True,
        )
        total_tonnage = st.number_input(
            "📦 ใส่จำนวนกิโลกรัมอาหารรวมที่ต้องการจะผสมในรอบนี้ (KG):",
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
                        f"🟢 ยก {bags} กระสอบ + ⚖️ ตักเศษ {rem_kg:.1f} กก."
                        if bags > 0
                        else f"⚖️ ตักเศษสุทธิ {rem_kg:.1f} กิโลกรัม"
                    )

                    po_buffer.append(
                        {
                            "รายการวัตถุดิบ": ing_name,
                            "สัดส่วนผสม (%)": round(actual_pct, 1),
                            "น้ำหนักรวมที่ต้องใช้ (KG)": round(weight_kg, 1),
                            "📢 วิธีตักหน้างาน (กระสอบละ 50kg)": bag_txt,
                            "ราคาทุน (บาท)": round(cost_item, 0),
                        }
                    )

        if po_buffer:
            df_po = pd.DataFrame(po_buffer)
            render_readable_table(
                df_po,
                column_config={
                    "สัดส่วนผสม (%)": st.column_config.NumberColumn(format="%.1f %%"),
                    "น้ำหนักรวมที่ต้องใช้ (KG)": st.column_config.NumberColumn(format="%.1f กก."),
                    "ราคาทุน (บาท)": st.column_config.NumberColumn(format="%.0f บาท"),
                },
            )

            st.markdown(
                f"<div style='background-color:#1e293b; padding:15px; border-radius:10px; border:2px dashed #10b981; font-size:24px; font-weight:bold; text-align:center; margin:15px 0;'>💵 งบประมาณค่าวัตถุดิบรวมรอบนี้: {total_po_cost:,.2f} บาท</div>",
                unsafe_allow_html=True,
            )

            # --- ฟีเจอร์: ปุ่มด่วนสำหรับก๊อปปี้ข้อความภาษาไทยส่งเข้ากลุ่ม LINE ---
            line_text = f"📋 *ใบสั่งผสมอาหารสัตว์รวม: {total_tonnage:,} กก.*\n"
            line_text += f"สูตรสำหรับ: {selected_b_name} ({selected_stage_label})\n"
            line_text += "--------------------------------------\n"
            for item in po_buffer:
                line_text += f"🔹 {item['รายการวัตถุดิบ']}: {item['📢 วิธีตักหน้างาน (กระสอบละ 50kg)']}\n"
            line_text += "--------------------------------------\n"
            line_text += f"💰 งบประมาณรวมรอบนี้: {total_po_cost:,.0f} บาท"

            st.markdown("### 📱 ข้อความด่วนสำหรับก๊อปปี้ส่ง LINE (คนงานเปิดอ่านง่าย)")
            st.text_area(
                "คัดลอกข้อความนี้ไปส่ง LINE:",
                value=line_text,
                height=260,
                key="line_copy_text",
            )
            st.download_button(
                "⬇️ ดาวน์โหลดข้อความใบสั่งผสม",
                data=line_text,
                file_name=f"mixing_order_{datetime.date.today()}.txt",
                mime="text/plain",
                use_container_width=True,
            )
        else:
            st.info("ยังไม่มีสูตรอาหารสำหรับทำใบสั่งผสม กรุณาไปหน้า 'คำนวณสูตรอาหาร' แล้วคำนวณหรือดึงสูตรที่บันทึกไว้ก่อน")
        st.markdown("</div>", unsafe_allow_html=True)
