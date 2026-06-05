import streamlit as st
import pandas as pd
import plotly.express as px
import pulp
import requests

# 🔱 1. ตั้งค่าแอปพลิเคชันและธีมเริ่มต้น
st.set_page_config(page_title="Smart Layer Feed - ระบบคำนวณอาหารไก่ไข่อัจฉริยะ", layout="wide")

# เมนูด้านข้างสำหรับการเชื่อมต่อระบบคลาวด์
st.sidebar.markdown("### ☁️ การเชื่อมต่อคลาวด์ระดับองค์กร")
SUPABASE_URL = st.sidebar.text_input("ลิงก์โปรเจกต์ Supabase (URL)", "https://your-project.supabase.co").strip()
SUPABASE_KEY = st.sidebar.text_input("รหัสผ่าน API (Supabase Anon Key)", "your-anon-key", type="password").strip()

# ==========================================
# 📋 2. ฐานข้อมูลส่วนประกอบและโภชนาการมาตรฐาน
# ==========================================

STAGE_NUTRITION_TARGETS = {
    "starter": {"name": "ลูกไก่ไข่ 0 - 6 สัปดาห์ (Starter)", "protein": 20.0, "me": 2900.0, "calcium": 1.00, "phos": 0.45, "amino": 0.42},
    "grower": {"name": "ไก่รุ่นไข่ 6 - 16 สัปดาห์ (Grower)", "protein": 16.0, "me": 2750.0, "calcium": 0.90, "phos": 0.40, "amino": 0.32},
    "laying": {"name": "ไก่ไข่ระยะให้ผลผลิต 16 สัปดาห์ขึ้นไป (Laying)", "protein": 17.5, "me": 2750.0, "calcium": 4.10, "phos": 0.42, "amino": 0.38}
}

INGREDIENT_DATA = {
    "ข้าวโพดบด": {"price": 13.5, "protein": 8.5, "me": 3300.0, "calcium": 0.02, "phos": 0.25, "amino": 0.18, "moisture": 12.0, "tox_risk": 3, "min_limit": 20.0, "max_limit": 70.0},
    "กากถั่วเหลือง": {"price": 18.5, "protein": 44.0, "me": 2420.0, "calcium": 0.25, "phos": 0.60, "amino": 0.65, "moisture": 11.5, "tox_risk": 1, "min_limit": 5.0, "max_limit": 40.0},
    "รำละเอียด": {"price": 11.0, "protein": 12.0, "me": 2400.0, "calcium": 0.05, "phos": 1.35, "amino": 0.22, "moisture": 10.5, "tox_risk": 3, "min_limit": 0.0, "max_limit": 30.0},
    "ปลาป่น": {"price": 32.0, "protein": 60.0, "me": 2850.0, "calcium": 5.00, "phos": 3.00, "amino": 0.95, "moisture": 10.0, "tox_risk": 1, "min_limit": 0.0, "max_limit": 15.0},
    "เปลือกหอยบด": {"price": 4.0, "protein": 0.0, "me": 0.0, "calcium": 38.00, "phos": 0.04, "amino": 0.00, "moisture": 0.5, "tox_risk": 0, "min_limit": 0.0, "max_limit": 12.0},
    "ไดแคลเซียมฟอสเฟต": {"price": 28.0, "protein": 0.0, "me": 0.0, "calcium": 21.00, "phos": 18.00, "amino": 0.00, "moisture": 1.0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 5.0},
    "กรดอะมิโนสังเคราะห์": {"price": 95.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "amino": 99.00, "moisture": 0.2, "tox_risk": 0, "min_limit": 0.0, "max_limit": 2.0}
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
# 🏛️ 3. ส่วนหัวของแอปและข้อมูลสายพันธุ์
# ==========================================
st.title("🔱 Smart Layer Feed — ระบบคำนวณโภชนาการอาหารไก่ไข่อัจฉริยะ")
st.caption("ระบบคำนวณเชิงลึกระดับอุตสาหกรรมด้วยกลไกการค้นหาจุดคุ้มทุนเชิงเส้น (PuLP Linear Programming Engine)")

st.markdown("### 🧬 0. ข้อมูลสายพันธุ์และสถานะการเชื่อมต่อคลาวด์")
c_group, c_breed = st.columns(2)
with c_group:
    selected_group = st.selectbox("เลือกกลุ่มสายพันธุ์ไก่ไข่:", list(BREED_PROFILES.keys()))

with c_breed:
    breed_options = BREED_PROFILES[selected_group]
    selected_breed_key = st.selectbox(
        "สายพันธุ์หลักในโรงเรือน:", 
        options=list(breed_options.keys()),
        format_func=lambda x: breed_options[x]["name"]
    )

breed_info = breed_options[selected_breed_key]

cloud_status_text = "พร้อมใช้งาน (เชื่อมต่อระบบจริง)" if "your-project" not in SUPABASE_URL and SUPABASE_KEY != "your-anon-key" else "โหมดทำงานแบบออฟไลน์ชั่วคราว"
st.markdown(f"""
<div style='background-color:{breed_info['bg_color']}; padding:15px; border-radius:10px; color:{breed_info['text_color']}; margin-bottom:15px; border: 1px solid rgba(0,0,0,0.1);'>
    <b>🧬 สายพันธุ์ปัจจุบัน: {breed_info['name']}</b> | 🎨 สีเปลือกไข่: {breed_info['egg_color']} | 🥣 อัตรากินอาหาร: {breed_info['default_feed']} กรัม/วัน <br>
    <p style='margin: 5px 0 0 0; font-size: 0.9em; opacity: 0.95;'>ℹ️ <i>{breed_info['desc']}</i></p>
    <small style='display:block; margin-top:5px; font-weight: bold; opacity: 0.8;'>📊 Status ระบบคลาวด์ Supabase: {cloud_status_text}</small>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# ⛅ 4. ระบบปรับสมดุลตามสภาพแวดล้อมและช่วงอายุ
# ==========================================
st.markdown("### ⛅ 1. ระบบปรับสมดุลและคำนวณสารอาหารเป้าหมาย")
c_age, c_weather = st.columns(2)
with c_age:
    current_key = st.selectbox(
        "เลือกช่วงอายุ/โปรไฟล์ของไก่ (Animal Profile):", 
        options=list(STAGE_NUTRITION_TARGETS.keys()), 
        index=2,
        format_func=lambda x: STAGE_NUTRITION_TARGETS[x]["name"]
    )
    target = STAGE_NUTRITION_TARGETS[current_key]
with c_weather:
    weather_env = st.radio("สภาพอากาศและอุณหภูมิในโรงเรือนวันนี้:", ["🌡️ อากาศปกติ (25-32°C)", "🔥 อากาศร้อนจัด (> 32°C)", "❄️ อากาศหนาว (< 25°C)"], horizontal=True)

density_factor = 1.0
if "ร้อนจัด" in weather_env:
    density_factor = 1.08
    st.warning("🔥 **เปิดใช้งานโหมดเร่งความเข้มข้นของสารอาหาร (1.08 เท่า):** เนื่องจากอากาศร้อน ไก่จะกินอาหารน้อยลง ระบบจึงปรับความเข้มข้นสารอาหารเพิ่มขึ้นอัตโนมัติเพื่อให้ร่างกายได้รับสารอาหารครบถ้วน")
elif "หนาว" in weather_env:
    density_factor = 0.95

adjusted_target = {
    "protein": target["protein"] * density_factor,
    "me": target["me"],
    "calcium": target["calcium"] * density_factor,
    "phos": target["phos"] * density_factor,
    "amino": target["amino"] * density_factor
}
st.markdown("---")

# ==========================================
# 🧠 5. สมองกลคำนวณต้นทุนต่ำสุด (PuLP Engine)
# ==========================================
st.markdown("### 🧠 2. ระบบประมวลผลสูตรอาหารต้นทุนต่ำที่สุด (AI Least-Cost Optimizer)")
st.caption("ระบบคำนวณหาสัดส่วนการผสมวัตถุดิบอัตโนมัติที่ต้นทุนต่ำที่สุดในตลาด ณ ปัจจุบัน แต่ให้ค่าสารอาหารครบถ้วนตามเกณฑ์")
use_phytase = st.checkbox("🧪 ใส่เอนไซม์ไฟเตส (Phytase) ช่วยย่อยฟอสฟอรัสจากรำละเอียด (ลดเป้าหมายไดแคลเซียมลง 0.10% อัตโนมัติ)", value=True)
if use_phytase:
    adjusted_target["phos"] = max(0.30, adjusted_target["phos"] - 0.10)

if st.button("⚡ สั่งปัญญาประดิษฐ์ประมวลผลคำนวณสูตรต้นทุนต่ำสุด (Run AI Optimizer)"):
    prob = pulp.LpProblem("LeastCostLayerFeed", pulp.LpMinimize)
    ingredient_vars = {}
    
    for name, data in INGREDIENT_DATA.items():
        ingredient_vars[name] = pulp.LpVariable(name, lowBound=data["min_limit"], upBound=data["max_limit"])
        
    prob += pulp.lpSum([ingredient_vars[name] * (INGREDIENT_DATA[name]["price"] / 100.0) for name in INGREDIENT_DATA.keys()])
    prob += pulp.lpSum([ingredient_vars[name] for name in INGREDIENT_DATA.keys()]) == 100.0, "TotalWeight"
    prob += pulp.lpSum([ingredient_vars[name] * (INGREDIENT_DATA[name]["protein"] / 100.0) for name in INGREDIENT_DATA.keys()]) >= adjusted_target["protein"], "ProteinRequired"
    prob += pulp.lpSum([ingredient_vars[name] * (INGREDIENT_DATA[name]["me"] / 100.0) for name in INGREDIENT_DATA.keys()]) >= adjusted_target["me"], "EnergyRequired"
    prob += pulp.lpSum([ingredient_vars[name] * (INGREDIENT_DATA[name]["calcium"] / 100.0) for name in INGREDIENT_DATA.keys()]) >= adjusted_target["calcium"], "CalciumRequired"
    prob += pulp.lpSum([ingredient_vars[name] * (INGREDIENT_DATA[name]["phos"] / 100.0) for name in INGREDIENT_DATA.keys()]) >= adjusted_target["phos"], "PhosRequired"
    prob += pulp.lpSum([ingredient_vars[name] * (INGREDIENT_DATA[name]["amino"] / 100.0) for name in INGREDIENT_DATA.keys()]) >= adjusted_target["amino"], "AminoRequired"
    
    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status] == "Optimal":
        for name in INGREDIENT_DATA.keys():
            val = round(ingredient_vars[name].varValue, 1)
            st.session_state.optimized_weights[name] = val
        st.success("🎉 ค้นพบทางเลือกการผสมสูตรอาหารที่ประหยัดเงินที่สุดและปลอดภัยเรียบร้อยแล้ว!")
    else:
        st.error("❌ ข้อจำกัดสารอาหารแน่นเกินไป หรือวัตถุดิบในคลังปัจจุบันไม่สามารถผสมให้ได้ค่าสารอาหารตามสภาวะอากาศนี้ได้ โปรดปรับสัดส่วนเองด้วยมือด้านล่าง")
st.markdown("---")

# ==========================================
# 🎛️ 6. พื้นที่ปรับแต่งสูตรอาหารด้วยมือ
# ==========================================
creator_left, creator_right = st.columns([1, 1], gap="large")
with creator_left:
    st.markdown("### 🛠️ 3. แผงควบคุมและปรับแต่งสูตรสัดส่วนอาหารด้วยตนเอง")
    user_weights = {}
    for name in INGREDIENT_DATA.keys():
        val = float(st.session_state.optimized_weights.get(name, 0.0))
        user_weights[name] = st.slider(f"{name} (%)", 0.0, 100.0, val, step=0.1, key=f"sl_{name}")

    sum_weights = sum(user_weights.values())
    st.markdown(f"**🔢 ผลรวมสัดส่วนปัจจุบัน:** `{sum_weights:.1f}%` / `100.0%`")
    if not (99.9 <= sum_weights <= 100.1):
        st.warning("⚠️ **สัดส่วนรวมไม่เท่ากับ 100%** กรุณาปรับสไลเดอร์ให้ได้รวม 100% ถ้วนเพื่อให้ได้สูตรอาหารที่สมบูรณ์")

current_nutrition = {"protein": 0.0, "me": 0.0, "calcium": 0.0, "phos": 0.0, "amino": 0.0}
total_moisture = 0.0
total_cost = 0.0
total_risk_score = 0.0

for name, weight in user_weights.items():
    factor = weight / 100.0
    nutrients = INGREDIENT_DATA[name]
    current_nutrition["protein"] += nutrients["protein"] * factor
    current_nutrition["me"] += nutrients["me"] * factor
    current_nutrition["calcium"] += nutrients["calcium"] * factor
    current_nutrition["phos"] += nutrients["phos"] * factor
    current_nutrition["amino"] += nutrients["amino"] * factor
    total_moisture += nutrients.get("moisture", 0.0) * factor
    total_cost += nutrients["price"] * factor
    total_risk_score += factor * nutrients.get("tox_risk", 0)

with creator_right:
    st.markdown("### 📊 หน้าจอติดตามระดับสารอาหารแบบเรียลไทม์")
    for nutrient, key_name, unit in [("โปรตีน", "protein", "%"), ("พลังงาน (ME)", "me", "กิโลแคลอรี/กก."), ("แคลเซียม", "calcium", "%"), ("ฟอสฟอรัส", "phos", "%"), ("กรดอะมิโน", "amino", "%")]:
        cur = current_nutrition[key_name]
        req = adjusted_target[key_name]
        st.write(f"**{nutrient}**: {cur:.2f} / {req:.2f} {unit}")
        st.progress(min(max(cur / req, 0.0), 1.0) if req > 0 else 0.0)
    st.metric(label="💰 ต้นทุนสูตรอาหารผสมเองเฉลี่ยฟาร์มของคุณ", value=f"{total_cost:.2f} บาท / กิโลกรัม")
st.markdown("---")

# ==========================================
# 🧫 7. บล็อกจัดการระบบปฏิบัติการฟาร์ม
# ==========================================
st.markdown("### 📅 4. ระบบการจัดการและการจัดการความเสี่ยงในฟาร์ม")
m_col1, m_col2, m_col3 = st.columns(3, gap="medium")
with m_col1:
    st.markdown("##### 💧 ระบบคำนวณปริมาณน้ำที่ต้องใช้")
    chicken_count = st.number_input("จำนวนไก่ในฟาร์มทั้งหมด (ตัว):", min_value=1, value=1000, step=100)
    base_water = (breed_info['default_feed'] / 1000.0) * 2.2 if current_key == "laying" else 0.15
    calc_water = chicken_count * base_water
    if "ร้อนจัด" in weather_env:
        calc_water *= 1.20
        st.error("🔥 อากาศร้อนจัด! ไก่เสี่ยงเกิดภาวะขาดน้ำ ให้เตรียมน้ำดื่มเพิ่มขึ้นอีก 20%")
    st.metric("ปริมาณน้ำที่ฝูงไก่ต้องกินต่อวัน", f"{calc_water:,.1f} ลิตร")

with m_col2:
    st.markdown("##### 🍄 ระบบตรวจสอบความชื้นและการเกิดเชื้อรา")
    if total_moisture > 12.0:
        st.error(f"⚠️ ความชื้นในอาหารวิกฤต {total_moisture:.1f}% ห้ามเก็บอาหารชุดนี้ไว้นานเกิน 7 วันเด็ดขาด! เสี่ยงต่อสารพิษอะฟลาท็อกซิน")
    else:
        st.success(f"✨ ความชื้นอยู่ในเกณฑ์ปลอดภัย {total_moisture:.1f}% สามารถจัดเก็บในโกดังแห้งได้ 14-30 วัน")
    if total_risk_score >= 1.8:
        st.markdown(f"🧫 **แจ้งเตือนความเสี่ยงเชื้อราสูง:** แนะนำให้ผสมสารจับสารพิษเชื้อรา (**Toxin Binder**) เพิ่มเข้าไปจำนวน **{2.0 * (chicken_count * breed_info['default_feed'] / 1000.0):,.1f} กรัม** สำหรับรอบการผสมนี้")

with m_col3:
    st.markdown("##### 🌙 โปรแกรมแสงสว่างกระตุ้นการไข่")
    enable_midnight = st.checkbox("เปิดใช้ระบบ Midnight Feeding (ให้อาหารมื้อดึก)")
    if enable_midnight:
        st.caption("💡 ข้อแนะนำเชิงเทคนิค: แนะนำให้ย้ายสัดส่วน 'เปลือกหอยบด 65%' มาให้กินในมื้อค่ำหรือมื้อดึก เพื่อช่วยเร่งการสร้างเปลือกไข่ให้หนาขึ้นในช่วงกลางคืน")
st.markdown("---")

# ==========================================
# 📊 8. การวางแผนปริมาณสั่งซื้อและใบจัดซื้อวัตถุดิบ
# ==========================================
st.markdown("### 📅 5. แผนการสำรองวัตถุดิบและประมาณการคำสั่งซื้อ")
total_phase_feed_needed_kg = chicken_count * LIFECYCLE_FEED_BUDGET[current_key]
st.write(f"📦 ยอดสั่งซื้อและปริมาณวัตถุดิบรวมที่ต้องกักตุนเข้าคลังสำหรับฝูงนี้ตลอดเฟสปัจจุบัน: **{total_phase_feed_needed_kg/1000.0:,.2f} ตัน**")
budget_data = []
for name in INGREDIENT_DATA.keys():
    w_kg = (user_weights[name] / 100.0) * total_phase_feed_needed_kg
    if w_kg > 0:
        budget_data.append({"วัตถุดิบ": name, "สัดส่วนการผสม (%)": f"{user_weights[name]}%", "น้ำหนักรวมที่ต้องสั่งซื้อเข้าโกดัง (กก.)": f"{w_kg:,.1f} กก."})
st.dataframe(pd.DataFrame(budget_data), use_container_width=True, hide_index=True)
st.markdown("---")

# ==========================================
# 📈 9. สมุดจดสถิติและกราฟดูสถิติไข่ไก่ประจำวัน [เวอร์ชันแก้ปัญหากลืนสี + อัปเกรดวิเคราะห์วิกฤต]
# ==========================================
st.markdown("### 📈 6. สมุดจดสถิติและกราฟวิเคราะห์ผลผลิตประจำวัน")

# ฐานข้อมูลเก็บสถิติ (รองรับคอลัมน์ "หมายเหตุ" เพิ่มเติม)
if "tracker_data" not in st.session_state:
    st.session_state.tracker_data = pd.DataFrame([
        {"วันที่": "01/06", "สูตรอาหาร": "สูตรเดิม", "อัตราการไข่ (%)": 82.0, "อัตราไข่บุบแตก (%)": 4.5, "หมายเหตุ": "ปกติ"},
        {"วันที่": "02/06", "สูตรอาหาร": "สูตรเดิม", "อัตราการไข่ (%)": 81.5, "อัตราไข่บุบแตก (%)": 5.0, "หมายเหตุ": "ฝนตกหนักตอนบ่าย"},
        {"วันที่": "03/06", "สูตรอาหาร": "สูตร AI แนะนำ", "อัตราการไข่ (%)": 84.0, "อัตราไข่บุบแตก (%)": 2.1, "หมายเหตุ": "เริ่มปรับสูตรอาหารใหม่"},
    ])

# ส่วนคำนวณและแสดงผลภาพรวมแดชบอร์ดด้านบนกราฟ
st.markdown("##### 📊 สรุปภาพรวมผลผลิตในสมุดจดปัจจุบัน")
avg_lay = st.session_state.tracker_data["อัตราการไข่ (%)"].mean()
avg_crack = st.session_state.tracker_data["อัตราไข่บุบแตก (%)"].mean()
last_lay = st.session_state.tracker_data["อัตราการไข่ (%)"].iloc[-1]
last_crack = st.session_state.tracker_data["อัตราไข่บุบแตก (%)"].iloc[-1]

m_lay, m_crack, m_alert = st.columns(3)
with m_lay:
    st.metric(label="🥚 อัตราการไข่เฉลี่ยรวม", value=f"{avg_lay:.2f} %", delta=f"ล่าสุด: {last_lay}%")
with m_crack:
    st.metric(label="💥 อัตราไข่บุบแตกเฉลี่ยรวม", value=f"{avg_crack:.2f} %", delta=f"ล่าสุด: {last_crack}%", delta_color="inverse")
with m_alert:
    # 🚨 ระบบแจ้งเตือนวิกฤตอัตโนมัติหน้างาน
    if last_lay < 80.0:
        st.error("🚨 วิกฤต: อัตราการไข่ล่าสุดต่ำกว่าเกณฑ์ 80%! ไก่กำลังส่งสัญญาณป่วยหรือเครียด")
    elif last_crack > 4.0:
        st.warning("⚠️ เตือนภัย: อัตราไข่แตกสูงเกิน 4%! แคลเซียมในอาหารอาจไม่พอ")
    else:
        st.success("✅ สถานะฝูงไก่: ผลผลิตอยู่ในเกณฑ์สมบูรณ์และปลอดภัยดี")

st.markdown("---")

track_col1, track_col2 = st.columns([4, 6], gap="large")
with track_col1:
    with st.form("supabase_sync_form_final"):
        st.markdown("##### 📝 กรอกรายงานหลังเดินตรวจเล้า")
        in_date = st.text_input("วันที่บันทึก (เช่น 04/06):", value="04/06")
        f_name = st.text_input("วันนี้ใช้สูตรอาหารชื่ออะไร:", value="สูตร AI แนะนำ")
        lay_r = st.number_input("วันนี้เก็บไข่ได้กี่ % (อัตราการไข่):", value=86.2, min_value=0.0, max_value=100.0, step=0.1)
        crack_r = st.number_input("วันนี้มีไข่บุบ/ไข่แตกกี่ %:", value=1.5, min_value=0.0, max_value=100.0, step=0.1)
        note_text = st.text_input("📌 หมายเหตุ/เหตุการณ์สำคัญวันนี้ (ถ้ามี):", value="ปกติ")
        
        if st.form_submit_button("💾 กดบันทึกสถิติวันนี้"):
            new_row = pd.DataFrame([{
                "วันที่": in_date, 
                "สูตรอาหาร": f_name, 
                "อัตราการไข่ (%)": lay_r, 
                "อัตราไข่บุบแตก (%)": crack_r,
                "หมายเหตุ": note_text
            }])
            st.session_state.tracker_data = pd.concat([st.session_state.tracker_data, new_row], ignore_index=True)
            
            payload = {
                "date_record": in_date, 
                "formula_name": f_name, 
                "laying_rate": lay_r, 
                "crack_rate": crack_r, 
                "cost_per_kg": float(total_cost),
                "breed_name": breed_info['name'],
                "notes": note_text
            }
            
            if "your-project" not in SUPABASE_URL and SUPABASE_KEY != "your-anon-key":
                try:
                    headers = {
                        "apikey": SUPABASE_KEY, 
                        "Authorization": f"Bearer {SUPABASE_KEY}", 
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal"
                    }
                    endpoint = f"{SUPABASE_URL}/rest/v1/farm_records"
                    response = requests.post(endpoint, json=payload, headers=headers, timeout=5)
                    
                    if response.status_code in [200, 201]:
                        st.success(f"☁️ บันทึกข้อมูลเข้าสู่ระบบออนไลน์เรียบร้อยแล้ว!")
                    else:
                        st.error(f"❌ เกิดข้อผิดพลาดจากคลาวด์: {response.status_code}")
                except Exception as e:
                    st.error(f"❌ สัญญาณอินเทอร์เน็ตขัดข้อง: {e}")
            else:
                st.info("⚠️ บันทึกข้อมูลลงในเครื่องเรียบร้อยแล้ว (กำลังทำงานในโหมดออฟไลน์)")
            
            st.rerun()

with track_col2:
    # 🎨 บังคับใช้ธีม "plotly_dark" และปรับสีพื้นหลังโปร่งใสเพื่อให้ข้อความเด้งชัดเจนในธีมมืด
    fig = px.line(
        st.session_state.tracker_data, 
        x="วันที่", 
        y=["อัตราการไข่ (%)", "อัตราไข่บุบแตก (%)"], 
        markers=True, 
        template="plotly_dark",
        hover_data=["สูตรอาหาร", "หมายเหตุ"],
        title="📈 กราฟเปรียบเทียบผลผลิตและอัตราไข่แตกประจำวัน"
    )
    
    fig.update_layout(
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)
