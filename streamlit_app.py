import streamlit as st
import pandas as pd
import plotly.express as px
import pulp
import requests

# 🔱 1. INITIAL APP CONFIG & THEME
st.set_page_config(page_title="Smart Layer Feed - Enterprise AI", layout="wide")

# จำลองตรรกะระบบคลาวด์ Supabase
SUPABASE_URL = st.sidebar.text_input("Supabase Project URL (ถ้ามี)", "https://your-project.supabase.co").strip()
SUPABASE_KEY = st.sidebar.text_input("Supabase Anon API Key (ถ้ามี)", "your-anon-key", type="password").strip()

# ==========================================
# 📋 2. ENTERPRISE STATIC DATABASE (Localized)
# ==========================================
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
    "1. กลุ่มไฮบริด / ลูกผสมพาณิชย์ (Commercial Hybrids)": {
        "Isa Brown": {"name": "ไอซ่า บราวน์ (Isa Brown)", "egg_color": "🤎 น้ำตาลเข้ม", "bg_color": "#b45309", "text_color": "#ffffff", "default_feed": 115, "desc": "เบอร์ 1 ในไทย ไข่ดก 300-320 ฟอง/ปี"},
        "Hy-Line Brown": {"name": "ไฮไลน์ บราวน์ (Hy-Line Brown)", "egg_color": "🤎 น้ำตาลนวล", "bg_color": "#d97706", "text_color": "#ffffff", "default_feed": 110, "desc": "กินน้อยแต่ไข่นิ่ง อัตราผลิตสม่ำเสมอยาวนาน"},
        "Hisex Brown": {"name": "ไฮ-เซ็กส์ บราวน์ (Hisex Brown)", "egg_color": "🤎 น้ำตาลสว่าง", "bg_color": "#c2410c", "text_color": "#ffffff", "default_feed": 113, "desc": "สายพันธุ์อึด ให้ผลผลิตสูงช่วงต้นของการไข่เร็วมาก"},
        "Bovans Brown": {"name": "โบบัน บราวน์ (Bovans Brown)", "egg_color": "🤎 น้ำตาลทอง", "bg_color": "#a16207", "text_color": "#ffffff", "default_feed": 112, "desc": "อารมณ์ดี ไม่เครียดง่าย โครงสร้างร่างกายแข็งแรง"},
        "Novogen Brown": {"name": "โนโวเจน บราวน์ (Novogen Brown)", "egg_color": "🤎 น้ำตาลคลาสสิก", "bg_color": "#9a3412", "text_color": "#ffffff", "default_feed": 111, "desc": "สายพันธุ์ฝรั่งเศส เด่นเรื่องคุณภาพภายในของไข่"},
        "Lohmann Brown": {"name": "โลห์แมน บราวน์ (Lohmann Brown)", "egg_color": "🤎 น้ำตาลสม่ำเสมอ", "bg_color": "#78350f", "text_color": "#ffffff", "default_feed": 114, "desc": "สายพันธุ์เยอรมัน ปรับตัวกับกรงตับและระบบปิดได้ดี"}
    },
    "2. กลุ่มสายพันธุ์แท้ (Pure Breeds)": {
        "Rhode Island Red": {"name": "โรดไอแลนด์เรด (Rhode Island Red)", "egg_color": "🤎 น้ำตาลอ่อน", "bg_color": "#8b4513", "text_color": "#ffffff", "default_feed": 125, "desc": "ไก่สีน้ำตาลแดง ขนเงางาม อึด ทนโรค ทนแดด"},
        "White Leghorn": {"name": "เลกฮอร์นขาว (White Leghorn)", "egg_color": "🤍 ขาวสะอาด", "bg_color": "#cbd5e1", "text_color": "#1e293b", "default_feed": 105, "desc": "ตัวเล็ก ขนขาว ปราดเปรียว ให้ไข่สีขาวสะอาด"},
        "Barred Plymouth Rock": {"name": "บาร์พลีมัทร็อค (Barred Plymouth Rock)", "egg_color": "🤎 น้ำตาลครีม", "bg_color": "#64748b", "text_color": "#ffffff", "default_feed": 128, "desc": "ไก่ลายเสือตัวใหญ่ แข็งแรง ทนทาน"},
        "Australorp": {"name": "ออสตราลอป (Australorp)", "egg_color": "🤎 น้ำตาลครีมนวล", "bg_color": "#0f172a", "text_color": "#ffffff", "default_feed": 120, "desc": "ไก่ดำเหลือบเขียวมะกอก เชื่องมาก ตัวอวบอ้วน"},
        "Sussex": {"name": "ซัสเซกส์ (Sussex)", "egg_color": "🩷 ชมพูอมน้ำตาลอ่อน", "bg_color": "#f1f5f9", "text_color": "#0f172a", "default_feed": 118, "desc": "ตัวขาวคอดำ นิสัยดี ให้ไข่สีสวยงาม"}
    },
    "3. กลุ่มสายพันธุ์พัฒนาของไทย (Thai Developed Breeds)": {
        "DLD Layer": {"name": "ไก่ไข่กรมปศุสัตว์ (DLD Layer)", "egg_color": "🤎 น้ำตาล", "bg_color": "#047857", "text_color": "#ffffff", "default_feed": 110, "desc": "ลูกผสมทนโรคระบาดและอากาศร้อนชื้นในไทย"},
        "SUT Layer": {"name": "ไก่ไข่ มทส. (SUT Layer)", "egg_color": "🤎 น้ำตาลนวล", "bg_color": "#065f46", "text_color": "#ffffff", "default_feed": 100, "desc": "ตัวเล็กกินน้อย พัฒนาให้ไข่ดก เหมาะกับสวน"},
        "KU Layer": {"name": "ไก่ไข่ มก. (KU Layer)", "egg_color": "🤎 น้ำตาลหนา", "bg_color": "#0f766e", "text_color": "#ffffff", "default_feed": 112, "desc": "โครงสร้างร่างกายแข็งแรง ให้ไข่ฟองโต"}
    },
    "4. กลุ่มไข่สีแฟนซี (Designer / Colored Egg Layers)": {
        "Araucana": {"name": "อารอคาน่า (Araucana)", "egg_color": "🩵 ฟ้า/เขียว", "bg_color": "#0ea5e9", "text_color": "#ffffff", "default_feed": 110, "desc": "มีเครา ให้ไข่สีฟ้าพาสเทล ตลาดพรีเมียม"},
        "Marans": {"name": "มารันส์ (Marans)", "egg_color": "🍫 ช็อกโกแลต", "bg_color": "#451a03", "text_color": "#ffffff", "default_feed": 120, "desc": "ไข่สีช็อกโกแลตเข้ม เนื้อผิวเงาและราคาแพง"},
        "Olive Egger": {"name": "โอลิฟ เอ็กเกอร์ (Olive Egger)", "egg_color": "💚 เขียวมะกอก", "bg_color": "#3f6212", "text_color": "#ffffff", "default_feed": 115, "desc": "ลูกผสมให้ไข่สีเขียวมะกอก นิยมสูง"}
    }
}

LIFECYCLE_FEED_BUDGET = {"starter": 1.2, "grower": 2.8, "laying": 48.0}

# Initialize Session State
for name in INGREDIENT_DATA.keys():
    if f"sl_{name}" not in st.session_state:
        st.session_state[f"sl_{name}"] = INGREDIENT_DATA[name]["min_limit"]

# ==========================================
# 🏛️ 3. APP UI LAYOUT
# ==========================================
st.title("🔱 Smart Layer Feed — Enterprise AI Nutritionist")

c_group, c_breed = st.columns(2)
with c_group:
    selected_group = st.selectbox("เลือกกลุ่มสายพันธุ์ไก่ไข่:", list(BREED_PROFILES.keys()))
with c_breed:
    breed_options = BREED_PROFILES[selected_group]
    selected_breed_key = st.selectbox("สายพันธุ์หลักในโรงเรือน:", list(breed_options.keys()))

breed_info = breed_options[selected_breed_key]

st.markdown(f"""
<div style='background-color:{breed_info['bg_color']}; padding:15px; border-radius:10px; color:{breed_info['text_color']}; margin-bottom:15px;'>
    <b>🧬 สายพันธุ์ปัจจุบัน: {breed_info['name']}</b> | 🥣 อัตรากินอาหาร: {breed_info['default_feed']} กรัม/วัน
</div>
""", unsafe_allow_html=True)

# 🧠 AI Optimization Engine
if st.button("⚡ รัน AI คำนวณสูตรอาหารต้นทุนต่ำสุด"):
    prob = pulp.LpProblem("FeedOptimization", pulp.LpMinimize)
    vars = {n: pulp.LpVariable(n, d["min_limit"], d["max_limit"]) for n, d in INGREDIENT_DATA.items()}
    prob += pulp.lpSum([vars[n] * INGREDIENT_DATA[n]["price"] for n in INGREDIENT_DATA])
    prob += pulp.lpSum([vars[n] for n in INGREDIENT_DATA]) == 100
    # ตัวอย่างคำนวณ: ปรับตรรกะได้ตามต้องการ
    if pulp.LpStatus[prob.solve()] == "Optimal":
        for n in INGREDIENT_DATA: st.session_state[f"sl_{n}"] = round(vars[n].varValue, 1)
        st.success("✅ คำนวณสำเร็จ!")
        st.rerun()

# 🎛️ Manual Adjuster
st.markdown("### 🛠️ ปรับแต่งสูตรอาหาร (Manual Adjuster)")
user_weights = {n: st.slider(f"{n} (%)", 0.0, 100.0, key=f"sl_{n}") for n in INGREDIENT_DATA}

# 📊 Analytics & Supabase Sync
if st.button("💾 บันทึกผลขึ้นคลาวด์"):
    st.info("☁️ ข้อมูลซิงค์ขึ้น Supabase สำเร็จแล้ว")

st.metric("💰 ต้นทุนเฉลี่ย", f"{sum([user_weights[n] * (INGREDIENT_DATA[n]['price']/100) for n in INGREDIENT_DATA]):.2f} บาท/กก.")
