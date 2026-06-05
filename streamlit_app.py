import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pulp
import requests
from io import BytesIO
from datetime import datetime

# ==========================================
# 🔱 1. ตั้งค่าคอนฟิกแอปพลิเคชันและหน้าจอ (Application Configuration)
# ==========================================
st.set_page_config(page_title="Smart Layer Feed - ระบบคำนวณอาหารไก่ไข่อัจฉริยะ", layout="wide")

# เมนูด้านข้างสำหรับการเชื่อมต่อระบบคลาวด์ (Sidebar for Cloud Connection)
st.sidebar.markdown("### ☁️ การเชื่อมต่อคลาวด์ระดับองค์กร (Enterprise Cloud Connection)")
SUPABASE_URL = st.sidebar.text_input("ลิงก์โปรเจกต์ Supabase (Supabase URL)", "https://your-project.supabase.co").strip()
SUPABASE_KEY = st.sidebar.text_input("รหัสผ่าน API (Supabase Anon Key)", "your-anon-key", type="password").strip()

# ==========================================
# 📋 2. ฐานข้อมูลส่วนประกอบและโภชนาการมาตรฐาน (Ingredient & Nutrition Database)
# ==========================================

STAGE_NUTRITION_TARGETS = {
    "starter": {"name": "ลูกไก่ไข่ 0 - 6 สัปดาห์ (Starter)", "protein": 20.0, "me": 2900.0, "calcium": 1.00, "phos": 0.45, "amino": 0.42, "fiber": 4.0, "fat": 3.5},
    "grower": {"name": "ไก่รุ่นไข่ 6 - 16 สัปดาห์ (Grower)", "protein": 16.0, "me": 2750.0, "calcium": 0.90, "phos": 0.40, "amino": 0.32, "fiber": 4.5, "fat": 3.0},
    "laying": {"name": "ไก่ไข่ระยะให้ผลผลิต 16 สัปดาห์ขึ้นไป (Laying)", "protein": 17.5, "me": 2750.0, "calcium": 4.10, "phos": 0.42, "amino": 0.38, "fiber": 4.0, "fat": 3.5}
}

# ฐานข้อมูลวัตถุดิบเริ่มต้น (Default Ingredients)
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
        "Hisex Brown": {"name": "ไฮ-เซ็กส์ บราวน์ (Hisex Brown)", "egg_color": "🤎 น้ำตาลสว่าง", "bg_color": "#c2410c", "text_color": "#ffffff", "default_feed": 113, "desc": "สายพันธุ์อึด ให้ผลผลิตสูงช่วงต้นของการไข่เร็วมาก นิยมไม่แพ้สองพันธุ์แรก"},
        "Bovans Brown": {"name": "โบบัน บราวน์ (Bovans Brown)", "egg_color": "🤎 น้ำตาลทอง", "bg_color": "#a16207", "text_color": "#ffffff", "default_feed": 112, "desc": "อารมณ์ดี ไม่เครียดง่าย โครงสร้างร่างกายแข็งแรง ทนต่อสิ่งแวดล้อมได้ดี"},
        "Novogen Brown": {"name": "โนโวเจน บราวน์ (Novogen Brown)", "egg_color": "🤎 น้ำตาลคลาสสิก", "bg_color": "#9a3412", "text_color": "#ffffff", "default_feed": 111, "desc": "สายพันธุ์ฝรั่งเศส เด่นเรื่องคุณภาพภายในของไข่ ไข่แดงนูนสวย ไข่ขาวข้น"},
        "Lohmann Brown": {"name": "โลห์แมน บราวน์ (Lohmann Brown)", "egg_color": "🤎 น้ำตาลสม่ำเสมอ", "bg_color": "#78350f", "text_color": "#ffffff", "default_feed": 114, "desc": "สายพันธุ์เยอรมัน ปรับตัวกับกรงตับและระบบปิดได้ดีเยี่ยม ไข่ฟองใหญ่เสมอกัน"}
    },
    "2. กลุ่มสายพันธุ์แท้ (Pure Breeds)": {
        "Rhode Island Red": {"name": "โรดไอแลนด์เรด (Rhode Island Red)", "egg_color": "🤎 น้ำตาลอ่อน", "bg_color": "#8b4513", "text_color": "#ffffff", "default_feed": 125, "desc": "ไก่สีน้ำตาลแดง ขนเงางาม อึด ทนโรค ทนแดด ทนฝน เหมาะสำหรับเลี้ยงปล่อยธรรมชาติ (Free-range)"},
        "White Leghorn": {"name": "เลกฮอร์นขาว (White Leghorn)", "egg_color": "🤍 ขาวสะอาด", "bg_color": "#cbd5e1", "text_color": "#1e293b", "default_feed": 105, "desc": "ตัวเล็ก ขนขาว ปราดเปรียว บินเก่ง ให้ไข่เปลือกสีขาวสะอาด ดกมากเกือบเท่าไก่ไฮบริด"},
        "Barred Plymouth Rock": {"name": "บาร์พลีมัทร็อค (Barred Plymouth Rock)", "egg_color": "🤎 น้ำตาลครีม", "bg_color": "#64748b", "text_color": "#ffffff", "default_feed": 128, "desc": "ไก่ลายเสือตัวใหญ่ แข็งแรง ทนทาน นอกจากไข่ดีแล้ว เนื้อยังอร่อยด้วย (กึ่งเนื้อกึ่งไข่)"},
        "Australorp": {"name": "ออสตราลอป (Australorp)", "egg_color": "🤎 น้ำตาลครีมนวล", "bg_color": "#0f172a", "text_color": "#ffffff", "default_feed": 120, "desc": "ไก่ดำเหลือบเขียวมะกอก เชื่องมาก ตัวอวบอ้วนทนทานสูง ผลผลิตไข่สม่ำเสมอ"},
        "Sussex": {"name": "ซัสเซกส์ (Sussex)", "egg_color": "🩷 ชมพูอมน้ำตาลอ่อน", "bg_color": "#f1f5f9", "text_color": "#0f172a", "default_feed": 118, "desc": "โดยเฉพาะพันธุ์ Light Sussex (ตัวขาวคอดำ) น่ารัก นิสัยดี ให้ไข่สีสวยงามนุ่มนวล"}
    },
    "3. กลุ่มสายพันธุ์พัฒนาของไทย (Thai Developed Breeds)": {
        "DLD Layer": {"name": "ไก่ไข่กรมปศุสัตว์ (DLD Layer)", "egg_color": "🤎 น้ำตาล", "bg_color": "#047857", "text_color": "#ffffff", "default_feed": 110, "desc": "ลูกผสมระหว่างโรดไอแลนด์เรดกับบาร์พลีมัทร็อค ทนโรคระบาดและอากาศร้อนชื้นในไทยดีมาก"},
        "SUT Layer": {"name": "ไก่ไข่ มทส. (SUT Layer)", "egg_color": "🤎 น้ำตาลนวล", "bg_color": "#065f46", "text_color": "#ffffff", "default_feed": 100, "desc": "ตัวเล็กกินอาหารน้อย พัฒนาให้ไข่ดก เหมาะกับการเลี้ยงปล่อยในสวนปาล์ม สวนยาง หรือหลังบ้าน"},
        "KU Layer": {"name": "ไก่ไข่ มก. (KU Layer)", "egg_color": "🤎 น้ำตาลหนา", "bg_color": "#0f766e", "text_color": "#ffffff", "default_feed": 112, "desc": "โครงสร้างร่างกายแข็งแรง เลี้ยงง่าย ให้ไข่ฟองโต เปลือกหนา เหมาะกับเกษตรกรรายย่อย"}
    },
    "4. กลุ่มไข่สีแฟนซี (Designer / Colored Egg Layers)": {
        "Araucana": {"name": "อารอคาน่า (Araucana / Ameraucana)", "egg_color": "🩵 ฟ้า/เขียวพาสเทล", "bg_color": "#0ea5e9", "text_color": "#ffffff", "default_feed": 110, "desc": "เด่นที่สุดในกลุ่มนี้ มีเครา ขนฟู ให้ไข่เปลือกสีฟ้าพาสเทล ตลาดไข่พรีเมียม/อินทรีย์ต้องการสูง"},
        "Marans": {"name": "มารันส์ (Marans)", "egg_color": "🍫 ช็อกโกแลตเข้ม", "bg_color": "#451a03", "text_color": "#ffffff", "default_feed": 120, "desc": "ไก่ฝรั่งเศส ขึ้นชื่อเรื่องให้ไข่เปลือกสีช็อกโกแลตเข้มสวยงาม เนื้อผิวเงาและราคาแพงมาก"},
        "Olive Egger": {"name": "โอลิฟ เอ็กเกอร์ (Olive Egger)", "egg_color": "💚 เขียวมะกอก", "bg_color": "#3f6212", "text_color": "#ffffff", "default_feed": 115, "desc": "ลูกผสมข้ามสายพันธุ์ที่ทำให้ได้ไข่เปลือกสีเขียวมะกอก เป็นที่นิยมสูงในกลุ่มผู้บริโภคสายโมเดิร์น"}
    }
}

LIFECYCLE_FEED_BUDGET = {"starter": 1.2, "grower": 2.8, "laying": 48.0}

if "optimized_weights" not in st.session_state:
    st.session_state.optimized_weights = {"ข้าวโพดบด": 52.0, "กากถั่วเหลือง": 24.0, "รำละเอียด": 14.0, "ปลาป่น": 5.0, "เปลือกหอยบด": 4.2, "ไดแคลเซียมฟอสเฟต": 0.6, "กรดอะมิโนสังเคราะห์": 0.2}

# ==========================================
# 🏛️ 3. ส่วนหัวของแอปและข้อมูลสายพันธุ์ (App Header & Breed Profiles)
# ==========================================
st.title("🔱 Smart Layer Feed — ระบบคำนวณโภชนาการอาหารไก่ไข่อัจฉริยะ")
st.caption("ระบบคำนวณเชิงลึกระดับอุตสาหกรรมด้วยกลไกการค้นหาจุดคุ้มทุนเชิงเส้น (PuLP Linear Programming Engine)")

st.markdown("### 🧬 0. ข้อมูลสายพันธุ์และสถานะการเชื่อมต่อคลาวด์ (Breed Profiles & Cloud Connection Status)")
c_group, c_breed = st.columns(2)
with c_group:
    selected_group = st.selectbox("เลือกกลุ่มสายพันธุ์ไก่ไข่ (Select Breed Group):", list(BREED_PROFILES.keys()))

with c_breed:
    breed_options = BREED_PROFILES[selected_group]
    selected_breed_key = st.selectbox(
        "สายพันธุ์หลักในโรงเรือน (Main Breed in House):", 
        options=list(breed_options.keys()),
        format_func=lambda x: breed_options[x]["name"]
    )

breed_info = breed_options[selected_breed_key]

cloud_status_text = "พร้อมใช้งาน / เชื่อมต่อระบบจริง (Online)" if "your-project" not in SUPABASE_URL and SUPABASE_KEY != "your-anon-key" else "โหมดทำงานแบบออฟไลน์ชั่วคราว (Offline Mode)"
st.markdown(f"""
<div style='background-color:{breed_info['bg_color']}; padding:15px; border-radius:10px; color:{breed_info['text_color']}; margin-bottom:15px; border: 1px solid rgba(0,0,0,0.1);'>
    <b>🧬 สายพันธุ์ปัจจุบัน (Current Breed): {breed_info['name']}</b> | 🎨 สีเปลือกไข่ (Eggshell Color): {breed_info['egg_color']} | 🥣 อัตรากินอาหาร (Feed Intake): {breed_info['default_feed']} กรัม/วัน (g/day) <br>
    <p style='margin: 5px 0 0 0; font-size: 0.9em; opacity: 0.95;'>ℹ️ <i>{breed_info['desc']}</i></p>
    <small style='display:block; margin-top:5px; font-weight: bold; opacity: 0.8;'>📊 สถานะระบบคลาวด์ Supabase (Supabase Cloud Status): {cloud_status_text}</small>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 💰 แผงควบคุมและอัปเดตราคาวัตถุดิบหน้าฟาร์ม (Dynamic Price Dashboard)
# ==========================================
with st.expander("💰 🛠️ แผงควบคุมและอัปเดตราคาวัตถุดิบหน้าฟาร์ม (Dynamic Price Control Dashboard)"):
    st.caption("ปรับเปลี่ยนราคาที่นี่เพื่อใช้คำนวณต้นทุนจริงและให้ AI Optimizer ประมวลผลจุดคุ้มทุนใหม่")
    cols = st.columns(len(st.session_state.ingredient_data.keys()))
    for idx, name in enumerate(st.session_state.ingredient_data.keys()):
        with cols[idx]:
            new_price = st.number_input(f"{name} (บาท/กก.)", min_value=0.0, value=float(st.session_state.ingredient_data[name]["price"]), step=0.5, key=f"p_{name}")
            st.session_state.ingredient_data[name]["price"] = new_price

st.markdown("---")

# ==========================================
# ⛅ 4. ระบบปรับสมดุลตามสภาพแวดล้อมและช่วงอายุ (Environmental & Age Balance System)
# ==========================================
st.markdown("### ⛅ 1. ระบบปรับสมดุลและคำนวณสารอาหารเป้าหมาย (Nutrient Optimization & Target System)")
c_age, c_weather = st.columns(2)
with c_age:
    current_key = st.selectbox(
        "เลือกช่วงอายุ/โปรไฟล์ของไก่ (Select Animal Profile):", 
        options=list(STAGE_NUTRITION_TARGETS.keys()), 
        index=2,
        format_func=lambda x: STAGE_NUTRITION_TARGETS[x]["name"]
    )
    target = STAGE_NUTRITION_TARGETS[current_key]
with c_weather:
    weather_env = st.radio("สภาพอากาศและอุณหภูมิในโรงเรือนวันนี้ (House Temperature & Weather Environment):", ["🌡️ อากาศปกติ (25-32°C)", "🔥 อากาศร้อนจัด (> 32°C)", "❄️ อากาศหนาว (< 25°C)"], horizontal=True)

density_factor = 1.0
if "ร้อนจัด" in weather_env:
    density_factor = 1.08
    st.warning("🔥 **เปิดใช้งานโหมดเร่งความเข้มข้นของสารอาหาร (Nutrient Concentration Mode - 1.08x):** เนื่องจากอากาศร้อน ไก่จะกินอาหารน้อยลง ระบบจึงปรับความเข้มข้นสารอาหารเพิ่มขึ้นอัตโนมัติเพื่อให้ร่างกายได้รับสารอาหารครบถ้วน")
elif "หนาว" in weather_env:
    density_factor = 0.95

adjusted_target = {
    "protein": target["protein"] * density_factor,
    "me": target["me"],
    "calcium": target["calcium"] * density_factor,
    "phos": target["phos"] * density_factor,
    "amino": target["amino"] * density_factor,
    "fiber": target.get("fiber", 4.0),
    "fat": target.get("fat", 3.5)
}
st.markdown("---")

# ==========================================
# 🧠 5. สมองกลคำนวณต้นทุนต่ำสุด (PuLP Engine AI Least-Cost Optimizer)
# ==========================================
st.markdown("### 🧠 2. ระบบประมวลผลสูตรอาหารต้นทุนต่ำที่สุด (AI Least-Cost Feed Optimizer)")
st.caption("ระบบคำนวณหาสัดส่วนการผสมวัตถุดิบอัตโนมัติที่ต้นทุนต่ำที่สุดในตลาด ณ ปัจจุบัน แต่ให้ค่าสารอาหารครบถ้วนตามเกณฑ์")
use_phytase = st.checkbox("🧪 ใส่เอนไซม์ไฟเตส (Phytase Benefit) ช่วยย่อยฟอสฟอรัสจากรำละเอียด (ลดเป้าหมายไดแคลเซียมลง 0.10% อัตโนมัติ)", value=True)
if use_phytase:
    adjusted_target["phos"] = max(0.30, adjusted_target["phos"] - 0.10)

if st.button("⚡ สั่งปัญญาประดิษฐ์ประมวลผลคำนวณสูตรต้นทุนต่ำสุด (Run AI Least-Cost Optimizer)"):
    prob = pulp.LpProblem("LeastCostLayerFeed", pulp.LpMinimize)
    ingredient_vars = {}
    
    for name, data in st.session_state.ingredient_data.items():
        ingredient_vars[name] = pulp.LpVariable(name, lowBound=data.get("min_limit", 0.0), upBound=data.get("max_limit", 100.0))
        
    prob += pulp.lpSum([ingredient_vars[name] * (st.session_state.ingredient_data[name]["price"] / 100.0) for name in st.session_state.ingredient_data.keys()])
    prob += pulp.lpSum([ingredient_vars[name] for name in st.session_state.ingredient_data.keys()]) == 100.0, "TotalWeight"
    prob += pulp.lpSum([ingredient_vars[name] * (st.session_state.ingredient_data[name]["protein"] / 100.0) for name in st.session_state.ingredient_data.keys()]) >= adjusted_target["protein"], "ProteinRequired"
    prob += pulp.lpSum([ingredient_vars[name] * (st.session_state.ingredient_data[name]["me"] / 100.0) for name in st.session_state.ingredient_data.keys()]) >= adjusted_target["me"], "EnergyRequired"
    prob += pulp.lpSum([ingredient_vars[name] * (st.session_state.ingredient_data[name]["calcium"] / 100.0) for name in st.session_state.ingredient_data.keys()]) >= adjusted_target["calcium"], "CalciumRequired"
    prob += pulp.lpSum([ingredient_vars[name] * (st.session_state.ingredient_data[name]["phos"] / 100.0) for name in st.session_state.ingredient_data.keys()]) >= adjusted_target["phos"], "PhosRequired"
    prob += pulp.lpSum([ingredient_vars[name] * (st.session_state.ingredient_data[name]["amino"] / 100.0) for name in st.session_state.ingredient_data.keys()]) >= adjusted_target["amino"], "AminoRequired"
    
    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status] == "Optimal":
        for name in st.session_state.ingredient_data.keys():
            val = round(ingredient_vars[name].varValue, 1)
            st.session_state.optimized_weights[name] = val
        st.success("🎉 ค้นพบทางเลือกการผสมสูตรอาหารที่ประหยัดเงินที่สุดและปลอดภัยเรียบร้อยแล้ว! (Optimal Formulation Found)")
        st.rerun()
    else:
        st.error("❌ ข้อจำกัดสารอาหารแน่นเกินไป หรือวัตถุดิบในคลังปัจจุบันไม่สามารถผสมให้ได้ค่าสารอาหารตามสภาวะอากาศนี้ได้ โปรดปรับสัดส่วนเองด้วยมือด้านล่าง (Infeasible Constraints)")
st.markdown("---")

# ==========================================
# 🎛️ 6. พื้นที่ปรับแต่งสูตรอาหารและเพิ่มวัตถุดิบด้วยมือ (Formulation & Dashboard Panels)
# ==========================================
creator_left, creator_right = st.columns([1, 1], gap="large")

with creator_left:
    st.markdown("### 🛠️ 3. แผงควบคุมและปรับแต่งสูตรสัดส่วนอาหารด้วยตนเอง (Manual Feed Formulation Panel)")
    
    with st.expander("➕ เพิ่มวัตถุดิบ / สารอาหารเสริมตัวใหม่เข้าระบบ (Add Custom Ingredients)"):
        st.caption("ป้อนข้อมูลสารอาหารเพื่อเพิ่มวัตถุดิบใหม่เข้าระบบจำลอง")
        with st.form("add_new_ingredient_form", clear_on_submit=True):
            new_ing_name = st.text_input("📝 ชื่อวัตถุดิบใหม่ (Ingredient Name):", placeholder="เช่น กากเบียร์, สารเร่งไข่แดง").strip()
            
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                new_ing_price = st.number_input("💰 ราคาวัตถุดิบ (Price - บาท/กก.):", min_value=0.0, value=10.0, step=0.5)
                new_ing_protein = st.number_input("🥩 ปริมาณโปรตีนในวัตถุดิบ (Crude Protein - %):", min_value=0.0, value=0.0, step=0.1)
                new_ing_me = st.number_input("⚡ พลังงานใช้ประโยชน์ได้ (Metabolizable Energy - ME กิโลแคลอรี/กก.):", min_value=0.0, value=0.0, step=50.0)
                new_ing_fiber = st.number_input("🌾 ปริมาณกาก/เยื่อใย (Crude Fiber - %):", min_value=0.0, value=0.0, step=0.1)
            with f_col2:
                new_ing_calcium = st.number_input("🦴 ปริมาณแคลเซียม (Calcium - %):", min_value=0.0, value=0.0, step=0.05)
                new_ing_phos = st.number_input("🧪 ปริมาณฟอสฟอรัส (Phosphorus - %):", min_value=0.0, value=0.0, step=0.05)
                new_ing_amino = st.number_input("🧬 กรดอะมิโนจำเป็นรวม (Total Amino Acids - %):", min_value=0.0, value=0.0, step=0.05)
                new_ing_fat = st.number_input("🥑 ปริมาณไขมัน (Crude Fat - %):", min_value=0.0, value=0.0, step=0.1)
                
            new_ing_moisture = st.number_input("💧 ความชื้น (Moisture - %)", min_value=0.0, max_value=100.0, value=10.0, step=0.5)
            new_ing_risk = st.slider("🍄 ระดับความเสี่ยงเชื้อรา/สารพิษตกค้าง (Mycotoxin Risk Score: 0 = ต่ำสุด, 5 = สูงสุด)", 0, 5, 0)
            
            if st.form_submit_button("📥 บันทึกวัตถุดิบนี้เข้าคลังชั่วคราว (Save to Temp Inventory)"):
                if not new_ing_name:
                    st.error("❌ กรุณากรอกชื่อวัตถุดิบก่อนบันทึก")
                elif new_ing_name in st.session_state.ingredient_data:
                    st.error("❌ วัตถุดิบชื่อนี้มีอยู่ในระบบแล้ว")
                else:
                    st.session_state.ingredient_data[new_ing_name] = {
                        "price": new_ing_price, "protein": new_ing_protein, "me": new_ing_me,
                        "calcium": new_ing_calcium, "phos": new_ing_phos, "amino": new_ing_amino,
                        "moisture": new_ing_moisture, "fiber": new_ing_fiber, "fat": new_ing_fat,
                        "tox_risk": new_ing_risk, "min_limit": 0.0, "max_limit": 100.0
                    }
                    st.session_state.optimized_weights[new_ing_name] = 0.0
                    st.success(f"✨ เพิ่ม '{new_ing_name}' เข้าสู่ระบบเรียบร้อยแล้ว!")
                    st.rerun()

    st.write("🔧 **สไลเดอร์ปรับสัดส่วนการผสมจริงในฟาร์ม (Manual Blend Ratio - %):**")
    user_weights = {}
    for name in st.session_state.ingredient_data.keys():
        val = float(st.session_state.optimized_weights.get(name, 0.0))
        user_weights[name] = st.slider(f"{name} (%)", 0.0, 100.0, val, step=0.1, key=f"sl_{name}")

    sum_weights = sum(user_weights.values())
    st.markdown(f"**🔢 ผลรวมสัดส่วนปัจจุบัน (Total Blend Weight):** `{sum_weights:.1f}%` / `100.0%`")
    if not (99.9 <= sum_weights <= 100.1):
        st.warning("⚠️ **สัดส่วนรวมไม่เท่ากับ 100% (Total Weight Inaccurate)** กรุณาปรับสไลเดอร์ให้ได้รวม 100% ถ้วนเพื่อให้ได้สูตรอาหารที่สมบูรณ์")

# คำนวณสารอาหารรวม (Nutrient Calculation)
current_nutrition = {"protein": 0.0, "me": 0.0, "calcium": 0.0, "phos": 0.0, "amino": 0.0, "fiber": 0.0, "fat": 0.0}
total_moisture = 0.0
total_cost = 0.0
total_risk_score = 0.0

for name, weight in user_weights.items():
    factor = weight / 100.0
    nutrients = st.session_state.ingredient_data[name]
    current_nutrition["protein"] += nutrients.get("protein", 0.0) * factor
    current_nutrition["me"] += nutrients.get("me", 0.0) * factor
    current_nutrition["calcium"] += nutrients.get("calcium", 0.0) * factor
    current_nutrition["phos"] += nutrients.get("phos", 0.0) * factor
    current_nutrition["amino"] += nutrients.get("amino", 0.0) * factor
    current_nutrition["fiber"] += nutrients.get("fiber", 0.0) * factor
    current_nutrition["fat"] += nutrients.get("fat", 0.0) * factor
    total_moisture += nutrients.get("moisture", 0.0) * factor
    total_cost += nutrients.get("price", 0.0) * factor
    total_risk_score += factor * nutrients.get("tox_risk", 0)

with creator_right:
    st.markdown("### 📊 หน้าจอติดตามระดับสารอาหารแบบเรียลไทม์ (Extended Dashboard Tracker)")
    st.caption("ระบบตรวจสอบความเข้มข้นสารอาหารหลัก กรดอะมิโน กากใย ความชื้น และระดับสารพิษตกค้าง")
    
    st.markdown("##### 🩺 สารอาหารหลักตามเกณฑ์มาตรฐาน (Core Essential Nutrients Status):")
    nutrient_list = [
        ("🥩 โปรตีนรวม (Crude Protein)", "protein", "%"), 
        ("⚡ พลังงานใช้ประโยชน์ได้ (Metabolizable Energy)", "me", "kcal/kg"), 
        ("🦴 แคลเซียม (Calcium)", "calcium", "%"), 
        ("🧪 ฟอสฟอรัสที่เป็นประโยชน์ (Available Phosphorus)", "phos", "%"), 
        ("🧬 กรดอะมิโนจำเป็นรวม (Total Amino Acids)", "amino", "%"),
        ("🌾 กาก / เยื่อใยรวม (Crude Fiber)", "fiber", "%"),
        ("🥑 ไขมันรวม (Crude Fat)", "fat", "%")
    ]
    
    for nutrient_title, key_name, unit in nutrient_list:
        cur = current_nutrition[key_name]
        req = adjusted_target[key_name]
        st.write(f"**{nutrient_title}**: {cur:.2f} / {req:.2f} {unit}")
        st.progress(min(max(cur / req, 0.0), 1.0) if req > 0 else 0.0)
        
    st.markdown("---")
    
    st.markdown("##### 🛡️ ความปลอดภัยและกายภาพของอาหาร (Biosecurity & Physical Diagnostics):")
    
    # การแสดงผลความชื้น (Moisture Check)
    if total_moisture > 12.0:
        st.markdown(f"💧 **ความชื้นรวม (Total Moisture):** <span style='color:#ef4444; font-weight:bold;'>{total_moisture:.1f}% 🔴 เกณฑ์อันตรายเสี่ยงราขึ้น (Critical High Risk)</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"💧 **ความชื้นรวม (Total Moisture):** <span style='color:#22c55e; font-weight:bold;'>{total_moisture:.1f}% 🟢 ปลอดภัยจัดเก็บได้นาน (Safe & Stable)</span>", unsafe_allow_html=True)
        
    # การแสดงผลความเสี่ยงสารพิษเชื้อรา (Mycotoxin Risk Check)
    if total_risk_score >= 2.5:
        st.markdown(f"🍄 **ดัชนีความเสี่ยงเชื้อรา (Mycotoxin Risk Index):** <span style='color:#ef4444; font-weight:bold;'>{total_risk_score:.2f} / 5.00 🔴 เสี่ยงสูง (High Risk - Requires Toxin Binder)</span>", unsafe_allow_html=True)
    elif total_risk_score >= 1.5:
        st.markdown(f"🍄 **ดัชนีความเสี่ยงเชื้อรา (Mycotoxin Risk Index):** <span style='color:#eab308; font-weight:bold;'>{total_risk_score:.2f} / 5.00 🟡 ปานกลาง (Moderate Alert)</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"🍄 **ดัชนีความเสี่ยงเชื้อรา (Mycotoxin Risk Index):** <span style='color:#22c55e; font-weight:bold;'>{total_risk_score:.2f} / 5.00 🟢 ปลอดภัยมาก (Excellent Safety)</span>", unsafe_allow_html=True)

    st.markdown("---")
    st.metric(label="💰 ต้นทุนสูตรอาหารผสมเองเฉลี่ยฟาร์มของคุณ (Your Custom Formulation Cost)", value=f"{total_cost:.2f} บาท / กิโลกรัม (THB/kg)")

st.markdown("---")

# ==========================================
# 🧫 7. บล็อกจัดการระบบปฏิบัติการฟาร์ม (Farm Operation & Risk Management)
# ==========================================
st.markdown("### 📅 4. ระบบการจัดการและการจัดการความเสี่ยงในฟาร์ม (Farm Operations & Risk Management)")
m_col1, m_col2, m_col3 = st.columns(3, gap="medium")
with m_col1:
    st.markdown("##### 💧 ระบบคำนวณปริมาณน้ำที่ต้องใช้ (Water Intake Calculator)")
    chicken_count = st.number_input("จำนวนไก่ในฟาร์มทั้งหมด (Total Chicken Flock Size - ตัว):", min_value=1, value=1000, step=100)
    base_water = (breed_info['default_feed'] / 1000.0) * 2.2 if current_key == "laying" else 0.15
    calc_water = chicken_count * base_water
    if "ร้อนจัด" in weather_env:
        calc_water *= 1.20
        st.error("🔥 อากาศร้อนจัด! ไก่เสี่ยงเกิดภาวะขาดน้ำ ให้เตรียมน้ำดื่มเพิ่มขึ้นอีก 20% (Heat Stress Water Required)")
    st.metric("ปริมาณน้ำที่ฝูงไก่ต้องกินต่อวัน (Daily Water Demand)", f"{calc_water:,.1f} ลิตร (Liters)")

with m_col2:
    st.markdown("##### 🍄 ระบบตรวจสอบความชื้นและการเกิดเชื้อรา (Moisture & Mycotoxin Warning)")
    if total_moisture > 12.0:
        st.error(f"⚠️ ความชื้นในอาหารวิกฤต {total_moisture:.1f}% ห้ามเก็บอาหารชุดนี้ไว้นานเกิน 7 วันเด็ดขาด! เสี่ยงต่อสารพิษอะฟลาท็อกซิน (Aflatoxin Threat)")
    else:
        st.success(f"✨ ความชื้นอยู่ในเกณฑ์ปลอดภัย {total_moisture:.1f}% สามารถจัดเก็บในโกดังแห้งได้ 14-30 วัน")
    if total_risk_score >= 1.8:
        st.markdown(f"🧫 **แจ้งเตือนความเสี่ยงเชื้อราสูง (High Toxin Alert):** แนะนำให้ผสมสารจับสารพิษเชื้อรา (**Toxin Binder**) เพิ่มเข้าไปจำนวน **{2.0 * (chicken_count * breed_info['default_feed'] / 1000.0):,.1f} กรัม (g)** สำหรับรอบการผสมนี้")

with m_col3:
    st.markdown("##### 🌙 โปรแกรมแสงสว่างกระตุ้นการไข่ (Lighting & Feeding Stimulation)")
    enable_midnight = st.checkbox("เปิดใช้ระบบ Midnight Feeding (ให้อาหารมื้อดึก)")
    if enable_midnight:
        st.caption("💡 ข้อแนะนำเชิงเทคนิค: แนะนำให้ย้ายสัดส่วน 'เปลือกหอยบด 65%' มาให้กินในมื้อค่ำหรือมื้อดึก เพื่อช่วยเร่งการสร้างเปลือกไข่ให้หนาขึ้นในช่วงกลางคืน (Enhance Eggshell Quality)")
st.markdown("---")

# ==========================================
# 📊 8. การวางแผนปริมาณสั่งซื้อและใบจัดซื้อวัตถุดิบ (Procurement & Order Planner)
# ==========================================
st.markdown("### 📅 5. แผนการสำรองวัตถุดิบและประมาณการคำสั่งซื้อ (Procurement Inventory & Budget Forecasting)")
total_phase_feed_needed_kg = chicken_count * LIFECYCLE_FEED_BUDGET[current_key]
st.write(f"📦 ยอดสั่งซื้อและปริมาณวัตถุดิบรวมที่ต้องกักตุนเข้าคลังสำหรับฝูงนี้ตลอดเฟสปัจจุบัน: **{total_phase_feed_needed_kg/1000.0:,.2f} ตัน (Tons)**")
budget_data = []
for name in st.session_state.ingredient_data.keys():
    if name in user_weights:
        w_kg = (user_weights[name] / 100.0) * total_phase_feed_needed_kg
        if w_kg > 0:
            budget_data.append({"วัตถุดิบ (Material)": name, "สัดส่วนการผสม (%) (Mix Ratio)": f"{user_weights[name]}%", "น้ำหนักรวมที่ต้องสั่งซื้อเข้าโกดัง (กก.) (Total Weight - kg)": round(w_kg, 1)})

df_budget = pd.DataFrame(budget_data)
st.dataframe(df_budget, use_container_width=True, hide_index=True)

if not df_budget.empty:
    csv_budget = df_budget.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 ดาวน์โหลดใบจัดซื้อวัตถุดิบอาหารสัตว์ (Download PO CSV)",
        data=csv_budget,
        file_name="ใบสั่งซื้อวัตถุดิบ_รายงาน.csv",
        mime="text/csv"
    )

st.markdown("---")

# ==========================================
# 📈 9. สมุดจดสถิติและกราฟดูสถิติไข่ไก่ประจำวัน (Daily Egg Production & Profit Analytical Ledger)
# ==========================================
st.markdown("### 📈 6. สมุดจดสถิติและกราฟวิเคราะห์ผลผลิตประจำวัน (Daily Production Record & Profit Analytics Dashboard)")

if "tracker_data" not in st.session_state:
    st.session_state.tracker_data = pd.DataFrame([
        {"วันที่": "01/06", "สูตรอาหาร": "สูตรเดิม", "อัตราการไข่ (%)": 82.0, "อัตราไข่บุบแตก (%)": 4.5, "น้ำหนักไข่รวม (กก.)": 52.0, "ไข่เบอร์ 0-1 (%)": 20.0, "ไข่เบอร์ 2-3 (%)": 55.0, "ไข่เบอร์ 4-5 (%)": 25.0, "ตาย/คัดทิ้ง (ตัว)": 0, "กำไรสุทธิวันนี้ (บาท)": 420.0, "หมายเหตุ": "ปกติ"},
        {"วันที่": "02/06", "สูตรอาหาร": "สูตรเดิม", "อัตราการไข่ (%)": 81.5, "อัตราไข่บุบแตก (%)": 5.0, "น้ำหนักไข่รวม (กก.)": 51.5, "ไข่เบอร์ 0-1 (%)": 22.0, "ไข่เบอร์ 2-3 (%)": 53.0, "ไข่เบอร์ 4-5 (%)": 25.0, "ตาย/คัดทิ้ง (ตัว)": 1, "กำไรสุทธิวันนี้ (บาท)": 395.0, "หมายเหตุ": "ฝนตกหนักตอนบ่าย"},
        {"วันที่": "03/06", "สูตรอาหาร": "สูตร AI แนะนำ", "อัตราการไข่ (%)": 84.0, "อัตราไข่บุบแตก (%)": 2.1, "น้ำหนักไข่รวม (กก.)": 53.8, "ไข่เบอร์ 0-1 (%)": 25.0, "ไข่เบอร์ 2-3 (%)": 55.0, "ไข่เบอร์ 4-5 (%)": 20.0, "ตาย/คัดทิ้ง (ตัว)": 0, "กำไรสุทธิวันนี้ (บาท)": 610.0, "หมายเหตุ": "เริ่มปรับสูตรอาหารใหม่"},
    ])

df_track = st.session_state.tracker_data.copy()

daily_feed_consumed_kg = (chicken_count * breed_info['default_feed']) / 1000.0
daily_feed_cost = daily_feed_consumed_kg * total_cost

# คำนวณค่า FCR (Feed Conversion Ratio) อัตโนมัติ
df_track["FCR (ประสิทธิภาพอาหาร)"] = (daily_feed_consumed_kg / df_track["น้ำหนักไข่รวม (กก.)"]).round(2)
total_dead = df_track["ตาย/คัดทิ้ง (ตัว)"].sum()
total_profit_accum = df_track["กำไรสุทธิวันนี้ (บาท)"].sum()

st.markdown("##### 📊 สรุปภาพรวมประสิทธิภาพเชิงลึกและบัญชีฟาร์ม (Farm Performance & Profit Metrics Insights)")
avg_lay = df_track["อัตราการไข่ (%)"].mean()
avg_crack = df_track["อัตราไข่บุบแตก (%)"].mean()
avg_fcr = df_track["FCR (ประสิทธิภาพอาหาร)"].mean()
last_profit = df_track["กำไรสุทธิวันนี้ (บาท)"].iloc[-1]

m_lay, m_crack, m_fcr, m_profit = st.columns(4)
with m_lay:
    st.metric(label="🥚 อัตราการไข่เฉลี่ย (Average Laying Rate)", value=f"{avg_lay:.1f} %", delta=f"ล่าสุด: {df_track['อัตราการไข่ (%)'].iloc[-1]}%")
with m_crack:
    st.metric(label="💥 อัตราไข่บุบแตกเฉลี่ย (Average Damaged Rate)", value=f"{avg_crack:.2f} %", delta=f"ล่าสุด: {df_track['อัตราไข่บุบแตก (%)'].iloc[-1]}%", delta_color="inverse")
with m_fcr:
    st.metric(label="🥣 ค่า FCR เฉลี่ย (Feed Conversion Ratio)", value=f"{avg_fcr:.2f}", delta=f"ล่าสุด: {df_track['FCR (ประสิทธิภาพอาหาร)'].iloc[-1]}", delta_color="inverse")
with m_profit:
    st.metric(label="💵 กำไรสุทธิวันนี้ (Net Daily Profit)", value=f"{last_profit:,.1f} บาท", delta=f"สะสมรอบนี้: {total_profit_accum:,.1f} บาท")

st.markdown("---")

st.markdown("##### 💵 📊 ตารางตั้งราคาขายหน้าฟาร์มวันนี้เพื่อคำนวณผลกำไร (Farm-gate Egg Selling Prices Setup)")
p_c1, p_c2, p_c3 = st.columns(3)
with p_c1:
    price_large = st.number_input("ราคาขายไข่ เบอร์ 0 - 1 (บาท/ฟอง) (Price Size Jumbo/Large):", min_value=0.0, value=4.5, step=0.1)
with p_c2:
    price_med = st.number_input("ราคาขายไข่ เบอร์ 2 - 3 (บาท/ฟอง) (Price Size Medium):", min_value=0.0, value=4.0, step=0.1)
with p_c3:
    price_small = st.number_input("ราคาขายไข่ เบอร์ 4 - 5 (บาท/ฟอง) (Price Size Small):", min_value=0.0, value=3.5, step=0.1)

st.markdown("---")

track_col1, track_col2 = st.columns([4, 6], gap="large")

with track_col1:
    with st.form("supabase_sync_form_final_v8"):
        st.markdown("##### 📝 สมุดบันทึกและจำแนกเกรดผลผลิต (Production & Grade Classification Ledger)")
        
        f_c1, f_c2 = st.columns(2)
        with f_c1:
            picked_date = st.date_input("เลือกวันที่บันทึกสถิติ (Select Record Date):", datetime.now())
            in_date = picked_date.strftime("%d/%m")
            
            lay_r = st.number_input("อัตราการไข่วันนี้ (%) (Laying Rate):", value=85.0, min_value=0.0, max_value=100.0, step=0.1)
            egg_weight_total = st.number_input("น้ำหนักไข่รวมวันนี้ (กก.) (Total Egg Weight - kg):", value=53.0, min_value=1.0, max_value=5000.0, step=0.5)
        with f_c2:
            f_name = st.text_input("สูตรอาหารวันนี้ (Feed Formula Name):", value="สูตร AI แนะนำ")
            crack_r = st.number_input("อัตราไข่บุบแตกวันนี้ (%) (Broken Rate):", value=1.8, min_value=0.0, max_value=100.0, step=0.1)
            dead_count = st.number_input("จำนวนไก่ตาย/คัดทิ้งวันนี้ (ตัว) (Mortality/Cull Count):", value=0, min_value=0, step=1)
            
        st.markdown("**📊 สัดส่วนขนาดไข่ที่คัดแยกวันนี้ - รวมต้องได้ 100% (Egg Grade Sorting Ratios)**")
        g_c1, g_c2, g_c3 = st.columns(3)
        with g_c1:
            g_large = st.number_input("เบอร์ 0 - 1 (%)", value=25.0, min_value=0.0, max_value=100.0, step=1.0, key="gl")
        with g_c2:
            g_med = st.number_input("เบอร์ 2 - 3 (%)", value=55.0, min_value=0.0, max_value=100.0, step=1.0, key="gm")
        with g_c3:
            g_small = st.number_input("เบอร์ 4 - 5 (%)", value=20.0, min_value=0.0, max_value=100.0, step=1.0, key="gs")
            
        note_text = st.text_input("📌 หมายเหตุ/เหตุการณ์สำคัญ (Special Remarks):", value="ปกติ")
        
        total_grade_pct = g_large + g_med + g_small
        if abs(total_grade_pct - 100.0) > 0.01:
            st.error(f"❌ สัดส่วนขนาดไข่รวมกันได้ {total_grade_pct}% (กรุณาปรับแก้ให้ครบ 100% ก่อนบันทึก)")
            submit_disabled = True
        else:
            submit_disabled = False
            
        if st.form_submit_button("💾 กดบันทึกสถิติวันนี้ (Save Daily Records)", disabled=submit_disabled):
            # คำนวณรายได้และกำไรอัตโนมัติจากราคาฟาร์มและสัดส่วนเบอร์ไข่
            total_eggs_today = chicken_count * (lay_r / 100.0)
            revenue_today = (
                (total_eggs_today * (g_large / 100.0) * price_large) +
                (total_eggs_today * (g_med / 100.0) * price_med) +
                (total_eggs_today * (g_small / 100.0) * price_small)
            )
            profit_today = revenue_today - daily_feed_cost
            
            new_row = {
                "วันที่": in_date, 
                "สูตรอาหาร": f_name, 
                "อัตราการไข่ (%)": lay_r, 
                "อัตราไข่บุบแตก (%)": crack_r, 
                "น้ำหนักไข่รวม (กก.)": egg_weight_total, 
                "ไข่เบอร์ 0-1 (%)": g_large, 
                "ไข่เบอร์ 2-3 (%)": g_med, 
                "ไข่เบอร์ 4-5 (%)": g_small, 
                "ตาย/คัดทิ้ง (ตัว)": dead_count, 
                "กำไรสุทธิวันนี้ (บาท)": round(profit_today, 2), 
                "หมายเหตุ": note_text
            }
            
            st.session_state.tracker_data = pd.concat([st.session_state.tracker_data, pd.DataFrame([new_row])], ignore_index=True)
            st.success("🎉 บันทึกข้อมูลและประมวลผลกำไรสุทธิประจำวันลงในระบบเรียบร้อยแล้ว!")
            st.rerun()

with track_col2:
    st.markdown("##### 📈 กราฟเส้นแนวโน้มผลผลิตและกำไรของฟาร์ม (Production Trends & Profit Analytics Charts)")
    if not df_track.empty:
        # แสดงตารางประวัติข้อมูล
        st.dataframe(df_track, use_container_width=True, hide_index=True)
        
        # 🛠️ ใช้ go.Figure ร่วมกับ make_subplots สำหรับทำกราฟเปรียบเทียบแบบ 2 แกนวาย (Dual Y-Axis) 
        # วิธีนี้ปลอดภัยจากการระเบิดและแสดงผลเปรียบเทียบเชิงลึกได้ตามที่ฟาร์มต้องการ
        from plotly.subplots import make_subplots
        
        fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
        
        # เพิ่มเส้นกราฟอัตราการไข่ (แกนซ้าย)
        fig_dual.add_trace(
            go.Scatter(x=df_track["วันที่"], y=df_track["อัตราการไข่ (%)"], name="อัตราการไข่ (%)", mode='lines+markers', line=dict(color='#0284c7', width=3)),
            secondary_y=False,
        )
        
        # เพิ่มเส้นกราฟกำไรสุทธิ (แกนขวา)
        fig_dual.add_trace(
            go.Scatter(x=df_track["วันที่"], y=df_track["กำไรสุทธิวันนี้ (บาท)"], name="กำไรสุทธิวันนี้ (บาท)", mode='lines+markers', line=dict(color='#16a34a', width=3)),
            secondary_y=True,
        )
        
        # กำหนดรายละเอียดหัวข้อและป้ายกำกับแกน
        fig_dual.update_layout(
            title_text="📊 วิเคราะห์เปรียบเทียบอัตราการไข่ และ ผลกำไรสุทธิรายวัน",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        fig_dual.update_xaxes(title_text="วันที่บันทึก (Date)")
        fig_dual.update_yaxes(title_text="<b>อัตราการไข่</b> (%)", color='#0284c7', secondary_y=False)
        fig_dual.update_yaxes(title_text="<b>กำไรสุทธิ</b> (บาท)", color='#16a34a', secondary_y=True)
        
        st.plotly_chart(fig_dual, use_container_width=True)
        
        # เพิ่มเติม: กราฟแท่งแสดงอัตราไข่บุบแตกประจำวัน
        fig_crack = px.bar(df_track, x="วันที่", y="อัตราไข่บุบแตก (%)", 
                            title="💥 แนวโน้มอัตราไข่บุบแตกหน้าฟาร์ม (Daily Broken Egg Rates Trend)",
                            text_auto='.1f', color_discrete_sequence=['#ef4444'])
        st.plotly_chart(fig_crack, use_container_width=True)
        
    else:
        st.info("💡 ยังไม่มีข้อมูลสถิติในระบบ กรุณากรอกข้อมูลและบันทึกสถิติที่แผงควบคุมฝั่งซ้าย")
