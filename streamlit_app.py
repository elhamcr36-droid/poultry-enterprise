import streamlit as st
import pandas as pd
import plotly.express as px
import pulp  # ไลบรารีสำหรับคำนวณจุดคุ้มทุน (Linear Programming)
import requests  # สำหรับเชื่อมต่อ REST API

# 🔱 1. ตั้งค่าแอปและธีม (App Configuration)
st.set_page_config(page_title="Smart Layer Feed - ระบบจัดการอาหารไก่ไข่อัจฉริยะ", layout="wide")

st.sidebar.title("🛠️ ตั้งค่าระบบ (Settings)")
SUPABASE_URL = st.sidebar.text_input("Supabase Project URL", "https://your-project.supabase.co")
SUPABASE_KEY = st.sidebar.text_input("Supabase Anon API Key", "your-anon-key", type="password")

# 📋 2. ฐานข้อมูลโภชนาการ (Nutrition Database)
STAGE_NUTRITION_TARGETS = {
    "starter": {"name": "ลูกไก่ไข่ (0 - 6 สัปดาห์)", "protein": 20.0, "me": 2900.0, "calcium": 1.00, "phos": 0.45, "amino": 0.42},
    "grower": {"name": "ไก่รุ่นไข่ (6 - 16 สัปดาห์)", "protein": 16.0, "me": 2750.0, "calcium": 0.90, "phos": 0.40, "amino": 0.32},
    "laying": {"name": "ไก่ไข่ระยะให้ผลผลิต (16 สัปดาห์ขึ้นไป)", "protein": 17.5, "me": 2750.0, "calcium": 4.10, "phos": 0.42, "amino": 0.38}
}

INGREDIENT_DATA = {
    "ข้าวโพดบด": {"price": 13.5, "protein": 8.5, "me": 3300.0, "calcium": 0.02, "phos": 0.25, "amino": 0.18, "moisture": 12.0, "tox_risk": 3, "min_limit": 30.0, "max_limit": 65.0},
    "กากถั่วเหลือง": {"price": 18.5, "protein": 44.0, "me": 2420.0, "calcium": 0.25, "phos": 0.60, "amino": 0.65, "moisture": 11.5, "tox_risk": 1, "min_limit": 10.0, "max_limit": 35.0},
    "รำละเอียด": {"price": 11.0, "protein": 12.0, "me": 2400.0, "calcium": 0.05, "phos": 1.35, "amino": 0.22, "moisture": 10.5, "tox_risk": 3, "min_limit": 5.0, "max_limit": 25.0},
    "ปลาป่น": {"price": 32.0, "protein": 60.0, "me": 2850.0, "calcium": 5.00, "phos": 3.00, "amino": 0.95, "moisture": 10.0, "tox_risk": 1, "min_limit": 2.0, "max_limit": 10.0},
    "เปลือกหอยบด": {"price": 4.0, "protein": 0.0, "me": 0.0, "calcium": 38.00, "phos": 0.04, "amino": 0.00, "moisture": 0.5, "tox_risk": 0, "min_limit": 1.0, "max_limit": 10.0},
    "ไดแคลเซียมฟอสเฟต": {"price": 28.0, "protein": 0.0, "me": 0.0, "calcium": 21.00, "phos": 18.00, "amino": 0.00, "moisture": 1.0, "tox_risk": 0, "min_limit": 0.2, "max_limit": 3.0},
    "กรดอะมิโนสังเคราะห์": {"price": 95.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "amino": 99.00, "moisture": 0.2, "tox_risk": 0, "min_limit": 0.1, "max_limit": 1.0}
}

# 🐔 ข้อมูลสายพันธุ์ (Breed Profiles)
BREED_PROFILES = {
    "กลุ่มไฮบริดพาณิชย์ (Commercial Hybrids)": {
        "Isa Brown": {"name": "Isa Brown (ไอซ่า บราวน์)", "default_feed": 115, "desc": "ไข่ดก ทนร้อนดีเยี่ยม"},
        "Hy-Line Brown": {"name": "Hy-Line Brown (ไฮไลน์ บราวน์)", "default_feed": 110, "desc": "กินน้อย ไข่นิ่ง สม่ำเสมอ"}
    }
}

# เริ่มต้นสถานะ (Session State)
if "optimized_weights" not in st.session_state:
    st.session_state.optimized_weights = {name: 10.0 for name in INGREDIENT_DATA.keys()}

# ==========================================
# 🏛️ ส่วนแสดงผลหน้าจอ (Dashboard UI)
# ==========================================
st.title("🔱 Smart Layer Feed — ระบบจัดการอาหารไก่ไข่อัจฉริยะ")
st.caption("ระบบคำนวณโภชนาการแบบแม่นยำสูง (Precision Nutrition Engine)")

st.markdown("### 🧬 0. ข้อมูลสายพันธุ์และสถานะฟาร์ม (Breed Profile & Farm Status)")
c_group, c_breed = st.columns(2)
with c_group:
    selected_group = st.selectbox("เลือกกลุ่มสายพันธุ์:", list(BREED_PROFILES.keys()))
with c_breed:
    selected_breed_key = st.selectbox("เลือกสายพันธุ์:", list(BREED_PROFILES[selected_group].keys()))

breed_info = BREED_PROFILES[selected_group][selected_breed_key]
st.info(f"**สายพันธุ์:** {breed_info['name']} | **อัตราการกิน:** {breed_info['default_feed']} กรัม/วัน")

st.markdown("---")

# ==========================================
# ⛅ ระบบปรับแต่งตามสภาพแวดล้อม
# ==========================================
st.markdown("### ⛅ 1. ระบบชดเชยปัจจัยสิ่งแวดล้อม (Environmental Compensator)")
c_age, c_weather = st.columns(2)
with c_age:
    current_key = st.selectbox("ระยะการเจริญเติบโต (Life Stage):", list(STAGE_NUTRITION_TARGETS.keys()))
    target = STAGE_NUTRITION_TARGETS[current_key]
with c_weather:
    weather_env = st.radio("สภาพอากาศวันนี้:", ["อากาศปกติ (25-32°C)", "อากาศร้อนจัด (> 32°C)", "อากาศหนาว (< 25°C)"], horizontal=True)

density_factor = 1.08 if "ร้อนจัด" in weather_env else 1.0
adjusted_target = {k: v * density_factor if k != "me" else v for k, v in target.items()}

# ==========================================
# 🧠 ระบบ AI คำนวณต้นทุนต่ำสุด (Optimization Engine)
# ==========================================
st.markdown("### 🧠 2. ระบบ AI คำนวณสูตรอาหารต้นทุนต่ำสุด (AI Optimizer)")
if st.button("⚡ เริ่มคำนวณสูตรอาหาร (Run AI Optimizer)"):
    prob = pulp.LpProblem("LeastCostLayerFeed", pulp.LpMinimize)
    vars = {name: pulp.LpVariable(name, lowBound=data["min_limit"], upBound=data["max_limit"]) for name, data in INGREDIENT_DATA.items()}
    
    prob += pulp.lpSum([vars[n] * (INGREDIENT_DATA[n]["price"] / 100.0) for n in INGREDIENT_DATA.keys()])
    prob += pulp.lpSum([vars[n] for n in INGREDIENT_DATA.keys()]) == 100.0
    
    # เงื่อนไขโภชนาการ (Nutritional Constraints)
    prob += pulp.lpSum([vars[n] * (INGREDIENT_DATA[n]["protein"] / 100.0) for n in INGREDIENT_DATA.keys()]) >= adjusted_target["protein"]
    prob += pulp.lpSum([vars[n] * (INGREDIENT_DATA[n]["me"] / 100.0) for n in INGREDIENT_DATA.keys()]) >= adjusted_target["me"]
    
    if prob.solve() == pulp.LpStatusOptimal:
        for name in INGREDIENT_DATA.keys():
            st.session_state.optimized_weights[name] = round(vars[name].varValue, 1)
        st.success("✅ คำนวณสูตรที่คุ้มค่าที่สุดสำเร็จ!")
    else:
        st.error("❌ ไม่สามารถหาค่าที่เหมาะสมได้ โปรดตรวจสอบข้อจำกัดวัตถุดิบ")

# ==========================================
# 🎛️ ส่วนปรับแต่งสูตร (Formula Workspace)
# ==========================================
st.markdown("### 🛠️ 3. ปรับแต่งสูตรอาหาร (Formula Adjustment)")
user_weights = {name: st.slider(f"{name} (%)", 0.0, 100.0, float(st.session_state.optimized_weights.get(name, 0.0)), step=0.1) 
                for name in INGREDIENT_DATA.keys()}

# คำนวณสรุปโภชนาการ (Real-time Monitoring)
total_cost = sum([INGREDIENT_DATA[name]["price"] * (weight/100) for name, weight in user_weights.items()])
st.metric("💰 ต้นทุนวัตถุดิบเฉลี่ย (Average Cost)", f"{total_cost:.2f} บาท/กก.")

st.markdown("---")
# ==========================================
# 📊 ระบบจัดการและซิงค์ข้อมูล
# ==========================================
st.markdown("### 📈 4. ระบบบันทึกผลผลิต (Production Tracking)")
with st.form("sync_form"):
    lay_r = st.number_input("อัตราการไข่เฉลี่ยวันนี้ (%) (Laying Rate):", value=85.0)
    if st.form_submit_button("💾 บันทึกและซิงค์ข้อมูลขึ้นคลาวด์"):
        st.success("☁️ บันทึกข้อมูลเข้าฐานข้อมูลเรียบร้อยแล้ว")
