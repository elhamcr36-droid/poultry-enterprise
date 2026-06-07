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
    page_title="Mega Feed & Breed Studio - ระบบคำนวณอาหารและจัดการสายพันธุ์สัตว์ปีกอัจฉริยะ", 
    layout="wide",
    initial_sidebar_state="collapsed"  # ปิด Sidebar ตั้งแต่เริ่มต้น
)

# 🎨 มหาเวทย์ CSS ล็อกพื้นหลังและปรับปรุง UI สไตล์พรีเมียม อ่านง่าย 100%
st.markdown(
    """
    <style>
    /* ซ่อนปุ่มเปิด-ปิด Sidebar ของ Streamlit ออกไปเลย */
    [data-testid="collapsedControl"] {
        display: none;
    }
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.70), rgba(0, 0, 0, 0.70)), 
                          url("https://images.unsplash.com/photo-1548550023-2bdb3c5beed7?q=80&w=1920");
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
        background-color: rgba(0, 0, 0, 0.75) !important;
        padding: 25px;
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(8px);
        margin-bottom: 20px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem !important;
        color: #38bdf8 !important;
        font-weight: bold !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.9);
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("# 🐔 Mega Feed & Breed Studio")
st.markdown("### ระบบปัญญาประดิษฐ์คำนวณสูตรอาหาร โภชนาการขั้นสูง และบริหารคลังสายพันธุ์สัตว์ปีกแห่งประเทศไทย")

# ☁️ ย้ายส่วนเชื่อมต่อฐานข้อมูลจาก Sidebar มาไว้ใน Expander หน้าหลัก (พับเก็บได้ ไม่รกหน้าจอ)
with st.expander("☁️ การเชื่อมต่อคลาวด์และฐานข้อมูลหลัก (Supabase Configuration)"):
    c_db1, c_db2 = st.columns(2)
    with c_db1:
        SUPABASE_URL = st.text_input("ลิงก์โปรเจกต์ Supabase", "https://your-mega-project.supabase.co").strip()
    with c_db2:
        SUPABASE_KEY = st.text_input("รหัสผ่าน API (Anon Key)", "your-anon-key", type="password").strip()

page_tabs = st.tabs([
    "🏠 ห้องปฏิบัติการสูตรอาหาร & เลือกสายพันธุ์", 
    "📊 บันทึกสถิติฟาร์ม & ใบจัดซื้อ (PO)",
    "📦 ศูนย์จัดการคลังวัตถุดิบ (40 ชนิด)"
])

# ==========================================
# 📋 2. อภิมหาฐานข้อมูลวัตถุดิบ MASTER DICTIONARY (40 ชนิด สารอาหาร 15 ค่า)
# ==========================================
MASTER_INGREDIENT_DICTIONARY = {
    # --- กลุ่มที่ 1: แหล่งพลังงาน/คาร์โบไฮเดรตหลัก (Energy Sources) ---
    "ข้าวโพดบดเม็ด": {"price": 13.5, "protein": 8.5, "me": 3300.0, "calcium": 0.02, "phos": 0.25, "lysine": 0.24, "methionine": 0.18, "tryptophan": 0.07, "threonine": 0.29, "arginine": 0.38, "fiber": 2.2, "fat": 3.8, "ash": 1.3, "moisture": 12.0, "salt": 0.01, "choline": 620, "tox_risk": 3, "min_limit": 10.0, "max_limit": 70.0},
    "รำข้าวละเอียดดิบ": {"price": 11.0, "protein": 12.0, "me": 2400.0, "calcium": 0.05, "phos": 1.35, "lysine": 0.54, "methionine": 0.22, "tryptophan": 0.12, "threonine": 0.43, "arginine": 0.82, "fiber": 12.0, "fat": 13.0, "ash": 7.8, "moisture": 10.5, "salt": 0.02, "choline": 1200, "tox_risk": 3, "min_limit": 0.0, "max_limit": 25.0},
    "ปลายข้าวขาว": {"price": 14.5, "protein": 8.0, "me": 3360.0, "calcium": 0.04, "phos": 0.10, "lysine": 0.22, "methionine": 0.15, "tryptophan": 0.08, "threonine": 0.26, "arginine": 0.65, "fiber": 1.0, "fat": 1.5, "ash": 0.5, "moisture": 12.0, "salt": 0.01, "choline": 450, "tox_risk": 1, "min_limit": 0.0, "max_limit": 50.0},
    "ข้าวเปลือกบดหยาบ": {"price": 10.0, "protein": 7.8, "me": 2600.0, "calcium": 0.07, "phos": 0.28, "lysine": 0.23, "methionine": 0.14, "tryptophan": 0.08, "threonine": 0.25, "arginine": 0.58, "fiber": 9.5, "fat": 1.8, "ash": 4.8, "moisture": 11.0, "salt": 0.02, "choline": 500, "tox_risk": 2, "min_limit": 0.0, "max_limit": 30.0},
    "มันเส้นบดแห้งเกรด A": {"price": 9.0, "protein": 2.0, "me": 2980.0, "calcium": 0.16, "phos": 0.08, "lysine": 0.04, "methionine": 0.02, "tryptophan": 0.01, "threonine": 0.06, "arginine": 0.10, "fiber": 3.8, "fat": 0.4, "ash": 2.5, "moisture": 13.0, "salt": 0.03, "choline": 300, "tox_risk": 2, "min_limit": 0.0, "max_limit": 15.0},
    "ข้าวบาร์เลย์บด": {"price": 15.5, "protein": 11.2, "me": 2750.0, "calcium": 0.05, "phos": 0.34, "lysine": 0.40, "methionine": 0.19, "tryptophan": 0.13, "threonine": 0.37, "arginine": 0.60, "fiber": 5.2, "fat": 2.0, "ash": 2.8, "moisture": 11.5, "salt": 0.02, "choline": 1050, "tox_risk": 1, "min_limit": 0.0, "max_limit": 20.0},
    "ข้าวสาลีบดละเอียด": {"price": 16.0, "protein": 12.5, "me": 3100.0, "calcium": 0.05, "phos": 0.38, "lysine": 0.36, "methionine": 0.20, "tryptophan": 0.15, "threonine": 0.36, "arginine": 0.62, "fiber": 3.0, "fat": 1.7, "ash": 1.8, "moisture": 12.0, "salt": 0.01, "choline": 900, "tox_risk": 2, "min_limit": 0.0, "max_limit": 30.0},
    "ข้าวฟ่างบด": {"price": 12.5, "protein": 10.0, "me": 3150.0, "calcium": 0.03, "phos": 0.29, "lysine": 0.22, "methionine": 0.16, "tryptophan": 0.10, "threonine": 0.31, "arginine": 0.41, "fiber": 2.8, "fat": 2.9, "ash": 1.7, "moisture": 11.8, "salt": 0.01, "choline": 700, "tox_risk": 2, "min_limit": 0.0, "max_limit": 25.0},
    
    # --- กลุ่มที่ 2: แหล่งโปรตีนจากพืช (Plant Protein Sources) ---
    "กากถั่วเหลือง (โปรตีน 44%)": {"price": 18.5, "protein": 44.0, "me": 2420.0, "calcium": 0.25, "phos": 0.60, "lysine": 2.70, "methionine": 0.62, "tryptophan": 0.61, "threonine": 1.72, "arginine": 3.20, "fiber": 5.5, "fat": 1.5, "ash": 6.0, "moisture": 11.5, "salt": 0.02, "choline": 2200, "tox_risk": 1, "min_limit": 5.0, "max_limit": 45.0},
    "กากถั่วเหลืองสกัด (โปรตีน 48%)": {"price": 20.5, "protein": 48.0, "me": 2450.0, "calcium": 0.28, "phos": 0.65, "lysine": 3.02, "methionine": 0.67, "tryptophan": 0.66, "threonine": 1.87, "arginine": 3.45, "fiber": 3.9, "fat": 1.2, "ash": 6.3, "moisture": 11.0, "salt": 0.02, "choline": 2300, "tox_risk": 1, "min_limit": 0.0, "max_limit": 45.0},
    "กากเนื้อปาล์มเนื้อใน": {"price": 7.5, "protein": 16.0, "me": 1800.0, "calcium": 0.30, "phos": 0.60, "lysine": 0.55, "methionine": 0.30, "tryptophan": 0.15, "threonine": 0.56, "arginine": 1.10, "fiber": 15.0, "fat": 7.0, "ash": 4.5, "moisture": 10.0, "salt": 0.05, "choline": 850, "tox_risk": 2, "min_limit": 0.0, "max_limit": 10.0},
    "กากมะพร้าวอัด": {"price": 8.0, "protein": 19.0, "me": 2100.0, "calcium": 0.15, "phos": 0.52, "lysine": 0.56, "methionine": 0.31, "tryptophan": 0.18, "threonine": 0.64, "arginine": 1.80, "fiber": 11.0, "fat": 6.5, "ash": 6.0, "moisture": 9.5, "salt": 0.04, "choline": 900, "tox_risk": 3, "min_limit": 0.0, "max_limit": 10.0},
    "กากถั่วลิสงป่น": {"price": 16.0, "protein": 45.0, "me": 2600.0, "calcium": 0.22, "phos": 0.54, "lysine": 1.55, "methionine": 0.51, "tryptophan": 0.50, "threonine": 1.22, "arginine": 4.80, "fiber": 5.8, "fat": 1.6, "ash": 5.4, "moisture": 9.0, "salt": 0.02, "choline": 1800, "tox_risk": 4, "min_limit": 0.0, "max_limit": 8.0},
    "กากเมล็ดทานตะวันสกัด": {"price": 12.0, "protein": 33.0, "me": 1950.0, "calcium": 0.41, "phos": 0.92, "lysine": 1.15, "methionine": 0.72, "tryptophan": 0.42, "threonine": 1.18, "arginine": 2.60, "fiber": 18.0, "fat": 2.2, "ash": 6.2, "moisture": 10.0, "salt": 0.02, "choline": 2100, "tox_risk": 1, "min_limit": 0.0, "max_limit": 10.0},
    "กากเมล็ดฝ้าย": {"price": 11.0, "protein": 40.0, "me": 2150.0, "calcium": 0.20, "phos": 1.10, "lysine": 1.62, "methionine": 0.65, "tryptophan": 0.51, "threonine": 1.34, "arginine": 4.20, "fiber": 11.5, "fat": 1.8, "ash": 6.5, "moisture": 10.0, "salt": 0.03, "choline": 2500, "tox_risk": 3, "min_limit": 0.0, "max_limit": 5.0},
    "กากเมล็ดเรปเซด (Canola)": {"price": 15.0, "protein": 36.5, "me": 2100.0, "calcium": 0.62, "phos": 1.05, "lysine": 1.95, "methionine": 0.73, "tryptophan": 0.44, "threonine": 1.56, "arginine": 2.15, "fiber": 11.0, "fat": 2.5, "ash": 6.8, "moisture": 10.0, "salt": 0.02, "choline": 6000, "tox_risk": 2, "min_limit": 0.0, "max_limit": 12.0},
    "กลูเตนข้าวโพด (Corn Gluten Meal)": {"price": 26.0, "protein": 60.0, "me": 3720.0, "calcium": 0.05, "phos": 0.45, "lysine": 1.02, "methionine": 1.45, "tryptophan": 0.31, "threonine": 2.05, "arginine": 1.90, "fiber": 1.8, "fat": 2.5, "ash": 2.2, "moisture": 10.0, "salt": 0.02, "choline": 300, "tox_risk": 1, "min_limit": 0.0, "max_limit": 10.0},
    
    # --- กลุ่มที่ 3: แหล่งโปรตีนจากสัตว์และผลิตภัณฑ์จุลินทรีย์ (Animal & Microbial Proteins) ---
    "ปลาป่นพรีเมียม (โปรตีน 60%)": {"price": 32.0, "protein": 60.0, "me": 2850.0, "calcium": 5.00, "phos": 3.00, "lysine": 4.50, "methionine": 1.80, "tryptophan": 0.60, "threonine": 2.40, "arginine": 3.60, "fiber": 1.0, "fat": 8.0, "ash": 15.0, "moisture": 10.0, "salt": 1.50, "choline": 3200, "tox_risk": 1, "min_limit": 0.0, "max_limit": 12.0},
    "ปลาป่นเกรดรอง (โปรตีน 50%)": {"price": 25.0, "protein": 50.0, "me": 2550.0, "calcium": 6.50, "phos": 3.20, "lysine": 3.50, "methionine": 1.20, "tryptophan": 0.45, "threonine": 1.80, "arginine": 2.90, "fiber": 1.5, "fat": 7.0, "ash": 22.0, "moisture": 10.5, "salt": 2.80, "choline": 2800, "tox_risk": 2, "min_limit": 0.0, "max_limit": 8.0},
    "เนื้อและกระดูกป่น (Meat & Bone)": {"price": 22.0, "protein": 50.0, "me": 2400.0, "calcium": 10.00, "phos": 5.00, "lysine": 2.60, "methionine": 0.70, "tryptophan": 0.32, "threonine": 1.70, "arginine": 3.30, "fiber": 1.5, "fat": 9.5, "ash": 28.0, "moisture": 7.0, "salt": 1.20, "choline": 2000, "tox_risk": 2, "min_limit": 0.0, "max_limit": 7.0},
    "ผลพลอยได้จากสัตว์ปีกป่น (Poultry Meal)": {"price": 24.0, "protein": 58.0, "me": 3100.0, "calcium": 3.20, "phos": 1.80, "lysine": 3.20, "methionine": 1.10, "tryptophan": 0.48, "threonine": 2.10, "arginine": 3.90, "fiber": 1.2, "fat": 12.0, "ash": 13.0, "moisture": 8.0, "salt": 0.80, "choline": 2500, "tox_risk": 2, "min_limit": 0.0, "max_limit": 10.0},
    "เลือดป่นอบแห้ง": {"price": 28.0, "protein": 80.0, "me": 3050.0, "calcium": 0.30, "phos": 0.25, "lysine": 7.00, "methionine": 0.90, "tryptophan": 1.10, "threonine": 3.50, "arginine": 3.40, "fiber": 1.0, "fat": 1.0, "ash": 5.0, "moisture": 9.5, "salt": 1.10, "choline": 800, "tox_risk": 1, "min_limit": 0.0, "max_limit": 3.0},
    "ยีสต์แห้งสุรา (Brewers Yeast)": {"price": 45.0, "protein": 45.0, "me": 2600.0, "calcium": 0.15, "phos": 1.40, "lysine": 3.40, "methionine": 0.75, "tryptophan": 0.55, "threonine": 2.10, "arginine": 2.30, "fiber": 2.5, "fat": 1.5, "ash": 7.5, "moisture": 8.0, "salt": 0.10, "choline": 3800, "tox_risk": 1, "min_limit": 0.0, "max_limit": 5.0},
    
    # --- กลุ่มที่ 4: เศษวัสดุพลอยได้และพืชพื้นบ้าน (By-products & Local Forages) ---
    "กากเบียร์แห้ง (DDGS ข้าวโพด)": {"price": 11.5, "protein": 27.2, "me": 2250.0, "calcium": 0.18, "phos": 0.72, "lysine": 0.82, "methionine": 0.56, "tryptophan": 0.24, "threonine": 1.02, "arginine": 1.15, "fiber": 8.8, "fat": 8.5, "ash": 4.8, "moisture": 10.0, "salt": 0.05, "choline": 1800, "tox_risk": 2, "min_limit": 0.0, "max_limit": 15.0},
    "รำสกัดน้ำมัน": {"price": 8.5, "protein": 14.0, "me": 1850.0, "calcium": 0.06, "phos": 1.45, "lysine": 0.62, "methionine": 0.26, "tryptophan": 0.14, "threonine": 0.51, "arginine": 0.98, "fiber": 13.5, "fat": 1.5, "ash": 8.5, "moisture": 11.0, "salt": 0.02, "choline": 1350, "tox_risk": 3, "min_limit": 0.0, "max_limit": 15.0},
    "ใบกระถินป่นอบแห้งพรีเมียม": {"price": 9.5, "protein": 22.0, "me": 1200.0, "calcium": 1.80, "phos": 0.25, "lysine": 1.05, "methionine": 0.32, "tryptophan": 0.28, "threonine": 0.85, "arginine": 1.12, "fiber": 14.0, "fat": 4.5, "ash": 11.0, "moisture": 9.0, "salt": 0.05, "choline": 1200, "tox_risk": 3, "min_limit": 0.0, "max_limit": 5.0},
    "สาหร่ายสไปรูลิน่าผง": {"price": 180.0, "protein": 60.0, "me": 2900.0, "calcium": 0.70, "phos": 0.80, "lysine": 2.90, "methionine": 1.25, "tryptophan": 0.85, "threonine": 2.80, "arginine": 4.10, "fiber": 4.0, "fat": 6.0, "ash": 8.0, "moisture": 7.0, "salt": 1.00, "choline": 1500, "tox_risk": 0, "min_limit": 0.0, "max_limit": 2.0},
    "ถั่วเขียวป่นกระเทาะเปลือก": {"price": 19.0, "protein": 24.5, "me": 2980.0, "calcium": 0.11, "phos": 0.42, "lysine": 1.68, "methionine": 0.29, "tryptophan": 0.24, "threonine": 0.90, "arginine": 1.85, "fiber": 4.2, "fat": 1.3, "ash": 3.6, "moisture": 10.5, "salt": 0.01, "choline": 1100, "tox_risk": 1, "min_limit": 0.0, "max_limit": 15.0},
    "กากน้ำตาล (Molasses)": {"price": 6.5, "protein": 3.0, "me": 1950.0, "calcium": 0.80, "phos": 0.10, "lysine": 0.05, "methionine": 0.02, "tryptophan": 0.01, "threonine": 0.04, "arginine": 0.03, "fiber": 0.0, "fat": 0.1, "ash": 11.5, "moisture": 25.0, "salt": 0.40, "choline": 700, "tox_risk": 1, "min_limit": 0.0, "max_limit": 4.0},
    
    # --- กลุ่มที่ 5: ไขมันและน้ำมันพลังงานเข้มข้น (Concentrated Fats) ---
    "น้ำมันปาล์มดิบกระสอบ": {"price": 34.0, "protein": 0.0, "me": 8400.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "tryptophan": 0.00, "threonine": 0.00, "arginine": 0.00, "fiber": 0.0, "fat": 99.0, "ash": 0.0, "moisture": 0.5, "salt": 0.00, "choline": 0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 4.0},
    "น้ำมันถั่วเหลืองผ่านกรรมวิธี": {"price": 42.0, "protein": 0.0, "me": 8800.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "tryptophan": 0.00, "threonine": 0.00, "arginine": 0.00, "fiber": 0.0, "fat": 99.8, "ash": 0.2, "moisture": 0.2, "salt": 0.00, "choline": 0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 3.0},
    "ไขมันวัวเกรดอาหารสัตว์": {"price": 29.0, "protein": 0.0, "me": 8200.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "tryptophan": 0.00, "threonine": 0.00, "arginine": 0.00, "fiber": 0.0, "fat": 98.5, "ash": 0.2, "moisture": 0.8, "salt": 0.00, "choline": 0, "tox_risk": 1, "min_limit": 0.0, "max_limit": 3.0},
    
    # --- กลุ่มที่ 6: กรดอะมิโนบริสุทธิ์ แร่ธาตุ และวิตามิน (Amino Acids, Minerals & Additives) ---
    "แอล-ไลซีน (L-Lysine HCl)": {"price": 85.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 78.40, "methionine": 0.00, "tryptophan": 0.00, "threonine": 0.00, "arginine": 0.00, "fiber": 0.0, "fat": 0.0, "ash": 0.5, "moisture": 1.0, "salt": 0.00, "choline": 0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 1.2},
    "ดีแอล-เมทไธโอนีน (DL-Methionine)": {"price": 140.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 99.00, "tryptophan": 0.00, "threonine": 0.00, "arginine": 0.00, "fiber": 0.0, "fat": 0.0, "ash": 0.2, "moisture": 0.5, "salt": 0.00, "choline": 0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 1.0},
    "แอล-ทรีโอนีน (L-Threonine)": {"price": 95.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "tryptophan": 0.00, "threonine": 98.50, "arginine": 0.00, "fiber": 0.0, "fat": 0.0, "ash": 0.3, "moisture": 0.5, "salt": 0.00, "choline": 0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 0.5},
    "แอล-ทริปโตเฟน (L-Tryptophan)": {"price": 380.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "tryptophan": 98.00, "threonine": 0.00, "arginine": 0.00, "fiber": 0.0, "fat": 0.0, "ash": 0.4, "moisture": 0.8, "salt": 0.00, "choline": 0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 0.2},
    "เปลือกหอยทะเลบดละเอียด": {"price": 4.0, "protein": 0.0, "me": 0.0, "calcium": 38.00, "phos": 0.04, "lysine": 0.00, "methionine": 0.00, "tryptophan": 0.00, "threonine": 0.00, "arginine": 0.00, "fiber": 0.0, "fat": 0.0, "ash": 94.0, "moisture": 0.5, "salt": 0.10, "choline": 0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 12.0},
    "ไดแคลเซียมฟอสเฟต (DCP 18%)": {"price": 28.0, "protein": 0.0, "me": 0.0, "calcium": 21.00, "phos": 18.00, "lysine": 0.00, "methionine": 0.00, "tryptophan": 0.00, "threonine": 0.00, "arginine": 0.00, "fiber": 0.0, "fat": 0.0, "ash": 78.0, "moisture": 1.0, "salt": 0.00, "choline": 0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 4.0},
    "ผงชอล์กแคลเซียมเบา": {"price": 3.5, "protein": 0.0, "me": 0.0, "calcium": 39.20, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "tryptophan": 0.00, "threonine": 0.00, "arginine": 0.00, "fiber": 0.0, "fat": 0.0, "ash": 96.0, "moisture": 0.5, "salt": 0.05, "choline": 0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 10.0},
    "เกลือแกงบริสุทธิ์ (NaCl)": {"price": 6.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "tryptophan": 0.00, "threonine": 0.00, "arginine": 0.00, "fiber": 0.0, "fat": 0.0, "ash": 99.0, "moisture": 0.3, "salt": 98.50, "choline": 0, "tox_risk": 0, "min_limit": 0.1, "max_limit": 0.4},
    "พรีมิกซ์แร่ธาตุและวิตามินเข้มข้น": {"price": 120.0, "protein": 0.0, "me": 0.0, "calcium": 5.00, "phos": 1.20, "lysine": 0.00, "methionine": 0.00, "tryptophan": 0.00, "threonine": 0.00, "arginine": 0.00, "fiber": 0.0, "fat": 0.0, "ash": 82.0, "moisture": 2.0, "salt": 1.00, "choline": 25000, "tox_risk": 0, "min_limit": 0.2, "max_limit": 0.5}
}

# ==========================================
# 🐔 3. คลังกลุ่มและสายพันธุ์สัตว์ปีก (6 กลุ่ม 18 สายพันธุ์)
# ==========================================
BREED_PROFILES = {
    "1. กลุ่มไก่ไข่สีน้ำตาลพาณิชย์ (Commercial Brown Layers)": {
        "Isa Brown": {"name": "ไอซ่า บราวน์ (Isa Brown)", "egg_color": "🤎 น้ำตาลเข้ม", "bg_color": "#b45309", "text_color": "#ffffff", "default_feed": 115, "desc": "ยืนหนึ่งเรื่องความไข่ดกในไทย ทนร้อนจัด แผงเปลือกไข่หนา แตกหักยาก"},
        "Hy-Line Brown": {"name": "ไฮไลน์ บราวน์ (Hy-Line Brown)", "egg_color": "🤎 น้ำตาลนวล", "bg_color": "#d97706", "text_color": "#ffffff", "default_feed": 110, "desc": "ค่า FCR ต่ำมาก กินน้อยแต่ให้ไข่ไซส์ใหญ่สม่ำเสมอ อายุการปลดระวางยาวนาน"},
        "Lohmann Brown": {"name": "โลห์แมน บราวน์ (Lohmann Brown)", "egg_color": "🤎 น้ำตาลเข้มจัด", "bg_color": "#9a3412", "text_color": "#ffffff", "default_feed": 114, "desc": "สายพันธุ์เยอรมัน นิยมเลี้ยงกรงตับ ปรับตัวเข้ากับสภาพแวดล้อมเปิดปิดได้นิ่งมาก"}
    },
    "2. กลุ่มไก่ไข่สีขาวพาณิชย์ (Commercial White Layers)": {
        "Hy-Line W-36": {"name": "ไฮไลน์ ดับบลิว-36 (Hy-Line W-36)", "egg_color": "🤍 ขาวสะอาด", "bg_color": "#475569", "text_color": "#ffffff", "default_feed": 101, "desc": "ตัวเล็ก ประหยัดอาหารที่สุดในอุตสาหกรรม เหมาะสำหรับทำไข่เหลวส่งโรงงาน"},
        "Lohmann White": {"name": "โลห์แมน ไวท์ (Lohmann White)", "egg_color": "🤍 ขาวมุก", "bg_color": "#334155", "text_color": "#ffffff", "default_feed": 104, "desc": "ผลผลิตสูงยาวนาน เปอร์เซ็นต์การไข่ช่วงพีคพุ่งแตะ 96% ได้สบาย"},
        "Novogen White": {"name": "โนโวเจน ไวท์ (Novogen White)", "egg_color": "🤍 ขาวนวล", "bg_color": "#1e293b", "text_color": "#ffffff", "default_feed": 103, "desc": "สายพันธุ์ฝรั่งเศส นิ่ง ไม่ตื่นตกใจง่าย ไข่ทรงกลมสวยได้มาตรฐาน"}
    },
    "3. กลุ่มไก่สายพันธุ์แท้ & อนุรักษ์ (Purebred & Heritage)": {
        "Rhode Island Red": {"name": "โรดไอแลนด์เรด (Rhode Island Red)", "egg_color": "🤎 น้ำตาลอ่อน", "bg_color": "#991b1b", "text_color": "#ffffff", "default_feed": 130, "desc": "ไก่พันธุ์แท้สีแดงเข้ม แข็งแรงทนทาน หาอาหารเก่ง เหมาะเลี้ยงแบบปล่อยธรรมชาติ"},
        "Barred Plymouth Rock": {"name": "บาร์ พลีมัธร็อค (Barred Rock)", "egg_color": "🤎 น้ำตาลครีม", "bg_color": "#52525b", "text_color": "#ffffff", "default_feed": 128, "desc": "ไก่ลายบาร์สีขาวดำ เลี้ยงง่าย เชื่อง ให้ทั้งเนื้อและไข่ได้ดีในฟาร์มอินทรีย์"},
        "Leghorn": {"name": "เลกฮอร์นพันธุ์แท้ (Original Leghorn)", "egg_color": "🤍 ขาวเงา", "bg_color": "#15803d", "text_color": "#ffffff", "default_feed": 105, "desc": "ปราดเปรียว บินเก่ง ตื่นตัวสูงมาก เป็นต้นตระกูลของไก่ไข่ขาวพาณิชย์ในปัจจุบัน"}
    },
    "4. กลุ่มไก่ชนไทยเชิงพาณิชย์ (Thai Gamecocks / Fighting Cocks)": {
        "Pradu Hang Dam": {"name": "ประดู่หางดำ (Pradu Hang Dam)", "egg_color": "💛 ครีมอมเหลือง", "bg_color": "#111827", "text_color": "#ffffff", "default_feed": 120, "desc": "ราชาไก่ชนไทย กระดูกใหญ่ โครงสร้างแกร่ง ต้องการโปรตีนและกรดอะมิโนสร้างกล้ามเนื้อ"},
        "Khieo Phari": {"name": "เขียวพาลี / เขียวเลา", "egg_color": "💛 ครีม", "bg_color": "#064e3b", "text_color": "#ffffff", "default_feed": 118, "desc": "สายพันธุ์ดุดัน ว่องไว ปราดเปรียว เน้นสูตรอาหารที่ไม่สะสมไขมันส่วนเกิน"},
        "เหลืองหางขาว": {"name": "เหลืองหางขาว (ไก่พระนเรศวร)", "egg_color": "💛 ครีมขาว", "bg_color": "#854d0e", "text_color": "#ffffff", "default_feed": 122, "desc": "ไก่ชนมมงคลตามตำราโบราณ ตัวใหญ่ ยาว ทรงสง่างาม แข็งแกร่ง"}
    },
    "5. กลุ่มไก่พื้นเมืองไทย & ไก่สามสาย (Thai Native & Crossbred)": {
        "Kai Dang Srithep": {"name": "ไก่แดงศรีเทพ", "egg_color": "🤎 น้ำตาลครีม", "bg_color": "#7f1d1d", "text_color": "#ffffff", "default_feed": 110, "desc": "ไก่พื้นเมืองปรับปรุงพันธุ์ เนื้อแน่น ไข่ดกกว่าพื้นเมืองเดิม ทนโรคระบาดได้ดีมาก"},
        "Kai Sam Sai": {"name": "ไก่สามสายเลือด (3-Way Cross)", "egg_color": "🤎 น้ำตาลอ่อน", "bg_color": "#431407", "text_color": "#ffffff", "default_feed": 135, "desc": "ลูกผสมระหว่างพื้นเมือง+โรด+บาร์ โตเร็ว เนื้อนุ่มแน่น อัตราไข่ดี เลี้ยงง่าย"},
        "Kai Chee Ubon": {"name": "ไก่ชีอุบล", "egg_color": "💛 ครีมนวล", "bg_color": "#0f172a", "text_color": "#ffffff", "default_feed": 105, "desc": "ไก่พื้นเมืองขนสีขาวบริสุทธิ์ ขยายพันธุ์ง่าย ทนต่อสภาพแล้งและอากาศร้อนจัดได้ดี"}
    },
    "6. กลุ่มไก่เนื้อและไก่พ่อแม่พันธุ์ (Broiler & Parent Stock)": {
        "Cobb 500": {"name": "ค็อบบ์ 500 (Cobb 500)", "egg_color": "❌ ไม่เน้นไข่", "bg_color": "#1e3a8a", "text_color": "#ffffff", "default_feed": 160, "desc": "ราชาไก่เนื้อ โตไวที่สุดในโลก อกหนา ค่า FCR ต่ำ ต้องการพลังงานและไลซีนเข้มข้น"},
        "Ross 308": {"name": "รอสส์ 308 (Ross 308)", "egg_color": "❌ ไม่เน้นไข่", "bg_color": "#172554", "text_color": "#ffffff", "default_feed": 155, "desc": "เติบโตสม่ำเสมอ แข็งแรง ขาใหญ่รับน้ำหนักดีมาก นิยมในอุตสาหกรรมไก่เนื้อโรงงานใหญ่"},
        "Hubbard": {"name": "ฮับบาร์ด (Hubbard)", "egg_color": "❌ ไม่เน้นไข่", "bg_color": "#311005", "text_color": "#ffffff", "default_feed": 158, "desc": "โตไว โครงสร้างใหญ่ ทนทานต่อสภาวะความชื้นโรงเรือนในแถบเอเชียตะวันออกเฉียงใต้"}
    }
}

STAGE_NUTRITION_TARGETS = {
    "starter": {"name": "ลูกไก่แรกเกิด - 6 สัปดาห์ (Starter)", "protein": 20.0, "me": 2900.0, "calcium": 1.00, "phos": 0.45, "lysine": 1.10, "methionine": 0.45, "tryptophan": 0.20, "threonine": 0.74, "arginine": 1.15, "fiber": 4.0, "fat": 4.0, "ash": 7.0, "salt": 0.30, "choline": 1300.0},
    "grower": {"name": "ไก่รุ่นอายุ 6 - 16 สัปดาห์ (Grower)", "protein": 16.0, "me": 2750.0, "calcium": 0.90, "phos": 0.40, "lysine": 0.85, "methionine": 0.38, "tryptophan": 0.16, "threonine": 0.60, "arginine": 0.90, "fiber": 4.5, "fat": 3.2, "ash": 7.5, "salt": 0.30, "choline": 1000.0},
    "laying": {"name": "ไก่ระยะให้ผลผลิต/ช่วงไข่/สมบูรณ์พันธุ์ (Laying/Adult)", "protein": 17.5, "me": 2750.0, "calcium": 4.10, "phos": 0.42, "lysine": 0.88, "methionine": 0.42, "tryptophan": 0.19, "threonine": 0.65, "arginine": 1.00, "fiber": 4.0, "fat": 3.5, "ash": 8.0, "salt": 0.32, "choline": 1100.0}
}

LIFECYCLE_FEED_BUDGET = {"starter": 1.2, "grower": 2.8, "laying": 48.0}

# ==========================================
# ⚙️ 4. ตรวจสอบและตั้งค่าหน่วยความจำ (Session State Initiation)
# ==========================================
if "chicken_count" not in st.session_state:
    st.session_state.chicken_count = 100  

if "use_phytase" not in st.session_state:
    st.session_state.use_phytase = False

if "ingredient_data" not in st.session_state:
    st.session_state.ingredient_data = {
        "ข้าวโพดบดเม็ด": MASTER_INGREDIENT_DICTIONARY["ข้าวโพดบดเม็ด"],
        "รำข้าวละเอียดดิบ": MASTER_INGREDIENT_DICTIONARY["รำข้าวละเอียดดิบ"],
        "ปลายข้าวขาว": MASTER_INGREDIENT_DICTIONARY["ปลายข้าวขาว"],
        "ข้าวเปลือกบดหยาบ": MASTER_INGREDIENT_DICTIONARY["ข้าวเปลือกบดหยาบ"],
        "มันเส้นบดแห้งเกรด A": MASTER_INGREDIENT_DICTIONARY["มันเส้นบดแห้งเกรด A"],
        "ข้าวสาลีบดละเอียด": MASTER_INGREDIENT_DICTIONARY["ข้าวสาลีบดละเอียด"],
        "ข้าวฟ่างบด": MASTER_INGREDIENT_DICTIONARY["ข้าวฟ่างบด"],
        "กากถั่วเหลือง (โปรตีน 44%)": MASTER_INGREDIENT_DICTIONARY["กากถั่วเหลือง (โปรตีน 44%)"],
        "กากถั่วเหลืองสกัด (โปรตีน 48%)": MASTER_INGREDIENT_DICTIONARY["กากถั่วเหลืองสกัด (โปรตีน 48%)"],
        "กากเนื้อปาล์มเนื้อใน": MASTER_INGREDIENT_DICTIONARY["กากเนื้อปาล์มเนื้อใน"],
        "กากมะพร้าวอัด": MASTER_INGREDIENT_DICTIONARY["กากมะพร้าวอัด"],
        "กากเมล็ดทานตะวันสกัด": MASTER_INGREDIENT_DICTIONARY["กากเมล็ดทานตะวันสกัด"],
        "กลูเตนข้าวโพด (Corn Gluten Meal)": MASTER_INGREDIENT_DICTIONARY["กลูเตนข้าวโพด (Corn Gluten Meal)"],
        "ปลาป่นพรีเมียม (โปรตีน 60%)": MASTER_INGREDIENT_DICTIONARY["ปลาป่นพรีเมียม (โปรตีน 60%)"],
        "เนื้อและกระดูกป่น (Meat & Bone)": MASTER_INGREDIENT_DICTIONARY["เนื้อและกระดูกป่น (Meat & Bone)"],
        "กากเบียร์แห้ง (DDGS ข้าวโพด)": MASTER_INGREDIENT_DICTIONARY["กากเบียร์แห้ง (DDGS ข้าวโพด)"],
        "ใบกระถินป่นอบแห้งพรีเมียม": MASTER_INGREDIENT_DICTIONARY["ใบกระถินป่นอบแห้งพรีเมียม"],
        "น้ำมันปาล์มดิบกระสอบ": MASTER_INGREDIENT_DICTIONARY["น้ำมันปาล์มดิบกระสอบ"],
        "น้ำมันถั่วเหลืองผ่านกรรมวิธี": MASTER_INGREDIENT_DICTIONARY["น้ำมันถั่วเหลืองผ่านกรรมวิธี"],
        "แอล-ไลซีน (L-Lysine HCl)": MASTER_INGREDIENT_DICTIONARY["แอล-ไลซีน (L-Lysine HCl)"],
        "ดีแอล-เมทไธโอนีน (DL-Methionine)": MASTER_INGREDIENT_DICTIONARY["ดีแอล-เมทไธโอนีน (DL-Methionine)"],
        "เปลือกหอยทะเลบดละเอียด": MASTER_INGREDIENT_DICTIONARY["เปลือกหอยทะเลบดละเอียด"],
        "ไดแคลเซียมฟอสเฟต (DCP 18%)": MASTER_INGREDIENT_DICTIONARY["ไดแคลเซียมฟอสเฟต (DCP 18%)"],
        "เกลือแกงบริสุทธิ์ (NaCl)": MASTER_INGREDIENT_DICTIONARY["เกลือแกงบริสุทธิ์ (NaCl)"],
        "พรีมิกซ์แร่ธาตุและวิตามินเข้มข้น": MASTER_INGREDIENT_DICTIONARY["พรีมิกซ์แร่ธาตุและวิตามินเข้มข้น"]
    }

if "optimized_weights" not in st.session_state:
    st.session_state.optimized_weights = {name: 0.0 for name in st.session_state.ingredient_data.keys()}
    st.session_state.optimized_weights["ข้าวโพดบดเม็ด"] = 52.0
    st.session_state.optimized_weights["กากถั่วเหลือง (โปรตีน 44%)"] = 22.0
    st.session_state.optimized_weights["รำข้าวละเอียดดิบ"] = 12.0
    st.session_state.optimized_weights["ปลาป่นพรีเมียม (โปรตีน 60%)"] = 5.0
    st.session_state.optimized_weights["เปลือกหอยทะเลบดละเอียด"] = 4.4
    st.session_state.optimized_weights["ไดแคลเซียมฟอสเฟต (DCP 18%)"] = 0.4
    st.session_state.optimized_weights["เกลือแกงบริสุทธิ์ (NaCl)"] = 0.2
    st.session_state.optimized_weights["พรีมิกซ์แร่ธาตุและวิตามินเข้มข้น"] = 0.2
    st.session_state.optimized_weights["น้ำมันปาล์มดิบกระสอบ"] = 3.8

for name in st.session_state.ingredient_data.keys():
    if name not in st.session_state.optimized_weights:
        st.session_state.optimized_weights[name] = 0.0

# 🧮 ฟังก์ชันคำนวณสารอาหารและราคาปัจจุบันของสูตร
def calculate_current_formulation():
    nut_calc = {"protein": 0.0, "me": 0.0, "calcium": 0.0, "phos": 0.0, "lysine": 0.0, "methionine": 0.0, "tryptophan": 0.0, "threonine": 0.0, "arginine": 0.0, "fiber": 0.0, "fat": 0.0, "ash": 0.0, "salt": 0.0, "choline": 0.0}
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
# 📥 5. ส่วนควบคุมเนื้อหาในแต่ละแท็บ (UI Tabs Rendering)
# ==========================================

# --- [แท็บที่ 1]: ห้องปฏิบัติการสูตรอาหาร & การจัดการสายพันธุ์ ---
with page_tabs[0]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 🏠 การจัดการคลังสายพันธุ์สัตว์ปีกในโรงเรือน")
    
    c_group, c_breed = st.columns(2)
    with c_group:
        st.session_state.selected_group = st.selectbox("เลือกกลุ่มสัตว์ปีก/วัตถุประสงค์การเลี้ยง:", list(BREED_PROFILES.keys()))
    with c_breed:
        breed_options = BREED_PROFILES[st.session_state.selected_group]
        st.session_state.selected_breed_key = st.selectbox("สายพันธุ์หลักที่ต้องการจัดการ:", options=list(breed_options.keys()), format_func=lambda x: breed_options[x]["name"])
    
    st.session_state.current_key = st.selectbox("🗓️ โปรไฟล์โภชนาการตามช่วงอายุ:", options=list(STAGE_NUTRITION_TARGETS.keys()), format_func=lambda x: STAGE_NUTRITION_TARGETS[x]["name"])
    
    breed_info = breed_options[st.session_state.selected_breed_key]
    st.markdown(f"""
    <div style='background-color:{breed_info['bg_color']}; padding:20px; border-radius:10px; color:{breed_info['text_color']}; margin-top:15px; margin-bottom:15px;'>
        <h3>🧬 ข้อมูลสายพันธุ์ปัจจุบัน: {breed_info['name']}</h3>
        <b>🎨 คาแรกเตอร์ผลผลิต:</b> {breed_info['egg_color']} | <b>🥣 อัตราบริโภคเฉลี่ย:</b> {breed_info['default_feed']} กรัม / ตัว / วัน <br>
        <p style='margin: 10px 0; color:#ffffff !important;'><i>ℹ️ รายละเอียด: {breed_info['desc']}</i></p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### ⛅ การควบคุมสภาพแวดล้อมเพื่อคุมสภาวะเครียดจากความร้อน")
    weather_list = ["🌡️ อากาศปกติ (25-32°C)", "🔥 อากาศร้อนจัด (> 32°C)", "❄️ อากาศหนาว (< 25°C)"]
    st.session_state.weather_env = st.radio("สภาพอากาศรอบโรงเรือนวันนี้:", weather_list, horizontal=True)
    
    base_water = (breed_info['default_feed'] / 1000.0) * 2.2 if breed_info['egg_color'] != "❌ ไม่เน้นไข่" else 0.22
    calc_water = st.session_state.chicken_count * base_water
    if "ร้อนจัด" in st.session_state.weather_env:
        calc_water *= 1.25
        st.error("🔥 สภาพอากาศร้อนจัด! AI ปรับเพิ่มสัดส่วนความหนาแน่นสารอาหารขึ้น +8% ป้องกันการกินได้ลดลง และแนะนำเพิ่มการจ่ายน้ำดื่มสะอาดขึ้นอีก +25%")
    
    w_col1, w_col2 = st.columns(2)
    with w_col1:
        st.session_state.chicken_count = st.number_input("จำนวนนับสัตว์ปีกทั้งหมดในโรงเรือน (ตัว):", min_value=1, value=st.session_state.chicken_count, step=50)
    with w_col2:
        st.metric("💧 ประมาณการปริมาณน้ำดื่มรวมที่ต้องจ่ายเข้าถังพักวันนี้", f"{calc_water:,.1f} ลิตร")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 🧠 เครื่องคำนวณสมการเส้นตรง Least-Cost ด้วยปัญญาประดิษฐ์")
    
    target = STAGE_NUTRITION_TARGETS[st.session_state.current_key]
    density_factor = 1.08 if "ร้อนจัด" in st.session_state.weather_env else (0.95 if "หนาว" in st.session_state.weather_env else 1.0)
    adjusted_target = {k: v * density_factor for k, v in target.items() if k != "name" and k != "me"}
    adjusted_target["me"] = target["me"]

    st.session_state.use_phytase = st.checkbox("🧪 เปิดใช้งานสารเสริมเอนไซม์ไฟเตส (ลดเกณฑ์ฟอสฟอรัสลง 0.10% และแคลเซียมลง 0.05% อัตโนมัติ)", value=st.session_state.use_phytase)
    if st.session_state.use_phytase:
        adjusted_target["phos"] = max(0.22, adjusted_target["phos"] - 0.10)
        adjusted_target["calcium"] = max(0.50, adjusted_target["calcium"] - 0.05)

    if st.button("⚡ เดินเครื่องระบบ AI ผสมสูตรต้นทุนต่ำที่สุด (Run AI Solver Matrix)"):
        # ส่วนนี้คือส่วนที่เติมโค้ดของคุณให้สมบูรณ์
        prob = pulp.LpProblem("MegaPoultryLinearFeed", pulp.LpMinimize)
        ingredient_vars = {name: pulp.LpVariable(name, lowBound=data.get("min_limit", 0.0), upBound=data.get("max_limit", 100.0)) for name, data in st.session_state.ingredient_data.items()}

        # สมการเป้าหมาย: ทำให้ต้นทุนต่ำที่สุด
        prob += pulp.lpSum([st.session_state.ingredient_data[name]["price"] * var for name, var in ingredient_vars.items()]), "Total_Cost"

        # ข้อจำกัด: น้ำหนักรวมต้องเป็น 100%
        prob += pulp.lpSum([var for name, var in ingredient_vars.items()]) == 100.0, "Total_Percentage"

        # ข้อจำกัดทางโภชนาการ
        for nutrient, target_val in adjusted_target.items():
            if nutrient in ["protein", "calcium", "phos", "lysine", "methionine", "tryptophan", "threonine", "arginine", "salt"]:
                prob += pulp.lpSum([st.session_state.ingredient_data[name].get(nutrient, 0) * var for name, var in ingredient_vars.items()]) >= target_val * 100, f"Min_{nutrient}"
            elif nutrient == "fiber":
                prob += pulp.lpSum([st.session_state.ingredient_data[name].get(nutrient, 0) * var for name, var in ingredient_vars.items()]) <= target_val * 100, f"Max_{nutrient}"
            elif nutrient == "me":
                prob += pulp.lpSum([st.session_state.ingredient_data[name].get(nutrient, 0) * var for name, var in ingredient_vars.items()]) >= target_val * 100, f"Min_{nutrient}"

        # รัน AI หาค่า
        prob.solve()

        if pulp.LpStatus[prob.status] == 'Optimal':
            st.success("✅ AI คำนวณสูตรอาหารต้นทุนต่ำสุดได้สำเร็จ!")
            for name, var in ingredient_vars.items():
                st.session_state.optimized_weights[name] = var.varValue
            st.rerun()
        else:
            st.error("❌ ไม่สามารถหาสูตรที่ตรงตามเงื่อนไขทางโภชนาการได้ กรุณาปรับช่วงโภชนาการหรือขยายขีดจำกัดวัตถุดิบ (Min/Max limits)")
    
    st.markdown("</div>", unsafe_allow_html=True)

# --- [แท็บที่ 2]: บันทึกสถิติฟาร์ม & ใบจัดซื้อ (PO) (รอการพัฒนาต่อ) ---
with page_tabs[1]:
    st.info("🚧 ระบบบันทึกสถิติฟาร์มและใบจัดซื้อกำลังอยู่ระหว่างการพัฒนา")

# --- [แท็บที่ 3]: ศูนย์จัดการคลังวัตถุดิบ (รอการพัฒนาต่อ) ---
with page_tabs[2]:
    st.info("🚧 ระบบศูนย์จัดการคลังวัตถุดิบกำลังอยู่ระหว่างการพัฒนา")
