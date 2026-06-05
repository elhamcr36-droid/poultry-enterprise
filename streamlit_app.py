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
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.65), rgba(0, 0, 0, 0.65)), 
                          url("https://images.unsplash.com/photo-1506976785307-8732e854ad03?q=80&w=1920");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, [data-testid="stHeader"] {
        color: #ffffff !important;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.9) !important;
    }
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
    .content-card {
        background-color: rgba(0, 0, 0, 0.60) !important;
        padding: 25px;
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(5px);
        margin-bottom: 20px;
    }
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
# 📋 2. คลังฐานข้อมูลวัตถุดิบขนาดใหญ่ (25 วัตถุดิบยอดนิยมในไทย)
# ==========================================
MASTER_INGREDIENT_DICTIONARY = {
    "ข้าวโพดบด": {"price": 13.5, "protein": 8.5, "me": 3300.0, "calcium": 0.02, "phos": 0.25, "lysine": 0.24, "methionine": 0.18, "tryptophan": 0.07, "threonine": 0.29, "moisture": 12.0, "fiber": 2.2, "fat": 3.8, "ash": 1.3, "tox_risk": 3, "min_limit": 20.0, "max_limit": 70.0},
    "รำละเอียด": {"price": 11.0, "protein": 12.0, "me": 2400.0, "calcium": 0.05, "phos": 1.35, "lysine": 0.54, "methionine": 0.22, "tryptophan": 0.12, "threonine": 0.43, "moisture": 10.5, "fiber": 12.0, "fat": 13.0, "ash": 7.8, "tox_risk": 3, "min_limit": 0.0, "max_limit": 30.0},
    "ปลายข้าว": {"price": 14.5, "protein": 8.0, "me": 3360.0, "calcium": 0.04, "phos": 0.10, "lysine": 0.22, "methionine": 0.15, "tryptophan": 0.08, "threonine": 0.26, "moisture": 12.0, "fiber": 1.0, "fat": 1.5, "ash": 0.5, "tox_risk": 1, "min_limit": 0.0, "max_limit": 40.0},
    "กากถั่วเหลือง (44%)": {"price": 18.5, "protein": 44.0, "me": 2420.0, "calcium": 0.25, "phos": 0.60, "lysine": 2.70, "methionine": 0.62, "tryptophan": 0.61, "threonine": 1.72, "moisture": 11.5, "fiber": 5.5, "fat": 1.5, "ash": 6.0, "tox_risk": 1, "min_limit": 5.0, "max_limit": 40.0},
    "ปลาป่น (โปรตีน 60%)": {"price": 32.0, "protein": 60.0, "me": 2850.0, "calcium": 5.00, "phos": 3.00, "lysine": 4.50, "methionine": 1.80, "tryptophan": 0.60, "threonine": 2.40, "moisture": 10.0, "fiber": 1.0, "fat": 8.0, "ash": 15.0, "tox_risk": 1, "min_limit": 0.0, "max_limit": 15.0},
    "เปลือกหอยบด": {"price": 4.0, "protein": 0.0, "me": 0.0, "calcium": 38.00, "phos": 0.04, "lysine": 0.00, "methionine": 0.00, "tryptophan": 0.00, "threonine": 0.00, "moisture": 0.5, "fiber": 0.0, "fat": 0.0, "ash": 92.0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 12.0},
    "ไดแคลเซียมฟอสเฟต (DCP)": {"price": 28.0, "protein": 0.0, "me": 0.0, "calcium": 21.00, "phos": 18.00, "lysine": 0.00, "methionine": 0.00, "tryptophan": 0.00, "threonine": 0.00, "moisture": 1.0, "fiber": 0.0, "fat": 0.0, "ash": 80.0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 5.0},
    "พรีมิกซ์ไก่ไข่ (วิตามินรวม)": {"price": 120.0, "protein": 0.0, "me": 0.0, "calcium": 4.00, "phos": 1.00, "lysine": 0.00, "methionine": 0.00, "tryptophan": 0.00, "threonine": 0.00, "moisture": 2.0, "fiber": 0.0, "fat": 0.0, "ash": 75.0, "tox_risk": 0, "min_limit": 0.2, "max_limit": 0.5},
    
    # วัตถุดิบเพิ่มเติมกลุ่มคาร์โบไฮเดรต & พลังงาน
    "ข้าวเปลือกบด": {"price": 10.5, "protein": 8.0, "me": 2650.0, "calcium": 0.08, "phos": 0.30, "lysine": 0.25, "methionine": 0.16, "tryptophan": 0.09, "threonine": 0.28, "moisture": 11.5, "fiber": 9.0, "fat": 2.0, "ash": 4.5, "tox_risk": 2, "min_limit": 0.0, "max_limit": 30.0},
    "มันเส้นบดละเอียด": {"price": 9.5, "protein": 2.2, "me": 3000.0, "calcium": 0.18, "phos": 0.09, "lysine": 0.05, "methionine": 0.03, "tryptophan": 0.02, "threonine": 0.07, "moisture": 12.5, "fiber": 3.5, "fat": 0.5, "ash": 2.2, "tox_risk": 2, "min_limit": 0.0, "max_limit": 20.0},
    "ข้าวบาร์เลย์": {"price": 15.0, "protein": 11.5, "me": 2770.0, "calcium": 0.06, "phos": 0.35, "lysine": 0.42, "methionine": 0.20, "tryptophan": 0.14, "threonine": 0.39, "moisture": 11.0, "fiber": 5.0, "fat": 1.9, "ash": 2.6, "tox_risk": 1, "min_limit": 0.0, "max_limit": 25.0},
    "น้ำมันปาล์มดิบ": {"price": 34.0, "protein": 0.0, "me": 8400.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "tryptophan": 0.00, "threonine": 0.00, "moisture": 0.5, "fiber": 0.0, "fat": 99.0, "ash": 0.0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 4.0},
    "น้ำมันถั่วเหลือง": {"price": 42.0, "protein": 0.0, "me": 8800.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "tryptophan": 0.00, "threonine": 0.00, "moisture": 0.2, "fiber": 0.0, "fat": 99.8, "ash": 0.0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 3.0},
    
    # วัตถุดิบเพิ่มเติมกลุ่มโปรตีนพืช & พลอยได้
    "กากถั่วเหลืองอบ (48%)": {"price": 20.0, "protein": 48.0, "me": 2450.0, "calcium": 0.28, "phos": 0.65, "lysine": 3.00, "methionine": 0.67, "tryptophan": 0.65, "threonine": 1.85, "moisture": 11.0, "fiber": 4.0, "fat": 1.5, "ash": 6.2, "tox_risk": 1, "min_limit": 0.0, "max_limit": 40.0},
    "กากเนื้อปาล์มสกัด (เนล)": {"price": 7.5, "protein": 15.0, "me": 1750.0, "calcium": 0.31, "phos": 0.62, "lysine": 0.52, "methionine": 0.29, "tryptophan": 0.16, "threonine": 0.54, "moisture": 10.0, "fiber": 15.0, "fat": 7.2, "ash": 4.5, "tox_risk": 2, "min_limit": 0.0, "max_limit": 10.0},
    "กากถั่วลิสง": {"price": 16.0, "protein": 45.0, "me": 2610.0, "calcium": 0.20, "phos": 0.55, "lysine": 1.60, "methionine": 0.52, "tryptophan": 0.48, "threonine": 1.20, "moisture": 9.5, "fiber": 6.0, "fat": 1.8, "ash": 5.5, "tox_risk": 4, "min_limit": 0.0, "max_limit": 10.0},
    "กากเมล็ดทานตะวัน": {"price": 12.0, "protein": 32.0, "me": 1900.0, "calcium": 0.40, "phos": 0.90, "lysine": 1.10, "methionine": 0.70, "tryptophan": 0.40, "threonine": 1.15, "moisture": 10.0, "fiber": 19.0, "fat": 2.5, "ash": 6.0, "tox_risk": 1, "min_limit": 0.0, "max_limit": 12.0},
    "กากเบียร์แห้ง (DDGS)": {"price": 11.5, "protein": 27.0, "me": 2200.0, "calcium": 0.20, "phos": 0.75, "lysine": 0.80, "methionine": 0.55, "tryptophan": 0.25, "threonine": 1.00, "moisture": 10.0, "fiber": 9.0, "fat": 8.0, "ash": 5.0, "tox_risk": 2, "min_limit": 0.0, "max_limit": 15.0},
    "ใบกระถินป่นอบแห้ง": {"price": 9.0, "protein": 22.0, "me": 1200.0, "calcium": 1.80, "phos": 0.25, "lysine": 1.05, "methionine": 0.32, "tryptophan": 0.28, "threonine": 0.85, "moisture": 9.0, "fiber": 14.0, "fat": 4.5, "ash": 11.0, "tox_risk": 3, "min_limit": 0.0, "max_limit": 5.0},
    "ยีสต์แห้งเลี้ยงสัตว์": {"price": 45.0, "protein": 45.0, "me": 2600.0, "calcium": 0.15, "phos": 1.40, "lysine": 3.40, "methionine": 0.75, "tryptophan": 0.55, "threonine": 2.10, "moisture": 8.0, "fiber": 2.5, "fat": 1.5, "ash": 7.5, "tox_risk": 1, "min_limit": 0.0, "max_limit": 5.0},
    "ถั่วเขียวป่น": {"price": 18.0, "protein": 24.0, "me": 2950.0, "calcium": 0.12, "phos": 0.40, "lysine": 1.65, "methionine": 0.28, "tryptophan": 0.23, "threonine": 0.88, "moisture": 11.0, "fiber": 4.5, "fat": 1.2, "ash": 3.8, "tox_risk": 1, "min_limit": 0.0, "max_limit": 15.0},
    
    # สารเติมแต่ง & กรดอะมิโนบริสุทธิ์
    "แอล-ไลซีน (L-Lysine)": {"price": 85.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 78.00, "methionine": 0.00, "tryptophan": 0.00, "threonine": 0.00, "moisture": 1.0, "fiber": 0.0, "fat": 0.0, "ash": 0.5, "tox_risk": 0, "min_limit": 0.0, "max_limit": 1.0},
    "ดีแอล-เมทไธโอนีน": {"price": 140.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 99.00, "tryptophan": 0.00, "threonine": 0.00, "moisture": 0.5, "fiber": 0.0, "fat": 0.0, "ash": 0.2, "tox_risk": 0, "min_limit": 0.0, "max_limit": 1.0},
    "เกลือแกง (NaCl)": {"price": 6.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "tryptophan": 0.00, "threonine": 0.00, "moisture": 1.0, "fiber": 0.0, "fat": 0.0, "ash": 98.0, "tox_risk": 0, "min_limit": 0.1, "max_limit": 0.4},
    "ผงชอล์ก (แคลเซียมคาร์บอเนต)": {"price": 3.5, "protein": 0.0, "me": 0.0, "calcium": 39.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "tryptophan": 0.00, "threonine": 0.00, "moisture": 0.5, "fiber": 0.0, "fat": 0.0, "ash": 95.0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 10.0}
}

# กำหนดวัตถุดิบเริ่มต้นที่จะให้แสดงในหน้าแรกตั้งแต่เปิดแอป
if "ingredient_data" not in st.session_state:
    st.session_state.ingredient_data = {
        "ข้าวโพดบด": MASTER_INGREDIENT_DICTIONARY["ข้าวโพดบด"],
        "รำละเอียด": MASTER_INGREDIENT_DICTIONARY["รำละเอียด"],
        "ปลายข้าว": MASTER_INGREDIENT_DICTIONARY["ปลายข้าว"],
        "กากถั่วเหลือง (44%)": MASTER_INGREDIENT_DICTIONARY["กากถั่วเหลือง (44%)"],
        "ปลาป่น (โปรตีน 60%)": MASTER_INGREDIENT_DICTIONARY["ปลาป่น (โปรตีน 60%)"],
        "เปลือกหอยบด": MASTER_INGREDIENT_DICTIONARY["เปลือกหอยบด"],
        "ไดแคลเซียมฟอสเฟต (DCP)": MASTER_INGREDIENT_DICTIONARY["ไดแคลเซียมฟอสเฟต (DCP)"],
        "พรีมิกซ์ไก่ไข่ (วิตามินรวม)": MASTER_INGREDIENT_DICTIONARY["พรีมิกซ์ไก่ไข่ (วิตามินรวม)"]
    }

STAGE_NUTRITION_TARGETS = {
    "starter": {"name": "ลูกไก่ไข่ 0 - 6 สัปดาห์ (Starter)", "protein": 20.0, "me": 2900.0, "calcium": 1.00, "phos": 0.45, "lysine": 1.10, "methionine": 0.45, "tryptophan": 0.20, "threonine": 0.74, "fiber": 4.0, "fat": 3.5, "ash": 7.0},
    "grower": {"name": "ไก่รุ่นไข่ 6 - 16 สัปดาห์ (Grower)", "protein": 16.0, "me": 2750.0, "calcium": 0.90, "phos": 0.40, "lysine": 0.85, "methionine": 0.38, "tryptophan": 0.16, "threonine": 0.60, "fiber": 4.5, "fat": 3.0, "ash": 7.5},
    "laying": {"name": "ไก่ไข่ระยะให้ผลผลิต 16 สัปดาห์ขึ้นไป (Laying)", "protein": 17.5, "me": 2750.0, "calcium": 4.10, "phos": 0.42, "lysine": 0.88, "methionine": 0.42, "tryptophan": 0.19, "threonine": 0.65, "fiber": 4.0, "fat": 3.5, "ash": 8.0}
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
    st.session_state.optimized_weights["ข้าวโพดบด"] = 54.0
    st.session_state.optimized_weights["กากถั่วเหลือง (44%)"] = 23.0
    st.session_state.optimized_weights["รำละเอียด"] = 13.0
    st.session_state.optimized_weights["ปลาป่น (โปรตีน 60%)"] = 5.0
    st.session_state.optimized_weights["เปลือกหอยบด"] = 4.4
    st.session_state.optimized_weights["ไดแคลเซียมฟอสเฟต (DCP)"] = 0.4
    st.session_state.optimized_weights["พรีมิกซ์ไก่ไข่ (วิตามินรวม)"] = 0.2

for name in st.session_state.ingredient_data.keys():
    if name not in st.session_state.optimized_weights:
        st.session_state.optimized_weights[name] = 0.0

def calculate_current_formulation():
    nut_calc = {"protein": 0.0, "me": 0.0, "calcium": 0.0, "phos": 0.0, "lysine": 0.0, "methionine": 0.0, "tryptophan": 0.0, "threonine": 0.0, "fiber": 0.0, "fat": 0.0, "ash": 0.0}
    cost, moisture, risk = 0.0, 0.0, 0.0
    for name, weight in st.session_state.optimized_weights.items():
        f = weight / 100.0
        ing = st.session_state.ingredient_data.get(name, {})
        if ing:
            for k in nut_calc.keys():
                nut_calc[k] += ing.get(k, 0.0) * f
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
    
    st.session_state.current_key = st.selectbox("🗓️ เลือกช่วงอายุ/โปรไฟล์ของไก่:", options=list(STAGE_NUTRITION_TARGETS.keys()), format_func=lambda x: STAGE_NUTRITION_TARGETS[x]["name"])
    
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
    adjusted_target = {k: v * density_factor for k, v in target.items() if k != "name" and k != "me"}
    adjusted_target["me"] = target["me"]

    st.session_state.use_phytase = st.checkbox("🧪 ใส่เอนไซม์ไฟเตส (ลดเป้าหมายฟอสฟอรัสลง 0.10% อัตโนมัติ)", value=st.session_state.use_phytase)
    if st.session_state.use_phytase:
        adjusted_target["phos"] = max(0.25, adjusted_target["phos"] - 0.10)

    if st.button("⚡ สั่งคำนวณสูตรอาหารต้นทุนต่ำที่สุดด้วย AI (Run AI Least-Cost Optimizer)"):
        prob = pulp.LpProblem("LeastCostLayerFeedMega", pulp.LpMinimize)
        ingredient_vars = {name: pulp.LpVariable(name, lowBound=data.get("min_limit", 0.0), upBound=data.get("max_limit", 100.0)) for name, data in st.session_state.ingredient_data.items()}
        
        prob += pulp.lpSum([ingredient_vars[name] * (st.session_state.ingredient_data[name]["price"] / 100.0) for name in st.session_state.ingredient_data.keys()])
        prob += pulp.lpSum([ingredient_vars[name] for name in st.session_state.ingredient_data.keys()]) == 100.0
        
        for key in ["protein", "me", "calcium", "phos", "lysine", "methionine"]:
            prob += pulp.lpSum([ingredient_vars[name] * (st.session_state.ingredient_data[name].get(key, 0.0) / 100.0) for name in st.session_state.ingredient_data.keys()]) >= adjusted_target[key]
        
        status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
        if pulp.LpStatus[status] == "Optimal":
            for name in st.session_state.ingredient_data.keys():
                st.session_state.optimized_weights[name] = round(ingredient_vars[name].varValue, 1)
            st.success("🎉 AI ค้นพบสัดส่วนสูตรที่ราคาประหยัดที่สุดเรียบร้อยแล้ว!")
            st.rerun()
        else:
            st.error("❌ ไม่สามารถผสานสูตรด้วยระบบอัตโนมัติได้เนื่องจากเกณฑ์โภชนาการขัดแย้งกันเกินไป แนะนำให้สลับมาปรับมือด้านล่างชั่วคราวครับ")

    st.markdown("---")
    creator_left, creator_right = st.columns(2, gap="large")
    
    with creator_left:
        st.markdown("#### 🔧 1. ปรับสัดส่วนวัตถุดิบด้วยมือ (%)")
        st.markdown("*สามารถเลื่อนสไลเดอร์ หรือกรอกตัวเลขที่ต้องการลงในช่องขวามือตรงๆ ได้เลยครับ*")
        
        user_weights = {}
        for name in list(st.session_state.ingredient_data.keys()):
            val = float(st.session_state.optimized_weights.get(name, 0.0))
            st.write(f"**🌾 {name}**")
            slider_col, input_col = st.columns([7, 3])
            with slider_col:
                s_val = st.slider(f"ปรับสัดส่วน {name}", 0.0, 100.0, val, step=0.1, label_visibility="collapsed", key=f"sl_bar_{name}")
            with input_col:
                i_val = st.number_input(f"ระบุตัวเลข {name}", min_value=0.0, max_value=100.0, value=s_val, step=0.1, format="%.1f", label_visibility="collapsed", key=f"num_in_{name}")
            user_weights[name] = i_val
            
        st.session_state.optimized_weights = user_weights
        total_sum = sum(user_weights.values())
        st.markdown(f"**🔢 น้ำหนักรวมสูตรตอนนี้:** `{total_sum:.1f}%` (เป้าหมายคือ 100%)")
        if not (99.9 <= total_sum <= 100.1):
            st.warning("⚠️ สัดส่วนรวมยังไม่ครบ 100% กรุณาปรับให้อยู่ในเกณฑ์พอดี")

    with creator_right:
        st.markdown("#### 🩺 2. ระดับสารอาหารจริงเทียบกับเป้าหมาย")
        nutrient_display = [
            ("🥩 โปรตีนรวม (Crude Protein)", "protein", "%"),
            ("⚡ พลังงานใช้ประโยชน์ได้ (ME)", "me", "kcal/kg"),
            ("🦴 แคลเซียม (Calcium)", "calcium", "%"),
            ("🧪 ฟอสฟอรัสที่เป็นประโยชน์ (Phos)", "phos", "%"),
            ("🧪 กรดอะมิโน ไลซีน (Lysine)", "lysine", "%"),
            ("🧪 เมทไธโอนีน (Methionine)", "methionine", "%"),
            ("🧬 ทริปโตเฟน (Tryptophan)", "tryptophan", "%"),
            ("🧬 ทรีโอนีน (Threonine)", "threonine", "%"),
            ("🌾 กากใยรวม (Crude Fiber)", "fiber", "%"),
            ("🌽 ไขมันรวม (Crude Fat)", "fat", "%"),
            ("🌋 เถ้า (Ash/Minerals)", "ash", "%")
        ]
        for label, key_name, unit in nutrient_display:
            cur = current_nutrition[key_name]
            req = adjusted_target.get(key_name, 0.0)
            st.write(f"**{label}**: {cur:.2f} / {req:.2f} {unit}")
            st.progress(min(max(cur / req, 0.0), 1.0) if req > 0 else 0.0)
            
        st.markdown("---")
        if total_moisture > 12.0:
            st.markdown(f"💧 **ความชื้นสะสมสูตร:** <span style='color:#ef4444; font-weight:bold;'>{total_moisture:.1f}% 🔴 เสี่ยงราขึ้น</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"💧 **ความชื้นสะสมสูตร:** <span style='color:#22c55e; font-weight:bold;'>{total_moisture:.1f}% 🟢 ปลอดภัย</span>", unsafe_allow_html=True)
            
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
                new_row = {"วันที่": in_date, "อัตราการไข่ (%)": lay_r, "อัตราไข่บุบแตก (%)": crack_r, "น้ำหนักไข่รวม (กก.)": egg_w, "กำไรสุทธิวันนี้ (บาท)": p_today}
                st.session_state.tracker_data = pd.concat([st.session_state.tracker_data, pd.DataFrame([new_row])], ignore_index=True)
                st.success("บันทึกข้อมูลสำเร็จ!")
                st.rerun()
                
    with track_col2:
        st.markdown("##### 📊 กราฟวิเคราะห์แนวโน้มอัตราผลิตไข่")
        fig_prod = go.Figure()
        fig_prod.add_trace(go.Scatter(x=df_track["วันที่"], y=df_track["อัตราการไข่ (%)"], name="อัตราการไข่ (%)", line=dict(color='#22c55e', width=3)))
        fig_prod.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=280, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"))
        st.plotly_chart(fig_prod, use_container_width=True)

    st.dataframe(df_track, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


# --- [แท็บที่ 3]: ระบบหลังบ้าน ---
with page_tabs[2]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 📦 ระบบหลังบ้าน & จัดการคลังวัตถุดิบอาหารสัตว์")
    
    # ➕ 1. ระบบกล่องเลือกวัตถุดิบอัจฉริยะ (Dropdown Selectbox) ดึงข้อมูลอัตโนมัติ
    st.markdown("### 📥 เลือกเพิ่มวัตถุดิบจากคลังมาตรฐานปศุสัตว์ไทย (25 ชนิด)")
    st.markdown("เลือกชื่อวัตถุดิบที่ต้องการจากกล่องด้านล่าง ระบบจะดึงค่าสารอาหารที่คำนวณตามแล็บมาตรฐานมาให้ทันทีโดยไม่ต้องจำตัวเลขครับ")
    
    # กรองเอาเฉพาะวัตถุดิบในฐานข้อมูลหลักที่ยังไม่มีในสูตรปัจจุบัน เพื่อไม่ให้เพิ่มซ้ำซ้อน
    available_to_add = [name for name in MASTER_INGREDIENT_DICTIONARY.keys() if name not in st.session_state.ingredient_data]
    
    if available_to_add:
        selected_ing_to_add = st.selectbox("🌾 เลือกวัตถุดิบที่ต้องการเพิ่มเข้าฟาร์มของคุณ:", available_to_add)
        
        # แสดงตารางคุณค่าสารอาหารตัวที่จะเพิ่มให้ผู้ใช้ดูก่อนกดบันทึก
        preview_data = MASTER_INGREDIENT_DICTIONARY[selected_ing_to_add]
        st.markdown(f"**📋 ข้อมูลโภชนาการพรีวิวของ {selected_ing_to_add} (ราคาแนะนำ: {preview_data['price']} บาท/กก.)**")
        
        df_preview = pd.DataFrame([{
            "ราคา (บาท)": preview_data["price"], "โปรตีน (%)": preview_data["protein"], "พลังงาน (kcal)": preview_data["me"],
            "แคลเซียม (%)": preview_data["calcium"], "ฟอสฟอรัส (%)": preview_data["phos"], "ไลซีน (%)": preview_data["lysine"],
            "เมทไธโอนีน (%)": preview_data["methionine"], "กากใย (%)": preview_data["fiber"], "ความชื้น (%)": preview_data["moisture"]
        }])
        st.dataframe(df_preview, use_container_width=True, hide_index=True)
        
        if st.button(f"✨ กดเพิ่ม '{selected_ing_to_add}' เข้าสู่สูตรอาหารหน้าแรก", type="primary"):
            st.session_state.ingredient_data[selected_ing_to_add] = MASTER_INGREDIENT_DICTIONARY[selected_ing_to_add]
            st.session_state.optimized_weights[selected_ing_to_add] = 0.0  # ตั้งค่าสัดส่วนเริ่มต้นเป็น 0%
            st.success(f"🎉 เพิ่ม '{selected_ing_to_add}' เรียบร้อย! ระบบเปิดสไลเดอร์และช่องป้อนตัวเลขที่หน้าแรกให้ทำงานทันที")
            st.rerun()
    else:
        st.info("💡 คุณได้เพิ่มวัตถุดิบครบทั้ง 25 ชนิดที่มีในฐานข้อมูลหลักเข้าสู่ระบบเรียบร้อยแล้ว!")

    st.markdown("---")

    # 💵 2. ตารางแสดงและปรับราคาท้องถิ่น
    st.markdown("### 📝 รายการวัตถุดิบและราคาปัจจุบันในฟาร์มของคุณ")
    st.markdown("สามารถเดินเช็กราคาท้องตลาด แล้วแก้ไขตัวเลขราคาของแต่ละตัวด้านล่างนี้ให้ตรงกับหน้าฟาร์มจริงได้เลยครับ")
    
    current_ingredients = st.session_state.ingredient_data
    col_left, col_right = st.columns(2, gap="large")
    updated_prices = {}
    ing_names = list(current_ingredients.keys())
    half_size = (len(ing_names) + 1) // 2
    
    with col_left:
        for name in ing_names[:half_size]:
            old_price = current_ingredients[name]["price"]
            updated_prices[name] = st.number_input(f"💵 ราคา {name} (บาท/กก.)", min_value=0.0, value=float(old_price), step=0.1, format="%.2f", key=f"bk_price_{name}")
    with col_right:
        for name in ing_names[half_size:]:
            old_price = current_ingredients[name]["price"]
            updated_prices[name] = st.number_input(f"💵 ราคา {name} (บาท/กก.)", min_value=0.0, value=float(old_price), step=0.1, format="%.2f", key=f"bk_price_{name}")

    st.markdown("---")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("💾 ยืนยันบันทึกราคาทุกอย่าง (Save Prices)", type="primary", use_container_width=True):
            for name, new_p in updated_prices.items():
                st.session_state.ingredient_data[name]["price"] = new_p
            st.success("🎉 อัปเดตราคาทั้งหมดเรียบร้อยแล้ว!")
            st.rerun()
            
    with col_btn2:
        if st.button("🔄 รีเซ็ตคลังกลับค่าเริ่มต้นโรงงาน", use_container_width=True):
            if "ingredient_data" in st.session_state: del st.session_state["ingredient_data"]
            if "optimized_weights" in st.session_state: del st.session_state["optimized_weights"]
            st.success("รีเซ็ตระบบเรียบร้อย")
            st.rerun()
            
    st.markdown("</div>", unsafe_allow_html=True)

    # --- ส่วนใบสั่งซื้อ ---
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 📝 ใบสั่งซื้อวัตถุดิบสำหรับเดินไปเข้าร้านค้า")
    total_feed_needed_kg = st.session_state.chicken_count * LIFECYCLE_FEED_BUDGET[st.session_state.current_key]
    st.info(f"📊 สำหรับไก่จำนวน **{st.session_state.chicken_count:,} ตัว** ต้องใช้อาหารรวมทั้งหมด **{total_feed_needed_kg:,.1f} กิโลกรัม**")
    
    budget_data = []
    for name, weight in st.session_state.optimized_weights.items():
        w_kg = (weight / 100.0) * total_feed_needed_kg
        if w_kg > 0:
            p_unit = st.session_state.ingredient_data.get(name, {}).get("price", 0.0)
            budget_data.append({
                "รายการวัตถุดิบที่ต้องซื้อ": name, "สัดส่วนในสูตร": f"{weight}%",
                "น้ำหนักรวมที่ต้องใช้ (กิโลกรัม)": f"{w_kg:,.1f} กก.", "คิดเป็นจำนวนกระสอบ (30 กก.)": f"~ {round(w_kg / 30, 1)} กระสอบ",
                "ประมาณการเงินที่ต้องเตรียม (บาท)": f"{round(w_kg * p_unit, 2):,} บาท"
            })
            
    df_budget = pd.DataFrame(budget_data)
    if not df_budget.empty:
        st.dataframe(df_budget, use_container_width=True, hide_index=True)
        csv = df_budget.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 ดาวน์โหลดใบสั่งซื้อนี้ไปพิมพ์รายงาน (Download PO)", data=csv, file_name="ใบสั่งซื้อวัตถุดิบหน้าฟาร์ม.csv", mime="text/csv")
    else:
        st.info("💡 สัดส่วนอาหารในสูตรยังเป็น 0% กรุณาไปกดปรับสัดส่วนหรือสั่ง AI คำนวณที่หน้าแรกก่อนนะครับ")
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 🏁 ส่วนท้ายของแอปพลิเคชัน
# ==========================================
st.markdown("---")
st.markdown("<div style='text-align: center; color: #ffffff; font-size: 0.85em; text-shadow: 1px 1px 2px #000;'>© 2026 Smart Layer Feed | ระบบกล่องเลือกวัตถุดิบและฐานข้อมูลสารอาหาร 25 ชนิดเสร็จสมบูรณ์</div>", unsafe_allow_html=True)
