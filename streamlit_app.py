import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pulp
import io
import datetime
import re
from supabase import create_client, Client

# ==========================================
# 🔌 SUPABASE CONNECTION INITIALIZATION
# ==========================================
SUPABASE_URL = "https://nxyncxqbtntlpzqessou.supabase.co"
SUPABASE_KEY = "sb_publishable_m411zYbsazCAsmmUMIuMkA_ypb1BYPr"

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"❌ ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ Supabase ได้: {e}")

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
    .stTabs [data-baseweb="tab-list"] button { font-size: 22px !important; font-weight: bold !important; height: 60px !important; }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-weight: bold !important; font-size:1.05rem !important; }
    
    .stNumberInput input, .stSelectbox div, .stSlider div { font-size: 20px !important; font-weight: bold !important; }
    label { font-size: 20px !important; font-weight: bold !important; color: #f1f5f9 !important; }
    .stButton button { font-size: 22px !important; font-weight: bold !important; padding: 15px 20px !important; border-radius: 12px !important; min-height: 55px !important; }
    
    .content-card {
        background-color: rgba(0, 0, 0, 0.90) !important; padding: 30px;
        border-radius: 18px; border: 1px solid rgba(255, 255, 255, 0.18);
        backdrop-filter: blur(10px); margin-bottom: 25px;
    }
    .farmer-card { background-color: #1e293b; border: 2px solid #475569; padding: 22px; border-radius: 14px; margin-bottom: 20px; }
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
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False
if "auth_page_mode" not in st.session_state:
    st.session_state.auth_page_mode = "login"  
if "user_role" not in st.session_state:
    st.session_state.user_role = "user"  
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "current_user_key" not in st.session_state:
    st.session_state.current_user_key = ""
if "saved_formulas" not in st.session_state:
    st.session_state.saved_formulas = []  
if "daily_logs" not in st.session_state:
    st.session_state.daily_logs = [] 
if "current_weights" not in st.session_state:
    st.session_state.current_weights = {}

# ฟังก์ชันตรวจสอบระดับความปลอดภัยของรหัสผ่าน
def check_password_strength(password):
    if len(password) < 8:
        return False, "❌ รหัสผ่านต้องมีความยาวอย่างน้อย 8 ตัวอักษร"
    if not re.search("[a-z]", password):
        return False, "❌ รหัสผ่านต้องมีอักษรพิมพ์เล็ก (a-z) อย่างน้อย 1 ตัว"
    if not re.search("[A-Z]", password):
        return False, "❌ รหัสผ่านต้องมีอักษรพิมพ์ใหญ่ (A-Z) อย่างน้อย 1 ตัว"
    if not re.search("[0-9]", password):
        return False, "❌ รหัสผ่านต้องมีตัวเลข (0-9) อย่างน้อย 1 ตัว"
    if not re.search("[_@$!%*#?&.]", password):
        return False, "❌ รหัสผ่านต้องมีอักขระพิเศษอย่างน้อย 1 ตัว (เช่น @, #, $, %, !, ., _)"
    return True, "🟢 รหัสผ่านมีความปลอดภัยสูงตามมาตรฐาน"

# โครงสร้างสารอาหารหลัก
if "db_nutrient_keys" not in st.session_state:
    st.session_state.db_nutrient_keys = {
        "price": {"label": "ราคากลาง (บาท/กก.)", "step": 0.1, "default": 0.0},
        "protein": {"label": "โปรตีนดิบ (% CP)", "step": 0.1, "default": 0.0},
        "me": {"label": "พลังงานใช้ประโยชน์ได้ (ME kcal/kg)", "step": 10.0, "default": 0.0},
        "calcium": {"label": "แคลเซียม (% Ca)", "step": 0.01, "default": 0.0},
        "phos": {"label": "ฟอสฟอรัสเป็นประโยชน์ (% Avail. P)", "step": 0.01, "default": 0.0},
    }

# ==========================================
# 🔄 REAL-TIME DATABASE FETCH (NEW TARGET TABLES)
# ==========================================

# 1. ฟังก์ชันดึงข้อมูลวัตถุดิบ (ตาราง: db_ingredients)
def fetch_ingredients_from_supabase():
    try:
        response = supabase.table("db_ingredients").select("*").execute()
        if response.data:
            ingredients_dict = {}
            for item in response.data:
                name_key = item.get("name")
                if name_key:
                    ingredients_dict[name_key] = {
                        "name": name_key,
                        "price": float(item.get("price") or 0.0),
                        "protein": float(item.get("protein") or 0.0),
                        "me": float(item.get("me") or 0.0),
                        "calcium": float(item.get("calcium") or 0.0),
                        "phos": float(item.get("phos") or 0.0)
                    }
            return ingredients_dict
    except Exception:
        pass
    return {
        "ข้าวโพดบด": {"name": "ข้าวโพดบด", "price": 12.5, "protein": 8.5, "me": 3370.0, "calcium": 0.02, "phos": 0.28},
        "กากถั่วเหลือง": {"name": "กากถั่วเหลือง", "price": 22.0, "protein": 44.0, "me": 2240.0, "calcium": 0.29, "phos": 0.65},
        "รำละเอียด": {"name": "รำละเอียด", "price": 10.5, "protein": 12.0, "me": 2860.0, "calcium": 0.07, "phos": 1.35},
        "เปลือกหอยบด": {"name": "เปลือกหอยบด", "price": 5.0, "protein": 0.0, "me": 0.0, "calcium": 38.0, "phos": 0.04}
    }

# 2. ฟังก์ชันดึงข้อมูลกลุ่มไก่ไข่ (ตาราง: db_groups)
def fetch_groups_from_supabase():
    try:
        response = supabase.table("db_groups").select("*").execute()
        if response.data:
            return response.data
    except Exception:
        pass
    return [{"id": 1, "group_name": "สายพันธุ์ไก่ไข่คอมเมอร์เชียล (อุตสาหกรรม)"}]

# 3. ฟังก์ชันดึงข้อมูลสายพันธุ์ย่อย (ตาราง: db_breeds)
def fetch_breeds_from_supabase():
    try:
        response = supabase.table("db_breeds").select("*").execute()
        if response.data:
            return response.data
    except Exception:
        pass
    return [{"id": 1, "breed_name": "Hy-Line Brown", "group_name": "สายพันธุ์ไก่ไข่คอมเมอร์เชียล (อุตสาหกรรม)", "default_feed": 115.0}]

# ==========================================
# 🧮 3. CORE AI SOLVER ENGINE
# ==========================================
def run_ai_solver(req_p, req_m, req_c, req_ph):
    prob = pulp.LpProblem("AI_First_Solver", pulp.LpMinimize)
    
    current_ingredients = fetch_ingredients_from_supabase()
    if not current_ingredients:
        return {}

    ing_vars = {}
    for name in current_ingredients.keys():
        ing_vars[name] = pulp.LpVariable(name, lowBound=0.0, upBound=1.0)
    
    s_p = pulp.LpVariable("s_p", lowBound=0)
    s_m = pulp.LpVariable("s_m", lowBound=0)
    s_c = pulp.LpVariable("s_c", lowBound=0)
    
    prob += pulp.lpSum([ing_vars[name] * float(current_ingredients[name]["price"]) for name in current_ingredients.keys()]) + 1000.0 * (s_p + s_m/100.0 + s_c), "Cost"
    prob += pulp.lpSum([ing_vars[name] for name in current_ingredients.keys()]) == 1.0, "Weight"
    
    prob += pulp.lpSum([ing_vars[name] * float(current_ingredients[name]["protein"]) for name in current_ingredients.keys()]) + s_p >= req_p
    prob += pulp.lpSum([ing_vars[name] * float(current_ingredients[name]["me"]) for name in current_ingredients.keys()]) + s_m >= req_m
    prob += pulp.lpSum([ing_vars[name] * float(current_ingredients[name]["calcium"]) for name in current_ingredients.keys()]) + s_c >= req_c
    prob += pulp.lpSum([ing_vars[name] * float(current_ingredients[name]["phos"]) for name in current_ingredients.keys()]) >= req_ph
    
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    
    res = {}
    for name in current_ingredients.keys():
        res[name] = round((ing_vars[name].varValue if ing_vars[name].varValue is not None else 0.0) * 100.0, 1)
    return res

# ==========================================
# 🔒 4. SECURITY GATEWAY (SUPABASE AUTH)
# ==========================================
if not st.session_state.is_authenticated:

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
                try:
                    auth_res = supabase.auth.sign_in_with_password({
                        "email": email_login, "password": pass_login
                    })
                    if auth_res.user:
                        st.session_state.is_authenticated = True
                        st.session_state.current_user_key = email_login
                        st.session_state.user_role = "admin" if email_login.lower() == "222@gmail.com" else "user"
                        st.session_state.user_email = f"{email_login.split('@')[0]} [{st.session_state.user_role.upper()}]"
                        st.success("🎉 เข้าสู่ระบบสำเร็จ")
                        st.rerun()
                except Exception:
                    st.error("❌ อีเมลหรือรหัสผ่านไม่ถูกต้อง หรือยังไม่ได้ยืนยันอีเมล")

        with col_btn2:
            if st.button("🆕 สมัครสมาชิกใหม่ที่นี่", use_container_width=True):
                st.session_state.auth_page_mode = "signup"
                st.rerun()

        st.markdown("<div style='text-align: center; margin-top: 15px;'>", unsafe_allow_html=True)
        if st.button("❓ ลืมรหัสผ่านใช่หรือไม่?", type="secondary"):
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
            if is_strong: st.success(pass_msg)
            else: st.warning(pass_msg)

        col_su1, col_su2 = st.columns(2)
        with col_su1:
            if st.button("✅ ยืนยันการลงทะเบียน", type="primary", use_container_width=True):
                if su_email and su_pass and su_name and su_tel:
                    if su_pass != su_pass_conf:
                        st.error("❌ รหัสผ่านที่ยืนยัน ไม่ตรงกับรหัสผ่านตั้งต้น!")
                    elif not is_strong:
                        st.error("❌ รหัสผ่านไม่ปลอดภัยตามมาตรฐาน")
                    else:
                        try:
                            supabase.auth.sign_up({
                                "email": su_email, "password": su_pass,
                                "options": {"data": {"first_name": su_name, "last_name": su_surname, "phone": su_tel, "role": "user"}}
                            })
                            st.success("🎉 ลงทะเบียนสำเร็จ! กรุณาตรวจสอบอีเมลของคุณเพื่อยืนยัน")
                            st.session_state.auth_page_mode = "login"
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

    # --- 4.3 หน้า FORGOT PASSWORD ---
    elif st.session_state.auth_page_mode == "forgot":
        st.markdown("<div class='content-card' style='max-width: 550px; margin: 60px auto 0 auto;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #f43f5e !important;'>🔑 กู้คืนและตั้งรหัสผ่านใหม่</h2>", unsafe_allow_html=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)

        fg_email = st.text_input("📧 ป้อนอีเมลที่ลงทะเบียนไว้:")
        st.info("🎯 ระบบจะส่งลิงก์สำหรับรีเซ็ตรหัสผ่านไปยังอีเมลของคุณโดยตรง")

        if st.button("📨 ส่งลิงก์กู้คืนรหัสผ่าน", type="primary", use_container_width=True):
            if fg_email:
                try:
                    supabase.auth.reset_password_for_email(fg_email)
                    st.success("🚀 ส่งข้อมูลกู้คืนเรียบร้อยแล้ว!")
                except Exception as error:
                    st.error(f"❌ เกิดข้อผิดพลาด: {error}")
            else:
                st.warning("⚠️ กรุณากรอกอีเมล")

        if st.button("⬅️ ยกเลิกและกลับหน้าเข้าสู่ระบบ", use_container_width=True):
            st.session_state.auth_page_mode = "login"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

# ==========================================
# 👑 5. MAIN APPLICATION INTERFACE (POST-AUTH)
# ==========================================
else:
    # เรียกโหลดข้อมูลรอบเดียวและเก็บลง Session State จากโครงสร้างตารางใหม่ภาษาอังกฤษ
    if "db_groups_data" not in st.session_state:
        st.session_state.db_groups_data = fetch_groups_from_supabase()
        st.session_state.db_breeds_data = fetch_breeds_from_supabase()
        st.session_state.db_ingredients_data = fetch_ingredients_from_supabase()
        try:
            st.session_state.saved_formulas = supabase.table("saved_formulas").select("*").execute().data or []
            st.session_state.daily_logs = supabase.table("daily_logs").select("*").execute().data or []
        except Exception:
            pass

    # หัวระบบระบุผู้ใช้งานปัจจุบัน
    st.markdown(f"<div style='text-align: right; padding-right: 15px; color: #cbd5e1;'>👤 ผู้ใช้งาน: <b>{st.session_state.user_email}</b></div>", unsafe_allow_html=True)

    page_tabs = st.tabs(["🥣 1. สูตรอาหาร & คลังสูตร", "💰 2. บันทึกรายวันฟาร์ม", "📊 3. ใบสั่งผสมอาหาร"])

    # --- TAB 1: บันทึกสูตรและการคำนวณสูตรอาหาร ---
    with page_tabs[0]:
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("### 🐔 เลือกกลุ่มและสายพันธุ์ไก่ไข่")
        col_br1, col_br2, col_br3 = st.columns(3)
        with col_br1:
            g_options = [g["group_name"] for g in st.session_state.db_groups_data]
            selected_g = st.selectbox("📁 กลุ่มสายพันธุ์หลัก:", g_options if g_options else ["ทั่วไป"])
        with col_br2:
            b_options = [b["breed_name"] for b in st.session_state.db_breeds_data if b.get("group_name") == selected_g]
            selected_b_name = st.selectbox("🐔 สายพันธุ์ไก่ไข่:", b_options if b_options else ["ทั่วไป"])
        with col_br3:
            selected_stage = st.selectbox("📋 ช่วงระยะการให้ไข่:", ["ระยะเริ่มไข่ (18-20 สัปดาห์)", "ระยะให้ไข่พีค (21-40 สัปดาห์)", "ระยะไข่ท้ายชุด"])
        st.markdown("</div>", unsafe_allow_html=True)

        col_left, col_right = st.columns([1.1, 0.9])
        with col_left:
            st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
            st.markdown("### 🥣 กำหนดเป้าหมายสารอาหารเพื่อคำนวณ")
            p_target = st.number_input("โปรตีนเป้าหมาย (%):", value=16.5, step=0.1)
            m_target = st.number_input("พลังงานเป้าหมาย (kcal/kg):", value=2750.0, step=50.0)
            c_target = st.number_input("แคลเซียมเป้าหมาย (%):", value=3.8, step=0.1)
            ph_target = st.number_input("ฟอสฟอรัสเป้าหมาย (%):", value=0.45, step=0.05)

            if st.button("⚡ สั่ง AI คำนวณสูตรอาหารอัตโนมัติ (Linear Programming)", type="primary", use_container_width=True):
                res_weights = run_ai_solver(p_target, m_target, c_target, ph_target)
                if res_weights: 
                    st.session_state.current_weights = res_weights
                    st.success("🤖 คำนวณสูตรที่ต้นทุนต่ำที่สุดให้สำเร็จแล้ว!")
                    st.rerun()
            
            st.markdown("#### 🌾 สัดส่วนวัตถุดิบในสูตรสัตว์ (%)")
            for name, nutr in st.session_state.db_ingredients_data.items():
                curr_w = st.session_state.current_weights.get(name, 0.0)
                st.session_state.current_weights[name] = st.slider(f"🌽 {name} (ราคา {nutr['price']} บาท/กก.)", 0.0, 100.0, float(curr_w), step=0.1)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_right:
            st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
            st.markdown("### 🧪 ผลวิเคราะห์โภชนาการจริงในเล้า")
            
            # คำนวณสัดส่วนสารอาหารและต้นทุนตามข้อมูลจริงใน Slider
            total_w = sum(st.session_state.current_weights.values()) or 1.0
            act_p, act_m, act_c, act_ph, net_cost = 0.0, 0.0, 0.0, 0.0, 0.0
            for name, w in st.session_state.current_weights.items():
                if name in st.session_state.db_ingredients_data:
                    ratio = w / total_w
                    ing = st.session_state.db_ingredients_data[name]
                    act_p += ratio * ing["protein"]
                    act_m += ratio * ing["me"]
                    act_c += ratio * ing["calcium"]
                    act_ph += ratio * ing["phos"]
                    net_cost += ratio * ing["price"]

            res_df = pd.DataFrame([
                {"สารอาหาร": "โปรตีนดิบ (% CP)", "เป้าหมาย": f"{p_target}%", "ค่าจริงในสูตร": f"{act_p:.2f}%"},
                {"สารอาหาร": "พลังงาน (ME kcal/kg)", "เป้าหมาย": f"{m_target}", "ค่าจริงในสูตร": f"{act_m:.0f}"},
                {"สารอาหาร": "แคลเซียม (% Ca)", "เป้าหมาย": f"{c_target}%", "ค่าจริงในสูตร": f"{act_c:.2f}%"},
                {"สารอาหาร": "ฟอสฟอรัสเป็นประโยชน์ (% P)", "เป้าหมาย": f"{ph_target}%", "ค่าจริงในสูตร": f"{act_ph:.2f}%"}
            ])
            st.dataframe(res_df, use_container_width=True, hide_index=True)
            st.markdown(f"### 💰 ต้นทุนสุทธิ: {net_cost:.2f} บาท / กิโลกรัม")
            
            f_name = st.text_input("💾 ตั้งชื่อสูตรนี้เพื่อบันทึก:", f"สูตรผสมไก่ไข่-{selected_b_name}")
            if st.button("📥 บันทึกสูตรนี้เข้าคลังฐานข้อมูล"):
                try:
                    supabase.table("saved_formulas").insert({
                        "name": f_name, "breed": selected_b_name, "stage": selected_stage,
                        "cost": round(net_cost, 2), "weights": st.session_state.current_weights, "date": str(datetime.date.today())
                    }).execute()
                    st.success("บันทึกข้อมูลเข้าสู่ตาราง saved_formulas เรียบร้อย!")
                except Exception as e:
                    st.error(f"ไม่สามารถบันทึกข้อมูลได้: {e}")
            st.markdown("</div>", unsafe_allow_html=True)

    # --- TAB 2: บันทึกข้อมูลรายวันฟาร์ม ---
    with page_tabs[1]:
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("### 📝 บันทึกข้อมูลประสิทธิภาพฟาร์มประจำวัน (`daily_logs`)")
        col_l1, col_l2 = st.columns(2)
        with col_l1:
            log_date = st.date_input("เลือกวันที่บันทึก:", datetime.date.today())
            f_age = st.number_input("🐣 อายุฝูงไก่ (สัปดาห์):", min_value=1, value=22)
            b_count = st.number_input("จำนวนแม่ไก่ทั้งหมดในเล้า (ตัว):", min_value=1, value=1000)
        with col_l2:
            eggs = st.number_input("จำนวนไข่ที่เก็บได้จริง (ฟอง):", min_value=0, value=880)
            f_given = st.number_input("ปริมาณอาหารที่ให้ทั้งหมด (กก.):", min_value=1.0, value=115.0)

        if st.button("💾 บันทึกข้อมูลรายวันด่วนลงฐานข้อมูล"):
            try:
                supabase.table("daily_logs").insert({
                    "date": str(log_date), "flock_age_weeks": int(f_age), "bird_count": int(b_count),
                    "collected_eggs": int(eggs), "actual_feed_given_kg": float(f_given)
                }).execute()
                st.success("บันทึกข้อมูลเข้าตาราง daily_logs เรียบร้อยแล้ว!")
            except Exception as e:
                st.error(f"ไม่สามารถบันทึกได้: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

    # --- TAB 3: ใบสั่งผสมอาหาร ---
    with page_tabs[2]:
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("### 📊 ใบสั่งงานตักผสมอาหารสัตว์สำหรับหน้างาน")
        total_kg = st.number_input("📦 น้ำหนักรวมที่ต้องการผสมรอบนี้ (กิโลกรัม):", min_value=100, value=1000, step=100)
        
        mix_data = []
        total_w = sum(st.session_state.current_weights.values()) or 1.0
        for name, w_pct in st.session_state.current_weights.items():
            pct = (w_pct / total_w) * 100.0
            if pct > 0:
                calc_kg = (pct / 100.0) * total_kg
                mix_data.append({"วัตถุดิบ": name, "สัดส่วน (%)": f"{pct:.1f}%", "น้ำหนักที่ต้องใช้ (KG)": round(calc_kg, 1)})
        
        if mix_data: 
            st.dataframe(pd.DataFrame(mix_data), use_container_width=True, hide_index=True)
        else:
            st.info("💡 ยังไม่มีข้อมูลวัตถุดิบในสูตรอาหาร กรุณาคำนวณหรือปรับสัดส่วนในแท็บที่ 1 ก่อนครับ")
        st.markdown("</div>", unsafe_allow_html=True)
# ==========================================
# 👑 5. MAIN APPLICATION INTERFACE (หลังผ่าน Login)
# ==========================================
    # เคลียร์และโหลด Data จากตารางใหม่ล่าสุดเข้า Session State
    if "db_groups" not in st.session_state or st.button("🔄 อัปเดตข้อมูลจากฐานข้อมูล"):
        try:
            st.session_state.db_groups = fetch_groups_from_supabase()
            st.session_state.db_breeds = fetch_breeds_from_supabase()
            st.session_state.db_ingredients = fetch_ingredients_from_supabase()
            
            user_id_now = st.session_state.get("current_user_key", "")
            res_formulas = supabase.table("saved_formulas").select("*").execute()
            st.session_state.saved_formulas = res_formulas.data if res_formulas.data else []

            res_logs = supabase.table("daily_logs").select("*").execute()
            st.session_state.daily_logs = res_logs.data if res_logs.data else []
        except Exception as e:
            st.error(f"⚠️ เกิดปัญหาระหว่างอัปเดตตารางฐานข้อมูล: {e}")

    # ตั้งค่าตัวแปรสูตรอาหารพื้นฐาน
    if "edit_p" not in st.session_state: st.session_state.edit_p = 16.5
    if "edit_m" not in st.session_state: st.session_state.edit_m = 2750.0
    if "edit_c" not in st.session_state: st.session_state.edit_c = 3.8
    if "edit_ph" not in st.session_state: st.session_state.edit_ph = 0.45

    user_id_now = st.session_state.get("current_user_key", "")
    my_formulas = [f for f in st.session_state.get("saved_formulas", []) if str(f.get("user_id")) == str(user_id_now) or not f.get("user_id")]

    if not my_formulas:
        mock_weights = {k: (100.0 / len(st.session_state.db_ingredients)) for k in st.session_state.db_ingredients.keys()} if st.session_state.db_ingredients else {"ข้าวโพดบด": 100.0}
        my_formulas = [{"id": 0, "name": "สูตรมาตรฐานฟาร์ม (สำรอง)", "date": str(datetime.date.today()), "breed": "ทั่วไป", "stage": "ระยะไข่", "weights": mock_weights, "cost": 12.50}]

    if not st.session_state.current_weights and st.session_state.db_ingredients:
        st.session_state.current_weights = {k: 0.0 for k in st.session_state.db_ingredients.keys()}

    # คำนวณต้นทุนรวมของสูตรปัจจุบัน
    net_cost = 0.0
    if st.session_state.current_weights:
        total_w = sum(st.session_state.current_weights.values())
        divisor = total_w if total_w > 0 else 1.0
        for name, w in st.session_state.current_weights.items():
            if name in st.session_state.db_ingredients:
                net_cost += (w / divisor) * st.session_state.db_ingredients[name]["price"]

    # NAVIGATION TABS
    page_tabs = st.tabs(["🥣 1. สูตรอาหาร & คลังสูตรเก่า", "💰 2. บันทึกรายวัน & บัญชีฟาร์ม", "📊 3. ใบสั่งผสมอาหาร (สำหรับคนงาน)"])

    # ------------------------------------------
    # TAB 1: FORMULA MANAGEMENT
    # ------------------------------------------
    with page_tabs[0]:
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("### 📂 เรียกใช้หรือลบสูตรอาหารเก่าในคลัง")
        col_load1, col_load2 = st.columns([6, 4])
        with col_load1:
            formula_labels = [f"{idx+1}. {f.get('name', 'ไม่ระบุชื่อ')} ({f.get('date', '-')})" for idx, f in enumerate(my_formulas)]
            selected_label = st.selectbox("🔍 ค้นหาและเลือกชื่อสูตรอาหาร:", formula_labels)
            target_formula = my_formulas[formula_labels.index(selected_label)]
        with col_load2:
            st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
            cb1, cb2 = st.columns(2)
            with cb1:
                if st.button("🔄 ดึงสูตรมาใช้", use_container_width=True):
                    raw_w = target_formula.get("weights", {})
                    st.session_state.current_weights = raw_w if isinstance(raw_w, dict) else {}
                    st.rerun()
            with cb2:
                if st.button("❌ ลบสูตรนี้", use_container_width=True) and target_formula.get("id") != 0:
                    supabase.table("saved_formulas").delete().eq("id", target_formula.get("id")).execute()
                    st.success("ลบสูตรสำเร็จ!")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("### 🐓 เลือกสายพันธุ์และกลุ่มไก่ไข่")
        col_br1, col_br2, col_br3 = st.columns(3)
        with col_br1:
            group_options = [g["group_name"] for g in st.session_state.get("db_groups", [])]
            selected_g = st.selectbox("📁 เลือกกลุ่มสายพันธุ์หลัก:", group_options if group_options else ["ทั่วไป"])
        with col_br2:
            breed_options = [b["breed_name"] for b in st.session_state.get("db_breeds", []) if b.get("group_name") == selected_g]
            selected_b_name = st.selectbox("🐔 เลือกสายพันธุ์ไก่ไข่:", breed_options if breed_options else ["ทั่วไป"])
            
            breed_data = next((b for b in st.session_state.get("db_breeds", []) if b.get("breed_name") == selected_b_name), {"default_feed": 115.0})
            st.session_state['current_breed_default_feed'] = float(breed_data.get("default_feed", 115.0))
        with col_br3:
            selected_stage_label = st.selectbox("📋 เลือกช่วงระยะการให้ไข่:", ["ระยะเริ่มไข่ (18-20 สัปดาห์)", "ระยะให้ไข่พีค (21-40 สัปดาห์)", "ระยะไข่ท้ายชุด (41 สัปดาห์ขึ้นไป)"])
            if "พีค" in selected_stage_label:
                st.session_state.edit_p, st.session_state.edit_m = 16.5, 2750.0
            elif "เริ่ม" in selected_stage_label:
                st.session_state.edit_p, st.session_state.edit_m = 17.0, 2800.0
            else:
                st.session_state.edit_p, st.session_state.edit_m = 15.5, 2700.0
        st.markdown("</div>", unsafe_allow_html=True)

        col_left, col_right = st.columns([1.1, 0.9])
        with col_left:
            st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
            st.markdown("### 🥣 ปรับค่าเป้าหมาย & สัดส่วนวัตถุดิบ (%)")
            
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                st.session_state.edit_p = st.number_input("🎯 โปรตีนเป้าหมาย (%):", value=float(st.session_state.edit_p), step=0.1)
                st.session_state.edit_m = st.number_input("🎯 พลังงานเป้าหมาย (kcal/kg):", value=float(st.session_state.edit_m), step=25.0)
            with t_col2:
                st.session_state.edit_c = st.number_input("🎯 แคลเซียมเป้าหมาย (%):", value=float(st.session_state.edit_c), step=0.05)
                st.session_state.edit_ph = st.number_input("🎯 ฟอสฟอรัสเป้าหมาย (%):", value=float(st.session_state.edit_ph), step=0.02)

            if st.button("⚡ สั่ง AI คำนวณสูตรด่วนตามเป้าหมายด้านบน", type="primary", use_container_width=True):
                computed = run_ai_solver(st.session_state.edit_p, st.session_state.edit_m, st.session_state.edit_c, st.session_state.edit_ph)
                if computed:
                    st.session_state.current_weights = computed
                    st.rerun()

            st.markdown("#### 🌾 ปรับสัดส่วนวัตถุดิบรายตัว (ตาราง db_ingredients)")
            temp_weights = {}
            running_total = 0.0
            
            if st.session_state.db_ingredients:
                for name, nutr in st.session_state.db_ingredients.items():
                    saved_w = float(st.session_state.current_weights.get(name, 0.0))
                    user_val = st.slider(f"🌽 {name} ({nutr['price']} บ./กก.)", 0.0, 100.0, saved_w, step=0.1, key=f"sld_{name}")
                    temp_weights[name] = user_val
                    running_total += user_val
                st.session_state.current_weights = temp_weights
            
            st.markdown(f"**สัดส่วนรวมปัจจุบัน:** {running_total:.1f}% " + ("🟢 ครบ 100%" if abs(running_total-100)<0.1 else "⚠️ ไม่ครบ 100%"))
            st.markdown("</div>", unsafe_allow_html=True)

        with col_right:
            st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
            st.markdown("### 🧪 ผลลัพธ์โภชนาการจริงในสูตร")
            
            act_nut = {"protein": 0.0, "me": 0.0, "calcium": 0.0, "phos": 0.0}
            total_w = sum(st.session_state.current_weights.values()) if st.session_state.current_weights else 0
            divisor = total_w if total_w > 0 else 1.0
            
            if st.session_state.current_weights and st.session_state.db_ingredients:
                for name, w in st.session_state.current_weights.items():
                    if name in st.session_state.db_ingredients:
                        ratio = w / divisor
                        for k in act_nut.keys():
                            act_nut[k] += ratio * st.session_state.db_ingredients[name][k]
                        
            comparison_table = [
                {"โภชนาการ": "โปรตีนดิบ (% CP)", "เป้าหมาย": f"{st.session_state.edit_p:.1f}%", "ได้จริง": f"{act_nut['protein']:.2f}%"},
                {"โภชนาการ": "พลังงานใช้ประโยชน์ (ME)", "เป้าหมาย": f"{st.session_state.edit_m:.0f}", "ได้จริง": f"{act_nut['me']:.0f}"},
                {"โภชนาการ": "แคลเซียม (% Ca)", "เป้าหมาย": f"{st.session_state.edit_c:.2f}%", "ได้จริง": f"{act_nut['calcium']:.2f}%"},
                {"โภชนาการ": "ฟอสฟอรัส (% P)", "เป้าหมาย": f"{st.session_state.edit_ph:.2f}%", "ได้จริง": f"{act_nut['phos']:.2f}%"}
            ]
            st.dataframe(pd.DataFrame(comparison_table), use_container_width=True, hide_index=True)
            st.markdown(f"### 💰 ต้นทุนสูตรนี้: {net_cost:.2f} บาท/กก.")
            
            save_name = st.text_input("💾 ชื่อเรียกสูตรอาหารเพื่อบันทึก:", f"สูตรผสม {selected_b_name}")
            if st.button("📥 ยืนยันบันทึกสูตรอาหารลง Supabase", use_container_width=True):
                new_f = {
                    "user_id": user_id_now if user_id_now else None, "date": str(datetime.date.today()), "name": save_name,
                    "cost": round(net_cost, 2), "breed": selected_b_name, "stage": selected_stage_label,
                    "protein": round(act_nut["protein"], 2), "me": round(act_nut["me"], 0), "calcium": round(act_nut["calcium"], 2),
                    "weights": st.session_state.current_weights
                }
                supabase.table("saved_formulas").insert(new_f).execute()
                st.success("บันทึกข้อมูลเข้าโครงสร้างตารางใหม่สำเร็จ!")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------
    # TAB 2: DAILY LOGS
    # ------------------------------------------
    with page_tabs[1]:
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("### ☀️ บันทึกตัวชี้วัดฟาร์มประจำวัน (`daily_logs`)")
        
        l_col1, l_col2 = st.columns(2)
        with l_col1:
            log_date = st.date_input("วันที่บันทึก:", datetime.date.today())
            flock_age = st.number_input("🐣 อายุฝูงไก่ปัจจุบัน (สัปดาห์):", min_value=1, value=25)
            bird_count = st.number_input("จำนวนไก่ในเล้าทั้งหมด (ตัว):", min_value=1, value=1000)
            env_temp = st.slider("🌡️ อุณหภูมิในเล้าวันนี้ (°C):", 15.0, 45.0, 28.0)
        with l_col2:
            collected_eggs = st.number_input("จำนวนฟองไข่ที่เก็บได้จริง (ฟอง):", min_value=0, value=850)
            egg_price = st.number_input("💵 ราคารับซื้อไข่หน้าฟาร์ม (บาท/ฟอง):", value=4.10)
            dead_birds = st.number_input("จำนวนไก่ตาย/คัดทิ้งวันนี้ (ตัว):", value=1)
            avg_egg_w = st.number_input("⚖️ น้ำหนักไข่เฉลี่ย (กรัม/ฟอง):", value=62.0)
            actual_feed = st.number_input("🍽️ อาหารที่ใช้เลี้ยงวันนี้ (กิโลกรัม):", value=float(bird_count * st.session_state.get('current_breed_default_feed', 115.0)/1000.0))

        if st.button("💾 บันทึกประวัติรายวันลงฐานข้อมูล", use_container_width=True):
            new_log = {
                "user_id": user_id_now if user_id_now else None, "date": str(log_date), "flock_age_weeks": int(flock_age),
                "bird_count": int(bird_count), "env_temp": float(env_temp), "actual_feed_given_kg": float(actual_feed),
                "collected_eggs": int(collected_eggs), "egg_sale_price": float(egg_price), "dead_birds": int(dead_birds),
                "avg_egg_weight_g": float(avg_egg_w)
            }
            supabase.table("daily_logs").insert(new_log).execute()
            st.success("บันทึกข้อมูลรายวันสำเร็จ!")
            st.rerun()

        if st.session_state.get("daily_logs"):
            st.markdown("### 📋 ตารางประวัติฟาร์มย้อนหลัง")
            st.dataframe(pd.DataFrame(st.session_state.daily_logs), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------
    # TAB 3: WORKER SHEET
    # ------------------------------------------
    with page_tabs[2]:
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("### 📊 ใบสั่งงานผสมอาหารสัตว์ (สำหรับคนงาน)")
        total_tonnage = st.number_input("📦 จำนวนกิโลกรัมรวมที่ต้องการผสมรอบนี้ (KG):", min_value=100, value=1000, step=100)
        
        po_buffer = []
        total_w = sum(st.session_state.current_weights.values()) if st.session_state.current_weights else 0
        divisor = total_w if total_w > 0 else 1.0
        
        if st.session_state.current_weights:
            for name, w_pct in st.session_state.current_weights.items():
                pct = (w_pct / divisor) * 100.0
                if pct > 0.01:
                    w_kg = (pct / 100.0) * total_tonnage
                    bags = int(w_kg // 50)
                    rem_kg = w_kg % 50
                    bag_txt = f"ยก {bags} กระสอบ + ตักเศษ {rem_kg:.1f} กก." if bags > 0 else f"ตักเศษสุทธิ {rem_kg:.1f} กิโลกรัม"
                    
                    po_buffer.append({"รายการวัตถุดิบ": name, "สัดส่วน (%)": round(pct, 1), "น้ำหนักที่ต้องตัก (KG)": round(w_kg, 1), "📢 วิธีตักหน้างาน": bag_txt})
                
        if po_buffer:
            df_po = pd.DataFrame(po_buffer)
            st.dataframe(df_po, use_container_width=True, hide_index=True)
            
            csv_s = io.StringIO()
            df_po.to_csv(csv_s, index=False, encoding='utf-8-sig')
            st.download_button("📥 ดาวน์โหลดใบสั่งงานเป็นไฟล์ CSV", data=csv_s.getvalue(), file_name=f"ใบสั่งผสมอาหาร_{total_tonnage}กก.csv", mime="text/csv", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

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

# =====================================================================
# 🛠️ 6. MAIN ROUTER & DASHBOARD INTERFACE (UX/UI PREMIUM VERSION)
# =====================================================================
if st.session_state.user_role == "admin":
    st.title("💻 Admin Master Data Control")
    st.caption("ระบบจัดการโครงสร้างสารอาหาร วัตถุดิบ สายพันธุ์ และผู้ใช้งานแบบ Dynamic ตรงสู่ Supabase คลาวด์")
    
    admin_tabs = st.tabs([
        "⚙️ ตั้งค่าหัวข้อสารอาหาร",
        "🌽 คลังวัตถุดิบ & สารอาหาร", 
        "🐓 ทำเนียบสายพันธุ์ไก่ไข่", 
        "🧬 เกณฑ์โภชนาการตามช่วงอายุ", 
        "👤 การจัดการสิทธิ์ผู้ใช้งาน"
    ])
    
    # --- แท็บที่ 0: เพิ่ม/ลบ สารอาหารด้วยตัวเอง (ตาราง โครงสร้างสารอาหาร_nutrient_keys) ---
    with admin_tabs[0]:
        st.subheader("⚙️ สารอาหารที่มีในระบบปัจจุบัน")
        
        # ดึงข้อมูลโครงสร้างสารอาหารแบบ Real-time จาก Supabase ภาษาไทย
        try:
            res_nut = supabase.table("โครงสร้างสารอาหาร_nutrient_keys").select("*").order("id").execute()
            db_nut_keys = {item["key"]: {"label": item["label"], "step": item["step"], "default": item["default"]} for item in res_nut.data} if res_nut.data else {}
        except Exception as e:
            st.error(f"❌ ไม่สามารถดึงโครงสร้างสารอาหารจาก Supabase ได้: {e}")
            db_nut_keys = {}

        with st.expander("📊 ดูโครงสร้างสารอาหารที่ใช้งานอยู่ทั้งหมด", expanded=True):
            if db_nut_keys:
                df_nutrients = pd.DataFrame([
                    {"รหัสระบบ (Key)": k, "ชื่อตัวชี้วัด (Label)": v["label"], "ความละเอียด (Step)": v["step"]} 
                    for k, v in db_nut_keys.items()
                ])
                st.dataframe(df_nutrients, use_container_width=True, hide_index=True)
            else:
                st.info("💡 ปัจจุบันยังไม่มีโครงสร้างหัวข้อสารอาหารในฐานข้อมูล")
        
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
                    elif new_nut_key in db_nut_keys or new_nut_key in ["name", "min_limit", "max_limit"]:
                        st.error("❌ รหัสนี้ซ้ำหรือเป็นคำต้องห้ามของระบบ")
                    else:
                        try:
                            supabase.table("โครงสร้างสารอาหาร_nutrient_keys").insert({
                                "key": new_nut_key,
                                "label": new_nut_label,
                                "step": new_nut_step,
                                "default": 0.0
                            }).execute()
                            st.success(f"🎉 เพิ่มโครงสร้างหัวข้อสารอาหาร '{new_nut_label}' ลงเซิร์ฟเวอร์เรียบร้อยแล้ว!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ ไม่สามารถบันทึกข้อมูลลง Supabase ได้: {e}")
                        
        with n_col2:
            st.markdown("### ❌ ลบสารอาหาร")
            with st.container(border=True):
                removable_keys = [k for k in db_nut_keys.keys() if k != "price"]
                
                if removable_keys:
                    nut_to_del = st.selectbox("เลือกสารอาหารที่ต้องการถอดถอน:", removable_keys, format_func=lambda x: db_nut_keys[x]["label"], key="del_nut_select")
                    st.markdown("<br><br><br>", unsafe_allow_html=True)
                    
                    if st.button("🗑️ ยืนยันลบออกจากระบบถาวร", type="secondary", use_container_width=True):
                        try:
                            supabase.table("โครงสร้างสารอาหาร_nutrient_keys").delete().eq("key", nut_to_del).execute()
                            st.success(f"🔥 ลบสารอาหาร '{db_nut_keys[nut_to_del]['label']}' ออกจาก Supabase สำเร็จ")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ ไม่สามารถลบข้อมูลออกจากเซิร์ฟเวอร์ได้: {e}")
                else:
                    st.warning("⚠️ ไม่มีสารอาหารอื่นนอกเหนือจากราคาที่สามารถลบได้")

    # --- แท็บที่ 1: จัดการและแก้ไขวัตถุดิบ/สารอาหาร (ตาราง คลังวัตถุดิบไก่ไข่_layer_ingredients) ---
    with admin_tabs[1]:
        current_db_ingredients = fetch_ingredients_from_supabase()
        
        with st.expander("📊 เปิดดูคลังวัตถุดิบและราคาปัจจุบันในระบบ", expanded=False):
            if current_db_ingredients:
                st.dataframe(pd.DataFrame.from_dict(current_db_ingredients, orient='index'), use_container_width=True)
            else:
                st.info("💡 ขณะนี้ไม่มีข้อมูลวัตถุดิบในระบบ กรุณาเลือกฟังก์ชัน '➕ เพิ่มวัตถุดิบใหม่' ด้านล่าง")
            
        crud_mode = st.segmented_control(
            "เลือกฟังก์ชันจัดการคลังวัตถุดิบ:", 
            ["✏️ แก้ไขข้อมูลวัตถุดิบเดิม", "➕ เพิ่มวัตถุดิบใหม่", "🗑️ ลบวัตถุดิบออก"],
            default="✏️ แก้ไขข้อมูลวัตถุดิบเดิม"
        )
        st.markdown("---")

        if crud_mode == "✏️ แก้ไขข้อมูลวัตถุดิบเดิม":
            if not current_db_ingredients:
                st.warning("⚠️ ไม่สามารถแก้ไขได้ เนื่องจากยังไม่มีข้อมูลวัตถุดิบใดๆ ในระบบ")
            else:
                ingredient_options = list(current_db_ingredients.keys())
                selected_ing_edit = st.selectbox("เลือกวัตถุดิบที่จะปรับปรุงข้อมูล:", ingredient_options)
                target_ing = current_db_ingredients.get(selected_ing_edit, {})
                
                if target_ing:
                    with st.form(key=f"form_edit_{selected_ing_edit}"):
                        st.markdown(f"#### 📝 แก้ไขข้อมูลสารอาหารของ: **{selected_ing_edit}**")
                        
                        # เพิ่มหมวดหมู่เพื่อให้ครบถ้วนตามโครงสร้าง DB ภาษาไทยใหม่
                        edit_category = st.text_input("หมวดหมู่วัตถุดิบ (Category):", value=str(target_ing.get("category", "วัตถุดิบทั่วไป")))
                        
                        c_limits = st.columns(2)
                        with c_limits[0]:
                            # ตารางไทยเก็บเป็นเปอร์เซ็นต์ (สัดส่วนขั้นต่ำ_min_limit และ สัดส่วนสูงสุด_max_limit)
                            edit_ing_min = st.number_input("สัดส่วนขั้นต่ำที่ต้องใช้ในสูตร (% Min):", min_value=0.0, max_value=100.0, value=float(target_ing.get("min_limit", 0.0)), step=0.1)
                        with c_limits[1]:
                            edit_ing_max = st.number_input("สัดส่วนสูงสุดที่ห้ามเกินในสูตร (% Max):", min_value=0.0, max_value=100.0, value=float(target_ing.get("max_limit", 100.0)), step=0.1)
                        
                        st.markdown("**📊 ค่าโภชนาการและสารอาหาร**")
                        
                        ec = st.columns(3)
                        # แมปและอัปเดตค่าเข้ากับฟิลด์ของตารางภาษาไทยใหม่
                        with ec[0]:
                            edit_price = st.number_input("ราคา_price (บาท/กก.):", min_value=0.0, value=float(target_ing.get("price", 0.0)), step=0.1)
                            edit_protein = st.number_input("โปรตีนดิบ_protein (%):", min_value=0.0, value=float(target_ing.get("protein", 0.0)), step=0.1)
                            edit_me = st.number_input("พลังงานใช้ประโยชน์ได้_me_kcal (kcal/kg):", min_value=0.0, value=float(target_ing.get("me", 0.0)), step=10.0)
                        with ec[1]:
                            edit_calcium = st.number_input("แคลเซียม_calcium (%):", min_value=0.0, value=float(target_ing.get("calcium", 0.0)), step=0.01)
                            edit_phosphorus = st.number_input("ฟอสฟอรัสที่ใช้ได้_phosphorus (%):", min_value=0.0, value=float(target_ing.get("phos", 0.0)), step=0.01)
                            edit_fiber = st.number_input("เยื่อใยดิบ_fiber (%):", min_value=0.0, value=float(target_ing.get("fiber", 0.0)), step=0.1)
                        with ec[2]:
                            edit_lysine = st.number_input("ไลซีน_lysine (%):", min_value=0.0, value=float(target_ing.get("lysine", 0.0)), step=0.01)
                            edit_methionine = st.number_input("เมทิโอนีน_methionine (%):", min_value=0.0, value=float(target_ing.get("methionine", 0.0)), step=0.01)

                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.form_submit_button("💾 บันทึกการเปลี่ยนแปลงทั้งหมดไปยัง Supabase", type="primary", use_container_width=True):
                            if edit_ing_min > edit_ing_max:
                                st.error("❌ ข้อผิดพลาด: สัดส่วนต่ำสุด (% Min) ห้ามมากกว่าสัดส่วนสูงสุด (% Max)")
                            else:
                                try:
                                    payload = {
                                        "หมวดหมู่_category": edit_category,
                                        "สัดส่วนขั้นต่ำ_min_limit": edit_ing_min,
                                        "สัดส่วนสูงสุด_max_limit": edit_ing_max,
                                        "ราคา_price": edit_price,
                                        "โปรตีนดิบ_protein": edit_protein,
                                        "พลังงานใช้ประโยชน์ได้_me_kcal": edit_me,
                                        "แคลเซียม_calcium": edit_calcium,
                                        "ฟอสฟอรัสที่ใช้ได้_phosphorus": edit_phosphorus,
                                        "ไลซีน_lysine": edit_lysine,
                                        "เมทิโอนีน_methionine": edit_methionine,
                                        "เยื่อใยดิบ_fiber": edit_fiber
                                    }
                                    supabase.table("คลังวัตถุดิบไก่ไข่_layer_ingredients").update(payload).eq("ชื่อวัตถุดิบ_name", selected_ing_edit).execute()
                                    st.success(f"🎉 ปรับปรุงข้อมูลสารอาหารของ '{selected_ing_edit}' บนคลาวด์เรียบร้อยแล้ว")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ ปรับปรุงข้อมูลล้มเหลว: {e}")

        elif crud_mode == "➕ เพิ่มวัตถุดิบใหม่":
            with st.form(key="form_add_new_ingredient"):
                st.markdown("#### ➕ ลงทะเบียนวัตถุดิบตัวใหม่เข้าคลังกลาง")
                ing_name = st.text_input("📝 ระบุชื่อวัตถุดิบใหม่:", placeholder="เช่น รำข้าวหอมมะลิบดละเอียด")
                new_category = st.text_input("📦 หมวดหมู่วัตถุดิบ:", placeholder="เช่น วัตถุดิบให้พลังงาน, แหล่งโปรตีน", value="ทั่วไป")
                
                c_limits = st.columns(2)
                with c_limits[0]:
                    ing_min = st.number_input("สัดส่วนขั้นต่ำที่ต้องใช้ในสูตร (% Min):", min_value=0.0, value=0.0)
                with c_limits[1]:
                    ing_max = st.number_input("สัดส่วนสูงสุดที่ห้ามเกินในสูตร (% Max):", min_value=0.0, value=100.0)
                
                st.markdown("**📊 ระบุสารอาหารตั้งต้น**")
                ac = st.columns(3)
                with ac[0]:
                    add_price = st.number_input("ราคากลาง (บาท/กก.):", min_value=0.0, value=0.0, step=0.1)
                    add_protein = st.number_input("โปรตีนดิบ (% CP):", min_value=0.0, value=0.0, step=0.1)
                    add_me = st.number_input("พลังงานใช้ประโยชน์ได้ (ME kcal/kg):", min_value=0.0, value=0.0, step=10.0)
                with ac[1]:
                    add_calcium = st.number_input("แคลเซียม (% Ca):", min_value=0.0, value=0.0, step=0.01)
                    add_phos = st.number_input("ฟอสฟอรัสเป็นประโยชน์ (% Avail. P):", min_value=0.0, value=0.0, step=0.01)
                    add_fiber = st.number_input("เยื่อใย (% Fiber):", min_value=0.0, value=0.0, step=0.1)
                with ac[2]:
                    add_lysine = st.number_input("อะมิโน ไลซีน (% Lys):", min_value=0.0, value=0.0, step=0.01)
                    add_methionine = st.number_input("อะมิโน เมทไธโอนีน (% Met):", min_value=0.0, value=0.0, step=0.01)
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("➕ บันทึกเพิ่มเข้าคลังสินค้ากลาง (Supabase)", type="primary", use_container_width=True):
                    ing_name_clean = ing_name.strip()
                    if not ing_name_clean:
                        st.error("❌ กรุณากรอกชื่อวัตถุดิบด้วยครับ")
                    elif ing_name_clean in current_db_ingredients:
                        st.error(f"❌ รายการ '{ing_name_clean}' มีในระบบอยู่แล้ว")
                    elif ing_min > ing_max:
                        st.error("❌ ข้อผิดพลาด: ค่าต่ำสุดห้ามมากกว่าค่าสูงสุด")
                    else:
                        try:
                            insert_data = {
                                "ชื่อวัตถุดิบ_name": ing_name_clean,
                                "หมวดหมู่_category": new_category,
                                "สัดส่วนขั้นต่ำ_min_limit": ing_min,
                                "สัดส่วนสูงสุด_max_limit": ing_max,
                                "ราคา_price": add_price,
                                "โปรตีนดิบ_protein": add_protein,
                                "พลังงานใช้ประโยชน์ได้_me_kcal": add_me,
                                "แคลเซียม_calcium": add_calcium,
                                "ฟอสฟอรัสที่ใช้ได้_phosphorus": add_phos,
                                "ไลซีน_lysine": add_lysine,
                                "เมทิโอนีน_methionine": add_methionine,
                                "เยื่อใยดิบ_fiber": add_fiber
                            }
                            supabase.table("คลังวัตถุดิบไก่ไข่_layer_ingredients").insert(insert_data).execute()
                            st.success(f"🎉 นำเข้า '{ing_name_clean}' สู่ฐานข้อมูล Supabase เรียบร้อย!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ ไม่สามารถเพิ่มวัตถุดิบใหม่ได้: {e}")

        elif crud_mode == "🗑️ ลบวัตถุดิบออก":
            st.markdown("#### 🗑️ ลบรายการวัตถุดิบ")
            if not current_db_ingredients:
                st.info("💡 ไม่มีข้อมูลวัตถุดิบในระบบให้ลบ")
            else:
                to_del = st.selectbox("เลือกวัตถุดิบที่จะนำออกจากระบบถาวร:", list(current_db_ingredients.keys()))
                if st.button("🗑️ ยืนยันคำสั่งลบวัตถุดิบออกจากระบบคลาวด์", type="primary", use_container_width=True):
                    try:
                        supabase.table("คลังวัตถุดิบไก่ไข่_layer_ingredients").delete().eq("ชื่อวัตถุดิบ_name", to_del).execute()
                        st.success(f"🔥 ลบ '{to_del}' ออกจากระบบฐานข้อมูลเรียบร้อย")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ ลบล้มเหลว: {e}")
                        
    # --- แท็บที่ 2: จัดการทำเนียบสายพันธุ์ (ตาราง สายพันธุ์ไก่ไข่_layer_breeds & กลุ่มไก่_chicken_categories) ---
    with admin_tabs[2]:
        db_breeds = fetch_breeds_from_supabase()
        db_groups = fetch_groups_from_supabase()

        with st.expander("📊 เปิดดูทำเนียบสายพันธุ์ไก่ไข่ในระบบทั้งหมด", expanded=True):
            if db_breeds:
                # แปลงหัวข้อแสดงผลให้อ่านง่ายสอดคล้องตารางภาษาไทย
                df_breeds_show = pd.DataFrame(db_breeds).rename(columns={
                    "กลุ่มสายพันธุ์_group_name": "กลุ่มสายพันธุ์",
                    "ชื่อสายพันธุ์_breed_name": "ชื่อสายพันธุ์สัตว์",
                    "สีเปลือกไข่_egg_shell_color": "ลักษณะเปลือกไข่",
                    "ปริมาณอาหารที่กิน_feed_intake_g": "ปริมาณกินตามคู่มือ (กรัม/วัน)"
                })
                st.dataframe(df_breeds_show, use_container_width=True, hide_index=True)
            else:
                st.info("💡 ขณะนี้ไม่มีข้อมูลสายพันธุ์ในระบบ")
            
        st.markdown("---")
        bc1, bc2 = st.columns(2, gap="large")
        
        with bc1:
            st.markdown("### ➕ เพิ่มสายพันธุ์ใหม่")
            with st.container(border=True):
                group_options = [g.get("ชื่อกลุ่ม_group_name", "Unknown") for g in db_groups] if db_groups else ["ไม่มีกลุ่มสายพันธุ์"]
                b_group = st.selectbox("กลุ่มสายพันธุ์หลัก:", group_options)
                b_name = st.text_input("ชื่อทางการค้า (Breed Name):", placeholder="เช่น ไฮ-เซ็กซ์ บราวน์")
                b_egg = st.text_input("ลักษณะเด่น/สีของเปลือกไข่:", placeholder="เช่น เปลือกไข่สีน้ำตาลเข้ม")
                b_feed = st.number_input("อัตรากินอาหารตามคู่มือ (กรัม/ตัว/วัน):", value=115.0, step=1.0)
                
                if st.button("➕ บันทึกสายพันธุ์ใหม่ไปยังคลาวด์", use_container_width=True, type="primary"):
                    if b_name.strip():
                        try:
                            supabase.table("สายพันธุ์ไก่ไข่_layer_breeds").insert({
                                "กลุ่มสายพันธุ์_group_name": b_group, 
                                "ชื่อสายพันธุ์_breed_name": b_name, 
                                "สีเปลือกไข่_egg_shell_color": b_egg, 
                                "ปริมาณอาหารที่กิน_feed_intake_g": b_feed
                            }).execute()
                            st.success(f"🎉 เพิ่มสายพันธุ์ '{b_name}' สำเร็จ")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ เพิ่มสายพันธุ์ล้มเหลว: {e}")
                    else: 
                        st.warning("⚠️ กรุณากรอกชื่อสายพันธุ์")
                        
        with bc2:
            st.markdown("### ❌ ลบข้อมูลสายพันธุ์")
            with st.container(border=True):
                if db_breeds:
                    b_del = st.selectbox("เลือกสายพันธุ์ที่ต้องการลบ:", [b.get("ชื่อสายพันธุ์_breed_name", "Unknown") for b in db_breeds])
                    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
                    if st.button("🗑️ ยืนยันลบออกจากทำเนียบเซิร์ฟเวอร์", type="primary", use_container_width=True):
                        try:
                            supabase.table("สายพันธุ์ไก่ไข่_layer_breeds").delete().eq("ชื่อสายพันธุ์_breed_name", b_del).execute()
                            st.success(f"🔥 ลบสายพันธุ์ '{b_del}' เรียบร้อยแล้ว")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ ลบข้อมูลล้มเหลว: {e}")
                else: 
                    st.info("ไม่มีข้อมูลสายพันธุ์ในระบบ")

    # --- แท็บที่ 3: แก้ไขเป้าหมายความต้องการโภชนาการ (ตาราง มาตรฐานโภชนาการไก่ไข่_layer_standards) ---
    with admin_tabs[3]:
        db_targets = fetch_targets_from_supabase()

        with st.expander("📊 เปิดดูค่าเกณฑ์มาตรฐานโภชนาการสัตว์ ณ ปัจจุบัน", expanded=False):
            if db_targets:
                st.dataframe(pd.DataFrame.from_dict(db_targets, orient='index'), use_container_width=True)
            else:
                st.info("💡 ไม่มีข้อมูลเกณฑ์มาตรฐานโภชนาการในระบบ")
            
        st.markdown("### ✏️ ปรับเปลี่ยนเกณฑ์ข้อกำหนดสารอาหารขั้นต่ำประจำช่วงอายุ")
        
        if not db_targets:
            st.warning("⚠️ ไม่พบข้อมูลช่วงระยะผลิตของไก่ไข่ในระบบ")
        else:
            select_stage_crud = st.selectbox(
                "เลือกช่วงระยะผลิตของไก่ไข่ที่ต้องการแก้ไขเกณฑ์:", 
                list(db_targets.keys())
            )
            
            with st.form(key=f"form_target_{select_stage_crud}"):
                st.markdown(f"📝 ตั้งค่าเกณฑ์ขั้นต่ำสำหรับช่วงอายุ: **{select_stage_crud}**")
                
                sc = st.columns(3)
                # ดึงเป้าหมายสารอาหารเฉพาะตัวหลักออกมาให้ Admin ปรับได้ทันที
                with sc[0]:
                    up_protein = st.number_input("ขั้นต่ำของ โปรตีนดิบ (% CP):", value=float(db_targets[select_stage_crud].get("min_protein", 0.0)), step=0.1)
                    up_me = st.number_input("ขั้นต่ำของ พลังงานใช้ประโยชน์ได้ (ME kcal/kg):", value=float(db_targets[select_stage_crud].get("min_me", 0.0)), step=10.0)
                with sc[1]:
                    up_calcium = st.number_input("ขั้นต่ำของ แคลเซียม (% Ca):", value=float(db_targets[select_stage_crud].get("min_calcium", 0.0)), step=0.01)
                    up_phos = st.number_input("ขั้นต่ำของ ฟอสฟอรัสเป็นประโยชน์ (%):", value=float(db_targets[select_stage_crud].get("min_phos", 0.0)), step=0.01)
                with sc[2]:
                    up_lysine = st.number_input("ขั้นต่ำของ อะมิโน ไลซีน (% Lys):", value=float(db_targets[select_stage_crud].get("min_lysine", 0.0)), step=0.01)
                    up_methionine = st.number_input("ขั้นต่ำของ อะมิโน เมทไธโอนีน (% Met):", value=float(db_targets[select_stage_crud].get("min_methionine", 0.0)), step=0.01)
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("💾 ยืนยันอัปเดตเกณฑ์โภชนาการช่วงอายุนี้ไปยังคลาวด์", type="primary", use_container_width=True):
                    try:
                        update_payload = {
                            "โปรตีนต่ำสุด_min_protein": up_protein,
                            "พลังงานต่ำสุด_min_me": up_me,
                            "แคลเซียมต่ำสุด_min_calcium": up_calcium,
                            "ฟอสฟอรัสต่ำสุด_min_phosphorus": up_phos,
                            "ไลซีนต่ำสุด_min_lysine": up_lysine,
                            "เมทิโอนีนต่ำสุด_min_methionine": up_methionine
                        }
                        supabase.table("มาตรฐานโภชนาการไก่ไข่_layer_standards").update(update_payload).eq("ช่วงอายุการเลี้ยง_phase_name", select_stage_crud).execute()
                        st.success("🎉 อัปเดตเกณฑ์มาตรฐานความต้องการทางโภชนาการบนคลาวด์เรียบร้อยแล้ว!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ อัปเดตข้อมูลล้มเหลว: {e}")

    # --- แท็บที่ 4: จัดการสมาชิกผู้ใช้งาน ---
    with admin_tabs[4]:
        st.subheader("👤 สรุปบัญชีผู้ใช้งานในระบบ")
        
        try:
            res_users = supabase.table("user_roles_view").select("*").execute()
            users_list = res_users.data if res_users.data else []
        except Exception as e:
            users_list = []

        if users_list:
            df_users = pd.DataFrame(users_list)
            st.dataframe(df_users, use_container_width=True, hide_index=True)
        else:
            st.info("💡 ระบบความปลอดภัย Supabase Auth จัดเก็บข้อมูลสมาชิกแยกอย่างปลอดภัยบนคลาวด์")
            
        st.markdown("---")
        
        uc1, uc2 = st.columns(2, gap="large")
        with uc1:
            st.markdown("### ✏️ เปลี่ยนแปลงสิทธิ์ของสมาชิก")
            with st.container(border=True):
                st.info("💡 การแก้ไขสิทธิ์ผู้ใช้งาน สามารถจัดการแบบเรียลไทม์ได้ที่หน้า Dashboard > Authentication ของ Supabase")
                
        with uc2:
            st.markdown("### ❌ ระงับและลบบัญชี")
            with st.container(border=True):
                st.warning("⚠️ การลบบัญชีหรือระงับสิทธิ์การใช้งานเพื่อความปลอดภัยสูงสุดของระบบข้อมูลฟาร์ม แนะนำให้ทำผ่านหน้าคอนโซลหลักของ Supabase")
            
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🔄 สลับบทบาทกลับไปโหมดผู้ใช้งานทั่วไป (User Dashboard)", use_container_width=True):
        st.session_state.user_role = "user"
        st.rerun()
else:
    # ==========================================
    # 🎨 CUSTOM UI/UX FOR ALL AGES (BIG FONT & HIGH CONTRAST)
    # ==========================================
    st.markdown("""
        <style>
            .stTabs [data-baseweb="tab-list"] button {
                font-size: 22px !important;
                font-weight: bold !important;
                height: 60px !important;
            }
            .stNumberInput input, .stSelectbox div, .stSlider div {
                font-size: 20px !important;
                font-weight: bold !important;
            }
            label {
                font-size: 20px !important;
                font-weight: bold !important;
                color: #f1f5f9 !important;
            }
            .stButton button {
                font-size: 22px !important;
                font-weight: bold !important;
                padding: 15px 20px !important;
                border-radius: 12px !important;
                min-height: 55px !important;
            }
            .farmer-card {
                background-color: #1e293b;
                border: 2px solid #475569;
                padding: 22px;
                border-radius: 14px;
                margin-bottom: 20px;
            }
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
    """, unsafe_allow_html=True)

    # ------------------------------------------
    # PRE-CALCULATION & STATE INITIALIZATION
    # ------------------------------------------
    if "current_weights" not in st.session_state:
        st.session_state.current_weights = {}
    if "saved_formulas" not in st.session_state:
        st.session_state.saved_formulas = []
    if "db_ingredients" not in st.session_state:
        st.session_state.db_ingredients = {}
    if "daily_logs" not in st.session_state:
        st.session_state.daily_logs = []
    if "net_cost" not in st.session_state:
        st.session_state.net_cost = 0.0
        
    # ระบบป้องกัน NameError ของเป้าหมายโภชนาการ
    if "edit_p" not in st.session_state: st.session_state.edit_p = 16.5
    if "edit_m" not in st.session_state: st.session_state.edit_m = 2750.0
    if "edit_c" not in st.session_state: st.session_state.edit_c = 3.8
    if "edit_ph" not in st.session_state: st.session_state.edit_ph = 0.45

    user_id_now = st.session_state.get("user_id", "")
    my_formulas = []
    raw_formulas = st.session_state.get("saved_formulas", [])
    
    if not isinstance(raw_formulas, list):
        raw_formulas = []

    for f in raw_formulas:
        if isinstance(f, dict):
            f_uid = str(f.get("user_id", ""))
            if not user_id_now or f_uid == str(user_id_now) or f_uid in ["", "None", "null"]:
                my_formulas.append(f)

    # กรณีไม่มีสูตรอาหารในระบบเลย ให้สร้างสูตรสำรองปลอดภัยไว้ป้องกัน Error
    if not my_formulas:
        mock_weights = {k: (100.0 / len(st.session_state.db_ingredients) if st.session_state.db_ingredients else 0.0) for k in st.session_state.db_ingredients.keys()}
        if not mock_weights:
            mock_weights = {"ข้าวโพดบด": 50.0, "กากถั่วเหลือง": 30.0, "รำละเอียด": 15.0, "เปลือกหอยบด": 5.0}
            
        my_formulas = [{
            "id": "mock_01",
            "name": "สูตรมาตรฐานฟาร์ม (สูตรสำรองระบบ)",
            "date": str(datetime.date.today()),
            "breed": "สายพันธุ์มาตรฐาน",
            "stage": "ระยะให้ไข่พีค",
            "weights": mock_weights,
            "cost": 12.50
        }]

    with st.expander("🔍 ระบบจัดการฐานข้อมูลความปลอดภัย (สิทธิ์การเข้าถึงข้อมูล)"):
        st.write(f"• ไอดีผู้ใช้งานปัจจุบัน (User ID): `{user_id_now if user_id_now else 'ว่างเปล่า'}`")
        st.write(f"• สูตรทั้งหมดที่ผ่านการคัดกรอง: `{len(my_formulas)} สูตร`")
        
        if st.button("⚡ รีเฟรชและบังคับดึงข้อมูลตรงจาก Supabase", use_container_width=True):
            try:
                query = supabase.table("saved_formulas").select("*")
                if user_id_now:
                    res = query.eq("user_id", user_id_now).execute()
                else:
                    res = query.execute()

                if hasattr(res, 'data') and isinstance(res.data, list):
                    st.session_state.saved_formulas = res.data
                    st.success(f"เชื่อมต่อสำเร็จ! ดึงข้อมูลสูตรมาได้ {len(res.data)} รายการ")
                    st.rerun()
                else:
                    st.error("การตอบกลับจากเซิร์ฟเวอร์ผิดพลาด")
            except Exception as e:
                st.error(f"การเชื่อมต่อถูกปฏิเสธ (ตรวจสอบ RLS Policy บน Supabase): {e}")

    # คำนวณต้นทุนต่อหน่วยล่วงหน้าและบันทึกลง Session State เสมอ เพื่อส่งต่อข้ามแท็บอย่างปลอดภัย
    calculated_cost = 0.0
    if st.session_state.current_weights:
        total_w = sum(st.session_state.current_weights.values())
        divisor = total_w if total_w > 0 else 1.0
        for name, w in st.session_state.current_weights.items():
            if name in st.session_state.db_ingredients:
                ratio = w / divisor
                calculated_cost += ratio * float(st.session_state.db_ingredients[name].get("price", 0.0))
    st.session_state.net_cost = calculated_cost if calculated_cost > 0 else 12.50

    # ==========================================
    # 👑 USER ROUTE: ACCESSIBLE INTERFACE
    # ==========================================
    page_tabs = st.tabs([
        "🥣 1. สูตรอาหาร & คลังสูตรเก่า", 
        "💰 2. บันทึกรายวัน & บัญชีฟาร์ม",
        "📊 3. ใบสั่งผสมอาหาร (สำหรับคนงาน)"
    ])

    # ------------------------------------------
    # TAB 1: FORMULA MATRIX & BANK MANAGEMENT
    # ------------------------------------------
    with page_tabs[0]:
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("### 📂 เรียกใช้หรือลบสูตรอาหารเก่าในคลัง")
        
        col_load1, col_load2 = st.columns([6, 4])
        with col_load1:
            formula_labels = []
            for idx, f in enumerate(my_formulas):
                f_name = f.get("name", "สูตรไม่ได้ตั้งชื่อ")
                f_date = f.get("date", "ไม่ระบุวัน")
                formula_labels.append(f"{idx+1}. {f_name} ({f_date})")
                
            selected_label = st.selectbox("🔍 ค้นหาและเลือกชื่อสูตรอาหาร:", formula_labels, key="sb_formula_selector")
            selected_index = formula_labels.index(selected_label)
            target_formula = my_formulas[selected_index]
            
        with col_load2:
            st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("🔄 ดึงสูตรมาใช้", use_container_width=True, key="btn_load_formula"):
                    raw_weights = target_formula.get("weights", {})
                    if isinstance(raw_weights, str):
                        try:
                            import json
                            raw_weights = json.loads(raw_weights)
                        except:
                            raw_weights = {}
                            
                    if isinstance(raw_weights, dict) and raw_weights:
                        st.session_state.current_weights = raw_weights.copy()
                        st.toast("🔄 ซิงค์สัดส่วนอาหารเรียบร้อยแล้ว!")
                        st.rerun()
                    else:
                        st.error("โครงสร้างข้อมูลสูตรผิดพลาด")
                        
            with col_btn2:
                if st.button("❌ ลบสูตรนี้ทิ้ง", use_container_width=True, key="btn_delete_formula"):
                    if target_formula.get("id") == "mock_01":
                        st.error("ระบบห้ามลบสูตรสำรองครับ")
                    else:
                        try:
                            formula_id = target_formula.get("id")
                            supabase.table("saved_formulas").delete().eq("id", formula_id).eq("user_id", user_id_now).execute()
                            st.session_state.saved_formulas = [f for f in st.session_state.saved_formulas if f.get("id") != formula_id]
                            st.toast("🗑️ ลบสูตรสำเร็จ!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"ลบไม่สำเร็จ: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("### 🐓 เลือกสายพันธุ์และกลุ่มไก่ไข่")
        
        col_br1, col_br2, col_br3 = st.columns(3)
        with col_br1:
            list_groups = [g["group_name"] for g in st.session_state.get("db_groups", [{"group_name": "กลุ่มมาตรฐาน"}])]
            selected_g = st.selectbox("📁 เลือกกลุ่มสายพันธุ์หลัก:", list_groups)
            
        with col_br2:
            filtered_breeds = [b for b in st.session_state.get("db_breeds", []) if b.get("group_name") == selected_g]
            breed_names = [b["breed_name"] for b in filtered_breeds] if filtered_breeds else ["สายพันธุ์มาตรฐาน"]
            selected_b_name = st.selectbox("🐔 เลือกสายพันธุ์ไก่ไข่:", breed_names)
            
            current_breed_data = next((b for b in filtered_breeds if b.get("breed_name") == selected_b_name), {"default_feed": 115.0, "egg_color": "ไม่ระบุ"})
            st.session_state['current_breed_default_feed'] = current_breed_data.get("default_feed", 115.0)
            
        with col_br3:
            if "db_targets" in st.session_state and st.session_state.db_targets:
                stage_options = {s["stage_name"]: s["stage_key"] for s in st.session_state.db_targets.values()}
                selected_stage_label = st.selectbox("📋 เลือกช่วงระยะการให้ไข่:", list(stage_options.keys()))
                base_req = st.session_state.db_targets[stage_options[selected_stage_label]]
            else:
                selected_stage_label = st.selectbox("📋 เลือกช่วงระยะการให้ไข่:", ["ระยะให้ไข่พีค (พีค)"])
                base_req = {"protein": 16.5, "me": 2750.0, "calcium": 3.8, "phos": 0.45, "lysine": 0.75, "methionine": 0.38}
            
            st.session_state.edit_p = base_req["protein"]
            st.session_state.edit_m = base_req["me"]
            st.session_state.edit_c = base_req["calcium"]
            st.session_state.edit_ph = base_req["phos"]
        st.markdown("</div>", unsafe_allow_html=True)

        col_left, col_right = st.columns([1.1, 0.9])
        
        with col_left:
            st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
            cl_title, cl_reset = st.columns([6, 4])
            with cl_title:
                st.markdown("### 🥣 ปรับค่าเป้าหมาย & สัดส่วนวัตถุดิบ (%)")
            with cl_reset:
                if st.button("🔄 รีเซ็ตสัดส่วนอาหาร", use_container_width=True):
                    st.session_state.current_weights = run_ai_solver(st.session_state.edit_p, st.session_state.edit_m, st.session_state.edit_c, st.session_state.edit_ph, float(base_req.get("lysine", 0.75)), float(base_req.get("methionine", 0.38)))
                    st.rerun()

            st.markdown("#### 🎯 ปรับแต่งระดับโภชนาการเป้าหมาย")
            target_col1, target_col2 = st.columns(2)
            with target_col1:
                st.session_state.edit_p = st.number_input("🎯 โปรตีนเป้าหมาย (%):", min_value=5.0, value=float(st.session_state.edit_p), step=0.1)
                st.session_state.edit_m = st.number_input("🎯 พลังงานเป้าหมาย (kcal/kg):", min_value=1000.0, value=float(st.session_state.edit_m), step=25.0)
            with target_col2:
                st.session_state.edit_c = st.number_input("🎯 แคลเซียมเป้าหมาย (%):", min_value=0.5, value=float(st.session_state.edit_c), step=0.05)
                st.session_state.edit_ph = st.number_input("🎯 ฟอสฟอรัสเป้าหมาย (%):", min_value=0.1, value=float(st.session_state.edit_ph), step=0.02)
            
            if st.button("⚡ สั่ง AI คำนวณสูตรด่วนตามเป้าหมายด้านบน", type="primary", use_container_width=True):
                with st.spinner("AI กำลังจัดสูตร..."):
                    st.session_state.current_weights = run_ai_solver(st.session_state.edit_p, st.session_state.edit_m, st.session_state.edit_c, st.session_state.edit_ph, float(base_req.get("lysine", 0.75)), float(base_req.get("methionine", 0.38)))
                    st.rerun()
            
            st.markdown("<div style='border-bottom: 1px solid #475569; margin:20px 0;'></div>", unsafe_allow_html=True)
            
            st.markdown("#### 🌾 ปรับสัดส่วนวัตถุดิบรายตัว")
            temp_weights = {}
            running_total = 0.0
            inclusion_limits = {"กากเบียร์แห้ง": 10.0, "กากน้ำตาล": 5.0, "น้ำมันปาล์ม": 4.0, "น้ำมันถั่วเหลือง": 4.0, "ข้าวนก": 15.0, "กากดีดีจีเอส": 15.0, "DDGS": 15.0}
            
            ing_keys = list(st.session_state.db_ingredients.keys())
            ing_col1, ing_col2 = st.columns(2)
            
            for idx, name in enumerate(ing_keys):
                d = st.session_state.db_ingredients[name]
                saved_w = float(st.session_state.current_weights.get(name, 0.0))
                saved_w = max(0.0, min(100.0, saved_w))
                
                target_col = ing_col1 if idx % 2 == 0 else ing_col2
                with target_col:
                    user_val = st.slider(
                        f"🌽 {name} ({d.get('price', 0.0)} บ.)", min_value=0.0, max_value=100.0, value=saved_w, step=0.1, key=f"sld_user_{name}"
                    )
                    if name in inclusion_limits and user_val > inclusion_limits[name]:
                        st.markdown(f"<p style='color:#f87171; font-size:14px; font-weight:bold; margin:-8px 0px 10px 0px;'>⚠️ ห้ามเกิน {inclusion_limits[name]}% ไก่จะท้องเสีย</p>", unsafe_allow_html=True)
                
                temp_weights[name] = user_val
                running_total += user_val
            
            st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
            if abs(running_total - 100.0) > 0.1:
                st.markdown(f"<div style='background-color:#991b1b; padding:15px; border-radius:8px; font-size:18px; font-weight:bold; text-align:center;'>⚠️ สัดส่วนอาหารรวมได้: {running_total:.1f}% (กรุณาปรับให้ครบ 100%)</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='background-color:#065f46; padding:15px; border-radius:8px; font-size:18px; font-weight:bold; text-align:center;'>🟢 ส่วนผสมครบถ้วนสมบูรณ์ 100%</div>", unsafe_allow_html=True)
            
            st.session_state.current_weights = temp_weights
            st.markdown("</div>", unsafe_allow_html=True)

        with col_right:
            st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
            st.markdown("### 🧪 ผลลัพธ์โภชนาการจริงในสูตร")
            
            act_nut = {"protein": 0.0, "me": 0.0, "calcium": 0.0, "phos": 0.0}
            total_w = sum(st.session_state.current_weights.values())
            divisor = total_w if total_w > 0 else 1.0
            
            for name, w in st.session_state.current_weights.items():
                if name in st.session_state.db_ingredients:
                    ratio = w / divisor
                    for k in act_nut.keys():
                        act_nut[k] += ratio * float(st.session_state.db_ingredients[name].get(k, 0.0))
            
            comparison_table = [
                {"โภชนาการสำคัญ": "โปรตีนดิบ (% CP)", "เป้าหมาย": f"{st.session_state.edit_p:.2f} %", "ได้จริงในสูตร": f"{act_nut['protein']:.2f} %"},
                {"โภชนาการสำคัญ": "พลังงานใช้ประโยชน์ (ME)", "เป้าหมาย": f"{st.session_state.edit_m:.0f}", "ได้จริงในสูตร": f"{act_nut['me']:.0f}"},
                {"โภชนาการสำคัญ": "แคลเซียม (% Ca)", "เป้าหมาย": f"{st.session_state.edit_c:.2f} %", "ได้จริงในสูตร": f"{act_nut['calcium']:.2f} %"},
                {"โภชนาการสำคัญ": "ฟอสฟอรัส (% P)", "เป้าหมาย": f"{st.session_state.edit_ph:.2f} %", "ได้จริงในสูตร": f"{act_nut['phos']:.2f} %"},
            ]
            st.dataframe(pd.DataFrame(comparison_table), use_container_width=True, hide_index=True)
            
            st.markdown(f"<div style='background-color:#1e293b; padding:15px; border-radius:10px; border:2px solid #38bdf8; text-align:center; font-size:24px; font-weight:bold; margin: 15px 0;'>💰 ต้นทุนค่าอาหารสูตรนี้: {st.session_state.net_cost:.2f} บาท/กก.</div>", unsafe_allow_html=True)
            
            name_parts = selected_b_name.split()
            breed_display_name = name_parts[-2] if len(name_parts) > 1 else selected_b_name
            
            save_name_input = st.text_input("💾 ตั้งชื่อเล่นสูตรอาหารเพื่อกดเซฟ:", value=f"สูตร {breed_display_name} {st.session_state.net_cost:.1f} บาท")
            
            if st.button("📥 ยืนยันกดบันทึกสูตรอาหารลงคลัง", use_container_width=True):
                new_formula_data = {
                    "user_id": user_id_now if user_id_now else None,
                    "date": str(datetime.date.today()), 
                    "name": save_name_input, 
                    "cost": round(st.session_state.net_cost, 2), 
                    "breed": selected_b_name, 
                    "stage": selected_stage_label,
                    "protein": round(act_nut["protein"], 2), 
                    "me": round(act_nut["me"], 0), 
                    "calcium": round(act_nut["calcium"], 2), 
                    "weights": st.session_state.current_weights.copy()
                }
                
                try:
                    supabase.table("saved_formulas").insert(new_formula_data).execute()
                    st.session_state.saved_formulas.append(new_formula_data)
                    st.toast("📥 บันทึกสูตรอาหารลงคลาวด์สำเร็จ!")
                except Exception as e:
                    st.session_state.saved_formulas.append(new_formula_data)
                    st.warning(f"เซฟลงเครื่องเสร็จสิ้น แต่คลาวด์ไม่เปิดสิทธิ์: {e}")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------
    # TAB 2: DAILY LOG & CASHFLOW (FINANCIAL)
    # ------------------------------------------
    with page_tabs[1]:
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("<h2>☀️ บันทึกตัวชี้วัดฟาร์ม & รายรับ-รายจ่ายประจำวัน</h2>", unsafe_allow_html=True)
        st.markdown("<div style='border-bottom: 2px solid #475569; margin:15px 0;'></div>", unsafe_allow_html=True)
        
        if st.session_state.daily_logs:
            if st.button("📋 ดึงข้อมูลจากประวัติล่าสุด (ไม่ต้องพิมพ์ใหม่หมด)", use_container_width=True):
                last_log = st.session_state.daily_logs[-1]
                st.session_state["shortcut_birds"] = last_log["จำนวนไก่ (ตัว)"]
                st.session_state["shortcut_price"] = last_log["รายได้ขายไข่ (บาท)"] / last_log["ไข่ที่เก็บได้ (ฟอง)"] if last_log["ไข่ที่เก็บได้ (ฟอง)"] > 0 else 4.10
                st.toast("📋 คัดลอกค่าเดิมจากประวัติเสร็จสิ้น!")

        log_col1, log_col2 = st.columns(2)
        with log_col1:
            st.markdown("#### 📝 ส่วนที่ 1: ข้อมูลฝูงไก่วันนี้")
            log_date = st.date_input("วันที่บันทึกข้อมูล:", datetime.date.today(), key="farm_log_date")
            flock_age_weeks = st.number_input("🐣 อายุฝูงไก่ปัจจุบัน (สัปดาห์):", min_value=1, max_value=100, value=25, step=1)
            
            default_birds = st.session_state.get("shortcut_birds", 5000)
            bird_count = st.number_input("จำนวนไก่ไข่ทั้งหมดในเล้าวันนี้ (ตัว):", min_value=1, value=int(default_birds), step=100)
            env_temp = st.slider("🌡️ อุณหภูมิสูงสุดในเล้าวันนี้ (°C):", 15.0, 45.0, 28.0, step=0.5, key="temp_slider")
            
            breed_default_feed = st.session_state.get('current_breed_default_feed', 115.0)
            recommended_feed = float(bird_count * breed_default_feed / 1000.0)
            st.markdown(f"<p style='color:#6366f1; font-size:16px; font-weight:bold; margin-bottom:-5px;'>💡 ปริมาณอาหารแนะนำตามสายพันธุ์: {recommended_feed:,.1f} กก.</p>", unsafe_allow_html=True)
            actual_feed_given_kg = st.number_input("🍽️ น้ำหนักอาหารที่ให้ไก่กินรวมวันนี้ (กิโลกรัม):", min_value=10.0, value=recommended_feed, step=10.0)
            
        with log_col2:
            st.markdown("#### 💰 ส่วนที่ 2: จำนวนไข่และราคาส่งวันนี้")
            collected_eggs = st.number_input("จำนวนฟองไข่ที่เก็บได้จริงวันนี้ (ฟอง):", min_value=0, value=4200)
            
            default_price = st.session_state.get("shortcut_price", 4.10)
            egg_sale_price = st.number_input("💵 ราคารับซื้อไข่หน้าฟาร์มวันนี้ (บาท/ฟอง):", min_value=1.0, value=float(default_price), step=0.1)
            dead_birds = st.number_input("จำนวนไก่ตาย/คัดทิ้งวันนี้ (ตัว):", min_value=0, value=2)
            avg_egg_weight_g = st.number_input("⚖️ น้ำหนักไข่เฉลี่ยวันนี้ (กรัม/ฟอง):", min_value=30.0, max_value=80.0, value=62.0, step=0.5)

        st.markdown("<div style='background-color:#1e1b4b; padding:20px; border-radius:12px; border:2px solid #6366f1; margin: 20px 0;'>", unsafe_allow_html=True)
        st.markdown(f"### 📋 ปฏิทินเตือนงานสำคัญสำหรับไก่อายุ {flock_age_weeks} สัปดาห์:")
        
        # ปรับปรุง Logic ปฏิทินให้ครอบคลุมค่าทศนิยมและแบ่งช่วงปลอดภัยชัดเจน
        if flock_age_weeks <= 3:
            st.markdown("<p style='color:#38bdf8; font-size:22px; font-weight:bold;'>• ต้องทำวัคซีนนิวคาสเซิล + หลอดลมอักเสบ และตรวจเช็กระบบไฟกก</p>", unsafe_allow_html=True)
        elif 4 <= flock_age_weeks <= 8:
            st.markdown("<p style='color:#38bdf8; font-size:22px; font-weight:bold;'>• ต้องทำวัคซีนฝีดาษ และทำวัคซีนอหิวาต์ไก่รอบที่ 1</p>", unsafe_allow_html=True)
        elif 9 <= flock_age_weeks <= 16:
            st.markdown("<p style='color:#38bdf8; font-size:22px; font-weight:bold;'>• ต้องถ่ายพยาธิไก่ก่อนย้ายเข้ากรงตับ และทำวัคซีนรวมก่อนเริ่มไข่</p>", unsafe_allow_html=True)
        elif 17 <= flock_age_weeks <= 24:
            st.markdown("<p style='color:#fbbf24; font-size:22px; font-weight:bold;'>• ไก่เริ่มไข่แล้ว: [ระวัง] ห้ามลดแสงสว่างในเล้าเด็ดขาด! แสงสว่างต้องเพิ่มอย่างสม่ำเสมอ</p>", unsafe_allow_html=True)
        elif 25 <= flock_age_weeks <= 60:
            st.markdown("<p style='color:#10b981; font-size:22px; font-weight:bold;'>• ช่วงไข่ดก: สุ่มเช็กความหนาเปลือกไข่ และล้างทำความสะอาดหัวนิปเปิ้ลน้ำทุกสัปดาห์</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p style='color:#f87171; font-size:22px; font-weight:bold;'>• ไก่แก่ท้ายชุด: ให้คนงานเสริมเปลือกหอยบดในรางช่วงเย็น ป้องกันไข่เปลือกบางแตกหัก</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
            
        # การคำนวณเงินไหลเวียนดึงค่าจาก st.session_state.net_cost โดยตรง ป้องกันปัญหา UnboundVariable
        total_revenue = collected_eggs * egg_sale_price
        total_feed_cost = actual_feed_given_kg * st.session_state.net_cost
        net_profit_day = total_revenue - total_feed_cost
        
        henday_pct = (collected_eggs / bird_count) * 100.0 if bird_count > 0 else 0.0
        total_egg_mass_kg = (collected_eggs * avg_egg_weight_g) / 1000.0
        fcr_ratio = actual_feed_given_kg / total_egg_mass_kg if total_egg_mass_kg > 0 else 0.0
        cost_per_egg = total_feed_cost / collected_eggs if collected_eggs > 0 else 0.0

        if 0 < henday_pct < 65.0:
            st.markdown(f"<div style='background-color:#7c2d12; padding:15px; border-radius:8px; font-size:18px; font-weight:bold; margin-bottom:15px;'>⚠️ เตือน: เปอร์เซ็นต์การไข่ต่ำกว่าเกณฑ์มาตรฐาน ({henday_pct:.1f}%) ตรวจเช็กพฤติกรรมการกินและสุ่มคัดไก่ป่วยด่วน</div>", unsafe_allow_html=True)
        if dead_birds > (bird_count * 0.001):
            st.markdown(f"<div style='background-color:#991b1b; padding:15px; border-radius:8px; font-size:18px; font-weight:bold; margin-bottom:15px;'>🚨 วิกฤต: วันนี้ไก่ตายผิดปกติ ({dead_birds} ตัว) สูงเกินเกณฑ์ ระวังสภาพอากาศร้อนจัดหรือโรคระบาดติดต่อ!</div>", unsafe_allow_html=True)
        if env_temp >= 32.0:
            st.error(f"🚨 เล้าร้อนจัด ({env_temp}°C) ไก่เสี่ยงช็อกตาย! คนงานต้องเปิดระบบพ่นหมอกและเร่งพัดลมทันที")

        st.markdown("### 📊 สรุปผลกำไรสุทธิและตัวชี้วัดวันนี้")
        profit_box_color = "#065f46" if net_profit_day >= 0 else "#991b1b"
        st.markdown(f"<div style='background-color:{profit_box_color}; padding:20px; border-radius:12px; text-align:center; font-size:26px; font-weight:bold; margin-bottom:20px;'>💸 เงินกำไรสุทธิประจำวัน (หักค่าอาหารแล้ว): {net_profit_day:,.2f} บาท</div>", unsafe_allow_html=True)

        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.markdown(f"<div style='background-color:#0f172a; padding:15px; border-radius:10px; border:1px solid #334155; text-align:center;'><span class='big-metric-label'>🥚 เปอร์เซ็นต์การไข่</span><br><span class='big-metric-value'>{henday_pct:.1f} %</span></div>", unsafe_allow_html=True)
        with m_col2:
            st.markdown(f"<div style='background-color:#0f172a; padding:15px; border-radius:10px; border:1px solid #334155; text-align:center;'><span class='big-metric-label'>🥣 อัตราแลกไข่ (FCR)</span><br><span class='big-metric-value'>{fcr_ratio:.2f}</span></div>", unsafe_allow_html=True)
        with m_col3:
            st.markdown(f"<div style='background-color:#0f172a; padding:15px; border-radius:10px; border:1px solid #334155; text-align:center;'><span class='big-metric-label'>🥚 ค่าอาหารต่อไข่ 1 ฟอง</span><br><span class='big-metric-value'>{cost_per_egg:.2f} บาท</span></div>", unsafe_allow_html=True)
            
        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
            
        if st.button("💾 กดปุ่มนี้เพื่อบันทึกประวัติประจำวัน", use_container_width=True):
            st.session_state.daily_logs.append({
                "วันที่": str(log_date), "อายุฝูง (สัปดาห์)": flock_age_weeks, "จำนวนไก่ (ตัว)": bird_count, "อุณหภูมิ (°C)": env_temp,
                "อาหารที่กิน (KG)": actual_feed_given_kg, "ไข่ที่เก็บได้ (ฟอง)": collected_eggs, 
                "รายได้ขายไข่ (บาท)": round(total_revenue, 2), "ต้นทุนอาหาร (บาท)": round(total_feed_cost, 2),
                "กำไรสุทธิ (บาท)": round(net_profit_day, 2), "อัตราไข่ (%)": round(henday_pct, 1), "FCR": round(fcr_ratio, 2)
            })
            st.toast("💾 บันทึกประวัติฟาร์มประจำวันเรียบร้อยแล้ว!")
            st.rerun()
            
        st.markdown("<div style='border-bottom: 2px dashed #475569; margin:25px 0;'></div>", unsafe_allow_html=True)
        st.markdown("### 📋 ตารางประวัติฟาร์มย้อนหลัง")
        if not st.session_state.daily_logs:
            st.info("💡 ยังไม่มีข้อมูลย้อนหลัง")
        else:
            st.dataframe(pd.DataFrame(st.session_state.daily_logs), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------
    # TAB 3: PROCUREMENT & WORKER SHEET
    # ------------------------------------------
    with page_tabs[2]:
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("<h2>📊 ใบสั่งงานผสมอาหารสัตว์ (สำหรับยื่นให้คนงานตักของ)</h2>", unsafe_allow_html=True)
        total_tonnage = st.number_input("📦 ใส่จำนวนกิโลกรัมอาหารรวมที่ต้องการจะผสมในรอบนี้ (KG):", min_value=100, value=1000, step=100)
        
        po_buffer = []
        total_po_cost = 0
        total_w = sum(st.session_state.current_weights.values())
        divisor = total_w if total_w > 0 else 1.0
        
        for ing_name, w_pct in st.session_state.current_weights.items():
            actual_pct = (w_pct / divisor) * 100.0
            if actual_pct > 0.01:
                if ing_name in st.session_state.db_ingredients:
                    weight_kg = (actual_pct / 100.0) * total_tonnage
                    cost_item = weight_kg * float(st.session_state.db_ingredients[ing_name].get("price", 0.0))
                    total_po_cost += cost_item
                    
                    bags = int(weight_kg // 50)
                    rem_kg = weight_kg % 50
                    
                    bag_txt = f"🟢 ยก {bags} กระสอบ + ⚖️ ตักเศษ {rem_kg:.1f} กก." if bags > 0 else f"⚖️ ตักเศษสุทธิ {rem_kg:.1f} กิโลกรัม"
                    
                    po_buffer.append({
                        "รายการวัตถุดิบ": ing_name, "สัดส่วนผสม (%)": round(actual_pct, 1), 
                        "น้ำหนักรวมที่ต้องใช้ (KG)": round(weight_kg, 1), "📢 วิธีตักหน้างาน (กระสอบละ 50kg)": bag_txt,
                        "ราคาทุน (บาท)": round(cost_item, 0)
                    })
                    
        if po_buffer:
            df_po = pd.DataFrame(po_buffer)
            st.dataframe(df_po, use_container_width=True, hide_index=True)
            
            st.markdown(f"<div style='background-color:#1e293b; padding:15px; border-radius:10px; border:2px dashed #10b981; font-size:24px; font-weight:bold; text-align:center; margin:15px 0;'>💵 งบประมาณค่าวัตถุดิบรวมรอบนี้: {total_po_cost:,.2f} บาท</div>", unsafe_allow_html=True)
            
            line_text = f"📋 *ใบสั่งผสมอาหารสัตว์รวม: {total_tonnage:,} กก.*\n"
            line_text += f"สูตรสำหรับ: {selected_b_name} ({selected_stage_label})\n"
            line_text += "--------------------------------------\n"
            for item in po_buffer:
                line_text += f"🔹 {item['รายการวัตถุดิบ']}: {item['📢 วิธีตักหน้างาน (กระสอบละ 50kg)']}\n"
            line_text += "--------------------------------------\n"
            line_text += f"💰 งบประมาณรวมรอบนี้: {total_po_cost:,.0f} บาท"

            st.markdown("### 📱 ข้อความด่วนสำหรับก๊อปปี้ส่ง LINE (คนงานเปิดอ่านง่าย)")
            st.code(line_text, language="text")
            
            import io
            csv_s = io.StringIO()
            df_po.to_csv(csv_s, index=False, encoding='utf-8-sig')
            st.download_button("📥 กดดาวน์โหลดใบสั่งงานเป็นไฟล์ CSV", data=csv_s.getvalue(), file_name=f"ใบสั่งผสมอาหาร_{total_tonnage}กก.csv", mime="text/csv", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
