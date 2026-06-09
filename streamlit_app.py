import streamlit as st
import pandas as pd
import pulp
import datetime

# ==========================================
# 🔱 1. INITIAL APP CONFIGURATION & THEME
# ==========================================
st.set_page_config(
    page_title="ระบบจัดการฟาร์มและคำนวณโภชนาการไก่ไข่ (Layer Farm & Nutrition Studio Pro)", 
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
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False
if "auth_page_mode" not in st.session_state:
    st.session_state.auth_page_mode = "login"  
if "user_role" not in st.session_state:
    st.session_state.user_role = "user"  
if "saved_formulas" not in st.session_state:
    st.session_state.saved_formulas = []  

# --- 🐔 ฐานข้อมูลกิจกรรมในฟาร์มของผู้ใช้ (Production Logs) ---
if "farm_production_logs" not in st.session_state:
    st.session_state.farm_production_logs = [
        {"วันที่": "2026-06-05", "โรงเรือน": "House A", "จำนวนไก่ต้นวัน": 5000, "ไข่ที่เก็บได้ (ฟอง)": 4350, "น้ำหนักไข่รวม (กก.)": 274.0, "ไก่ตาย/คัดทิ้ง (ตัว)": 2, "อาหารที่กิน (กก.)": 570.0, "อุณหภูมิเฉลี่ย (°C)": 28.5, "หมายเหตุ": "ปกติ ให้วิตามินละลายน้ำ"},
        {"วันที่": "2026-06-06", "โรงเรือน": "House A", "จำนวนไก่ต้นวัน": 4998, "ไข่ที่เก็บได้ (ฟอง)": 4410, "น้ำหนักไข่รวม (กก.)": 278.2, "ไก่ตาย/คัดทิ้ง (ตัว)": 1, "อาหารที่กิน (กก.)": 575.0, "อุณหภูมิเฉลี่ย (°C)": 29.0, "หมายเหตุ": "ปกติ อากาศค่อนข้างอ้าวช่วงบ่าย"},
        {"วันที่": "2026-06-07", "โรงเรือน": "House A", "จำนวนไก่ต้นวัน": 4997, "ไข่ที่เก็บได้ (ฟอง)": 4390, "น้ำหนักไข่รวม (กก.)": 276.5, "ไก่ตาย/คัดทิ้ง (ตัว)": 3, "อาหารที่กิน (กก.)": 568.0, "อุณหภูมิเฉลี่ย (°C)": 27.8, "หมายเหตุ": "ทำวัคซีนนิวคาสเซิลประจำรอบ"}
    ]

# ฐานข้อมูลกลางเก็บข้อมูลผู้ใช้งานระบบ
if "user_database" not in st.session_state:
    st.session_state.user_database = {
        "admin": {"password": "222", "name": "ผู้ดูแลระบบ", "surname": "ระดับสูง", "role": "admin", "tel": "089-999-9999", "reg_date": "2026-01-01"},
        "222": {"password": "222", "name": "แอดมินทางลัด", "surname": "ระบบผสม", "role": "admin", "tel": "088-888-8888", "reg_date": "2026-01-02"},
        "user": {"password": "123", "name": "สมชาย", "surname": "ใจดี", "role": "user", "tel": "081-234-5678", "reg_date": "2026-05-10"}
    }

# ฐานข้อมูลกลุ่มหลักสายพันธุ์ไก่ไข่
if "db_groups" not in st.session_state:
    st.session_state.db_groups = [
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "bg_color": "#b45309"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีขาว (Commercial White Layers)", "bg_color": "#0284c7"}
    ]

# ฐานข้อมูลสายพันธุ์ย่อยภายใต้กลุ่มหลัก
if "db_breeds" not in st.session_state:
    st.session_state.db_breeds = [
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "breed_name": "สายพันธุ์ ไอซ่า บราวน์ (Isa Brown)", "egg_color": "สีน้ำตาลเข้ม", "default_feed": 114.0},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "breed_name": "สายพันธุ์ โลห์แมน บราวน์ (Lohmann Brown)", "egg_color": "สีน้ำตาลเงางาม", "default_feed": 116.0},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีขาว (Commercial White Layers)", "breed_name": "สายพันธุ์ ไฮ-ไลน์ ขาว ดับบลิว-36 (Hy-Line W-36)", "egg_color": "สีขาวสะอาดตา", "default_feed": 101.0}
    ]

# ฐานข้อมูลสารอาหารวัตถุดิบ
if "db_ingredients" not in st.session_state:
    st.session_state.db_ingredients = {
        "ข้าวโพดบดเม็ด (Ground Corn)": {"name": "ข้าวโพดบดเม็ด (Ground Corn)", "price": 13.5, "protein": 8.5, "me": 3300.0, "calcium": 0.02, "phos": 0.25, "lysine": 0.24, "methionine": 0.18, "fiber": 2.2, "min_limit": 0.0, "max_limit": 70.0},
        "กากถั่วเหลือง 46% (Soybean Meal 46%)": {"name": "กากถั่วเหลือง 46% (Soybean Meal 46%)", "price": 19.5, "protein": 46.0, "me": 2440.0, "calcium": 0.25, "phos": 0.62, "lysine": 2.85, "methionine": 0.65, "fiber": 3.5, "min_limit": 0.0, "max_limit": 50.0},
        "ปลาป่นเกรด A 60% (Fish Meal 60%)": {"name": "ปลาป่นเกรด A 60% (Fish Meal 60%)", "price": 35.0, "protein": 60.0, "me": 2850.0, "calcium": 5.00, "phos": 3.00, "lysine": 4.50, "methionine": 1.80, "fiber": 1.0, "min_limit": 0.0, "max_limit": 12.0},
        "หินฝุ่นเม็ดหยาบ (Coarse Limestone)": {"name": "หินฝุ่นเม็ดหยาบ (Coarse Limestone)", "price": 2.5, "protein": 0.0, "me": 0.0, "calcium": 38.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "fiber": 0.0, "min_limit": 0.0, "max_limit": 15.0},
        "ไดแคลเซียมฟอสเฟต (DCP 18%)": {"name": "ไดแคลเซียมฟอสเฟต (DCP 18%)", "price": 28.0, "protein": 0.0, "me": 0.0, "calcium": 21.00, "phos": 18.00, "lysine": 0.00, "methionine": 0.00, "fiber": 0.0, "min_limit": 0.0, "max_limit": 4.0},
        "เกลือแกงบริสุทธิ์ (Refined Salt)": {"name": "เกลือแกงบริสุทธิ์ (Refined Salt)", "price": 6.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "fiber": 0.0, "min_limit": 0.10, "max_limit": 0.50},
        "พรีมิกซ์วิตามินแร่ธาตุ (Vitamin-Mineral Premix)": {"name": "พรีมิกซ์วิตามินแร่ธาตุ (Vitamin-Mineral Premix)", "price": 160.0, "protein": 0.0, "me": 0.0, "calcium": 5.00, "phos": 1.20, "lysine": 0.00, "methionine": 0.00, "fiber": 0.0, "min_limit": 0.20, "max_limit": 0.40},
        "DL-Methionine": {"name": "DL-Methionine", "price": 145.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 99.00, "fiber": 0.0, "min_limit": 0.0, "max_limit": 1.00},
        "L-Lysine HCl": {"name": "L-Lysine HCl", "price": 95.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 78.40, "methionine": 0.00, "fiber": 0.0, "min_limit": 0.0, "max_limit": 1.00}
    }

# ฐานข้อมูลเป้าหมายความต้องการสารอาหารตามช่วงระยะการไข่
if "db_targets" not in st.session_state:
    st.session_state.db_targets = {
        "layer_phase_1": {"stage_key": "layer_phase_1", "stage_name": "ระยะผลิตไข่พีค ช่วงที่ 1 อายุ 19-45 สัปดาห์", "protein": 17.5, "me": 2750.0, "calcium": 4.10, "phos": 0.42, "lysine": 0.88, "methionine": 0.42, "fiber_max": 4.5},
        "layer_phase_2": {"stage_key": "layer_phase_2", "stage_name": "ระยะกลาง ช่วงที่ 2 อายุ 46-65 สัปดาห์", "protein": 16.5, "me": 2725.0, "calcium": 4.30, "phos": 0.38, "lysine": 0.82, "methionine": 0.39, "fiber_max": 5.0}
    }

if "current_weights" not in st.session_state:
    st.session_state.current_weights = {}

# ==========================================
# 🧮 3. CORE AI SOLVER ENGINE
# ==========================================
def run_ai_solver(req_p, req_m, req_c, req_ph, req_ly, req_me):
    prob = pulp.LpProblem("AI_First_Solver", pulp.LpMinimize)
    ing_vars = {name: pulp.LpVariable(name, lowBound=float(d["min_limit"])/100.0, upBound=float(d["max_limit"])/100.0) for name, d in st.session_state.db_ingredients.items()}
    
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
        st.markdown("<h2 style='text-align: center; color: #ffb703 !important;'>🔐 เข้าสู่ระบบ Layer Nutrition Studio Pro</h2>", unsafe_allow_html=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        
        email_login = st.text_input("📧 อีเมลเข้าใช้งาน (หรือพิมพ์ '222' สำหรับแอดมินทางลัด):", key="login_email")
        pass_login = st.text_input("🔑 รหัสผ่านเข้าใช้งาน (ป้อน '222' หรือ '123'):", type="password", key="login_pass")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("เข้าสู่ระบบ (Log In)", type="primary", use_container_width=True):
                if email_login in st.session_state.user_database and st.session_state.user_database[email_login]["password"] == pass_login:
                    user_info = st.session_state.user_database[email_login]
                    st.session_state.is_authenticated = True
                    st.session_state.user_role = user_info.get("role", "user")
                    st.session_state.user_email = f"{user_info['name']} [{user_info['role'].upper()}]"
                    st.session_state.current_user_key = email_login
                    st.rerun()
                else:
                    st.error("❌ อีเมลหรือรหัสผ่านไม่ถูกต้อง")
        with col_btn2:
            if st.button("🆕 สมัครสมาชิกใหม่ที่นี่", use_container_width=True):
                st.session_state.auth_page_mode = "signup"
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    elif st.session_state.auth_page_mode == "signup":
        st.markdown("<div class='content-card' style='max-width: 600px; margin: 40px auto 0 auto;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #38bdf8 !important;'>📝 สมัครสมาชิกฟาร์มใหม่ (Sign Up)</h2>", unsafe_allow_html=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        
        su_name = st.text_input("👤 ชื่อจริง (First Name):")
        su_surname = st.text_input("👤 นามสกุล (Last Name):")
        su_tel = st.text_input("📞 เบอร์โทรศัพท์ติดต่อ:")
        su_email = st.text_input("📧 อีเมลบัญชีผู้ใช้ (ใช้เป็นไอดีสำหรับ Log In):")
        su_pass = st.text_input("🔑 รหัสผ่านความปลอดภัยที่ต้องการ:", type="password")
        
        col_su1, col_su2 = st.columns(2)
        with col_su1:
            if st.button("✅ ยืนยันการลงทะเบียน", type="primary", use_container_width=True):
                if su_email and su_pass and su_name:
                    if su_email in st.session_state.user_database:
                        st.error("❌ อีเมลนี้เคยลงทะเบียนในระบบฟาร์มแล้ว")
                    else:
                        st.session_state.user_database[su_email] = {
                            "password": su_pass, "name": su_name, "surname": su_surname,
                            "role": "user", "tel": su_tel, "reg_date": str(datetime.date.today())
                        }
                        st.success("🎉 สมัครสมาชิกสำเร็จ! ระบบพากลับหน้าเข้าสู่ระบบ...")
                        st.session_state.auth_page_mode = "login"
                        st.rerun()
                else:
                    st.warning("⚠️ กรุณากรอกข้อมูลในช่องจำเป็นให้ครบถ้วน")
        with col_su2:
            if st.button("⬅️ ย้อนกลับไปหน้าล็อกอิน", use_container_width=True):
                st.session_state.auth_page_mode = "login"
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

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
    # 🛠️ ADMIN ROUTE: FULL CRUD CONTROL PANEL
    # -----------------------------------------------------------------------------------------
    st.markdown("<div style='background-color:#1e3a8a; padding:15px; border-radius:10px; margin-bottom:20px;'><h3 style='margin:0; color:#93c5fd !important;'>🛠️ FULL CRUD CONTROL PANEL: หน้าบริหารจัดการฐานข้อมูลระบบฟาร์ม</h3></div>", unsafe_allow_html=True)
    admin_tabs = st.tabs(["🌽 จัดการวัตถุดิบอาหาร", "🐓 จัดการสายพันธุ์ไก่ไข่", "🧬 จัดการเกณฑ์โภชนาการอายุ", "👤 จัดการบัญชีผู้ใช้ (User Management)"])
    
    with admin_tabs[0]:
        st.markdown("<div class='content-card'>### 🌽 เพิ่ม/แก้ไขคลังวัตถุดิบหลัก (Full CRUD)</div>", unsafe_allow_html=True)
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
            if st.button("💾 บันทึกวัตถุดิบลงเซิร์ฟเวอร์"):
                if ing_name:
                    st.session_state.db_ingredients[ing_name] = {"name": ing_name, "price": ing_price, "protein": ing_prot, "me": ing_me, "calcium": ing_ca, "phos": ing_phos, "lysine": ing_lys, "methionine": ing_meth, "fiber": ing_fiber, "min_limit": ing_min, "max_limit": ing_max}
                    st.success("บันทึกข้อมูลวัตถุดิบเรียบร้อย!"); st.rerun()
        with c2:
            st.markdown("#### ❌ ลบวัตถุดิบออกจากระบบ")
            to_del = st.selectbox("เลือกวัตถุดิบที่จะลบออกจากคลัง:", list(st.session_state.db_ingredients.keys()))
            if st.button("🗑 `Confirm` ยืนยันลบวัตถุดิบ"):
                del st.session_state.db_ingredients[to_del]; st.warning("ลบข้อมูลเรียบร้อย!"); st.rerun()

    with admin_tabs[1]:
        st.markdown("<div class='content-card'>### 🐓 จัดการข้อมูลสายพันธุ์ไก่ไข่และกลุ่มหลัก (Full CRUD)</div>", unsafe_allow_html=True)
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("##### 📁 กลุ่มหลักปัจจุบันในระบบ")
            st.dataframe(pd.DataFrame(st.session_state.db_groups), use_container_width=True)
            new_g_name = st.text_input("➕ เพิ่มชื่อกลุ่มสายพันธุ์หลักใหม่:")
            if st.button("💾 บันทึกกลุ่มใหม่"):
                if new_g_name:
                    st.session_state.db_groups.append({"group_name": new_g_name, "bg_color": "#475569"})
                    st.success("เพิ่มกลุ่มสำเร็จ"); st.rerun()
        with col_g2:
            st.markdown("##### 🐔 รายชื่อสายพันธุ์ทั้งหมด")
            st.dataframe(pd.DataFrame(st.session_state.db_breeds), use_container_width=True)
            
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        bc1, bc2 = st.columns(2)
        with bc1:
            st.markdown("#### ➕ เพิ่มสายพันธุ์การค้า")
            b_group = st.selectbox("เลือกกลุ่มหลักที่จะสังกัด:", [g["group_name"] for g in st.session_state.db_groups])
            b_name = st.text_input("ชื่อทางการค้าของสายพันธุ์ใหม่:")
            b_egg = st.text_input("สีของเปลือกไข่:")
            b_feed = st.number_input("อัตรากินอาหารมาตรฐาน (กรัม/ตัว/วัน):", value=115.0)
            if st.button("➕ ยืนยันเพิ่มสายพันธุ์ใหม่"):
                if b_name:
                    st.session_state.db_breeds.append({"group_name": b_group, "breed_name": b_name, "egg_color": b_egg, "default_feed": b_feed})
                    st.success("เพิ่มข้อมูลสายพันธุ์เรียบร้อย!"); st.rerun()
        with bc2:
            st.markdown("#### ❌ ลบสายพันธุ์การค้า")
            b_del = st.selectbox("เลือกสายพันธุ์ที่ต้องการลบ:", [b["breed_name"] for b in st.session_state.db_breeds])
            if st.button("🗑️ ยืนยันลบสายพันธุ์นี้"):
                st.session_state.db_breeds = [b for b in st.session_state.db_breeds if b["breed_name"] != b_del]
                st.warning("ลบออกเรียบร้อยแล้ว!"); st.rerun()

    with admin_tabs[2]:
        st.markdown("<div class='content-card'>### 🧬 จัดการเกณฑ์โภชนาการเป้าหมายตามช่วงอายุสัตว์</div>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame.from_dict(st.session_state.db_targets, orient='index'), use_container_width=True)

    with admin_tabs[3]:
        st.markdown("<div class='content-card'>### 👤 ระบบบริหารจัดการบัญชีผู้ใช้งานระบบฟาร์ม (User Matrix Access Control)</div>", unsafe_allow_html=True)
        users_list = []
        for email, info in st.session_state.user_database.items():
            users_list.append({
                "Email ID / Username": email, "ชื่อ": info.get("name", "-"), "นามสกุล": info.get("surname", "-"),
                "เบอร์โทรศัพท์": info.get("tel", "-"), "บทบาทผู้ใช้ (Role)": info.get("role", "user"), "วันที่ลงทะเบียน": info.get("reg_date", "2026-01-01")
            })
        st.dataframe(pd.DataFrame(users_list), use_container_width=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        
        uc1, uc2 = st.columns(2)
        with uc1:
            st.markdown("#### ✏️ แก้ไขสิทธิ์/บทบาทของผู้ใช้งาน (Update Role)")
            selected_user_email = st.selectbox("เลือกบัญชีผู้ใช้ที่ต้องการเปลี่ยนสิทธิ์:", list(st.session_state.user_database.keys()))
            new_role = st.selectbox("กำหนดบทบาทใหม่ให้กับผู้ใช้รายนี้:", ["user", "admin"], index=0 if st.session_state.user_database[selected_user_email]["role"] == "user" else 1)
            if st.button("💾 ยืนยันอัปเดตสิทธิ์บัญชีนี้", use_container_width=True):
                st.session_state.user_database[selected_user_email]["role"] = new_role
                st.success(f"เปลี่ยนบทบาทของ {selected_user_email} เป็น {new_role.upper()} สำเร็จแล้ว!"); st.rerun()
        with uc2:
            st.markdown("#### ❌ ลบบัญชีผู้ใช้ถาวร (Delete User)")
            user_to_delete = st.selectbox("เลือกบัญชีผู้ใช้ที่ต้องการลบออกจากระบบ:", ["-- เลือกบัญชีเพื่อลบ --"] + list(st.session_state.user_database.keys()))
            if st.button("🗑️ ยืนยันการลบบัญชีผู้ใช้นี้", type="primary", use_container_width=True):
                if user_to_delete != "-- เลือกบัญชีเพื่อลบ --":
                    if user_to_delete in ["admin", "222"]: st.error("❌ ไม่สามารถลบบัญชีผู้ดูแลระบบหลักได้")
                    elif user_to_delete == st.session_state.get("current_user_key"): st.error("❌ คุณไม่สามารถลบบัญชีตัวเองได้")
                    else:
                        del st.session_state.user_database[user_to_delete]
                        st.warning(f"ลบบัญชีผู้ใช้ {user_to_delete} ออกแล้ว!"); st.rerun()
        
    if st.button("🔄 สลับกลับไปใช้โหมดหน้าจอปรับสูตร (User Menu)"):
        st.session_state.user_role = "user"
        st.rerun()

else:
    # -----------------------------------------------------------------------------------------
    # 👑 USER ROUTE: UNIFIED HYBRID MATRIX INTERFACE (EVERYTHING NEEDED FOR LAYER FARM)
    # -----------------------------------------------------------------------------------------
    page_tabs = st.tabs([
        "🏠 คำนวณสูตรอาหาร (Live Matrix)", 
        "📊 บันทึกผลผลิตประจำวัน & KPIs ฟาร์ม (Daily Log & Metrics)",
        "📋 สั่งซื้อวัตถุดิบ & แผนแบ่งชั่ง (Procurement)", 
        "📈 ประวัติสูตรอาหาร (History)"
    ])
    
    # -------------------------------------------------------------
    # TAB 1: FORMULATION ENGINE
    # -------------------------------------------------------------
    with page_tabs[0]:
        st.markdown("<div class='content-card'>### 🐓 ข้อมูลฝูงและโครงสร้างสายพันธุ์ไก่ไข่</div>", unsafe_allow_html=True)
        col_br1, col_br2, col_br3 = st.columns(3)
        with col_br1:
            selected_g = st.selectbox("📁 เลือกกลุ่มสายพันธุ์หลัก:", [g["group_name"] for g in st.session_state.db_groups])
        with col_br2:
            filtered_breeds = [b for b in st.session_state.db_breeds if b["group_name"] == selected_g]
            breed_names = [b["breed_name"] for b in filtered_breeds] if filtered_breeds else ["ไม่มีข้อมูล"]
            selected_b_name = st.selectbox("🐔 เลือกสายพันธุ์ไก่ไข่ทางเศรษฐกิจ:", breed_names)
            current_breed_data = next((b for b in filtered_breeds if b["breed_name"] == selected_b_name), {"default_feed": 114.0, "egg_color": "ไม่ระบุ"})
        with col_br3:
            st.markdown(f"<p style='margin-top:25px; color:#38bdf8; font-weight:bold;'>🎨 สีเปลือกไข่: {current_breed_data['egg_color']}<br>🍽️ กินอาหารมาตรฐาน: {current_breed_data['default_feed']} กรัม/ตัว/วัน</p>", unsafe_allow_html=True)

        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        col_top1, col_top2, col_top3 = st.columns(3)
        with col_top1:
            selected_stage_label = st.selectbox("📋 เลือกช่วงระยะการออกไข่:", list({s["stage_name"]: s["stage_key"] for s in st.session_state.db_targets.values()}.keys()))
            base_req = st.session_state.db_targets[{s["stage_name"]: s["stage_key"] for s in st.session_state.db_targets.values()}[selected_stage_label]]
        with col_top2:
            egg_price = st.number_input("💰 ราคารับซื้อไข่หน้าฟาร์มเฉลี่ย (บาท/ฟอง):", min_value=1.0, value=4.10)
        with col_top3:
            laying_rate = st.slider("📊 อัตราการให้ไข่เฉลี่ยของฝูงปัจจุบัน (%):", 10, 100, 85)
        st.markdown("</div>", unsafe_allow_html=True)

        if not st.session_state.current_weights:
            st.session_state.current_weights = run_ai_solver(base_req["protein"], base_req["me"], base_req["calcium"], base_req["phos"], base_req["lysine"], base_req["methionine"])

        col_left, col_right = st.columns([1.1, 0.9])
        with col_left:
            st.markdown("<div class='content-card'>### 🥣 1. สัดส่วนและปริมาณวัตถุดิบดิบที่ใช้ (%)</div>", unsafe_allow_html=True)
            temp_weights = {}
            running_total = 0.0
            for name, d in st.session_state.db_ingredients.items():
                saved_w = max(0.0, min(100.0, float(st.session_state.current_weights.get(name, 0.0))))
                user_val = st.slider(f"🌽 {name} ({d['price']} บ./กก.)", 0.0, 100.0, saved_w, 0.1, key=f"sld_u_{name}")
                temp_weights[name] = user_val
                running_total += user_val
            
            if abs(running_total - 100.0) > 0.1:
                st.markdown(f"<div style='background-color:#991b1b; padding:10px; border-radius:8px; font-weight:bold; text-align:center;'>⚠️ สัดส่วนรวมได้: {running_total:.1f}% (กรุณาปรับให้ครบ 100%)</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='background-color:#065f46; padding:10px; border-radius:8px; font-weight:bold; text-align:center;'>🟢 สัดส่วนครบถ้วนสมบูรณ์: 100%</div>", unsafe_allow_html=True)
            st.session_state.current_weights = temp_weights

        with col_right:
            st.markdown("<div class='content-card'>### 🧪 2. ตารางระดับโภชนาการเเละเป้าหมายควบคุม</div>", unsafe_allow_html=True)
            net_cost = 0.0
            act_nut = {"protein": 0.0, "me": 0.0, "calcium": 0.0, "phos": 0.0, "lysine": 0.0, "methionine": 0.0}
            divisor = sum(st.session_state.current_weights.values()) if sum(st.session_state.current_weights.values()) > 0 else 1.0
            
            for name, w in st.session_state.current_weights.items():
                r = w / divisor
                net_cost += r * float(st.session_state.db_ingredients[name]["price"])
                for k in act_nut.keys(): act_nut[k] += r * float(st.session_state.db_ingredients[name].get(k, 0.0))
            
            c_cell1, c_cell2 = st.columns(2)
            with c_cell1:
                edit_p = st.number_input("🎯 โปรตีนเป้าหมาย (%):", value=float(base_req["protein"]))
                edit_m = st.number_input("🎯 พลังงานเป้าหมาย (kcal):", value=float(base_req["me"]))
            with c_cell2:
                edit_c = st.number_input("🎯 แคลเซียมเป้าหมาย (%):", value=float(base_req["calcium"]))
                if st.button("⚡ ให้ AI คำนวณสูตรด่วน", type="primary", use_container_width=True):
                    st.session_state.current_weights = run_ai_solver(edit_p, edit_m, edit_c, base_req["phos"], base_req["lysine"], base_req["methionine"])
                    st.rerun()
            
            st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
            comparison_table = [
                {"โภชนาการ": "โปรตีนดิบ (CP %)", "เป้าหมาย": f"{edit_p:.2f} %", "ได้จริงในสูตร": f"{act_nut['protein']:.2f} %"},
                {"โภชนาการ": "พลังงาน (ME kcal/kg)", "เป้าหมาย": f"{edit_m:.0f}", "ได้จริงในสูตร": f"{act_nut['me']:.0f}"},
                {"โภชนาการ": "แคลเซียม (Ca %)", "เป้าหมาย": f"{edit_c:.2f} %", "ได้จริงในสูตร": f"{act_nut['calcium']:.2f} %"}
            ]
            st.dataframe(pd.DataFrame(comparison_table), use_container_width=True, hide_index=True)
            
            # คำนวณ IOFC เบื้องต้น
            f_consumed = float(current_breed_data["default_feed"]) / 1000.0
            st.metric("💰 ต้นทุนค่าอาหารสูตรนี้", f"{net_cost:.2f} บาท/กก.")
            st.metric("📈 กำไรเหนือค่าอาหาร (IOFC)", f"{((laying_rate/100.0)*egg_price) - (f_consumed*net_cost):.2f} บาท/ตัว/วัน")
            
            save_name_input = st.text_input("ตั้งชื่อเล่นสูตรเพื่อเซฟ:", value=f"สูตรผสมวันที่ {datetime.date.today()}")
            if st.button("📥 บันทึกสูตรลงคลังส่วนตัว"):
                st.session_state.saved_formulas.append({
                    "date": str(datetime.date.today()), 
                    "name": save_name_input, 
                    "cost": round(net_cost, 2), 
                    "breed": selected_b_name, 
                    "stage": selected_stage_label, 
                    "protein": round(act_nut["protein"], 2), 
                    "me": round(act_nut["me"], 0), 
                    "calcium": round(act_nut["calcium"], 2), 
                    "weights": st.session_state.current_weights.copy()
                })
                st.success("บันทึกสูตรเข้าประวัติสำเร็จ!")

    # -------------------------------------------------------------
    # TAB 2: FARM PRODUCTION LOGS & LIVE KPIs 
    # -------------------------------------------------------------
    with page_tabs[1]:
        st.markdown("<div class='content-card'><h2>📊 ระบบบันทึกผลผลิตและวิเคราะห์ประสิทธิภาพโรงเรือน (Flock KPIs)</h2></div>", unsafe_allow_html=True)
        
        # ฟอร์มบันทึกข้อมูลประจำวัน
        with st.expander("📝 เปิดฟอร์มบันทึกข้อมูลประจำวันเข้าสู่ระบบ (Daily Entry Form)", expanded=True):
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            with f_col1:
                log_date = st.date_input("เลือกวันที่บันทึก:", datetime.date.today())
                log_house = st.selectbox("เลือกโรงเรือน:", ["House A", "House B", "House C"])
            with f_col2:
                log_birds = st.number_input("จำนวนไก่ ณ ต้นวัน (ตัว):", min_value=1, value=5000, step=100)
                log_eggs = st.number_input("จำนวนไข่ที่เก็บได้ทั้งหมด (ฟอง):", min_value=0, value=4400, step=10)
            with f_col3:
                log_egg_w = st.number_input("น้ำหนักไข่รวมทั้งหมด (กิโลกรัม):", min_value=0.0, value=275.0, step=1.0)
                log_dead = st.number_input("ไก่ตาย / คัดทิ้งวันนี้ (ตัว):", min_value=0, value=2, step=1)
            with f_col4:
                log_feed = st.number_input("อาหารที่ไก่กินรวมวันนี้ (กิโลกรัม):", min_value=0.0, value=570.0, step=5.0)
                log_temp = st.number_input("อุณหภูมิเฉลี่ยในโรงเรือน (°C):", min_value=15.0, value=28.0, step=0.5)
            
            log_note = st.text_input("📝 บันทึกเพิ่มเติม (เช่น การทำวัคซีน, ยา, ข้อมูลสภาพอากาศ):", placeholder="ปกติ / ทำวัคซีนนิวคาสเซิล...")
            
            if st.button("💾 บันทึกข้อมูลการผลิตของวันนี้", type="primary"):
                st.session_state.farm_production_logs.append({
                    "วันที่": str(log_date), "โรงเรือน": log_house, "จำนวนไก่ต้นวัน": log_birds,
                    "ไข่ที่เก็บได้ (ฟอง)": log_eggs, "น้ำหนักไข่รวม (กก.)": log_egg_w,
                    "ไก่ตาย/คัดทิ้ง (ตัว)": log_dead, "อาหารที่กิน (กก.)": log_feed,
                    "อุณหภูมิเฉลี่ย (°C)": log_temp, "หมายเหตุ": log_note
                })
                st.success("บันทึกข้อมูลฟาร์มประจำวันเรียบร้อยแล้ว!"); st.rerun()

        # ส่วนคำนวณและแสดงผล KPIs ทันทีแบบ Real-time
        if st.session_state.farm_production_logs:
            df_farm = pd.DataFrame(st.session_state.farm_production_logs)
            
            st.markdown("<div class='content-card'>### 📈 ผลวิเคราะห์ประสิทธิภาพของฝูงล่าสุด</div>", unsafe_allow_html=True)
            latest_data = df_farm.iloc[-1]
            
            # สูตรคำนวณสัตวบาลไก่ไข่
            calc_prod_rate = (latest_data["ไข่ที่เก็บได้ (ฟอง)"] / latest_data["จำนวนไก่ต้นวัน"]) * 100
            calc_fcr = latest_data["อาหารที่กิน (กก.)"] / latest_data["น้ำหนักไข่รวม (กก.)"] if latest_data["น้ำหนักไข่รวม (กก.)"] > 0 else 0
            calc_avg_egg_w = (latest_data["น้ำหนักไข่รวม (กก.)"] * 1000) / latest_data["ไข่ที่เก็บได้ (ฟอง)"] if latest_data["ไข่ที่เก็บได้ (ฟอง)"] > 0 else 0
            
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            with m_col1:
                st.metric("🥚 อัตราการไข่ (Egg Production)", f"{calc_prod_rate:.2f} %", help="เกณฑ์มาตรฐานควรอยู่ที่ 85-90% ในช่วงพีค")
            with m_col2:
                st.metric("🍽️ อัตราแลกอาหารเป็นไข่ (FCR / ไข่ 1 กก.)", f"{calc_fcr:.3f}", help="ปริมาณอาหารเป็นกิโลกรัมที่ใช้ในการผลิตไข่ 1 กิโลกรัม (ค่ายิ่งน้อยยิ่งดี มาตรฐานทั่วไปอยู่ที่ 2.0 - 2.2)")
            with m_col3:
                st.metric("⚖️ น้ำหนักไข่เฉลี่ยต่อฟอง", f"{calc_avg_egg_w:.1f} กรัม", help="น้ำหนักมาตรฐานเฉลี่ยควรอยู่ระหว่าง 60-65 กรัม")
            with m_col4:
                st.metric("🌡️ สภาพแวดล้อมโรงเรือน", f"{latest_data['อุณหภูมิเฉลี่ย (°C)']} °C")
                
            st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
            st.markdown("🌐 **ตารางบันทึกข้อมูลประวัติและสุขภาพฝูงย้อนหลัง**")
            st.dataframe(df_farm, use_container_width=True)
            
            if st.button("🗑️ รีเซ็ตล้างข้อมูลประวัติฟาร์มทั้งหมด"):
                st.session_state.farm_production_logs = []
                st.rerun()

    # -------------------------------------------------------------
    # TAB 3: PROCUREMENT BATCH SHEET & MIXING PLAN
    # -------------------------------------------------------------
    with page_tabs[2]:
        st.markdown("<div class='content-card'><h2>📋 ระบบออกเอกสารจัดเตรียมและสั่งซื้อวัตถุดิบ (Procurement & Mixing Plan)</h2></div>", unsafe_allow_html=True)
        total_tonnage = st.number_input("ระบุปริมาณอาหารสัตว์รวมทั้งหมดที่ต้องการใช้ผสมในรอบนี้ (กิโลกรัม):", min_value=100, value=1000, step=100)
        
        po_buffer = []
        total_po_cost = 0
        divisor = sum(st.session_state.current_weights.values()) if sum(st.session_state.current_weights.values()) > 0 else 1.0
        
        for ing_name, w_pct in st.session_state.current_weights.items():
            actual_pct = (w_pct / divisor) * 100.0
            if actual_pct > 0.01:
                weight_kg = (actual_pct / 100.0) * total_tonnage
                cost_item = weight_kg * float(st.session_state.db_ingredients[ing_name]["price"])
                total_po_cost += cost_item
                po_buffer.append({
                    "รายการวัตถุดิบที่ต้องจัดเตรียม": ing_name, 
                    "สัดส่วนการผสมจริง (%)": round(actual_pct, 2), 
                    "น้ำหนักที่ต้องแบ่งชั่งสุทธิ (KG)": round(weight_kg, 2), 
                    "ประมาณการราคาทุนแยกชิ้น (บาท)": round(cost_item, 2)
                })
                
        if po_buffer:
            st.dataframe(pd.DataFrame(po_buffer), use_container_width=True, hide_index=True)
            st.metric("💵 งบประมาณจัดซื้อและเตรียมของรวมทั้งสิ้นรอบนี้", f"{total_po_cost:,.2f} บาท")
        else:
            st.warning("⚠️ ไม่พบข้อมูลสัดส่วนวัตถุดิบในสูตรปัจจุบัน กรุณาเปิดหน้าแรกเพื่อให้ AI คำนวณสูตรอาหารก่อน")

    # -------------------------------------------------------------
    # TAB 4: HISTORY STORAGE
    # -------------------------------------------------------------
    with page_tabs[3]:
        st.markdown("<div class='content-card'><h2>📈 คลังประวัติสูตรอาหารที่เคยบันทึกไว้ (Saved Formula History)</h2></div>", unsafe_allow_html=True)
        if not st.session_state.saved_formulas:
            st.info("💡 ขณะนี้ยังไม่มีรายการสูตรอาหารในคลังประวัติ สามารถกดเซฟสูตรได้ที่แท็บ 'คำนวณสูตรอาหาร'")
        else:
            df_history = pd.DataFrame(st.session_state.saved_formulas).drop(columns=["weights"])
            st.dataframe(df_history, use_container_width=True)
