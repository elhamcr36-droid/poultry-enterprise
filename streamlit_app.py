import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pulp
from datetime import datetime

# ==========================================
# 🔱 1. ตั้งค่าคอนฟิกแอปพลิเคชันและหน้าจอ (Application Configuration)
# ==========================================
st.set_page_config(
    page_title="Smart Layer Feed - ระบบคำนวณอาหารไก่ไข่อัจฉริยะ", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 มหาเวทย์ CSS ล็อกพื้นหลังไข่ไก่ และปรับการ์ดอ่านง่าย 100% ไม่แคร์ Dark/Light Mode
st.markdown(
    """
    <style>
    /* ใส่พื้นหลังรูปไข่ไก่และเคลือบ Layer มืดป้องกันฟอนต์กลืน */
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.60), rgba(0, 0, 0, 0.60)), 
                          url("https://images.unsplash.com/photo-1506976785307-8732e854ad03?q=80&w=1920");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }
    
    /* บังคับข้อความหลักให้เป็นสีขาวและมีมิติเงา */
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, [data-testid="stHeader"] {
        color: #ffffff !important;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.9) !important;
    }
    
    /* ปรับแต่งปุ่ม Tabs นำทางหลัก */
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(255, 255, 255, 0.12) !important;
        padding: 10px;
        border-radius: 12px;
        backdrop-filter: blur(10px);
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #ffffff !important;
        font-weight: bold !important;
    }
    
    /* กล่องการ์ดโปร่งแสงสำหรับครอบเนื้อหาให้เด่นและอ่านง่าย */
    .content-card {
        background-color: rgba(0, 0, 0, 0.55) !important;
        padding: 25px;
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(5px);
        margin-bottom: 20px;
    }
    
    /* สีของตัวเลขสถิติ (Metric) */
    div[data-testid="stMetricValue"] {
        font-size: 2rem !important;
        color: #22c55e !important;
        font-weight: bold !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.9);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# แถบข้างซ้ายสำหรับระบบ Cloud ระดับองค์กร
st.sidebar.markdown("### ☁️ การเชื่อมต่อคลาวด์ระดับองค์กร")
SUPABASE_URL = st.sidebar.text_input("ลิงก์โปรเจกต์ Supabase", "https://your-project.supabase.co").strip()
SUPABASE_KEY = st.sidebar.text_input("รหัสผ่าน API (Anon Key)", "your-anon-key", type="password").strip()

# ==========================================
# 🧭 ระบบเมนูแท็บนำทางด้านบน
# ==========================================
st.markdown("# 🐔 Smart Layer Feed")
st.markdown("### ระบบคำนวณสูตรอาหารและบริหารจัดการฟาร์มไก่ไข่อัจฉริยะแบบครบวงจร")

page_tabs = st.tabs([
    "🏠 หน้าแรก & ห้องปฏิบัติการสูตรอาหาร", 
    "📈 สถิติผลผลิต & บัญชีฟาร์ม",
    "📦 ระบบหลังบ้าน"
])

# ==========================================
# 📋 2. ฐานข้อมูลคุณค่าทางโภชนาการและสารอาหาร
# ==========================================
STAGE_NUTRITION_TARGETS = {
    "starter": {"name": "ลูกไก่ไข่ 0 - 6 สัปดาห์ (Starter)", "protein": 20.0, "me": 2900.0, "calcium": 1.00, "phos": 0.45, "amino": 0.42, "fiber": 4.0, "fat": 3.5},
    "grower": {"name": "ไก่รุ่นไข่ 6 - 16 สัปดาห์ (Grower)", "protein": 16.0, "me": 2750.0, "calcium": 0.90, "phos": 0.40, "amino": 0.32, "fiber": 4.5, "fat": 3.0},
    "laying": {"name": "ไก่ไข่ระยะให้ผลผลิต 16 สัปดาห์ขึ้นไป (Laying)", "protein": 17.5, "me": 2750.0, "calcium": 4.10, "phos": 0.42, "amino": 0.38, "fiber": 4.0, "fat": 3.5}
}

if "ingredient_data" not in st.session_state:
    st.session_state.ingredient_data = {
        "ข้าวโพดบด": {"price": 13.5, "protein": 8.5, "me": 3300.0, "calcium": 0.02, "phos": 0.25, "amino": 0.18, "moisture": 12.0, "fiber": 2.2, "fat": 3.8, "tox_risk": 3, "min_limit": 20.0, "max_limit": 70.0},
        "รำละเอียด": {"price": 11.0, "protein": 12.0, "me": 2400.0, "calcium": 0.05, "phos": 1.35, "amino": 0.22, "moisture": 10.5, "fiber": 12.0, "fat": 13.0, "tox_risk": 3, "min_limit": 0.0, "max_limit": 30.0},
        "ปลายข้าว": {"price": 14.5, "protein": 8.0, "me": 3360.0, "calcium": 0.04, "phos": 0.10, "amino": 0.15, "moisture": 12.0, "fiber": 1.0, "fat": 1.5, "tox_risk": 1, "min_limit": 0.0, "max_limit": 40.0},
        "มันเส้นบด": {"price": 9.5, "protein": 2.0, "me": 3000.0, "calcium": 0.18, "phos": 0.09, "amino": 0.04, "moisture": 13.0, "fiber": 3.5, "fat": 0.5, "tox_risk": 2, "min_limit": 0.0, "max_limit": 20.0},
        "กากถั่วเหลือง": {"price": 18.5, "protein": 44.0, "me": 2420.0, "calcium": 0.25, "phos": 0.60, "amino": 0.65, "moisture": 11.5, "fiber": 5.5, "fat": 1.5, "tox_risk": 1, "min_limit": 5.0, "max_limit": 40.0},
        "ปลาป่น": {"price": 32.0, "protein": 60.0, "me": 2850.0, "calcium": 5.00, "phos": 3.00, "amino": 0.95, "moisture": 10.0, "fiber": 1.0, "fat": 8.0, "tox_risk": 1, "min_limit": 0.0, "max_limit": 15.0},
        "กากเนื้อปาล์ม": {"price": 8.0, "protein": 15.0, "me": 1650.0, "calcium": 0.30, "phos": 0.60, "amino": 0.25, "moisture": 10.0, "fiber": 16.0, "fat": 7.0, "tox_risk": 2, "min_limit": 0.0, "max_limit": 10.0},
        "กากเบียร์แห้ง": {"price": 10.5, "protein": 26.0, "me": 2100.0, "calcium": 0.30, "phos": 0.50, "amino": 0.40, "moisture": 11.0, "fiber": 15.0, "fat": 6.0, "tox_risk": 2, "min_limit": 0.0, "max_limit": 10.0},
        "กากถั่วลิสง": {"price": 16.0, "protein": 45.0, "me": 2600.0, "calcium": 0.20, "phos": 0.55, "amino": 0.50, "moisture": 10.0, "fiber": 6.0, "fat": 1.8, "tox_risk": 4, "min_limit": 0.0, "max_limit": 10.0},
        "น้ำมันปาล์มดิบ": {"price": 34.0, "protein": 0.0, "me": 8400.0, "calcium": 0.00, "phos": 0.00, "amino": 0.00, "moisture": 0.5, "fiber": 0.0, "fat": 99.0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 4.0},
        "เปลือกหอยบด": {"price": 4.0, "protein": 0.0, "me": 0.0, "calcium": 38.00, "phos": 0.04, "amino": 0.00, "moisture": 0.5, "fiber": 0.0, "fat": 0.0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 12.0},
        "ไดแคลเซียมฟอสเฟต": {"price": 28.0, "protein": 0.0, "me": 0.0, "calcium": 21.00, "phos": 18.00, "amino": 0.00, "moisture": 1.0, "fiber": 0.0, "fat": 0.0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 5.0},
        "เกลือแกง": {"price": 6.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "amino": 0.00, "moisture": 1.0, "fiber": 0.0, "fat": 0.0, "tox_risk": 0, "min_limit": 0.1, "max_limit": 0.4},
        "กรดอะมิโนสังเคราะห์": {"price": 95.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "amino": 99.00, "moisture": 0.2, "fiber": 0.0, "fat": 0.0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 2.0},
        "พรีมิกซ์ไก่ไข่ (วิตามิน)": {"price": 120.0, "protein": 0.0, "me": 0.0, "calcium": 4.00, "phos": 1.00, "amino": 0.00, "moisture": 2.0, "fiber": 0.0, "fat": 0.0, "tox_risk": 0, "min_limit": 0.2, "max_limit": 0.5}
    }

BREED_PROFILES = {
    "1. กลุ่มไฮบริดสีน้ำตาลพาณิชย์ (Commercial Brown Hybrids)": {
        "Isa Brown": {"name": "ไอซ่า บราวน์ (Isa Brown)", "egg_color": "🤎 น้ำตาลเข้ม", "bg_color": "#b45309", "text_color": "#ffffff", "default_feed": 115, "desc": "เบอร์ 1 ในไทย ไข่ดก 300-320 ฟอง/ปี เปลือกหนา ทนความร้อนเมืองไทยได้ดีเยี่ยม"},
        "Hy-Line Brown": {"name": "ไฮไลน์ บราวน์ (Hy-Line Brown)", "egg_color": "🤎 น้ำตาลนวล", "bg_color": "#d97706", "text_color": "#ffffff", "default_feed": 110, "desc": "กินน้อย FCR ดีมาก อัตราผลิตสม่ำเสมอยาวนาน เปลือกแข็งแรงแตกยาก"},
        "Hisex Brown": {"name": "ไฮ-เซ็กส์ บราวน์ (Hisex Brown)", "egg_color": "🤎 น้ำตาลสว่าง", "bg_color": "#c2410c", "text_color": "#ffffff", "default_feed": 113, "desc": "สายพันธุ์อึด ให้ผลผลิตสูงช่วงต้นของการไข่เร็วมาก นิยมมากในฟาร์มระบบปิด"}
    },
    "2. กลุ่มไฮบริดสีขาวพาณิชย์ (Commercial White Hybrids)": {
        "Hy-Line W-36": {"name": "ไฮไลน์ ดับบลิว-36 (Hy-Line W-36)", "egg_color": "🤍 ขาวสะอาด", "bg_color": "#475569", "text_color": "#ffffff", "default_feed": 101, "desc": "กินอาหารน้อยที่สุดในกลุ่มพาณิชย์ น้ำหนักตัวเบา ค่า FCR ต่ำมาก ประหยัดทุน"},
        "Lohmann White": {"name": "โลห์แมน ไวท์ (Lohmann White)", "egg_color": "🤍 ขาวมุก", "bg_color": "#334155", "text_color": "#ffffff", "default_feed": 105, "desc": "ให้ผลผลิตเปอร์เซ็นต์ไข่สูงยาวนาน นิยมในอุตสาหกรรมแปรรูปไข่เหลว"}
    }
}

LIFECYCLE_FEED_BUDGET = {"starter": 1.2, "grower": 2.8, "laying": 48.0}

# ==========================================
# 🛡️ 3. ระบบจัดการและตรวจสอบ State ป้องกัน Bug 
# ==========================================
if "selected_group" not in st.session_state: st.session_state.selected_group = list(BREED_PROFILES.keys())[0]
if "selected_breed_key" not in st.session_state: st.session_state.selected_breed_key = list(BREED_PROFILES[st.session_state.selected_group].keys())[0]
if "current_key" not in st.session_state: st.session_state.current_key = "laying"
if "weather_env" not in st.session_state: st.session_state.weather_env = "🌡️ อากาศปกติ (25-32°C)"
if "chicken_count" not in st.session_state: st.session_state.chicken_count = 1000
if "use_phytase" not in st.session_state: st.session_state.use_phytase = False

if "optimized_weights" not in st.session_state:
    st.session_state.optimized_weights = {name: 0.0 for name in st.session_state.ingredient_data.keys()}
    st.session_state.optimized_weights["ข้าวโพดบด"] = 52.0
    st.session_state.optimized_weights["กากถั่วเหลือง"] = 24.0
    st.session_state.optimized_weights["รำละเอียด"] = 14.0
    st.session_state.optimized_weights["ปลาป่น"] = 5.0
    st.session_state.optimized_weights["เปลือกหอยบด"] = 4.4
    st.session_state.optimized_weights["ไดแคลเซียมฟอสเฟต"] = 0.4
    st.session_state.optimized_weights["พรีมิกซ์ไก่ไข่ (วิตามิน)"] = 0.2

# คอยตรวจสอบค่าน้ำหนักของวัตถุดิบที่เพิ่มใหม่ให้เป็น 0 เสมอเพื่อไม่ให้ค้างคา
for name in st.session_state.ingredient_data.keys():
    if name not in st.session_state.optimized_weights:
        st.session_state.optimized_weights[name] = 0.0

def calculate_current_formulation():
    nut_calc = {"protein": 0.0, "me": 0.0, "calcium": 0.0, "phos": 0.0, "amino": 0.0, "fiber": 0.0, "fat": 0.0}
    cost, moisture, risk = 0.0, 0.0, 0.0
    for name, weight in st.session_state.optimized_weights.items():
        f = weight / 100.0
        ing = st.session_state.ingredient_data.get(name, {})
        if ing:
            nut_calc["protein"] += ing.get("protein", 0.0) * f
            nut_calc["me"] += ing.get("me", 0.0) * f
            nut_calc["calcium"] += ing.get("calcium", 0.0) * f
            nut_calc["phos"] += ing.get("phos", 0.0) * f
            nut_calc["amino"] += ing.get("amino", 0.0) * f
            nut_calc["fiber"] += ing.get("fiber", 0.0) * f
            nut_calc["fat"] += ing.get("fat", 0.0) * f
            cost += ing.get("price", 0.0) * f
            moisture += ing.get("moisture", 0.0) * f
            risk += ing.get("tox_risk", 0) * f
    return nut_calc, cost, moisture, risk

current_nutrition, current_formula_cost, total_moisture, total_risk_score = calculate_current_formulation()

# ==========================================
# 📥 4. ส่วนเนื้อหาของแต่ละแท็บแอปพลิเคชัน
# ==========================================

# --- [แท็บที่ 1]: หน้าแรก & ห้องปฏิบัติการสูตรอาหาร ---
with page_tabs[0]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 🏠 ข้อมูลสายพันธุ์หลักและการตั้งค่าฟาร์ม")
    
    c_group, c_breed = st.columns(2)
    with c_group:
        st.session_state.selected_group = st.selectbox("เลือกกลุ่มสายพันธุ์ไก่ไข่/ไก่ชน:", list(BREED_PROFILES.keys()))
    with c_breed:
        breed_options = BREED_PROFILES[st.session_state.selected_group]
        st.session_state.selected_breed_key = st.selectbox("สายพันธุ์หลักในโรงเรือน:", options=list(breed_options.keys()), format_func=lambda x: breed_options[x]["name"])
    
    st.session_state.current_key = st.selectbox("🗓️ เลือกช่วงอายุ/โปรไฟล์ของไก่ (การจัดการอายุฝูงสัตว์):", options=list(STAGE_NUTRITION_TARGETS.keys()), format_func=lambda x: STAGE_NUTRITION_TARGETS[x]["name"])
    
    breed_info = breed_options[st.session_state.selected_breed_key]
    st.markdown(f"""
    <div style='background-color:{breed_info['bg_color']}; padding:20px; border-radius:10px; color:{breed_info['text_color']}; margin-top:15px; margin-bottom:15px;'>
        <h3>🧬 สายพันธุ์ปัจจุบัน: {breed_info['name']}</h3>
        <b>🎨 สีเปลือกไข่:</b> {breed_info['egg_color']} | <b>🥣 อัตรากินอาหารเฉลี่ย:</b> {breed_info['default_feed']} กรัม/วัน/ตัว <br>
        <p style='margin: 10px 0; color:#ffffff !important;'><i>ℹ️ {breed_info['desc']}</i></p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### ⛅ การจัดการสภาพแวดล้อมและอุณหภูมิโรงเรือน")
    weather_list = ["🌡️ อากาศปกติ (25-32°C)", "🔥 อากาศร้อนจัด (> 32°C)", "❄️ อากาศหนาว (< 25°C)"]
    st.session_state.weather_env = st.radio("สภาพอากาศและอุณหภูมิวันนี้:", weather_list, horizontal=True)
    
    base_water = (breed_info['default_feed'] / 1000.0) * 2.2 if st.session_state.current_key == "laying" else 0.15
    calc_water = st.session_state.chicken_count * base_water
    if "ร้อนจัด" in st.session_state.weather_env:
        calc_water *= 1.25
        st.error("🔥 ตรวจพบสภาวะอากาศร้อนจัด! ระบบปรับโภชนาการเมตาบอลิซึม และแนะนำให้จ่ายน้ำเพิ่มขึ้น +25% ทันทีเพื่อลดสภาวะ Heat Stress")
    
    w_col1, w_col2 = st.columns(2)
    with w_col1:
        st.session_state.chicken_count = st.number_input("จำนวนไก่ในฟาร์มทั้งหมด (ตัว):", min_value=1, value=st.session_state.chicken_count, step=100)
    with w_col2:
        st.metric("💧 ปริมาณน้ำดื่มรวมที่ต้องจ่ายเข้าโรงเรือนวันนี้", f"{calc_water:,.1f} ลิตร")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 🧠 ห้องปฏิบัติการสูตรอาหาร & ปัญญาประดิษฐ์ (AI Optimizer)")
    
    target = STAGE_NUTRITION_TARGETS[st.session_state.current_key]
    density_factor = 1.08 if "ร้อนจัด" in st.session_state.weather_env else (0.95 if "หนาว" in st.session_state.weather_env else 1.0)
    adjusted_target = {
        "protein": target["protein"] * density_factor, "me": target["me"],
        "calcium": target["calcium"] * density_factor, "phos": target["phos"] * density_factor,
        "amino": target["amino"] * density_factor, "fiber": target.get("fiber", 4.0), "fat": target.get("fat", 3.5)
    }

    st.session_state.use_phytase = st.checkbox("🧪 ใส่เอนไซม์ไฟเตส (ลดเป้าหมายฟอสฟอรัสลง 0.10% อัตโนมัติ)", value=st.session_state.use_phytase)
    if st.session_state.use_phytase:
        adjusted_target["phos"] = max(0.30, adjusted_target["phos"] - 0.10)

    if st.button("⚡ สั่งคำนวณสูตรอาหารต้นทุนต่ำที่สุดด้วย AI (Run AI Least-Cost Optimizer)"):
        prob = pulp.LpProblem("LeastCostLayerFeed", pulp.LpMinimize)
        ingredient_vars = {name: pulp.LpVariable(name, lowBound=data.get("min_limit", 0.0), upBound=data.get("max_limit", 100.0)) for name, data in st.session_state.ingredient_data.items()}
        
        prob += pulp.lpSum([ingredient_vars[name] * (st.session_state.ingredient_data[name]["price"] / 100.0) for name in st.session_state.ingredient_data.keys()])
        prob += pulp.lpSum([ingredient_vars[name] for name in st.session_state.ingredient_data.keys()]) == 100.0
        
        prob += pulp.lpSum([ingredient_vars[name] * (st.session_state.ingredient_data[name]["protein"] / 100.0) for name in st.session_state.ingredient_data.keys()]) >= adjusted_target["protein"]
        prob += pulp.lpSum([ingredient_vars[name] * (st.session_state.ingredient_data[name]["me"] / 100.0) for name in st.session_state.ingredient_data.keys()]) >= adjusted_target["me"]
        prob += pulp.lpSum([ingredient_vars[name] * (st.session_state.ingredient_data[name]["calcium"] / 100.0) for name in st.session_state.ingredient_data.keys()]) >= adjusted_target["calcium"]
        prob += pulp.lpSum([ingredient_vars[name] * (st.session_state.ingredient_data[name]["phos"] / 100.0) for name in st.session_state.ingredient_data.keys()]) >= adjusted_target["phos"]
        
        status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
        if pulp.LpStatus[status] == "Optimal":
            for name in st.session_state.ingredient_data.keys():
                st.session_state.optimized_weights[name] = round(ingredient_vars[name].varValue, 1)
            st.success("🎉 AI ค้นพบสัดส่วนสูตรที่ราคาประหยัดที่สุดเรียบร้อยแล้ว!")
            st.rerun()
        else:
            st.error("❌ ไม่สามารถผสานสูตรได้เนื่องจากเกณฑ์โภชนาการแน่นเกินไป กรุณาขยายขีดจำกัด Min/Max วัตถุดิบ")

    st.markdown("---")
    creator_left, creator_right = st.columns(2, gap="large")
    
    with creator_left:
        st.markdown("#### 🔧 1. ปรับสัดส่วนวัตถุดิบด้วยมือ (%)")
        st.markdown("*สามารถเลื่อนสไลเดอร์ หรือกรอกตัวเลขที่ต้องการลงในช่องขวามือตรงๆ ได้เลยครับ*")
        
        user_weights = {}
        # วนลูปสร้างหน้าตาแบบสไลเดอร์คู่กับกล่องกรอกตัวเลข เพื่อให้ชาวบ้านพิมพ์เองได้ง่ายๆ
        for name in list(st.session_state.ingredient_data.keys()):
            val = float(st.session_state.optimized_weights.get(name, 0.0))
            
            # แบ่งพื้นที่เป็นแถว: ชื่อวัตถุดิบนำหน้า ตามด้วยสไลเดอร์และกล่องข้อความ
            st.write(f"**🌾 {name}**")
            slider_col, input_col = st.columns([7, 3])
            
            with slider_col:
                s_val = st.slider(
                    f"ปรับสัดส่วน {name}", 0.0, 100.0, val, step=0.1, 
                    label_visibility="collapsed", key=f"sl_bar_{name}"
                )
            with input_col:
                i_val = st.number_input(
                    f"ระบุตัวเลข {name}", min_value=0.0, max_value=100.0, value=s_val, step=0.1, 
                    format="%.1f", label_visibility="collapsed", key=f"num_in_{name}"
                )
            
            # ตรวจจับว่าถ้าฝั่งไหนขยับ ให้ดึงค่านั้นไปใช้งาน
            user_weights[name] = i_val
            
        st.session_state.optimized_weights = user_weights

        total_sum = sum(user_weights.values())
        st.markdown(f"**🔢 น้ำหนักรวมสูตรตอนนี้:** `{total_sum:.1f}%` (เป้าหมายคือ 100%)")
        if not (99.9 <= total_sum <= 100.1):
            st.warning("⚠️ สัดส่วนรวมยังไม่ครบ 100% กรุณาปรับเพิ่มหรือลดวัตถุดิบให้รวมได้ 100.0% พอดี")

    with creator_right:
        st.markdown("#### 🩺 2. ระดับสารอาหารจริงเทียบกับเป้าหมาย")
        nutrient_display = [
            ("🥩 โปรตีนรวม (Crude Protein)", "protein", "%"),
            ("⚡ พลังงานใช้ประโยชน์ได้ (ME)", "me", "kcal/kg"),
            ("🦴 แคลเซียม (Calcium)", "calcium", "%"),
            ("🧪 ฟอสฟอรัสที่เป็นประโยชน์ (Phosphorus)", "phos", "%"),
            ("🌾 กากใยรวม (Crude Fiber)", "fiber", "%"),
            ("🌽 ไขมันรวม (Crude Fat)", "fat", "%")
        ]
        for label, key_name, unit in nutrient_display:
            cur = current_nutrition[key_name]
            req = adjusted_target.get(key_name, 1.0)
            st.write(f"**{label}**: {cur:.2f} / {req:.2f} {unit}")
            st.progress(min(max(cur / req, 0.0), 1.0) if req > 0 else 0.0)
            
        st.markdown("---")
        if total_moisture > 12.0:
            st.markdown(f"💧 **ความชื้นสะสมสูตร:** <span style='color:#ef4444; font-weight:bold;'>{total_moisture:.1f}% 🔴 เสี่ยงเกิดเชื้อราสูง</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"💧 **ความชื้นสะสมสูตร:** <span style='color:#22c55e; font-weight:bold;'>{total_moisture:.1f}% 🟢 เกณฑ์ปลอดภัย</span>", unsafe_allow_html=True)
            
        st.metric("💰 ต้นทุนสูตรผสมอาหารปัจจุบัน", f"{current_formula_cost:.2f} บาท / กิโลกรัม")
    st.markdown("</div>", unsafe_allow_html=True)


# --- [แท็บที่ 2]: สถิติผลผลิต & บัญชีฟาร์ม ---
with page_tabs[1]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 📈 สมุดจดบันทึกสถิติและวิเคราะห์ผลกำไรฟาร์ม")
    if "tracker_data" not in st.session_state:
        st.session_state.tracker_data = pd.DataFrame([
            {"วันที่": "01/06", "อัตราการไข่ (%)": 82.0, "อัตราไข่บุบแตก (%)": 4.5, "น้ำหนักไข่รวม (กก.)": 52.0, "กำไรสุทธิวันนี้ (บาท)": 420.0},
            {"วันที่": "02/06", "อัตราการไข่ (%)": 81.5, "อัตราไข่บุบแตก (%)": 5.0, "น้ำหนักไข่รวม (กก.)": 51.5, "กำไรสุทธิวันนี้ (บาท)": 395.0},
        ])
    
    df_track = st.session_state.tracker_data.copy()
    m1, m2 = st.columns(2)
    m1.metric("🥚 อัตราการให้ไข่เฉลี่ย", f"{df_track['อัตราการไข่ (%)'].mean():.1f} %")
    m2.metric("💵 กำไรสุทธิรวมสะสม", f"{df_track['กำไรสุทธิวันนี้ (บาท)'].sum():,.1f} บาท")
    
    st.markdown("---")
    track_col1, track_col2 = st.columns([4, 6], gap="large")
    
    with track_col1:
        st.markdown("##### 📝 จดบันทึกผลผลิตประจำวัน")
        with st.form("ledger_input_mega_form"):
            in_date = st.text_input("วันที่บันทึก (วัน/เดือน):", value=datetime.now().strftime("%d/%m"))
            lay_r = st.number_input("อัตราการไข่วันนี้ (%):", value=84.0)
            crack_r = st.number_input("อัตราไข่แตกเสียหาย (%):", value=1.5)
            egg_w = st.number_input("น้ำหนักไข่รวมหน้าแผง (กก.):", value=53.0)
            p_today = st.number_input("กำไรสุทธิประเมินวันนี้ (บาท):", value=450.0)
            
            if st.form_submit_button("💾 กดบันทึกข้อมูล"):
                new_row = {
                    "วันที่": in_date, "อัตราการไข่ (%)": lay_r, 
                    "อัตราไข่บุบแตก (%)": crack_r, "น้ำหนักไข่รวม (กก.)": egg_w, 
                    "กำไรสุทธิวันนี้ (บาท)": p_today
                }
                st.session_state.tracker_data = pd.concat([st.session_state.tracker_data, pd.DataFrame([new_row])], ignore_index=True)
                st.success("บันทึกข้อมูลสำเร็จ!")
                st.rerun()
                
    with track_col2:
        st.markdown("##### 📊 กราฟวิเคราะห์แนวโน้มอัตราผลิตไข่")
        fig_prod = go.Figure()
        fig_prod.add_trace(go.Scatter(x=df_track["วันที่"], y=df_track["อัตราการไข่ (%)"], name="อัตราการไข่ (%)", line=dict(color='#22c55e', width=3)))
        fig_prod.update_layout(
            margin=dict(t=20, b=20, l=20, r=20), 
            height=280,
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="white")
        )
        st.plotly_chart(fig_prod, use_container_width=True)

    st.markdown("##### 📄 ตารางประวัติบัญชีย้อนหลัง")
    st.dataframe(df_track, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


# --- [แท็บที่ 3]: ระบบหลังบ้าน ---
with page_tabs[2]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 📦 ระบบหลังบ้าน & จัดการราคาวัตถุดิบ")
    st.markdown("### 💰 อัปเดตราคาท้องตลาดประจำวันนี้")
    st.markdown("ชาวบ้านหรือคนงานสามารถเดินเช็กราคาในตลาด แล้วมาแก้เฉพาะตัวเลขราคาตรงนี้ได้เลยครับ")
    st.markdown("---")

    # ➕ 1. ระบบเพิ่มวัตถุดิบใหม่ด้วยตัวเอง
    st.markdown("### ➕ เพิ่มวัตถุดิบใหม่เข้าฟาร์ม")
    st.markdown("หากมีวัตถุดิบใหม่นอกเหนือจากรายการด้านล่าง สามารถพิมพ์ชื่อและราคาตั้งต้นเพื่อเพิ่มลงระบบได้เลยครับ")
    
    with st.form("add_new_ingredient_form", clear_on_submit=True):
        new_ing_col1, new_ing_col2 = st.columns(2)
        with new_ing_col1:
            new_name = st.text_input("🌾 ชื่อวัตถุดิบใหม่:", placeholder="เช่น ข้าวเปลือก, กากมะพร้าวดิบ...")
        with new_ing_col2:
            new_price = st.number_input("💵 ราคาตั้งต้น (บาท ต่อ กิโลกรัม):", min_value=0.0, value=10.0, step=0.5, format="%.2f")
        
        submit_new_ing = st.form_submit_button("✨ กดเพิ่มวัตถุดิบใหม่เข้าตารางด้านล่าง", use_container_width=True)
        
        if submit_new_ing and new_name:
            new_name_clean = new_name.strip()
            if new_name_clean in st.session_state.ingredient_data:
                st.warning(f"⚠️ มีวัตถุดิบชื่อ '{new_name_clean}' อยู่ในระบบแล้วครับ")
            else:
                st.session_state.ingredient_data[new_name_clean] = {
                    "price": new_price, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, 
                    "amino": 0.00, "moisture": 10.0, "fiber": 0.0, "fat": 0.0, "tox_risk": 0, 
                    "min_limit": 0.0, "max_limit": 100.0
                }
                st.session_state.optimized_weights[new_name_clean] = 0.0
                st.success(f"🎉 เพิ่ม '{new_name_clean}' เข้าสู่ระบบจัดการราคาเรียบร้อยแล้ว!")
                st.rerun()

    st.markdown("---")

    # 💵 2. แสดงกล่องแก้ไขราคาแยกชิ้น สไตล์บ้านๆ ตามรูปภาพ
    st.markdown("### 📝 รายการวัตถุดิบทั้งหมดที่มีในระบบ")
    current_ingredients = st.session_state.ingredient_data
    
    col_left, col_right = st.columns(2, gap="large")
    updated_prices = {}
    
    ing_names = list(current_ingredients.keys())
    half_size = (len(ing_names) + 1) // 2
    
    # ฝั่งซ้าย
    with col_left:
        for name in ing_names[:half_size]:
            old_price = current_ingredients[name]["price"]
            updated_prices[name] = st.number_input(
                f"💵 ราคา {name} (บาท ต่อ กิโลกรัม)", 
                min_value=0.0, 
                value=float(old_price), 
                step=0.5, 
                format="%.2f",
                key=f"simple_price_{name}"
            )

    # ฝั่งขวา
    with col_right:
        for name in ing_names[half_size:]:
            old_price = current_ingredients[name]["price"]
            updated_prices[name] = st.number_input(
                f"💵 ราคา {name} (บาท ต่อ กิโลกรัม)", 
                min_value=0.0, 
                value=float(old_price), 
                step=0.5, 
                format="%.2f",
                key=f"simple_price_{name}"
            )

    st.markdown("---")
    
    if st.button("💾 ยืนยันบันทึกราคาทุกอย่าง (Save Prices)", type="primary", use_container_width=True):
        for name, new_p in updated_prices.items():
            st.session_state.ingredient_data[name]["price"] = new_p
        st.success("🎉 อัปเดตราคาทั้งหมดเรียบร้อยแล้ว! สามารถกลับไปกดคำนวณสูตรอาหารหรือปรับสไลเดอร์ที่หน้าแรกได้เลย")
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


    # --- ส่วนใบสั่งซื้อ สำหรับเอาไปยื่นร้านขายอาหารสัตว์ ---
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 📝 ใบสั่งซื้อวัตถุดิบสำหรับเดินไปเข้าร้านค้า")
    
    total_feed_needed_kg = st.session_state.chicken_count * LIFECYCLE_FEED_BUDGET[st.session_state.current_key]
    st.info(f"📊 สำหรับไก่จำนวน **{st.session_state.chicken_count:,} ตัว** ต้องใช้อาหารรวมทั้งหมด **{total_feed_needed_kg:,.1f} กิโลกรัม** (หรือประมาณ {total_feed_needed_kg/30:,.0f} กระสอบ)")
    
    budget_data = []
    for name, weight in st.session_state.optimized_weights.items():
        w_kg = (weight / 100.0) * total_feed_needed_kg
        if w_kg > 0:
            p_unit = st.session_state.ingredient_data.get(name, {}).get("price", 0.0)
            budget_data.append({
                "รายการวัตถุดิบที่ต้องซื้อ": name,
                "สัดส่วนในสูตร": f"{weight}%",
                "น้ำหนักรวมที่ต้องใช้ (กิโลกรัม)": f"{w_kg:,.1f} กก.",
                "คิดเป็นจำนวนกระสอบ (30 กก.)": f"~ {round(w_kg / 30, 1)} กระสอบ",
                "ประมาณการเงินที่ต้องเตรียม (บาท)": f"{round(w_kg * p_unit, 2):,} บาท"
            })
            
    df_budget = pd.DataFrame(budget_data)
    if not df_budget.empty:
        st.dataframe(df_budget, use_container_width=True, hide_index=True)
        csv = df_budget.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 ดาวน์โหลดใบสั่งซื้อนี้ไปพิมพ์รายงาน (Download PO)", data=csv, file_name="ใบสั่งซื้อวัตถุดิบหน้าฟาร์ม.csv", mime="text/csv")
    else:
        st.info("💡 สัดส่วนอาหารในสูตรยังเป็น 0% กรุณาไปกดปุ่ม 'สั่งคำนวณสูตรอาหาร' หรือปรับเปอร์เซ็นต์ที่หน้าแรกก่อนนะครับ")
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 🏁 ส่วนท้ายของแอปพลิเคชัน
# ==========================================
st.markdown("---")
st.markdown("<div style='text-align: center; color: #ffffff; font-size: 0.85em; text-shadow: 1px 1px 2px #000;'>© 2026 Smart Layer Feed | ปรับปรุงโมดูลผสมอาหารด้วยสไลเดอร์ควบคู่กล่องป้อนตัวเลขเสร็จสมบูรณ์</div>", unsafe_allow_html=True)
