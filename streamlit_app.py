import streamlit as st
import pandas as pd
import plotly.express as px
import pulp
import io
import datetime

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
    
    .fb-header {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #1877f2 !important;
        font-size: 3.2rem !important;
        font-weight: bold !important;
        text-align: center;
        margin-bottom: 2px;
        letter-spacing: -1.5px;
    }
    .fb-subtitle {
        color: #ffffff !important;
        font-size: 1.25rem !important;
        text-align: center;
        margin-bottom: 25px;
        opacity: 0.9;
    }
    .divider-line {
        border-top: 1px solid rgba(255, 255, 255, 0.18);
        margin: 22px 0;
    }
    
    div.stButton > button[key="btn_fb_signup_trigger"] {
        background-color: #42b72a !important;
        color: white !important;
        font-size: 1.35rem !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        border: none !important;
        box-shadow: 0px 5px 15px rgba(66, 183, 42, 0.4) !important;
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
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False
if "auth_page_mode" not in st.session_state:
    st.session_state.auth_page_mode = "login"  
if "user_role" not in st.session_state:
    st.session_state.user_role = "user"  
if "saved_formulas" not in st.session_state:
    st.session_state.saved_formulas = []  

if "user_database" not in st.session_state:
    st.session_state.user_database = {
        "admin": {"password": "222", "name": "ผู้ดูแลระบบ", "surname": "ระดับสูง", "role": "admin", "tel": "089-999-9999", "reg_date": "2026-01-01"},
        "222": {"password": "222", "name": "แอดมิน", "surname": "ทางลัด", "role": "admin", "tel": "088-888-8888", "reg_date": "2026-01-02"},
        "user_test@gmail.com": {"password": "123", "name": "สมชาย", "surname": "ใจดี", "role": "user", "tel": "081-234-5678", "reg_date": "2026-05-10"}
    }

if "db_groups" not in st.session_state:
    st.session_state.db_groups = [
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "bg_color": "#b45309", "text_color": "#ffffff", "market_trend": "ครองแชมป์ความนิยมอันดับ 1 ในไทยและเอเชีย โดดเด่นเรื่องขนาดฟองและเปลือกไข่หนา"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีขาว (Commercial White Layers)", "bg_color": "#0284c7", "text_color": "#ffffff", "market_trend": "อุตสาหกรรมแปรรูป ให้ปริมาณไข่ดกสูงสุดและประหยัดต้นทุนอาหารดีเยี่ยม"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีครีมและพาสเทล (Commercial Tinted Layers)", "bg_color": "#0d9488", "text_color": "#ffffff", "market_trend": "ตลาดพรีเมียมยุคใหม่ เปลือกสีนวลชมพู/ครีม เป็นที่ต้องการของตลาดโมเดิร์นเทรด"}
    ]

if "db_breeds" not in st.session_state:
    st.session_state.db_breeds = [
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "breed_key": "Isa Brown", "breed_name": "สายพันธุ์ ไอซ่า บราวน์ (Isa Brown)", "egg_color": "สีน้ำตาลเข้ม", "default_feed": 114.0, "description": "สายพันธุ์ฝรั่งเศส ทนร้อนชื้นได้ดีเลิศ ผลผลิตนิ่งสม่ำเสมอ"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "breed_key": "Lohmann Brown", "breed_name": "สายพันธุ์ โลห์แมน บราวน์ (Lohmann Brown)", "egg_color": "สีน้ำตาลเงางาม", "default_feed": 116.0, "description": "สายพันธุ์เยอรมัน โดดเด่นเรื่องไข่ฟองใหญ่ เปลือกหนาเหนียวพิเศษ"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีขาว (Commercial White Layers)", "breed_key": "Hy-Line W-36", "breed_name": "สายพันธุ์ ไฮ-ไลน์ ขาว ดับบลิว-36 (Hy-Line W-36)", "egg_color": "สีขาวสะอาดตา", "default_feed": 101.0, "description": "กินอาหารน้อยที่สุดในโลก ให้ปริมาณไข่ขาวหนาตัวดีมาก"}
    ]

if "db_ingredients" not in st.session_state:
    st.session_state.db_ingredients = {
        "ข้าวโพดบดเม็ด (Ground Corn)": {"name": "ข้าวโพดบดเม็ด (Ground Corn)", "price": 13.5, "protein": 8.5, "me": 3300.0, "calcium": 0.02, "phos": 0.25, "lysine": 0.24, "methionine": 0.18, "fiber": 2.2, "min_limit": 0.0, "max_limit": 70.0},
        "กากถั่วเหลือง 46% (Soybean Meal 46%)": {"name": "กากถั่วเหลือง 46% (Soybean Meal 46%)", "price": 19.5, "protein": 46.0, "me": 2440.0, "calcium": 0.25, "phos": 0.62, "lysine": 2.85, "methionine": 0.65, "fiber": 3.5, "min_limit": 0.0, "max_limit": 50.0},
        "ปลาป่นเกรด A 60% (Fish Meal 60%)": {"name": "ปลาป่นเกรด A 60% (Fish Meal 60%)", "price": 35.0, "protein": 60.0, "me": 2850.0, "calcium": 5.00, "phos": 3.00, "lysine": 4.50, "methionine": 1.80, "fiber": 1.0, "min_limit": 0.0, "max_limit": 12.0},
        "หินฝุ่นเม็ดหยาบ (Coarse Limestone)": {"name": "หินฝุ่นเม็ดหยาบ (Coarse Limestone)", "price": 2.5, "protein": 0.0, "me": 0.0, "calcium": 38.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "fiber": 0.0, "min_limit": 0.0, "max_limit": 15.0},
        "ไดแคลเซียมฟอสเฟต (DCP 18%)": {"name": "ไดแคลเซียมฟอสเฟต (DCP 18%)", "price": 28.0, "protein": 0.0, "me": 0.0, "calcium": 21.00, "phos": 18.00, "lysine": 0.00, "methionine": 0.00, "fiber": 0.0, "min_limit": 0.0, "max_limit": 4.0},
        "เกลือแกงบริสุทธิ์ (Refined Salt)": {"name": "เกลือแกงบริสุทธิ์ (Refined Salt)", "price": 6.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "fiber": 0.0, "min_limit": 0.10, "max_limit": 0.50},
        "พรีมิกซ์วิตามินแร่ธาตุ (Vitamin-Mineral Premix)": {"name": "พรีมิกซ์วิตามินแร่ธาตุ (Vitamin-Mineral Premix)", "price": 160.0, "protein": 0.0, "me": 0.0, "calcium": 5.00, "phos": 1.20, "lysine": 0.00, "methionine": 0.00, "fiber": 0.0, "min_limit": 0.20, "max_limit": 0.40},
        "DL-Methionine (กรดอะมิโนสังเคราะห์)": {"name": "DL-Methionine (กรดอะมิโนสังเคราะห์)", "price": 145.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 99.00, "fiber": 0.0, "min_limit": 0.0, "max_limit": 1.00},
        "L-Lysine HCl (กรดอะมิโนสังเคราะห์)": {"name": "L-Lysine HCl (กรดอะมิโนสังเคราะห์)", "price": 95.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 78.40, "methionine": 0.00, "fiber": 0.0, "min_limit": 0.0, "max_limit": 1.00}
    }

if "db_targets" not in st.session_state:
    st.session_state.db_targets = {
        "layer_phase_1": {"stage_key": "layer_phase_1", "stage_name": "ระยะผลิตไข่พีค ช่วงที่ 1 อายุ 19-45 สัปดาห์ (Production Phase 1)", "protein": 17.5, "me": 2750.0, "calcium": 4.10, "phos": 0.42, "lysine": 0.88, "methionine": 0.42, "fiber_max": 4.5},
        "layer_phase_2": {"stage_key": "layer_phase_2", "stage_name": "ระยะกลาง ช่วงที่ 2 อายุ 46-65 สัปดาห์ (Production Phase 2)", "protein": 16.5, "me": 2725.0, "calcium": 4.30, "phos": 0.38, "lysine": 0.82, "methionine": 0.39, "fiber_max": 5.0}
    }

if "optimized_weights" not in st.session_state:
    st.session_state.optimized_weights = {k: 0.0 for k in st.session_state.db_ingredients.keys()}
    # ให้ค่าเริ่มต้นมีสารอาหารบ้างป้องกันกราฟว่างเปล่าก่อนคำนวณ
    st.session_state.optimized_weights["ข้าวโพดบดเม็ด (Ground Corn)"] = 60.0
    st.session_state.optimized_weights["กากถั่วเหลือง 46% (Soybean Meal 46%)"] = 28.0
    st.session_state.optimized_weights["หินฝุ่นเม็ดหยาบ (Coarse Limestone)"] = 12.0

if "current_formula_metadata" not in st.session_state:
    st.session_state.current_formula_metadata = {
        "formula_name": "สูตรเริ่มต้นระบบ", "breed": "Isa Brown", "stage": "layer_phase_1", "climate": "🟢", "egg_price": 4.1, "laying_rate": 85, "default_feed": 114.0
    }

# ==========================================
# 🔒 3. SECURITY GATEWAY (LOGIN / SIGNUP)
# ==========================================
if not st.session_state.is_authenticated:
    if st.session_state.auth_page_mode == "login":
        st.markdown("<div class='content-card' style='max-width: 550px; margin: 80px auto 0 auto;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #ffb703 !important;'>🔐 ระบบวิเคราะห์โภชนาการและจัดการสายพันธุ์ไก่ไข่ระดับสากล</h2>", unsafe_allow_html=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        
        email_login = st.text_input("📧 อีเมลผู้ใช้งาน หรือรหัสทางลัด (Email / Username):", key="login_email")
        pass_login = st.text_input("🔑 รหัสผ่านเข้าใช้งาน (Password):", type="password", key="login_pass")
        
        if st.button("เข้าสู่ระบบ (Log In)", type="primary", use_container_width=True):
            if email_login in st.session_state.user_database and st.session_state.user_database[email_login]["password"] == pass_login:
                user_info = st.session_state.user_database[email_login]
                st.session_state.is_authenticated = True
                st.session_state.user_role = user_info.get("role", "user")
                st.session_state.user_email = f"{'🛠️ Admin' if st.session_state.user_role == 'admin' else '👑 User'}: คุณ {user_info['name']}"
                st.rerun()
            else:
                st.error("❌ ไอดีหรือรหัสผ่านไม่ถูกต้อง (แอดมินทดสอบระบบ ป้อนไอดี '222' และรหัสผ่าน '222')")
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("❓ ลืมรหัสผ่าน?", use_container_width=True): st.session_state.auth_page_mode = "forgot"; st.rerun()
        with col_b2:
            if st.button("✨ สร้างบัญชีใหม่ (Sign Up)", use_container_width=True): st.session_state.auth_page_mode = "signup"; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    elif st.session_state.auth_page_mode == "signup":
        st.markdown("<div class='content-card' style='max-width: 620px; margin: 40px auto 0 auto;'>", unsafe_allow_html=True)
        st.markdown("<h1 class='fb-header'>facebook</h1>", unsafe_allow_html=True)
        st.markdown("<p class='fb-subtitle'><b>สร้างบัญชีใหม่</b></p>", unsafe_allow_html=True)
        col_name1, col_name2 = st.columns(2)
        with col_name1: reg_name = st.text_input("ชื่อจริง")
        with col_name2: reg_surname = st.text_input("นามสกุล")
        reg_identity = st.text_input("เบอร์โทรศัพท์หรืออีเมล")
        reg_password = st.text_input("รหัสผ่านใหม่", type="password")
        
        if st.button("สมัครสมาชิก (Sign Up)", key="btn_fb_signup_trigger", use_container_width=True):
            if not reg_name or not reg_identity or not reg_password: st.error("⚠️ กรุณากรอกรายละเอียดให้ครบถ้วน")
            else:
                st.session_state.user_database[reg_identity] = {"password": reg_password, "name": reg_name, "surname": reg_surname, "role": "user", "tel": reg_identity, "reg_date": str(datetime.date.today())}
                st.success("🎉 สมัครสมาชิกสำเร็จ! กลับไปหน้าล็อกอินเพื่อเข้าใช้งาน")
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        if st.button("➡️ มีบัญชีอยู่แล้ว? เข้าสู่ระบบ", use_container_width=True): st.session_state.auth_page_mode = "login"; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    elif st.session_state.auth_page_mode == "forgot":
        st.markdown("<div class='content-card' style='max-width: 550px; margin: 80px auto 0 auto;'>", unsafe_allow_html=True)
        forgot_identity = st.text_input("ระบุข้อมูลอีเมลหรือเบอร์โทรศัพท์:")
        if st.button("ดึงข้อมูลรหัสผ่าน", type="primary", use_container_width=True):
            if forgot_identity in st.session_state.user_database: st.success(f"💡 รหัสผ่านของคุณคือ: `{st.session_state.user_database[forgot_identity]['password']}`")
            else: st.error("❌ ไม่พบข้อมูลบัญชีนี้")
        if st.button("⬅️ กลับไปหน้าล็อกอิน", use_container_width=True): st.session_state.auth_page_mode = "login"; st.rerun()
        st.stop()

# ==========================================
# 🎉 4. HEADER CONTROL PANEL
# ==========================================
col_h1, col_h2 = st.columns([7.5, 2.5])
with col_h1:
    st.markdown("# 🐔 Layer Nutrition Studio Pro")
    st.markdown(f"<p style='color:#38bdf8; font-weight:bold;'>🎯 ระดับสิทธิ์: {st.session_state.user_email}</p>", unsafe_allow_html=True)
with col_h2:
    if st.button("🔴 ออกจากระบบ (Logout)", use_container_width=True):
        st.session_state.is_authenticated = False
        st.session_state.user_role = "user"
        st.session_state.optimized_weights = {}
        st.session_state.current_formula_metadata = {}
        st.rerun()
st.markdown("---")

# ==========================================
# 🛠️ 5. INTERACTION ROUTER
# ==========================================
if st.session_state.user_role == "admin":
    # Admin Control Panel คงเดิมสำหรับการแก้ไขฐานข้อมูลหลักแบบเสถียร
    st.markdown("<div style='background-color:#1e3a8a; padding:15px; border-radius:10px; margin-bottom:20px;'><h3 style='margin:0; color:#93c5fd !important;'>🛠️ FULL CRUD CONTROL PANEL: หน้าบริหารจัดการฐานข้อมูลระบบฟาร์ม</h3></div>", unsafe_allow_html=True)
    admin_tabs = st.tabs(["🌽 1. จัดการสารอาหารวัตถุดิบ", "🐓 2. จัดการสายพันธุ์ไก่ไข่", "🧬 3. จัดการเกณฑ์โภชนาการอายุ", "👥 4. จัดการผู้ใช้งาน"])
    
    with admin_tabs[0]:
        st.markdown("<div class='content-card'>### 🌽 บริหารจัดการวัตถุดิบและคุณค่าทางโภชนาการ</div>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame.from_dict(st.session_state.db_ingredients, orient='index'), use_container_width=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### ➕ เพิ่ม / ✏️ แก้ไข วัตถุดิบ")
            ing_name = st.text_input("ชื่อวัตถุดิบ:")
            ing_price = st.number_input("ราคา (บาท/กก.):", min_value=0.0, value=12.0)
            ing_prot = st.number_input("โปรตีน (%):", min_value=0.0, value=10.0)
            ing_me = st.number_input("พลังงาน ME (kcal/kg):", min_value=0.0, value=2500.0)
            ing_ca = st.number_input("แคลเซียม (%):", min_value=0.0, value=0.0)
            ing_phos = st.number_input("ฟอสฟอรัส (%):", min_value=0.0, value=0.0)
            ing_lys = st.number_input("ไลซีน (%):", min_value=0.0, value=0.0)
            ing_meth = st.number_input("เมทไธโอนีน (%):", min_value=0.0, value=0.0)
            ing_fiber = st.number_input("เยื่อใย (%):", min_value=0.0, value=0.0)
            ing_min = st.number_input("ขั้นต่ำในสูตร (%):", min_value=0.0, value=0.0)
            ing_max = st.number_input("สูงสุดในสูตร (%):", min_value=0.0, value=100.0)
            if st.button("💾 บันทึกวัตถุดิบ"):
                if ing_name:
                    st.session_state.db_ingredients[ing_name] = {"name": ing_name, "price": ing_price, "protein": ing_prot, "me": ing_me, "calcium": ing_ca, "phos": ing_phos, "lysine": ing_lys, "methionine": ing_meth, "fiber": ing_fiber, "min_limit": ing_min, "max_limit": ing_max}
                    st.success("บันทึกสำเร็จ!"); st.rerun()
        with c2:
            st.markdown("#### ❌ ลบวัตถุดิบ")
            to_del = st.selectbox("เลือกวัตถุดิบที่จะลบ:", list(st.session_state.db_ingredients.keys()))
            if st.button("🗑️ ยืนยันลบวัตถุดิบ"):
                del st.session_state.db_ingredients[to_del]; st.warning("ลบออกแล้ว!"); st.rerun()

    with admin_tabs[1]:
        st.markdown("<div class='content-card'>### 🐓 จัดการกลุ่มและสายพันธุ์ไก่ไข่</div>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(st.session_state.db_breeds), use_container_width=True)
        bc1, bc2 = st.columns(2)
        with bc1:
            b_group = st.selectbox("เลือกกลุ่มหลักที่ต้องการเพิ่มสายพันธุ์:", [g["group_name"] for g in st.session_state.db_groups])
            b_name = st.text_input("ชื่อสายพันธุ์การค้าใหม่:")
            b_egg = st.text_input("สีเปลือกไข่:")
            b_feed = st.number_input("อัตรากินอาหารมาตรฐาน (กรัม/วัน):", value=115.0)
            b_desc = st.text_area("ข้อมูลสายพันธุ์:")
            if st.button("➕ เพิ่มสายพันธุ์"):
                if b_name:
                    st.session_state.db_breeds.append({"group_name": b_group, "breed_key": b_name, "breed_name": b_name, "egg_color": b_egg, "default_feed": b_feed, "description": b_desc})
                    st.success("เพิ่มสำเร็จ!"); st.rerun()
        with bc2:
            b_del = st.selectbox("เลือกสายพันธุ์ที่ต้องการลบ:", [b["breed_name"] for b in st.session_state.db_breeds])
            if st.button("🗑️ ยืนยันลบสายพันธุ์"):
                st.session_state.db_breeds = [b for b in st.session_state.db_breeds if b["breed_name"] != b_del]
                st.warning("ลบออกแล้ว!"); st.rerun()

    with admin_tabs[2]:
        st.markdown("<div class='content-card'>### 🧬 จัดการเกณฑ์ความต้องการโภชนาการตามช่วงอายุ</div>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame.from_dict(st.session_state.db_targets, orient='index'), use_container_width=True)
        tc1, tc2 = st.columns(2)
        with tc1:
            t_key = st.text_input("คีย์ระบบ (ภาษาอังกฤษห้ามเคาะเว้นวรรค):")
            t_name = st.text_input("ชื่อระยะอายุสัตว์:")
            t_prot = st.number_input("ต้องการโปรตีน (%):", value=16.5)
            t_me = st.number_input("ต้องการพลังงาน (ME):", value=2750.0)
            t_ca = st.number_input("ต้องการแคลเซียม (%):", value=4.0)
            t_phos = st.number_input("ต้องการฟอสฟอรัส (%):", value=0.4)
            t_lys = st.number_input("ต้องการไลซีน (%):", value=0.8)
            t_meth = st.number_input("ต้องการเมทไธโอนีน (%):", value=0.38)
            t_fib = st.number_input("กากใยสูงสุด (%):", value=5.0)
            if st.button("💾 บันทึกเกณฑ์อายุ"):
                if t_key and t_name:
                    st.session_state.db_targets[t_key] = {"stage_key": t_key, "stage_name": t_name, "protein": t_prot, "me": t_me, "calcium": t_ca, "phos": t_phos, "lysine": t_lys, "methionine": t_meth, "fiber_max": t_fib}
                    st.success("บันทึกสำเร็จ!"); st.rerun()
        with tc2:
            t_del = st.selectbox("เลือกเกณฑ์สารอาหารที่ต้องการลบ:", list(st.session_state.db_targets.keys()))
            if st.button("🗑️ ยืนยันลบเกณฑ์"):
                del st.session_state.db_targets[t_del]; st.warning("ลบออกแล้ว!"); st.rerun()

    with admin_tabs[3]:
        st.markdown("<div class='content-card'>### 👥 บัญชีผู้ใช้และจัดการสิทธิ์เข้าถึง</div>", unsafe_allow_html=True)
        for idx, (username, u_info) in enumerate(st.session_state.user_database.items()):
            col_u1, col_u2, col_u3 = st.columns([4, 4, 2])
            with col_u1: st.write(f"👤 {username} ({u_info.get('name')})")
            with col_u2: st.write(f"สิทธิ์: {u_info.get('role')}")
            with col_u3:
                if username not in ["admin", "222"]:
                    if st.button("🗑️ ลบผู้ใช้", key=f"del_u_{idx}"):
                        del st.session_state.user_database[username]; st.rerun()

else:
    # -----------------------------------------------------------------------------------------
    # 🐔 USER CONTROL PANEL (ระบบปรับเปลี่ยนสารอาหารเเละวัตถุดิบสองทางแบบ Interactive)
    # -----------------------------------------------------------------------------------------
    page_tabs = st.tabs([
        "🏠 ระบบผสมสูตรอาหารแบบสลับสองทาง (Interactive Two-Way Matrix)", 
        "📊 ใบส่งสั่งซื้อวัตถุดิบ (Procurement PO Sheet)", 
        "📈 คลังประวัติสูตรอาหารที่บันทึก (Saved Formula History Log)"
    ])
    
    with page_tabs[0]:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        
        # --- CONTROL MODE SELECTOR ---
        st.markdown("### 🔄 เลือกโหมดการทำงานของระบบควบคุม")
        control_mode = st.radio(
            "โปรดเลือกกลไกการคำนวณอาหารสัตว์:",
            ["🤖 โหมด AI Dynamic Goal-Seeking (แก้ไขระดับสารอาหารเป้าหมาย ➡️ แล้วให้วัตถุดิบขยับตามอัตโนมัติ)", 
             "🎛️ โหมด DIY Manual Override (ปรับลบ-เพิ่มสัดส่วนวัตถุดิบเองด้วยมือ ➡️ แล้วให้ระดับสารอาหารขยับคำนวณตามสด ๆ)"],
            index=0
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # --- SECTION A: INPUT SIDE (LEFT) vs OUTPUT SIDE (RIGHT) ---
        col_main_left, col_main_right = st.columns([1.1, 0.9])
        
        with col_main_left:
            st.markdown("<div class='content-card'>", unsafe_allow_html=True)
            
            if "🤖" in control_mode:
                st.markdown("### 🧬 ปรับแก้สารอาหารเป้าหมาย (AI จะหาวัตถุดิบให้ขยับตาม)")
                st.markdown("คุณสามารถปรับแกิตัวเลขคุณค่าทางอาหารที่ต้องการได้อิสระ AI จะคำนวณหาจุดคุ้มทุนวัตถุดิบใหม่ให้ทันที")
                
                # ดึงเกณฑ์ตั้งต้น
                stage_options = {s["stage_name"]: s["stage_key"] for s in st.session_state.db_targets.values()}
                selected_stage_label = st.selectbox("ดึงฐานข้อมูลระยะอายุเริ่มต้นจากระบบ:", list(stage_options.keys()))
                base_req = st.session_state.db_targets[stage_options[selected_stage_label]]
                
                # ฟิลด์ป้อนสารอาหารแบบแปรผันยืดหยุ่นสูง
                req_protein = st.number_input("ต้องการโปรตีนดิบเป้าหมาย (Crude Protein %):", min_value=10.0, max_value=30.0, value=float(base_req["protein"]), step=0.1)
                req_me = st.number_input("ต้องการพลังงานสัตว์เป้าหมาย (ME kcal/kg):", min_value=2000.0, max_value=3500.0, value=float(base_req["me"]), step=25.0)
                req_ca = st.number_input("ต้องการแคลเซียมเพื่อเปลือกไข่เป้าหมาย (% Calcium):", min_value=1.0, max_value=6.0, value=float(base_req["calcium"]), step=0.05)
                req_p = st.number_input("ต้องการฟอสฟอรัสที่เป็นประโยชน์เป้าหมาย (% Avail. Phosphorus):", min_value=0.1, max_value=2.0, value=float(base_req["phos"]), step=0.02)
                req_lys = st.number_input("ต้องการกรดอะมิโนไลซีนเป้าหมาย (% Lysine):", min_value=0.2, max_value=2.0, value=float(base_req["lysine"]), step=0.01)
                req_meth = st.number_input("ต้องการกรดอะมิโนเมทไธโอนีนเป้าหมาย (% Methionine):", min_value=0.1, max_value=1.5, value=float(base_req["methionine"]), step=0.01)
                
                st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
                st.markdown("### 🐓 ข้อมูลสายพันธุ์และเศรษฐศาสตร์")
                egg_price_per_piece = st.number_input("ราคารับซื้อไข่หน้าฟาร์ม (บาท/ฟอง):", min_value=1.0, value=4.10)
                laying_rate = st.slider("เปอร์เซ็นต์การไข่ของฝูง (% Laying Rate):", 10, 100, 85)
                feed_per_day = st.number_input("ปริมาณการกินมาตรฐาน (กรัม/ตัว/วัน):", value=114.0)

                if st.button("⚡ เดินเครื่องคำนวณสูตรอาหาร (Run AI Matrix)", type="primary", use_container_width=True):
                    with st.spinner("AI กำลังปรับสัดส่วนวัตถุดิบให้ขยับตามเป้าหมายโภชนาการของคุณ..."):
                        prob = pulp.LpProblem("DynamicTwoWaySolver", pulp.LpMinimize)
                        ing_vars = {name: pulp.LpVariable(name, lowBound=float(d["min_limit"])/100.0, upBound=float(d["max_limit"])/100.0) for name, d in st.session_state.db_ingredients.items()}
                        
                        # เพิ่มกลไกความยืดหยุ่น ป้องกันสมการขัดแย้งพังทลาย
                        slack_pr = pulp.LpVariable("s_pr", lowBound=0)
                        slack_me = pulp.LpVariable("s_me", lowBound=0)
                        slack_ca = pulp.LpVariable("s_ca", lowBound=0)
                        
                        prob += pulp.lpSum([ing_vars[name] * float(d["price"]) for name, d in st.session_state.db_ingredients.items()]) + 1000.0 * (slack_pr + slack_me/100.0 + slack_ca), "Cost"
                        prob += pulp.lpSum([ing_vars[name] for name in st.session_state.db_ingredients.keys()]) == 1.0, "TotalWeight"
                        
                        prob += pulp.lpSum([ing_vars[name] * float(d["protein"]) for name, d in st.session_state.db_ingredients.items()]) + slack_pr >= req_protein
                        prob += pulp.lpSum([ing_vars[name] * float(d["me"]) for name, d in st.session_state.db_ingredients.items()]) + slack_me >= req_me
                        prob += pulp.lpSum([ing_vars[name] * float(d["calcium"]) for name, d in st.session_state.db_ingredients.items()]) + slack_ca >= req_ca
                        prob += pulp.lpSum([ing_vars[name] * float(d["phos"]) for name, d in st.session_state.db_ingredients.items()]) >= req_p
                        prob += pulp.lpSum([ing_vars[name] * float(d["lysine"]) for name, d in st.session_state.db_ingredients.items()]) >= req_lys
                        prob += pulp.lpSum([ing_vars[name] * float(d["methionine"]) for name, d in st.session_state.db_ingredients.items()]) >= req_meth
                        
                        prob.solve(pulp.PULP_CBC_CMD(msg=False))
                        
                        # เซฟผลลัพธ์ลง Session State ให้สัดส่วนวัตถุดิบขยับตามทันที
                        for name in st.session_state.db_ingredients.keys():
                            st.session_state.optimized_weights[name] = ing_vars[name].varValue * 100.0 if ing_vars[name].varValue is not None else 0.0
                        
                        st.session_state.current_formula_metadata.update({
                            "egg_price": egg_price_per_piece, "laying_rate": laying_rate, "default_feed": feed_per_day
                        })
                        st.success("🎉 วัตถุดิบขยับสัดส่วนตามเกณฑ์สารอาหารใหม่เรียบร้อยแล้ว!")
                        st.rerun()

            else:
                st.markdown("### 🎛️ ปรับ/ลบ/เพิ่ม เปอร์เซ็นต์วัตถุดิบ (สารอาหารด้านขวาจะคำนวณตาม)")
                st.markdown("ปรับสไลเดอร์วัตถุดิบแต่ละชนิดด้วยตัวคุณเองได้อิสระ **(ผลรวมต้องเท่ากับ 100%)** เพื่อวิเคราะห์สูตรตามใจชอบ")
                
                accumulated_weights = {}
                running_total = 0.0
                
                # วนลูปสร้างตัวปรับวัตถุดิบแบบเรียลไทม์
                for name, d in st.session_state.db_ingredients.items():
                    current_saved_val = float(st.session_state.optimized_weights.get(name, 0.0))
                    # บังคับให้อยู่ในขอบเขต 0-100
                    current_saved_val = max(0.0, min(100.0, current_saved_val))
                    
                    user_val = st.slider(
                        f"🥣 {name} (ราคา {d['price']} บาท/กก.)", 
                        min_value=0.0, max_value=100.0, 
                        value=current_saved_val, step=0.1, key=f"manual_ing_{name}"
                    )
                    accumulated_weights[name] = user_val
                    running_total += user_val
                
                # แสดงสถานะผลรวมเปอร์เซ็นต์วัตถุดิบ
                if abs(running_total - 100.0) > 0.01:
                    st.markdown(f"<div style='background-color:#991b1b; padding:10px; border-radius:5px;'>⚠️ สัดส่วนวัตถุดิบรวมกันได้: <b>{running_total:.1f}%</b> (กรุณาปรับให้ครบ 100% เพื่อความแม่นยำของสารอาหาร)</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='background-color:#065f46; padding:10px; border-radius:5px;'>🟢 สัดส่วนผสมครบถ้วนสมบูรณ์: <b>{running_total:.1f}%</b></div>", unsafe_allow_html=True)
                
                # อัปเดตค่าลงถังข้อมูลส่วนกลางเพื่อสะท้อนกลับทันที
                st.session_state.optimized_weights = accumulated_weights

            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_main_right:
            st.markdown("<div class='content-card'>", unsafe_allow_html=True)
            st.markdown("### 🧪 คุณค่าทางโภชนาการจริงที่ได้รับและผลลัพธ์")
            st.markdown("สารอาหารเหล่านี้จะ**ขยับตามทันที**ไม่ว่าจะปรับทางฝั่ง AI หรือปรับเพิ่มลดวัตถุดิบด้วยตัวเอง")
            
            # คำนวณสารอาหารและราคาจากน้ำหนักจริง ณ ปัจจุบัน
            net_cost_per_kg = 0.0
            act_nut = {"protein": 0.0, "me": 0.0, "calcium": 0.0, "phos": 0.0, "lysine": 0.0, "methionine": 0.0, "fiber": 0.0}
            
            total_w = sum(st.session_state.optimized_weights.values())
            # ทำนอร์มัลไลซ์เพื่อหาค่าสัดส่วนจริง
            divisor = total_w if total_w > 0 else 1.0
            
            for name, w in st.session_state.optimized_weights.items():
                ratio = w / divisor
                net_cost_per_kg += ratio * float(st.session_state.db_ingredients[name]["price"])
                for k in act_nut.keys():
                    act_nut[k] += ratio * float(st.session_state.db_ingredients[name].get(k, 0.0))
            
            # แสดงตารางสารอาหารขยับตามจริง
            comparison_rows = [
                {"รายการโภชนาการ": "โปรตีนดิบรวม (Crude Protein %)", "ระดับสารอาหารที่ได้จริง": f"{act_nut['protein']:.2f} %"},
                {"รายการโภชนาการ": "พลังงานใช้ประโยชน์ได้ (ME kcal/kg)", "ระดับสารอาหารที่ได้จริง": f"{act_nut['me']:.0f} kcal/kg"},
                {"รายการโภชนาการ": "แคลเซียมหนุนเปลือกไข่ (% Calcium)", "ระดับสารอาหารที่ได้จริง": f"{act_nut['calcium']:.2f} %"},
                {"รายการโภชนาการ": "ฟอสฟอรัสที่เป็นประโยชน์ (% Avail. Phos)", "ระดับสารอาหารที่ได้จริง": f"{act_nut['phos']:.2f} %"},
                {"รายการโภชนาการ": "กรดอะมิโน ไลซีน (% Lysine)", "ระดับสารอาหารที่ได้จริง": f"{act_nut['lysine']:.2f} %"},
                {"รายการโภชนาการ": "กรดอะมิโน เมทไธโอนีน (% Methionine)", "ระดับสารอาหารที่ได้จริง": f"{act_nut['methionine']:.2f} %"},
                {"รายการโภชนาการ": "กากใยอาหารรวม (% Crude Fiber)", "ระดับสารอาหารที่ได้จริง": f"{act_nut['fiber']:.2f} %"}
            ]
            st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)
            
            # ประเมินโครงสร้างทางเศรษฐศาสตร์แบบ Real-time
            meta = st.session_state.current_formula_metadata
            feed_consumed_kg = float(meta.get("default_feed", 114.0)) / 1000.0
            feed_cost_bird_day = feed_consumed_kg * net_cost_per_kg
            revenue_bird_day = (float(meta.get("laying_rate", 85)) / 100.0) * float(meta.get("egg_price", 4.1))
            iofc_profit = revenue_bird_day - feed_cost_bird_day
            
            st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
            st.markdown("##### 💵 ตัวชี้วัดทางเศรษฐศาสตร์")
            ec1, ec2 = st.columns(2)
            with ec1: st.metric("💰 ต้นทุนรวมสูตรนี้", f"{net_cost_per_kg:.2f} บาท/กก.")
            with ec2: st.metric("📈 กำไรเหนือค่าอาหาร (IOFC)", f"{iofc_profit:.2f} บาท/ตัว/วัน")
            
            # แสดงกราฟสัดส่วนการใช้วัตถุดิบปัจจุบัน
            st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
            st.markdown("##### 📊 แผนภูมิวงกลมสัดส่วนวัตถุดิบปัจจุบัน")
            clean_plot = [{"วัตถุดิบ": k, "สัดส่วน (%)": v} for k, v in st.session_state.optimized_weights.items() if v > 0.01]
            if clean_plot:
                fig_p = px.pie(pd.DataFrame(clean_plot), names="วัตถุดิบ", values="สัดส่วน (%)", hole=0.4, color_discrete_sequence=px.colors.sequential.YlOrBr)
                fig_p.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), margin=dict(t=10, b=10, l=10, r=10), height=250)
                st.plotly_chart(fig_p, use_container_width=True)
                
            # ฟังก์ชันจัดเก็บสูตรอาหารลงประวัติคลัง
            st.markdown("##### 💾 บันทึกสูตรปัจจุบันนี้")
            f_save_name = st.text_input("ตั้งชื่อเล่นสำหรับจำสูตรนี้:", value=f"สูตรดีไอวาย {net_cost_per_kg:.1f} บาท")
            if st.button("📥 ยืนยันบันทึกสูตรอาหารลงคลังประวัติ"):
                st.session_state.saved_formulas.append({
                    "date": str(datetime.date.today()), "name": f_save_name, "cost": round(net_cost_per_kg, 2), "breed": "Customized", "stage": "พิกัดปรับแต่งเอง",
                    "protein": round(act_nut["protein"], 2), "me": round(act_nut["me"], 0), "calcium": round(act_nut["calcium"], 2), "weights": st.session_state.optimized_weights.copy()
                })
                st.success("💾 จัดเก็บสูตรลงคลังเรียบร้อยแล้ว!")
                
            st.markdown("</div>", unsafe_allow_html=True)

    with page_tabs[1]:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("## 📊 ระบบคำนวณสัดส่วนจัดซื้อและสั่งซื้อวัตถุดิบรวม (Procurement Logistics Matrix)")
        total_tonnage = st.number_input("ป้อนปริมาณอาหารรวมทั้งหมดที่ต้องการผสมในรอบนี้ (กิโลกรัม):", min_value=100, value=1000, step=500)
        
        po_buffer = []
        total_po_cost = 0
        total_w = sum(st.session_state.optimized_weights.values())
        divisor = total_w if total_w > 0 else 1.0
        
        for ing_name, w_pct in st.session_state.optimized_weights.items():
            actual_pct = (w_pct / divisor) * 100.0
            if actual_pct > 0.01:
                weight_kg = (actual_pct / 100.0) * total_tonnage
                cost_item = weight_kg * float(st.session_state.db_ingredients[ing_name]["price"])
                total_po_cost += cost_item
                po_buffer.append({"รายการวัตถุดิบสั่งซื้อ": ing_name, "สัดส่วนใช้ (%)": round(actual_pct, 2), "น้ำหนักสุทธิที่ต้องเตรียม (KG)": round(weight_kg, 2), "ประมาณการยอดเงิน (บาท)": round(cost_item, 2)})
                
        if po_buffer:
            df_po = pd.DataFrame(po_buffer)
            st.dataframe(df_po, use_container_width=True, hide_index=True)
            st.metric("💵 งบประมาณจัดซื้อรวมทั้งหมดประจำงวดนี้", f"{total_po_cost:,.2f} บาท")
            
            csv_s = io.StringIO()
            df_po.to_csv(csv_s, index=False, encoding='utf-8-sig')
            st.download_button("📥 ดาวน์โหลดใบสั่งซื้อวัตถุดิบ (Export PO to CSV File)", data=csv_s.getvalue(), file_name=f"PO_Order_Batch_{total_tonnage}KG.csv", mime="text/csv", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with page_tabs[2]:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("## 📈 คลังประวัติสูตรอาหารที่บันทึก (Saved Formula History Log)")
        
        if not st.session_state.saved_formulas:
            st.info("💡 ปัจจุบันยังไม่มีการเซฟสูตรอาหารเก็บไว้ คุณสามารถกดคำนวณและตั้งชื่อบันทึกสูตรอาหารได้จากแท็บแรกครับ")
        else:
            df_history = pd.DataFrame(st.session_state.saved_formulas)
            st.markdown("### 📑 รายการสูตรอาหารทั้งหมดในคลังของคุณ")
            st.dataframe(df_history.drop(columns=["weights"]), use_container_width=True)
            
            st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
            st.markdown("### 🔍 เจาะลึกและส่องสูตรเก่าเปรียบเทียบ")
            selected_f_name = st.selectbox("เลือกสูตรอาหารในอดีตเพื่อดึงสัดส่วนวัตถุดิบขึ้นมาดู:", [f["name"] for f in st.session_state.saved_formulas])
            
            target_f = next(f for f in st.session_state.saved_formulas if f["name"] == selected_f_name)
            st.markdown(f"**📝 รายละเอียดสูตร:** {target_f['name']} | **💰 ต้นทุนเดิม:** {target_f['cost']} บาท/กก.")
            
            sub_rows = [{"วัตถุดิบ": k, "เปอร์เซ็นต์ที่ใช้ (%)": v} for k, v in target_f["weights"].items() if v > 0.01]
            st.dataframe(pd.DataFrame(sub_rows).sort_values(by="เปอร์เซ็นต์ที่ใช้ (%)", ascending=False), use_container_width=True, hide_index=True)
            
            if st.button("🗑️ ลบสูตรอาหารนี้ออกจากคลังประวัติ"):
                st.session_state.saved_formulas = [f for f in st.session_state.saved_formulas if f["name"] != selected_f_name]
                st.success("ลบสูตรอาหารเรียบร้อยแล้ว")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
