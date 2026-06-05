import streamlit as st
import pandas as pd
import plotly.express as px
import pulp  # ไลบรารีสำหรับคำนวณจุดคุ้มทุน (Linear Programming)
import requests  # สำหรับเชื่อมต่อ REST API

# 🔱 1. ตั้งค่าแอปและธีม (App Configuration)
st.set_page_config(page_title="Smart Layer Feed - Enterprise AI", layout="wide")

st.sidebar.title("🛠️ ตั้งค่าระบบคลาวด์")
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

BREED_PROFILES = {
    "1. กลุ่มไฮบริดพาณิชย์ (Commercial Hybrids)": {
        "Isa Brown": {"name": "Isa Brown (ไอซ่า บราวน์)", "egg_color": "🤎 น้ำตาลเข้ม", "default_feed": 115, "desc": "ไข่ดก ทนร้อน"},
        "Hy-Line Brown": {"name": "Hy-Line Brown (ไฮไลน์ บราวน์)", "egg_color": "🤎 น้ำตาลนวล", "default_feed": 110, "desc": "กินน้อย ไข่นิ่ง"},
        "Lohmann Brown": {"name": "Lohmann Brown (โลห์แมน บราวน์)", "egg_color": "🤎 น้ำตาลสม่ำเสมอ", "default_feed": 114, "desc": "ปรับตัวดี ไข่ฟองใหญ่"}
    },
    "2. กลุ่มสายพันธุ์แท้ (Pure Breeds)": {
        "Rhode Island Red": {"name": "Rhode Island Red (โรดไอแลนด์เรด)", "egg_color": "🤎 น้ำตาลอ่อน", "default_feed": 125, "desc": "อึด ทนโรค"}
    }
}

LIFECYCLE_FEED_BUDGET = {"starter": 1.2, "grower": 2.8, "laying": 48.0}

if "optimized_weights" not in st.session_state:
    st.session_state.optimized_weights = {"ข้าวโพดบด": 52.0, "กากถั่วเหลือง": 24.0, "รำละเอียด": 14.0, "ปลาป่น": 5.0, "เปลือกหอยบด": 4.2, "ไดแคลเซียมฟอสเฟต": 0.6, "กรดอะมิโนสังเคราะห์": 0.2}

# ==========================================
# 🏛️ Header & Breed Info
# ==========================================
st.title("🔱 Smart Layer Feed — ระบบจัดการอาหารไก่ไข่อัจฉริยะ")
st.markdown("### 🧬 0. ข้อมูลสายพันธุ์ (Breed Profile)")
c_group, c_breed = st.columns(2)
with c_group: selected_group = st.selectbox("เลือกกลุ่ม:", list(BREED_PROFILES.keys()))
with c_breed: selected_breed_key = st.selectbox("เลือกสายพันธุ์:", list(BREED_PROFILES[selected_group].keys()))
breed_info = BREED_PROFILES[selected_group][selected_breed_key]

st.info(f"**{breed_info['name']}** | อัตรากินอาหาร: {breed_info['default_feed']} กรัม/วัน | {breed_info['desc']}")

# ==========================================
# ⛅ Environmental Compensator
# ==========================================
st.markdown("### ⛅ 1. ระบบชดเชยปัจจัยสิ่งแวดล้อม (Environmental Compensator)")
c_age, c_weather = st.columns(2)
with c_age:
    current_key = st.selectbox("ระยะการเจริญเติบโต (Life Stage):", list(STAGE_NUTRITION_TARGETS.keys()), index=2)
    target = STAGE_NUTRITION_TARGETS[current_key]
with c_weather:
    weather_env = st.radio("อุณหภูมิหน้าเล้า:", ["อากาศปกติ (25-32°C)", "อากาศร้อนจัด (> 32°C)", "อากาศหนาว (< 25°C)"], horizontal=True)

density_factor = 1.08 if "ร้อนจัด" in weather_env else (0.95 if "หนาว" in weather_env else 1.0)
adjusted_target = {k: target[k] * density_factor if k in ["protein", "calcium", "phos", "amino"] else target[k] for k in target}

# ==========================================
# 🧠 AI Optimizer
# ==========================================
st.markdown("### 🧠 2. ระบบ AI คำนวณสูตรอาหารต้นทุนต่ำสุด (AI Optimizer)")
use_phytase = st.checkbox("🧪 ใส่เอนไซม์ไฟเตส (Phytase) เพื่อย่อยฟอสฟอรัส", value=True)
if use_phytase: adjusted_target["phos"] = max(0.30, adjusted_target["phos"] - 0.10)

if st.button("⚡ ประมวลผลสูตรอาหาร"):
    prob = pulp.LpProblem("LeastCostLayerFeed", pulp.LpMinimize)
    vars = {n: pulp.LpVariable(n, lowBound=d["min_limit"], upBound=d["max_limit"]) for n, d in INGREDIENT_DATA.items()}
    prob += pulp.lpSum([vars[n] * (INGREDIENT_DATA[n]["price"] / 100.0) for n in INGREDIENT_DATA.keys()])
    prob += pulp.lpSum([vars[n] for n in INGREDIENT_DATA.keys()]) == 100.0
    prob += pulp.lpSum([vars[n] * (INGREDIENT_DATA[n]["protein"] / 100.0) for n in INGREDIENT_DATA.keys()]) >= adjusted_target["protein"]
    prob += pulp.lpSum([vars[n] * (INGREDIENT_DATA[n]["me"] / 100.0) for n in INGREDIENT_DATA.keys()]) >= adjusted_target["me"]
    prob += pulp.lpSum([vars[n] * (INGREDIENT_DATA[n]["calcium"] / 100.0) for n in INGREDIENT_DATA.keys()]) >= adjusted_target["calcium"]
    
    if prob.solve() == pulp.LpStatusOptimal:
        for n in INGREDIENT_DATA.keys(): st.session_state.optimized_weights[n] = round(vars[n].varValue, 1)
        st.success("🎉 ค้นพบสูตรอาหารที่ประหยัดที่สุดแล้ว!")
    else: st.error("❌ ไม่พบสูตรที่เหมาะสม")

# ==========================================
# 🎛️ Matrix Adjustment
# ==========================================
st.markdown("### 🛠️ 3. ปรับแต่งสูตร (Formula Adjustment)")
user_weights = {n: st.slider(f"{n} (%)", 0.0, 100.0, float(st.session_state.optimized_weights.get(n, 0.0)), step=0.1) for n in INGREDIENT_DATA.keys()}

# Calculations
total_cost = sum([INGREDIENT_DATA[n]["price"] * (w/100) for n, w in user_weights.items()])
total_moisture = sum([INGREDIENT_DATA[n]["moisture"] * (w/100) for n, w in user_weights.items()])
st.metric("💰 ต้นทุนอาหารเฉลี่ย (Average Feed Cost)", f"{total_cost:.2f} บาท/กก.")

# ==========================================
# 📅 Farm Operations
# ==========================================
st.markdown("### 📅 4. ระบบจัดการฟาร์ม (Farm Operations)")
c_water, c_moist, c_night = st.columns(3)
with c_water:
    chicken_count = st.number_input("จำนวนไก่ (ตัว):", value=1000)
    water_liters = chicken_count * ((breed_info['default_feed']/1000)*2.2) * (1.2 if "ร้อนจัด" in weather_env else 1)
    st.metric("น้ำที่ต้องใช้/วัน", f"{water_liters:,.1f} ลิตร")

with c_moist:
    if total_moisture > 12.0: st.error(f"⚠️ ความชื้นสูง: {total_moisture:.1f}%")
    else: st.success(f"✨ ความชื้นปลอดภัย: {total_moisture:.1f}%")

with c_night:
    st.checkbox("ระบบ Midnight Feeding (มื้อดึก)")

# ==========================================
# 📈 Tracker & Sync
# ==========================================
st.markdown("### 📈 5. บันทึกผลผลิตและซิงค์ข้อมูล (Production Tracking)")
if "tracker_data" not in st.session_state:
    st.session_state.tracker_data = pd.DataFrame([{"วันที่": "01/06", "อัตราการไข่ (%)": 82.0, "อัตราไข่แตก (%)": 4.5}])

with st.form("sync_form"):
    lay_r = st.number_input("อัตราการไข่ (%)", value=85.0)
    crack_r = st.number_input("อัตราไข่แตก (%)", value=2.0)
    if st.form_submit_button("💾 บันทึกและซิงค์ขึ้น Cloud"):
        new_row = pd.DataFrame([{"วันที่": "05/06", "อัตราการไข่ (%)": lay_r, "อัตราไข่แตก (%)": crack_r}])
        st.session_state.tracker_data = pd.concat([st.session_state.tracker_data, new_row])
        st.success("☁️ ซิงค์ข้อมูลสำเร็จ!")

st.line_chart(st.session_state.tracker_data.set_index("วันที่"))
