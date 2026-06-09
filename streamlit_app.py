import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pulp
import io
import datetime
import re  # สำหรับตรวจสอบ Regex ความปลอดภัยของรหัสผ่าน

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
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False
if "auth_page_mode" not in st.session_state:
    st.session_state.auth_page_mode = "login"  
if "user_role" not in st.session_state:
    st.session_state.user_role = "user"  
if "saved_formulas" not in st.session_state:
    st.session_state.saved_formulas = []  
if "daily_logs" not in st.session_state:
    st.session_state.daily_logs = [] 

# ฟังก์ชันตรวจสอบระดับความปลอดภัยของรหัสผ่านตามมาตรฐานขั้นสูง
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
        return False, "❌ รหัสผ่านต้องมีอักขระพิเศษอย่างน้อย 1 ตัว (เช่น @, #, $, %, ., !, _)"
    return True, "🟢 รหัสผ่านมีความปลอดภัยสูงตามมาตรฐาน"

# ฐานข้อมูลกลางเก็บข้อมูลผู้ใช้งานระบบ (รหัสผ่านของสมาชิกใหม่จะต้องเป็นแบบ Secure Password)
if "user_database" not in st.session_state:
    st.session_state.user_database = {
        "admin": {"password": "AdminPassword@2026", "name": "ผู้ดูแลระบบ", "surname": "ระดับสูง", "role": "admin", "tel": "089-999-9999", "reg_date": "2026-01-01"},
        "222": {"password": "222", "name": "แอดมินทางลัด", "surname": "ระบบผสม", "role": "admin", "tel": "088-888-8888", "reg_date": "2026-01-02"},
        "user@farm.com": {"password": "UserPassword@2026", "name": "สมชาย", "surname": "ใจดี", "role": "user", "tel": "081-234-5678", "reg_date": "2026-05-10"}
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
# 🔒 4. SECURITY GATEWAY (LOGIN, SIGN UP & FORGOT PASSWORD)
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
                
        st.markdown("<div style='text-align: center; margin-top: 15px;'>", unsafe_allow_html=True)
        if st.button("❓ ลืมรหัสผ่านใช่หรือไม่?", type="secondary"):  # แก้ไขจุดที่ 1 ตรงนี้
            st.session_state.auth_page_mode = "forgot"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    # --- 4.2 หน้า SIGN UP (สมัครสมาชิกใหม่ + เช็ครหัสผ่านปลอดภัยสูง) ---
    elif st.session_state.auth_page_mode == "signup":
        st.markdown("<div class='content-card' style='max-width: 600px; margin: 40px auto 0 auto;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #38bdf8 !important;'>📝 สมัครสมาชิกฟาร์มใหม่ (Sign Up)</h2>", unsafe_allow_html=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        
        su_name = st.text_input("👤 ชื่อจริง:")
        su_surname = st.text_input("👤 นามสกุล:")
        su_tel = st.text_input("📞 เบอร์โทรศัพท์ติดต่อ (ใช้สำหรับกรณีกู้คืนรหัสผ่าน):")
        su_email = st.text_input("📧 อีเมลบัญชีผู้ใช้ (ใช้เป็นไอดีสำหรับ Log In):")
        
        st.markdown("<div style='background-color:#1e293b; padding:12px; border-radius:8px; margin-bottom:10px; font-size:0.85rem; color:#94a3b8;'>"
                    "🔒 **ข้อกำหนดรหัสผ่านความปลอดภัยสูง:**<br>"
                    "- ความยาวไม่น้อยกว่า 8 ตัวอักษร<br>"
                    "- มีอักษรพิมพ์ใหญ่ (A-Z) และพิมพ์เล็ก (a-z)<br>"
                    "- มีตัวเลข (0-9) และอักขระพิเศษอย่างน้อย 1 ตัว (@, #, $, %, !, ., _)"
                    "</div>", unsafe_allow_html=True)
        
        su_pass = st.text_input("🔑 ตั้งรหัสผ่านความปลอดภัยสูง:", type="password")
        su_pass_conf = st.text_input("🔄 พิมพ์ยืนยันรหัสผ่านอีกครั้ง:", type="password")
        
        # ตรวจสอบความแรงของรหัสผ่านแบบ Real-time
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
                    if su_email in st.session_state.user_database:
                        st.error("❌ อีเมลนี้เคยลงทะเบียนในระบบฟาร์มแล้ว")
                    elif su_pass != su_pass_conf:
                        st.error("❌ รหัสผ่านที่ยืนยัน ไม่ตรงกับรหัสผ่านตั้งต้น!")
                    elif not is_strong:
                        st.error("❌ ไม่สามารถลงทะเบียนได้ เนื่องจากรหัสผ่านไม่ปลอดภัยตามมาตรฐาน")
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

    # --- 4.3 หน้า FORGOT PASSWORD (ลืมรหัสผ่าน/กู้คืนบัญชี) ---
    elif st.session_state.auth_page_mode == "forgot":
        st.markdown("<div class='content-card' style='max-width: 550px; margin: 60px auto 0 auto;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #f43f5e !important;'>🔑 กู้คืนและตั้งรหัสผ่านใหม่</h2>", unsafe_allow_html=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        
        fg_email = st.text_input("📧 ป้อนอีเมลที่ลงทะเบียนไว้:")
        fg_tel = st.text_input("📞 ป้อนเบอร์โทรศัพท์ที่ลงทะเบียนไว้เพื่อตรวจสอบสิทธิ์:")
        
        if fg_email in st.session_state.user_database:
            user_found = st.session_state.user_database[fg_email]
            if user_found.get("tel") == fg_tel:
                st.info("🎯 ตรวจสอบข้อมูลถูกต้อง! กรุณาตั้งรหัสผ่านใหม่ที่ปลอดภัยด้านล่าง:")
                
                new_pass = st.text_input("🔑 กำหนดรหัสผ่านใหม่ความปลอดภัยสูง:", type="password", key="fg_new")
                new_pass_conf = st.text_input("🔄 พิมพ์ยืนยันรหัสผ่านใหม่อีกครั้ง:", type="password", key="fg_conf")
                
                is_new_strong, new_pass_msg = check_password_strength(new_pass) if new_pass else (False, "")
                if new_pass:
                    if is_new_strong: st.success(new_pass_msg)
                    else: st.warning(new_pass_msg)
                
                if st.button("💾 บันทึกเปลี่ยนรหัสผ่านใหม่", type="primary", use_container_width=True):
                    if new_pass != new_pass_conf:
                        st.error("❌ รหัสผ่านใหม่ทั้งสองช่องไม่ตรงกัน")
                    elif not is_new_strong:
                        st.error("❌ รหัสผ่านใหม่ไม่ปลอดภัยตามเกณฑ์มาตรฐาน")
                    else:
                        st.session_state.user_database[fg_email]["password"] = new_pass
                        st.success("🎉 เปลี่ยนรหัสผ่านสำเร็จ! ระบบกำลังนำคุณไปล็อกอิน...")
                        st.session_state.auth_page_mode = "login"
                        st.rerun()
            else:
                if fg_tel: st.error("❌ เบอร์โทรศัพท์ไม่ตรงกับข้อมูลในระบบ")
        else:
            if fg_email: st.error("❌ ไม่พบที่อยู่อีเมลนี้ในระบบ")
            
        if st.button("⬅️ ยกเลิกและกลับหน้าเข้าสู่ระบบ", use_container_width=True, type="secondary"):  # แก้ไขจุดที่ 2 ตรงนี้
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
    st.markdown("<div style='background-color:#1e3a8a; padding:15px; border-radius:10px; margin-bottom:20px;'><h3 style='margin:0; color:#93c5fd !important;'>💻 ระบบจัดการข้อมูลดิบหลังบ้าน (Master Data CRUD Management Control)</h3></div>", unsafe_allow_html=True)
    
    admin_tabs = st.tabs(["🌽 1. คลังวัตถุดิบ & แก้ไขสารอาหารแบบละเอียด", "🐓 2. จัดการข้อมูลทำเนียบสายพันธุ์", "🧬 3. แก้ไขเกณฑ์โภชนาการตามช่วงอายุ", "👤 4. จัดการสิทธิ์บัญชีผู้ใช้งาน"])
    
    # --- แท็บที่ 1: จัดการและแก้ไขวัตถุดิบ/สารอาหาร ---
    with admin_tabs[0]:
        st.markdown("<div class='content-card'>### 🌽 คลังข้อมูลดิบวัตถุดิบและข้อจำกัดในสูตร ณ ปัจจุบัน</div>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame.from_dict(st.session_state.db_ingredients, orient='index'), use_container_width=True)
        
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        
        crud_mode = st.radio("เลือกการทำงานที่ต้องการ:", ["✏️ แก้ไขข้อมูลสารอาหารวัตถุดิบเดิม", "➕ เพิ่มวัตถุดิบใหม่เข้าคลัง", "🗑️ ลบวัตถุดิบออกจากระบบ"], horizontal=True)
        st.markdown("<br>", unsafe_allow_html=True)

        if crud_mode == "✏️ แก้ไขข้อมูลสารอาหารวัตถุดิบเดิม":
            st.markdown("#### ✏️ ปรับปรุงแก้ไขค่าสารอาหารและราคากลางรายวัตถุดิบ")
            selected_ing_edit = st.selectbox("เลือกวัตถุดิบที่ต้องการเข้าไปแก้ไขข้อมูล:", list(st.session_state.db_ingredients.keys()))
            
            target_ing = st.session_state.db_ingredients[selected_ing_edit]
            
            ec_1, ec_2, ec_3 = st.columns(3)
            with ec_1:
                edit_ing_price = st.number_input("แก้ไขราคากลาง (บาท/กก.):", min_value=0.0, value=float(target_ing.get("price", 0.0)), step=0.1, key="e_price")
                edit_ing_prot = st.number_input("แก้ไขโปรตีนดิบ (% CP):", min_value=0.0, value=float(target_ing.get("protein", 0.0)), step=0.1, key="e_prot")
                edit_ing_me = st.number_input("แก้ไขพลังงานใช้ประโยชน์ได้ (ME kcal/kg):", min_value=0.0, value=float(target_ing.get("me", 0.0)), step=10.0, key="e_me")
                edit_ing_fiber = st.number_input("แก้ไขสัดส่วนเยื่อใยสูงสุด (% Fiber):", min_value=0.0, value=float(target_ing.get("fiber", 0.0)), step=0.1, key="e_fiber")
            with ec_2:
                edit_ing_ca = st.number_input("แก้ไขแคลเซียม (% Ca):", min_value=0.0, value=float(target_ing.get("calcium", 0.0)), step=0.01, key="e_ca")
                edit_ing_phos = st.number_input("แก้ไขฟอสฟอรัสเป็นประโยชน์ (% Avail. P):", min_value=0.0, value=float(target_ing.get("phos", 0.0)), step=0.01, key="e_phos")
                edit_ing_lys = st.number_input("แก้ไขอะมิโน ไลซีน (% Lys):", min_value=0.0, value=float(target_ing.get("lysine", 0.0)), step=0.01, key="e_lys")
                edit_ing_meth = st.number_input("แก้ไขอะมิโน เมทไธโอนีน (% Met):", min_value=0.0, value=float(target_ing.get("methionine", 0.0)), step=0.01, key="e_met")
            with ec_3:
                st.markdown("<div style='background-color:#334155; padding:15px; border-radius:10px;'><strong>⚙️ เกณฑ์จำกัดข้อกำหนดในการคำนวณสูตรของ AI</strong></div>", unsafe_allow_html=True)
                edit_ing_min = st.number_input("ข้อจำกัด: สัดส่วนขั้นต่ำที่ต้องใช้ในสูตร (% Min):", min_value=0.0, max_value=100.0, value=float(target_ing.get("min_limit", 0.0)), step=0.1, key="e_min")
                edit_ing_max = st.number_input("ข้อจำกัด: สัดส่วนสูงสุดที่ห้ามเกินในสูตร (% Max):", min_value=0.0, max_value=100.0, value=float(target_ing.get("max_limit", 100.0)), step=0.1, key="e_max")

            if st.button("💾 บันทึกอัปเดตการแก้ไขสารอาหารทั้งหมด", type="primary", use_container_width=True):
                st.session_state.db_ingredients[selected_ing_edit].update({
                    "price": edit_ing_price, "protein": edit_ing_prot, "me": edit_ing_me, 
                    "calcium": edit_ing_ca, "phos": edit_ing_phos, "lysine": edit_ing_lys, 
                    "methionine": edit_ing_meth, "fiber": edit_ing_fiber, 
                    "min_limit": edit_ing_min, "max_limit": edit_ing_max
                })
                st.success(f"🎉 อัปเดตโครงสร้างข้อมูลสารอาหารของวัตถุดิบ '{selected_ing_edit}' สำเร็จเรียบร้อย!"); st.rerun()

        elif crud_mode == "➕ เพิ่มวัตถุดิบใหม่เข้าคลัง":
            st.markdown("#### ➕ เพิ่มรายการวัตถุดิบใหม่และสารอาหารตั้งต้น")
            c1, c2 = st.columns(2)
            with c1:
                ing_name = st.text_input("ระบุชื่อวัตถุดิบใหม่:", placeholder="เช่น รำสกัดน้ำมันเกรด A")
                ing_price = st.number_input("ราคากลางตั้งต้น (บาท/กก.):", min_value=0.0, value=12.0)
                ing_prot = st.number_input("โปรตีนดิบเฉลี่ย (%):", min_value=0.0, value=10.0)
                ing_me = st.number_input("พลังงานใช้ประโยชน์ได้ ME (kcal/kg):", min_value=0.0, value=2500.0)
                ing_fiber = st.number_input("ปริมาณเยื่อใย (% Fiber):", min_value=0.0, value=2.0)
            with c2:
                ing_ca = st.number_input("ปริมาณแคลเซียม (% Ca):", min_value=0.0, value=0.0)
                ing_phos = st.number_input("ปริมาณฟอสฟอรัส (% P):", min_value=0.0, value=0.0)
                ing_lys = st.number_input("ปริมาณกรดอะมิโน ไลซีน (% Lys):", min_value=0.0, value=0.0)
                ing_meth = st.number_input("ปริมาณกรดอะมิโน เมทไธโอนีน (% Met):", min_value=0.0, value=0.0)
                ing_min = st.number_input("ข้อจำกัดขั้นต่ำที่ต้องใส่ในสูตร (%):", min_value=0.0, value=0.0)
                ing_max = st.number_input("ข้อจำกัดสูงสุดที่ใส่ได้ในสูตร (%):", min_value=0.0, value=100.0)
            
            if st.button("➕ ยืนยันเพิ่มวัตถุดิบชิ้นใหม่นี้เข้าฐานข้อมูลหลัก", use_container_width=True):
                if ing_name:
                    st.session_state.db_ingredients[ing_name] = {
                        "name": ing_name, "price": ing_price, "protein": ing_prot, "me": ing_me, 
                        "calcium": ing_ca, "phos": ing_phos, "lysine": ing_lys, "methionine": ing_meth, 
                        "fiber": ing_fiber, "min_limit": ing_min, "max_limit": ing_max
                    }
                    st.success(f"เพิ่มวัตถุดิบ '{ing_name}' เข้าสู่ระบบหลังบ้านเรียบร้อยแล้ว!"); st.rerun()
                else:
                    st.warning("⚠️ กรุณาระบุชื่อวัตถุดิบก่อนกดบันทึก")

        elif crud_mode == "🗑️ ลบวัตถุดิบออกจากระบบ":
            st.markdown("#### ❌ ลบรายการวัตถุดิบออกจากฐานข้อมูลระบบ")
            to_del = st.selectbox("เลือกวัตถุดิบที่จะถูกถอดออกจากฐานข้อมูลกลางถาวร:", list(st.session_state.db_ingredients.keys()))
            if st.button("🗑️ ยืนยันคำสั่งลบวัตถุดิบนี้ออกจากฐานข้อมูล", type="primary", use_container_width=True):
                del st.session_state.db_ingredients[to_del]
                st.warning(f"ถอนข้อมูล '{to_del}' ออกจากระบบเรียบร้อยแล้ว!"); st.rerun()

    # --- แท็บที่ 2: จัดการทำเนียบสายพันธุ์ ---
    with admin_tabs[1]:
        st.markdown("<div class='content-card'>### 🐓 รายชื่อสายพันธุ์ไก่ไข่ที่อนุญาตให้ใช้งานในระบบ</div>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(st.session_state.db_breeds), use_container_width=True)
            
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        bc1, bc2 = st.columns(2)
        with bc1:
            st.markdown("#### ➕ เพิ่มรายชื่อสายพันธุ์การค้าใหม่")
            b_group = st.selectbox("กำหนดกลุ่มสายพันธุ์หลัก:", [g["group_name"] for g in st.session_state.db_groups])
            b_name = st.text_input("ชื่อทางการค้าของสายพันธุ์ (Breed Name):", placeholder="เช่น นอฟ บราวน์")
            b_egg = st.text_input("ลักษณะเด่น/สีของเปลือกไข่:", placeholder="เช่น น้ำตาลอ่อน")
            b_feed = st.number_input("อัตราการบริโภคอาหารตามคู่มือสายพันธุ์ (กรัม/ตัว/วัน):", value=115.0)
            
            if st.button("➕ ยืนยันการเพิ่มสายพันธุ์เข้าทำเนียบ", use_container_width=True):
                if b_name:
                    st.session_state.db_breeds.append({
                        "group_name": b_group, "breed_name": b_name, "egg_color": b_egg, "default_feed": b_feed
                    })
                    st.success(f"เพิ่มข้อมูลสายพันธุ์ '{b_name}' เข้าสู่ระบบแล้ว!"); st.rerun()
                else:
                    st.warning("⚠️ กรุณากรอกชื่อสายพันธุ์")
        with bc2:
            st.markdown("#### ❌ ลบข้อมูลสายพันธุ์ออกจากทำเนียบ")
            b_del = st.selectbox("เลือกสายพันธุ์ที่ต้องการถอนรากถอนโคน:", [b["breed_name"] for b in st.session_state.db_breeds])
            if st.button("🗑️ ยืนยันลบสายพันธุ์นี้ออกจากระบบ", type="primary", use_container_width=True):
                st.session_state.db_breeds = [b for b in st.session_state.db_breeds if b["breed_name"] != b_del]
                st.warning(f"ถอดสายพันธุ์ '{b_del}' ออกเรียบร้อยแล้ว!"); st.rerun()

    # --- แท็บที่ 3: แก้ไขเป้าหมายความต้องการโภชนาการสัตว์แยกตามอายุ ---
    with admin_tabs[2]:
        st.markdown("<div class='content-card'>### 🧬 แก้ไขค่าเกณฑ์มาตรฐานความต้องการสารอาหารประจำช่วงอายุของสัตว์</div>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame.from_dict(st.session_state.db_targets, orient='index'), use_container_width=True)
        
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        st.markdown("#### ✏️ ปรับเปลี่ยนเกณฑ์ข้อกำหนดสารอาหารขั้นต่ำประจำช่วงอายุ")
        select_stage_crud = st.selectbox("เลือกช่วงระยะผลิตที่ต้องการปรับแก้เกณฑ์ควบคุม:", list(st.session_state.db_targets.keys()), format_func=lambda x: st.session_state.db_targets[x]["stage_name"])
        
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            crud_p = st.number_input("แก้ไขเกณฑ์โปรตีนขั้นต่ำ (% CP):", value=float(st.session_state.db_targets[select_stage_crud]["protein"]), step=0.1, key="c_p")
            crud_m = st.number_input("แก้ไขเกณฑ์พลังงานขั้นต่ำ (ME kcal/kg):", value=float(st.session_state.db_targets[select_stage_crud]["me"]), step=10.0, key="c_m")
        with sc2:
            crud_c = st.number_input("แก้ไขเกณฑ์แคลเซียมขั้นต่ำ (% Ca):", value=float(st.session_state.db_targets[select_stage_crud]["calcium"]), step=0.05, key="c_c")
            crud_ph = st.number_input("แก้ไขเกณฑ์ฟอสฟอรัสขั้นต่ำ (% P):", value=float(st.session_state.db_targets[select_stage_crud]["phos"]), step=0.02, key="c_ph")
        with sc3:
            crud_ly = st.number_input("แก้ไขเกณฑ์ไลซีนขั้นต่ำ (% Lys):", value=float(st.session_state.db_targets[select_stage_crud]["lysine"]), step=0.01, key="c_ly")
            crud_me = st.number_input("แก้ไขเกณฑ์เมทไธโอนีนขั้นต่ำ (% Met):", value=float(st.session_state.db_targets[select_stage_crud]["methionine"]), step=0.01, key="c_me")
            crud_fib = st.number_input("แก้ไขเกณฑ์เยื่อใยสูงสุดพึงมี (% Max Fiber):", value=float(st.session_state.db_targets[select_stage_crud].get("fiber_max", 4.5)), step=0.1, key="c_fib")
            
        if st.button("💾 ยืนยันบันทึกเกณฑ์โภชนาการช่วงอายุใหม่", use_container_width=True):
            st.session_state.db_targets[select_stage_crud].update({
                "protein": crud_p, "me": crud_m, "calcium": crud_c, "phos": crud_ph, "lysine": crud_ly, "methionine": crud_me, "fiber_max": crud_fib
            })
            st.success("🎉 อัปเดตเกณฑ์มาตรฐานความต้องการทางโภชนาการประจำช่วงอายุสำเร็จ!"); st.rerun()

    # --- แท็บที่ 4: จัดการสมาชิกผู้ใช้งาน ---
    with admin_tabs[3]:
        st.markdown("<div class='content-card'>### 👤 บัญชีรายชื่อผู้ใช้งานและระดับสิทธิ์การเข้าถึงระบบทั้งหมด (User Management)</div>", unsafe_allow_html=True)
        
        users_list = []
        for email, info in st.session_state.user_database.items():
            users_list.append({
                "Email ID / Username": email,
                "ชื่อ": info.get("name", "-"),
                "นามสกุล": info.get("surname", "-"),
                "เบอร์โทรศัพท์": info.get("tel", "-"),
                "บทบาทผู้ใช้ (Role)": info.get("role", "user"),
                "วันที่ลงทะเบียน": info.get("reg_date", "2026-01-01")
            })
        st.dataframe(pd.DataFrame(users_list), use_container_width=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        
        uc1, uc2 = st.columns(2)
        with uc1:
            st.markdown("#### ✏️ เปลี่ยนแปลงสิทธิ์ของกลุ่มผู้ใช้ (Update User Role)")
            selected_user_email = st.selectbox("เลือกบัญชีอีเมลที่ต้องการปรับระดับสิทธิ์:", list(st.session_state.user_database.keys()))
            new_role = st.selectbox("มอบสิทธิ์การใช้งานใหม่:", ["user", "admin"], index=0 if st.session_state.user_database[selected_user_email]["role"] == "user" else 1)
            
            if st.button("💾 บันทึกเปลี่ยนสิทธิ์การเข้าใช้งาน", use_container_width=True):
                st.session_state.user_database[selected_user_email]["role"] = new_role
                st.success(f"อัปเดตสิทธิ์ของ {selected_user_email} เป็น {new_role.upper()} เรียบร้อย!")
                st.rerun()
                
        with uc2:
            st.markdown("#### ❌ ลบบัญชีผู้ใช้ (Delete User Account)")
            user_to_delete = st.selectbox("เลือกไอดีผู้ใช้ที่ต้องการลบถาวร:", ["-- เลือกบัญชีเพื่อลบ --"] + list(st.session_state.user_database.keys()))
            
            if st.button("🗑️ ยืนยันคำสั่งระงับและลบบัญชีนี้", type="primary", use_container_width=True):
                if user_to_delete != "-- เลือกบัญชีเพื่อลบ --":
                    if user_to_delete in ["admin", "222"]:
                        st.error("❌ บัญชีผู้ดูแลระบบตั้งต้น (System Root Account) ไม่สามารถลบได้")
                    elif user_to_delete == st.session_state.get("current_user_key"):
                        st.error("❌ คุณไม่สามารถสั่งลบบัญชีปัจจุบันที่คุณกำลังล็อกอินทำงานอยู่ได้")
                    else:
                        del st.session_state.user_database[user_to_delete]
                        st.warning(f"ลบบัญชีผู้ใช้ {user_to_delete} เรียบร้อยแล้ว")
                        st.rerun()
        
    if st.button("🔄 ออกจากโหมดแอดมิน เพื่อไปหน้าสลับสูตรอาหาร (User Dashboard)"):
        st.session_state.user_role = "user"
        st.rerun()

else:
    # ==========================================
    # 👑 USER ROUTE: UNIFIED HYBRID MATRIX INTERFACE
    # ==========================================
    page_tabs = st.tabs([
        "🏠 หน้าจอคำนวณและผสมสูตรอาหาร (Unified Live Matrix)", 
        "☀️ บันทึกปฏิบัติงานฟาร์มรายวัน (Daily Temperature & Performance)",
        "📊 ใบจัดเตรียมและสั่งซื้อวัตถุดิบ (Procurement Batch Sheet)", 
        "📈 คลังประวัติสูตรอาหารส่วนตัว (Personal History Log)"
    ])

    with page_tabs[0]:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("### 🐓 ข้อมูลฝูงและโครงสร้างสายพันธุ์ไก่ไข่")
        
        col_br1, col_br2, col_br3 = st.columns(3)
        with col_br1:
            list_groups = [g["group_name"] for g in st.session_state.db_groups]
            selected_g = st.selectbox("📁 เลือกกลุ่มสายพันธุ์หลัก:", list_groups)
        with col_br2:
            filtered_breeds = [b for b in st.session_state.db_breeds if b["group_name"] == selected_g]
            breed_names = [b["breed_name"] for b in filtered_breeds] if filtered_breeds else ["ไม่มีข้อมูลสายพันธุ์ในระบบ"]
            selected_b_name = st.selectbox("🐔 เลือกสายพันธุ์ไก่ไข่ทางเศรษฐกิจ:", breed_names)
            current_breed_data = next((b for b in filtered_breeds if b["breed_name"] == selected_b_name), {"default_feed": 114.0, "egg_color": "ไม่ระบุ"})
        with col_br3:
            st.markdown(f"<p style='margin-top:25px; color:#38bdf8; font-weight:bold;'>🎨 ลักษณะสีเปลือกไข่: {current_breed_data['egg_color']}<br>🍽️ อัตรากินอาหารเฉลี่ย: {current_breed_data['default_feed']} กรัม/วัน</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        stage_options = {s["stage_name"]: s["stage_key"] for s in st.session_state.db_targets.values()}
        
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        col_top1, col_top2, col_top3 = st.columns(3)
        with col_top1:
            selected_stage_label = st.selectbox("📋 เลือกช่วงระยะการออกไข่ของฝูงปัจจุบัน:", list(stage_options.keys()))
            base_req = st.session_state.db_targets[stage_options[selected_stage_label]]
        with col_top2:
            egg_price = st.number_input("💰 ราคารับซื้อไข่หน้าฟาร์มปัจจุบัน (บาท/ฟอง):", min_value=1.0, value=4.10)
        with col_top3:
            laying_rate = st.slider("📊 อัตราการให้ไข่เฉลี่ยประจำสัปดาห์ของฝูง (%):", 10, 100, 85)
        st.markdown("</div>", unsafe_allow_html=True)

        if not st.session_state.current_weights:
            st.session_state.current_weights = run_ai_solver(
                base_req["protein"], base_req["me"], base_req["calcium"], base_req["phos"], base_req["lysine"], base_req["methionine"]
            )

        col_left, col_right = st.columns([1.1, 0.9])
        
        with col_left:
            st.markdown("<div class='content-card'>", unsafe_allow_html=True)
            cl_title, cl_reset = st.columns([6, 4])
            with cl_title:
                st.markdown("### 🥣 1. สัดส่วนวัตถุดิบที่ใช้ (%)")
            with cl_reset:
                if st.button("🔄 ล้างค่า/ใช้ค่า AI ตั้งต้น", use_container_width=True):
                    st.session_state.current_weights = run_ai_solver(
                        base_req["protein"], base_req["me"], base_req["calcium"], base_req["phos"], base_req["lysine"], base_req["methionine"]
                    )
                    st.rerun()
            
            temp_weights = {}
            running_total = 0.0
            
            # 🛑 1. กำหนดเกณฑ์มาตรฐานความปลอดภัย (Inclusion Limits)
            inclusion_limits = {
                "กากเบียร์แห้ง": 10.0,
                "กากน้ำตาล": 5.0,
                "น้ำมันปาล์ม": 4.0,
                "น้ำมันถั่วเหลือง": 4.0,
                "ข้าวนก": 15.0,
                "กากดีดีจีเอส": 15.0,
                "DDGS": 15.0
            }
            
            for name, d in st.session_state.db_ingredients.items():
                saved_w = float(st.session_state.current_weights.get(name, 0.0))
                saved_w = max(0.0, min(100.0, saved_w))
                
                user_val = st.slider(
                    f"🌽 {name} (ราคา {d['price']} บ./กก.)",
                    min_value=0.0, max_value=100.0, value=saved_w, step=0.1, key=f"sld_user_{name}"
                )
                
                # ตรวจสอบการใส่เกินเกณฑ์และแจ้งเตือนทันทีใต้ Slider ตัวนั้น
                if name in inclusion_limits and user_val > inclusion_limits[name]:
                    st.markdown(f"<p style='color:#f87171; font-size:13px; margin:-10px 0px 10px 0px;'>⚠️ คำเตือน: ไม่ควรใช้ {name} เกิน {inclusion_limits[name]}% เนื่องจากส่งผลต่อระบบย่อยของสัตว์ปีก</p>", unsafe_allow_html=True)
                    
                temp_weights[name] = user_val
                running_total += user_val
            
            if abs(running_total - 100.0) > 0.1:
                st.markdown(f"<div style='background-color:#991b1b; padding:10px; border-radius:8px; font-weight:bold; text-align:center;'>⚠️ สัดส่วนรวมได้: {running_total:.1f}% (กรุณาปรับแก้ให้ครบ 100% พอดี)</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='background-color:#065f46; padding:10px; border-radius:8px; font-weight:bold; text-align:center;'>🟢 สัดส่วนรวมครบถ้วนสมบูรณ์: 100%</div>", unsafe_allow_html=True)
            
            st.session_state.current_weights = temp_weights
            st.markdown("</div>", unsafe_allow_html=True)

        with col_right:
            st.markdown("<div class='content-card'>", unsafe_allow_html=True)
            st.markdown("### 🧪 2. ตารางระดับโภชนาการเเละเป้าหมายควบคุม")
            
            net_cost = 0.0
            act_nut = {"protein": 0.0, "me": 0.0, "calcium": 0.0, "phos": 0.0, "lysine": 0.0, "methionine": 0.0, "fiber": 0.0}
            total_w = sum(st.session_state.current_weights.values())
            divisor = total_w if total_w > 0 else 1.0
            
            for name, w in st.session_state.current_weights.items():
                if name in st.session_state.db_ingredients:
                    ratio = w / divisor
                    net_cost += ratio * float(st.session_state.db_ingredients[name]["price"])
                    for k in act_nut.keys():
                        act_nut[k] += ratio * float(st.session_state.db_ingredients[name].get(k, 0.0))
            
            col_cell1, col_cell2 = st.columns([1, 1])
            with col_cell1:
                edit_p = st.number_input("🎯 โปรตีนเป้าหมาย (% CP):", min_value=5.0, value=float(base_req["protein"]), step=0.1)
                edit_m = st.number_input("🎯 พลังงานเป้าหมาย (ME kcal/kg):", min_value=1000.0, value=float(base_req["me"]), step=25.0)
                edit_c = st.number_input("🎯 แคลเซียมเป้าหมาย (% Ca):", min_value=0.5, value=float(base_req["calcium"]), step=0.05)
            with col_cell2:
                edit_ph = st.number_input("🎯 ฟอสฟอรัสเป้าหมาย (% P):", min_value=0.1, value=float(base_req["phos"]), step=0.02)
                edit_ly = st.number_input("🎯 ไลซีนเป้าหมาย (% Lys):", min_value=0.1, value=float(base_req["lysine"]), step=0.01)
                edit_me = st.number_input("🎯 เมทไธโอนีนเป้าหมาย (% Met):", min_value=0.1, value=float(st.session_state.db_targets[stage_options[selected_stage_label]]["methionine"]), step=0.01)
            
            if st.button("⚡ สั่ง AI คำนวณสัดส่วนใหม่ยึดตามค่าเป้าหมายด้านบนนี้", type="primary", use_container_width=True):
                with st.spinner("AI กำลังปรับสัดส่วนโครงสร้างสูตร..."):
                    st.session_state.current_weights = run_ai_solver(edit_p, edit_m, edit_c, edit_ph, edit_ly, edit_me)
                    st.success("🤖 AI ปรับสัดส่วนวัตถุดิบเรียบร้อยแล้ว!")
                    st.rerun()
            
            st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
            
            if act_nut["protein"] < edit_p - 0.1:
                st.error(f"🚨 โปรตีนต่ำเกินไป! ได้แค่ {act_nut['protein']:.2f}% (เป้าหมาย: {edit_p}%)")
            if act_nut["me"] < edit_m - 10:
                st.error(f"🚨 พลังงานขาด! ได้แค่ {act_nut['me']:.0f} kcal (เป้าหมาย: {edit_m} kcal)")
            if act_nut["calcium"] < edit_c - 0.05:
                st.warning(f"⚠️ แคลเซียมต่ำไป! เปลือกไข่อาจจะบาง ({act_nut['calcium']:.2f}%)")
            
            comparison_table = [
                {"โภชนาการ": "โปรตีนดิบ (Crude Protein %)", "เป้าหมาย": f"{edit_p:.2f} %", "ได้จริงในสูตร": f"{act_nut['protein']:.2f} %"},
                {"โภชนาการ": "พลังงานใช้ประโยชน์ได้ (ME kcal/kg)", "เป้าหมาย": f"{edit_m:.0f}", "ได้จริงในสูตร": f"{act_nut['me']:.0f}"},
                {"โภชนาการ": "แคลเซียม (% Calcium)", "เป้าหมาย": f"{edit_c:.2f} %", "ได้จริงในสูตร": f"{act_nut['calcium']:.2f} %"},
                {"โภชนาการ": "ฟอสฟอรัสเป็นประโยชน์ (% Avail. P)", "เป้าหมาย": f"{edit_ph:.2f} %", "ได้จริงในสูตร": f"{act_nut['phos']:.2f} %"},
                {"โภชนาการ": "ไลซีน (% Lysine)", "เป้าหมาย": f"{edit_ly:.2f} %", "ได้จริงในสูตร": f"{act_nut['lysine']:.2f} %"},
                {"โภชนาการ": "เมทไธโอนีน (% Methionine)", "เป้าหมาย": f"{edit_me:.2f} %", "ได้จริงในสูตร": f"{act_nut['methionine']:.2f} %"},
            ]
            st.dataframe(pd.DataFrame(comparison_table), use_container_width=True, hide_index=True)
            
            categories = ['Protein', 'Calcium', 'Phos', 'Lysine', 'Methionine']
            target_vals = [edit_p, edit_c, edit_ph, edit_ly, edit_me]
            actual_vals = [act_nut['protein'], act_nut['calcium'], act_nut['phos'], act_nut['lysine'], act_nut['methionine']]
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=categories, y=target_vals, name='เป้าหมาย (Target)', marker_color='#ffb703'))
            fig.add_trace(go.Bar(x=categories, y=actual_vals, name='ได้จริง (Actual)', marker_color='#38bdf8'))
            fig.update_layout(title="📈 กราฟเปรียบเทียบสัดส่วนโภชนาการ (%)", barmode='group', template="plotly_dark", height=250, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
            ec1, ec2 = st.columns(2)
            with ec1: 
                st.metric("💰 ต้นทุนค่าอาหารเฉลี่ยสูตรนี้", f"{net_cost:.2f} บาท/กก.")
            with ec2:
                feed_consumed_kg = float(current_breed_data["default_feed"]) / 1000.0
                feed_cost_day = feed_consumed_kg * net_cost
                revenue_day = (laying_rate / 100.0) * egg_price
                iofc_profit = revenue_day - feed_cost_day
                
                breed_display_name = selected_b_name.split()[-2] if len(selected_b_name.split()) > 1 else selected_b_name
                st.metric(f"📈 กำไรเหนือค่าอาหาร (IOFC) ของ [{breed_display_name}]", f"{iofc_profit:.2f} บาท/ตัว/วัน")
            
            st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
            save_name_input = st.text_input("ตั้งชื่อเล่นของสูตรเพื่อกดจัดเก็บเข้าคลังประวัติ:", value=f"สูตร {breed_display_name} {net_cost:.1f} บาท")
            if st.button("📥 ยืนยันบันทึกสูตรอาหารนี้ลงคลัง"):
                st.session_state.saved_formulas.append({
                    "date": str(datetime.date.today()), "name": save_name_input, "cost": round(net_cost, 2), "breed": selected_b_name, "stage": selected_stage_label,
                    "protein": round(act_nut["protein"], 2), "me": round(act_nut["me"], 0), "calcium": round(act_nut["calcium"], 2), "weights": st.session_state.current_weights.copy()
                })
                st.success("บันทึกข้อมูลสูตรอาหารเรียบร้อยแล้ว!")
            st.markdown("</div>", unsafe_allow_html=True)

    with page_tabs[1]:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("<h2>☀️ บันทึกตัวชี้วัดโรงเรือน & AI วิเคราะห์ประสิทธิภาพการผลิตเชิงลึก</h2>", unsafe_allow_html=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        
        log_col1, log_col2 = st.columns(2)
        with log_col1:
            st.markdown("#### 📝 ป้อนข้อมูลกิจกรรมฟาร์มวันนี้")
            log_date = st.date_input("เลือกวันที่จดบันทึก:", datetime.date.today())
            bird_count = st.number_input("จำนวนไก่ไข่ทั้งหมดที่มีในโรงเรือนปัจจุบัน (ตัว):", min_value=1, value=5000, step=100)
            env_temp = st.slider("🌡️ อุณหภูมิสูงสุดภายในโรงเรือนวันนี้ (°C):", 15.0, 45.0, 28.0, step=0.5)
            # 🔄 เพิ่มช่องกรอกปริมาณอาหารที่กินจริงเพื่อคำนวณประสิทธิภาพ
            actual_feed_given_kg = st.number_input("🍽️ ปริมาณอาหารสัตว์ที่ใช้เลี้ยงรวมวันนี้ (กิโลกรัม):", min_value=10.0, value=float(bird_count * current_breed_data["default_feed"] / 1000.0), step=10.0)
            
        with log_col2:
            st.markdown("#### 🥚 บันทึกผลผลิตไข่เเละอัตราสูญเสีย")
            collected_eggs = st.number_input("จำนวนฟองไข่ที่เก็บได้จริงวันนี้ (ฟอง):", min_value=0, value=4200)
            dead_birds = st.number_input("จำนวนไก่ตาย/คัดทิ้งวันนี้ (ตัว):", min_value=0, value=2)
            # 🔄 เพิ่มน้ำหนักไข่เฉลี่ยเพื่อนำไปคำนวณค่า FCR ตัวจริง
            avg_egg_weight_g = st.number_input("⚖️ น้ำหนักไข่เฉลี่ยวันนี้ (กรัม/ฟอง) [มาตรฐาน: 60-65g]:", min_value=30.0, max_value=80.0, value=62.0, step=0.5)
            
            # คำนวณปริมาณน้ำตามอุณหภูมิโรงเรือน
            if env_temp <= 20.0:
                water_per_bird_ml = 160.0
            elif env_temp <= 28.0:
                water_per_bird_ml = 200.0 + (env_temp - 20.0) * 7.5
            elif env_temp <= 32.0:
                water_per_bird_ml = 260.0 + (env_temp - 28.0) * 15.0 
            else:
                water_per_bird_ml = 320.0 + (env_temp - 32.0) * 25.0
                
            total_water_needed_liters = (water_per_bird_ml * bird_count) / 1000.0
            
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        st.markdown("### 📊 ผลวิเคราะห์สภาวะฟาร์มและความคุ้มค่าทางเศรษฐกิจ (KPI)")
        
        # 📈 2. คำนวณอัตรา Hen-Day Production และ FCR
        henday_pct = (collected_eggs / bird_count) * 100.0 if bird_count > 0 else 0.0
        total_egg_mass_kg = (collected_eggs * avg_egg_weight_g) / 1000.0
        fcr_ratio = actual_feed_given_kg / total_egg_mass_kg if total_egg_mass_kg > 0 else 0.0
        
        kp1, kp2, kp3 = st.columns(3)
        with kp1:
            st.metric("🥚 อัตราการให้ไข่ (Hen-Day Production)", f"{henday_pct:.1f} %", delta=f"{henday_pct - 85.0:.1f} % vs มาตรฐาน")
        with kp2:
            # ค่า FCR ยิ่งต่ำยิ่งดี (เช่น 2.0-2.2 คือดีเยี่ยม กินอาหารน้อยแต่ไข่หนัก)
            fcr_delta = "ดีเยี่ยม" if fcr_ratio <= 2.2 else "ควรปรับปรุงสูตรอาหาร"
            st.metric("🥣 อัตราแลกไข่ (FCR ต่อ นน.ไข่ 1 กก.)", f"{fcr_ratio:.2f}", delta=fcr_delta, delta_color="inverse" if fcr_ratio > 2.2 else "normal")
        with kp3:
            st.metric("💧 ปริมาณน้ำดื่มรวมที่ฝูงต้องได้รับวันนี้", f"{total_water_needed_liters:,.1f} ลิตร")
            
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        w_res1, w_res2 = st.columns(2)
        with w_res1:
            if env_temp >= 32.0:
                st.markdown(f"<div style='background-color:#991b1b; padding:15px; border-radius:10px; text-align:center;'><strong>⚠️ อากาศร้อนวิกฤต ({env_temp}°C)</strong><br>เสี่ยงเกิด Heat Stress สูงมาก ให้เสริมวิตามินละลายน้ำและห้ามขาดน้ำเด็ดขาด!</div>", unsafe_allow_html=True)
            elif env_temp >= 28.0:
                st.markdown(f"<div style='background-color:#c2410c; padding:15px; border-radius:10px; text-align:center;'><strong>☀️ อากาศร้อนปานกลาง ({env_temp}°C)</strong><br>เปิดระบบพ่นหมอกหรือเร่งพัดลมระบายอากาศในเล้าเพื่อช่วยลดอุณหภูมิ</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='background-color:#065f46; padding:15px; border-radius:10px; text-align:center;'><strong>🟢 อุณหภูมิสบายต่อตัวไก่ ({env_temp}°C)</strong><br>สภาวะแวดล้อมดีเยี่ยม เอื้อต่อการกินอาหารและสร้างเปลือกไข่</div>", unsafe_allow_html=True)
        with w_res2:
            feed_per_bird = (actual_feed_given_kg * 1000) / bird_count
            st.markdown(f"<div style='background-color:#1e293b; padding:15px; border-radius:10px; border:1px solid #334155;'>💡 <b>สรุปการกินอาหาร:</b> เฉลี่ยกินตัวละ <b>{feed_per_bird:.1f} กรัม/วัน</b><br>ค่าน้ำหนักไข่รวมทั้งหมดที่ผลิตได้วันนี้: <b>{total_egg_mass_kg:.1f} กิโลกรัม</b></div>", unsafe_allow_html=True)
            
        if st.button("💾 บันทึกประจุประจำวันลงฐานข้อมูลฟาร์ม", use_container_width=True):
            st.session_state.daily_logs.append({
                "วันที่": str(log_date), "จำนวนไก่ (ตัว)": bird_count, "อุณหภูมิ (°C)": env_temp,
                "อาหารที่ใช้ (KG)": actual_feed_given_kg, "ไข่ที่ได้ (ฟอง)": collected_eggs, 
                "อัตราไข่ (%)": round(henday_pct, 1), "FCR": round(fcr_ratio, 2), "จำนวนตาย (ตัว)": dead_birds
            })
            st.success("🎉 บันทึกประวัติและดัชนีประสิทธิภาพฟาร์มรายวันเรียบร้อยแล้ว!")
            st.rerun()
            
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        st.markdown("### 📋 ตารางบันทึกประวัติฟาร์มและประสิทธิภาพย้อนหลัง")
        if not st.session_state.daily_logs:
            st.info("💡 ปัจจุบันยังไม่มีประวัติการบันทึกรายวัน ลองกดบันทึกข้อมูลด้านบน")
        else:
            st.dataframe(pd.DataFrame(st.session_state.daily_logs), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with page_tabs[2]:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("<h2>📊 ระบบออกเอกสารจัดเตรียมและสั่งซื้อวัตถุดิบ (Procurement Batch Matrix)</h2>", unsafe_allow_html=True)
        total_tonnage = st.number_input("ระบุปริมาณอาหารสัตว์รวมทั้งหมดที่ต้องการใช้ผสมในรอบนี้ (กิโลกรัม):", min_value=100, value=1000, step=100)
        
        po_buffer = []
        total_po_cost = 0
        total_w = sum(st.session_state.current_weights.values())
        divisor = total_w if total_w > 0 else 1.0
        
        for ing_name, w_pct in st.session_state.current_weights.items():
            actual_pct = (w_pct / divisor) * 100.0
            if actual_pct > 0.01:
                if ing_name in st.session_state.db_ingredients:
                    weight_kg = (actual_pct / 100.0) * total_tonnage
                    cost_item = weight_kg * float(st.session_state.db_ingredients[ing_name]["price"])
                    total_po_cost += cost_item
                    
                    bags = int(weight_kg // 50)
                    rem_kg = weight_kg % 50
                    bag_txt = f"{bags} กระสอบ + {rem_kg:.1f} กิโลกรัม" if bags > 0 else f"{rem_kg:.1f} กิโลกรัม"
                    
                    po_buffer.append({
                        "รายการวัตถุดิบที่ต้องจัดเตรียม": ing_name, "สัดส่วนการผสมจริง (%)": round(actual_pct, 2), 
                        "น้ำหนักสุทธิ (KG)": round(weight_kg, 2), "📦 หน่วยคนงาน (กระสอบละ 50kg)": bag_txt,
                        "ประมาณการราคาทุนแยกชิ้น (บาท)": round(cost_item, 2)
                    })
                    
        if po_buffer:
            df_po = pd.DataFrame(po_buffer)
            st.dataframe(df_po, use_container_width=True, hide_index=True)
            st.metric("💵 งบประมาณจัดซื้อและเตรียมของรวมทั้งสิ้นรอบนี้", f"{total_po_cost:,.2f} บาท")
            
            csv_s = io.StringIO()
            df_po.to_csv(csv_s, index=False, encoding='utf-8-sig')
            st.download_button("📥 ดาวน์โหลดใบจัดเตรียมและสั่งซื้อวัตถุดิบ (Export PO to CSV)", data=csv_s.getvalue(), file_name=f"PO_Order_Batch.csv", mime="text/csv", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with page_tabs[3]:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("<h2>📈 คลังประวัติสูตรอาหารที่เคยบันทึกไว้ (Saved Formula History)</h2>", unsafe_allow_html=True)
        if not st.session_state.saved_formulas:
            st.info("💡 ขณะนี้ยังไม่มีรายการสูตรอาหารในคลังประวัติ สามารถกดเซฟสูตรได้ที่แท็บแรก")
        else:
            df_history = pd.DataFrame(st.session_state.saved_formulas)
            st.dataframe(df_history.drop(columns=["weights"]), use_container_width=True)
            
            st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
            selected_f_name = st.selectbox("🔍 เลือกสูตรอาหารเก่าในอดีตที่ต้องการเปิดดูสูตรส่วนผสมเชิงลึก:", [f["name"] for f in st.session_state.saved_formulas])
            
            target_f = next(f for f in st.session_state.saved_formulas if f["name"] == selected_f_name)
            
            hc1, hc2 = st.columns([6, 4])
            with hc1:
                st.markdown(f"**📝 โครงสร้างสัดส่วนวัตถุดิบอาหารของสูตร: {target_f['name']}**")
            with hc2:
                if st.button("🔄 ดึงสูตรเก่านี้กลับไปใช้และปรับแต่งต่อที่หน้าหลัก", use_container_width=True):
                    st.session_state.current_weights = target_f["weights"].copy()
                    st.success(f"ดึงข้อมูล '{target_f['name']}' ไปติดตั้งเป็นสูตรหน้างานปัจจุบันสำเร็จแล้ว! กรุณากลับไปเช็กที่แท็บ 1")
                    st.rerun()
            
            sub_rows = [{"รายการวัตถุดิบ": k, "สัดส่วนที่ใช้ผสมจริง (%)": v} for k, v in target_f["weights"].items() if v > 0.01]
            st.dataframe(pd.DataFrame(sub_rows).sort_values(by="สัดส่วนที่ใช้ผสมจริง (%)", ascending=False), use_container_width=True, hide_index=True)
            
            if st.button("🗑️ ลบสูตรอาหารนี้ออกจากฐานข้อมูล"):
                st.session_state.saved_formulas = [f for f in st.session_state.saved_formulas if f["name"] != selected_f_name]
                st.success("ลบสูตรออกจากประวัติเรียบร้อยแล้ว")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
