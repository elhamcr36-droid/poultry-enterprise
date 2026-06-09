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

if "user_database" not in st.session_state:
    st.session_state.user_database = {
        "admin": {"password": "222", "name": "ผู้ดูแลระบบ", "surname": "ระดับสูง", "role": "admin", "tel": "089-999-9999", "reg_date": "2026-01-01"},
        "222": {"password": "222", "name": "แอดมินทางลัด", "surname": "ระบบผสม", "role": "admin", "tel": "088-888-8888", "reg_date": "2026-01-02"},
        "user": {"password": "123", "name": "สมชาย", "surname": "ใจดี", "role": "user", "tel": "081-234-5678", "reg_date": "2026-05-10"}
    }

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
    
    # เพิ่มกลไกความยืดหยุ่น (Soft Constraints) เพื่อป้องกันสมการขัดแย้งกันจนแอปเออร์เรอร์
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
# 🔒 4. SECURITY GATEWAY (LOGIN / SIGNUP)
# ==========================================
if not st.session_state.is_authenticated:
    if st.session_state.auth_page_mode == "login":
        st.markdown("<div class='content-card' style='max-width: 550px; margin: 80px auto 0 auto;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #ffb703 !important;'>🔐 เข้าสู่ระบบ Layer Nutrition Studio Pro</h2>", unsafe_allow_html=True)
        st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
        
        email_login = st.text_input("📧 อีเมล หรือ รหัสผ่านทางลัด (แอดมินและยูสเซอร์ป้อน '222' ได้):", key="login_email")
        pass_login = st.text_input("🔑 รหัสผ่านเข้าใช้งาน (ป้อน '222' หรือ '123'):", type="password", key="login_pass")
        
        if st.button("เข้าสู่ระบบ (Log In)", type="primary", use_container_width=True):
            if email_login in st.session_state.user_database and st.session_state.user_database[email_login]["password"] == pass_login:
                user_info = st.session_state.user_database[email_login]
                st.session_state.is_authenticated = True
                st.session_state.user_role = user_info.get("role", "user")
                st.session_state.user_email = f"{user_info['name']} [{user_info['role'].upper()}]"
                st.rerun()
            else:
                st.error("❌ ข้อมูลประจำตัวไม่ถูกต้อง")
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

# ==========================================
# 🎉 5. HEADER CONTROL PANEL
# ==========================================
col_h1, col_h2 = st.columns([8, 2])
with col_h1:
    st.markdown(f"# 🐔 Layer Nutrition Studio Pro <span style='font-size:1.2rem; color:#38bdf8;'>[ลงชื่อเข้าใช้: {st.session_state.user_email}]</span>", unsafe_allow_html=True)
with col_h2:
    if st.button("🔴 ออกจากระบบ", use_container_width=True):
        st.session_state.is_authenticated = False
        st.session_state.current_weights = {}
        st.rerun()
st.markdown("---")

# ==========================================
# 🛠️ 6. MAIN ROUTER & DASHBOARD INTERFACE
# ==========================================
if st.session_state.user_role == "admin":
    # -----------------------------------------------------------------------------------------
    # 🛠️ ADMIN ROUTE: FULL CRUD DATABASE CONTROL
    # -----------------------------------------------------------------------------------------
    st.markdown("<div style='background-color:#1e3a8a; padding:15px; border-radius:10px; margin-bottom:20px;'><h3 style='margin:0; color:#93c5fd !important;'>🛠️ FULL CRUD CONTROL PANEL: หน้าบริหารจัดการฐานข้อมูลระบบฟาร์ม</h3></div>", unsafe_allow_html=True)
    admin_tabs = st.tabs(["🌽 จัดการวัตถุดิบอาหาร", "🐓 จัดการสายพันธุ์ไก่ไข่", "🧬 จัดการเกณฑ์โภชนาการอายุ"])
    
    with admin_tabs[0]:
        st.markdown("<div class='content-card'>### 🌽 เพิ่ม/แก้ไขคลังวัตถุดิบหลัก</div>", unsafe_allow_html=True)
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
                    st.success("บันทึกข้อมูลเรียบร้อย!"); st.rerun()
        with c2:
            st.markdown("#### ❌ ลบวัตถุดิบออกจากระบบ")
            to_del = st.selectbox("เลือกวัตถุดิบที่จะลบ:", list(st.session_state.db_ingredients.keys()))
            if st.button("🗑️ ยืนยันลบวัตถุดิบ"):
                del st.session_state.db_ingredients[to_del]; st.warning("ลบข้อมูลเรียบร้อย!"); st.rerun()

    with admin_tabs[1]:
        st.markdown("<div class='content-card'>### 🐓 จัดการข้อมูลสายพันธุ์ไก่ไข่</div>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(st.session_state.db_breeds), use_container_width=True)
        bc1, bc2 = st.columns(2)
        with bc1:
            b_group = st.selectbox("เลือกกลุ่มหลัก:", [g["group_name"] for g in st.session_state.db_groups])
            b_name = st.text_input("ชื่อสายพันธุ์การค้าใหม่:")
            b_egg = st.text_input("สีเปลือกไข่:")
            b_feed = st.number_input("อัตรากินอาหารมาตรฐาน (กรัม/วัน):", value=115.0)
            if st.button("➕ เพิ่มสายพันธุ์ใหม่"):
                if b_name:
                    st.session_state.db_breeds.append({"group_name": b_group, "breed_name": b_name, "egg_color": b_egg, "default_feed": b_feed})
                    st.success("เพิ่มข้อมูลเรียบร้อย!"); st.rerun()
        with bc2:
            b_del = st.selectbox("เลือกสายพันธุ์ที่จะลบ:", [b["breed_name"] for b in st.session_state.db_breeds])
            if st.button("🗑️ ยืนยันลบสายพันธุ์"):
                st.session_state.db_breeds = [b for b in st.session_state.db_breeds if b["breed_name"] != b_del]
                st.warning("ลบออกแล้ว!"); st.rerun()

    with admin_tabs[2]:
        st.markdown("<div class='content-card'>### 🧬 จัดการเกณฑ์โภชนาการตามช่วงอายุสัตว์</div>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame.from_dict(st.session_state.db_targets, orient='index'), use_container_width=True)
        
    if st.button("🔄 สลับไปใช้โหมดหน้าจอ User"):
        st.session_state.user_role = "user"
        st.rerun()

else:
    # -----------------------------------------------------------------------------------------
    # 👑 USER ROUTE: UNIFIED HYBRID MATRIX INTERFACE (AI-First & Two-Way Live Editing)
    # -----------------------------------------------------------------------------------------
    page_tabs = st.tabs([
        "🏠 หน้าจอคำนวณและผสมสูตรอาหาร (Unified Live Matrix)", 
        "📊 ใบจัดเตรียมและสั่งซื้อวัตถุดิบ (Procurement Batch Sheet)", 
        "📈 คลังประวัติสูตรอาหารส่วนตัว (Personal History Log)"
    ])
    
    with page_tabs[0]:
        # ดึงรายชื่อระยะปลอดภัยของอาหารสัตว์เพื่อเตรียมการป้อนข้อมูล
        stage_options = {s["stage_name"]: s["stage_key"] for s in st.session_state.db_targets.values()}
        
        # กล่องควบคุมด้านบนสุดของแผงหน้าจอ
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        col_top1, col_top2, col_top3 = st.columns(3)
        with col_top1:
            selected_stage_label = st.selectbox("📋 เลือกช่วงระยะการออกไข่ของฝูง:", list(stage_options.keys()))
            base_req = st.session_state.db_targets[stage_options[selected_stage_label]]
        with col_top2:
            egg_price = st.number_input("💰 ราคารับซื้อไข่หน้าฟาร์มปัจจุบัน (บาท/ฟอง):", min_value=1.0, value=4.10)
        with col_top3:
            laying_rate = st.slider("📊 อัตราการให้ไข่เฉลี่ยของฝูงประจำสัปดาห์ (%):", 10, 100, 85)
        st.markdown("</div>", unsafe_allow_html=True)

        # ⚡ 🛑 CRITICAL AUTOMATION: สั่ง AI รันคำนวณสูตรอาหารต้นทุนต่ำสุดให้ก่อนเสมอเป็นค่าเริ่มต้น
        if not st.session_state.current_weights:
            st.session_state.current_weights = run_ai_solver(
                base_req["protein"], base_req["me"], base_req["calcium"], base_req["phos"], base_req["lysine"], base_req["methionine"]
            )

        # -----------------------------------------------------------------------------------------
        # 🔄 UNIFIED HYBRID TWO-WAY INTERFACE (ฝั่งซ้ายปรับวัตถุดิบ / ฝั่งขวาปรับแก้สารอาหารและประมวลผลตามจริง)
        # -----------------------------------------------------------------------------------------
        col_left, col_right = st.columns([1.1, 0.9])
        
        # --- 🎛️ ฝั่งซ้าย: แผงควบคุมและแก้ไขวัตถุดิบด้วยตัวเอง (User Manual Customization Slider) ---
        with col_left:
            st.markdown("<div class='content-card'>", unsafe_allow_html=True)
            st.markdown("### 🥣 1. สัดส่วนและปริมาณวัตถุดิบดิบที่ใช้ (%)")
            st.markdown("<p style='color:#38bdf8;'>สูตรด้านล่างมาจากการคำนวณของ AI คุณสามารถ 'ขยับสไลเดอร์เพิ่มลดด้วยตนเอง' เพื่อแต่งสูตรอาหารได้ทันท่วงที</p>", unsafe_allow_html=True)
            
            temp_weights = {}
            running_total = 0.0
            
            # วนลูปเพื่อแสดงรายการวัตถุดิบและค่าเปอร์เซ็นต์ที่ดึงมาจากถังข้อมูลปัจจุบัน
            for name, d in st.session_state.db_ingredients.items():
                saved_w = float(st.session_state.current_weights.get(name, 0.0))
                saved_w = max(0.0, min(100.0, saved_w))  # ป้องกันปัญหาน้ำหนักหลุดขอบเขตความปลอดภัย
                
                # ตัวสไลเดอร์ที่ผู้ใช้สามารถปรับเลื่อนเพิ่ม/ลบวัตถุดิบได้เองสด ๆ บนหน้าเว็บบอร์ด
                user_val = st.slider(
                    f"🌽 {name} (ราคา {d['price']} บ./กก.)",
                    min_value=0.0, max_value=100.0, value=saved_w, step=0.1, key=f"sld_user_{name}"
                )
                temp_weights[name] = user_val
                running_total += user_val
            
            # ตรวจสอบความสมบูรณ์ของสูตรอาหาร (ต้องรวมได้ 100%)
            if abs(running_total - 100.0) > 0.1:
                st.markdown(f"<div style='background-color:#991b1b; padding:10px; border-radius:8px; font-weight:bold; text-align:center;'>⚠️ สัดส่วนรวมได้: {running_total:.1f}% (กรุณาปรับลดส่วนผสมอื่นทดแทนให้ครบ 100% พอดี)</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='background-color:#065f46; padding:10px; border-radius:8px; font-weight:bold; text-align:center;'>🟢 สัดส่วนรวมครบถ้วนสมบูรณ์: {running_total:.1f}%</div>", unsafe_allow_html=True)
            
            # บันทึกค่าที่ได้จากการเลื่อนสไลเดอร์กลับลงไปใน State ส่วนกลางทันที
            st.session_state.current_weights = temp_weights
            st.markdown("</div>", unsafe_allow_html=True)

        # --- 🧬 ฝั่งขวา: แสดงระดับสารอาหารจริงที่ได้รับสด ๆ & ช่องกรอกปรับแต่งโภชนาการเป้าหมาย ---
        with col_right:
            st.markdown("<div class='content-card'>", unsafe_allow_html=True)
            st.markdown("### 🧪 2. ตารางระดับโภชนาการเเละเป้าหมายควบคุม")
            st.markdown("หากต้องการแก้ไขคุณค่าสารอาหารเป้าหมาย ให้ระบุตัวเลขใหม่ด้านล่างแล้วกดปุ่มสั่งให้ AI จัดวัตถุดิบขยับตาม")
            
            # คำนวณสารอาหารและราคาจริง ณ วินาทีปัจจุบันที่ได้จากการเลื่อนแถบสไลเดอร์ฝั่งซ้ายมือ
            net_cost = 0.0
            act_nut = {"protein": 0.0, "me": 0.0, "calcium": 0.0, "phos": 0.0, "lysine": 0.0, "methionine": 0.0, "fiber": 0.0}
            total_w = sum(st.session_state.current_weights.values())
            divisor = total_w if total_w > 0 else 1.0
            
            for name, w in st.session_state.current_weights.items():
                ratio = w / divisor
                net_cost += ratio * float(st.session_state.db_ingredients[name]["price"])
                for k in act_nut.keys():
                    act_nut[k] += ratio * float(st.session_state.db_ingredients[name].get(k, 0.0))
            
            # บล็อกอินพุตป้อนแก้ไขเพื่อส่งเป้าหมายใหม่ให้ AI ประมวลผลย้อนกลับ
            col_cell1, col_cell2 = st.columns([1, 1])
            with col_cell1:
                edit_p = st.number_input("🎯 แก้ไขเป้าโปรตีนดิบ (% CP):", min_value=10.0, value=float(base_req["protein"]), step=0.1)
                edit_m = st.number_input("🎯 แก้ไขเป้าพลังงาน (ME kcal/kg):", min_value=2000.0, value=float(base_req["me"]), step=25.0)
                edit_c = st.number_input("🎯 แก้ไขเป้าแคลเซียม (% Ca):", min_value=1.0, value=float(base_req["calcium"]), step=0.05)
            with col_cell2:
                edit_ph = st.number_input("🎯 แก้ไขเป้าฟอสฟอรัส (% P):", min_value=0.1, value=float(base_req["phos"]), step=0.02)
                edit_ly = st.number_input("🎯 แก้ไขเป้าไลซีน (% Lys):", min_value=0.2, value=float(base_req["lysine"]), step=0.01)
                edit_me = st.number_input("🎯 แก้ไขเป้าเมทไธโอนีน (% Met):", min_value=0.1, value=float(base_req["methionine"]), step=0.01)
            
            # ปุ่มกลไกสั่งการให้ AI จัดเรียงวัตถุดิบด้านซ้ายขยับสัดส่วนเปอร์เซ็นต์ตาม
            if st.button("⚡ สั่ง AI จัดการวัตถุดิบให้ขยับสัดส่วนตามเป้าสารอาหารนี้", type="primary", use_container_width=True):
                with st.spinner("AI กำลังจัดทัพสัดส่วนวัตถุดิบชิ้นใหม่..."):
                    st.session_state.current_weights = run_ai_solver(edit_p, edit_m, edit_c, edit_ph, edit_ly, edit_me)
                    st.success("🤖 AI ทำการจัดทัพสัดส่วนวัตถุดิบใหม่ให้สอดคล้องกันเรียบร้อยแล้ว!")
                    st.rerun()
            
            st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
            st.markdown("##### 📊 ตารางระดับสารอาหารที่ฝูงสัตว์ได้รับจริง ณ ปัจจุบัน (ขยับสดเรียลไทม์)")
            
            comparison_table = [
                {"รายการโภชนาการหลัก": "โปรตีนดิบรวมในสูตร (Crude Protein %)", "ระดับสารอาหารที่ได้จริง": f"{act_nut['protein']:.2f} %"},
                {"รายการโภชนาการหลัก": "พลังงานใช้ประโยชน์ได้ (ME kcal/kg)", "ระดับสารอาหารที่ได้จริง": f"{act_nut['me']:.0f} kcal/kg"},
                {"รายการโภชนาการหลัก": "แคลเซียมหนุนความหนาเปลือกไข่ (% Ca)", "ระดับสารอาหารที่ได้จริง": f"{act_nut['calcium']:.2f} %"},
                {"รายการโภชนาการหลัก": "ฟอสฟอรัสที่เป็นประโยชน์ (% Avail. P)", "ระดับสารอาหารที่ได้จริง": f"{act_nut['phos']:.2f} %"},
                {"รายการโภชนาการหลัก": "กรดอะมิโนจำเป็น ไลซีน (% Lysine)", "ระดับสารอาหารที่ได้จริง": f"{act_nut['lysine']:.2f} %"},
                {"รายการโภชนาการหลัก": "กรดอะมิโนจำเป็น เมทไธโอนีน (% Methionine)", "ระดับสารอาหารที่ได้จริง": f"{act_nut['methionine']:.2f} %"},
                {"รายการโภชนาการหลัก": "กากใยอาหารรวมในกระเพาะ (% Fiber)", "ระดับสารอาหารที่ได้จริง": f"{act_nut['fiber']:.2f} %"}
            ]
            st.dataframe(pd.DataFrame(comparison_table), use_container_width=True, hide_index=True)
            
            # คำนวณดัชนีชี้วัดเศรษฐศาสตร์ฟาร์มแบบนาทีต่อนาที
            st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
            st.markdown("##### 💵 ตัวชี้วัดประสิทธิภาพทางต้นทุนและกำไรฟาร์ม")
            ec1, ec2 = st.columns(2)
            with ec1: 
                st.metric("💰 ต้นทุนค่าอาหารเฉลี่ย", f"{net_cost:.2f} บาท/กก.")
            with ec2:
                feed_consumed_kg = 114.0 / 1000.0
                feed_cost_day = feed_consumed_kg * net_cost
                revenue_day = (laying_rate / 100.0) * egg_price
                iofc_profit = revenue_day - feed_cost_day
                st.metric("📈 รายได้เหนือต้นทุนค่าอาหาร (IOFC)", f"{iofc_profit:.2f} บาท/ตัว/วัน")
            
            st.markdown("##### 💾 จัดเก็บสูตรอาหารปัจจุบันลงฐานข้อมูลคลังส่วนตัว")
            save_name_input = st.text_input("ระบุชื่อเรียกของสูตรอาหารนี้เพื่อความจำจำง่าย:", value=f"สูตรปรับปรุง {net_cost:.1f} บาท")
            if st.button("📥 ยืนยันบันทึกสูตรอาหารลงประวัติ"):
                st.session_state.saved_formulas.append({
                    "date": str(datetime.date.today()), "name": save_name_input, "cost": round(net_cost, 2), "breed": "Unified Matrix Model", "stage": "สูตรปรับแต่งไฮบริด",
                    "protein": round(act_nut["protein"], 2), "me": round(act_nut["me"], 0), "calcium": round(act_nut["calcium"], 2), "weights": st.session_state.current_weights.copy()
                })
                st.success("บันทึกข้อมูลสูตรอาหารลงระบบเรียบร้อยแล้ว!")
                
            st.markdown("</div>", unsafe_allow_html=True)

    with page_tabs[1]:
        # -----------------------------------------------------------------------------------------
        # 📊 PROCUREMENT MODULE: คำนวณยอดจัดซื้อสินค้าและน้ำหนักจัดเตรียมใบผสมกระสอบ
        # -----------------------------------------------------------------------------------------
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("## 📊 ระบบออกเอกสารจัดเตรียมและคำนวณสัดส่วนสั่งซื้อวัตถุดิบ (Procurement Batch Matrix)")
        total_tonnage = st.number_input("ระบุจำนวนปริมาณอาหารสัตว์รวมทั้งหมดที่ต้องการใช้ผสมในรอบงวดนี้ (หน่วย: กิโลกรัม):", min_value=100, value=1000, step=100)
        
        po_buffer = []
        total_po_cost = 0
        total_w = sum(st.session_state.current_weights.values())
        divisor = total_w if total_w > 0 else 1.0
        
        for ing_name, w_pct in st.session_state.current_weights.items():
            actual_pct = (w_pct / divisor) * 100.0
            if actual_pct > 0.01:
                weight_kg = (actual_pct / 100.0) * total_tonnage
                cost_item = weight_kg * float(st.session_state.db_ingredients[ing_name]["price"])
                total_po_cost += cost_item
                po_buffer.append({
                    "รายการคลังวัตถุดิบที่ต้องสั่งซื้อ": ing_name, 
                    "สัดส่วนการผสมจริงในสูตร (%)": round(actual_pct, 2), 
                    "น้ำหนักสุทธิที่ต้องใช้ชั่งตวง (KG)": round(weight_kg, 2), 
                    "ประมาณการยอดงบประมาณจัดซื้อ (บาท)": round(cost_item, 2)
                })
                
        if po_buffer:
            df_po = pd.DataFrame(po_buffer)
            st.dataframe(df_po, use_container_width=True, hide_index=True)
            st.metric("💵 งบประมาณจัดซื้อรวมทั้งหมดประจำงวดผสมอาหารรอบนี้", f"{total_po_cost:,.2f} บาท")
            
            # ฟังก์ชันส่งออกไฟล์ตารางออกมาในรูปแบบไฟล์ Excel/CSV เพื่อใช้ทำใบสั่งของภายนอกฟาร์มได้ทันที
            csv_s = io.StringIO()
            df_po.to_csv(csv_s, index=False, encoding='utf-8-sig')
            st.download_button("📥 ดาวน์โหลดเอกสารใบจัดเตรียมและสั่งซื้อวัตถุดิบ (Export PO to CSV File)", data=csv_s.getvalue(), file_name=f"PO_Order_Batch_Report.csv", mime="text/csv", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with page_tabs[2]:
        # -----------------------------------------------------------------------------------------
        # 📈 HISTORY STORAGE MODULE: คลังประวัติสูตรอาหารอดีตเพื่อใช้รีวิวย้อนหลัง
        # -----------------------------------------------------------------------------------------
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("## 📈 คลังฐานข้อมูลประวัติสูตรอาหารที่เคยบันทึกไว้ (Saved Formula History Log)")
        if not st.session_state.saved_formulas:
            st.info("💡 ปัจจุบันฟาร์มของคุณยังไม่มีประวัติการจัดเก็บสูตรอาหารใด ๆ สามารถทำรายการบันทึกได้จากเมนูแท็บแรกครับ")
        else:
            df_history = pd.DataFrame(st.session_state.saved_formulas)
            st.markdown("### 📑 ประวัติภาพรวมของสูตรอาหารที่บันทึกสำเร็จ")
            st.dataframe(df_history.drop(columns=["weights"]), use_container_width=True)
            
            st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)
            st.markdown("### 🔍 ดึงข้อมูลสัดส่วนวัตถุดิบเก่าขึ้นมาเปรียบเทียบดูแบบลึก")
            selected_f_name = st.selectbox("เลือกสูตรอาหารในอดีตที่ต้องการเปิดดูสูตรลับ:", [f["name"] for f in st.session_state.saved_formulas])
            
            target_f = next(f for f in st.session_state.saved_formulas if f["name"] == selected_f_name)
            st.markdown(f"**📝 รายละเอียดชื่อสูตรอาหาร:** {target_f['name']} | **💰 โครงสร้างต้นทุนเฉลี่ย ณ วันบันทึก:** {target_f['cost']} บาท/กก.")
            
            sub_rows = [{"รายการวัตถุดิบ": k, "สัดส่วนเปอร์เซ็นต์ที่ใช้ (%)": v} for k, v in target_f["weights"].items() if v > 0.01]
            st.dataframe(pd.DataFrame(sub_rows).sort_values(by="สัดส่วนเปอร์เซ็นต์ที่ใช้ (%)", ascending=False), use_container_width=True, hide_index=True)
            
            if st.button("🗑️ ลบสูตรอาหารนี้ออกจากคลังบันทึก"):
                st.session_state.saved_formulas = [f for f in st.session_state.saved_formulas if f["name"] != selected_f_name]
                st.success("ทำการลบสูตรอาหารออกจากประวัติเรียบร้อยแล้ว")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
