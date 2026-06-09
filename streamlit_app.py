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
        background-image: linear-gradient(rgba(0, 0, 0, 0.82), rgba(0, 0, 0, 0.82)), 
                          url("https://images.unsplash.com/photo-1548550023-2bdb3c5beed7?q=80&w=1920");
        background-size: cover; background-position: center;
        background-repeat: no-repeat; background-attachment: fixed;
    }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, [data-testid="stHeader"] {
        color: #ffffff !important;
        text-shadow: 2px 2px 5px rgba(0, 0, 0, 0.95) !important;
    }
    
    /* กล่อง Selectbox ขอบทองเด่นชัด */
    div[data-testid="stSelectbox"] > label {
        font-size: 1.25rem !important;
        font-weight: 800 !important;
        color: #ffb703 !important;
        margin-bottom: 8px !important;
        display: block;
    }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] {
        font-size: 1.15rem !important; 
        font-weight: bold !important;
        background-color: rgba(26, 26, 26, 0.9) !important;
        border: 2px solid #ffb703 !important; 
        border-radius: 10px !important;
        color: white !important;
    }
    
    /* อัตลักษณ์ Facebook Sign Up */
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
    
    /* ปุ่มสมัครสมาชิกสีเขียว Facebook */
    div.stButton > button[key="btn_fb_signup_trigger"] {
        background-color: #42b72a !important;
        color: white !important;
        font-size: 1.35rem !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        border: none !important;
        box-shadow: 0px 5px 15px rgba(66, 183, 42, 0.4) !important;
    }
    
    /* การ์ดครอบระบบ */
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(255, 255, 255, 0.1) !important;
        padding: 8px; border-radius: 10px; backdrop-filter: blur(10px);
    }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-weight: bold !important; font-size:1.05rem !important; }
    .content-card {
        background-color: rgba(0, 0, 0, 0.88) !important; padding: 30px;
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

if "user_database" not in st.session_state:
    st.session_state.user_database = {
        "admin": {"password": "222", "name": "ผู้ดูแลระบบ", "surname": "ระดับสูง", "role": "admin", "tel": "089-999-9999", "reg_date": "2026-01-01"},
        "222": {"password": "222", "name": "แอดมิน", "surname": "ทางลัด", "role": "admin", "tel": "088-888-8888", "reg_date": "2026-01-02"},
        "user_test@gmail.com": {"password": "123", "name": "สมชาย", "surname": "ใจดี", "role": "user", "tel": "081-234-5678", "reg_date": "2026-05-10"}
    }

# โครงสร้างคลังข้อมูลหลัก (ย้ายมาลง Session เพื่อให้สิทธิ์ Admin ทำ CRUD ลบ/เพิ่ม/แก้ไขได้แบบ Real-time)
if "db_groups" not in st.session_state:
    st.session_state.db_groups = [
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "bg_color": "#b45309", "text_color": "#ffffff", "market_trend": "ครองแชมป์ความนิยมอันดับ 1 ในทวีปเอเชีย ประเทศไทย และยุโรป โดดเด่นเรื่องขนาดฟองและเปลือกไข่หนา"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีขาว (Commercial White Layers)", "bg_color": "#0284c7", "text_color": "#ffffff", "market_trend": "ครองตลาดอเมริกาเหนือและโรงงานแปรรูปอุตสาหกรรม ให้ปริมาณไข่ดกสูงสุดและประหยัดต้นทุนอาหารดีเยี่ยม"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีครีมและพาสเทล (Commercial Tinted Layers)", "bg_color": "#0d9488", "text_color": "#ffffff", "market_trend": "ตลาดพรีเมียมยุคใหม่ เปลือกสีนวลชมพู/ครีม เป็นที่ต้องการของตลาดโมเดิร์นเทรดและผู้บริโภคระดับสูง"},
        {"group_name": "กลุ่มไก่ไข่ทางเลือกและไก่พื้นเมืองประยุกต์ (Heritage & Local Heritage Layers)", "bg_color": "#4f46e5", "text_color": "#ffffff", "market_trend": "เหมาะสำหรับฟาร์มปล่อยลาน ปศุสัตว์อินทรีย์ (Organic) และระบบขยายพันธุ์พึ่งพาตนเอง ทนทานโรคสูง"}
    ]

if "db_breeds" not in st.session_state:
    st.session_state.db_breeds = [
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "breed_key": "Isa Brown", "breed_name": "สายพันธุ์ ไอซ่า บราวน์ (Isa Brown)", "egg_color": "สีน้ำตาลเข้ม (Dark Brown Egg)", "default_feed": 114.0, "description": "สายพันธุ์ฝรั่งเศส ยอดนิยมอันดับ 1 ในไทย แข็งแรง ทนร้อนชื้นได้ดีเลิศ ผลผลิตนิ่งสม่ำเสมอ"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "breed_key": "Lohmann Brown", "breed_name": "สายพันธุ์ โลห์แมน บราวน์ (Lohmann Brown)", "egg_color": "สีน้ำตาลเงางาม (Glossy Brown Egg)", "default_feed": 116.0, "description": "สายพันธุ์เยอรมัน โดดเด่นเรื่องไข่ฟองใหญ่ เปอร์เซ็นต์ไข่ไซส์ XL สูงมาก เปลือกหนาเหนียวพิเศษ"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "breed_key": "Hy-Line Brown", "breed_name": "สายพันธุ์ ไฮ-ไลน์ บราวน์ (Hy-Line Brown)", "egg_color": "สีน้ำตาลประกายทอง (Golden Brown Egg)", "default_feed": 112.0, "description": "สายพันธุ์อเมริกา อารมณ์นิ่ง ไม่ตื่นตกใจง่าย อัตราเปลี่ยนอาหารเป็นน้ำหนักไข่ดีเยี่ยม เหมาะกับฟาร์มปิด"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีขาว (Commercial White Layers)", "breed_key": "Hy-Line W-36", "breed_name": "สายพันธุ์ ไฮ-ไลน์ ขาว ดับบลิว-36 (Hy-Line W-36)", "egg_color": "สีขาวสะอาดตา (Pure White Egg)", "default_feed": 101.0, "description": "แชมป์โลกด้านความประหยัด กินอาหารน้อยที่สุดในโลก ให้ไข่ฟองสีขาวข้นแน่น ปริมาณไข่ขาวหนาตัวดีมาก"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีครีมและพาสเทล (Commercial Tinted Layers)", "breed_key": "Lohmann Sandy", "breed_name": "สายพันธุ์ โลห์แมน แซนดี้ (Lohmann Sandy)", "egg_color": "สีครีมเม็ดทราย (Sandy Tinted Egg)", "default_feed": 110.0, "description": "ให้ผลผลิตไข่สีครีมพาสเทลอมชมพูสวยงาม อัตราการเปลี่ยนอาหารเป็นไข่ (FCR) ดีเยี่ยม นิยมมากในตลาดยุโรป"},
        {"group_name": "กลุ่มไก่ไข่ทางเลือกและไก่พื้นเมืองประยุกต์ (Heritage & Local Heritage Layers)", "breed_key": "Pradu Hang Dam Egg-Line", "breed_name": "สายพันธุ์ ประดู่หางดำเชียงใหม่ สายไข่ (Pradu Hang Dam)", "egg_color": "สีน้ำตาลอ่อนนวล (Native Cream-Brown Egg)", "default_feed": 120.0, "description": "สายพันธุ์ปรับปรุงโดยปศุสัตว์ไทย ทนร้อน ทนโรคสัตว์ปีกได้ดีเลิศ ไข่แดงฟองใหญ่ รสชาติมันเข้มข้น ตอบโจทย์วิถีไก่บ้าน"}
    ]

if "db_ingredients" not in st.session_state:
    st.session_state.db_ingredients = {
        "ข้าวโพดบดเม็ด (Ground Corn)": {"name": "ข้าวโพดบดเม็ด (Ground Corn)", "price": 13.5, "protein": 8.5, "me": 3300.0, "calcium": 0.02, "phos": 0.25, "lysine": 0.24, "methionine": 0.18, "threonine": 0.29, "fat": 3.8, "moisture": 12.0, "fiber": 2.2, "min_limit": 10.0, "max_limit": 65.0},
        "กากถั่วเหลือง 46% (Soybean Meal 46%)": {"name": "กากถั่วเหลือง 46% (Soybean Meal 46%)", "price": 19.5, "protein": 46.0, "me": 2440.0, "calcium": 0.25, "phos": 0.62, "lysine": 2.85, "methionine": 0.65, "threonine": 1.80, "fat": 1.5, "moisture": 11.0, "fiber": 3.5, "min_limit": 10.0, "max_limit": 40.0},
        "ปลาป่นเกรด A 60% (Fish Meal 60%)": {"name": "ปลาป่นเกรด A 60% (Fish Meal 60%)", "price": 35.0, "protein": 60.0, "me": 2850.0, "calcium": 5.00, "phos": 3.00, "lysine": 4.50, "methionine": 1.80, "threonine": 2.40, "fat": 8.0, "moisture": 10.0, "fiber": 1.0, "min_limit": 0.0, "max_limit": 8.0},
        "หินฝุ่นเม็ดหยาบ (Coarse Limestone)": {"name": "หินฝุ่นเม็ดหยาบ (Coarse Limestone)", "price": 2.5, "protein": 0.0, "me": 0.0, "calcium": 38.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 0.5, "fiber": 0.0, "min_limit": 0.0, "max_limit": 12.0},
        "ไดแคลเซียมฟอสเฟต (DCP 18%)": {"name": "ไดแคลเซียมฟอสเฟต (DCP 18%)", "price": 28.0, "protein": 0.0, "me": 0.0, "calcium": 21.00, "phos": 18.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 1.0, "fiber": 0.0, "min_limit": 0.0, "max_limit": 3.0},
        "เกลือแกงบริสุทธิ์ (Refined Salt)": {"name": "เกลือแกงบริสุทธิ์ (Refined Salt)", "price": 6.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 0.3, "fiber": 0.0, "min_limit": 0.15, "max_limit": 0.45},
        "พรีมิกซ์วิตามินแร่ธาตุ (Vitamin-Mineral Premix)": {"name": "พรีมิกซ์วิตามินแร่ธาตุ (Vitamin-Mineral Premix)", "price": 160.0, "protein": 0.0, "me": 0.0, "calcium": 5.00, "phos": 1.20, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 2.0, "fiber": 0.0, "min_limit": 0.25, "max_limit": 0.35}
    }

if "db_targets" not in st.session_state:
    st.session_state.db_targets = {
        "layer_phase_1": {"stage_key": "layer_phase_1", "stage_name": "ระยะผลิตไข่พีค ช่วงที่ 1 อายุ 19-45 สัปดาห์ (Production Phase 1)", "protein": 17.5, "me": 2750.0, "calcium": 4.10, "phos": 0.42, "lysine": 0.88, "methionine": 0.42, "fiber_max": 4.5},
        "layer_phase_2": {"stage_key": "layer_phase_2", "stage_name": "ระยะกลาง ช่วงที่ 2 อายุ 46-65 สัปดาห์ (Production Phase 2)", "protein": 16.5, "me": 2725.0, "calcium": 4.30, "phos": 0.38, "lysine": 0.82, "methionine": 0.39, "fiber_max": 5.0}
    }

if "optimized_weights" not in st.session_state:
    st.session_state.optimized_weights = {}

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
            if st.button("❓ ลืมรหัสผ่าน?", use_container_width=True):
                st.session_state.auth_page_mode = "forgot"
                st.rerun()
        with col_b2:
            if st.button("✨ สร้างบัญชีใหม่ (Sign Up)", use_container_width=True):
                st.session_state.auth_page_mode = "signup"
                st.rerun()
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
            if not reg_name or not reg_identity or not reg_password:
                st.error("⚠️ กรุณากรอกรายละเอียดให้ครบถ้วน")
            else:
                st.session_state.user_database[reg_identity] = {
                    "password": reg_password, "name": reg_name, "surname": reg_surname,
                    "role": "user", "tel": reg_identity, "reg_date": str(datetime.date.today())
                }
                st.success("🎉 สมัครสมาชิกสำเร็จ! กลับไปหน้าล็อกอินเพื่อเข้าใช้งาน")
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        if st.button("➡️ มีบัญชีอยู่แล้ว? เข้าสู่ระบบ", use_container_width=True):
            st.session_state.auth_page_mode = "login"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    elif st.session_state.auth_page_mode == "forgot":
        st.markdown("<div class='content-card' style='max-width: 550px; margin: 80px auto 0 auto;'>", unsafe_allow_html=True)
        forgot_identity = st.text_input("ระบุข้อมูลอีเมลหรือเบอร์โทรศัพท์:")
        if st.button("ดึงข้อมูลรหัสผ่าน", type="primary", use_container_width=True):
            if forgot_identity in st.session_state.user_database:
                st.success(f"💡 รหัสผ่านของคุณคือ: `{st.session_state.user_database[forgot_identity]['password']}`")
            else: st.error("❌ ไม่พบข้อมูลบัญชีนี้")
        if st.button("⬅️ กลับไปหน้าล็อกอิน", use_container_width=True):
            st.session_state.auth_page_mode = "login"
            st.rerun()
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
        st.rerun()
st.markdown("---")

# =========================================================================================
# 🛠️ 5. INTERACTION ROUTER
# =========================================================================================

# -----------------------------------------------------------------------------------------
# 🛠️ [CASE 1]: ADMIN CORE PANEL (Full CRUD Engine)
# -----------------------------------------------------------------------------------------
if st.session_state.user_role == "admin":
    st.markdown("<div style='background-color:#1e3a8a; padding:15px; border-radius:10px; margin-bottom:20px;'><h3 style='margin:0; color:#93c5fd !important;'>🛠️ FULL CRUD CONTROL PANEL: หน้าบริหารจัดการฐานข้อมูลระบบฟาร์ม</h3></div>", unsafe_allow_html=True)
    
    admin_tabs = st.tabs([
        "🌽 1. จัดการสารอาหารวัตถุดิบ (Raw Ingredients)", 
        "🐓 2. จัดการสายพันธุ์ไก่ไข่ (Breeds & Groups)", 
        "🧬 3. จัดการเกณฑ์โภชนาการอายุ (Nutrition Targets)",
        "👥 4. จัดการผู้ใช้งาน (User Accounts)"
    ])
    
    # --- TAP 1: วัตถุดิบ (CRUD Ingredients) ---
    with admin_tabs[0]:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("### 🌽 บริหารจัดการวัตถุดิบและคุณค่าทางโภชนาการ")
        
        # ส่วนแสดงผลลิสต์ปัจจุบัน
        df_ing = pd.DataFrame.from_dict(st.session_state.db_ingredients, orient='index')
        st.dataframe(df_ing, use_container_width=True)
        
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        sub_ing_col1, sub_ing_col2 = st.columns(2)
        
        with sub_ing_col1:
            st.markdown("#### ➕ เพิ่ม / ✏️ แก้ไข วัตถุดิบ")
            ing_name = st.text_input("ชื่อวัตถุดิบ (หากตรงกับของเดิมจะเป็นการอัปเดต):", placeholder="เช่น รำละเอียด (Fine Rice Bran)")
            ing_price = st.number_input("ราคา (บาท/กก.):", min_value=0.0, value=10.0, step=0.1)
            ing_prot = st.number_input("โปรตีนดิบ (%):", min_value=0.0, value=0.0, step=0.1)
            ing_me = st.number_input("พลังงานใช้ประโยชน์ได้ (ME kcal/kg):", min_value=0.0, value=0.0, step=10.0)
            ing_ca = st.number_input("แคลเซียม (%):", min_value=0.0, value=0.0, step=0.01)
            ing_phos = st.number_input("ฟอสฟอรัส (%):", min_value=0.0, value=0.0, step=0.01)
            ing_lys = st.number_input("ไลซีน (%):", min_value=0.0, value=0.0, step=0.01)
            ing_meth = st.number_input("เมทไธโอนีน (%):", min_value=0.0, value=0.0, step=0.01)
            ing_fiber = st.number_input("เยื่อใย/กาก (%):", min_value=0.0, value=0.0, step=0.1)
            ing_min = st.number_input("ขีดจำกัดขั้นต่ำในสูตร (%):", min_value=0.0, value=0.0, step=1.0)
            ing_max = st.number_input("ขีดจำกัดสูงสุดในสูตร (%):", min_value=0.0, value=100.0, step=1.0)
            
            if st.button("💾 บันทึกข้อมูลวัตถุดิบ (Add/Update Ingredient)", type="primary"):
                if ing_name:
                    st.session_state.db_ingredients[ing_name] = {
                        "name": ing_name, "price": ing_price, "protein": ing_prot, "me": ing_me,
                        "calcium": ing_ca, "phos": ing_phos, "lysine": ing_lys, "methionine": ing_meth,
                        "fiber": ing_fiber, "min_limit": ing_min, "max_limit": ing_max
                    }
                    st.success(f"บันทึกข้อมูล '{ing_name}' เรียบร้อย!")
                    st.rerun()
                else: st.error("กรุณากรอกชื่อวัตถุดิบ")
                
        with sub_ing_col2:
            st.markdown("#### ❌ ลบวัตถุดิบออกจากคลัง")
            ing_to_delete = st.selectbox("เลือกวัตถุดิบที่ต้องการลบถาวร:", list(st.session_state.db_ingredients.keys()), key="del_ing_box")
            if st.button("🗑️ ยืนยันการลบวัตถุดิบ", type="secondary"):
                if ing_to_delete in st.session_state.db_ingredients:
                    del st.session_state.db_ingredients[ing_to_delete]
                    st.warning(f"ลบวัตถุดิบ '{ing_to_delete}' ออกจากระบบแล้ว")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # --- TAP 2: สายพันธุ์และกลุ่มสายพันธุ์ (CRUD Breeds & Groups) ---
    with admin_tabs[1]:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("### 🐓 บริหารจัดการกลุ่มและรายสายพันธุ์ไก่ไข่")
        
        # แสดงตารางกลุ่มหลัก
        st.markdown("#### 📁 โครงสร้างกลุ่มหลักปัจจุบัน")
        st.dataframe(pd.DataFrame(st.session_state.db_groups), use_container_width=True)
        
        # เพิ่ม/ลบ กลุ่มหลัก
        g_c1, g_c2 = st.columns(2)
        with g_c1:
            new_g_name = st.text_input("➕ เพิ่มกลุ่มหลักใหม่:")
            new_g_trend = st.text_area("แนวโน้มตลาดของกลุ่มนี้:")
            if st.button("➕ บันทึกกลุ่มใหม่"):
                if new_g_name:
                    st.session_state.db_groups.append({"group_name": new_g_name, "bg_color": "#1e293b", "text_color": "#ffffff", "market_trend": new_g_trend})
                    st.success("เพิ่มกลุ่มสำเร็จ")
                    st.rerun()
        with g_c2:
            g_to_del = st.selectbox("🗑️ ลบกลุ่มหลัก (สายพันธุ์ข้างในจะถูกถอนออก):", [g["group_name"] for g in st.session_state.db_groups])
            if st.button("🗑️ ยืนยันลบกลุ่มหลัก"):
                st.session_state.db_groups = [g for g in st.session_state.db_groups if g["group_name"] != g_to_del]
                st.session_state.db_breeds = [b for b in st.session_state.db_breeds if b["group_name"] != g_to_del]
                st.warning("ลบกลุ่มหลักและสายพันธุ์ย่อยที่สังกัดเรียบร้อย")
                st.rerun()
                
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        
        # จัดการรายสายพันธุ์ย่อย
        st.markdown("#### 🪶 รายชื่อสายพันธุ์ย่อยทั้งหมดในระบบ")
        st.dataframe(pd.DataFrame(st.session_state.db_breeds), use_container_width=True)
        
        b_c1, b_c2 = st.columns(2)
        with b_c1:
            st.markdown("#### ➕ เพิ่ม / ✏️ อัปเดตสายพันธุ์")
            b_group = st.selectbox("สังกัดกลุ่มหลัก:", [g["group_name"] for g in st.session_state.db_groups], key="b_g_add")
            b_name = st.text_input("ชื่อสายพันธุ์ (หากตรงกับของเดิมจะถือเป็นการอัปเดตค่า):", placeholder="เช่น CP Brown")
            b_egg = st.text_input("สีเปลือกไข่เป้าหมาย:", value="สีน้ำตาลเข้ม")
            b_feed = st.number_input("เกณฑ์กินอาหารมาตรฐาน (กรัม/วัน/ตัว):", min_value=50.0, value=115.0)
            b_desc = st.text_area("คำอธิบาย/ข้อมูลเชิงลึกสายพันธุ์:")
            
            if st.button("💾 บันทึกข้อมูลสายพันธุ์"):
                if b_name:
                    # ค้นหาว่ามีอยู่แล้วไหมเพื่อเปลี่ยนค่า หรือแอดใหม่
                    exists = False
                    for b in st.session_state.db_breeds:
                        if b["breed_name"] == b_name:
                            b["group_name"] = b_group
                            b["egg_color"] = b_egg
                            b["default_feed"] = b_feed
                            b["description"] = b_desc
                            exists = True
                            break
                    if not exists:
                        st.session_state.db_breeds.append({
                            "group_name": b_group, "breed_key": b_name, "breed_name": b_name,
                            "egg_color": b_egg, "default_feed": b_feed, "description": b_desc
                        })
                    st.success(f"จัดเก็บข้อมูลสายพันธุ์ '{b_name}' สำเร็จ")
                    st.rerun()
                    
        with b_c2:
            st.markdown("#### ❌ ลบสายพันธุ์การค้า")
            b_to_del = st.selectbox("เลือกสายพันธุ์ที่ต้องการลบออกจากระบบ:", [b["breed_name"] for b in st.session_state.db_breeds])
            if st.button("🗑️ ยืนยันการลบสายพันธุ์"):
                st.session_state.db_breeds = [b for b in st.session_state.db_breeds if b["breed_name"] != b_to_del]
                st.warning(f"ลบสายพันธุ์ '{b_to_del}' สำเร็จ")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # --- TAP 3: เกณฑ์สารอาหารของแต่ละช่วงอายุ (CRUD Nutrition Targets) ---
    with admin_tabs[2]:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("### 🧬 บริหารเกณฑ์ความต้องการสารอาหารของแม่ไก่แยกตามระยะอายุ")
        
        df_tgt = pd.DataFrame.from_dict(st.session_state.db_targets, orient='index')
        st.dataframe(df_tgt, use_container_width=True)
        
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        t_c1, t_c2 = st.columns(2)
        with t_c1:
            st.markdown("#### ➕ เพิ่ม / ✏️ อัปเดตเกณฑ์ความต้องการ")
            t_key = st.text_input("คีย์อ้างอิงระบบ (อังกฤษห้ามเว้นวรรค):", placeholder="เช่น layer_phase_3")
            t_name = st.text_input("ชื่อระยะอายุแสดงผลฟาร์ม:", placeholder="เช่น ระยะท้าย อายุ 66 สัปดาห์ขึ้นไป")
            t_prot = st.number_input("ความต้องการโปรตีนขั้นต่ำ (%):", min_value=0.0, value=16.0)
            t_me = st.number_input("ความต้องการพลังงาน ME ขั้นต่ำ (kcal/kg):", min_value=0.0, value=2700.0)
            t_ca = st.number_input("ความต้องการแคลเซียมขั้นต่ำ (%):", min_value=0.0, value=4.0)
            t_phos = st.number_input("ความต้องการฟอสฟอรัสขั้นต่ำ (%):", min_value=0.0, value=0.35)
            t_lys = st.number_input("ความต้องการไลซีนขั้นต่ำ (%):", min_value=0.0, value=0.8)
            t_meth = st.number_input("ความต้องการเมทไธโอนีนขั้นต่ำ (%):", min_value=0.0, value=0.35)
            t_fiber = st.number_input("เกณฑ์กากใยสูงสุดยอมรับได้ (%):", min_value=0.0, value=5.0)
            
            if st.button("💾 บันทึกเกณฑ์ความต้องการ"):
                if t_key and t_name:
                    st.session_state.db_targets[t_key] = {
                        "stage_key": t_key, "stage_name": t_name, "protein": t_prot, "me": t_me,
                        "calcium": t_ca, "phos": t_phos, "lysine": t_lys, "methionine": t_meth, "fiber_max": t_fiber
                    }
                    st.success(f"บันทึกเกณฑ์ '{t_name}' เรียบร้อย")
                    st.rerun()
                    
        with t_c2:
            st.markdown("#### ❌ ลบเกณฑ์ความต้องการ")
            t_to_del = st.selectbox("เลือกเกณฑ์อายุที่ต้องการลบ:", list(st.session_state.db_targets.keys()))
            if st.button("🗑️ ยืนยันการลบเกณฑ์"):
                del st.session_state.db_targets[t_to_del]
                st.warning("ลบเกณฑ์สารอาหารเรียบร้อย")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # --- TAP 4: ผู้ใช้งาน (CRUD Users - ฉบับ Inline แก้ไขง่าย 1-Click) ---
    with admin_tabs[3]:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("### 👥 บัญชีผู้ใช้และจัดการสิทธิ์เข้าถึง (Quick User Access Dashboard)")
        st.markdown("จัดการสิทธิ์และลบผู้ใช้งานแบบด่วนได้ทันทีผ่านปุ่มท้ายแถวรายชื่อ")
        
        # 📊 ส่วนสรุปยอดบัญชีแบบดูง่าย
        total_users = len(st.session_state.user_database)
        admin_count = sum(1 for u in st.session_state.user_database.values() if u.get("role") == "admin")
        regular_count = total_users - admin_count
        
        c_metric1, c_metric2, c_metric3 = st.columns(3)
        with c_metric1:
            st.metric("👥 บัญชีผู้ใช้ทั้งหมดในระบบ", f"{total_users} บัญชี")
        with c_metric2:
            st.metric("🛠️ สิทธิ์ผู้ดูแลระบบ (Admin)", f"{admin_count} ท่าน")
        with c_metric3:
            st.metric("👑 สิทธิ์ผู้ใช้งาน (User)", f"{regular_count} ท่าน")
            
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        
        # 📋 สร้างโครงสร้างตารางแสดงผลรายบุคคลแบบ Custom พร้อมปุ่ม Action หลังแถว
        st.markdown("#### 📑 รายชื่อสมาชิกและแผงควบคุมสิทธิ์แบบด่วน (Inline Control)")
        
        # ส่วนหัวตาราง
        h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([2.5, 2.5, 1.5, 2.2, 1.3])
        with h_col1: st.markdown("**Username / Email**")
        with h_col2: st.markdown("**ชื่อ - นามสกุล**")
        with h_col3: st.markdown("**ระดับสิทธิ์ปัจจุบัน**")
        with h_col4: st.markdown("**สลับระดับสิทธิ์ (1-Click)**")
        with h_col5: st.markdown("**ลบไอดี**")
        st.markdown("<hr style='margin: 8px 0; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
        
        # ลูปเรนเดอร์รายชื่อผู้ใช้ทีละแถวพร้อมสร้างปุ่มกด
        for idx, (username, u_info) in enumerate(st.session_state.user_database.items()):
            row_col1, row_col2, row_col3, row_col4, row_col5 = st.columns([2.5, 2.5, 1.5, 2.2, 1.3])
            
            with row_col1:
                st.write(username)
            with row_col2:
                st.write(f"{u_info.get('name', '')} {u_info.get('surname', '')}")
            with row_col3:
                current_role = u_info.get("role", "user")
                if current_role == "admin":
                    st.markdown("<span style='color: #fca5a5; font-weight: bold;'>🔴 Admin</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span style='color: #86efac;'>🟢 User</span>", unsafe_allow_html=True)
                    
            with row_col4:
                # ปุ่มสลับสิทธิ์อัจฉริยะ (ถ้าเป็น User จะขึ้นให้สลับเป็น Admin / ถ้าเป็น Admin จะขึ้นให้สลับเป็น User)
                if current_role == "user":
                    if st.button("🔄 สลับเป็น Admin", key=f"toggle_adm_{idx}", use_container_width=True):
                        st.session_state.user_database[username]["role"] = "admin"
                        st.success(f"เปลี่ยนสิทธิ์คุณ {u_info.get('name')} เป็น Admin สำเร็จ!")
                        st.rerun()
                else:
                    # ป้องกันไม่ให้แอดมินเผลอปลดสิทธิ์ตัวเองจนระบบล็อก
                    if username == "admin" or username == "222":
                        st.button("🔒 บัญชีหลักระบบ", key=f"toggle_lock_{idx}", disabled=True, use_container_width=True)
                    else:
                        if st.button("🔄 สลับเป็น User", key=f"toggle_usr_{idx}", use_container_width=True):
                            st.session_state.user_database[username]["role"] = "user"
                            st.success(f"เปลี่ยนสิทธิ์คุณ {u_info.get('name')} เป็น User สำเร็จ!")
                            st.rerun()
                            
            with row_col5:
                # ปุ่มลบไอดีรายบุคคลออกจากระบบ
                if username == "admin" or username == "222":
                    st.button("❌ ลบไม่ได้", key=f"del_lock_{idx}", disabled=True, use_container_width=True)
                else:
                    if st.button("🗑️ ลบ", key=f"del_usr_{idx}", type="secondary", use_container_width=True):
                        del st.session_state.user_database[username]
                        st.warning(f"ลบบัญชีผู้ใช้งาน {username} ออกเรียบร้อยแล้ว")
                        st.rerun()
                        
            st.markdown("<hr style='margin: 4px 0; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------------------
# 🐔 [CASE 2]: USER PANEL (AI Optimizer Engine ดึงข้อมูลสดจากที่ Admin แก้ไขข้างบน)
# -----------------------------------------------------------------------------------------
else:
    page_tabs = st.tabs(["🏠 ระบบผสมสูตรอาหารปัญญาประดิษฐ์ (AI Feed Optimization)", "📊 แผนสถิติและใบสั่งซื้อวัตถุดิบ (Procurement & PO Sheet)"])
    
    with page_tabs[0]:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("## 📊 ส่วนการเลือกโครงสร้างพันธุกรรมสายพันธุ์ (Genetic Matrix Selection)")
        
        group_names = [g["group_name"] for g in st.session_state.db_groups]
        if not group_names:
            st.error("❌ ระบบส่วนกลางไม่มีข้อมูลกลุ่มกรุณาให้แอดมินมาเพิ่มในระบบหลังบ้านก่อนครับ")
            st.stop()
            
        selected_group = st.selectbox("🗂️ 1. เลือกคัดกรองตามกลุ่มประเภทไก่ไข่หลัก:", group_names, index=0)
        
        g_meta = next(g for g in st.session_state.db_groups if g["group_name"] == selected_group)
        filtered_breeds = [b for b in st.session_state.db_breeds if b["group_name"] == selected_group]
        breed_options_map = {b["breed_name"]: b for b in filtered_breeds}
        
        if breed_options_map:
            selected_breed_name = st.selectbox("🐓 2. คัดกรองเจาะลึกรายสายพันธุ์การค้าอัตโนมัติ:", list(breed_options_map.keys()))
            b_meta = breed_options_map[selected_breed_name]
            
            st.markdown(f"""
            <div style='background-color: {g_meta["bg_color"]}; padding: 25px; border-radius: 16px; border: 2.5px solid rgba(255,255,255,0.25); margin-top:15px;'>
                <h4 style='margin:0; color:{g_meta["text_color"]} !important;'>📋 รายละเอียดโปรไฟล์พันธุกรรม: {b_meta["breed_name"]}</h4>
                <p style='margin:12px 0 0 0; color:{g_meta["text_color"]} !important; line-height: 1.6;'>
                    <b>🥚 สีเปลือกไข่เป้าหมาย:</b> {b_meta["egg_color"]}<br>
                    <b>🍽️ เกณฑ์การกินอาหารมาตรฐาน:</b> <span style='color:#ffb703; font-weight:bold; font-size:1.2rem;'>{b_meta["default_feed"]}</span> กรัม/วัน/ตัว<br>
                    <b>💡 ข้อมูลประจำสายพันธุ์:</b> {b_meta["description"]}
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ ไม่พบรายชื่อสายพันธุ์ย่อยภายใต้กลุ่มหลักนี้")

        st.markdown("---")
        st.markdown("### 🧬 3. กำหนดระยะอายุและเป้าหมายสารอาหารที่ต้องการ")
        stage_options = {s["stage_name"]: s["stage_key"] for s in st.session_state.db_targets.values()}
        
        if not stage_options:
            st.error("❌ ไม่มีข้อมูลเกณฑ์ความต้องการอาหารสัตว์ในระบบ")
            st.stop()
            
        selected_stage_label = st.selectbox("เลือกระยะอายุการให้ผลผลิตของฝูง:", list(stage_options.keys()))
        active_req = st.session_state.db_targets[stage_options[selected_stage_label]]
        
        st.session_state.use_phytase = st.checkbox("🧪 เปิดใช้งานเอนไซม์ไฟเตสเสริม (-0.05% Ca, -0.10% Available P)")
        
        if st.button("⚡ เริ่มเดินเครื่องคำนวณสูตรอาหารต้นทุนต่ำสุด (Run AI Solver)", type="primary", use_container_width=True):
            if not st.session_state.db_ingredients:
                st.error("❌ ไม่มีวัตถุดิบหลงเหลืออยู่ในคลังข้อมูลผสมโปรแกรม")
            else:
                with st.spinner("กำลังประมวลผลทางคณิตศาสตร์เชิงเส้น..."):
                    prob = pulp.LpProblem("LayerLinearSolver", pulp.LpMinimize)
                    ing_vars = {name: pulp.LpVariable(name, lowBound=float(d["min_limit"])/100.0, upBound=float(d["max_limit"])/100.0) for name, d in st.session_state.db_ingredients.items()}
                    
                    prob += pulp.lpSum([ing_vars[name] * float(d["price"]) for name, d in st.session_state.db_ingredients.items()]), "Total_Cost"
                    prob += pulp.lpSum([ing_vars[name] for name in st.session_state.db_ingredients.keys()]) == 1.0, "Total_Weight"
                    
                    final_p = float(active_req["phos"]) - 0.10 if st.session_state.use_phytase else float(active_req["phos"])
                    final_ca = float(active_req["calcium"]) - 0.05 if st.session_state.use_phytase else float(active_req["calcium"])
                    
                    prob += pulp.lpSum([ing_vars[name] * float(d["protein"]) for name, d in st.session_state.db_ingredients.items()]) >= float(active_req["protein"])
                    prob += pulp.lpSum([ing_vars[name] * float(d["me"]) for name, d in st.session_state.db_ingredients.items()]) >= float(active_req["me"])
                    prob += pulp.lpSum([ing_vars[name] * float(d["calcium"]) for name, d in st.session_state.db_ingredients.items()]) >= final_ca
                    prob += pulp.lpSum([ing_vars[name] * float(d["phos"]) for name, d in st.session_state.db_ingredients.items()]) >= final_p
                    prob += pulp.lpSum([ing_vars[name] * float(d["lysine"]) for name, d in st.session_state.db_ingredients.items()]) >= float(active_req["lysine"])
                    prob += pulp.lpSum([ing_vars[name] * float(d["methionine"]) for name, d in st.session_state.db_ingredients.items()]) >= float(active_req["methionine"])
                    prob += pulp.lpSum([ing_vars[name] * float(d["fiber"]) for name, d in st.session_state.db_ingredients.items()]) <= float(active_req["fiber_max"])

                    prob.solve(pulp.PULP_CBC_CMD(msg=False))
                    
                    if pulp.LpStatus[prob.status] == "Optimal":
                        st.success("✅ AI ประมวลผลสำเร็จตามข้อมูลวัตถุดิบล่าสุด!")
                        st.session_state.optimized_weights = {name: ing_vars[name].varValue * 100.0 for name in st.session_state.db_ingredients.keys()}
                    else:
                        st.session_state.optimized_weights = {}
                        st.error("❌ ไม่สามารถคำนวณหาจุดสมดุลได้เนื่องจากเกณฑ์แน่นเกินไป หรือราคาวัตถุดิบบางตัวถูกตัดออก")

        if st.session_state.optimized_weights and any(v > 0 for v in st.session_state.optimized_weights.values()):
            col_res1, col_res2 = st.columns([1.2, 1])
            with col_res1:
                st.markdown("#### 📊 แผนภาพวงกลมสัดส่วนวัตถุดิบอาหารที่ใช้ (%)")
                clean_plot = [{"วัตถุดิบอาหาร": k, "สัดส่วนที่ใช้ (%)": v} for k, v in st.session_state.optimized_weights.items() if v > 0.01]
                df_cp = pd.DataFrame(clean_plot).sort_values(by="สัดส่วนที่ใช้ (%)", ascending=False)
                fig_p = px.pie(df_cp, names="วัตถุดิบอาหาร", values="สัดส่วนที่ใช้ (%)", hole=0.45, color_discrete_sequence=px.colors.sequential.YlOrBr)
                fig_p.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
                st.plotly_chart(fig_p, use_container_width=True)
                st.dataframe(df_cp, use_container_width=True, hide_index=True)

            with col_res2:
                st.markdown("#### 🧪 สรุปผลตรวจสอบระดับโภชนาการจริง")
                act_nut = {"protein": 0, "me": 0, "calcium": 0, "phos": 0, "lysine": 0, "methionine": 0, "fiber": 0}
                net_cost = 0
                for name, w in st.session_state.optimized_weights.items():
                    if w > 0 and name in st.session_state.db_ingredients:
                        ratio = w / 100.0
                        net_cost += ratio * float(st.session_state.db_ingredients[name]["price"])
                        for n_key in act_nut.keys():
                            if n_key in st.session_state.db_ingredients[name]:
                                act_nut[n_key] += ratio * float(st.session_state.db_ingredients[name][n_key])
                
                comparison_rows = [
                    {"โภชนาการ": "โปรตีนดิบรวม (Crude Protein %)", "ค่าจริง": round(act_nut["protein"], 2), "เกณฑ์กำหนด": f">= {active_req['protein']}"},
                    {"โภชนาการ": "พลังงานใช้ประโยชน์ได้ (ME kcal/kg)", "ค่าจริง": round(act_nut["me"], 0), "เกณฑ์กำหนด": f">= {active_req['me']}"},
                    {"โภชนาการ": "แคลเซียมเพื่อเปลือกไข่ (%)", "ค่าจริง": round(act_nut["calcium"], 2), "เกณฑ์กำหนด": f">= {active_req['calcium']}"},
                    {"โภชนาการ": "ฟอสฟอรัสที่เป็นประโยชน์ (%)", "ค่าจริง": round(act_nut["phos"], 2), "เกณฑ์กำหนด": f">= {active_req['phos']}"},
                    {"โภชนาการ": "กรดอะมิโน ไลซีน (%)", "ค่าจริง": round(act_nut["lysine"], 2), "เกณฑ์กำหนด": f">= {active_req['lysine']}"},
                    {"โภชนาการ": "กรดอะมิโน เมทไธโอนีน (%)", "ค่าจริง": round(act_nut["methionine"], 2), "เกณฑ์กำหนด": f">= {active_req['methionine']}"}
                ]
                st.markdown(f"<h3 style='color:#ffb703 !important; text-align:center;'>💰 ต้นทุนสูตรอาหาร: {net_cost:.2f} บาท/กก.</h3>", unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with page_tabs[1]:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("<h2>📊 ระบบประเมินน้ำหนักวัตถุดิบเพื่อส่งจัดซื้อ</h2>")
        
        total_tonnage = st.number_input("ป้อนยอดการผลิตล๊อตนี้ (กิโลกรัม):", min_value=100, value=2000, step=500)
        
        po_table_buffer = []
        accumulated_po_cost = 0
        
        for ing_title, weight_percentage in st.session_state.optimized_weights.items():
            if weight_percentage > 0.01 and ing_title in st.session_state.db_ingredients:
                exact_weight_kg = (weight_percentage / 100.0) * total_tonnage
                item_cost_evaluation = exact_weight_kg * float(st.session_state.db_ingredients[ing_title]["price"])
                accumulated_po_cost += item_cost_evaluation
                po_table_buffer.append({
                    "รายการวัตถุดิบ (Material Description)": ing_title,
                    "น้ำหนักสุทธิที่ต้องใช้ (KG)": round(exact_weight_kg, 2),
                    "ราคารวมโดยประมาณ (THB)": round(item_cost_evaluation, 2)
                })
                
        if po_table_buffer:
            df_final_po = pd.DataFrame(po_table_buffer)
            st.dataframe(df_final_po, use_container_width=True, hide_index=True)
            st.metric("💵 ยอดงบประมาณรวมจัดจัดซื้อสุทธิ", f"{accumulated_po_cost:,.2f} บาท")
            
            csv_stream = io.StringIO()
            df_final_po.to_csv(csv_stream, index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 ดาวน์โหลดใบส่งสั่งซื้อ (Export PO to CSV)",
                data=csv_stream.getvalue(),
                file_name=f"PO_Batch_{total_tonnage}KG.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.warning("⚠️ ไม่พบโครงสร้างสูตร กรุณากดปุ่มคำนวณในแท็บแรกก่อนเสร็จสิ้น")
        st.markdown("</div>", unsafe_allow_html=True)
