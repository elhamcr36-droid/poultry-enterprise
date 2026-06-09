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

# ปรับแต่งธีมสไตล์ Cyber Dark และยกระดับกล่อง Selectbox และฟอร์มสมัครสมาชิกสไตล์ Facebook ให้เด่นชัดที่สุด
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
    
    /* 🎯 จุดปรับโครงสร้างกล่องตัวเลือก (Selectbox) ทั้งระบบให้ใหญ่ยักษ์และกดง่าย ขอบทองอร่าม */
    div[data-testid="stSelectbox"] > label {
        font-size: 1.45rem !important;
        font-weight: 800 !important;
        color: #ffb703 !important;
        margin-bottom: 12px !important;
        display: block;
    }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] {
        font-size: 1.35rem !important; 
        font-weight: bold !important;
        background-color: rgba(26, 26, 26, 0.9) !important;
        border: 3px solid #ffb703 !important; 
        border-radius: 14px !important;
        padding: 8px 12px !important;
        box-shadow: 0px 4px 15px rgba(245, 158, 11, 0.25) !important;
        transition: all 0.3s ease-in-out;
    }
    div[data-testid="stSelectbox"] div[data-baseweb="select"]:hover {
        border-color: #f59e0b !important;
        box-shadow: 0px 6px 20px rgba(245, 158, 11, 0.45) !important;
    }
    div[data-baseweb="popover"] ul {
        background-color: #1e1e1e !important;
        font-size: 1.25rem !important;
    }
    
    /* 👥 สไตล์จำลองอัตลักษณ์ Facebook Sign Up */
    .fb-header {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #1877f2 !important;
        font-size: 3.2rem !important;
        font-weight: bold !important;
        text-align: center;
        margin-bottom: 2px;
        letter-spacing: -1.5px;
        text-shadow: none !important;
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
    /* ปุ่มสมัครสมาชิกสีเขียวสดสไตล์ Facebook */
    div.stButton > button[key="btn_fb_signup_trigger"] {
        background-color: #42b72a !important;
        color: white !important;
        font-size: 1.35rem !important;
        font-weight: bold !important;
        padding: 10px 40px !important;
        border-radius: 8px !important;
        border: none !important;
        box-shadow: 0px 5px 15px rgba(66, 183, 42, 0.4) !important;
        transition: all 0.2s;
    }
    div.stButton > button[key="btn_fb_signup_trigger"]:hover {
        background-color: #36a420 !important;
        transform: scale(1.02);
    }
    
    /* การ์ดและแท็บครอบระบบ */
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(255, 255, 255, 0.1) !important;
        padding: 8px; border-radius: 10px; backdrop-filter: blur(10px);
    }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-weight: bold !important; font-size:1.1rem !important; }
    .content-card {
        background-color: rgba(0, 0, 0, 0.88) !important; padding: 30px;
        border-radius: 18px; border: 1px solid rgba(255, 255, 255, 0.18);
        backdrop-filter: blur(10px); margin-bottom: 25px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem !important; color: #ffb703 !important;
        font-weight: bold !important;
    }
    [data-testid="stDataFrame"] { background-color: rgba(255,255,255,0.95) !important; border-radius: 8px; padding: 5px; }
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================================
# 🔐 2. SECURITY & ROLE-BASED ACCESS GATEWAY
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

CORRECT_URL = "https://nxyncxqbtntlpzqessou.supabase.co"
CORRECT_KEY = "sb_publishable_m411zYbsazCAsmmUMIuMkA_ypb1BYPr"

# ตรวจสอบสิทธิ์การเข้าถึง หากยังไม่ล็อกอินให้แสดงหน้า Login/Register กั้นไว้ก่อน
if not st.session_state.is_authenticated:
    
    # --- 2.1 หน้าล็อกอิน (Login Gate) ---
    if st.session_state.auth_page_mode == "login":
        st.markdown("<div class='content-card' style='max-width: 550px; margin: 80px auto 0 auto;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #ffb703 !important;'>🔐 ระบบวิเคราะห์โภชนาการและจัดการสายพันธุ์ไก่ไข่ระดับสากล</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; opacity:0.75;'>Layer Nutrition Studio Professional Enterprise</p>", unsafe_allow_html=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        
        email_login = st.text_input("📧 อีเมลผู้ใช้งาน หรือรหัสทางลัด (Email / Username):", key="login_email")
        pass_login = st.text_input("🔑 รหัสผ่านเข้าใช้งาน (Password):", type="password", key="login_pass")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("เข้าสู่ระบบ (Log In)", type="primary", use_container_width=True):
            if email_login in st.session_state.user_database and st.session_state.user_database[email_login]["password"] == pass_login:
                user_info = st.session_state.user_database[email_login]
                
                # ฝังค่าสถานะและสิทธิ์ลงใน Session ทันทีก่อน Rerun
                st.session_state.is_authenticated = True
                st.session_state.user_role = user_info.get("role", "user")
                
                if st.session_state.user_role == "admin":
                    st.session_state.user_email = f"🛠️ แอดมิน: คุณ {user_info['name']} {user_info['surname']}"
                else:
                    st.session_state.user_email = f"👑 คุณ {user_info['name']} {user_info['surname']} ({email_login})"
                    
                st.session_state.supabase_url = CORRECT_URL
                st.session_state.supabase_key = CORRECT_KEY
                st.rerun()
            else:
                st.error("❌ ข้อมูลสิทธิ์เข้าใช้งานไม่ถูกต้อง! (สำหรับแอดมินทดสอบระบบ ให้ป้อนไอดี '222' และรหัสผ่าน '222')")
        
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

    # --- 2.2 หน้าสมัครสมาชิกดีไซน์ Facebook ---
    elif st.session_state.auth_page_mode == "signup":
        st.markdown("<div class='content-card' style='max-width: 620px; margin: 40px auto 0 auto;'>", unsafe_allow_html=True)
        st.markdown("<h1 class='fb-header'>facebook</h1>", unsafe_allow_html=True)
        st.markdown("<p class='fb-subtitle'><b>สร้างบัญชีใหม่</b> <br><span style='font-size:0.95rem; opacity:0.8;'>ง่ายและรวดเร็วเพื่อร่วมงานกับฟาร์มของเรา</span></p>", unsafe_allow_html=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        
        col_name1, col_name2 = st.columns(2)
        with col_name1:
            reg_name = st.text_input("ชื่อจริง (First name)", placeholder="กรอกชื่อจริง")
        with col_name2:
            reg_surname = st.text_input("นามสกุล (Surname)", placeholder="กรอกนามสกุล")
            
        reg_identity = st.text_input("หมายเลขโทรศัพท์มือถือหรืออีเมล (Mobile number or email)", placeholder="ระบุไอดีสำหรับการล็อกอินครั้งถัดไป")
        reg_password = st.text_input("รหัสผ่านใหม่ (New password)", type="password", placeholder="ตั้งรหัสผ่านใหม่อย่างน้อย 4 หลักขึ้นไป")
        
        st.markdown("<p style='margin-bottom:2px; font-weight:bold; color:#ffffff; font-size:0.95rem;'>วันเกิด (Birthday)</p>", unsafe_allow_html=True)
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            birth_day = st.selectbox("วัน", list(range(1, 32)), index=datetime.datetime.now().day - 1)
        with col_d2:
            months_th = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
            birth_month = st.selectbox("เดือน", months_th, index=datetime.datetime.now().month - 1)
        with col_d3:
            current_year_th = datetime.datetime.now().year + 543
            birth_year = st.selectbox("ปี (พ.ศ.)", list(range(current_year_th - 90, current_year_th + 1)), index=72)
            
        st.markdown("<p style='margin-bottom:4px; font-weight:bold; color:#ffffff; font-size:0.95rem; margin-top:10px;'>เพศ (Gender)</p>", unsafe_allow_html=True)
        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1:
            st.markdown("<div style='border: 1px solid rgba(255,255,255,0.25); padding: 8px; border-radius:6px; text-align:center; background:rgba(255,255,255,0.05);'>หญิง 👩‍💼</div>", unsafe_allow_html=True)
            gender_female = st.checkbox("สมัครในสิทธิ์เพศหญิง", label_visibility="collapsed")
        with col_g2:
            st.markdown("<div style='border: 1px solid rgba(255,255,255,0.25); padding: 8px; border-radius:6px; text-align:center; background:rgba(255,255,255,0.05);'>ชาย 👨‍💼</div>", unsafe_allow_html=True)
            gender_male = st.checkbox("สมัครในสิทธิ์เพศชาย", label_visibility="collapsed")
        with col_g3:
            st.markdown("<div style='border: 1px solid rgba(255,255,255,0.25); padding: 8px; border-radius:6px; text-align:center; background:rgba(255,255,255,0.05);'>อื่นๆ 🌈</div>", unsafe_allow_html=True)
            gender_other = st.checkbox("สมัครในสิทธิ์ทางเลือก", label_visibility="collapsed")
            
        if st.button("สมัครสมาชิก (Sign Up)", key="btn_fb_signup_trigger", use_container_width=True):
            if not reg_name or not reg_surname or not reg_identity or not reg_password:
                st.error("⚠️ กรุณากรอกรายละเอียดส่วนบุคคลที่สำคัญให้ครบถ้วนทุกช่องก่อนส่งข้อมูลครับ")
            else:
                st.session_state.user_database[reg_identity] = {
                    "password": reg_password,
                    "name": reg_name,
                    "surname": reg_surname,
                    "role": "user",
                    "tel": reg_identity if reg_identity.isdigit() else "ไม่ได้ระบุ",
                    "reg_date": str(datetime.date.today())
                }
                st.success(f"🎉 บัญชีผู้ใช้ของคุณ {reg_name} ถูกจัดเก็บในฐานข้อมูลเรียบร้อยแล้ว ย้อนกลับเพื่อล็อกอินได้เลย!")
                
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        if st.button("➡️ มีบัญชีผู้ใช้งานอยู่แล้ว? ย้อนกลับไปล็อกอิน", use_container_width=True):
            st.session_state.auth_page_mode = "login"
            st.rerun()
            
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    # --- 2.3 หน้าลืมรหัสผ่าน ---
    elif st.session_state.auth_page_mode == "forgot":
        st.markdown("<div class='content-card' style='max-width: 550px; margin: 80px auto 0 auto;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='color:#f59e0b !important;'>🔍 ค้นหาบัญชีของคุณ (Find Your Account)</h2>", unsafe_allow_html=True)
        st.markdown("<p style='opacity:0.85;'>โปรดระบุที่อยู่อีเมลหรือเบอร์มือถือที่ใช้สมัครสมาชิกไว้เพื่อดึงข้อมูลรหัสผ่าน</p>", unsafe_allow_html=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        
        forgot_identity = st.text_input("ระบุข้อมูลอีเมลหรือเบอร์โทรศัพท์มือถือ:")
        
        if st.button("ตรวจสอบสิทธิ์และดึงรหัสผ่าน (Retrieve Password)", type="primary", use_container_width=True):
            if forgot_identity in st.session_state.user_database:
                account_found = st.session_state.user_database[forgot_identity]
                st.success(f"📧 ระบบจับคู่บัญชีสำเร็จ! คุณคือ {account_found['name']} {account_found['surname']}")
                st.info(f"💡 **รหัสผ่านของคุณคือ:** `{account_found['password']}`")
            else:
                st.error("❌ ไม่พบข้อมูลรายชื่อสมาชิกรายนี้ในระบบฟาร์ม")
                
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        if st.button("⬅️ ย้อนกลับไปหน้าล็อกอิน (Back to Login)", use_container_width=True):
            st.session_state.auth_page_mode = "login"
            st.rerun()
            
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

# ==========================================
# 📥 3. DATA ACQUISITION & BIG-DATA FAILSAFE
# ==========================================
@st.cache_data(ttl=2)
def fetch_complete_layer_data(url, key):
    groups_data = [
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "bg_color": "#b45309", "text_color": "#ffffff", "market_trend": "ครองแชมป์ความนิยมอันดับ 1 ในทวีปเอเชีย ประเทศไทย และยุโรป โดดเด่นเรื่องขนาดฟองและเปลือกไข่หนา"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีขาว (Commercial White Layers)", "bg_color": "#0284c7", "text_color": "#ffffff", "market_trend": "ครองตลาดอเมริกาเหนือและโรงงานแปรรูปอุตสาหกรรม ให้ปริมาณไข่ดกสูงสุดและประหยัดต้นทุนอาหารดีเยี่ยม"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีครีมและพาสเทล (Commercial Tinted Layers)", "bg_color": "#0d9488", "text_color": "#ffffff", "market_trend": "ตลาดพรีเมียมยุคใหม่ เปลือกสีนวลชมพู/ครีม เป็นที่ต้องการของตลาดโมเดิร์นเทรดและผู้บริโภคระดับสูง"},
        {"group_name": "กลุ่มไก่ไข่ทางเลือกและไก่พื้นเมืองประยุกต์ (Heritage & Local Heritage Layers)", "bg_color": "#4f46e5", "text_color": "#ffffff", "market_trend": "เหมาะสำหรับฟาร์มปล่อยลาน ปศุสัตว์อินทรีย์ (Organic) และระบบขยายพันธุ์พึ่งพาตนเอง ทนทานโรคสูง"}
    ]
    
    breeds_data = [
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "breed_key": "Isa Brown", "breed_name": "สายพันธุ์ ไอซ่า บราวน์ (Isa Brown)", "egg_color": "สีน้ำตาลเข้ม (Dark Brown Egg)", "default_feed": 114, "description": "สายพันธุ์ฝรั่งเศส ยอดนิยมอันดับ 1 ในไทย แข็งแรง ทนร้อนชื้นได้ดีเลิศ ผลผลิตนิ่งสม่ำเสมอ"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "breed_key": "Lohmann Brown", "breed_name": "สายพันธุ์ โลห์แมน บราวน์ (Lohmann Brown)", "egg_color": "สีน้ำตาลเงางาม (Glossy Brown Egg)", "default_feed": 116, "description": "สายพันธุ์เยอรมัน โดดเด่นเรื่องไข่ฟองใหญ่ เปอร์เซ็นต์ไข่ไซส์ XL สูงมาก เปลือกหนาเหนียวพิเศษ"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "breed_key": "Hy-Line Brown", "breed_name": "สายพันธุ์ ไฮ-ไลน์ บราวน์ (Hy-Line Brown)", "egg_color": "สีน้ำตาลประกายทอง (Golden Brown Egg)", "default_feed": 112, "description": "สายพันธุ์อเมริกา อารมณ์นิ่ง ไม่ตื่นตกใจง่าย อัตราเปลี่ยนอาหารเป็นน้ำหนักไข่ดีเยี่ยม เหมาะกับฟาร์มปิด"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีขาว (Commercial White Layers)", "breed_key": "Hy-Line W-36", "breed_name": "สายพันธุ์ ไฮ-ไลน์ ขาว ดับบลิว-36 (Hy-Line W-36)", "egg_color": "สีขาวสะอาดตา (Pure White Egg)", "default_feed": 101, "description": "แชมป์โลกด้านความประหยัด กินอาหารน้อยที่สุดในโลก ให้ไข่ฟองสีขาวข้นแน่น ปริมาณไข่ขาวหนาตัวดีมาก"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีครีมและพาสเทล (Commercial Tinted Layers)", "breed_key": "Lohmann Sandy", "breed_name": "สายพันธุ์ โลห์แมน แซนดี้ (Lohmann Sandy)", "egg_color": "สีครีมเม็ดทราย (Sandy Tinted Egg)", "default_feed": 110, "description": "ให้ผลผลิตไข่สีครีมพาสเทลอมชมพูสวยงาม อัตราการเปลี่ยนอาหารเป็นไข่ (FCR) ดีเยี่ยม นิยมมากในตลาดยุโรป"},
        {"group_name": "กลุ่มไก่ไข่ทางเลือกและไก่พื้นเมืองประยุกต์ (Heritage & Local Heritage Layers)", "breed_key": "Pradu Hang Dam Egg-Line", "breed_name": "สายพันธุ์ ประดู่หางดำเชียงใหม่ สายไข่ (Pradu Hang Dam)", "egg_color": "สีน้ำตาลอ่อนนวล (Native Cream-Brown Egg)", "default_feed": 120, "description": "สายพันธุ์ปรับปรุงโดยปศุสัตว์ไทย ทนร้อน ทนโรคสัตว์ปีกได้ดีเลิศ ไข่แดงฟองใหญ่ รสชาติมันเข้มข้น ตอบโจทย์วิถีไก่บ้าน"}
    ]
    
    ing_data = [
        {"name": "ข้าวโพดบดเม็ด (Ground Corn)", "price": 13.5, "protein": 8.5, "me": 3300.0, "calcium": 0.02, "phos": 0.25, "lysine": 0.24, "methionine": 0.18, "threonine": 0.29, "fat": 3.8, "moisture": 12.0, "fiber": 2.2, "sodium": 0.02, "chloride": 0.04, "linoleic": 2.2, "min_limit": 10.0, "max_limit": 65.0},
        {"name": "กากถั่วเหลือง 46% (Soybean Meal 46%)", "price": 19.5, "protein": 46.0, "me": 2440.0, "calcium": 0.25, "phos": 0.62, "lysine": 2.85, "methionine": 0.65, "threonine": 1.80, "fat": 1.5, "moisture": 11.0, "fiber": 3.5, "sodium": 0.02, "chloride": 0.05, "linoleic": 0.5, "min_limit": 10.0, "max_limit": 40.0},
        {"name": "ปลาป่นเกรด A 60% (Fish Meal 60%)", "price": 35.0, "protein": 60.0, "me": 2850.0, "calcium": 5.00, "phos": 3.00, "lysine": 4.50, "methionine": 1.80, "threonine": 2.40, "fat": 8.0, "moisture": 10.0, "fiber": 1.0, "sodium": 1.20, "chloride": 1.50, "linoleic": 0.2, "min_limit": 0.0, "max_limit": 8.0},
        {"name": "หินฝุ่นเม็ดหยาบ (Coarse Limestone)", "price": 2.5, "protein": 0.0, "me": 0.0, "calcium": 38.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 0.5, "fiber": 0.0, "sodium": 0.00, "chloride": 0.00, "linoleic": 0.0, "min_limit": 0.0, "max_limit": 12.0},
        {"name": "ไดแคลเซียมฟอสเฟต (DCP 18%)", "price": 28.0, "protein": 0.0, "me": 0.0, "calcium": 21.00, "phos": 18.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 1.0, "fiber": 0.0, "sodium": 0.00, "chloride": 0.00, "linoleic": 0.0, "min_limit": 0.0, "max_limit": 3.0},
        {"name": "เกลือแกงบริสุทธิ์ (Refined Salt)", "price": 6.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 0.3, "fiber": 0.0, "sodium": 39.30, "chloride": 60.00, "linoleic": 0.0, "min_limit": 0.15, "max_limit": 0.45},
        {"name": "พรีมิกซ์วิตามินแร่ธาตุ (Vitamin-Mineral Premix)", "price": 160.0, "protein": 0.0, "me": 0.0, "calcium": 5.00, "phos": 1.20, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 2.0, "fiber": 0.0, "sodium": 0.00, "chloride": 0.00, "linoleic": 0.25, "min_limit": 0.25, "max_limit": 0.35}
    ]
    
    tgt_data = [
        {"stage_key": "layer_phase_1", "stage_name": "ระยะผลิตไข่พีค ช่วงที่ 1 อายุ 19-45 สัปดาห์ (Production Phase 1)", "protein": 17.5, "me": 2750.0, "calcium": 4.10, "phos": 0.42, "lysine": 0.88, "methionine": 0.42, "fiber_max": 4.5, "sodium_min": 0.16, "chloride_min": 0.16, "linoleic_min": 1.50},
        {"stage_key": "layer_phase_2", "stage_name": "ระยะกลาง ช่วงที่ 2 อายุ 46-65 สัปดาห์ (Production Phase 2)", "protein": 16.5, "me": 2725.0, "calcium": 4.30, "phos": 0.38, "lysine": 0.82, "methionine": 0.39, "fiber_max": 5.0, "sodium_min": 0.16, "chloride_min": 0.16, "linoleic_min": 1.30}
    ]

    ing_dict = {i["name"]: i for i in ing_data}
    tgt_dict = {t["stage_key"]: t for t in tgt_data}
    return ing_dict, tgt_dict, groups_data, breeds_data

ingredients_data, targets_data, groups_list, breeds_list = fetch_complete_layer_data(st.session_state.supabase_url, st.session_state.supabase_key)

if "optimized_weights" not in st.session_state:
    st.session_state.optimized_weights = {name: 0.0 for name in ingredients_data.keys()}

# ==========================================
# 🎉 4. HEADER CONTROL PANEL
# ==========================================
col_h1, col_h2 = st.columns([7.5, 2.5])
with col_h1:
    st.markdown("# 🐔 สตูดิโอคำนวณสูตรอาหารและจัดการสายพันธุ์ไก่ไข่ (Layer Nutrition Studio Pro)")
    st.markdown(f"<p style='color:#38bdf8; font-weight:bold; font-size:1.15rem;'>🎯 ระดับสิทธิ์การเข้าถึงข้อมูล: {st.session_state.user_email}</p>", unsafe_allow_html=True)
with col_h2:
    st.markdown("<p style='text-align:right; margin:0;'></p>", unsafe_allow_html=True)
    if st.button("🔴 ออกจากระบบ (Logout)", use_container_width=True):
        st.session_state.is_authenticated = False
        st.session_state.user_role = "user"
        st.rerun()

st.markdown("---")

# =========================================================================================
# 🛡️ 5. INTERACTION ROUTER (แยกบล็อกการทำงานระหว่าง ADMIN และ USER เป็นเอกเทศ 100%)
# =========================================================================================

if st.session_state.user_role == "admin":
    # -------------------------------------------------------------------------------------
    # 🛠️ [BLOCK ADMIN เท่านั้น]: หน้าควบคุมสิทธิ์และจัดการหลังบ้าน (ไม่มีเมนูคํานวณของ User โผล่)
    # -------------------------------------------------------------------------------------
    st.markdown("<div style='background-color:#7f1d1d; padding:15px; border-radius:10px; margin-bottom:20px;'><h3 style='margin:0; color:#fca5a5 !important;'>🛠️ CONTROL PANEL: พื้นที่ควบคุมระบบของผู้ดูแลระบบหลังบ้าน</h3></div>", unsafe_allow_html=True)
    
    admin_tabs = st.tabs(["👥 จัดการข้อมูลผู้ใช้งาน (User Account Manager)", "⚙️ แก้ไขพารามิเตอร์ระบบ (SQL Cache Editor)"])
    
    with admin_tabs[0]:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("### 👥 รายชื่อผู้ใช้งานทั้งหมดในระบบฟาร์ม (User Database Real-time)")
        st.markdown("แอดมินสามารถส่องดูไอดี รหัสผ่าน และปรับบทบาทของผู้ใช้งานจากตรงนี้ได้ทันที")
        
        raw_user_list = []
        for username, u_info in st.session_state.user_database.items():
            raw_user_list.append({
                "Username/ID": username,
                "ชื่อ": u_info.get("name", "N/A"),
                "นามสกุล": u_info.get("surname", "N/A"),
                "สิทธิ์ผู้ใช้ (Role)": u_info.get("role", "user"),
                "เบอร์โทรศัพท์": u_info.get("tel", "N/A"),
                "รหัสผ่าน (Password)": u_info.get("password", "N/A"),
                "วันที่ลงทะเบียน": u_info.get("reg_date", "N/A")
            })
        df_users = pd.DataFrame(raw_user_list)
        st.dataframe(df_users, use_container_width=True)
        
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        st.markdown("#### ⚡ เครื่องมือจัดการสิทธิ์ด่วน (Modify User Role)")
        
        col_adm1, col_adm2, col_adm3 = st.columns(3)
        with col_adm1:
            target_user_to_change = st.selectbox("เลือกไอดีผู้ใช้งานที่ต้องการเปลี่ยนสิทธิ์:", list(st.session_state.user_database.keys()))
        with col_adm2:
            current_user_role = st.session_state.user_database[target_user_to_change].get("role", "user")
            default_role_idx = 0 if current_user_role == "user" else 1
            new_role_assignment = st.selectbox("กำหนดระดับสิทธิ์ใหม่ (Role assignment):", ["user", "admin"], index=default_role_idx)
        with col_adm3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 บันทึกการอัปเดตสิทธิ์", use_container_width=True):
                st.session_state.user_database[target_user_to_change]["role"] = new_role_assignment
                st.success(f"เปลี่ยนสิทธิ์ของ {target_user_to_change} เป็น {new_role_assignment} เรียบร้อยแล้ว!")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        
    with admin_tabs[1]:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("## 📦 ส่วนจัดการฐานข้อมูลความต้องการสายพันธุ์ (SQL Cache Editor Control)")
        
        database_action_mode = st.selectbox(
            "⚡ เลือกเป้าหมายโครงสร้างตารางที่ต้องการปรับแต่งพัฒนา:",
            ["📁 ปรับเปลี่ยนพารามิเตอร์ตารางกลุ่มใหญ่ (Chicken Groups Table)", "🪶 ปรับเปลี่ยนพารามิเตอร์ตารางรายสายพันธุ์เดี่ยว (Chicken Breeds Table)"]
        )
        
        if database_action_mode == "📁 ปรับเปลี่ยนพารามิเตอร์ตารางกลุ่มใหญ่ (Chicken Groups Table)":
            st.markdown("#### ✏️ แก้ไขข้อมูลแนวโน้มตลาดกลุ่มแม่ไก่ไข่")
            avail_groups = [g["group_name"] for g in groups_list]
            selected_g_to_update = st.selectbox("เลือกชื่อกลุ่มข้อมูลที่ต้องการแก้ไข:", avail_groups)
            group_current_obj = next(g for g in groups_list if g["group_name"] == selected_g_to_update)
            st.info(f"📝 ค่าปัจจุบันในระบบ: {group_current_obj.get('market_trend')}")
            new_trend_text = st.text_area("ป้อนข้อมูลแนวโน้มตลาดอัปเดตใหม่ล่าสุด:")
            if st.button("💾 บันทึกการเปลี่ยนแปลงข้อมูลกลุ่มใหญ่"):
                st.success("🎉 อัปเดตข้อมูลโครงสร้างหน่วยความจำเรียบร้อยแล้ว!")
        else:
            st.markdown("#### ✏️ แก้ไขเกณฑ์ปริมาณการกินอาหารมาตรฐานรายสายพันธุ์")
            avail_breeds_map = {b["breed_name"]: b for b in breeds_list}
            selected_b_to_update_label = st.selectbox("เลือกรายชื่อสายพันธุ์ที่ต้องการแก้ไข:", list(avail_breeds_map.keys()))
            breed_current_obj = avail_breeds_map[selected_b_to_update_label]
            st.info(f"💡 เกณฑ์กินอาหารปัจจุบันของสายพันธุ์นี้คือ: {breed_current_obj.get('default_feed')} กรัม/วัน/ตัว")
            new_feed_intake_value = st.number_input("กำหนดตัวเลขเกณฑ์การกินอาหารใหม่ (กรัม):", min_value=70, max_value=160, value=int(breed_current_obj.get('default_feed')))
            if st.button("💾 บันทึกพารามิเตอร์สายพันธุ์ลงฐานข้อมูล"):
                st.success("🎉 ปรับแต่งเกณฑ์คุณสมบัติสายพันธุ์สำเร็จพึงประสงค์!")
                
        st.markdown("---")
        st.markdown("### 📋 ตารางตรวจสอบระดับสารอาหารของวัตถุดิบทั้งหมดในฟาร์ม")
        df_raw_ing = pd.DataFrame.from_dict(ingredients_data, orient='index')
        if not df_raw_ing.empty:
            df_raw_ing.rename(columns={
                "price": "ราคา(บาท/กก.)", "protein": "โปรตีนดิบ(%)", "me": "พลังงานสัตว์(ME)",
                "calcium": "แคลเซียม(%)", "phos": "ฟอสฟอรัส(%)", "lysine": "กรดไลซีน(%)",
                "methionine": "กรดเมท(%)", "threonine": "ทรีโอนีน(%)", "fat": "ไขมันดิบ(%)", 
                "fiber": "กากใย(%)", "min_limit": "ขั้นต่ำ(%)", "max_limit": "สูงสุด(%)"
            }, inplace=True)
            st.dataframe(df_raw_ing, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

else:
    # -------------------------------------------------------------------------------------
    # 🐔 [BLOCK USER ทั่วไป]: หน้าคำนวณและประมวลผลสูตรอาหาร AI (ทางฝั่ง Admin จะมองไม่เห็นส่วนนี้)
    # -------------------------------------------------------------------------------------
    page_tabs = st.tabs(["🏠 ระบบผสมสูตรอาหารปัญญาประดิษฐ์ (AI Feed Optimization)", "📊 แผนสถิติและใบสั่งซื้อวัตถุดิบ (Procurement & PO Sheet)"])
    
    # 🏠 [แท็บที่ 1]: ระบบผสมสูตรอาหารปัญญาประดิษฐ์
    with page_tabs[0]:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("## 📊 ส่วนการเลือกโครงสร้างพันธุกรรมสายพันธุ์ (Genetic Matrix Selection)")
        st.markdown("---")
        
        group_names = [g["group_name"] for g in groups_list]
        
        selected_group = st.selectbox(
            "🗂️ 1. เลือกคัดกรองตามกลุ่มประเภทไก่ไข่หลัก (Breeding Groups Mode):", 
            group_names,
            index=0
        )
        
        g_meta = next(g for g in groups_list if g["group_name"] == selected_group)
        filtered_breeds = [b for b in breeds_list if b["group_name"] == selected_group]
        breed_options_map = {b["breed_name"]: b for b in filtered_breeds}
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if breed_options_map:
            selected_breed_name = st.selectbox(
                "🐓 2. คัดกรองเจาะลึกรายสายพันธุ์การค้าอัตโนมัติ (Commercial Breeds Mode):", 
                list(breed_options_map.keys())
            )
            b_meta = breed_options_map[selected_breed_name]
            
            st.markdown(f"""
            <div style='background-color: {g_meta["bg_color"]}; padding: 25px; border-radius: 16px; border: 2.5px solid rgba(255,255,255,0.25); margin-top:15px;'>
                <h4 style='margin:0; color:{g_meta["text_color"]} !important; font-size:1.3rem;'>📋 รายละเอียดโปรไฟล์พันธุกรรม: {b_meta["breed_name"]}</h4>
                <p style='margin:12px 0 0 0; color:{g_meta["text_color"]} !important; font-size:1.18rem; line-height: 1.6;'>
                    <b>🧬 กลุ่มหลักสังกัด (Breeding Group):</b> {b_meta["group_name"]}<br>
                    <b>🥚 สีเปลือกไข่เป้าหมาย (Target Shell Color):</b> {b_meta["egg_color"]}<br>
                    <b>🍽️ เกณฑ์การกินอาหารมาตรฐาน (Standard Feed Intake):</b> <span style='color:#ffb703; font-weight:bold; font-size:1.3rem;'>{b_meta["default_feed"]}</span> กรัม/วัน/ตัว (g/day/bird)<br>
                    <b>💡 ข้อมูลเชิงลึกประจำสายพันธุ์ (Breed Insight):</b> {b_meta["description"]}
                </p>
            </div>
            """, unsafe_allow_html=True)
            active_breed_profile = b_meta
        else:
            st.warning("⚠️ ไม่พบข้อมูลสายพันธุ์ย่อยที่เชื่อมโยงกับกลุ่มหลักนี้ในระบบคลังข้อมูล")
            active_breed_profile = {"breed_name": "Unknown", "default_feed": 110}

        st.markdown("---")
        st.markdown("### 🧬 3. กำหนดระยะอายุและเป้าหมายสารอาหารที่เหมาะสม (Nutrition Target & Stage)")
        stage_options = {s["stage_name"]: s["stage_key"] for s in targets_data.values()}
        selected_stage_label = st.selectbox("เลือกระยะอายุการให้ผลผลิตของฝูง (Select Production Stage):", list(stage_options.keys()))
        active_req = targets_data[stage_options[selected_stage_label]]
        
        st.session_state.use_phytase = st.checkbox("🧪 เปิดใช้งานเอนไซม์ไฟเตสเสริม (Enable Phytase Enzyme Optimization)")
        
        if st.button("⚡ เริ่มเดินเครื่องคำนวณสูตรอาหารต้นทุนต่ำสุด (Run AI Low-Cost Linear Solver)", type="primary", use_container_width=True):
            with st.spinner("กระบวนการคำนวณเชิงเส้นกำลังจับคู่ราคาวัตถุดิบและกรดอะมิโน..."):
                prob = pulp.LpProblem("LayerLinearSolver", pulp.LpMinimize)
                ing_vars = {name: pulp.LpVariable(name, lowBound=float(d["min_limit"])/100.0, upBound=float(d["max_limit"])/100.0) for name, d in ingredients_data.items()}
                
                prob += pulp.lpSum([ing_vars[name] * float(d["price"]) for name, d in ingredients_data.items()]), "Total_Cost"
                prob += pulp.lpSum([ing_vars[name] for name in ingredients_data.keys()]) == 1.0, "Total_Weight"
                
                final_p = float(active_req["phos"]) - 0.10 if st.session_state.use_phytase else float(active_req["phos"])
                final_ca = float(active_req["calcium"]) - 0.05 if st.session_state.use_phytase else float(active_req["calcium"])
                
                prob += pulp.lpSum([ing_vars[name] * float(d["protein"]) for name, d in ingredients_data.items()]) >= float(active_req["protein"])
                prob += pulp.lpSum([ing_vars[name] * float(d["me"]) for name, d in ingredients_data.items()]) >= float(active_req["me"])
                prob += pulp.lpSum([ing_vars[name] * float(d["calcium"]) for name, d in ingredients_data.items()]) >= final_ca
                prob += pulp.lpSum([ing_vars[name] * float(d["phos"]) for name, d in ingredients_data.items()]) >= final_p
                prob += pulp.lpSum([ing_vars[name] * float(d["lysine"]) for name, d in ingredients_data.items()]) >= float(active_req["lysine"])
                prob += pulp.lpSum([ing_vars[name] * float(d["methionine"]) for name, d in ingredients_data.items()]) >= float(active_req["methionine"])
                prob += pulp.lpSum([ing_vars[name] * float(d["fiber"]) for name, d in ingredients_data.items()]) <= float(active_req["fiber_max"])

                prob.solve(pulp.PULP_CBC_CMD(msg=False))
                
                if pulp.LpStatus[prob.status] == "Optimal":
                    st.success(f"✅ AI ประมวลผลสำเร็จ! ได้สูตรอาหารที่สมดุลและมีราคาประหยัดที่สุดเรียบร้อย")
                    st.session_state.optimized_weights = {name: ing_vars[name].varValue * 100.0 for name in ingredients_data.keys()}
                else:
                    st.session_state.optimized_weights = {name: 0.0 for name in ingredients_data.keys()}
                    st.error("❌ ไม่สามารถหาคำตอบที่ลงตัวได้ เนื่องจากข้อจำกัดวัตถุดิบบางตัวแน่นจนเกินไป")

        if any(v > 0 for v in st.session_state.optimized_weights.values()):
            col_res1, col_res2 = st.columns([1.2, 1])
            with col_res1:
                st.markdown("#### 📊 แผนภาพวงกลมสัดส่วนวัตถุดิบอาหารที่ใช้ (Ingredient Proportion %)")
                clean_plot = [{"วัตถุดิบอาหาร (Ingredients)": k, "สัดส่วนที่ใช้ (Percentage %)": v} for k, v in st.session_state.optimized_weights.items() if v > 0.01]
                df_cp = pd.DataFrame(clean_plot).sort_values(by="สัดส่วนที่ใช้ (Percentage %)", ascending=False)
                fig_p = px.pie(df_cp, names="วัตถุดิบอาหาร (Ingredients)", values="สัดส่วนที่ใช้ (Percentage %)", hole=0.45, color_discrete_sequence=px.colors.sequential.YlOrBr)
                fig_p.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_p, use_container_width=True)
                st.dataframe(df_cp, use_container_width=True, hide_index=True)

            with col_res2:
                st.markdown("#### 🧪 สรุปผลวิเคราะห์ระดับสารอาหารจริงเปรียบเทียบเกณฑ์ (Nutrition Matrix Audit)")
                act_nut = {"protein": 0, "me": 0, "calcium": 0, "phos": 0, "lysine": 0, "methionine": 0, "fiber": 0}
                net_cost = 0
                for name, w in st.session_state.optimized_weights.items():
                    if w > 0:
                        ratio = w / 100.0
                        net_cost += ratio * float(ingredients_data[name]["price"])
                        for n_key in act_nut.keys():
                            if n_key in ingredients_data[name]:
                                act_nut[n_key] += ratio * float(ingredients_data[name][n_key])
                
                comparison_rows = [
                    {"โภชนาการที่วิเคราะห์ (Nutrient Profiles)": "โปรตีนดิบรวม (Crude Protein %)", "ค่าจริงในสูตร (Actual)": round(act_nut["protein"], 2), "เกณฑ์กำหนด (Target Constraint)": f">= {active_req['protein']}"},
                    {"โภชนาการที่วิเคราะห์ (Nutrient Profiles)": "พลังงานใช้ประโยชน์ได้ (Metabolizable Energy kcal/kg)", "ค่าจริงในสูตร (Actual)": round(act_nut["me"], 0), "เกณฑ์กำหนด (Target Constraint)": f">= {active_req['me']}"},
                    {"โภชนาการที่วิเคราะห์ (Nutrient Profiles)": "แคลเซียมเพื่อเปลือกไข่ (Calcium %)", "ค่าจริงในสูตร (Actual)": round(act_nut["calcium"], 2), "เกณฑ์กำหนด (Target Constraint)": f">= {active_req['calcium']}"},
                    {"โภชนาการที่วิเคราะห์ (Nutrient Profiles)": "ฟอสฟอรัสที่เป็นประโยชน์ (Available Phosphorus %)", "ค่าจริงในสูตร (Actual)": round(act_nut["phos"], 2), "เกณฑ์กำหนด (Target Constraint)": f">= {active_req['phos']}"},
                    {"โภชนาการที่วิเคราะห์ (Nutrient Profiles)": "กรดอะมิโน ไลซีน (Lysine %)", "ค่าจริงในสูตร (Actual)": round(act_nut["lysine"], 2), "เกณฑ์กำหนด (Target Constraint)": f">= {active_req['lysine']}"},
                    {"โภชนาการที่วิเคราะห์ (Nutrient Profiles)": "กรดอะมิโน เมทไธโอนีน (Methionine %)", "ค่าจริงในสูตร (Actual)": round(act_nut["methionine"], 2), "เกณฑ์กำหนด (Target Constraint)": f">= {active_req['methionine']}"},
                    {"โภชนาการที่วิเคราะห์ (Nutrient Profiles)": "ไฟเบอร์กากใยสูงสุด (Crude Fiber Max %)", "ค่าจริงในสูตร (Actual)": round(act_nut["fiber"], 2), "เกณฑ์กำหนด (Target Constraint)": f"<= {active_req['fiber_max']}"}
                ]
                st.markdown(f"<h3 style='color:#ffb703 !important; text-align:center;'>💰 ต้นทุนค่าอาหาร: {net_cost:.2f} บาท / กิโลกรัม (THB/KG)</h3>", unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # 📊 [แท็บที่ 2]: แผนสถิติและใบสั่งซื้อวัตถุดิบ (Procurement & PO Sheet)
    with page_tabs[1]:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("## 📊 ระบบประเมินน้ำหนักวัตถุดิบและส่งออกใบสั่งซื้อ (Purchase Order Document)")
        
        total_tonnage = st.number_input("ป้อนจำนวนยอดการผลิตอาหารสัตว์รวมสำหรับล๊อตนี้ (น้ำหนักกิโลกรัม):", min_value=100, max_value=10000000, value=2000, step=1000)
        
        po_table_buffer = []
        accumulated_po_cost = 0
        
        for ing_title, weight_percentage in st.session_state.optimized_weights.items():
            if weight_percentage > 0.01:
                exact_weight_kg = (weight_percentage / 100.0) * total_tonnage
                item_cost_evaluation = exact_weight_kg * float(ingredients_data[ing_title]["price"])
                accumulated_po_cost += item_cost_evaluation
                po_table_buffer.append({
                    "รายการวัตถุดิบในคลัง (Material Description)": ing_title,
                    "น้ำหนักสุทธิที่ต้องใช้ (Net Weight KG)": round(exact_weight_kg, 2),
                    "ราคารวมโดยประมาณ (Total Cost THB)": round(item_cost_evaluation, 2)
                })
                
        if po_table_buffer:
            df_final_po = pd.DataFrame(po_table_buffer)
            st.dataframe(df_final_po, use_container_width=True, hide_index=True)
            
            stat_c1, stat_c2 = st.columns(2)
            with stat_c1:
                st.metric("💵 ยอดงบประมาณรวมจัดซื้อวัตถุดิบล็อตนี้", f"{accumulated_po_cost:,.2f} บาท")
            with stat_c2:
                st.metric("🏷️ ต้นทุนเฉลี่ยของสูตรล็อตนี้", f"{(accumulated_po_cost / total_tonnage):.2f} บาท/กก.")
                
            csv_stream = io.StringIO()
            df_final_po.to_csv(csv_stream, index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 ดาวน์โหลดใบส่งสั่งซื้อวัตถุดิบอาหารสัตว์ (Export PO to CSV)",
                data=csv_stream.getvalue(),
                file_name=f"PO_Batch_{total_tonnage}KG.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.warning("⚠️ ไม่พบโครงสร้างส่วนผสมอาหาร กรุณากดปุ่มคำนวณสูตรอาหารปัญญาประดิษฐ์ในแท็บแรกก่อน")
        st.markdown("</div>", unsafe_allow_html=True)
