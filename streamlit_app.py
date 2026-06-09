import streamlit as st
import pandas as pd
import pulp
import datetime
import plotly.graph_objects as go

# ==========================================
# 🔱 1. INITIAL APP CONFIGURATION & THEME
# ==========================================
st.set_page_config(
    page_title="ระบบจัดการฟาร์มและคำนวณโภชนาการไก่ไข่ระดับองค์กร (Layer Farm Enterprise Studio)", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(
    """
    <style>
    [data-testid="collapsedControl"] { display: none; }
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.88), rgba(0, 0, 0, 0.88)), 
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
        background-color: rgba(255, 255, 255, 0.15) !important;
        padding: 8px; border-radius: 10px; backdrop-filter: blur(10px);
    }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-weight: bold !important; font-size:1.05rem !important; }
    .content-card {
        background-color: rgba(0, 0, 0, 0.92) !important; padding: 30px;
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
# 🔐 2. GLOBAL SECURITY & STATE INITIALIZATION
# ==========================================
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False
if "auth_page_mode" not in st.session_state:
    st.session_state.auth_page_mode = "login"  
if "user_role" not in st.session_state:
    st.session_state.user_role = "user"  
if "saved_formulas" not in st.session_state:
    st.session_state.saved_formulas = []  
if "audit_logs" not in st.session_state:
    st.session_state.audit_logs = [
        {"เวลา": "2026-06-09 08:00", "ผู้ใช้": "System", "กิจกรรม": "เปิดระบบฐานข้อมูลฟาร์มความปลอดภัยสูง"}
    ]

# 🐔 ฐานข้อมูลกิจกรรมประจำวันย้อนหลังในโรงเรือน (เพิ่มช่อง บันทึกการกินน้ำ)
if "farm_production_logs" not in st.session_state:
    st.session_state.farm_production_logs = [
        {"วันที่": "2026-06-05", "โรงเรือน": "House A", "จำนวนไก่ต้นวัน": 5000, "ไข่รวม(ฟอง)": 4450, "เบอร์0": 300, "เบอร์1": 1200, "เบอร์2": 2000, "เบอร์3": 750, "เบอร์4": 200, "น้ำหนักไข่รวม(กก.)": 280.0, "ตาย/คัดทิ้ง(ตัว)": 1, "อาหารกิน(กก.)": 570.0, "น้ำที่กิน(ลิตร)": 1140.0, "อุณหภูมิ(°C)": 28.5, "หมายเหตุ": "ปกติ ให้วิตามินเสริม"},
        {"วันที่": "2026-06-06", "โรงเรือน": "House A", "จำนวนไก่ต้นวัน": 4999, "ไข่รวม(ฟอง)": 4410, "เบอร์0": 310, "เบอร์1": 1190, "เบอร์2": 1980, "เบอร์3": 740, "เบอร์4": 190, "น้ำหนักไข่รวม(กก.)": 278.2, "ตาย/คัดทิ้ง(ตัว)": 2, "อาหารกิน(กก.)": 575.0, "น้ำที่กิน(ลิตร)": 1250.0, "อุณหภูมิ(°C)": 29.2, "หมายเหตุ": "อากาศร้อนช่วงบ่าย"},
        {"วันที่": "2026-06-07", "โรงเรือน": "House A", "จำนวนไก่ต้นวัน": 4997, "ไข่รวม(ฟอง)": 4390, "เบอร์0": 290, "เบอร์1": 1210, "เบอร์2": 1950, "เบอร์3": 760, "เบอร์4": 180, "น้ำหนักไข่รวม(กก.)": 276.5, "ตาย/คัดทิ้ง(ตัว)": 1, "อาหารกิน(กก.)": 568.0, "น้ำที่กิน(ลิตร)": 1130.0, "อุณหภูมิ(°C)": 27.8, "หมายเหตุ": "ทำวัคซีนตามรอบ"},
    ]

# ⚙️ เกณฑ์ตั้งค่าเฝ้าระวังวิกฤตฟาร์มโดยแอดมิน
if "threshold_drop_rate" not in st.session_state:
    st.session_state.threshold_drop_rate = 3.0
if "threshold_mortality_rate" not in st.session_state:
    st.session_state.threshold_mortality_rate = 0.1

# ฐานข้อมูลผู้ใช้หลัก
if "user_database" not in st.session_state:
    st.session_state.user_database = {
        "admin": {"password": "222", "name": "ผู้จัดการฟาร์ม", "surname": "ระดับสูง", "role": "admin", "tel": "089-999-9999", "reg_date": "2026-01-01"},
        "user": {"password": "123", "name": "สัตวบาลหน้างาน", "surname": "ใจดี", "role": "user", "tel": "081-234-5678", "reg_date": "2026-05-10"}
    }

# ฐานข้อมูลกลุ่มสายพันธุ์และข้อมูลจำลอง Curve มาตรฐาน
if "db_groups" not in st.session_state:
    st.session_state.db_groups = [
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "bg_color": "#b45309"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีขาว (Commercial White Layers)", "bg_color": "#0284c7"}
    ]

if "db_breeds" not in st.session_state:
    st.session_state.db_breeds = [
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "breed_name": "สายพันธุ์ ไอซ่า บราวน์ (Isa Brown)", "egg_color": "สีน้ำตาลเข้ม", "default_feed": 114.0, "std_curve": 90.0},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "breed_name": "สายพันธุ์ โลห์แมน บราวน์ (Lohmann Brown)", "egg_color": "สีน้ำตาลเงางาม", "default_feed": 116.0, "std_curve": 91.5},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีขาว (Commercial White Layers)", "breed_name": "สายพันธุ์ ไฮ-ไลน์ ขาว ดับบลิว-36 (Hy-Line W-36)", "egg_color": "สีขาวสะอาดตา", "default_feed": 101.0, "std_curve": 93.0}
    ]

# คลังวัตถุดิบสารอาหาร (เพิ่มข้อมูล Lysine, Methionine, Fiber และ สต็อกคงเหลือ)
if "db_ingredients" not in st.session_state:
    st.session_state.db_ingredients = {
        "ข้าวโพดบดเม็ด (Ground Corn)": {"name": "ข้าวโพดบดเม็ด (Ground Corn)", "price": 13.5, "protein": 8.5, "me": 3300.0, "calcium": 0.02, "phos": 0.25, "lysine": 0.24, "methionine": 0.18, "fiber": 2.2, "min_limit": 0.0, "max_limit": 70.0, "anti_nut_max": 75.0, "msg": "", "stock_kg": 5000.0},
        "กากถั่วเหลือง 46% (Soybean Meal 46%)": {"name": "กากถั่วเหลือง 46% (Soybean Meal 46%)", "price": 19.5, "protein": 46.0, "me": 2440.0, "calcium": 0.25, "phos": 0.62, "lysine": 2.85, "methionine": 0.65, "fiber": 3.5, "min_limit": 0.0, "max_limit": 50.0, "anti_nut_max": 45.0, "msg": "⚠️ ระวังสารยับยั้งทริปซินหากใส่เกิน 45%", "stock_kg": 3500.0},
        "ปลาป่นเกรด A 60% (Fish Meal 60%)": {"name": "ปลาป่นเกรด A 60% (Fish Meal 60%)", "price": 35.0, "protein": 60.0, "me": 2850.0, "calcium": 5.00, "phos": 3.00, "lysine": 4.50, "methionine": 1.80, "fiber": 1.0, "min_limit": 0.0, "max_limit": 12.0, "anti_nut_max": 10.0, "msg": "⚠️ เกิน 10% ไข่จะเริ่มมีกลิ่นคาวปลา", "stock_kg": 800.0},
        "หินฝุ่นเม็ดหยาบ (Coarse Limestone)": {"name": "หินฝุ่นเม็ดหยาบ (Coarse Limestone)", "price": 2.5, "protein": 0.0, "me": 0.0, "calcium": 38.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "fiber": 0.0, "min_limit": 0.0, "max_limit": 15.0, "anti_nut_max": 15.0, "msg": "", "stock_kg": 2000.0},
        "ไดแคลเซียมฟอสเฟต (DCP 18%)": {"name": "ไดแคลเซียมฟอสเฟต (DCP 18%)", "price": 28.0, "protein": 0.0, "me": 0.0, "calcium": 21.00, "phos": 18.00, "lysine": 0.00, "methionine": 0.00, "fiber": 0.0, "min_limit": 0.0, "max_limit": 4.0, "anti_nut_max": 5.0, "msg": "", "stock_kg": 400.0},
        "เกลือแกงบริสุทธิ์ (Refined Salt)": {"name": "เกลือแกงบริสุทธิ์ (Refined Salt)", "price": 6.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "fiber": 0.0, "min_limit": 0.10, "max_limit": 0.50, "anti_nut_max": 0.6, "msg": "", "stock_kg": 150.0},
        "พรีมิกซ์วิตามินแร่ธาตุ (Vitamin-Mineral Premix)": {"name": "พรีมิกซ์วิตามินแร่ธาตุ (Vitamin-Mineral Premix)", "price": 160.0, "protein": 0.0, "me": 0.0, "calcium": 5.00, "phos": 1.20, "lysine": 0.00, "methionine": 0.00, "fiber": 0.0, "min_limit": 0.20, "max_limit": 0.40, "anti_nut_max": 0.5, "msg": "", "stock_kg": 200.0},
        "DL-Methionine": {"name": "DL-Methionine", "price": 145.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 99.00, "fiber": 0.0, "min_limit": 0.0, "max_limit": 1.00, "anti_nut_max": 1.5, "msg": "", "stock_kg": 100.0},
        "L-Lysine HCl": {"name": "L-Lysine HCl", "price": 95.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 78.40, "methionine": 0.00, "fiber": 0.0, "min_limit": 0.0, "max_limit": 1.00, "anti_nut_max": 1.5, "msg": "", "stock_kg": 120.0}
    }

if "db_targets" not in st.session_state:
    st.session_state.db_targets = {
        "layer_phase_1": {"stage_key": "layer_phase_1", "stage_name": "ระยะผลิตไข่พีค ช่วงที่ 1 อายุ 19-45 สัปดาห์", "protein": 17.5, "me": 2750.0, "calcium": 4.10, "phos": 0.42, "lysine": 0.88, "methionine": 0.42, "fiber_max": 4.5},
        "layer_phase_2": {"stage_key": "layer_phase_2", "stage_name": "ระยะกลาง ช่วงที่ 2 อายุ 46-65 สัปดาห์", "protein": 16.5, "me": 2725.0, "calcium": 4.30, "phos": 0.38, "lysine": 0.82, "methionine": 0.39, "fiber_max": 5.0}
    }

if "current_weights" not in st.session_state:
    st.session_state.current_weights = {}
if "locked_ingredients" not in st.session_state:
    st.session_state.locked_ingredients = {}

def add_audit_log(user, text):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    st.session_state.audit_logs.insert(0, {"เวลา": now_str, "ผู้ใช้": user, "กิจกรรม": text})

# ==========================================
# 🧮 3. CORE AI SOLVER ENGINE WITH LOCK MATRIX
# ==========================================
def run_ai_solver(req_p, req_m, req_c, req_ph, req_ly, req_me):
    prob = pulp.LpProblem("AI_Advance_Solver", pulp.LpMinimize)
    
    ing_vars = {}
    for name, d in st.session_state.db_ingredients.items():
        if st.session_state.locked_ingredients.get(name, False):
            # หากวัตถุดิบถูกล็อกไว้ ให้ขอบเขตบนและล่างเท่ากับค่าที่ตั้งไว้ชั่วคราว
            current_val = float(st.session_state.current_weights.get(name, 0.0)) / 100.0
            ing_vars[name] = pulp.LpVariable(name, lowBound=current_val, upBound=current_val)
        else:
            ing_vars[name] = pulp.LpVariable(name, lowBound=float(d["min_limit"])/100.0, upBound=float(d["max_limit"])/100.0)
            
    s_p = pulp.LpVariable("s_p", lowBound=0)
    s_m = pulp.LpVariable("s_m", lowBound=0)
    s_c = pulp.LpVariable("s_c", lowBound=0)
    
    prob += pulp.lpSum([ing_vars[name] * float(d["price"]) for name, d in st.session_state.db_ingredients.items()]) + 1000.0 * (s_p + s_m/100.0 + s_c), "Cost"
    prob += pulp.lpSum([ing_vars[name] for name in st.session_state.db_ingredients.keys()]) == 1.0, "Weight"
    
    prob += pulp.lpSum([ing_vars[name] * float(d["protein"]) for name, d in st.session_state.db_ingredients.items()]) + s_p >= req_p
    prob += pulp.lpSum([ing_vars[name] * float(d["me"]) for name, d in st.session_state.db_ingredients.items()]) + s_m >= req_m
    prob += pulp.lpSum([ing_vars[name] * float(d["calcium"]) for name, d in st.session_state.db_ingredients.items()]) + s_c >= req_c
    prob += pulp.lpSum([ing_vars[name] * float(d["phos"]) for name, d in st.session_state.db_ingredients.items()]) >= req_ph
    prob += pulp.lpSum([ing_vars[name] * float(d["lysine"]) for name, d in st.session_state.db_ingredients.items()]) >= req_ly
    prob += pulp.lpSum([ing_vars[name] * float(d["methionine"]) for name, d in st.session_state.db_ingredients.items()]) >= req_me
    
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    
    res = {}
    for name in st.session_state.db_ingredients.keys():
        res[name] = round((ing_vars[name].varValue if ing_vars[name].varValue is not None else 0.0) * 100.0, 1)
    return res

# ==========================================
# 🔒 4. SECURITY GATEWAY (LOGIN & SIGN UP)
# ==========================================
if not st.session_state.is_authenticated:
    if st.session_state.auth_page_mode == "login":
        st.markdown("<div class='content-card' style='max-width: 550px; margin: 60px auto 0 auto;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #ffb703 !important;'>🔐 เข้าสู่ระบบ Layer Enterprise Solution</h2>", unsafe_allow_html=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        
        email_login = st.text_input("📧 อีเมลบัญชีผู้ใช้:", key="login_email")
        pass_login = st.text_input("🔑 รหัสผ่านความปลอดภัย:", type="password", key="login_pass")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("เข้าสู่ระบบ (Log In)", type="primary", use_container_width=True):
                if email_login in st.session_state.user_database and st.session_state.user_database[email_login]["password"] == pass_login:
                    user_info = st.session_state.user_database[email_login]
                    st.session_state.is_authenticated = True
                    st.session_state.user_role = user_info.get("role", "user")
                    st.session_state.user_email = f"{user_info['name']} [{user_info['role'].upper()}]"
                    st.session_state.current_user_key = email_login
                    add_audit_log(email_login, "เข้าสู่ระบบสำเร็จ")
                    st.rerun()
                else:
                    st.error("❌ อีเมลหรือรหัสผ่านไม่ถูกต้อง")
        with col_btn2:
            if st.button("🆕 ลงทะเบียนฟาร์มใหม่", use_container_width=True):
                st.session_state.auth_page_mode = "signup"
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    elif st.session_state.auth_page_mode == "signup":
        st.markdown("<div class='content-card' style='max-width: 600px; margin: 40px auto 0 auto;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #38bdf8 !important;'>📝 สมัครสมาชิกฟาร์มใหม่ (Sign Up)</h2>", unsafe_allow_html=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        
        su_name = st.text_input("👤 ชื่อจริง:")
        su_surname = st.text_input("👤 นามสกุล:")
        su_tel = st.text_input("📞 เบอร์โทรศัพท์:")
        su_email = st.text_input("📧 อีเมลบัญชีผู้ใช้ (ใช้ล็อกอิน):")
        su_pass = st.text_input("🔑 ตั้งรหัสผ่าน:", type="password")
        
        col_su1, col_su2 = st.columns(2)
        with col_su1:
            if st.button("✅ ยืนยันการลงทะเบียน", type="primary", use_container_width=True):
                if su_email and su_pass and su_name:
                    if su_email in st.session_state.user_database:
                        st.error("❌ อีเมลนี้มีในระบบแล้ว")
                    else:
                        st.session_state.user_database[su_email] = {
                            "password": su_pass, "name": su_name, "surname": su_surname,
                            "role": "user", "tel": su_tel, "reg_date": "2026-06-09"
                        }
                        add_audit_log("System", f"ลงทะเบียนบัญชีใหม่: {su_email}")
                        st.success("🎉 ลงทะเบียนสำเร็จ! กำลังพากลับไปหน้าล็อกอิน...")
                        st.session_state.auth_page_mode = "login"
                        st.rerun()
                else:
                    st.warning("⚠️ กรุณากรอกข้อมูลให้ครบถ้วน")
        with col_su2:
            if st.button("⬅️ ย้อนกลับไปหน้าล็อกอิน", use_container_width=True):
                st.session_state.auth_page_mode = "login"
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

# ==========================================
# 🎉 5. HEADER CONTROL PANEL
# ==========================================
col_h1, col_h2 = st.columns([7.2, 2.8])
with col_h1:
    st.markdown(f"# 🐔 Layer Enterprise Studio Pro <span style='font-size:1.05rem; color:#38bdf8;'>[ผู้ใช้งานปัจจุบัน: {st.session_state.user_email}]</span>", unsafe_allow_html=True)
with col_h2:
    cc1, cc2 = st.columns(2)
    with cc1:
        if "admin" in st.session_state.user_email.lower() or st.session_state.user_role == "admin" or st.session_state.get("current_user_key") in ["admin"]:
            if st.session_state.user_role == "user":
                if st.button("⚙️ ไปหน้า Admin", use_container_width=True):
                    st.session_state.user_role = "admin"
                    st.rerun()
            else:
                if st.button("🐓 ไปหน้า User", use_container_width=True):
                    st.session_state.user_role = "user"
                    st.rerun()
    with cc2:
        if st.button("🔴 ออกจากระบบ", use_container_width=True):
            add_audit_log(st.session_state.get("current_user_key", "Unknown"), "ออกจากระบบ")
            st.session_state.is_authenticated = False
            st.session_state.current_weights = {}
            st.session_state.auth_page_mode = "login"
            st.rerun()
st.markdown("---")

# ==========================================
# 🛠️ 6. MAIN ROUTER & DASHBOARD INTERFACE
# ==========================================
if st.session_state.user_role == "admin":
    # -----------------------------------------------------------------------------------------
    # 🛠️ ADMIN ROUTE: CONTROL PANEL & CRITICAL ALERTS CONFIG
    # -----------------------------------------------------------------------------------------
    st.markdown("<div style='background-color:#1e3a8a; padding:15px; border-radius:10px; margin-bottom:20px;'><h3 style='margin:0; color:#93c5fd !important;'>🛠️ CONTROL CENTER: แผงควบคุมระบบและเกณฑ์ความปลอดภัยฟาร์ม</h3></div>", unsafe_allow_html=True)
    admin_tabs = st.tabs(["🌽 จัดการคลังวัตถุดิบอาหาร", "🐓 คลังสายพันธุ์ไก่ไข่", "🚨 ตั้งค่าเกณฑ์เตือนภัย (Thresholds)", "👤 สิทธิ์ผู้ใช้งาน", "🕵️ บันทึกกิจกรรม (Audit Trail)"])
    
    with admin_tabs[0]:
        st.markdown("<div class='content-card'>### 🌽 ข้อมูลวัตถุดิบและปริมาณสต็อกปัจจุบันในฟาร์ม</div>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame.from_dict(st.session_state.db_ingredients, orient='index'), use_container_width=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### ➕ เพิ่ม / ✏️ อัปเดตข้อมูลวัตถุดิบและสต็อกสินค้า")
            ing_name = st.text_input("ชื่อวัตถุดิบอาหารสัตว์:")
            ing_price = st.number_input("ราคาทุน (บาท/กิโลกรัม):", min_value=0.0, value=12.0)
            ing_prot = st.number_input("โปรตีนดิบ Crude Protein (%):", min_value=0.0, value=10.0)
            ing_me = st.number_input("พลังงานใช้ประโยชน์ได้ ME (kcal/kg):", min_value=0.0, value=2500.0)
            ing_ca = st.number_input("แคลเซียม Ca (%):", min_value=0.0, value=0.0)
            ing_phos = st.number_input("ฟอสฟอรัสที่เป็นประโยชน์ Av.P (%):", min_value=0.0, value=0.0)
            ing_stock = st.number_input("ปริมาณสต็อกยกมาคงเหลือในคลัง (กิโลกรัม):", min_value=0.0, value=1000.0)
            ing_min = st.number_input("เกณฑ์ขั้นต่ำในสูตร (%):", min_value=0.0, value=0.0)
            ing_max = st.number_input("เกณฑ์สูงสุดในสูตร (%):", min_value=0.0, value=100.0)
            if st.button("💾 ยืนยันบันทึกวัตถุดิบ"):
                if ing_name:
                    st.session_state.db_ingredients[ing_name] = {
                        "name": ing_name, "price": ing_price, "protein": ing_prot, "me": ing_me, 
                        "calcium": ing_ca, "phos": ing_phos, "lysine": 0.0, "methionine": 0.0, "fiber": 2.0,
                        "min_limit": ing_min, "max_limit": ing_max, "anti_nut_max": ing_max, "msg": "", "stock_kg": ing_stock
                    }
                    add_audit_log(st.session_state.get("current_user_key"), f"อัปเดตสต็อก/วัตถุดิบ: {ing_name} เติมสต็อก {ing_stock} กก.")
                    st.success("บันทึกวัตถุดิบและอัปเดตยอดสต็อกเข้าคลังสำเร็จ!"); st.rerun()
        with c2:
            st.markdown("#### ❌ ลบวัตถุดิบออกจากฐานข้อมูล")
            to_del = st.selectbox("เลือกวัตถุดิบที่ต้องการลบถาวร:", list(st.session_state.db_ingredients.keys()))
            if st.button("🗑️ ยืนยันคำสั่งลบ"):
                del st.session_state.db_ingredients[to_del]
                add_audit_log(st.session_state.get("current_user_key"), f"ลบวัตถุดิบ: {to_del}")
                st.warning("ลบวัตถุดิบออกจากระบบเรียบร้อย!"); st.rerun()

    with admin_tabs[1]:
        st.markdown("<div class='content-card'>### 🐓 จัดการมาตรฐานสายพันธุ์และสถิติเป้าหมาย</div>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(st.session_state.db_breeds), use_container_width=True)
        ab1, ab2 = st.columns(2)
        with ab1:
            st.markdown("#### ➕ เพิ่มสายพันธุ์การค้าใหม่")
            sel_g = st.selectbox("เลือกกลุ่มสังกัดหลัก:", [g["group_name"] for g in st.session_state.db_groups])
            new_b = st.text_input("ระบุชื่อสายพันธุ์การค้า:")
            new_c = st.slider("ระบุมาตรฐานเปอร์เซ็นต์การไข่ช่วง Peak (%)", 50.0, 100.0, 92.0)
            if st.button("💾 บันทึกสายพันธุ์ใหม่"):
                if new_b:
                    st.session_state.db_breeds.append({"group_name": sel_g, "breed_name": new_b, "egg_color": "น้ำตาล", "default_feed": 115.0, "std_curve": new_c})
                    add_audit_log(st.session_state.get("current_user_key"), f"เพิ่มสายพันธุ์ไก่: {new_b}")
                    st.success("บันทึกสายพันธุ์เรียบร้อยแล้ว!"); st.rerun()
        with ab2:
            st.markdown("#### ❌ ลบสายพันธุ์")
            b_del = st.selectbox("เลือกสายพันธุ์ที่จะลบ:", [b["breed_name"] for b in st.session_state.db_breeds])
            if st.button("🗑️ ยืนยันลบสายพันธุ์"):
                st.session_state.db_breeds = [b for b in st.session_state.db_breeds if b["breed_name"] != b_del]
                add_audit_log(st.session_state.get("current_user_key"), f"ลบสายพันธุ์ไก่: {b_del}")
                st.warning("ลบสายพันธุ์เสร็จสิ้น"); st.rerun()

    with admin_tabs[2]:
        st.markdown("<div class='content-card'>### 🚨 Custom Threshold Settings (กำหนดค่าวิกฤตความปลอดภัยฟาร์มส่วนกลาง)</div>", unsafe_allow_html=True)
        st.session_state.threshold_drop_rate = st.number_input("ขีดจำกัดเปอร์เซ็นต์การไข่ตกกะทันหันสูงสุดที่ยอมรับได้ต่อวัน (%):", min_value=0.5, max_value=10.0, value=st.session_state.threshold_drop_rate, step=0.5)
        st.session_state.threshold_mortality_rate = st.number_input("ขีดจำกัดอัตราการตายต่อวันสูงสุดที่ยอมรับได้ (% ของจำนวนฝูง):", min_value=0.01, max_value=1.0, value=st.session_state.threshold_mortality_rate, step=0.01)
        st.success("บันทึกเกณฑ์ควบคุมระบบหลักเรียบร้อย สัญญาณเตือนจะอัปเดตไปยังหน้าผู้ใช้งานโดยตรง")

    with admin_tabs[3]:
        st.markdown("<div class='content-card'>### 👤 บัญชีผู้ใช้และระบบจัดการ Access Control Matrix</div>", unsafe_allow_html=True)
        u_list = [{"Username": k, "ชื่อ": v["name"], "สิทธิ์การเข้าถึง": v["role"].upper(), "วันที่ลงทะเบียน": v["reg_date"]} for k, v in st.session_state.user_database.items()]
        st.dataframe(pd.DataFrame(u_list), use_container_width=True)
        
        st.markdown("#### ✏️ ปรับสิทธิ์ผู้ใช้งาน")
        target_u = st.selectbox("เลือกบัญชีผู้ใช้:", list(st.session_state.user_database.keys()))
        target_r = st.selectbox("กำหนดระดับสิทธิ์สัตวบาล:", ["user", "admin"])
        if st.button("💾 บันทึกการเปลี่ยนสิทธิ์"):
            st.session_state.user_database[target_u]["role"] = target_r
            add_audit_log(st.session_state.get("current_user_key"), f"เปลี่ยนสิทธิ์ผู้ใช้ {target_u} เป็น {target_r.upper()}")
            st.success("อัปเดตสิทธิ์ผู้ใช้สำเร็จ!"); st.rerun()

    with admin_tabs[4]:
        st.markdown("<div class='content-card'>### 🕵️ Audit Trail Logs (บันทึกมาตรการความปลอดภัยและความโปร่งใสในฟาร์ม)</div>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(st.session_state.audit_logs), use_container_width=True)

else:
    # -----------------------------------------------------------------------------------------
    # 👑 USER ROUTE: FULL UNIFIED HYBRID MATRIX INTERFACE (EVERYTHING EXTENDED V2)
    # -----------------------------------------------------------------------------------------
    page_tabs = st.tabs([
        "🏠 คำนวณสูตรอาหารอัจฉริยะ (Live Matrix)", 
        "📊 บันทึกผลผลิต & วิเคราะห์วิกฤต (Flock KPIs)",
        "📋 แผนจัดซื้อและแบ่งชั่ง (Procurement Sheets)", 
        "📈 ประวัติและดึงสูตรอาหาร (Formula Loader)"
    ])
    
    # -------------------------------------------------------------
    # TAB 1: FORMULATION ENGINE (EXTENDED FEATURES V2)
    # -------------------------------------------------------------
    with page_tabs[0]:
        st.markdown("<div class='content-card'>### 🐓 โครงสร้างฝูงและระบบชดเชยภูมิอากาศ</div>", unsafe_allow_html=True)
        col_br1, col_br2, col_br3 = st.columns(3)
        with col_br1:
            selected_g = st.selectbox("📁 เลือกกลุ่มสายพันธุ์หลัก:", [g["group_name"] for g in st.session_state.db_groups])
        with col_br2:
            filtered_breeds = [b for b in st.session_state.db_breeds if b["group_name"] == selected_g]
            breed_names = [b["breed_name"] for b in filtered_breeds] if filtered_breeds else ["ไม่มีข้อมูล"]
            selected_b_name = st.selectbox("🐔 เลือกสายพันธุ์ไก่ไข่ในฟาร์ม:", breed_names)
            current_breed_data = next((b for b in filtered_breeds if b["breed_name"] == selected_b_name), {"default_feed": 114.0, "egg_color": "ไม่ระบุ", "std_curve": 90.0})
        with col_br3:
            heat_stress = st.checkbox("🌡️ เปิดโหมดชดเชยความเครียดจากความร้อน (Heat Stress Mode)", help="เมื่อเปิดระบบจะเพิ่มความเข้มข้นของโปรตีนและแร่ธาตุ 5% อัตโนมัติ เพื่อชดเชยการกินอาหารที่ลดลงของไก่ในช่วงอากาศร้อนจัด")
        
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        col_top1, col_top2, col_top3 = st.columns(3)
        with col_top1:
            selected_stage_label = st.selectbox("📋 ช่วงอายุและระยะการไข่:", list({s["stage_name"]: s["stage_key"] for s in st.session_state.db_targets.values()}.keys()))
            base_req = st.session_state.db_targets[{s["stage_name"]: s["stage_key"] for s in st.session_state.db_targets.values()}[selected_stage_label]]
        with col_top2:
            egg_price = st.number_input("💰 ราคารับซื้อไข่หน้าฟาร์มเฉลี่ยวันนี้ (บาท/ฟอง):", min_value=1.0, value=4.10)
        with col_top3:
            laying_rate = st.slider("📊 อัตราการให้ไข่เฉลี่ยปัจจุบันของฝูง (%):", 10, 100, 85)
        st.markdown("</div>", unsafe_allow_html=True)

        # คำนวณความต้องการสารอาหารพื้นฐานพร้อมชดเชยความร้อน
        target_p = float(base_req["protein"]) * (1.05 if heat_stress else 1.0)
        target_m = float(base_req["me"])
        target_c = float(base_req["calcium"]) * (1.05 if heat_stress else 1.0)

        if not st.session_state.current_weights:
            st.session_state.current_weights = run_ai_solver(target_p, target_m, target_c, base_req["phos"], base_req["lysine"], base_req["methionine"])

        col_left, col_right = st.columns([1.1, 0.9])
        with col_left:
            st.markdown("<div class='content-card'>### 🥣 สัดส่วนวัตถุดิบผสมอาหารสัตว์ (%) และฟังก์ชัน Shadow Lock</div>", unsafe_allow_html=True)
            temp_weights = {}
            running_total = 0.0
            
            for name, d in st.session_state.db_ingredients.items():
                saved_w = max(0.0, min(100.0, float(st.session_state.current_weights.get(name, 0.0))))
                
                # ล้อมรอบแถวด้วยการเพิ่มฟังก์ชันตรึงค่า (Shadow Lock) ข้างหน้าสไลเดอร์
                l_col1, l_col2 = st.columns([0.15, 0.85])
                with l_col1:
                    is_locked = st.checkbox("🔒 ล็อก", key=f"lock_{name}", value=st.session_state.locked_ingredients.get(name, False))
                    st.session_state.locked_ingredients[name] = is_locked
                with l_col2:
                    user_val = st.slider(f"🌽 {name} (ทุน {d['price']} บ./กก.)", 0.0, 100.0, saved_w, 0.1, key=f"sld_u_{name}")
                
                # ตรวจสอบขีดจำกัดความปลอดภัยวัตถุดิบและสารพิษต้านโภชนาการ
                if user_val > d["anti_nut_max"] and d["msg"] != "":
                    st.markdown(f"<p style='color:#f87171; font-size:0.85rem; margin:-10px 0 10px 0; padding-left:50px;'>{d['msg']}</p>", unsafe_allow_html=True)
                    
                temp_weights[name] = user_val
                running_total += user_val
            
            if abs(running_total - 100.0) > 0.1:
                st.markdown(f"<div style='background-color:#991b1b; padding:10px; border-radius:8px; font-weight:bold; text-align:center;'>⚠️ สัดส่วนวัตถุดิรรวมได้: {running_total:.1f}% (กรุณาปรับสไลเดอร์ให้ครบ 100%)</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='background-color:#065f46; padding:10px; border-radius:8px; font-weight:bold; text-align:center;'>🟢 สัดส่วนสูตรอาหารมีความสมดุลครบถ้วน: 100%</div>", unsafe_allow_html=True)
            st.session_state.current_weights = temp_weights

        with col_right:
            st.markdown("<div class='content-card'>### 🧪 ผลลัพธ์ทางโภชนาการที่คำนวณได้จริง & Amino Acid Profile</div>", unsafe_allow_html=True)
            net_cost = 0.0
            act_nut = {"protein": 0.0, "me": 0.0, "calcium": 0.0, "phos": 0.0, "lysine": 0.0, "methionine": 0.0}
            divisor = sum(st.session_state.current_weights.values()) if sum(st.session_state.current_weights.values()) > 0 else 1.0
            
            for name, w in st.session_state.current_weights.items():
                r = w / divisor
                net_cost += r * float(st.session_state.db_ingredients[name]["price"])
                for k in act_nut.keys(): act_nut[k] += r * float(st.session_state.db_ingredients[name].get(k, 0.0))
            
            # Interactive Graph (Pie Chart วิเคราะห์วัตถุดิบ)
            pie_labels = [k for k, v in st.session_state.current_weights.items() if v > 0]
            pie_values = [v for k, v in st.session_state.current_weights.items() if v > 0]
            if pie_values:
                fig_pie = go.Figure(data=[go.Pie(labels=pie_labels, values=pie_values, hole=.3)])
                fig_pie.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=200, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False)
                st.plotly_chart(fig_pie, use_container_width=True)

            c_cell1, c_cell2 = st.columns(2)
            with c_cell1:
                edit_p = st.number_input("🎯 โปรตีนควบคุมที่ต้องการ (%):", value=float(target_p))
                edit_m = st.number_input("🎯 พลังงานควบคุมที่ต้องการ (kcal):", value=float(target_m))
            with c_cell2:
                edit_c = st.number_input("🎯 แคลเซียมควบคุมที่ต้องการ (%):", value=float(target_c))
                if st.button("⚡ ให้ AI ช่วยคำนวณสูตรต้นทุนต่ำสุด (โดยไม่ยุ่งกับตัวล็อก)", type="primary", use_container_width=True):
                    st.session_state.current_weights = run_ai_solver(edit_p, edit_m, edit_c, base_req["phos"], base_req["lysine"], base_req["methionine"])
                    st.rerun()
            
            st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
            comparison_table = [
                {"โภชนาการสำคัญ": "โปรตีนดิบ (Crude Protein %)", "ค่าควบคุมเป้าหมาย": f"{edit_p:.2f} %", "สูตรที่ได้จริง": f"{act_nut['protein']:.2f} %"},
                {"โภชนาการสำคัญ": "พลังงานสัตว์ (ME kcal/kg)", "ค่าควบคุมเป้าหมาย": f"{edit_m:.0f}", "สูตรที่ได้จริง": f"{act_nut['me']:.0f}"},
                {"โภชนาการสำคัญ": "แคลเซียมกระดูกและเปลือก (Ca %)", "ค่าควบคุมเป้าหมาย": f"{edit_c:.2f} %", "สูตรที่ได้จริง": f"{act_nut['calcium']:.2f} %"},
                {"โภชนาการสำคัญ": "กรดอะมิโน ไลซีน (Lysine %)", "ค่าควบคุมเป้าหมาย": f"{base_req['lysine']:.2f} %", "สูตรที่ได้จริง": f"{act_nut['lysine']:.2f} %"},
                {"โภชนาการสำคัญ": "กรดอะมิโน เมทไธโอนีน (Methionine %)", "ค่าควบคุมเป้าหมาย": f"{base_req['methionine']:.2f} %", "สูตรที่ได้จริง": f"{act_nut['methionine']:.2f} %"}
            ]
            st.dataframe(pd.DataFrame(comparison_table), use_container_width=True, hide_index=True)
            
            f_consumed = float(current_breed_data["default_feed"]) / 1000.0
            st.metric("💰 ราคาทุนอาหารผสมสูตรนี้", f"{net_cost:.2f} บาท/กก.")
            st.metric("📈 ดัชนีกำไรเหนือค่าอาหาร (IOFC)", f"{((laying_rate/100.0)*egg_price) - (f_consumed*net_cost):.2f} บาท/ตัว/วัน")
            
            save_name_input = st.text_input("ตั้งชื่อระบุรุ่นสูตรผสมอาหารเพื่อจัดเก็บ:", value=f"สูตรผสมพิเศษรอบวันที่ {datetime.date.today()}")
            if st.button("📥 บันทึกสูตรลงคลังประวัติ"):
                st.session_state.saved_formulas.append({
                    "date": str(datetime.date.today()), "name": save_name_input, "cost": round(net_cost, 2), 
                    "breed": selected_b_name, "stage": selected_stage_label, "protein": round(act_nut["protein"], 2), 
                    "me": round(act_nut["me"], 0), "calcium": round(act_nut["calcium"], 2), "weights": st.session_state.current_weights.copy()
                })
                add_audit_log(st.session_state.get("current_user_key"), f"บันทึกสูตรอาหารคลังส่วนตัว: {save_name_input}")
                st.success("บันทึกสูตรสำเร็จ!")

    # -------------------------------------------------------------
    # TAB 2: FARM PRODUCTION LOGS & LIVE KPIs (WATER RATIO & EGG MASS ADDED)
    # -------------------------------------------------------------
    with page_tabs[1]:
        st.markdown("<div class='content-card'><h2>📊 บันทึกผลผลิตรายวันเเละระบบวิเคราะห์เตือนภัยสุขภาพฝูง (Flock Matrix Alert)</h2></div>", unsafe_allow_html=True)
        
        with st.expander("📝 เปิดแบบฟอร์มบันทึกการคัดเกรดไข่ การกินน้ำ และอัตราการตาย (Daily Entry Form)", expanded=True):
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1:
                log_date = st.date_input("วันที่ระบุข้อมูล:", datetime.date.today())
                log_house = st.selectbox("เลือกโรงเรือนผู้ผลิตหลัก:", ["House A", "House B", "House C"])
                log_birds = st.number_input("จำนวนแม่ไก่ต้นวัน (ตัว):", min_value=1, value=5000, step=100)
            with f_col2:
                st.markdown("<small style='color:#ffb703;'>🗂️ แยกขนาดคัดเกรดฟองไข่ประจำวัน (ฟอง)</small>", unsafe_allow_html=True)
                e0 = st.number_input("ไข่เบอร์ 0 (จัมโบ้):", min_value=0, value=300)
                e1 = st.number_input("ไข่เบอร์ 1:", min_value=0, value=1200)
                e2 = st.number_input("ไข่เบอร์ 2:", min_value=0, value=2000)
            with f_col3:
                e3 = st.number_input("ไข่เบอร์ 3:", min_value=0, value=750)
                e4 = st.number_input("ไข่เบอร์ 4 (เล็กสุด):", min_value=0, value=200)
                log_egg_w = st.number_input("น้ำหนักไข่รวมทั้งหมดที่ชั่งได้จริงวันนี้ (กิโลกรัม):", min_value=0.0, value=278.0, step=1.0)
                
            st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
            f_col4, f_col5, f_col6 = st.columns(3)
            with f_col4:
                log_dead = st.number_input("จำนวนไก่ตาย/คัดทิ้งคัดออกวันนี้ (ตัว):", min_value=0, value=2)
            with f_col5:
                log_feed = st.number_input("ปริมาณอาหารที่ใช้เลี้ยงรวมวันนี้ (กิโลกรัม):", min_value=0.0, value=572.0)
                # 💧 FEATURE: บันทึกปริมาณการกินน้ำ
                log_water = st.number_input("ปริมาณน้ำดื่มที่ฝูงสัตว์กินรวมวันนี้ (ลิตร):", min_value=0.0, value=1144.0)
            with f_col6:
                log_temp = st.number_input("อุณหภูมิเฉลี่ยภายในโรงเรือนวันนี้ (°C):", min_value=10.0, value=29.0)
            
            log_note = st.text_input("ข้อสังเกตเพิ่มเติมของสัตวบาลหน้างาน:", value="ปกติ")
            
            if st.button("💾 ยืนยันคำสั่งบันทึกการผลิตส่งเข้าฐานข้อมูลส่วนกลาง", type="primary"):
                total_eggs_calculated = e0 + e1 + e2 + e3 + e4
                st.session_state.farm_production_logs.append({
                    "วันที่": str(log_date), "โรงเรือน": log_house, "จำนวนไก่ต้นวัน": log_birds,
                    "ไข่รวม(ฟอง)": total_eggs_calculated, "เบอร์0": e0, "เบอร์1": e1, "เบอร์2": e2, "เบอร์3": e3, "เบอร์4": e4,
                    "น้ำหนักไข่รวม(กก.)": log_egg_w, "ตาย/คัดทิ้ง(ตัว)": log_dead, "อาหารกิน(กก.)": log_feed, "น้ำที่กิน(ลิตร)": log_water,
                    "อุณหภูมิ(°C)": log_temp, "หมายเหตุ": log_note
                })
                add_audit_log(st.session_state.get("current_user_key"), f"บันทึกผลผลิตประจำวันโรงเรือน {log_house}")
                st.success("บันทึกข้อมูลการผลิตและคัดแยกขนาดไข่สำเร็จแล้ว!"); st.rerun()

        if st.session_state.farm_production_logs:
            df_farm = pd.DataFrame(st.session_state.farm_production_logs)
            latest_data = df_farm.iloc[-1]
            
            calc_prod_rate = (latest_data["ไข่รวม(ฟอง)"] / latest_data["จำนวนไก่ต้นวัน"]) * 100
            calc_fcr_egg = latest_data["อาหารกิน(กก.)"] / latest_data["น้ำหนักไข่รวม(กก.)"] if latest_data["น้ำหนักไข่รวม(กก.)"] > 0 else 0
            water_feed_ratio = latest_data["น้ำที่กิน(ลิตร)"] / latest_data["อาหารกิน(กก.)"] if latest_data["อาหารกิน(กก.)"] > 0 else 0
            egg_mass_val = (latest_data["น้ำหนักไข่รวม(กก.)"] * 1000) / latest_data["จำนวนไก่ต้นวัน"]
            
            # 🔥 FEATURE: Dynamic Anomaly Detection (ดึงเกณฑ์วิกฤตจากหน้า Admin)
            st.markdown("<div class='content-card'>### 🚨 ศูนย์ควบคุมเฝ้าระวังความปลอดภัยทางชีวภาพ (Biosecurity Watch)</div>", unsafe_allow_html=True)
            
            has_warning = False
            if calc_prod_rate < (current_breed_data["std_curve"] - st.session_state.threshold_drop_rate):
                st.error(f"⚠️ **ตรวจพบวิกฤตผลผลิตตกต่ำ!** เปอร์เซ็นต์ไข่อยู่ที่ {calc_prod_rate:.2f}% ซึ่งต่ำกว่าเกณฑ์เบี่ยงเบนความปลอดภัยของสายพันธุ์ {selected_b_name}")
                has_warning = True
            if latest_data["ตาย/คัดทิ้ง(ตัว)"] >= (latest_data["จำนวนไก่ต้นวัน"] * (st.session_state.threshold_mortality_rate / 100.0)):
                st.error(f"⚠️ **เตือนภัยอัตราการตายสูงเกินค่าควบคุม!** วันนี้พบไก่ตาย {latest_data['ตาย/คัดทิ้ง(ตัว)']} ตัว เสี่ยงต่อการเกิดโรคระบาด")
                has_warning = True
            if water_feed_ratio > 2.3 or water_feed_ratio < 1.6:
                st.warning(f"⚠️ **อัตราการกินน้ำต่ออาหารผิดปกติ (Water-to-Feed Ratio: {water_feed_ratio:.2f} เท่า)** ไก่อาจเกิดภาวะเครียดจากความร้อน ท้องเสีย หรือระบบท่อน้ำชำรุด")
                has_warning = True
                
            if not has_warning:
                st.success("🟢 สถานะสุขภาพฝูงสัตว์และสภาพแวดล้อม: อยู่ในเกณฑ์มาตรฐานความปลอดภัยเชิงพาณิชย์สูงสุด")

            # กราฟเส้นคู่ (Actual vs Standard Breed Curve)
            st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
            st.markdown("#### 📈 กราฟเปรียบเทียบอัตราการไข่จริงกับมาตรฐานประจำสายพันธุ์ย้อนหลัง")
            
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(x=df_farm["วันที่"], y=(df_farm["ไข่รวม(ฟอง)"]/df_farm["จำนวนไก่ต้นวัน"])*100, mode='lines+markers', name='อัตราการไข่จริงในฟาร์ม (Actual %)', line=dict(color='#ffb703', width=3)))
            fig_line.add_trace(go.Scatter(x=df_farm["วันที่"], y=[current_breed_data["std_curve"]]*len(df_farm), mode='lines', name='เส้นเกณฑ์มาตรฐานสายพันธุ์ (Standard Curve)', line=dict(color='#0284c7', dash='dash')))
            fig_line.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=40,r=40,t=20,b=20), height=250)
            st.plotly_chart(fig_line, use_container_width=True)

            # ข้อมูล KPIs ระดับสูง
            kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
            with kpi_col1:
                st.metric("🥚 ประสิทธิภาพอาหาร FCR ต่อไข่ 1 กก.", f"{calc_fcr_egg:.2f}")
            with kpi_col2:
                st.metric("🐓 ดัชนีน้ำหนักเนื้อไข่รวม (Egg Mass)", f"{egg_mass_val:.2f} กรัม/ตัว/วัน")
            with kpi_col3:
                st.metric("💧 สัดส่วนน้ำต่ออาหารที่กิน", f"{water_feed_ratio:.2f} เท่า")

            st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
            st.markdown("🌐 **ฐานข้อมูลสมุดบันทึกประวัติฟาร์มโดยละเอียด**")
            st.dataframe(df_farm, use_container_width=True)
            
            csv_data = df_farm.to_csv(index=False).encode('utf-8')
            st.download_button("📥 ดาวน์โหลดรายงานประวัติฟาร์มครบวงจร (.CSV)", data=csv_data, file_name=f"farm_report_{datetime.date.today()}.csv", mime="text/csv")

    # -------------------------------------------------------------
    # TAB 3: PROCUREMENT & MIXING BATCH SHEET (WITH STOCK ALERT)
    # -------------------------------------------------------------
    with page_tabs[2]:
        st.markdown("<div class='content-card'><h2>📋 แผนจัดเตรียมวัตถุดิบและระบบควบคุมปริมาณคลังสินค้าคงคลัง (Inventory Balance)</h2></div>", unsafe_allow_html=True)
        
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            total_tonnage = st.number_input("ระบุปริมาณอาหารรวมที่ต้องการใช้ผสมทั้งหมดในรอบนี้ (กิโลกรัม):", min_value=100, value=1000, step=100)
        with b_col2:
            mixer_size = st.number_input("ระบุขีดจำกัดความจุต่อรอบของเครื่องผสมหน้างาน (กิโลกรัม/รอบผสม):", min_value=50, value=500, step=50)
            
        num_batches = int(total_tonnage / mixer_size) if total_tonnage > mixer_size else 1
        st.info(f"💡 สำหรับเป้าหมาย {total_tonnage:,} กิโลกรัม คนงานต้องเดินเครื่องผสมทั้งหมด: {num_batches} รอบผสม (รอบละ {mixer_size if total_tonnage > mixer_size else total_tonnage} กิโลกรัม)")
        
        po_buffer = []
        total_po_cost = 0
        stock_out_triggered = False
        divisor = sum(st.session_state.current_weights.values()) if sum(st.session_state.current_weights.values()) > 0 else 1.0
        
        for ing_name, w_pct in st.session_state.current_weights.items():
            actual_pct = (w_pct / divisor) * 100.0
            if actual_pct > 0.01:
                weight_total_kg = (actual_pct / 100.0) * total_tonnage
                weight_per_batch = (actual_pct / 100.0) * (mixer_size if total_tonnage > mixer_size else total_tonnage)
                cost_item = weight_total_kg * float(st.session_state.db_ingredients[ing_name]["price"])
                total_po_cost += cost_item
                
                # 🔥 FEATURE: Inventory Stock Alert & Days remaining check
                current_stock = st.session_state.db_ingredients[ing_name].get("stock_kg", 0.0)
                stock_status = "🟢 เพียงพอ"
                if weight_total_kg > current_stock:
                    stock_status = f"🚨 วัตถุดิบไม่พอ! (ขาดอีก {weight_total_kg - current_stock:.1f} กก.)"
                    stock_out_triggered = True
                
                po_buffer.append({
                    "วัตถุดิบ": ing_name, 
                    "สัดส่วนสูตร (%)": round(actual_pct, 2), 
                    "น้ำหนักสุทธิรวม (KG)": round(weight_total_kg, 2), 
                    "⚖️ ตักชั่งต่อรอบผสม (KG)": round(weight_per_batch, 2),
                    "สต็อกที่มีในฟาร์ม (KG)": current_stock,
                    "สถานะคลังสินค้า": stock_status
                })
                
        if po_buffer:
            st.dataframe(pd.DataFrame(po_buffer), use_container_width=True, hide_index=True)
            st.metric("💵 งบประมาณจัดซื้อวัตถุดิบรวมทั้งสิ้นในรอบนี้", f"{total_po_cost:,.2f} บาท")
            
            # ปุ่มอนุมัติการเบิกจ่ายตัดสต็อก
            if stock_out_triggered:
                st.error("❌ ไม่สามารถกดอนุมัติสูตรอาหารได้ เนื่องจากวัตถุดิบบางรายการในคลังสินค้ามีไม่เพียงพอ กรุณาเติมสต็อกที่หน้า Admin ก่อน")
            else:
                if st.button("✅ อนุมัติการเบิกจ่ายและหักยอดสต็อกสินค้าทันที", type="primary"):
                    for ing_name, w_pct in st.session_state.current_weights.items():
                        actual_pct = (w_pct / divisor) * 100.0
                        weight_total_kg = (actual_pct / 100.0) * total_tonnage
                        if weight_total_kg > 0:
                            st.session_state.db_ingredients[ing_name]["stock_kg"] -= weight_total_kg
                    add_audit_log(st.session_state.get("current_user_key"), f"อนุมัติผสมอาหาร {total_tonnage} กก. และตัดยอดสต็อกออกจากคลังสินค้า")
                    st.success("🎉 อนุมัติใบเบิกสำเร็จและทำหักยอดสต็อกออกจากเซิร์ฟเวอร์ส่วนกลางแล้ว!"); st.rerun()
        else:
            st.warning("⚠️ ไม่พบโครงสร้างสัดส่วนสูตรอาหารในเมมโมรี่ กรุณาเปิดไปที่แท็บหน้าแรกเพื่อให้ AI คำนวณสูตรอาหารก่อน")

    # -------------------------------------------------------------
    # TAB 4: HISTORY STORAGE & FORMULA COMPARISON MATRIX
    # -------------------------------------------------------------
    with page_tabs[3]:
        st.markdown("<div class='content-card'><h2>📈 คลังจัดเก็บประวัติสูตรอาหารและระบบเปรียบเทียบเชิงลึก (Formula Loader)</h2></div>", unsafe_allow_html=True)
        if not st.session_state.saved_formulas:
            st.info("💡 ขณะนี้ยังไม่มีประวัติการบันทึกสูตรอาหารในฐานข้อมูล")
        else:
            df_history = pd.DataFrame(st.session_state.saved_formulas).drop(columns=["weights"])
            st.dataframe(df_history, use_container_width=True)
            
            st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
            
            # 🔥 FEATURE: Side-by-Side Formula Comparison (เปรียบเทียบสูตรเก่าคู่กัน)
            st.markdown("#### 👯 เครื่องมือเปรียบเทียบความแตกต่างระหว่างสูตรอาหาร (Side-by-Side Formula Matrix)")
            hist_options = [f"[{idx}] {f['name']} (โปรตีน: {f['protein']}%)" for idx, f in enumerate(st.session_state.saved_formulas)]
            
            hc1, hc2 = st.columns(2)
            with hc1:
                f_choice_1 = st.selectbox("เลือกสูตรตัวเปรียบเทียบที่ 1:", hist_options, key="comp_1")
                idx_1 = int(f_choice_1.split("]")[0].replace("[", ""))
                formula_1 = st.session_state.saved_formulas[idx_1]
                st.json({k: v for k, v in formula_1.items() if k != "weights"})
            with hc2:
                f_choice_2 = st.selectbox("เลือกสูตรตัวเปรียบเทียบที่ 2:", hist_options, key="comp_2")
                idx_2 = int(f_choice_2.split("]")[0].replace("[", ""))
                formula_2 = st.session_state.saved_formulas[idx_2]
                st.json({k: v for k, v in formula_2.items() if k != "weights"})
            
            st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
            st.markdown("#### ⚡ ระบบดึงสูตรเก่ากลับคืนสู่พื้นที่ทดลองผสม (Formula Rollback Processor)")
            options_loader = {f"[{f['date']}] {f['name']} - ทุน {f['cost']} บ.": idx for idx, f in enumerate(st.session_state.saved_formulas)}
            selected_loader_key = st.selectbox("เลือกสูตรอาหารในอดีตที่ต้องการดึงกลับคืนมาทำซ้ำหรือดัดแปลงหลัก:", list(options_loader.keys()))
            
            if st.button("⚡ ยืนยันดึงสูตรนี้กลับไปที่หน้าคำนวณหลัก"):
                target_idx = options_loader[selected_loader_key]
                st.session_state.current_weights = st.session_state.saved_formulas[target_idx]["weights"].copy()
                add_audit_log(st.session_state.get("current_user_key"), f"ดึงสูตรเก่ามาทำงานซ้ำ: {st.session_state.saved_formulas[target_idx]['name']}")
                st.success("ดึงสูตรสำเร็จ! สัดส่วนวัตถุดิบทั้งหมดถูกส่งกลับไปจำลองค่าวัดที่แท็บแรกเรียบร้อยแล้ว")
