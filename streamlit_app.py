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
    page_title="ระบบคำนวณโภชนาการและจัดการสายพันธุ์ไก่ไข่ (Layer Nutrition Studio Pro)", 
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

if "db_groups" not in st.session_state:
    st.session_state.db_groups = [
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "bg_color": "#b45309"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีขาว (Commercial White Layers)", "bg_color": "#0284c7"}
    ]

if "db_breeds" not in st.session_state:
    st.session_state.db_breeds = [
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "breed_name": "สายพันธุ์ ไอซ่า บราวน์ (Isa Brown)", "egg_color": "สีน้ำตาลเข้ม", "default_feed": 114.0},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "breed_name": "สายพันธุ์ โลห์แมน บราวน์ (Lohmann Brown)", "egg_color": "สีน้ำตาลเงางาม", "default_feed": 116.0},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีขาว (Commercial White Layers)", "breed_name": "สายพันธุ์ ไฮ-ไลน์ ขาว ดับบลิว-36 (Hy-Line W-36)", "egg_color": "สีขาวสะอาดตา", "default_feed": 101.0}
    ]

if "db_targets" not in st.session_state:
    st.session_state.db_targets = {
        "layer_phase_1": {"stage_key": "layer_phase_1", "stage_name": "ระยะผลิตไข่พีค ช่วงที่ 1 อายุ 19-45 สัปดาห์", "protein": 17.5, "me": 2750.0, "calcium": 4.10, "phos": 0.42, "lysine": 0.88, "methionine": 0.42, "fiber_max": 4.5},
        "layer_phase_2": {"stage_key": "layer_phase_2", "stage_name": "ระยะกลาง ช่วงที่ 2 อายุ 46-65 สัปดาห์", "protein": 16.5, "me": 2725.0, "calcium": 4.30, "phos": 0.38, "lysine": 0.82, "methionine": 0.39, "fiber_max": 5.0}
    }

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

FALLBACK_INGREDIENTS = {
    "ข้าวโพดบด": {"name": "ข้าวโพดบด", "price": 12.5, "protein": 8.0, "me": 3370, "calcium": 0.02, "phos": 0.08, "lysine": 0.24, "methionine": 0.18, "fiber": 2.0},
    "กากถั่วเหลือง (44%)": {"name": "กากถั่วเหลือง (44%)", "price": 22.0, "protein": 44.0, "me": 2230, "calcium": 0.29, "phos": 0.20, "lysine": 2.69, "methionine": 0.62, "fiber": 6.0},
    "เปลือกหอยบด": {"name": "เปลือกหอยบด", "price": 5.0, "protein": 0.0, "me": 0, "calcium": 38.0, "phos": 0.0, "lysine": 0.0, "methionine": 0.0, "fiber": 0.0}
}

DEFAULT_INGREDIENT_OWNER = "system_default"
MASTER_TABLE_CANDIDATES = {
    "groups": ["db_groups", "breed_groups", "groups"],
    "breeds": ["db_breeds", "breeds"],
    "targets": ["db_targets", "nutrition_targets", "targets"],
    "nutrient_keys": ["db_nutrient_keys", "nutrient_keys"],
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
            st.session_state.master_load_debug.append(
                {"table_key": table_key, "table_name": table_name, "status": "empty", "rows": 0}
            )
        except Exception as table_err:
            st.session_state.master_load_debug.append(
                {"table_key": table_key, "table_name": table_name, "status": "error", "rows": 0, "error": str(table_err)}
            )
            continue
    st.session_state[f"{table_key}_table_source"] = ""
    return []

def fetch_master_data_from_supabase():
    try:
        st.session_state.master_load_debug = []
        groups = fetch_first_available_table("groups")
        if groups:
            st.session_state.db_groups = [
                {
                    "group_name": item.get("group_name") or item.get("name"),
                    "bg_color": item.get("bg_color", "#0284c7"),
                }
                for item in groups
                if item.get("group_name") or item.get("name")
            ]

        breeds = fetch_first_available_table("breeds")
        if breeds:
            st.session_state.db_breeds = [
                {
                    "group_name": item.get("group_name", ""),
                    "breed_name": item.get("breed_name") or item.get("name"),
                    "egg_color": item.get("egg_color", ""),
                    "default_feed": float(item.get("default_feed", 114.0)),
                }
                for item in breeds
                if item.get("breed_name") or item.get("name")
            ]
            breed_group_names = sorted({item["group_name"] for item in st.session_state.db_breeds if item.get("group_name")})
            current_group_names = {item.get("group_name") for item in st.session_state.db_groups}
            if breed_group_names and not current_group_names.intersection(breed_group_names):
                st.session_state.db_groups = [
                    {"group_name": group_name, "bg_color": "#0284c7"}
                    for group_name in breed_group_names
                ]

        targets = fetch_first_available_table("targets")
        if targets:
            normalized_targets = {}
            for item in targets:
                stage_key = item.get("stage_key") or item.get("key") or item.get("id")
                if stage_key:
                    normalized_item = item.copy()
                    normalized_item["stage_key"] = stage_key
                    normalized_item["stage_name"] = item.get("stage_name") or item.get("name") or str(stage_key)
                    normalized_targets[stage_key] = normalized_item
            st.session_state.db_targets = normalized_targets

        nutrient_keys = fetch_first_available_table("nutrient_keys")
        if nutrient_keys:
            st.session_state.db_nutrient_keys = {
                item.get("nutrient_key") or item.get("key") or item.get("name"): {
                    "label": item.get("label") or item.get("nutrient_label") or item.get("name"),
                    "step": float(item.get("step", 0.1)),
                    "default": float(item.get("default", 0.0)),
                }
                for item in nutrient_keys
                if item.get("nutrient_key") or item.get("key") or item.get("name")
            }
    except Exception as e:
        st.warning(f"โหลดข้อมูลตั้งต้นจากฐานข้อมูลไม่สำเร็จ กำลังใช้ข้อมูลสำรองในระบบแทน: {e}")

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
            st.session_state.db_ingredients = FALLBACK_INGREDIENTS
            return FALLBACK_INGREDIENTS
    except Exception as e:
        st.warning(f"⚠️ ดึงข้อมูลจากคลาวด์ไม่สำเร็จ (กำลังใช้ข้อมูลสำรองในระบบแทน): {e}")
        st.session_state.db_ingredients = FALLBACK_INGREDIENTS
        return FALLBACK_INGREDIENTS

# =========================================================================
# 🔄 FUNCTIONS: จัดการข้อมูลสูตรอาหาร และบันทึกฟาร์มรายวันตัวใครตัวมัน
# =========================================================================

def fetch_saved_formulas_from_supabase():
    """ดึงสูตรอาหารเฉพาะของผู้ใช้งานที่ล็อกอินอยู่ปัจจุบัน"""
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
        st.warning(f"⚠️ ไม่สามารถดึงสูตรอาหารส่วนตัวจากคลาวด์ได้: {e}")
        return []

def save_formula_to_supabase(formula_data):
    """บันทึกสูตรอาหารใหม่ ผูกเจ้าของด้วย owner_email ทุกครั้ง"""
    try:
        if st.session_state.is_authenticated and st.session_state.current_user_key:
            formula_data["owner_email"] = st.session_state.current_user_key
            supabase.table("saved_formulas").insert(formula_data).execute()
            st.success("🎉 บันทึกสูตรอาหารลงพื้นที่ส่วนตัวของคุณเรียบร้อยแล้ว!")
            fetch_saved_formulas_from_supabase()
            return True
        else:
            st.error("❌ กรุณาเข้าสู่ระบบก่อนทำการบันทึกข้อมูล")
            return False
    except Exception as e:
        st.error(f"❌ ไม่สามารถบันทึกสูตรลงคลาวด์ได้: {e}")
        return False

def fetch_daily_logs_from_supabase():
    """ดึงสมุดบันทึกกิจกรรมฟาร์มรายวันเฉพาะของตนเอง"""
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
        st.warning(f"⚠️ ไม่สามารถดึงบันทึกกิจกรรมฟาร์มจากคลาวด์ได้: {e}")
        return []

def save_daily_log_to_supabase(log_data):
    """บันทึกข้อมูลกิจกรรมฟาร์มประจำวัน ผูกเข้ากับระบบบัญชีผู้ใช้จริง"""
    try:
        if st.session_state.is_authenticated and st.session_state.current_user_key:
            log_data["owner_email"] = st.session_state.current_user_key
            supabase.table("daily_logs").insert(log_data).execute()
            st.success("🎉 บันทึกประวัติกิจกรรมฟาร์มประจำวันสำเร็จ!")
            fetch_daily_logs_from_supabase()
            return True
        else:
            st.error("❌ กรุณาเข้าสู่ระบบก่อนทำการบันทึกข้อมูล")
            return False
    except Exception as e:
        st.error(f"❌ ไม่สามารถบันทึกข้อมูลฟาร์มรายวันได้: {e}")
        return False


# ==========================================
# 🧮 3. CORE AI SOLVER ENGINE
# ==========================================
def run_ai_solver(req_p, req_m, req_c, req_ph, req_ly, req_me):
    prob = pulp.LpProblem("AI_First_Solver", pulp.LpMinimize)
    
    current_ingredients = fetch_ingredients_from_supabase()
    if not current_ingredients:
        st.error("❌ ไม่พบข้อมูลวัตถุดิบในระบบ ไม่สามารถคำนวณได้")
        return {}

    ing_vars = {
        name: pulp.LpVariable(
            name, 
            lowBound=float(d.get("min_limit", 0)) / 100.0, 
            upBound=float(d.get("max_limit", 100)) / 100.0
        ) 
        for name, d in current_ingredients.items()
    }
    
    s_p = pulp.LpVariable("s_p", lowBound=0)
    s_m = pulp.LpVariable("s_m", lowBound=0)
    s_c = pulp.LpVariable("s_c", lowBound=0)
    
    prob += pulp.lpSum([ing_vars[name] * float(d["price"]) for name, d in current_ingredients.items()]) + (10000.0 * s_p) + (10.0 * s_m) + (10000.0 * s_c), "Cost"
    
    prob += pulp.lpSum([ing_vars[name] for name in current_ingredients.keys()]) == 1.0, "Weight"
    
    prob += pulp.lpSum([ing_vars[name] * float(d["protein"]) for name, d in current_ingredients.items()]) + s_p >= req_p
    prob += pulp.lpSum([ing_vars[name] * float(d["me"]) for name, d in current_ingredients.items()]) + s_m >= req_m
    prob += pulp.lpSum([ing_vars[name] * float(d["calcium"]) for name, d in current_ingredients.items()]) + s_c >= req_c
    prob += pulp.lpSum([ing_vars[name] * float(d["phos"]) for name, d in current_ingredients.items()]) >= req_ph
    prob += pulp.lpSum([ing_vars[name] * float(d["lysine"]) for name, d in current_ingredients.items()]) >= req_ly
    prob += pulp.lpSum([ing_vars[name] * float(d["methionine"]) for name, d in current_ingredients.items()]) >= req_me
    
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
            st.error(f"ไม่สามารถเปิดหน้าตั้งรหัสผ่านใหม่ได้: {error}")
    elif recovery_code and not st.session_state.get("password_recovery_ready"):
        try:
            supabase.auth.exchange_code_for_session(recovery_code)
            st.session_state.auth_page_mode = "reset_password"
            st.session_state.password_recovery_ready = True
        except Exception as error:
            st.error(f"ไม่สามารถยืนยันลิงก์ตั้งรหัสผ่านใหม่ได้: {error}")

normalize_recovery_link_params()
detect_password_recovery_session()

if "user_database" not in st.session_state:
    st.session_state.user_database = {}

if not st.session_state.is_authenticated:

    # --- 4.0 หน้า RESET PASSWORD หลังจากกดลิงก์ในอีเมล ---
    if st.session_state.auth_page_mode == "reset_password":
        st.markdown("<div class='content-card' style='max-width: 550px; margin: 60px auto 0 auto;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #38bdf8 !important;'>🔑 ตั้งรหัสผ่านใหม่</h2>", unsafe_allow_html=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)

        if not st.session_state.get("password_recovery_ready"):
            st.warning("หน้านี้ใช้สำหรับตั้งรหัสผ่านใหม่หลังจากกดลิงก์ในอีเมลเท่านั้น")
            st.info("ถ้าคุณต้องการกู้คืนรหัสผ่าน ให้กลับไปหน้าเข้าสู่ระบบแล้วกดปุ่มลืมรหัสผ่าน ระบบจะส่งลิงก์มายังอีเมลของคุณ")
            if st.button("กลับไปหน้าเข้าสู่ระบบ", use_container_width=True):
                st.session_state.auth_page_mode = "login"
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

    # --- 4.1 หน้า LOGIN ---
    if st.session_state.auth_page_mode == "login":
        st.markdown("<div class='content-card' style='max-width: 550px; margin: 60px auto 0 auto;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #ffb703 !important;'>🔐 เข้าสู่ระบบ Layer Nutrition Studio Pro</h2>", unsafe_allow_html=True)
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
                            st.session_state.current_user_key = email_login.strip()

                            if email_login.strip().lower() == "222@gmail.com":
                                st.session_state.user_role = "admin"
                            else:
                                st.session_state.user_role = "user"

                            st.session_state.user_email = f"{email_login.strip().split('@')[0]} [{st.session_state.user_role.upper()}]"
                            
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
            st.query_params["auth_action"] = "forgot_password"
            st.session_state.auth_page_mode = "forgot"
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
                            st.success("🎉 สมัครสมาชิกสำเร็จและเข้าสู่ระบบแล้ว")
                            st.session_state.is_authenticated = True
                            st.session_state.current_user_key = su_email
                            st.session_state.user_role = "user"
                            st.session_state.user_email = f"{su_email.split('@')[0]} [USER]"
                            
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

# ==========================================
# 🎉 5. HEADER CONTROL PANEL
# ==========================================
col_h1, col_h2 = st.columns([7.5, 2.5])
with col_h1:
    st.markdown(f"# 🐔 Layer Nutrition Studio Pro <span style='font-size:1.1rem; color:#38bdf8;'>[สิทธิ์การใช้งาน: {st.session_state.user_email}]</span>", unsafe_allow_html=True)
with col_h2:
    cc1, cc2 = st.columns(2)
    with cc1:
        if "admin" in st.session_state.user_email.lower() or st.session_state.user_role == "admin":
            if st.session_state.user_role == "user":
                if st.button("🔄 หน้า Admin", use_container_width=True):
                    st.session_state.user_role = "admin"
                    st.rerun()
            else:
                if st.button("🔄 หน้า User", use_container_width=True):
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
    st.title("💻 Admin Master Data Control")
    st.caption("ระบบจัดการโครงสร้างสารอาหาร วัตถุดิบ สายพันธุ์ และผู้ใช้งานแบบ Dynamic ร่วมกับคลาวด์")
    
    admin_tabs = st.tabs([
        "⚙️ ตั้งค่าหัวข้อสารอาหาร",
        "🌽 คลังวัตถุดิบ & สารอาหาร", 
        "🐓 ทำเนียบสายพันธุ์ไก่ไข่", 
        "🧬 เกณฑ์โภชนาการตามช่วงอายุ", 
        "👤 การจัดการสิทธิ์ผู้ใช้งาน"
    ])
    
    # --- แท็บที่ 0: เพิ่ม/ลบ สารอาหารด้วยตัวเอง ---
    with admin_tabs[0]:
        st.subheader("⚙️ สารอาหารที่มีในระบบปัจจุบัน")
        
        with st.expander("📊 ดูโครงสร้างสารอาหารที่ใช้งานอยู่ทั้งหมด", expanded=True):
            df_nutrients = pd.DataFrame([
                {"รหัสระบบ (Key)": k, "ชื่อตัวชี้วัด (Label)": v["label"], "ความละเอียด (Step)": v["step"]} 
                for k, v in st.session_state.db_nutrient_keys.items()
            ])
            st.dataframe(df_nutrients, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        n_col1, n_col2 = st.columns(2, gap="large")
        
        with n_col1:
            st.markdown("### ➕ เพิ่มสารอาหารใหม่")
            with st.container(border=True):
                new_nut_key = st.text_input("รหัสอังกฤษ (เช่น fat, ash):", placeholder="กรอกพิมพ์เล็กห้ามมีช่องว่าง", key="add_nut_key").strip().lower()
                new_nut_label = st.text_input("ชื่อภาษาไทยที่แสดง (เช่น ไขมันดิบ (%)):", placeholder="เช่น วิตามินอี (mg/kg)", key="add_nut_label")
                new_nut_step = st.number_input("ความละเอียดในการกดปุ่มเพิ่ม/ลดค่า:", min_value=0.001, max_value=100.0, value=0.1, format="%.3f", key="add_nut_step")
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("✨ ยืนยันสร้างหัวข้อสารอาหาร", type="primary", use_container_width=True):
                    if not new_nut_key or not new_nut_label:
                        st.error("❌ กรุณากรอกข้อมูลให้ครบทั้งสองช่อง")
                    elif new_nut_key in st.session_state.db_nutrient_keys or new_nut_key in ["name", "min_limit", "max_limit"]:
                        st.error("❌ รหัสนี้ซ้ำหรือเป็นคำต้องห้ามของระบบ")
                    else:
                        # 1. เพิ่มเข้า Local Session State
                        st.session_state.db_nutrient_keys[new_nut_key] = {"label": new_nut_label, "step": new_nut_step, "default": 0.0}
                        
                        # 2. ทำการอัปเดต Schema วัตถุดิบเดิมให้รองรับ Key ใหม่ (ป้องกันบั๊ก KeyError)
                        for ing_name in st.session_state.db_ingredients.keys():
                            if new_nut_key not in st.session_state.db_ingredients[ing_name]:
                                st.session_state.db_ingredients[ing_name][new_nut_key] = 0.0
                        
                        st.success(f"🎉 เพิ่มโครงสร้างหัวข้อสารอาหาร '{new_nut_label}' เรียบร้อยแล้ว!")
                        st.rerun()
                        
        with n_col2:
            st.markdown("### ❌ ลบสารอาหาร")
            with st.container(border=True):
                removable_keys = [k for k in st.session_state.db_nutrient_keys.keys() if k != "price"]
                
                if removable_keys:
                    nut_to_del = st.selectbox("เลือกสารอาหารที่ต้องการถอดถอน:", removable_keys, format_func=lambda x: st.session_state.db_nutrient_keys[x]["label"], key="del_nut_select")
                    st.markdown("<br><br><br>", unsafe_allow_html=True)
                    
                    if st.button("🗑️ ยืนยันลบออกจากระบบถาวร", type="secondary", use_container_width=True):
                        del_label = st.session_state.db_nutrient_keys[nut_to_del]["label"]
                        
                        # ลบออกจากโครงสร้างหลักและวัตถุดิบทุกตัวป้องกันข้อมูลขยะค้างคั่ง
                        del st.session_state.db_nutrient_keys[nut_to_del]
                        for ing_name in st.session_state.db_ingredients.keys():
                            if nut_to_del in st.session_state.db_ingredients[ing_name]:
                                del st.session_state.db_ingredients[ing_name][nut_to_del]
                                
                        st.success(f"🔥 ลบสารอาหาร '{del_label}' สำเร็จ")
                        st.rerun()
                else:
                    st.warning("⚠️ ไม่มีสารอาหารอื่นนอกเหนือจากราคาที่สามารถลบได้")

    # --- แท็บที่ 1: จัดการและแก้ไขวัตถุดิบ/สารอาหาร ---
    with admin_tabs[1]:
        with st.expander("📊 เปิดดูคลังวัตถุดิบและราคาปัจจุบันในระบบ", expanded=False):
            if st.session_state.db_ingredients:
                st.dataframe(pd.DataFrame.from_dict(st.session_state.db_ingredients, orient='index'), use_container_width=True)
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
                        # อัปเดตข้อมูลลง Local State
                        st.session_state.db_ingredients[selected_ing_edit].update(edited_values)
                        st.session_state.db_ingredients[selected_ing_edit].update({"min_limit": edit_ing_min, "max_limit": edit_ing_max})
                        
                        # ⚡ ซิงค์ความถาวรลง Supabase Cloud Database แบบเรียลไทม์
                        try:
                            owner_email = get_ingredient_owner_for_write(target_ing)
                            payload = {"name": selected_ing_edit, "min_limit": edit_ing_min, "max_limit": edit_ing_max, "owner_email": owner_email}
                            payload.update(edited_values)
                            st.session_state.db_ingredients[selected_ing_edit]["owner_email"] = owner_email
                            supabase.table("ingredients").upsert(payload).execute()
                            st.success(f"🎉 ปรับปรุงข้อมูลสารอาหารของ '{selected_ing_edit}' ลงระบบคลาวด์เรียบร้อยแล้ว")
                            st.rerun()
                        except Exception as cloud_err:
                            st.warning(f"⚠️ บันทึกในระบบจำลองสำเร็จ แต่ไม่สามารถซิงค์ขึ้น Cloud ได้: {cloud_err}")

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
                        
                        # บันทึกลงเครื่องและยิงขึ้นฐานข้อมูลคลาวด์ Supabase
                        st.session_state.db_ingredients[ing_name] = base_data
                        try:
                            supabase.table("ingredients").insert(base_data).execute()
                            st.success(f"🎉 นำเข้า '{ing_name}' สู่คลาวด์ฐานข้อมูลเรียบร้อย!")
                            st.rerun()
                        except Exception as cloud_err:
                            st.success(f"🎉 บันทึกชั่วคราวสำเร็จ (Cloud Error: {cloud_err})")

        elif crud_mode == "🗑️ ลบวัตถุดิบออก" and st.session_state.db_ingredients:
            st.markdown("#### 🗑️ ลบรายการวัตถุดิบ")
            to_del = st.selectbox("เลือกวัตถุดิบที่จะนำออกจากระบบถาวร:", list(st.session_state.db_ingredients.keys()))
            if st.button("🗑️ ยืนยันคำสั่งลบวัตถุดิบออกจากระบบ", type="primary", use_container_width=True):
                owner_email = get_ingredient_owner_for_write(st.session_state.db_ingredients.get(to_del, {}))
                try:
                    supabase.table("ingredients").delete().eq("name", to_del).eq("owner_email", owner_email).execute()
                except:
                    pass
                del st.session_state.db_ingredients[to_del]
                st.success(f"🔥 ลบ '{to_del}' ออกจากคลังเรียบร้อยแล้ว")
                st.rerun()

    # --- แท็บที่ 2: จัดการทำเนียบสายพันธุ์ ---
    with admin_tabs[2]:
        with st.expander("📊 เปิดดูทำเนียบสายพันธุ์ไก่ไข่ในระบบทั้งหมด", expanded=True):
            st.dataframe(pd.DataFrame(st.session_state.db_breeds), use_container_width=True, hide_index=True)
            
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
                        st.session_state.db_breeds.append(breed_payload)
                        try:
                            supabase.table("db_breeds").insert(breed_payload).execute()
                        except Exception as cloud_err:
                            st.warning(f"บันทึกสายพันธุ์ในหน่วยความจำแล้ว แต่ยังส่งขึ้น Supabase ไม่สำเร็จ: {cloud_err}")
                        st.success(f"🎉 เพิ่มสายพันธุ์ '{b_name}' สำเร็จ")
                        st.rerun()
                    else: st.warning("⚠️ กรุณากรอกชื่อสายพันธุ์")
        with bc2:
            st.markdown("### ❌ ลบข้อมูลสายพันธุ์")
            with st.container(border=True):
                if st.session_state.db_breeds:
                    b_del = st.selectbox("เลือกสายพันธุ์ที่ต้องการลบ:", [b["breed_name"] for b in st.session_state.db_breeds])
                    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
                    if st.button("🗑️ ยืนยันลบออกจากทำเนียบ", type="primary", use_container_width=True):
                        try:
                            supabase.table("db_breeds").delete().eq("breed_name", b_del).execute()
                        except Exception as cloud_err:
                            st.warning(f"ลบออกจากหน้าจอแล้ว แต่ยังลบจาก Supabase ไม่สำเร็จ: {cloud_err}")
                        st.session_state.db_breeds = [b for b in st.session_state.db_breeds if b["breed_name"] != b_del]
                        st.success(f"🔥 ลบสายพันธุ์ '{b_del}' เรียบร้อยแล้ว")
                        st.rerun()
                else: st.info("ไม่มีข้อมูลสายพันธุ์ในระบบ")

    # --- แท็บที่ 3: แก้ไขเป้าหมายความต้องการโภชนาการสัตว์แยกตามอายุ ---
    with admin_tabs[3]:
        with st.expander("📊 เปิดดูค่าเกณฑ์มาตรฐานโภชนาการสัตว์ ณ ปัจจุบัน", expanded=False):
            st.dataframe(pd.DataFrame.from_dict(st.session_state.db_targets, orient='index'), use_container_width=True)
        
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
                    current_target_val = float(st.session_state.db_targets[select_stage_crud].get(nut_key, 0.0))
                    updated_target_values[nut_key] = st.number_input(f"ขั้นต่ำของ {nut_info['label']}:", value=current_target_val, step=nut_info["step"])
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("💾 ยืนยันอัปเดตเกณฑ์โภชนาการช่วงอายุนี้", type="primary", use_container_width=True):
                st.session_state.db_targets[select_stage_crud].update(updated_target_values)
                try:
                    supabase.table("db_targets").update(updated_target_values).eq("stage_key", select_stage_crud).execute()
                except Exception as cloud_err:
                    st.warning(f"อัปเดตในหน้าจอแล้ว แต่ยังส่งขึ้น Supabase ไม่สำเร็จ: {cloud_err}")
                st.success("🎉 อัปเดตเกณฑ์มาตรฐานความต้องการทางโภชนาการเรียบร้อยแล้ว!")
                st.rerun()

    # --- แท็บที่ 4: จัดการสมาชิกผู้ใช้งาน ---
    with admin_tabs[4]:
        st.subheader("👤 สรุปบัญชีผู้ใช้งานในระบบ")
        
        users_list = []
        for email, info in st.session_state.user_database.items():
            role_badge = "🔑 ADMIN" if info.get("role") == "admin" else "👤 USER"
            users_list.append({
                "Email ID / Username": email,
                "ชื่อ-นามสกุล": f"{info.get('name', '-')} {info.get('surname', '-')}",
                "เบอร์โทรศัพท์": info.get("tel", "-"),
                "ระดับสิทธิ์ (Role)": role_badge,
                "วันที่ลงทะเบียน": info.get("reg_date", "2026-01-01")
            })
            
        if users_list:
            st.dataframe(pd.DataFrame(users_list), use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ ปัจจุบันใช้ระบบทดสอบจำลอง (ไม่มีประวัติบัญชีผู้ใช้อื่นในตารางชั่วคราว)")
            
        st.markdown("---")
        uc1, uc2 = st.columns(2, gap="large")
        with uc1:
            st.markdown("### ✏️ เปลี่ยนแปลงสิทธิ์ของสมาชิก")
            with st.container(border=True):
                user_keys = list(st.session_state.get("user_database", {}).keys())
                if not user_keys:
                    st.warning("ยังไม่มีข้อมูลสมาชิกในระบบหน่วยความจำชั่วคราว")
                else:
                    selected_user_email = st.selectbox("เลือกบัญชีอีเมลที่ต้องการแก้ไข:", user_keys)
                    current_user_role = st.session_state.user_database[selected_user_email]["role"]
                    new_role = st.selectbox("ระบุสิทธิ์ใหม่ที่ต้องการมอบให้:", ["user", "admin"], index=0 if current_user_role == "user" else 1)
                    
                    if st.button("💾 บันทึกการเปลี่ยนสิทธิ์", use_container_width=True, type="primary"):
                        st.session_state.user_database[selected_user_email]["role"] = new_role
                        st.success(f"🎉 อัปเดตสิทธิ์ของ {selected_user_email} เป็น {new_role.upper()} สำเร็จ")
                        st.rerun()
                
        with uc2:
            st.markdown("### ❌ ระงับและลบบัญชี")
            with st.container(border=True):
                user_to_delete = st.selectbox("เลือกบัญชีที่จะลบออกจากระบบถาวร:", ["-- เลือกบัญชี --"] + list(st.session_state.user_database.keys()))
                if st.button("🗑️ ยืนยันคำสั่งลบบัญชีผู้ใช้", type="primary", use_container_width=True):
                    current_user = st.session_state.get("current_user_key", "").lower().strip()
                    
                    if user_to_delete == "-- เลือกบัญชี --":
                        st.warning("⚠️ กรุณาเลือกบัญชีผู้ใช้ก่อนกดยืนยัน")
                    # ปรับปรุงให้ตรวจสอบอีเมลแบบเต็มสเกล ป้องกันแอดมินลบตัวเอง
                    elif "222@gmail.com" in user_to_delete.lower() or "admin" in user_to_delete.lower():
                        st.error("❌ บัญชี Root Account หลักของฟาร์ม ไม่สามารถลบได้")
                    elif user_to_delete.lower().strip() == current_user:
                        st.error("❌ คุณไม่สามารถสั่งลบบัญชีตัวเองที่กำลังใช้งานล็อกอินอยู่ได้")
                    else:
                        del st.session_state.user_database[user_to_delete]
                        st.success(f"🔥 ลบบัญชี {user_to_delete} เรียบร้อย")
                        st.rerun()
        
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🔄 สลับบทบาทกลับไปโหมดผู้ใช้งานทั่วไป (User Dashboard)", use_container_width=True):
        st.session_state.user_role = "user"
        st.rerun()
       
else:
    # ==========================================
    # 🎨 CUSTOM UI/UX FOR ALL AGES (BIG FONT & HIGH CONTRAST)
    # ==========================================
    st.markdown(
        """
        <style>
            /* ขยายขนาดฟอนต์ของหัวข้อแท็บ */
            .stTabs [data-baseweb="tab-list"] button {
                font-size: 22px !important;
                font-weight: bold !important;
                height: 60px !important;
            }
            /* ขยายฟอนต์และช่องพิมพ์ข้อมูลทั้งหมด */
            .stNumberInput input, .stSelectbox div, .stSlider div {
                font-size: 20px !important;
                font-weight: bold !important;
            }
            label {
                font-size: 20px !important;
                font-weight: bold !important;
                color: #f1f5f9 !important;
            }
            /* ปรับแต่งปุ่มกดให้ใหญ่เบิ้ม จิ้มง่ายไม่พลาด */
            .stButton button {
                font-size: 22px !important;
                font-weight: bold !important;
                padding: 15px 20px !important;
                border-radius: 12px !important;
                min-height: 55px !important;
            }
            /* กล่องการ์ดเน้นข้อความให้อ่านง่าย */
            .farmer-card {
                background-color: #1e293b;
                border: 2px solid #475569;
                padding: 22px;
                border-radius: 14px;
                margin-bottom: 20px;
            }
            /* สไตล์ตัวเลขแดชบอร์ดขนาดใหญ่พิเศษ */
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
    # 👑 USER ROUTE: ACCESSIBLE INTERFACE
    # ==========================================
    page_tabs = st.tabs(
        [
            "🥣 1. สูตรอาหาร & คลังสูตรเก่า",
            "💰 2. บันทึกรายวัน & บัญชีฟาร์ม",
            "📊 3. ใบสั่งผสมอาหาร (สำหรับคนงาน)",
        ]
    )

    # ------------------------------------------
    # TAB 1: MANAGEMENT & FORMULA MATRIX
    # ------------------------------------------
    with page_tabs[0]:
        # --- ส่วนที่ 1: ดึงสูตรเก่า ---
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("### 📂 [ปุ่มทางลัด] เรียกใช้สูตรเก่าที่เคยเซฟไว้")
        if not st.session_state.saved_formulas:
            st.info("💡 ตอนนี้ยังไม่มีสูตรอาหารที่บันทึกไว้")
        else:
            col_load1, col_load2 = st.columns([7, 3])
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
                    st.session_state.current_weights = target_f["weights"].copy()
                    st.success(f"ดึงข้อมูล '{selected_f_name}' มาใช้งานแล้ว!")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        # --- ส่วนที่ 2: เลือกสายพันธุ์ และ ตั้งค่าโภชนาการเป้าหมาย ---
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("### 🐓 เลือกสายพันธุ์และโภชนาการเป้าหมาย")

        col_br1, col_br2, col_br3 = st.columns(3)
        with col_br1:
            list_groups = [g["group_name"] for g in st.session_state.db_groups]
            selected_g = st.selectbox("📁 เลือกกลุ่มสายพันธุ์หลัก:", list_groups)

            # ย้ายเป้าหมายมาอยู่ด้านบนเพื่อความลื่นไหลในการใช้งาน
            edit_p = st.number_input(
                "🎯 โปรตีนเป้าหมาย (%):",
                min_value=5.0,
                value=float(st.session_state.get("base_req_protein", 16.5)),
                step=0.1,
            )
            edit_m = st.number_input(
                "🎯 พลังงานเป้าหมาย (kcal/kg):",
                min_value=1000.0,
                value=float(st.session_state.get("base_req_me", 2750.0)),
                step=25.0,
            )

        with col_br2:
            filtered_breeds = [
                b for b in st.session_state.db_breeds if b["group_name"] == selected_g
            ]
            breed_names = (
                [b["breed_name"] for b in filtered_breeds] if filtered_breeds else ["ไม่มีข้อมูล"]
            )
            selected_b_name = st.selectbox("🐔 เลือกสายพันธุ์ไก่ไข่:", breed_names)

            # ดึงข้อมูลสายพันธุ์และเซฟเข้า session_state เพื่อป้องกันความผิดพลาดข้ามแท็บ
            current_breed_data = next(
                (b for b in filtered_breeds if b["breed_name"] == selected_b_name),
                {"default_feed": 114.0, "egg_color": "ไม่ระบุ"},
            )
            st.session_state["current_breed_default_feed"] = current_breed_data.get(
                "default_feed", 114.0
            )

            edit_c = st.number_input(
                "🎯 แคลเซียมเป้าหมาย (%):",
                min_value=0.5,
                value=float(st.session_state.get("base_req_calcium", 3.8)),
                step=0.05,
            )
            edit_ph = st.number_input(
                "🎯 ฟอสฟอรัสเป้าหมาย (%):",
                min_value=0.1,
                value=float(st.session_state.get("base_req_phos", 0.45)),
                step=0.02,
            )

        with col_br3:
            stage_options = {
                s["stage_name"]: s["stage_key"] for s in st.session_state.db_targets.values()
            }
            selected_stage_label = st.selectbox(
                "📋 เลือกช่วงระยะการให้ไข่:", list(stage_options.keys())
            )
            base_req = st.session_state.db_targets[stage_options[selected_stage_label]]

            # โหลดค่าเริ่มต้นจากสายพันธุ์ที่เลือกเข้า session
            if "base_req_protein" not in st.session_state:
                st.session_state["base_req_protein"] = base_req["protein"]
                st.session_state["base_req_me"] = base_req["me"]
                st.session_state["base_req_calcium"] = base_req["calcium"]
                st.session_state["base_req_phos"] = base_req["phos"]

            st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
            if st.button("⚡ สั่ง AI คำนวณสูตรด่วน", type="primary", use_container_width=True):
                with st.spinner("AI กำลังจัดสูตร..."):
                    st.session_state.current_weights = run_ai_solver(
                        edit_p,
                        edit_m,
                        edit_c,
                        edit_ph,
                        float(base_req["lysine"]),
                        float(base_req["methionine"]),
                    )
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        # --- ส่วนที่ 3: ปุ่มลัดตามสถานการณ์ราคาตลาด ---
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("### ⚡ [กดด่วน] ปุ่มลัดสลับสูตรอาหารตามสถานการณ์ราคาตลาด")
        sc_col1, sc_col2, sc_col3 = st.columns(3)

        if not st.session_state.current_weights:
            st.session_state.current_weights = run_ai_solver(
                base_req["protein"],
                base_req["me"],
                base_req["calcium"],
                base_req["phos"],
                base_req["lysine"],
                base_req["methionine"],
            )

        with sc_col1:
            if st.button("🟢 โหมดปกติ / เน้นถูกสุด", use_container_width=True):
                st.session_state.current_weights = run_ai_solver(
                    base_req["protein"],
                    base_req["me"],
                    base_req["calcium"],
                    base_req["phos"],
                    base_req["lysine"],
                    base_req["methionine"],
                )
                st.rerun()
        with sc_col2:
            if st.button("🌾 โหมดข้าวโพด / รำข้าวแพง", use_container_width=True):
                raw_weights = run_ai_solver(
                    base_req["protein"],
                    base_req["me"],
                    base_req["calcium"],
                    base_req["phos"],
                    base_req["lysine"],
                    base_req["methionine"],
                )
                if "ข้าวโพด" in raw_weights:
                    raw_weights["ข้าวโพด"] = max(0.0, raw_weights["ข้าวโพด"] - 20.0)
                if "รำข้าวละเอียด" in raw_weights:
                    raw_weights["รำข้าวละเอียด"] = max(0.0, raw_weights["รำข้าวละเอียด"] - 10.0)
                if "ปลายข้าว" in raw_weights:
                    raw_weights["ปลายข้าว"] += 15.0
                if "มันเส้น" in raw_weights:
                    raw_weights["มันเส้น"] += 15.0
                st.session_state.current_weights = raw_weights
                st.rerun()
        with sc_col3:
            if st.button("🥚 โหมดเร่งไข่ใหญ่ / เปลือกหนา", use_container_width=True):
                raw_weights = run_ai_solver(
                    base_req["protein"] + 0.5,
                    base_req["me"],
                    base_req["calcium"] + 0.3,
                    base_req["phos"],
                    base_req["lysine"],
                    base_req["methionine"],
                )
                if "น้ำมันปาล์ม" in raw_weights:
                    raw_weights["น้ำมันปาล์ม"] = max(2.0, raw_weights["น้ำมันปาล์ม"])
                if "เปลือกหอยบด" in raw_weights:
                    raw_weights["เปลือกหอยบด"] = max(8.0, raw_weights["เปลือกหอยบด"])
                st.session_state.current_weights = raw_weights
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        # --- ส่วนที่ 4: แถบปรับสัดส่วนอาหารแบบ 2 คอลัมน์ย่อย และตารางผลลัพธ์ ---
        col_left, col_right = st.columns([1.1, 0.9])

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

        with col_left:
            st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
            cl_title, cl_reset = st.columns([6, 4])
            with cl_title:
                st.markdown("### 🥣 แถบปรับสัดส่วนวัตถุดิบ (%)")
            with cl_reset:
                if st.button("🔄 รีเซ็ตค่าใหม่ทั้งหมด", use_container_width=True):
                    st.session_state.current_weights = run_ai_solver(
                        base_req["protein"],
                        base_req["me"],
                        base_req["calcium"],
                        base_req["phos"],
                        base_req["lysine"],
                        base_req["methionine"],
                    )
                    st.rerun()

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

            # ปรับแบ่งตัว Slider วัตถุดิบออกเป็น 2 คอลัมน์ย่อย เพื่อหน้าจอที่กระชับ ไม่ยาวเกินไป
            ing_keys = list(st.session_state.db_ingredients.keys())
            ing_col1, ing_col2 = st.columns(2)

            for idx, name in enumerate(ing_keys):
                d = st.session_state.db_ingredients[name]
                saved_w = float(st.session_state.current_weights.get(name, 0.0))
                saved_w = max(0.0, min(100.0, saved_w))

                target_col = ing_col1 if idx % 2 == 0 else ing_col2
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

            st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
            if abs(running_total - 100.0) > 0.1:
                st.markdown(
                    f"<div style='background-color:#991b1b; padding:15px; border-radius:8px; font-size:18px; font-weight:bold; text-align:center;'>⚠️ สัดส่วนอาหารรวมได้: {running_total:.1f}% (กรุณาปรับให้ครบ 100%)</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div style='background-color:#065f46; padding:15px; border-radius:8px; font-size:18px; font-weight:bold; text-align:center;'>🟢 ส่วนผสมครบถ้วนสมบูรณ์ 100%</div>",
                    unsafe_allow_html=True,
                )

            st.session_state.current_weights = temp_weights
            st.markdown("</div>", unsafe_allow_html=True)

        with col_right:
            st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
            st.markdown("### 🧪 ผลลัพธ์โภชนาการจริงในสูตร")

            comparison_table = [
                {
                    "โภชนาการสำคัญ": "โปรตีนดิบ (% CP)",
                    "เป้าหมาย": f"{edit_p:.2f} %",
                    "ได้จริงในสูตร": f"{act_nut['protein']:.2f} %",
                },
                {
                    "โภชนาการสำคัญ": "พลังงานใช้ประโยชน์ (ME)",
                    "เป้าหมาย": f"{edit_m:.0f}",
                    "ได้จริงในสูตร": f"{act_nut['me']:.0f}",
                },
                {
                    "โภชนาการสำคัญ": "แคลเซียม (% Ca)",
                    "เป้าหมาย": f"{edit_c:.2f} %",
                    "ได้จริงในสูตร": f"{act_nut['calcium']:.2f} %",
                },
                {
                    "โภชนาการสำคัญ": "ฟอสฟอรัส (% P)",
                    "เป้าหมาย": f"{edit_ph:.2f} %",
                    "ได้จริงในสูตร": f"{act_nut['phos']:.2f} %",
                },
            ]
            st.dataframe(
                pd.DataFrame(comparison_table), use_container_width=True, hide_index=True
            )

            st.markdown(
                f"<div style='background-color:#1e293b; padding:15px; border-radius:10px; border:2px solid #38bdf8; text-align:center; font-size:24px; font-weight:bold; margin: 15px 0;'>💰 ต้นทุนค่าอาหารสูตรนี้: {net_cost:.2f} บาท/กก.</div>",
                unsafe_allow_html=True,
            )

            breed_display_name = (
                selected_b_name.split()[-2]
                if len(selected_b_name.split()) > 1
                else selected_b_name
            )
            save_name_input = st.text_input(
                "💾 ตั้งชื่อเล่นสูตรอาหารเพื่อกดเซฟ:",
                value=f"สูตร {breed_display_name} {net_cost:.1f} บาท",
            )
            if st.button("📥 ยืนยันกดบันทึกสูตรอาหารลงคลัง", use_container_width=True):
                st.session_state.saved_formulas.append(
                    {
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
                )
                st.success("บันทึกสูตรเรียบร้อย!")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------
    # TAB 2: DAILY LOG & CASHFLOW
    # ------------------------------------------
    with page_tabs[1]:
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown(
            "<h2>☀️ บันทึกตัวชี้วัดฟาร์ม & รายรับ-รายจ่ายประจำวัน</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='border-bottom: 2px solid #475569; margin:15px 0;'></div>",
            unsafe_allow_html=True,
        )

        # ปุ่มทางลัด: ดึงข้อมูลเมื่อวานมาเติมอัตโนมัติ เพื่อลดเวลาพิมพ์เอกสารหน้าฟาร์ม
        if st.session_state.daily_logs:
            if st.button(
                "📋 ดึงข้อมูลจากประวัติล่าสุด (ไม่ต้องพิมพ์ใหม่หมด)", use_container_width=True
            ):
                last_log = st.session_state.daily_logs[-1]
                st.session_state["shortcut_birds"] = last_log["จำนวนไก่ (ตัว)"]
                st.session_state["shortcut_price"] = (
                    last_log["รายได้ขายไข่ (บาท)"] / last_log["ไข่ที่เก็บได้ (ฟอง)"]
                    if last_log["ไข่ที่เก็บได้ (ฟอง)"] > 0
                    else 4.10
                )
                st.success("ดึงข้อมูลเดิมเรียบร้อย! กรุณาตรวจสอบและอัปเดตจำนวนไข่ประจำวันนี้")

        log_col1, log_col2 = st.columns(2)
        with log_col1:
            st.markdown("#### 📝 ส่วนที่ 1: ข้อมูลฝูงไก่วันนี้")
            log_date = st.date_input(
                "วันที่บันทึกข้อมูล:", datetime.date.today(), key="farm_log_date"
            )
            flock_age_weeks = st.number_input(
                "🐣 อายุฝูงไก่ปัจจุบัน (สัปดาห์):", min_value=1, max_value=100, value=25, step=1
            )

            default_birds = st.session_state.get("shortcut_birds", 5000)
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

            # เรียกใช้ค่าแนะนำจากที่เราเซฟลง session_state ไว้เพื่อความปลอดภัย
            breed_default_feed = st.session_state.get("current_breed_default_feed", 114.0)
            recommended_feed = float(bird_count * breed_default_feed / 1000.0)
            st.markdown(
                f"<p style='color:#6366f1; font-size:16px; font-weight:bold; margin-bottom:-5px;'>💡 ปริมาณอาหารแนะนำตามสายพันธุ์: {recommended_feed:,.1f} กก.</p>",
                unsafe_allow_html=True,
            )
            actual_feed_given_kg = st.number_input(
                "🍽️ น้ำหนักอาหารที่ให้ไก่กินรวมวันนี้ (กิโลกรัม):",
                min_value=10.0,
                value=recommended_feed,
                step=10.0,
            )

        with log_col2:
            st.markdown("#### 💰 ส่วนที่ 2: จำนวนไข่และราคาส่งวันนี้")
            collected_eggs = st.number_input(
                "จำนวนฟองไข่ที่เก็บได้จริงวันนี้ (ฟอง):", min_value=0, value=4200
            )

            default_price = st.session_state.get("shortcut_price", 4.10)
            egg_sale_price = st.number_input(
                "💵 ราคารับซื้อไข่หน้าฟาร์มวันนี้ (บาท/ฟอง):",
                min_value=1.0,
                value=float(default_price),
                step=0.1,
            )
            dead_birds = st.number_input(
                "จำนวนไก่ตาย/คัดทิ้งวันนี้ (ตัว):", min_value=0, value=2
            )
            avg_egg_weight_g = st.number_input(
                "⚖️ น้ำหนักไข่เฉลี่ยวันนี้ (กรัม/ฟอง):",
                min_value=30.0,
                max_value=80.0,
                value=62.0,
                step=0.5,
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

        # 🚨 ระบบปฏิทินเตือนความจำวัคซีนและงานรูทีนตามช่วงอายุไก่
        st.markdown(
            "<div style='background-color:#1e1b4b; padding:20px; border-radius:12px; border:2px solid #6366f1; margin: 20px 0;'>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"### 📋 ปฏิทินเตือนงานสำคัญสำหรับไก่อายุ {flock_age_weeks} สัปดาห์:"
        )
        if flock_age_weeks <= 3:
            st.markdown(
                "<p style='color:#38bdf8; font-size:22px; font-weight:bold;'>• ต้องทำวัคซีนนิวคาสเซิล + หลอดลมอักเสบ และตรวจเช็กระบบไฟกก</p>",
                unsafe_allow_html=True,
            )
        elif flock_age_weeks <= 8:
            st.markdown(
                "<p style='color:#38bdf8; font-size:22px; font-weight:bold;'>• ต้องทำวัคซีนฝีดาษ และทำวัคซีนอหิวาต์ไก่รอบที่ 1</p>",
                unsafe_allow_html=True,
            )
        elif flock_age_weeks <= 16:
            st.markdown(
                "<p style='color:#38bdf8; font-size:22px; font-weight:bold;'>• ต้องถ่ายพยาธิไก่ก่อนย้ายเข้ากรงตับ และทำวัคซีนรวมก่อนเริ่มไข่</p>",
                unsafe_allow_html=True,
            )
        elif flock_age_weeks <= 24:
            st.markdown(
                "<p style='color:#fbbf24; font-size:22px; font-weight:bold;'>• ไก่เริ่มไข่แล้ว: [ระวัง] ห้ามลดแสงสว่างในเล้าเด็ดขาด! แสงต้องสม่ำเสมอ</p>",
                unsafe_allow_html=True,
            )
        elif flock_age_weeks <= 60:
            st.markdown(
                "<p style='color:#10b981; font-size:22px; font-weight:bold;'>• ช่วงไข่ดก: สุ่มเช็กความหนาเปลือกไข่ และล้างทำความสะอาดหัวนิปเปิ้ลน้ำทุกสัปดาห์</p>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<p style='color:#f87171; font-size:22px; font-weight:bold;'>• ไก่แก่ท้ายชุด: ให้คนงานเสริมเปลือกหอยบดในรางช่วงเย็น ป้องกันไข่เปลือกบางแตกหัก</p>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            "<div style='border-bottom: 2px dashed #475569; margin:20px 0;'></div>",
            unsafe_allow_html=True,
        )

        # 💰 เมทริกซ์คำนวณต้นทุนการเงินหน้าฟาร์มสุทธิ
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
                f"🚨 เล้าร้อนจัด ({env_temp}°C) ไก่เสี่ยงช็อกตาย! คนงานต้องเปิดระบบพ่นหมอกและเร่งพัดลมทันที"
            )

        st.markdown("### 📊 สรุปผลกำไรสุทธิและตัวชี้วัดวันนี้")
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
            st.session_state.daily_logs.append(
                {
                    "วันที่": str(log_date),
                    "อายุฝูง (สัปดาห์)": flock_age_weeks,
                    "จำนวนไก่ (ตัว)": bird_count,
                    "อุณหภูมิ (°C)": env_temp,
                    "อาหารที่กิน (KG)": actual_feed_given_kg,
                    "ไข่ที่เก็บได้ (ฟอง)": collected_eggs,
                    "รายได้ขายไข่ (บาท)": round(total_revenue, 2),
                    "ต้นทุนอาหาร (บาท)": round(total_feed_cost, 2),
                    "กำไรสุทธิ (บาท)": round(net_profit_day, 2),
                    "อัตราไข่ (%)": round(henday_pct, 1),
                    "FCR": round(fcr_ratio, 2),
                }
            )
            st.success("บันทึกข้อมูลเรียบร้อย!")
            st.rerun()

        st.markdown(
            "<div style='border-bottom: 2px dashed #475569; margin:25px 0;'></div>",
            unsafe_allow_html=True,
        )
        st.markdown("### 📋 ตารางประวัติฟาร์มย้อนหลัง")
        if not st.session_state.daily_logs:
            st.info("💡 ยังไม่มีข้อมูลย้อนหลัง")
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

                    # ปรับสัญลักษณ์ให้คนงานในโรงเรือนอ่านง่าย ไม่ตักสัดส่วนผิดพลาด
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
            st.dataframe(df_po, use_container_width=True, hide_index=True)

            st.markdown(
                f"<div style='background-color:#1e293b; padding:15px; border-radius:10px; border:2px dashed #10b981; font-size:24px; font-weight:bold; text-align:center; margin:15px 0;'>💵 งบประมาณค่าวัตถุดิบรวมรอบนี้: {total_po_cost:,.2f} บาท</div>",
                unsafe_allow_html=True,
            )

            # --- ฟีเจอร์ใหม่: ปุ่มด่วนสำหรับก๊อปปี้ข้อความภาษาไทยส่งเข้ากลุ่ม LINE ---
            line_text = f"📋 *ใบสั่งผสมอาหารสัตว์รวม: {total_tonnage:,} กก.*\n"
            line_text += f"สูตรสำหรับ: {selected_b_name} ({selected_stage_label})\n"
            line_text += "--------------------------------------\n"
            for item in po_buffer:
                line_text += f"🔹 {item['รายการวัตถุดิบ']}: {item['📢 วิธีตักหน้างาน (กระสอบละ 50kg)']}\n"
            line_text += "--------------------------------------\n"
            line_text += f"💰 งบประมาณรวมรอบนี้: {total_po_cost:,.0f} บาท"

            st.markdown("### 📱 ข้อความด่วนสำหรับก๊อปปี้ส่ง LINE (คนงานเปิดอ่านง่าย)")
            st.code(line_text, language="text")

            # ดาวน์โหลดแบบไฟล์ดั้งเดิม
            csv_s = io.StringIO()
            df_po.to_csv(csv_s, index=False, encoding="utf-8-sig")
            st.download_button(
                "📥 กดดาวน์โหลดใบสั่งงานเป็นไฟล์ CSV",
                data=csv_s.getvalue(),
                file_name=f"ใบสั่งผสมอาหาร_{total_tonnage}กก.csv",
                mime="text/csv",
                use_container_width=True,
                key="download_csv_btn",
            )
        st.markdown("</div>", unsafe_allow_html=True)
