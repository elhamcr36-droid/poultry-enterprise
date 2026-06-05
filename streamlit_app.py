import streamlit as st
import pandas as pd
import plotly.express as px
import pulp
import requests

# 🔱 1. INITIAL APP CONFIG
st.set_page_config(page_title="Smart Layer Feed - Enterprise AI", layout="wide")

# 📋 DATA DEFINITIONS (ย่อเพื่อความกระชับ)
STAGE_NUTRITION_TARGETS = {
    "starter": {"name": "ลูกไก่ไข่ (0-6 สัปดาห์)", "protein": 20.0, "me": 2900.0, "calcium": 1.00, "phos": 0.45, "amino": 0.42},
    "grower": {"name": "ไก่รุ่นไข่ (6-16 สัปดาห์)", "protein": 16.0, "me": 2750.0, "calcium": 0.90, "phos": 0.40, "amino": 0.32},
    "laying": {"name": "ไก่ไข่ระยะให้ผลผลิต", "protein": 17.5, "me": 2750.0, "calcium": 4.10, "phos": 0.42, "amino": 0.38}
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

# 🧠 AI OPTIMIZER FUNCTION
def run_optimization(target, use_phytase):
    # ปรับปรุงเป้าหมายตาม Phytase
    if use_phytase: target["phos"] = max(0.30, target["phos"] - 0.10)
    
    prob = pulp.LpProblem("LeastCostLayerFeed", pulp.LpMinimize)
    vars = {name: pulp.LpVariable(name, lowBound=data["min_limit"], upBound=data["max_limit"]) for name, data in INGREDIENT_DATA.items()}
    
    prob += pulp.lpSum([vars[n] * (INGREDIENT_DATA[n]["price"] / 100.0) for n in INGREDIENT_DATA.keys()])
    prob += pulp.lpSum([vars[n] for n in INGREDIENT_DATA.keys()]) == 100.0
    for nut in ["protein", "me", "calcium", "phos", "amino"]:
        prob += pulp.lpSum([vars[n] * (INGREDIENT_DATA[n][nut] / 100.0) for n in INGREDIENT_DATA.keys()]) >= target[nut]
        
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    return prob, vars

# 🖥️ MAIN APP UI
st.title("🔱 Smart Layer Feed — Enterprise AI")

# ส่วนตั้งค่า (Expander ช่วยประหยัดพื้นที่หน้าจอ)
with st.expander("🛠️ 1. ตั้งค่าโปรไฟล์และสิ่งแวดล้อม", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        stage = st.selectbox("เลือกโปรไฟล์อายุไก่:", list(STAGE_NUTRITION_TARGETS.keys()))
        use_phytase = st.checkbox("ใส่เอนไซม์ไฟเตส (Phytase)", value=True)
    with col2:
        weather = st.radio("อุณหภูมิหน้าเล้า:", ["ปกติ", "ร้อนจัด", "หนาว"], horizontal=True)
        density_factor = 1.08 if weather == "ร้อนจัด" else (0.95 if weather == "หนาว" else 1.0)

# คำนวณ
target = {k: (v * density_factor if k != "me" else v) for k, v in STAGE_NUTRITION_TARGETS[stage].items() if k != "name"}
prob, vars = run_optimization(target.copy(), use_phytase)

# ส่วนแสดงผล
if st.button("⚡ รัน AI Optimization Engine"):
    if pulp.LpStatus[prob.status] == "Optimal":
        st.success("✅ คำนวณสูตรอาหารที่ประหยัดที่สุดสำเร็จ!")
        results = {name: round(vars[name].varValue, 2) for name in INGREDIENT_DATA.keys()}
        st.write("### สัดส่วนที่แนะนำ (%):", results)
        
        # ส่วนวิเคราะห์ Shadow Price
        st.write("#### 📉 ข้อมูลเชิงลึก (Shadow Price Analysis)")
        shadows = {name: prob.constraints[name].pi for name in prob.constraints if hasattr(prob.constraints[name], 'pi') and prob.constraints[name].pi != 0}
        st.write("วัตถุดิบที่มีผลต่อการลดต้นทุน:", shadows)
    else:
        st.error("❌ ไม่พบทางเลือกที่เหมาะสม (โปรดปรับข้อจำกัดของวัตถุดิบ)")

# ส่วนบันทึกผล
st.markdown("---")
st.subheader("📈 Production Tracker")
if "tracker" not in st.session_state:
    st.session_state.tracker = pd.DataFrame(columns=["วันที่", "อัตราการไข่ (%)"])

with st.form("sync_data"):
    d = st.text_input("วันที่บันทึก:", "05/06/2026")
    rate = st.number_input("อัตราการไข่ (%):", 0.0, 100.0)
    if st.form_submit_button("💾 บันทึกผลลงฐานข้อมูล"):
        new_data = pd.DataFrame([{"วันที่": d, "อัตราการไข่ (%)": rate}])
        st.session_state.tracker = pd.concat([st.session_state.tracker, new_data])
        st.success("บันทึกข้อมูลสำเร็จ!")

st.dataframe(st.session_state.tracker)
