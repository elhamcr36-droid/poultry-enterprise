import streamlit as st
import pandas as pd
import pulp
import plotly.graph_objects as go
import datetime
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==========================================
# 🔱 1. APP CONFIGURATION & ENTERPRISE THEME
# ==========================================
st.set_page_config(
    page_title="ระบบบริหารจัดการฟาร์มและโภชนาการไก่ไข่ระดับองค์กร Layer Pro Studio", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS เพื่อควบคุม UI ให้เป็น Dark Theme หรูหรา สแกนง่าย และซ่อนปุ่มที่ไม่จำเป็น
st.markdown(
    """
    <style>
    [data-testid="collapsedControl"] { display: none; }
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.90), rgba(0, 0, 0, 0.90)), 
                          url("https://images.unsplash.com/photo-1548550023-2bdb3c5beed7?q=80&w=1920");
        background-size: cover; background-position: center;
        background-repeat: no-repeat; background-attachment: fixed;
    }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, [data-testid="stHeader"] {
        color: #ffffff !important;
        text-shadow: 2px 2px 5px rgba(0, 0, 0, 0.95) !important;
    }
    div[data-testid="stSelectbox"] > label {
        font-size: 1.1rem !important;
        font-weight: 800 !important;
        color: #ffb703 !important;
        margin-bottom: 4px !important;
    }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] {
        font-size: 1.05rem !important; 
        font-weight: bold !important;
        background-color: rgba(26, 26, 26, 0.9) !important;
        border: 2px solid #ffb703 !important; 
        color: white !important;
    }
    .divider-line {
        border-top: 1px solid rgba(255, 255, 255, 0.18);
        margin: 20px 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(255, 255, 255, 0.12) !important;
        padding: 8px; border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-weight: bold !important; font-size:1.05rem !important; }
    .content-card {
        background-color: rgba(0, 0, 0, 0.93) !important; padding: 25px;
        border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.15);
        margin-bottom: 20px;
    }
    div[data-testid="stMetricValue"] { font-size: 2.2rem !important; color: #ffb703 !important; }
    [data-testid="stDataFrame"] { background-color: rgba(255,255,255,0.95) !important; border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================================
# 🔐 2. GLOBAL STATE INITIALIZATION
# ==========================================
if "is_authenticated" not in st.session_state: st.session_state.is_authenticated = False
if "user_role" not in st.session_state: st.session_state.user_role = "user"  
if "user_email" not in st.session_state: st.session_state.user_email = ""
if "saved_formulas" not in st.session_state: st.session_state.saved_formulas = []  
if "audit_logs" not in st.session_state:
    st.session_state.audit_logs = [{"เวลา": "2026-06-09 08:00", "ผู้ใช้": "System", "กิจกรรม": "เปิดระบบรักษาความปลอดภัยเครือข่ายฟาร์มขั้นสูง"}]

# เกณฑ์ความปลอดภัยวิกฤตหลังบ้าน (Admin Configuration)
if "threshold_drop_rate" not in st.session_state: st.session_state.threshold_drop_rate = 3.0
if "threshold_mortality_rate" not in st.session_state: st.session_state.threshold_mortality_rate = 0.1
if "threshold_broken_egg" not in st.session_state: st.session_state.threshold_broken_egg = 2.0

# ฐานข้อมูลผู้ใช้จำลองของระบบฟาร์ม
if "user_database" not in st.session_state:
    st.session_state.user_database = {
        "admin": {"password": "222", "name": "ผู้จัดการฟาร์ม/เจ้าของกิจการ", "role": "admin"},
        "user": {"password": "123", "name": "สัตวบาลประจำกลุ่มเทคนิค", "role": "user"}
    }

# ข้อมูลกลุ่มและสายพันธุ์ไก่ไข่ (โครงสร้างเดิม)
if "db_groups" not in st.session_state:
    st.session_state.db_groups = [
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)"},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีขาว (Commercial White Layers)"}
    ]

if "db_breeds" not in st.session_state:
    st.session_state.db_breeds = [
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "breed_name": "สายพันธุ์ ไอซ่า บราวน์ (Isa Brown)", "std_curve": 91.0},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "breed_name": "สายพันธุ์ โลห์แมน บราวน์ (Lohmann Brown)", "std_curve": 92.5},
        {"group_name": "กลุ่มไก่ไข่เปลือกสีขาว (Commercial White Layers)", "breed_name": "สายพันธุ์ โลห์แมน แอลเอสแอล (Lohmann LSL White)", "std_curve": 93.0}
    ]

# ข้อมูลวัตถุดิบ พร้อมราคา เปอร์เซ็นต์โภชนาการ และระดับคลังสต็อก (กก.)
if "db_ingredients" not in st.session_state:
    st.session_state.db_ingredients = {
        "ข้าวโพดบดเม็ด (Ground Corn)": {"name": "ข้าวโพดบดเม็ด (Ground Corn)", "price": 13.5, "protein": 8.5, "me": 3300.0, "calcium": 0.02, "phos": 0.25, "lysine": 0.24, "methionine": 0.18, "fiber": 2.2, "min_limit": 0.0, "max_limit": 70.0, "stock_kg": 5000.0},
        "กากถั่วเหลือง 46% (Soybean Meal 46%)": {"name": "กากถั่วเหลือง 46% (Soybean Meal 46%)", "price": 19.5, "protein": 46.0, "me": 2440.0, "calcium": 0.25, "phos": 0.62, "lysine": 2.85, "methionine": 0.65, "fiber": 3.5, "min_limit": 0.0, "max_limit": 50.0, "stock_kg": 3500.0},
        "ปลาป่นเกรด A 60% (Fish Meal 60%)": {"name": "ปลาป่นเกรด A 60% (Fish Meal 60%)", "price": 35.0, "protein": 60.0, "me": 2850.0, "calcium": 5.00, "phos": 3.00, "lysine": 4.50, "methionine": 1.80, "fiber": 1.0, "min_limit": 0.0, "max_limit": 12.0, "stock_kg": 800.0},
        "หินฝุ่นเม็ดหยาb (Coarse Limestone)": {"name": "หินฝุ่นเม็ดหยาb (Coarse Limestone)", "price": 2.5, "protein": 0.0, "me": 0.0, "calcium": 38.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "fiber": 0.0, "min_limit": 0.0, "max_limit": 15.0, "stock_kg": 2000.0},
        "ไดแคลเซียมฟอสเฟต (DCP 18%)": {"name": "ไดแคลเซียมฟอสเฟต (DCP 18%)", "price": 28.0, "protein": 0.0, "me": 0.0, "calcium": 21.00, "phos": 18.00, "lysine": 0.00, "methionine": 0.00, "fiber": 0.0, "min_limit": 0.0, "max_limit": 4.0, "stock_kg": 400.0},
    }

# สเปกสารอาหารควบคุมตามระยะการเลี้ยง (โจทย์เดิมแบบละเอียด)
if "db_targets" not in st.session_state:
    st.session_state.db_targets = {
        "layer_phase_1": {"stage_key": "layer_phase_1", "stage_name": "ระยะไข่พีค ช่วงที่ 1 (อายุ 19-45 สัปดาห์)", "protein": 17.5, "me": 2750.0, "calcium": 4.10, "phos": 0.42, "lysine": 0.88, "methionine": 0.42, "fiber_max": 4.5},
        "layer_phase_2": {"stage_key": "layer_phase_2", "stage_name": "ระยะไข่ ช่วงที่ 2 (อายุ 46-65 สัปดาห์)", "protein": 16.5, "me": 2725.0, "calcium": 4.30, "phos": 0.38, "lysine": 0.82, "methionine": 0.39, "fiber_max": 4.5},
        "layer_phase_3": {"stage_key": "layer_phase_3", "stage_name": "ระยะท้ายก่อนปลด (อายุ >65 สัปดาห์)", "protein": 15.5, "me": 2700.0, "calcium": 4.55, "phos": 0.34, "lysine": 0.76, "methionine": 0.36, "fiber_max": 5.0},
    }

# ข้อมูลบันทึกผลผลิตประจำเล้า (สมุดบันทึกเดิม)
if "farm_production_logs" not in st.session_state:
    st.session_state.farm_production_logs = [
        {"วันที่": "2026-06-07", "โรงเรือน": "House A", "จำนวนไก่ต้นวัน": 5000, "ไข่ดี(ฟอง)": 4450, "ไข่เสีย/แตก(ฟอง)": 45, "น้ำหนักไข่รวม(กก.)": 282.0, "ตาย(ตัว)": 1, "อาหาร(กก.)": 570.0, "น้ำ(ลิตร)": 1140.0, "อุณหภูมิ(°C)": 28.2, "หมายเหตุ": "ปกติ"},
        {"วันที่": "2026-06-08", "โรงเรือน": "House A", "จำนวนไก่ต้นวัน": 4999, "ไข่ดี(ฟอง)": 4310, "ไข่เสีย/แตก(ฟอง)": 130, "น้ำหนักไข่รวม(กก.)": 275.5, "ตาย(ตัว)": 3, "อาหาร(กก.)": 575.0, "น้ำ(ลิตร)": 1260.0, "อุณหภูมิ(°C)": 29.5, "หมายเหตุ": "อากาศร้อนจัด เปลือกไข่บางลงชัดเจน"},
    ]

if "current_weights" not in st.session_state:
    st.session_state.current_weights = {k: 0.0 for k in st.session_state.db_ingredients.keys()}
if "locked_ingredients" not in st.session_state:
    st.session_state.locked_ingredients = {k: False for k in st.session_state.db_ingredients.keys()}

def add_audit_log(user, text):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    st.session_state.audit_logs.insert(0, {"เวลา": now_str, "ผู้ใช้": user, "กิจกรรม": text})

# ==========================================
# 🧮 3. CORE AI LINEAR PROGRAMMING SOLVER
# ==========================================
def run_ai_solver(req_p, req_m, req_c, req_ph, req_ly, req_me):
    prob = pulp.LpProblem("AI_Advance_Enterprise_Solver", pulp.LpMinimize)
    ing_vars = {}
    
    for name, d in st.session_state.db_ingredients.items():
        if st.session_state.locked_ingredients.get(name, False):
            # บังคับค่าสัดส่วน (Shadow Lock Fixed Constraint)
            current_val = float(st.session_state.current_weights.get(name, 0.0)) / 100.0
            ing_vars[name] = pulp.LpVariable(name, lowBound=current_val, upBound=current_val)
        else:
            ing_vars[name] = pulp.LpVariable(name, lowBound=float(d["min_limit"])/100.0, upBound=float(d["max_limit"])/100.0)
            
    s_p, s_m, s_c = pulp.LpVariable("s_p", lowBound=0), pulp.LpVariable("s_m", lowBound=0), pulp.LpVariable("s_c", lowBound=0)
    prob += pulp.lpSum([ing_vars[name] * float(d["price"]) for name, d in st.session_state.db_ingredients.items()]) + 2000.0 * (s_p + s_m/100.0 + s_c), "Cost"
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
# 🔒 4. GATEWAY SCREEN (SECURITY LOGIN SYSTEM)
# ==========================================
if not st.session_state.is_authenticated:
    st.markdown("<div class='content-card' style='max-width: 520px; margin: 80px auto 0 auto;'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: #ffb703 !important;'>🔒 Layer Studio Enterprise Entrance</h2>", unsafe_allow_html=True)
    st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
    
    login_role = st.selectbox("👥 สิทธิ์ของกลุ่มผู้ใช้งานเพื่อสลับเมนูหน้าบ้าน:", ["สัตวบาลประจำฟาร์ม (User Mode)", "ผู้บริหาร / เจ้าของฟาร์ม (Admin Mode)"])
    email_login = st.text_input("📧 รหัสบัญชีผู้ใช้งาน (Username):")
    show_pass = st.checkbox("👁️ แสดงรหัสผ่านความปลอดภัยประจำศูนย์")
    pass_login = st.text_input("🔑 รหัสเข้าถึงฐานข้อมูล:", type="default" if show_pass else "password")
    
    if st.button("ยืนยันตัวตนเข้าระบบ (Secure Sign In)", type="primary", use_container_width=True):
        if email_login in st.session_state.user_database and st.session_state.user_database[email_login]["password"] == pass_login:
            user_info = st.session_state.user_database[email_login]
            st.session_state.is_authenticated = True
            st.session_state.user_role = user_info["role"]
            st.session_state.user_email = f"{user_info['name']}"
            add_audit_log(email_login, f"ผ่านการรับรองระบบเครือข่ายความปลอดภัย ในฐานะ {user_info['role'].upper()}")
            st.rerun()
        else:
            st.error("❌ ไม่สามารถเข้าสู่ระบบได้: ข้อมูลสิทธิ์ความปลอดภัยไม่ถูกต้อง")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==========================================
# 🎉 5. SYSTEM CONTROL TOP BANNER
# ==========================================
col_h1, col_h2 = st.columns([7.8, 2.2])
with col_h1:
    st.markdown(f"# 🐔 Layer Studio Pro <span style='font-size:1.1rem; color:#38bdf8;'>[เจ้าหน้าที่ปฏิบัติการ: {st.session_state.user_email} | โหมดการทำงานปัจจุบัน: {st.session_state.user_role.upper()}]</span>", unsafe_allow_html=True)
with col_h2:
    cc1, cc2 = st.columns(2)
    with cc1:
        if "ผู้จัดการ" in st.session_state.user_email or st.session_state.user_role == "admin":
            if st.button("🔄 สลับบทบาท", use_container_width=True):
                st.session_state.user_role = "user" if st.session_state.user_role == "admin" else "admin"
                st.rerun()
    with cc2:
        if st.button("🔴 Logout", use_container_width=True):
            st.session_state.is_authenticated = False
            st.session_state.user_role = "user"
            st.rerun()
st.markdown("---")

# ==========================================
# 🛠️ 6. MAIN SYSTEM NAVIGATION
# ==========================================
if st.session_state.user_role == "admin":
    st.markdown("### 🛠️ แผงควบคุมระบบหลังบ้านและการจัดการกลุ่มโครงสร้างฟาร์ม (Admin Core)")
    adm_tabs = st.tabs(["🚨 ตั้งค่าเกณฑ์ควบคุมความปลอดภัย (Thresholds)", "🐔 จัดการโครงสร้างสายพันธุ์ (Breeds & Groups)", "🕵️ รายงานตรวจสอบ Audit Trail"])
    
    with adm_tabs[0]:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("#### กำหนดค่าดัชนีชี้วัดสถานการณ์วิกฤตหน้าฟาร์ม")
        st.session_state.threshold_drop_rate = st.number_input("เกณฑ์อัตราไข่ตกสูงสุดประจำวันที่ยอมรับได้ (%):", min_value=0.5, value=st.session_state.threshold_drop_rate)
        st.session_state.threshold_mortality_rate = st.number_input("เกณฑ์อัตราการตายรายวันสูงสุดที่ยอมรับได้ (%):", min_value=0.01, value=st.session_state.threshold_mortality_rate, step=0.01)
        st.session_state.threshold_broken_egg = st.number_input("เกณฑ์เปอร์เซ็นต์ไข่แตกบุบชำรุดรายวันสูงสุดยอมรับได้ (%):", min_value=0.5, value=st.session_state.threshold_broken_egg)
        st.success("บันทึกเกณฑ์ความปลอดภัยหลักสู่ศูนย์กลางเครือข่ายเสร็จสิ้น")
        st.markdown("</div>", unsafe_allow_html=True)
        
    with adm_tabs[1]:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("#### 📁 ข้อมูลกลุ่มไก่ไข่")
            st.dataframe(pd.DataFrame(st.session_state.db_groups), use_container_width=True)
            new_g = st.text_input("➕ เพิ่มชื่อกลุ่มใหม่:")
            if st.button("บันทึกกลุ่ม"):
                if new_g and not any(d['group_name'] == new_g for d in st.session_state.db_groups):
                    st.session_state.db_groups.append({"group_name": new_g})
                    add_audit_log(st.session_state.user_email, f"เพิ่มกลุ่มไก่ไข่ใหม่: {new_g}")
                    st.rerun()
        with col_g2:
            st.markdown("#### 🧬 ข้อมูลสายพันธุ์ในสังกัด")
            st.dataframe(pd.DataFrame(st.session_state.db_breeds), use_container_width=True)
            sel_g = st.selectbox("เลือกกลุ่มที่ต้องการเพิ่มสายพันธุ์:", [d["group_name"] for d in st.session_state.db_groups])
            new_b = st.text_input("➕ เพิ่มชื่อสายพันธุ์ใหม่:")
            new_c = st.number_input("เส้นกราฟมาตรฐานความดกเป้าหมาย (%):", min_value=50.0, max_value=100.0, value=90.0)
            if st.button("บันทึกสายพันธุ์"):
                if new_b:
                    st.session_state.db_breeds.append({"group_name": sel_g, "breed_name": new_b, "std_curve": new_c})
                    add_audit_log(st.session_state.user_email, f"เพิ่มสายพันธุ์ย่อย: {new_b} ในกลุ่ม {sel_g}")
                    st.rerun()
                    
    with adm_tabs[2]:
        st.markdown("#### บันทึกความปลอดภัยระบบและบันทึกประวัติย้อนหลัง (Audit Logging Data)")
        st.dataframe(pd.DataFrame(st.session_state.audit_logs), use_container_width=True)

else:
    page_tabs = st.tabs([
        "🏠 คำนวณสูตรอาหารและวิเคราะห์เรดาร์ (Formulator Matrix)",
        "📊 บันทึกผลผลิตประจำเล้า & วิเคราะห์วิกฤต (Production KPIs)",
        "📦 ระบบจัดการคลังวัตถุดิบ (Inventory & Stock)",
        "📋 แผนใบสั่งชั่งและพิมพ์จ่ายงาน (Procurement Sheets)",
        "📈 คลังประวัติสูตรอาหารโปรด (Saved Formulas Vault)"
    ])
    
    # -------------------------------------------------------------
    # TAB 1: FORMULATION ENGINE (RADAR CHART & AI CORE)
    # -------------------------------------------------------------
    with page_tabs[0]:
        st.markdown("<div class='content-card'>#### 🧬 เลือกเป้าหมายทางโภชนาการตามเฟสอายุของฝูงไก่ไข่</div>", unsafe_allow_html=True)
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            stage_sel = st.selectbox("🎯 เลือกเฟสอายุการให้ผลผลิตของไก่ไข่:", list(st.session_state.db_targets.keys()), format_func=lambda x: st.session_state.db_targets[x]["stage_name"])
            base_req = st.session_state.db_targets[stage_sel]
        with col_t2:
            # ปุ่มลัดล้างค่าสไลเดอร์หน้าเว็บทั้งหมดเป็นศูนย์
            if st.button("🔄 รีเซ็ตสัดส่วนวัตถุดิบทั้งหมดเป็น 0% เพื่อออกแบบใหม่", use_container_width=True):
                st.session_state.current_weights = {k: 0.0 for k in st.session_state.db_ingredients.keys()}
                st.rerun()
                
        col_left, col_right = st.columns([1.1, 0.9])
        with col_left:
            st.markdown("#### 🥣 ปรับระดับสัดส่วนวัตถุดิบและระบบล็อคสมการ (Shadow Lock)")
            temp_weights = {}
            for name, d in st.session_state.db_ingredients.items():
                saved_w = max(0.0, min(100.0, float(st.session_state.current_weights.get(name, 0.0))))
                l_col1, l_col2 = st.columns([0.22, 0.78])
                with l_col1:
                    st.session_state.locked_ingredients[name] = st.checkbox("🔒 ล็อกสัดส่วน", key=f"lock_{name}", value=st.session_state.locked_ingredients.get(name, False))
                with l_col2:
                    temp_weights[name] = st.slider(f"{name} (ข้อจำกัด: {d['min_limit']}-{d['max_limit']}%)", 0.0, 100.0, saved_w, 0.1, key=f"sld_{name}")
            st.session_state.current_weights = temp_weights

        with col_right:
            st.markdown("#### 🧪 ผลวิเคราะห์สารอาหารสุทธิและการประเมินแจ้งเตือนเกณฑ์วิกฤต")
            net_cost, act_p, act_c, act_f, act_me, act_ph, act_ly, act_meth = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
            divisor = sum(st.session_state.current_weights.values()) if sum(st.session_state.current_weights.values()) > 0 else 1.0
            
            for name, w in st.session_state.current_weights.items():
                r = w / divisor
                net_cost += r * float(st.session_state.db_ingredients[name]["price"])
                act_p += r * float(st.session_state.db_ingredients[name]["protein"])
                act_c += r * float(st.session_state.db_ingredients[name]["calcium"])
                act_f += r * float(st.session_state.db_ingredients[name]["fiber"])
                act_me += r * float(st.session_state.db_ingredients[name]["me"])
                act_ph += r * float(st.session_state.db_ingredients[name]["phos"])
                act_ly += r * float(st.session_state.db_ingredients[name]["lysine"])
                act_meth += r * float(st.session_state.db_ingredients[name]["methionine"])
                
            # กล่องแถบเตือนสีแดงกรณีสารอาหารวิกฤตหลุดต่ำกว่าเกณฑ์ความปลอดภัยของไก่ไข่
            if act_p < base_req["protein"]: 
                st.markdown(f"<div style='background-color:#991b1b; padding:10px; border-radius:8px; margin-bottom:6px; font-weight:bold;'>🚨 โภชนาการวิกฤต: โปรตีนต่ำเกินไป! ได้จริง {act_p:.2f}% (เป้าหมาย {base_req['protein']}%)</div>", unsafe_allow_html=True)
            if act_c < base_req["calcium"]: 
                st.markdown(f"<div style='background-color:#991b1b; padding:10px; border-radius:8px; margin-bottom:6px; font-weight:bold;'>🚨 คุณภาพเปลือกไข่เสี่ยง: แคลเซียมไม่พอ! ได้จริง {act_c:.2f}% (เป้าหมาย {base_req['calcium']}%)</div>", unsafe_allow_html=True)
            if act_f > base_req["fiber_max"]:
                st.markdown(f"<div style='background-color:#c2410c; padding:10px; border-radius:8px; margin-bottom:6px; font-weight:bold;'>⚠️ สารต้านโภชนาการ: ค่าเยื่อใย (Fiber) สูงเกินเป้าหมาย! ได้จริง {act_f:.2f}%</div>", unsafe_allow_html=True)

            st.metric("คำนวณต้นทุนค่าอาหารสุทธิ", f"{net_cost:.2f} บาท / กิโลกรัม")
            
            # กราฟเรดาร์ชาร์ตเปรียบเทียบโภชนาการจริง (Radar Chart)
            categories = ['Protein', 'Energy(ME)', 'Calcium', 'Phos', 'Lysine', 'Methionine']
            req_nodes = [base_req["protein"], base_req["me"], base_req["calcium"], base_req["phos"], base_req["lysine"], base_req["methionine"]]
            act_nodes = [act_p, act_me, act_c, act_ph, act_ly, act_meth]
            
            # ทำการ Normalize สเกลให้ใกล้เคียง 100 เพื่อแสดงรูปทรงที่สวยงามบนเรดาร์
            norm_req = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0]
            norm_act = [(act_nodes[i]/req_nodes[i])*100.0 if req_nodes[i]>0 else 0 for i in range(len(req_nodes))]
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=norm_req, theta=categories, fill='toself', name='Target Spec (100%)', line_color='#38bdf8'))
            fig.add_trace(go.Scatterpolar(r=norm_act, theta=categories, fill='toself', name='Current Nutrition', line_color='#ffb703'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 150])), showlegend=True, margin=dict(t=30, b=30, l=30, r=30), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
            
            col_action1, col_action2 = st.columns(2)
            with col_action1:
                if st.button("⚡ ให้ AI ค้นหาสูตรอาหารต้นทุนต่ำสุด", type="primary", use_container_width=True):
                    st.session_state.current_weights = run_ai_solver(base_req["protein"], base_req["me"], base_req["calcium"], base_req["phos"], base_req["lysine"], base_req["methionine"])
                    add_audit_log(st.session_state.user_email, "สั่งเปิดระบบประมวลผลต้นทุนอาหารสัตว์ขั้นต่ำด้วย AI Linear Solver")
                    st.rerun()
            with col_action2:
                f_name_save = st.text_input("ตั้งชื่อสูตรอาหารสัตว์:", placeholder="เช่น สูตรไข่พีคทองคำ-A1")
                if st.button("💾 บันทึกสูตรนี้เข้าคลัง", use_container_width=True):
                    if f_name_save:
                        st.session_state.saved_formulas.append({
                            "ชื่อสูตร": f_name_save, "เฟสอายุ": base_req["stage_name"], "วันที่บันทึก": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "ราคาทุน (บาท)": round(net_cost, 2), "โปรตีน (%)": round(act_p, 2), "แคลเซียม (%)": round(act_c, 2), "weights": st.session_state.current_weights.copy()
                        })
                        add_audit_log(st.session_state.user_email, f"บันทึกสูตรอาหารใหม่ชื่อ '{f_name_save}'")
                        st.success("บันทึกข้อมูลสำเร็จแล้ว")
                    else:
                        st.error("กรุณาระบุชื่อสูตรก่อนบันทึก")

    # -------------------------------------------------------------
    # TAB 2: PRODUCTION & ANOMALY ANALYSIS (FLOCK HEALTH MONITOR)
    # -------------------------------------------------------------
    with page_tabs[1]:
        st.markdown("### 📊 บันทึกประสิทธิภาพประจำวันและระบบดักจับสถิติตกต่ำวิกฤต")
        
        # ฟอร์มลงบันทึกข้อมูลดิบรายวันเข้าสู่ระบบ
        with st.expander("➕ กรอกสมุดบันทึกรายงานประจำวันหน้าเล้า"):
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                in_date = st.date_input("วันที่บันทึกสถิติ:", datetime.date.today())
                in_house = st.selectbox("เลือกโรงเรือน:", ["House A", "House B", "House C"])
                in_total_birds = st.number_input("จำนวนไก่ไข่คงเหลือต้นวัน (ตัว):", min_value=100, value=5000)
            with col_f2:
                in_good_eggs = st.number_input("จำนวนไข่ดีสมบูรณ์ (ฟอง):", min_value=0, value=4300)
                in_bad_eggs = st.number_input("จำนวนไข่ชำรุด/แตก/บุบ (ฟอง):", min_value=0, value=40)
                in_weight = st.number_input("น้ำหนักไข่รวมทั้งหมด (กิโลกรัม):", min_value=0.0, value=276.0)
            with col_f3:
                in_dead = st.number_input("จำนวนไก่ตายในวัน (ตัว):", min_value=0, value=2)
                in_feed = st.number_input("ปริมาณอาหารที่กินรวม (กิโลกรัม):", min_value=0.0, value=570.0)
                in_temp = st.number_input("อุณหภูมิเฉลี่ยในโรงเรือน (°C):", min_value=15.0, value=28.0)
            in_note = st.text_input("หมายเหตุเพิ่มเติมเกี่ยวกับสุขภาพ:", "ปกติ")
            
            if st.button("💾 บันทึกรายงานเข้าสู่ระบบฐานข้อมูลกลาง"):
                st.session_state.farm_production_logs.append({
                    "วันที่": str(in_date), "โรงเรือน": in_house, "จำนวนไก่ต้นวัน": in_total_birds, "ไข่ดี(ฟอง)": in_good_eggs,
                    "ไข่เสีย/แตก(ฟอง)": in_bad_eggs, "น้ำหนักไข่รวม(กก.)": in_weight, "ตาย(ตัว)": in_dead, "อาหาร(กก.)": in_feed,
                    "น้ำ(ลิตร)": in_feed*2, "อุณหภูมิ(°C)": in_temp, "หมายเหตุ": in_note
                })
                add_audit_log(st.session_state.user_email, f"คีย์ข้อมูลผลผลิตรายวัน โรงเรือน {in_house}")
                st.success("บันทึกข้อมูลเรียบร้อย")
                st.rerun()

        # ประมวลผลและวิเคราะห์วิกฤตคุณภาพไข่+สุขภาพจากข้อมูลล่าสุด
        df_farm = pd.DataFrame(st.session_state.farm_production_logs)
        latest_data = df_farm.iloc[-1]
        
        act_lay_rate = (latest_data["ไข่ดี(ฟอง)"] / latest_data["จำนวนไก่ต้นวัน"]) * 100
        act_mortality = (latest_data["ตาย(ตัว)"] / latest_data["จำนวนไก่ต้นวัน"]) * 100
        total_eggs_collected = latest_data["ไข่ดี(ฟอง)"] + latest_data["ไข่เสีย/แตก(ฟอง)"]
        act_broken_rate = (latest_data["ไข่เสีย/แตก(ฟอง)"] / total_eggs_collected * 100) if total_eggs_collected > 0 else 0
        
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown(f"#### 🔎 ผลการตรวจสอบระบบเฝ้าระวังอัตราไข่ชำรุดเสียหายประจำวันนี้: `{act_broken_rate:.2f}%` (ค่าวิกฤตสูงสุดต้องไม่เกิน {st.session_state.threshold_broken_egg}%)")
        if act_broken_rate > st.session_state.threshold_broken_egg:
            st.markdown(f"<div style='background-color:#991b1b; padding:15px; border-radius:8px; font-weight:bold;'>❌ วิกฤตโครงสร้างเปลือกไข่บางเกินเกณฑ์มาตรฐาน! พบอัตราแตกร้าวสะสมสูง แนะนำให้เพิ่มสัดส่วนวัตถุดิบกลุ่ม 'หินฝุ่นเม็ดหยาบ' หรือ 'ไดแคลเซียมฟอสเฟต' ในหน้าคำนวณหลักทันทีเพื่อเพิ่มระดับ Calcium สุทธิ</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='background-color:#065f46; padding:15px; border-radius:8px; font-weight:bold;'>🟢 ดัชนีคุณภาพความหนาของเปลือกไข่และการจัดการแร่ธาตุโครงสร้างอยู่ในเกณฑ์ดีเยี่ยม</div>", unsafe_allow_html=True)
            
        if act_mortality > st.session_state.threshold_mortality_rate:
            st.markdown(f"<div style='background-color:#991b1b; padding:15px; border-radius:8px; font-weight:bold; margin-top:10px;'>❌ อัตราการตายของฝูงสัตว์วันนี้เกินเกณฑ์ควบคุมความปลอดภัย ({st.session_state.threshold_mortality_rate}%) สัตวบาลโปรดเข้าพื้นที่ตรวจสอบด่วน!</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("#### ตารางสรุปประวัติผลงานย้อนหลังทั้งหมด")
        st.dataframe(df_farm, use_container_width=True)

    # -------------------------------------------------------------
    # TAB 3: INVENTORY & STOCK MANAGEMENT
    # -------------------------------------------------------------
    with page_tabs[2]:
        st.markdown("### 📦 ระบบบริหารคลังสต็อกวัตถุดิบอาหารสัตว์และปรับเปลี่ยนข้อจำกัดราคา")
        
        # ตารางแสดงข้อมูลคลังสินค้าปัจจุบัน
        ing_table_data = []
        for name, d in st.session_state.db_ingredients.items():
            ing_table_data.append({
                "ชื่อวัตถุดิบอาหาร": name, "ราคาทุนปัจจุบัน (บาท/กก.)": d["price"],
                "ข้อจำกัดต่ำสุด (%)": d["min_limit"], "ข้อจำกัดสูงสุด (%)": d["max_limit"],
                "ปริมาณสต็อกปัจจุบันในเล้า (กก.)": d.get("stock_kg", 0.0)
            })
        df_ing = pd.DataFrame(ing_table_data)
        st.dataframe(df_ing, use_container_width=True)
        
        with st.expander("🛠️ แก้ไขราคา ข้อจำกัด หรือเติมยอดสต็อกวัตถุดิบเข้าฟาร์ม"):
            target_ing = st.selectbox("เลือกวัตถุดิบที่ต้องการปรับค่าข้อมูล:", list(st.session_state.db_ingredients.keys()))
            ed = st.session_state.db_ingredients[target_ing]
            
            c_price = st.number_input("ปรับราคาทุนสินค้าใหม่ (บาท/กก.):", value=float(ed["price"]))
            c_min = st.number_input("ปรับขีดจำกัดขั้นต่ำในสมการ AI (%):", value=float(ed["min_limit"]))
            c_max = st.number_input("ปรับขีดจำกัดสูงสุดในสมการ AI (%):", value=float(ed["max_limit"]))
            c_stock = st.number_input("เพิ่มหรือปรับจำนวนสต็อกสินค้าในคลัง (กิโลกรัม):", value=float(ed.get("stock_kg", 0.0)))
            
            if st.button("💾 ยืนยันการอัปเดตข้อมูลวัตถุดิบอาหารสัตว์"):
                st.session_state.db_ingredients[target_ing]["price"] = c_price
                st.session_state.db_ingredients[target_ing]["min_limit"] = c_min
                st.session_state.db_ingredients[target_ing]["max_limit"] = c_max
                st.session_state.db_ingredients[target_ing]["stock_kg"] = c_stock
                add_audit_log(st.session_state.user_email, f"แก้ไขฐานข้อมูลวัตถุดิบ {target_ing}: ราคา={c_price}, คลัง={c_stock}กก.")
                st.success("อัปเดตข้อมูลโครงสร้างวัตถุดิบหลักเสร็จสิ้นเรียบร้อย")
                st.rerun()

    # -------------------------------------------------------------
    # TAB 4: PROCUREMENT & REAL-TIME STOCK BALANCE ENGINE
    # -------------------------------------------------------------
    with page_tabs[3]:
        st.markdown("### 📋 ใบแบ่งงานชั่งผสมอาหารและระบบวิเคราะห์หักคลังสต็อกเรียอลไทม์")
        total_tonnage = st.number_input("ปริมาณรวมของอาหารสัตว์ทั้งหมดที่ต้องการสั่งผสมชั่งจริงรอบนี้ (กิโลกรัม):", min_value=100, value=1000, step=50)
        
        po_buffer = []
        stock_out_triggered = False
        divisor = sum(st.session_state.current_weights.values()) if sum(st.session_state.current_weights.values()) > 0 else 1.0
        
        for name, w_pct in st.session_state.current_weights.items():
            actual_pct = (w_pct / divisor) * 100.0
            if actual_pct > 0:
                needed_kg = (actual_pct / 100.0) * total_tonnage
                current_stock = st.session_state.db_ingredients[name].get("stock_kg", 0.0)
                
                if needed_kg > current_stock:
                    status_text = f"❌ สต็อกไม่พอผสม! (วิกฤตสินค้าขาดแคลนอีก {needed_kg - current_stock:.1f} กก.)"
                    stock_out_triggered = True
                else:
                    status_text = "🟢 ปริมาณสต็อกปลอดภัย พร้อมเบิกจ่ายชั่งผสมหน้างาน"
                    
                po_buffer.append({
                    "วัตถุดิบสารอาหาร": name, "สัดส่วนในสูตร (%)": round(actual_pct, 1),
                    "น้ำหนักที่ต้องใช้ชั่งจริง (KG)": round(needed_kg, 1),
                    "ยอดสินค้าคงเหลือในคลังฟาร์มปัจจุบัน (KG)": round(current_stock, 1), "ผลการประเมินสถานะคลัง": status_text
                })
                
        if po_buffer:
            df_po = pd.DataFrame(po_buffer)
            st.dataframe(df_po, use_container_width=True)
            
            # ฟังก์ชันสร้างและดาวน์โหลดรายงานความปลอดภัยในรูปแบบ PDF
            def generate_pdf_report(dataframe, tonnage):
                buffer = io.BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=letter)
                styles = getSampleStyleSheet()
                
                # Custom Style ป้องกันภาษาไทยเพี้ยนในระบบสากล
                title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor("#1e3a8a"), spaceAfter=12)
                text_style = ParagraphStyle('TextStyle', parent=styles['Normal'], fontSize=11, spaceAfter=8)
                
                elements = []
                elements.append(Paragraph("Layer Studio Pro - Production Worksheet", title_style))
                elements.append(Paragraph(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", text_style))
                elements.append(Paragraph(f"Total Ordered Tonnage: {tonnage:,} KG", text_style))
                elements.append(Spacer(1, 12))
                
                # แปลงข้อมูลตารางให้รองรับโครงสร้างรายงาน PDF
                table_content = [["Ingredient", "Formula %", "Weight (KG)", "Warehouse Status"]]
                for _, row in dataframe.iterrows():
                    table_content.append([
                        str(row["วัตถุดิบสารอาหาร"]), str(row["สัดส่วนในสูตร (%)"]),
                        str(row["น้ำหนักที่ต้องใช้ชั่งจริง (KG)"]), str(row["ผลการประเมินสถานะคลัง"])
                    ])
                
                pdf_table = Table(table_content, colWidths=[180, 70, 90, 160])
                pdf_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0,0), (-1,0), 8),
                    ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#f8fafc")),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
                ]))
                
                elements.append(pdf_table)
                doc.build(elements)
                buffer.seek(0)
                return buffer.getvalue()

            pdf_bytes = generate_pdf_report(df_po, total_tonnage)
            st.download_button("🖨️ ดาวน์โหลดใบงานและคู่มือการชั่งส่งหน้างาน (Download PDF Sheet)", data=pdf_bytes, file_name="Feed_Production_Sheet.pdf", mime="application/pdf", use_container_width=True)

            if stock_out_triggered:
                st.markdown("<div style='background-color:#991b1b; padding:12px; border-radius:8px; font-weight:bold; text-align:center;'>❌ ระบบระงับการสั่งงาน: ไม่สามารถดำเนินการหักสต็อกได้ เนื่องจากสินค้าในคลังไม่เพียงพอ กรุณาเติมคลังหรือปรับสัดส่วนใหม่</div>", unsafe_allow_html=True)
            else:
                if st.button("✅ อนุมัติใบชั่งชุดนี้และดำเนินการหักยอดสต็อกคลังสินค้าทันที", type="primary", use_container_width=True):
                    for item in po_buffer:
                        st.session_state.db_ingredients[item["วัตถุดิบสารอาหาร"]]["stock_kg"] -= item["น้ำหนักที่ต้องใช้ชั่งจริง (KG)"]
                    add_audit_log(st.session_state.user_email, f"สั่งหักยอดสต็อกสินค้าเพื่อผสมสูตรอาหารปริมาณ {total_tonnage} กก. เข้าสู่เล้า")
                    st.success("🎉 หักยอดสต็อกและส่งประวัติบันทึกการเบิกจ่ายเข้าศูนย์ควบคุมหลักแล้ว!")
                    st.rerun()
        else:
            st.info("💡 กรุณากำหนดอัตราส่วนวัตถุดิบในแท็บแรกให้มากกว่า 0% ก่อนเพื่อเปิดระบบพิมพ์ใบชั่งงานผสม")

    # -------------------------------------------------------------
    # TAB 5: HISTORICAL VAULT (FORMULA RETRIEVAL ENGINE)
    # -------------------------------------------------------------
    with page_tabs[4]:
        st.markdown("### 📈 คลังศูนย์รวมประวัติสูตรอาหารโปรด (Saved Formulas Repository)")
        if not st.session_state.saved_formulas:
            st.info("ยังไม่มีบันทึกข้อมูลสูตรอาหารเก่าในฐานข้อมูลระบบฟาร์มประจำฤดูกาลนี้")
        else:
            df_saved_formulas = pd.DataFrame(st.session_state.saved_formulas)
            st.dataframe(df_saved_formulas.drop(columns=["weights"]), use_container_width=True)
            
            st.markdown("#### 🔄 เรียกคืนและโหลดสูตรอาหารเก่ากลับมาใช้งานหลัก")
            select_f_name = st.selectbox("เลือกสูตรอาหารที่ต้องการโหลดกลับเข้าสู่หน้าทำงานโมเดลหลัก:", [f["ชื่อสูตร"] for f in st.session_state.saved_formulas])
            if st.button("ยืนยันการดึงข้อมูลสูตรนี้กลับคืนค่า (Load Active Vault)"):
                for idx, f in enumerate(st.session_state.saved_formulas):
                    if f["ชื่อสูตร"] == select_f_name:
                        st.session_state.current_weights = f["weights"].copy()
                        add_audit_log(st.session_state.user_email, f"เรียกคืนข้อมูลสูตรอาหารโปรดเก่ากลับมาทำงาน: '{select_f_name}'")
                        st.success(f"ดึงข้อมูลสูตร '{select_f_name}' กลับคืนสู่หน้าต่างคำนวณแท็บที่ 1 เรียบร้อยแล้ว")
                        st.rerun()
