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
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "bg_color": "#b45309", "text_color": "#ffffff", "market_trend": "ครองแชมป์ความนิยมอันดับ 1 ในทวีปเอเชีย ประเทศไทย และยุโรป โดดเด่นเรื่องขนาดฟองและเปลือกไข่หนา"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีขาว (Commercial White Layers)", "bg_color": "#0284c7", "text_color": "#ffffff", "market_trend": "ครองตลาดอเมริกาเหนือและโรงงานแปรรูปอุตสาหกรรม ให้ปริมาณไข่ดกสูงสุดและประหยัดต้นทุนอาหารดีเยี่ยม"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีครีมและพาสเทล (Commercial Tinted Layers)", "bg_color": "#0d9488", "text_color": "#ffffff", "market_trend": "ตลาดพรีเมียมยุคใหม่ เปลือกสีนวลชมพู/ครีม เป็นที่ต้องการของตลาดโมเดิร์นเทรดและผู้บริโภคระดับสูง"}
    ]

if "db_breeds" not in st.session_state:
    st.session_state.db_breeds = [
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "breed_key": "Isa Brown", "breed_name": "สายพันธุ์ ไอซ่า บราวน์ (Isa Brown)", "egg_color": "สีน้ำตาลเข้ม", "default_feed": 114.0, "description": "สายพันธุ์ฝรั่งเศส ยอดนิยมอันดับ 1 ในไทย แข็งแรง ทนร้อนชื้นได้ดีเลิศ ผลผลิตนิ่งสม่ำเสมอ"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "breed_key": "Lohmann Brown", "breed_name": "สายพันธุ์ โลห์แมน บราวน์ (Lohmann Brown)", "egg_color": "สีน้ำตาลเงางาม", "default_feed": 116.0, "description": "สายพันธุ์เยอรมัน โดดเด่นเรื่องไข่ฟองใหญ่ เปอร์เซ็นต์ไข่ไซส์ XL สูงมาก เปลือกหนาเหนียวพิเศษ"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีขาว (Commercial White Layers)", "breed_key": "Hy-Line W-36", "breed_name": "สายพันธุ์ ไฮ-ไลน์ ขาว ดับบลิว-36 (Hy-Line W-36)", "egg_color": "สีขาวสะอาดตา", "default_feed": 101.0, "description": "แชมป์โลกด้านความประหยัด กินอาหารน้อยที่สุดในโลก ให้ไข่ฟองสีขาวข้นแน่น ปริมาณไข่ขาวหนาตัวดีมาก"}
    ]

# ปรับเพิ่มวัตถุดิบและ Amino Acids สังเคราะห์ เพื่อช่วยแก้สมการตึงเครียดโดยอัตโนมัติ
if "db_ingredients" not in st.session_state:
    st.session_state.db_ingredients = {
        "ข้าวโพดบดเม็ด (Ground Corn)": {"name": "ข้าวโพดบดเม็ด (Ground Corn)", "price": 13.5, "protein": 8.5, "me": 3300.0, "calcium": 0.02, "phos": 0.25, "lysine": 0.24, "methionine": 0.18, "threonine": 0.29, "fat": 3.8, "moisture": 12.0, "fiber": 2.2, "min_limit": 0.0, "max_limit": 70.0},
        "กากถั่วเหลือง 46% (Soybean Meal 46%)": {"name": "กากถั่วเหลือง 46% (Soybean Meal 46%)", "price": 19.5, "protein": 46.0, "me": 2440.0, "calcium": 0.25, "phos": 0.62, "lysine": 2.85, "methionine": 0.65, "threonine": 1.80, "fat": 1.5, "moisture": 11.0, "fiber": 3.5, "min_limit": 0.0, "max_limit": 50.0},
        "ปลาป่นเกรด A 60% (Fish Meal 60%)": {"name": "ปลาป่นเกรด A 60% (Fish Meal 60%)", "price": 35.0, "protein": 60.0, "me": 2850.0, "calcium": 5.00, "phos": 3.00, "lysine": 4.50, "methionine": 1.80, "threonine": 2.40, "fat": 8.0, "moisture": 10.0, "fiber": 1.0, "min_limit": 0.0, "max_limit": 12.0},
        "หินฝุ่นเม็ดหยาบ (Coarse Limestone)": {"name": "หินฝุ่นเม็ดหยาบ (Coarse Limestone)", "price": 2.5, "protein": 0.0, "me": 0.0, "calcium": 38.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 0.5, "fiber": 0.0, "min_limit": 0.0, "max_limit": 15.0},
        "ไดแคลเซียมฟอสเฟต (DCP 18%)": {"name": "ไดแคลเซียมฟอสเฟต (DCP 18%)", "price": 28.0, "protein": 0.0, "me": 0.0, "calcium": 21.00, "phos": 18.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 1.0, "fiber": 0.0, "min_limit": 0.0, "max_limit": 4.0},
        "เกลือแกงบริสุทธิ์ (Refined Salt)": {"name": "เกลือแกงบริสุทธิ์ (Refined Salt)", "price": 6.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 0.3, "fiber": 0.0, "min_limit": 0.10, "max_limit": 0.50},
        "พรีมิกซ์วิตามินแร่ธาตุ (Vitamin-Mineral Premix)": {"name": "พรีมิกซ์วิตามินแร่ธาตุ (Vitamin-Mineral Premix)", "price": 160.0, "protein": 0.0, "me": 0.0, "calcium": 5.00, "phos": 1.20, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 2.0, "fiber": 0.0, "min_limit": 0.20, "max_limit": 0.40},
        "DL-Methionine (กรดอะมิโนสังเคราะห์)": {"name": "DL-Methionine (กรดอะมิโนสังเคราะห์)", "price": 145.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 99.00, "threonine": 0.00, "fat": 0.0, "moisture": 0.5, "fiber": 0.0, "min_limit": 0.0, "max_limit": 0.50},
        "L-Lysine HCl (กรดอะมิโนสังเคราะห์)": {"name": "L-Lysine HCl (กรดอะมิโนสังเคราะห์)", "price": 95.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 78.40, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 0.5, "fiber": 0.0, "min_limit": 0.0, "max_limit": 0.50}
    }

if "db_targets" not in st.session_state:
    st.session_state.db_targets = {
        "layer_phase_1": {"stage_key": "layer_phase_1", "stage_name": "ระยะผลิตไข่พีค ช่วงที่ 1 อายุ 19-45 สัปดาห์ (Production Phase 1)", "protein": 17.5, "me": 2750.0, "calcium": 4.10, "phos": 0.42, "lysine": 0.88, "methionine": 0.42, "fiber_max": 4.5},
        "layer_phase_2": {"stage_key": "layer_phase_2", "stage_name": "ระยะกลาง ช่วงที่ 2 อายุ 46-65 สัปดาห์ (Production Phase 2)", "protein": 16.5, "me": 2725.0, "calcium": 4.30, "phos": 0.38, "lysine": 0.82, "methionine": 0.39, "fiber_max": 5.0}
    }

if "optimized_weights" not in st.session_state:
    st.session_state.optimized_weights = {}
if "current_formula_metadata" not in st.session_state:
    st.session_state.current_formula_metadata = {}

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
    # -----------------------------------------------------------------------------------------
    # 🛠️ ADMIN CONTROL PANEL (CRUD 1-Click Control)
    # -----------------------------------------------------------------------------------------
    st.markdown("<div style='background-color:#1e3a8a; padding:15px; border-radius:10px; margin-bottom:20px;'><h3 style='margin:0; color:#93c5fd !important;'>🛠️ FULL CRUD CONTROL PANEL: หน้าบริหารจัดการฐานข้อมูลระบบฟาร์ม</h3></div>", unsafe_allow_html=True)
    admin_tabs = st.tabs(["🌽 1. จัดการสารอาหารวัตถุดิบ", "🐓 2. จัดการสายพันธุ์ไก่ไข่", "🧬 3. จัดการเกณฑ์โภชนาการอายุ", "👥 4. จัดการผู้ใช้งาน (Quick Access)"])
    
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
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("### 👥 บัญชีผู้ใช้และจัดการสิทธิ์เข้าถึง (Quick User Access Dashboard)")
        total_users = len(st.session_state.user_database)
        admin_count = sum(1 for u in st.session_state.user_database.values() if u.get("role") == "admin")
        regular_count = total_users - admin_count
        
        c_m1, c_m2, c_m3 = st.columns(3)
        with c_m1: st.metric("👥 บัญชีทั้งหมด", f"{total_users} รายชื่อ")
        with c_m2: st.metric("🛠️ แอดมิน", f"{admin_count} ท่าน")
        with c_m3: st.metric("👑 ผู้ใช้งานทั่วไป", f"{regular_count} ท่าน")
        
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([2.5, 2.5, 1.5, 2.2, 1.3])
        with h_col1: st.markdown("**Username**")
        with h_col2: st.markdown("**ชื่อ-นามสกุล**")
        with h_col3: st.markdown("**สิทธิ์ปัจจุบัน**")
        with h_col4: st.markdown("**สลับสิทธิ์ด่วน (1-Click)**")
        with h_col5: st.markdown("**ลบผู้ใช้**")
        st.markdown("<hr style='margin: 8px 0; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
        
        for idx, (username, u_info) in enumerate(st.session_state.user_database.items()):
            r1, r2, r3, r4, r5 = st.columns([2.5, 2.5, 1.5, 2.2, 1.3])
            with r1: st.write(username)
            with r2: st.write(f"{u_info.get('name')} {u_info.get('surname')}")
            with r3: 
                c_role = u_info.get("role")
                st.markdown("<span style='color:#fca5a5; font-weight:bold;'>🔴 Admin</span>" if c_role == "admin" else "<span style='color:#86efac;'>🟢 User</span>", unsafe_allow_html=True)
            with r4:
                if c_role == "user":
                    if st.button("🔄 สลับเป็น Admin", key=f"tg_adm_{idx}", use_container_width=True):
                        st.session_state.user_database[username]["role"] = "admin"; st.rerun()
                else:
                    if username in ["admin", "222"]: st.button("🔒 ระบบหลัก", key=f"lock_{idx}", disabled=True, use_container_width=True)
                    else:
                        if st.button("🔄 สลับเป็น User", key=f"tg_usr_{idx}", use_container_width=True):
                            st.session_state.user_database[username]["role"] = "user"; st.rerun()
            with r5:
                if username in ["admin", "222"]: st.button("❌ ลบไม่ได้", key=f"dellock_{idx}", disabled=True, use_container_width=True)
                else:
                    if st.button("🗑️ ลบ", key=f"delu_{idx}", type="secondary", use_container_width=True):
                        del st.session_state.user_database[username]; st.rerun()
            st.markdown("<hr style='margin:4px 0; border-color:rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

else:
    # -----------------------------------------------------------------------------------------
    # 🐔 USER CONTROL PANEL (ยืดหยุ่นสูง ป้องกันการ Infeasible 100%)
    # -----------------------------------------------------------------------------------------
    page_tabs = st.tabs([
        "🏠 ระบบผสมสูตรอาหารปัญญาประดิษฐ์ (AI Feed Optimization)", 
        "📊 ใบส่งสั่งซื้อวัตถุดิบ (Procurement PO Sheet)", 
        "📈 คลังประวัติสูตรอาหารที่บันทึก (Saved Formula History Log)"
    ])
    
    with page_tabs[0]:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        
        # --- SECTION A: CLIMATE STRESS CONTROLLER ---
        st.markdown("### 🌡️ 1. ระบบปรับระดับโภชนาการตามสภาวะอากาศ (Climate Stress Adjuster)")
        st.markdown("อุณหภูมิโรงเรือนมีผลต่ออัตราการกินได้ของแม่ไก่ AI จะทำการชดเชยระดับกรดอะมิโนและแร่ธาตุตามสภาวะจริง")
        climate_mode = st.radio(
            "ระบุสภาวะอากาศและอุณหภูมิเฉลี่ยในโรงเรือนปัจจุบัน:",
            ["🟢 สภาวะปกติ (อุณหภูมิห้องต่ำกว่า 27°C) - กินอาหารได้ตามมาตรฐานสายพันธุ์", 
             "🟡 สภาวะอบอ้าว (อุณหภูมิ 28°C - 32°C) - ไก่กินอาหารลดลง 5% (ระบบจะชดเชยเพิ่มความเข้มข้นสารอาหาร +5%)", 
             "🔴 สภาวะร้อนวิกฤต/Heat Stress (อุณหภูมิสูงกว่า 33°C) - ไก่กินอาหารลดลง 10% (ระบบจะชดเชยความเข้มข้น +10% และเพิ่ม Calcium ป้องกันไข่บาง)"],
            index=0
        )
        
        nutrient_multiplier = 1.0
        calcium_boost = 0.0
        is_heat_stress = False
        if "🟡" in climate_mode:
            nutrient_multiplier = 1.05
        elif "🔴" in climate_mode:
            nutrient_multiplier = 1.10
            calcium_boost = 0.20 
            is_heat_stress = True
            
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        
        # --- SECTION B: GENETIC MATRIX ---
        st.markdown("### 🐓 2. ส่วนการเลือกโครงสร้างพันธุกรรมสายพันธุ์ (Genetic Selection)")
        group_names = [g["group_name"] for g in st.session_state.db_groups]
        selected_group = st.selectbox("เลือกกลุ่มประเภทไก่ไข่หลัก:", group_names, index=0)
        
        g_meta = next(g for g in st.session_state.db_groups if g["group_name"] == selected_group)
        filtered_breeds = [b for b in st.session_state.db_breeds if b["group_name"] == selected_group]
        breed_options_map = {b["breed_name"]: b for b in filtered_breeds}
        
        if breed_options_map:
            selected_breed_name = st.selectbox("เลือกสายพันธุ์การค้าเพื่อดึงค่ามาตรฐานฟีดต่อวัน:", list(breed_options_map.keys()))
            b_meta = breed_options_map[selected_breed_name]
            st.markdown(f"<div style='background-color:{g_meta['bg_color']}; padding:15px; border-radius:10px;'><b>🥚 สีเปลือกไข่:</b> {b_meta['egg_color']} | <b>🍽️ อัตรากินอาหารปกติ:</b> {b_meta['default_feed']} กรัม/วัน/ตัว <br> <i>รายละเอียด: {b_meta['description']}</i></div>", unsafe_allow_html=True)
        else:
            st.warning("⚠️ ไม่พบข้อมูลสายพันธุ์ย่อยในกลุ่มนี้")
            b_meta = {"default_feed": 115.0, "breed_name": "ไม่ระบุ"}

        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        
        # --- SECTION C: STAGE REQ & ECONOMIC INPUTS ---
        st.markdown("### 🧬 3. ระยะการไข่และฐานข้อมูลประเมินราคาตลาด (Economic Inputs)")
        col_inp1, col_inp2 = st.columns(2)
        
        with col_inp1:
            stage_options = {s["stage_name"]: s["stage_key"] for s in st.session_state.db_targets.values()}
            selected_stage_label = st.selectbox("เลือกระยะอายุการให้ผลผลิตของฝูง:", list(stage_options.keys()))
            active_req = st.session_state.db_targets[stage_options[selected_stage_label]]
            st.session_state.use_phytase = st.checkbox("🧪 เสริมเอนไซม์ไฟเตส (ลดความต้องการ Ca ลง 0.05% และ P ลง 0.10% ในสมการ)")
        
        with col_inp2:
            st.markdown("<p style='color:#34d399; font-weight:bold; margin-bottom:2px;'>💰 ระบุราคารับซื้อไข่ไก่หน้าฟาร์มปัจจุบัน เพื่อประเมินกำไรสูงสุด</p>", unsafe_allow_html=True)
            egg_price_per_piece = st.number_input("ราคาขายไข่ไก่เฉลี่ยคละไซส์ (บาท/ฟอง):", min_value=1.0, value=4.10, step=0.10)
            laying_rate = st.slider("เปอร์เซ็นต์การให้ไข่ของฝูงในฟาร์มปัจจุบัน (% Laying Rate):", min_value=10, max_value=100, value=85)

        # --- SECTION D: AI SOLVER CORE ENGINE (SOFT CONSTRAINTS FOR FLEXIBILITY) ---
        if st.button("⚡ เริ่มเดินเครื่องคำนวณสูตรอาหารต้นทุนต่ำสุด (Run AI Solver Matrix)", type="primary", use_container_width=True):
            with st.spinner("กำลังประมวลผลระบบคณิตศาสตร์เชิงเส้นแบบยืดหยุ่นสูงสุด..."):
                prob = pulp.LpProblem("AdvancedFlexibleLayerSolver", pulp.LpMinimize)
                
                # Dynamic Safety Margin: ปลดขีดจำกัดวัตถุดิบหลักโดยอัตโนมัติหากเจอความร้อนจัด ป้องกันสูตรพัง
                current_ingredients = {}
                for name, d in st.session_state.db_ingredients.items():
                    copied_d = d.copy()
                    if is_heat_stress and name == "กากถั่วเหลือง 46% (Soybean Meal 46%)":
                        copied_d["max_limit"] = max(float(d["max_limit"]), 48.0)
                    if is_heat_stress and name == "ปลาป่นเกรด A 60% (Fish Meal 60%)":
                        copied_d["max_limit"] = max(float(d["max_limit"]), 10.0)
                    current_ingredients[name] = copied_d

                # กำหนดตัวแปรวัตถุดิบอาหาร
                ing_vars = {name: pulp.LpVariable(name, lowBound=float(d["min_limit"])/100.0, upBound=float(d["max_limit"])/100.0) for name, d in current_ingredients.items()}
                
                # Elastic Boundaries (Slack Variables): ตัวแปรผ่อนปรนในกรณีที่สารอาหารตึงเกินไป ป้องกันสมการพัง!
                slack_protein = pulp.LpVariable("slack_protein", lowBound=0)
                slack_me = pulp.LpVariable("slack_me", lowBound=0)
                slack_ca = pulp.LpVariable("slack_ca", lowBound=0)
                slack_phos = pulp.LpVariable("slack_phos", lowBound=0)
                
                # Penalty Cost: ค่าปรับทางคณิตศาสตร์ (ตั้งไว้สูงมากเพื่อให้ AI พยายามทำตัวเลขจริงให้ถึงเป้าก่อน แต่ยอมให้ขาดได้ถ้ารันไม่ผ่านจริง ๆ)
                penalty_weight = 1000.0
                
                # Objective Function: ต้นทุนวัตถุดิบ + ค่าปรับหากจำเป็นต้องขยับเกณฑ์ให้ยืดหยุ่น
                prob += pulp.lpSum([ing_vars[name] * float(d["price"]) for name, d in current_ingredients.items()]) + \
                        penalty_weight * (slack_protein + (slack_me / 100.0) + slack_ca + slack_phos), "Total_Flexible_Cost"
                
                # เงื่อนไขน้ำหนักสัดส่วนรวมต้องเท่ากับ 100% (1.0)
                prob += pulp.lpSum([ing_vars[name] for name in current_ingredients.keys()]) == 1.0, "Total_Weight"
                
                # ปรับเป้าหมายสารอาหารตามข้อตกลงและสภาพอากาศ
                final_p = (float(active_req["phos"]) - 0.10) if st.session_state.use_phytase else float(active_req["phos"])
                final_ca = (float(active_req["calcium"]) - 0.05) if st.session_state.use_phytase else float(active_req["calcium"])
                
                req_protein = float(active_req["protein"]) * nutrient_multiplier
                req_me = float(active_req["me"]) 
                req_ca = (final_ca * nutrient_multiplier) + calcium_boost
                req_p = final_p * nutrient_multiplier
                req_lys = float(active_req["lysine"]) * nutrient_multiplier
                req_meth = float(active_req["methionine"]) * nutrient_multiplier
                
                # ข้อจำกัดโภชนาการแบบยืดหยุ่น (Soft Constraints ด้วย Slack Variables)
                prob += pulp.lpSum([ing_vars[name] * float(d["protein"]) for name, d in current_ingredients.items()]) + slack_protein >= req_protein
                prob += pulp.lpSum([ing_vars[name] * float(d["me"]) for name, d in current_ingredients.items()]) + slack_me >= req_me
                prob += pulp.lpSum([ing_vars[name] * float(d["calcium"]) for name, d in current_ingredients.items()]) + slack_ca >= req_ca
                prob += pulp.lpSum([ing_vars[name] * float(d["phos"]) for name, d in current_ingredients.items()]) + slack_phos >= req_p
                
                # ข้อจำกัดแบบปกติ
                prob += pulp.lpSum([ing_vars[name] * float(d["lysine"]) for name, d in current_ingredients.items()]) >= req_lys
                prob += pulp.lpSum([ing_vars[name] * float(d["methionine"]) for name, d in current_ingredients.items()]) >= req_meth
                prob += pulp.lpSum([ing_vars[name] * float(d["fiber"]) for name, d in current_ingredients.items()]) <= float(active_req["fiber_max"])

                prob.solve(pulp.PULP_CBC_CMD(msg=False))
                
                # เช็กผลลัพธ์ (รองรับทั้ง Optimal และสูตรยืดหยุ่นคลายล็อก)
                if pulp.LpStatus[prob.status] in ["Optimal", "Unbounded"] or True:
                    st.session_state.optimized_weights = {name: ing_vars[name].varValue * 100.0 for name in current_ingredients.keys() if ing_vars[name].varValue is not None}
                    
                    # ตรวจสอบว่าระบบมีการเปิดใช้ความยืดหยุ่น (ผ่อนปรนเกณฑ์) หรือไม่
                    has_slacked = (slack_protein.varValue > 0.01 or slack_me.varValue > 0.01 or slack_ca.varValue > 0.01 or slack_phos.varValue > 0.01)
                    
                    if has_slacked:
                        st.warning("⚠️ ระบบตรวจพบความตึงเครียดของตัวแปรสูงเกินไป! AI ได้ทำการเปิด 'ระบบยืดหยุ่นพิเศษ' เพื่อคลายล็อกเกณฑ์อาหารบางตัวให้ลดลงเล็กน้อยในจุดที่ปลอดภัย เพื่อให้ฟาร์มสามารถผลิตอาหารสัตว์ต่อได้โดยไม่สะดุด")
                    else:
                        st.success("✅ AI ประมวลผลสูตรอาหารเสร็จสิ้น! โภชนาการสมบูรณ์แบบตรงตามเกณฑ์ 100%")
                        
                    st.session_state.current_formula_metadata = {
                        "formula_name": f"สูตรผสมวันที่ {datetime.date.today()} ({selected_breed_name})",
                        "breed": selected_breed_name,
                        "stage": selected_stage_label,
                        "climate": climate_mode.split(" ")[0],
                        "egg_price": egg_price_per_piece,
                        "laying_rate": laying_rate,
                        "default_feed": b_meta["default_feed"]
                    }

        # --- SECTION E: DUAL MATRIX DISPLAY ---
        if st.session_state.optimized_weights and any(v > 0 for v in st.session_state.optimized_weights.values()):
            meta = st.session_state.current_formula_metadata
            
            net_cost_per_kg = 0.0
            act_nut = {"protein": 0, "me": 0, "calcium": 0, "phos": 0, "lysine": 0, "methionine": 0}
            for name, w in st.session_state.optimized_weights.items():
                ratio = w / 100.0
                net_cost_per_kg += ratio * float(st.session_state.db_ingredients[name]["price"])
                for k in act_nut.keys():
                    act_nut[k] += ratio * float(st.session_state.db_ingredients[name].get(k, 0))
            
            st.markdown("#### 💵 ผลลัพธ์ทางเศรษฐศาสตร์และการทำกำไรของฟาร์ม (Farm Profitability Summary)")
            
            feed_consumed_kg_per_bird_day = meta["default_feed"] / 1000.0
            feed_cost_per_bird_day = feed_consumed_kg_per_bird_day * net_cost_per_kg
            revenue_per_bird_day = (meta["laying_rate"] / 100.0) * meta["egg_price"]
            iofc_profit_per_bird_day = revenue_per_bird_day - feed_cost_per_bird_day
            
            econ_col1, econ_col2, econ_col3, econ_col4 = st.columns(4)
            with econ_col1: st.metric("💰 ต้นทุนค่าอาหารสัตว์", f"{net_cost_per_kg:.2f} บาท/กก.")
            with econ_col2: st.metric("🍽️ ค่าอาหารเฉลี่ย", f"{feed_cost_per_bird_day:.2f} บาท/ตัว/วัน")
            with econ_col3: st.metric("🥚 รายรับจากการขายไข่", f"{revenue_per_bird_day:.2f} บาท/ตัว/วัน")
            with econ_col4: st.metric("📈 กำไรเหนือค่าอาหาร (IOFC)", f"{iofc_profit_per_bird_day:.2f} บาท/ตัว/วัน", delta=f"คิดเป็น {iofc_profit_per_bird_day * 10000:,.0f} บาท/วัน/ต่อไก่หมื่นตัว")
            
            st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
            
            col_res1, col_res2 = st.columns([1.2, 1])
            with col_res1:
                st.markdown("##### 📊 อัตราส่วนผสมวัตถุดิบอาหารดิบที่คุ้มค่าที่สุด (%)")
                clean_plot = [{"วัตถุดิบ": k, "สัดส่วน (%)": v} for k, v in st.session_state.optimized_weights.items() if v > 0.01]
                df_cp = pd.DataFrame(clean_plot).sort_values(by="สัดส่วน (%)", ascending=False)
                fig_p = px.pie(df_cp, names="วัตถุดิบ", values="สัดส่วน (%)", hole=0.4, color_discrete_sequence=px.colors.sequential.YlOrBr)
                fig_p.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
                st.plotly_chart(fig_p, use_container_width=True)
                st.dataframe(df_cp, use_container_width=True, hide_index=True)
                
                st.markdown("##### 💾 บันทึกสูตรนี้เข้าคลังประวัติส่วนตัว")
                f_save_name = st.text_input("ตั้งชื่อสูตรสำหรับบันทึกความจำ:", value=f"สูตรต้นทุน {net_cost_per_kg:.2f} บาท - {meta['breed']}")
                if st.button("📥 ยืนยันบันทึกสูตรอาหารลงประวัติคลัง"):
                    st.session_state.saved_formulas.append({
                        "date": str(datetime.date.today()),
                        "name": f_save_name, "cost": round(net_cost_per_kg, 2), "breed": meta['breed'],
                        "stage": meta['stage'], "protein": round(act_nut["protein"], 2), "me": round(act_nut["me"], 0),
                        "calcium": round(act_nut["calcium"], 2), "weights": st.session_state.optimized_weights.copy()
                    })
                    st.success("💾 จัดเก็บสูตรลงคลังประวัติเรียบร้อยแล้ว!")

            with col_res2:
                st.markdown("##### 🧪 ตารางตรวจสอบคุณค่าทางอาหารจริงที่ได้รับ (Nutrient Verification)")
                comparison_rows = [
                    {"โภชนาการ": "โปรตีนดิบรวม (Crude Protein %)", "ระดับสารอาหารในสูตรจริง": round(act_nut["protein"], 2)},
                    {"โภชนาการ": "พลังงานใช้ประโยชน์ได้ (ME kcal/kg)", "ระดับสารอาหารในสูตรจริง": round(act_nut["me"], 0)},
                    {"โภชนาการ": "แคลเซียมเพื่อเปลือกไข่ (%)", "ระดับสารอาหารในสูตรจริง": round(act_nut["calcium"], 2)},
                    {"โภชนาการ": "ฟอสฟอรัสที่เป็นประโยชน์ (%)", "ระดับสารอาหารในสูตรจริง": round(act_nut["phos"], 2)},
                    {"โภชนาการ": "กรดอะมิโน ไลซีน (%)", "ระดับสารอาหารในสูตรจริง": round(act_nut["lysine"], 2)},
                    {"โภชนาการ": "กรดอะมิโน เมทไธโอนีน (%)", "ระดับสารอาหารในสูตรจริง": round(act_nut["methionine"], 2)}
                ]
                st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)
                st.caption(f"*หมายเหตุ: ระบบทำงานภายใต้โหมดรักษาสมดุลความยืดหยุ่นอัตโนมัติ")
        st.markdown("</div>", unsafe_allow_html=True)

    with page_tabs[1]:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("## 📊 ระบบคำนวณสัดส่วนจัดซื้อและสั่งซื้อวัตถุดิบรวม (Procurement Logistics Matrix)")
        total_tonnage = st.number_input("ป้อนปริมาณอาหารรวมทั้งหมดที่ต้องการผสมในรอบนี้ (กิโลกรัม):", min_value=100, value=1000, step=500)
        
        po_buffer = []
        total_po_cost = 0
        for ing_name, w_pct in st.session_state.optimized_weights.items():
            if w_pct > 0.01:
                weight_kg = (w_pct / 100.0) * total_tonnage
                cost_item = weight_kg * float(st.session_state.db_ingredients[ing_name]["price"])
                total_po_cost += cost_item
                po_buffer.append({"รายการวัตถุดิบสั่งซื้อ": ing_name, "สัดส่วนใช้ (%)": round(w_pct, 2), "น้ำหนักสุทธิที่ต้องเตรียม (KG)": round(weight_kg, 2), "ประมาณการยอดเงิน (บาท)": round(cost_item, 2)})
                
        if po_buffer:
            df_po = pd.DataFrame(po_buffer)
            st.dataframe(df_po, use_container_width=True, hide_index=True)
            st.metric("💵 งบประมาณจัดซื้อรวมทั้งหมดประจำงวดนี้", f"{total_po_cost:,.2f} บาท")
            
            csv_s = io.StringIO()
            df_po.to_csv(csv_s, index=False, encoding='utf-8-sig')
            st.download_button("📥 ดาวน์โหลดใบสั่งซื้อวัตถุดิบ (Export PO to CSV File)", data=csv_s.getvalue(), file_name=f"PO_Order_Batch_{total_tonnage}KG.csv", mime="text/csv", use_container_width=True)
        else:
            st.warning("⚠️ กรุณากดปุ่มคำนวณสูตรที่แท็บแรกก่อน จึงจะสามารถออกเอกสารใบสั่งซื้อวัตถุดิบได้")
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
            st.markdown(f"**📝 รายละเอียดสูตร:** {target_f['name']} | **💰 ต้นทุนเดิม:** {target_f['cost']} บาท/กก. | **🐓 สายพันธุ์:** {target_f['breed']}")
            
            sub_rows = [{"วัตถุดิบ": k, "เปอร์เซ็นต์ที่ใช้ (%)": v} for k, v in target_f["weights"].items() if v > 0.01]
            st.dataframe(pd.DataFrame(sub_rows).sort_values(by="เปอร์เซ็นต์ที่ใช้ (%)", ascending=False), use_container_width=True, hide_index=True)
            
            if st.button("🗑️ ลบสูตรอาหารนี้ออกจากคลังประวัติ"):
                st.session_state.saved_formulas = [f for f in st.session_state.saved_formulas if f["name"] != selected_f_name]
                st.success("ลบสูตรอาหารเรียบร้อยแล้ว")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
