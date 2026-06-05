import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pulp
from datetime import datetime

# ==========================================
# 🔱 1. ตั้งค่าคอนฟิกแอปพลิเคชันและหน้าจอ (Application Configuration)
# ==========================================
st.set_page_config(page_title="Smart Layer Feed - ระบบคำนวณอาหารไก่ไข่อัจฉริยะ", layout="wide")

# เมนูด้านข้างสำหรับการเชื่อมต่อระบบคลาวด์ (Sidebar for Cloud Connection)
st.sidebar.markdown("### ☁️ การเชื่อมต่อคลาวด์ระดับองค์กร")
SUPABASE_URL = st.sidebar.text_input("ลิงก์โปรเจกต์ Supabase", "https://your-project.supabase.co").strip()
SUPABASE_KEY = st.sidebar.text_input("รหัสผ่าน API (Anon Key)", "your-anon-key", type="password").strip()

# ==========================================
# 🧭 ระบบปุ่มกดเปลี่ยนหน้าแยก (Navigation / Router System)
# ==========================================
st.sidebar.markdown("---")
st.sidebar.markdown("### 🗺️ เมนูนำทางเลือกหน้าจอ")

# ใช้ Session State เพื่อจำว่าตอนนี้อยู่หน้าไหน
if "current_page" not in st.session_state:
    st.session_state.current_page = "🏠 หน้าแรก & ตั้งค่าสายพันธุ์"

# สร้างปุ่มกดเลือกหน้าใน Sidebar
page = st.sidebar.radio(
    "ไปที่หน้าจอ:",
    ["🏠 หน้าแรก & ตั้งค่าสายพันธุ์", "🧠 คำนวณสูตรอาหาร (AI Optimizer)", "📦 แผนการจัดซื้อวัตถุดิบ", "📈 สถิติผลผลิต & บัญชีฟาร์ม"],
    key="navigation_radio_v8"
)
st.session_state.current_page = page

# ==========================================
# 📋 2. ฐานข้อมูลส่วนประกอบและโภชนาการมาตรฐาน (Database Initialization)
# ==========================================
STAGE_NUTRITION_TARGETS = {
    "starter": {"name": "ลูกไก่ไข่ 0 - 6 สัปดาห์ (Starter)", "protein": 20.0, "me": 2900.0, "calcium": 1.00, "phos": 0.45, "amino": 0.42, "fiber": 4.0, "fat": 3.5},
    "grower": {"name": "ไก่รุ่นไข่ 6 - 16 สัปดาห์ (Grower)", "protein": 16.0, "me": 2750.0, "calcium": 0.90, "phos": 0.40, "amino": 0.32, "fiber": 4.5, "fat": 3.0},
    "laying": {"name": "ไก่ไข่ระยะให้ผลผลิต 16 สัปดาห์ขึ้นไป (Laying)", "protein": 17.5, "me": 2750.0, "calcium": 4.10, "phos": 0.42, "amino": 0.38, "fiber": 4.0, "fat": 3.5}
}

if "ingredient_data" not in st.session_state:
    st.session_state.ingredient_data = {
        "ข้าวโพดบด": {"price": 13.5, "protein": 8.5, "me": 3300.0, "calcium": 0.02, "phos": 0.25, "amino": 0.18, "moisture": 12.0, "fiber": 2.2, "fat": 3.8, "tox_risk": 3, "min_limit": 20.0, "max_limit": 70.0},
        "กากถั่วเหลือง": {"price": 18.5, "protein": 44.0, "me": 2420.0, "calcium": 0.25, "phos": 0.60, "amino": 0.65, "moisture": 11.5, "fiber": 5.5, "fat": 1.5, "tox_risk": 1, "min_limit": 5.0, "max_limit": 40.0},
        "รำละเอียด": {"price": 11.0, "protein": 12.0, "me": 2400.0, "calcium": 0.05, "phos": 1.35, "amino": 0.22, "moisture": 10.5, "fiber": 12.0, "fat": 13.0, "tox_risk": 3, "min_limit": 0.0, "max_limit": 30.0},
        "ปลาป่น": {"price": 32.0, "protein": 60.0, "me": 2850.0, "calcium": 5.00, "phos": 3.00, "amino": 0.95, "moisture": 10.0, "fiber": 1.0, "fat": 8.0, "tox_risk": 1, "min_limit": 0.0, "max_limit": 15.0},
        "เปลือกหอยบด": {"price": 4.0, "protein": 0.0, "me": 0.0, "calcium": 38.00, "phos": 0.04, "amino": 0.00, "moisture": 0.5, "fiber": 0.0, "fat": 0.0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 12.0},
        "ไดแคลเซียมฟอสเฟต": {"price": 28.0, "protein": 0.0, "me": 0.0, "calcium": 21.00, "phos": 18.00, "amino": 0.00, "moisture": 1.0, "fiber": 0.0, "fat": 0.0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 5.0},
        "กรดอะมิโนสังเคราะห์": {"price": 95.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "amino": 99.00, "moisture": 0.2, "fiber": 0.0, "fat": 0.0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 2.0}
    }

BREED_PROFILES = {
    "1. กลุ่มไฮบริด / ลูกผสมพาณิชย์ (Commercial Hybrids)": {
        "Isa Brown": {"name": "ไอซ่า บราวน์ (Isa Brown)", "egg_color": "🤎 น้ำตาลเข้ม", "bg_color": "#b45309", "text_color": "#ffffff", "default_feed": 115, "desc": "เบอร์ 1 ในไทย ไข่ดก 300-320 ฟอง/ปี เปลือกหนา ทนร้อนดีเยี่ยม"},
        "Hy-Line Brown": {"name": "ไฮไลน์ บราวน์ (Hy-Line Brown)", "egg_color": "🤎 น้ำตาลนวล", "bg_color": "#d97706", "text_color": "#ffffff", "default_feed": 110, "desc": "กินน้อยแต่ไข่นิ่ง อัตราผลิตสม่ำเสมอยาวนาน เปลือกแข็งแรงแตกยาก"},
        "Hisex Brown": {"name": "ไฮ-เซ็กส์ บราวน์ (Hisex Brown)", "egg_color": "🤎 น้ำตาลสว่าง", "bg_color": "#c2410c", "text_color": "#ffffff", "default_feed": 113, "desc": "สายพันธุ์อึด ให้ผลผลิตสูงช่วงต้นของการไข่เร็วมาก นิยมไม่แพ้สองพันธุ์แรก"}
    },
    "2. กลุ่มสายพันธุ์แท้ (Pure Breeds)": {
        "Rhode Island Red": {"name": "โรดไอแลนด์เรด (Rhode Island Red)", "egg_color": "🤎 น้ำตาลอ่อน", "bg_color": "#8b4513", "text_color": "#ffffff", "default_feed": 125, "desc": "ไก่สีน้ำตาลแดง ขนเงางาม อึด ทนโรค ทนแดด ทนฝน เหมาะสำหรับเลี้ยงปล่อยธรรมชาติ"},
        "White Leghorn": {"name": "เลกฮอร์นขาว (White Leghorn)", "egg_color": "🤍 ขาวสะอาด", "bg_color": "#cbd5e1", "text_color": "#1e293b", "default_feed": 105, "desc": "ตัวเล็ก ขนขาว ปราดเปรียว บินเก่ง ให้ไข่เปลือกสีขาวสะอาด ดกมาก"}
    }
}

LIFECYCLE_FEED_BUDGET = {"starter": 1.2, "grower": 2.8, "laying": 48.0}

# ป้องกันข้อมูลหายระหว่างสลับหน้าด้วยการล็อกตัวแปรไว้กับ Session State
if "selected_group" not in st.session_state: st.session_state.selected_group = list(BREED_PROFILES.keys())[0]
if "selected_breed_key" not in st.session_state: st.session_state.selected_breed_key = list(BREED_PROFILES[st.session_state.selected_group].keys())[0]
if "current_key" not in st.session_state: st.session_state.current_key = "laying"
if "weather_env" not in st.session_state: st.session_state.weather_env = "🌡️ อากาศปกติ (25-32°C)"
if "chicken_count" not in st.session_state: st.session_state.chicken_count = 1000
if "optimized_weights" not in st.session_state:
    st.session_state.optimized_weights = {"ข้าวโพดบด": 52.0, "กากถั่วเหลือง": 24.0, "รำละเอียด": 14.0, "ปลาป่น": 5.0, "เปลือกหอยบด": 4.2, "ไดแคลเซียมฟอสเฟต": 0.6, "กรดอะมิโนสังเคราะห์": 0.2}
if "use_phytase" not in st.session_state: st.session_state.use_phytase = True

# ดึงข้อมูลสายพันธุ์ที่เลือกอยู่ปัจจุบันมาแสดงผลด้านบนสุด
breed_info = BREED_PROFILES[st.session_state.selected_group][st.session_state.selected_breed_key]

# ฟังก์ชันส่วนกลางสำหรับคำนวณคุณค่าทางโภชนาการและต้นทุน (Global Calculation Engine)
def calculate_current_formulation():
    nut_calc = {"protein": 0.0, "me": 0.0, "calcium": 0.0, "phos": 0.0, "amino": 0.0, "fiber": 0.0, "fat": 0.0}
    cost = 0.0
    moisture = 0.0
    risk = 0.0
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
# 🏠 หน้าที่ 1: หน้าแรก & ตั้งค่าสายพันธุ์
# ==========================================
if st.session_state.current_page == "🏠 หน้าแรก & ตั้งค่าสายพันธุ์":
    st.markdown("## 🏠 หน้าแรก: ข้อมูลสายพันธุ์และสภาวะแวดล้อมฟาร์ม")
    
    c_group, c_breed = st.columns(2)
    with c_group:
        st.session_state.selected_group = st.selectbox("เลือกกลุ่มสายพันธุ์ไก่ไข่:", list(BREED_PROFILES.keys()), index=list(BREED_PROFILES.keys()).index(st.session_state.selected_group))
    with c_breed:
        breed_options = BREED_PROFILES[st.session_state.selected_group]
        default_index = list(breed_options.keys()).index(st.session_state.selected_breed_key) if st.session_state.selected_breed_key in breed_options else 0
        st.session_state.selected_breed_key = st.selectbox("สายพันธุ์หลักในโรงเรือน:", options=list(breed_options.keys()), index=default_index, format_func=lambda x: breed_options[x]["name"])
    
    breed_info = breed_options[st.session_state.selected_breed_key]
    cloud_status_text = "พร้อมใช้งาน / เชื่อมต่อระบบจริง (Online)" if "your-project" not in SUPABASE_URL and SUPABASE_KEY != "your-anon-key" else "โหมดทำงานแบบออฟไลน์ชั่วคราว (Offline Mode)"
    
    st.markdown(f"""
    <div style='background-color:{breed_info['bg_color']}; padding:20px; border-radius:10px; color:{breed_info['text_color']}; margin-bottom:15px;'>
        <h3>🧬 สายพันธุ์ปัจจุบัน: {breed_info['name']}</h3>
        <b>🎨 สีเปลือกไข่:</b> {breed_info['egg_color']} | <b>🥣 อัตรากินอาหารเฉลี่ย:</b> {breed_info['default_feed']} กรัม/วัน/ตัว <br>
        <p style='margin: 10px 0;'><i>ℹ️ {breed_info['desc']}</i></p>
        <small style='font-weight: bold; opacity: 0.8;'>📊 สถานะคลาวด์: {cloud_status_text}</small>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### ⛅ การจัดการอายุและสภาพแวดล้อม")
    c_age, c_weather = st.columns(2)
    with c_age:
        st.session_state.current_key = st.selectbox("เลือกช่วงอายุ/โปรไฟล์ของไก่:", options=list(STAGE_NUTRITION_TARGETS.keys()), index=list(STAGE_NUTRITION_TARGETS.keys()).index(st.session_state.current_key), format_func=lambda x: STAGE_NUTRITION_TARGETS[x]["name"])
    with c_weather:
        weather_list = ["🌡️ อากาศปกติ (25-32°C)", "🔥 อากาศร้อนจัด (> 32°C)", "❄️ อากาศหนาว (< 25°C)"]
        st.session_state.weather_env = st.radio("สภาพอากาศและอุณหภูมิในโรงเรือนวันนี้:", weather_list, index=weather_list.index(st.session_state.weather_env), horizontal=True)

    st.markdown("### 💧 ระบบคำนวณปริมาณน้ำดื่มประจำวัน (Water Calculator)")
    st.session_state.chicken_count = st.number_input("จำนวนไก่ในฟาร์มทั้งหมด (ตัว):", min_value=1, value=st.session_state.chicken_count, step=100)
    base_water = (breed_info['default_feed'] / 1000.0) * 2.2 if st.session_state.current_key == "laying" else 0.15
    calc_water = st.session_state.chicken_count * base_water
    if "ร้อนจัด" in st.session_state.weather_env:
        calc_water *= 1.20
        st.error("🔥 อากาศร้อนจัด! แนะนำให้เตรียมน้ำดื่มเพิ่มขึ้นอีก 20% เพื่อแก้ปัญหาความร้อน (Heat Stress)")
    st.metric("ปริมาณน้ำที่ฝูงไก่ต้องกินต่อวันรวม", f"{calc_water:,.1f} ลิตร (Liters)")

# ==========================================
# 🧠 หน้าที่ 2: คำนวณสูตรอาหาร (AI Optimizer)
# ==========================================
elif st.session_state.current_page == "🧠 คำนวณสูตรอาหาร (AI Optimizer)":
    st.markdown("## 🧠 ห้องปฏิบัติการสูตรอาหาร & ปัญญาประดิษฐ์")
    
    target = STAGE_NUTRITION_TARGETS[st.session_state.current_key]
    density_factor = 1.08 if "ร้อนจัด" in st.session_state.weather_env else (0.95 if "หนาว" in st.session_state.weather_env else 1.0)
    
    adjusted_target = {
        "protein": target["protein"] * density_factor, "me": target["me"],
        "calcium": target["calcium"] * density_factor, "phos": target["phos"] * density_factor,
        "amino": target["amino"] * density_factor, "fiber": target.get("fiber", 4.0), "fat": target.get("fat", 3.5)
    }

    with st.expander("💰 ⚙️ อัปเดตราคาวัตถุดิบหน้าฟาร์มปัจจุบัน (บาท/กิโลกรัม)"):
        cols = st.columns(len(st.session_state.ingredient_data.keys()))
        for idx, name in enumerate(st.session_state.ingredient_data.keys()):
            with cols[idx]:
                st.session_state.ingredient_data[name]["price"] = st.number_input(f"{name}", min_value=0.0, value=float(st.session_state.ingredient_data[name]["price"]), step=0.5, key=f"p_{name}")

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
        prob += pulp.lpSum([ingredient_vars[name] * (st.session_state.ingredient_data[name]["amino"] / 100.0) for name in st.session_state.ingredient_data.keys()]) >= adjusted_target["amino"]
        
        status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
        if pulp.LpStatus[status] == "Optimal":
            for name in st.session_state.ingredient_data.keys():
                st.session_state.optimized_weights[name] = round(ingredient_vars[name].varValue, 1)
            st.success("🎉 AI ประมวลผลสำเร็จ ค้นพบสูตรอาหารที่ประหยัดเงินที่สุดในท้องตลาดปัจจุบันแล้ว!")
            st.rerun()
        else:
            st.error("❌ ขีดจำกัดสารอาหารแน่นเกินไป วัตถุดิบปัจจุบันไม่พอผสมให้ครบคุณค่าได้")

    st.markdown("---")
    creator_left, creator_right = st.columns(2, gap="large")
    
    with creator_left:
        st.markdown("#### 🔧 1. สไลเดอร์ปรับสัดส่วนผสมด้วยมือ / เพิ่มวัตถุดิบเสริม")
        with st.expander("➕ เพิ่มสารอาหารเสริม/วัตถุดิบตัวใหม่เข้าระบบ"):
            with st.form("add_ing_form_v8"):
                new_name = st.text_input("ชื่อวัตถุดิบใหม่:")
                n_p = st.number_input("ราคา (บาท/กก.):", value=15.0)
                n_pro = st.number_input("โปรตีน (%):", value=15.0)
                n_me = st.number_input("พลังงาน (kcal/kg):", value=2000.0)
                if st.form_submit_button("บันทึกวัตถุดิบ"):
                    st.session_state.ingredient_data[new_name] = {"price": n_p, "protein": n_pro, "me": n_me, "calcium": 1.0, "phos": 0.4, "amino": 0.3, "moisture": 10.0, "tox_risk": 1, "min_limit": 0.0, "max_limit": 50.0}
                    st.session_state.optimized_weights[new_name] = 0.0
                    st.rerun()

        user_weights = {}
        for name in st.session_state.ingredient_data.keys():
            val = float(st.session_state.optimized_weights.get(name, 0.0))
            user_weights[name] = st.slider(f"{name} (%)", 0.0, 100.0, val, step=0.1, key=f"form_sl_{name}")
        st.session_state.optimized_weights = user_weights

        total_sum = sum(user_weights.values())
        st.markdown(f"**🔢 น้ำหนักรวมสูตรตอนนี้:** `{total_sum:.1f}%` (ต้องให้เท่ากับ 100%)")
        if not (99.9 <= total_sum <= 100.1):
            st.warning("⚠️ สัดส่วนรวมยังไม่ครบ 100% อาหารจะไม่เต็มสูตรตามการเติบโต")

    with creator_right:
        st.markdown("#### 🩺 2. หน้าจอตรวจสอบระดับคุณค่าสารอาหารเรียลไทม์")
        
        nutrient_display = [
            ("🥩 โปรตีนรวม (Crude Protein)", "protein", "%"),
            ("⚡ พลังงานใช้ประโยชน์ได้ (ME)", "me", "kcal/kg"),
            ("Bone แคลเซียม (Calcium)", "calcium", "%"),
            ("🧪 ฟอสฟอรัสที่เป็นประโยชน์ (Phosphorus)", "phos", "%"),
            ("🧬 กรดอะมิโนจำเป็นรวม (Amino Acids)", "amino", "%")
        ]
        
        for label, key_name, unit in nutrient_display:
            cur = current_nutrition[key_name]
            req = adjusted_target[key_name]
            st.write(f"**{label}**: {cur:.2f} / {req:.2f} {unit}")
            st.progress(min(max(cur / req, 0.0), 1.0) if req > 0 else 0.0)
            
        st.markdown("---")
        if total_moisture > 12.0:
            st.markdown(f"💧 **ความชื้นสะสม:** <span style='color:red;'>{total_moisture:.1f}% 🔴 เสี่ยงเกิดราในอาหาร</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"💧 **ความชื้นสะสม:** <span style='color:green;'>{total_moisture:.1f}% 🟢 แห้งดี ปลอดภัย</span>", unsafe_allow_html=True)
            
        st.metric("💰 ต้นทุนสูตรผสมอาหารปัจจุบันของคุณ", f"{current_formula_cost:.2f} บาท / กิโลกรัม")

# ==========================================
# 📦 หน้าที่ 3: แผนการจัดซื้อวัตถุดิบ
# ==========================================
elif st.session_state.current_page == "📦 แผนการจัดซื้อวัตถุดิบ":
    st.markdown("## 📦 แผนจัดซื้อวัตถุดิบอาหารสัตว์และควบคุมความเสี่ยง")
    
    total_feed_needed_kg = st.session_state.chicken_count * LIFECYCLE_FEED_BUDGET[st.session_state.current_key]
    st.info(f"📊 ปริมาณอาหารรวมทั้งหมดที่ฟาร์มคุณต้องเตรียมสำรองในระยะนี้: **{total_feed_needed_kg/1000.0:,.2f} ตัน** (ประเมินจากฝูงไก่ {st.session_state.chicken_count:,} ตัว)")
    
    budget_data = []
    for name, weight in st.session_state.optimized_weights.items():
        w_kg = (weight / 100.0) * total_feed_needed_kg
        if w_kg > 0:
            p_unit = st.session_state.ingredient_data[name]["price"]
            budget_data.append({
                "วัตถุดิบวัตถุ": name,
                "สัดส่วนในสูตร (%)": f"{weight}%",
                "ปริมาณรวมที่ต้องสั่งเข้าคลัง (กก.)": round(w_kg, 1),
                "งบประมาณจัดซื้อโดยประมาณ (บาท)": round(w_kg * p_unit, 2)
            })
            
    df_budget = pd.DataFrame(budget_data)
    if not df_budget.empty:
        st.dataframe(df_budget, use_container_width=True, hide_index=True)
        csv = df_budget.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 ดาวน์โหลดใบจัดซื้อวัตถุดิบอาหารสัตว์ (Download PO CSV)", data=csv, file_name="ใบสั่งซื้ออาหารสัตว์_SmartLayer.csv", mime="text/csv")
    else:
        st.info("💡 สัดส่วนอาหารยังเป็น 0% กรุณาไปคำนวณและตั้งค่าสัดส่วนสูตรที่หน้า AI Optimizer ก่อน")

    st.markdown("---")
    st.markdown("#### 🛡️ การบริหารจัดการความปลอดภัยทางชีวภาพ (Biosecurity Control)")
    if total_risk_score >= 2.0:
        st.error(f"⚠️ ดัชนีสารพิษเชื้อรารวมอยู่ที่ {total_risk_score:.2f} (เสี่ยงสูง) แนะนำให้สั่งสารจับสารพิษเชื้อรา (Toxin Binder) ผสมเพิ่มจำนวน {2.0 * (total_feed_needed_kg/1000.0):,.1f} กก. เข้าไปในเครื่องผสมอาหารด้วย")
    else:
        st.success("🟢 วัตถุดิบในสูตรมีความปลอดภัยจากสารพิษเชื้อราสูง จัดเก็บได้ตามเกณฑ์มาตรฐาน")

# ==========================================
# 📈 หน้าที่ 4: สถิติผลผลิต & บัญชีฟาร์ม
# ==========================================
elif st.session_state.current_page == "📈 สถิติผลผลิต & บัญชีฟาร์ม":
    st.markdown("## 📈 สมุดจดบันทึกสถิติและวิเคราะห์ผลกำไรฟาร์ม")
    
    if "tracker_data" not in st.session_state:
        st.session_state.tracker_data = pd.DataFrame([
            {"วันที่": "01/06", "สูตรอาหาร": "สูตรเดิม", "อัตราการไข่ (%)": 82.0, "อัตราไข่บุบแตก (%)": 4.5, "น้ำหนักไข่รวม (กก.)": 52.0, "ตาย/คัดทิ้ง (ตัว)": 0, "กำไรสุทธิวันนี้ (บาท)": 420.0},
            {"วันที่": "02/06", "สูตรอาหาร": "สูตรเดิม", "อัตราการไข่ (%)": 81.5, "อัตราไข่บุบแตก (%)": 5.0, "น้ำหนักไข่รวม (กก.)": 51.5, "ตาย/คัดทิ้ง (ตัว)": 1, "กำไรสุทธิวันนี้ (บาท)": 395.0},
            {"วันที่": "03/06", "สูตรอาหาร": "สูตร AI แนะนำ", "อัตราการไข่ (%)": 84.0, "อัตราไข่บุบแตก (%)": 2.1, "น้ำหนักไข่รวม (กก.)": 53.8, "ตาย/คัดทิ้ง (ตัว)": 0, "กำไรสุทธิวันนี้ (บาท)": 610.0},
        ])
        
    df_track = st.session_state.tracker_data.copy()
    
    # คำนวณปริมาณอาหารที่กินต่อวันเพื่อคำนวณ FCR
    daily_feed_consumed_kg = (st.session_state.chicken_count * breed_info['default_feed']) / 1000.0
    df_track["FCR"] = (daily_feed_consumed_kg / df_track["น้ำหนักไข่รวม (กก.)"]).round(2)
    
    avg_lay = df_track["อัตราการไข่ (%)"].mean()
    total_profit_accum = df_track["กำไรสุทธิวันนี้ (บาท)"].sum()
    avg_fcr = df_track["FCR"].mean()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("🥚 อัตราการให้ไข่เฉลี่ย", f"{avg_lay:.1f} %")
    m2.metric("🥣 ประสิทธิภาพอาหาร (FCR เฉลี่ย)", f"{avg_fcr:.2f}")
    m3.metric("💵 กำไรสุทธิรวมสะสมรอบนี้", f"{total_profit_accum:,.1f} บาท")
    
    st.markdown("---")
    track_col1, track_col2 = st.columns([4, 6], gap="large")
    
    with track_col1:
        st.markdown("##### 📝 จดบันทึกผลผลิตประจำวัน")
        with st.form("daily_form_ledger"):
            in_date = st.text_input("วันที่บันทึก (เช่น 05/06):", value=datetime.now().strftime("%d/%m"))
            lay_r = st.number_input("อัตราการไข่วันนี้ (%):", value=85.0)
            crack_r = st.number_input("อัตราไข่แตกเสียหาย (%):", value=1.5)
            egg_w = st.number_input("น้ำหนักไข่รวมหน้าแผง (กก.):", value=54.0)
            dead = st.number_input("ไก่ตาย/คัดออกวันนี้ (ตัว):", value=0, step=1)
            
            st.caption(f"💡 ระบบคำนวณต้นทุนค่าอาหารวันนี้ให้อัตโนมัติ: {daily_feed_consumed_kg * current_formula_cost:,.1f} บาท")
            profit_today = st.number_input("คำนวณหรือกรอกกำไรสุทธิวันนี้ (บาท):", value=650.0)
            
            if st.form_submit_button("💾 กดบันทึกข้อมูลเข้าฐานระบบ"):
                new_row = {
                    "วันที่": in_date, "สูตรอาหาร": "สูตรปัจจุบัน", 
                    "อัตราการไข่ (%)": lay_r, "อัตราไข่บุบแตก (%)": crack_r, 
                    "น้ำหนักไข่รวม (กก.)": egg_w, "ตาย/คัดทิ้ง (ตัว)": dead, 
                    "กำไรสุทธิวันนี้ (บาท)": profit_today
                }
                st.session_state.tracker_data = pd.concat([st.session_state.tracker_data, pd.DataFrame([new_row])], ignore_index=True)
                st.success("บันทึกสถิติรายวันเสร็จสิ้น!")
                st.rerun()
                
    with track_col2:
        st.markdown("##### 📊 กราฟวิเคราะห์แนวโน้มอัตราผลิตไข่")
        fig_prod = go.Figure()
        fig_prod.add_trace(go.Scatter(x=df_track["วันที่"], y=df_track["อัตราการไข่ (%)"], name="อัตราการไข่ (%)", line=dict(color='#22c55e', width=3)))
        fig_prod.add_trace(go.Bar(x=df_track["วันที่"], y=df_track["อัตราไข่บุบแตก (%)"], name="ไข่แตกเสียหาย (%)", marker_color='#ef4444', opacity=0.4))
        fig_prod.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=280)
        st.plotly_chart(fig_prod, use_container_width=True)
        
    st.markdown("##### 📄 ตารางบัญชีและสถิติประวัติย้อนหลัง (Historical Ledger)")
    st.dataframe(df_track, use_container_width=True, hide_index=True)

# ==========================================
# 🏁 10. ส่วนท้ายของแอปพลิเคชัน (Enterprise Footer)
# ==========================================
st.markdown("---")
st.markdown(f"<div style='text-align: center; color: #64748b; font-size: 0.8em;'>© 2026 Smart Layer Feed v8.5 Enterprise | สลับหน้าไร้รอยต่อผ่านสถาปัตยกรรม st.session_state โค้ดชุดสมบูรณ์</div>", unsafe_allow_html=True)
