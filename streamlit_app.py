import streamlit as st
import pandas as pd
import plotly.express as px
import pulp
from supabase import create_client, Client
import io
import math

# ==========================================
# 🔱 1. ตั้งค่าคอนฟิกแอปพลิเคชันและหน้าจอ
# ==========================================
st.set_page_config(
    page_title="Mega Feed & Breed Studio", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(
    """
    <style>
    [data-testid="collapsedControl"] { display: none; }
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), 
                          url("https://images.unsplash.com/photo-1548550023-2bdb3c5beed7?q=80&w=1920");
        background-size: cover; background-position: center;
        background-repeat: no-repeat; background-attachment: fixed;
    }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, [data-testid="stHeader"] {
        color: #ffffff !important;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.9) !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(255, 255, 255, 0.12) !important;
        padding: 10px; border-radius: 12px; backdrop-filter: blur(10px);
    }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-weight: bold !important; }
    .content-card {
        background-color: rgba(0, 0, 0, 0.75) !important; padding: 25px;
        border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(8px); margin-bottom: 20px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem !important; color: #38bdf8 !important;
        font-weight: bold !important; text-shadow: 1px 1px 2px rgba(0,0,0,0.9);
    }
    [data-testid="stDataFrame"] { background-color: rgba(255,255,255,0.9) !important; border-radius: 10px; padding: 5px; }
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================================
# 🔐 2. ระบบล็อกอินและการเชื่อมต่อฐานข้อมูล
# ==========================================
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False

CORRECT_URL = "https://nxyncxqbtntlpzqessou.supabase.co"
CORRECT_KEY = "sb_publishable_m411zYbsazCAsmmUMIuMkA_ypb1BYPr"

if not st.session_state.is_authenticated:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center;'>🔐 ยินดีต้อนรับสู่ Mega Feed & Breed Studio</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    tab_login, _ = st.tabs(["🔑 เข้าสู่ระบบ (Login)", "📝 สมัครสมาชิก (ปิดใช้งานชั่วคราว)"])
    
    with tab_login:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            email_login = st.text_input("📧 อีเมล หรือ ชื่อผู้ใช้", key="login_email")
            pass_login = st.text_input("🔑 รหัสผ่าน", type="password", key="login_pass")
            
            if st.button("เข้าสู่ระบบ (Login)", type="primary", use_container_width=True):
                if email_login in ["222", "จีเมล222", "222@gmail.com"] and pass_login in ["222", "รหัส222"]:
                    st.session_state.is_authenticated = True
                    st.session_state.user_email = "👑 Admin (SQL Superuser)"
                    st.session_state.supabase_url = CORRECT_URL
                    st.session_state.supabase_key = CORRECT_KEY
                    st.success("✅ เชื่อมต่อระบบสำเร็จ!")
                    st.rerun()
                else:
                    st.error("❌ ข้อมูลไม่ถูกต้อง กรุณาเข้าใช้งานด้วยรหัสแอดมิน '222'")
                    
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==========================================
# 📥 3. ระบบดึงข้อมูลยืดหยุ่นสูง + บิ๊กดาต้าสำรอง 24 รายการ
# ==========================================
@st.cache_data(ttl=2) 
def fetch_master_data(url, key):
    ing_data, tgt_data, brd_data = [], [], []
    
    try:
        supabase: Client = create_client(url, key)
        try:
            ing_res = supabase.table("ingredients").select("*").execute()
            ing_data = ing_res.data if ing_res.data else []
        except Exception as e: pass
            
        try:
            tgt_res = supabase.table("nutrition_targets").select("*").execute()
            tgt_data = tgt_res.data if tgt_res.data else []
        except Exception as e: pass
            
        try:
            brd_res = supabase.table("chicken_breeds").select("*").execute()
            brd_data = brd_res.data if brd_res.data else []
        except Exception as e: pass
            
    except Exception as general_err: pass

    # 🛡️ FAIL-SAFE SUPER DATASET: ขยายวัตถุดิบจุใจ 24 รายการ (ตรงกับ SQL ตัวท็อป)
    if not ing_data:
        ing_data = [
            # [หมวดคาร์โบไฮเดรตและพลังงานหลัก]
            {"name": "ข้าวโพดบดเม็ด (Corn)", "price": 13.5, "protein": 8.5, "me": 3300.0, "calcium": 0.02, "phos": 0.25, "lysine": 0.24, "methionine": 0.18, "threonine": 0.29, "fat": 3.8, "moisture": 12.0, "fiber": 2.2, "sodium": 0.02, "chloride": 0.04, "linoleic": 2.2, "min_limit": 10.0, "max_limit": 65.0},
            {"name": "ปลายข้าว (Broken Rice)", "price": 15.0, "protein": 8.0, "me": 3400.0, "calcium": 0.04, "phos": 0.12, "lysine": 0.30, "methionine": 0.18, "threonine": 0.25, "fat": 1.5, "moisture": 12.0, "fiber": 0.6, "sodium": 0.01, "chloride": 0.03, "linoleic": 0.4, "min_limit": 0.0, "max_limit": 45.0},
            {"name": "ข้าวสาลีนำเข้า (Feed Wheat)", "price": 14.5, "protein": 11.5, "me": 3150.0, "calcium": 0.05, "phos": 0.30, "lysine": 0.32, "methionine": 0.17, "threonine": 0.33, "fat": 1.8, "moisture": 11.5, "fiber": 2.5, "sodium": 0.02, "chloride": 0.06, "linoleic": 0.8, "min_limit": 0.0, "max_limit": 30.0},
            {"name": "รำข้าวละเอียด (Rice Bran)", "price": 11.0, "protein": 12.0, "me": 2400.0, "calcium": 0.05, "phos": 1.35, "lysine": 0.54, "methionine": 0.22, "threonine": 0.43, "fat": 13.0, "moisture": 10.5, "fiber": 8.0, "sodium": 0.02, "chloride": 0.07, "linoleic": 4.5, "min_limit": 0.0, "max_limit": 20.0},
            {"name": "ข้าวทริทิเคลี (Triticale Feed)", "price": 13.8, "protein": 12.0, "me": 3120.0, "calcium": 0.05, "phos": 0.35, "lysine": 0.39, "methionine": 0.19, "threonine": 0.37, "fat": 1.8, "moisture": 11.0, "fiber": 3.0, "sodium": 0.01, "chloride": 0.05, "linoleic": 0.9, "min_limit": 0.0, "max_limit": 40.0},
            {"name": "ข้าวฟ่างเมล็ดต่ำ (Low-Tannin Sorghum)", "price": 12.5, "protein": 9.0, "me": 3250.0, "calcium": 0.03, "phos": 0.29, "lysine": 0.22, "methionine": 0.16, "threonine": 0.30, "fat": 2.8, "moisture": 12.0, "fiber": 2.5, "sodium": 0.02, "chloride": 0.04, "linoleic": 1.1, "min_limit": 0.0, "max_limit": 50.0},
            {"name": "ข้าวบาร์เลย์บด (Barley Feed)", "price": 14.0, "protein": 11.0, "me": 2750.0, "calcium": 0.06, "phos": 0.35, "lysine": 0.38, "methionine": 0.18, "threonine": 0.36, "fat": 1.9, "moisture": 11.0, "fiber": 5.0, "sodium": 0.02, "chloride": 0.12, "linoleic": 1.0, "min_limit": 0.0, "max_limit": 25.0},
            {"name": "กากมันสำปะหลังแห้ง (Cassava Meal)", "price": 9.5, "protein": 2.5, "me": 2900.0, "calcium": 0.15, "phos": 0.08, "lysine": 0.07, "methionine": 0.04, "threonine": 0.06, "fat": 0.6, "moisture": 12.0, "fiber": 3.5, "sodium": 0.02, "chloride": 0.04, "linoleic": 0.1, "min_limit": 0.0, "max_limit": 20.0},
            {"name": "ข้าวโอ๊ตบดอาหารสัตว์ (Feed Oats)", "price": 15.5, "protein": 11.0, "me": 2650.0, "calcium": 0.10, "phos": 0.35, "lysine": 0.40, "methionine": 0.18, "threonine": 0.36, "fat": 4.5, "moisture": 11.0, "fiber": 10.5, "sodium": 0.02, "chloride": 0.06, "linoleic": 1.8, "min_limit": 0.0, "max_limit": 15.0},
            
            # [หมวดโปรตีนพืชและโปรตีนสัตว์]
            {"name": "กากถั่วเหลือง 46% (SBM 46%)", "price": 19.5, "protein": 46.0, "me": 2440.0, "calcium": 0.25, "phos": 0.62, "lysine": 2.85, "methionine": 0.65, "threonine": 1.80, "fat": 1.5, "moisture": 11.0, "fiber": 3.5, "sodium": 0.02, "chloride": 0.05, "linoleic": 0.5, "min_limit": 10.0, "max_limit": 40.0},
            {"name": "ปลาป่นเกรด A 60% (Fish Meal 60%)", "price": 35.0, "protein": 60.0, "me": 2850.0, "calcium": 5.00, "phos": 3.00, "lysine": 4.50, "methionine": 1.80, "threonine": 2.40, "fat": 8.0, "moisture": 10.0, "fiber": 1.0, "sodium": 1.20, "chloride": 1.50, "linoleic": 0.2, "min_limit": 0.0, "max_limit": 8.0},
            {"name": "กากเบียร์แห้งข้าวโพด (DDGS)", "price": 15.0, "protein": 27.0, "me": 2800.0, "calcium": 0.06, "phos": 0.75, "lysine": 0.78, "methionine": 0.55, "threonine": 1.00, "fat": 9.0, "moisture": 10.0, "fiber": 7.5, "sodium": 0.15, "chloride": 0.10, "linoleic": 2.0, "min_limit": 0.0, "max_limit": 15.0},
            {"name": "กากคาโนลา (Canola Meal)", "price": 17.5, "protein": 36.0, "me": 2100.0, "calcium": 0.65, "phos": 1.00, "lysine": 2.00, "methionine": 0.70, "threonine": 1.55, "fat": 2.5, "moisture": 10.0, "fiber": 11.5, "sodium": 0.06, "chloride": 0.10, "linoleic": 0.6, "min_limit": 0.0, "max_limit": 15.0},
            {"name": "กากเมล็ดทานตะวัน (Sunflower Meal)", "price": 13.0, "protein": 32.0, "me": 1900.0, "calcium": 0.35, "phos": 0.95, "lysine": 1.10, "methionine": 0.72, "threonine": 1.15, "fat": 1.5, "moisture": 10.5, "fiber": 16.0, "sodium": 0.05, "chloride": 0.20, "linoleic": 0.5, "min_limit": 0.0, "max_limit": 10.0},
            {"name": "หนอนแมลงวันลายอบแห้ง (BSFL)", "price": 28.0, "protein": 45.0, "me": 3400.0, "calcium": 5.20, "phos": 0.90, "lysine": 2.90, "methionine": 0.85, "threonine": 1.90, "fat": 28.0, "moisture": 6.0, "fiber": 7.0, "sodium": 0.12, "chloride": 0.40, "linoleic": 4.5, "min_limit": 0.0, "max_limit": 7.5},
            {"name": "กากเมล็ดฝ้าย (Cottonseed Meal)", "price": 12.0, "protein": 41.0, "me": 2050.0, "calcium": 0.20, "phos": 1.00, "lysine": 1.70, "methionine": 0.55, "threonine": 1.30, "fat": 1.8, "moisture": 10.0, "fiber": 12.0, "sodium": 0.04, "chloride": 0.05, "linoleic": 0.8, "min_limit": 0.0, "max_limit": 8.0},
            {"name": "เลือดสัตว์แห้งป่น (Blood Meal)", "price": 42.0, "protein": 80.0, "me": 3000.0, "calcium": 0.30, "phos": 0.30, "lysine": 7.00, "methionine": 1.00, "threonine": 3.80, "fat": 1.0, "moisture": 9.0, "fiber": 1.0, "sodium": 0.30, "chloride": 0.50, "linoleic": 0.1, "min_limit": 0.0, "max_limit": 3.0},

            # [หมวดกรดอะมิโนและสารเสริมบริสุทธิ์]
            {"name": "แอล-ไลซีน (L-Lysine HCl 78%)", "price": 85.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 78.40, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 1.0, "fiber": 0.0, "sodium": 0.00, "chloride": 19.50, "linoleic": 0.0, "min_limit": 0.0, "max_limit": 1.5},
            {"name": "ดีแอล-เมทไธโอนีน (DL-Methionine 99%)", "price": 140.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 99.00, "threonine": 0.00, "fat": 0.0, "moisture": 0.5, "fiber": 0.0, "sodium": 0.00, "chloride": 0.00, "linoleic": 0.0, "min_limit": 0.0, "max_limit": 0.8},
            {"name": "แอล-ทรีโอนีน (L-Threonine 98%)", "price": 110.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "threonine": 98.50, "fat": 0.0, "moisture": 1.0, "fiber": 0.0, "sodium": 0.00, "chloride": 0.00, "linoleic": 0.0, "min_limit": 0.0, "max_limit": 0.5},
            
            # [หมวดไขมัน แร่ธาตุ และวิตามิน]
            {"name": "น้ำมันปาล์มดิบ (Palm Oil)", "price": 34.0, "protein": 0.0, "me": 8400.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 99.0, "moisture": 0.5, "fiber": 0.0, "sodium": 0.00, "chloride": 0.00, "linoleic": 10.0, "min_limit": 0.0, "max_limit": 5.0},
            {"name": "หินฝุ่นเม็ดหยาบ 2-4 มม. (Limestone)", "price": 2.5, "protein": 0.0, "me": 0.0, "calcium": 38.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 0.5, "fiber": 0.0, "sodium": 0.00, "chloride": 0.00, "linoleic": 0.0, "min_limit": 0.0, "max_limit": 12.0},
            {"name": "เปลือกหอยบดละเอียด (Oyster Shell)", "price": 6.5, "protein": 0.0, "me": 0.0, "calcium": 38.50, "phos": 0.02, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 1.0, "fiber": 0.0, "sodium": 0.05, "chloride": 0.02, "linoleic": 0.0, "min_limit": 0.0, "max_limit": 10.0},
            {"name": "ไดแคลเซียมฟอสเฟต (DCP 18%)", "price": 28.0, "protein": 0.0, "me": 0.0, "calcium": 21.00, "phos": 18.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 1.0, "fiber": 0.0, "sodium": 0.00, "chloride": 0.00, "linoleic": 0.0, "min_limit": 0.0, "max_limit": 3.0},
            {"name": "เกลือแกงบริสุทธิ์ (Salt - NaCl)", "price": 6.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 0.3, "fiber": 0.0, "sodium": 39.30, "chloride": 60.00, "linoleic": 0.0, "min_limit": 0.15, "max_limit": 0.45},
            {"name": "พรีมิกซ์วิตามินแร่ธาตุ (Premix)", "price": 160.0, "protein": 0.0, "me": 0.0, "calcium": 5.00, "phos": 1.20, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 2.0, "fiber": 0.0, "sodium": 0.00, "chloride": 0.00, "linoleic": 0.0, "min_limit": 0.25, "max_limit": 0.35}
        ]
        
    if not tgt_data:
        tgt_data = [
            {"stage_key": "layer_phase_1", "stage_name": "ไก่ไข่ระยะพีค Phase 1 (19-45 สัปดาห์)", "protein": 17.5, "me": 2750.0, "calcium": 4.10, "phos": 0.42, "lysine": 0.88, "methionine": 0.42, "fiber_max": 4.5, "sodium_min": 0.16, "chloride_min": 0.16, "linoleic_min": 1.50},
            {"stage_key": "layer_phase_2", "stage_name": "ไก่ไข่ระยะกลาง Phase 2 (46-65 สัปดาห์)", "protein": 16.5, "me": 2725.0, "calcium": 4.30, "phos": 0.38, "lysine": 0.82, "methionine": 0.39, "fiber_max": 5.0, "sodium_min": 0.16, "chloride_min": 0.16, "linoleic_min": 1.30},
            {"stage_key": "broiler_starter", "stage_name": "ไก่เนื้อระยะแรก Starter (0-10 วัน)", "protein": 23.0, "me": 3000.0, "calcium": 1.00, "phos": 0.50, "lysine": 1.44, "methionine": 0.51, "fiber_max": 3.0, "sodium_min": 0.16, "chloride_min": 0.16, "linoleic_min": 1.00},
            {"stage_key": "broiler_grower", "stage_name": "ไก่เนื้อระยะเติบโต Grower (11-24 วัน)", "protein": 21.5, "me": 3100.0, "calcium": 0.90, "phos": 0.44, "lysine": 1.25, "methionine": 0.48, "fiber_max": 3.5, "sodium_min": 0.16, "chloride_min": 0.16, "linoleic_min": 1.00},
            {"stage_key": "broiler_finisher", "stage_name": "ไก่เนื้อระยะสุดท้าย Finisher (25 วันขึ้นไป)", "protein": 19.5, "me": 3200.0, "calcium": 0.85, "phos": 0.40, "lysine": 1.09, "methionine": 0.41, "fiber_max": 3.5, "sodium_min": 0.16, "chloride_min": 0.16, "linoleic_min": 1.00},
            {"stage_key": "native_chicken", "stage_name": "ไก่พื้นเมือง/ไก่บ้าน ระยะเจริญเติบโต", "protein": 16.0, "me": 2800.0, "calcium": 0.90, "phos": 0.35, "lysine": 0.85, "methionine": 0.35, "fiber_max": 6.0, "sodium_min": 0.15, "chloride_min": 0.15, "linoleic_min": 0.80}
        ]
        
    if not brd_data:
        brd_data = [
            {"group_name": "ไก่ไข่ (Layers)", "breed_key": "Isa Brown", "breed_name": "ไอซ่า บราวน์", "egg_color": "🤎 น้ำตาล", "bg_color": "#b45309", "text_color": "#ffffff", "default_feed": 114, "description": "สายพันธุ์ยอดนิยม ทนร้อนเป็นเลิศ เปลือกไข่แข็งแรงสม่ำเสมอ"},
            {"group_name": "ไก่ไข่ (Layers)", "breed_key": "Lohmann Brown", "breed_name": "โลห์แมน บราวน์", "egg_color": "🤎 น้ำตาลเข้ม", "bg_color": "#854d0e", "text_color": "#ffffff", "default_feed": 116, "description": "สายพันธุ์เยอรมัน โดดเด่นเรื่องขนาดฟองใหญ่และอัตราการไข่สม่ำเสมอในระยะยาว"},
            {"group_name": "ไก่เนื้อ (Broilers)", "breed_key": "Ross 308", "breed_name": "รอสส์ 308", "egg_color": "❌ ไม่เน้นไข่", "bg_color": "#1d4ed8", "text_color": "#ffffff", "default_feed": 161, "description": "อันดับหนึ่งของโลก โตไว แลกเนื้อได้ดีเยี่ยม (FCR ต่ำ) กล้ามเนื้ออกแน่น"},
            {"group_name": "ไก่เนื้อ (Broilers)", "breed_key": "Cobb 500", "breed_name": "ค็อบบ์ 500", "egg_color": "❌ ไม่เน้นไข่", "bg_color": "#0369a1", "text_color": "#ffffff", "default_feed": 159, "description": "สายพันธุ์ยอดนิยม กินอาหารคุ้มค่า ต้นทุนต่ำสุด ทนทานต่อสภาพอากาศร้อนชื้น"},
            {"group_name": "ไก่ลูกผสม/พื้นเมือง", "breed_key": "Kuroda", "breed_name": "ไก่ดำคูโรดะ / สามสายเลือด", "egg_color": "🥚 ครีม/ขาว", "bg_color": "#0f172a", "text_color": "#ffffff", "default_feed": 125, "description": "เนื้อนุ่มแน่น หนังกรุบ ได้ราคาดีในตลาดทางเลือก เลี้ยงง่ายต้านทานโรคสูง"},
            {"group_name": "ไก่พื้นเมือง", "breed_key": "Thai Native", "breed_name": "ไก่บ้าน/ไก่ชนไทย", "egg_color": "🥚 ครีมนวล", "bg_color": "#16a34a", "text_color": "#ffffff", "default_feed": 85, "description": "เติบโตตามธรรมชาติ หาอาหารเก่ง เนื้อแน่นไขมันต่ำมาก เป็นที่ต้องการของตลาดชุมชน"}
        ]

    # ทำความสะอาดข้อมูลเพื่อความปลอดภัย
    def safe_clean_ingredients(raw_list):
        cleaned = {}
        for item in raw_list:
            name = item.get("name", "Unknown Ingredient")
            cleaned[name] = {
                "name": name,
                "price": float(item.get("price") if item.get("price") is not None else 0),
                "protein": float(item.get("protein") if item.get("protein") is not None else 0),
                "me": float(item.get("me") if item.get("me") is not None else 0),
                "calcium": float(item.get("calcium") if item.get("calcium") is not None else 0),
                "phos": float(item.get("phos") if item.get("phos") is not None else 0),
                "lysine": float(item.get("lysine") if item.get("lysine") is not None else 0),
                "methionine": float(item.get("methionine") if item.get("methionine") is not None else 0),
                "threonine": float(item.get("threonine") if item.get("threonine") is not None else 0),
                "fat": float(item.get("fat") if item.get("fat") is not None else 0),
                "moisture": float(item.get("moisture") if item.get("moisture") is not None else 0),
                "fiber": float(item.get("fiber") if item.get("fiber") is not None else 0),
                "sodium": float(item.get("sodium") if item.get("sodium") is not None else 0),
                "chloride": float(item.get("chloride") if item.get("chloride") is not None else 0),
                "linoleic": float(item.get("linoleic") if item.get("linoleic") is not None else 0),
                "min_limit": float(item.get("min_limit") if item.get("min_limit") is not None else 0),
                "max_limit": float(item.get("max_limit") if item.get("max_limit") is not None else 100),
            }
        return cleaned

    def safe_clean_targets(raw_list):
        cleaned = {}
        for item in raw_list:
            key = item.get("stage_key", "unknown")
            cleaned[key] = {
                "stage_key": key,
                "stage_name": item.get("stage_name", "Unknown Stage"),
                "protein": float(item.get("protein") if item.get("protein") is not None else 0),
                "me": float(item.get("me") if item.get("me") is not None else 0),
                "calcium": float(item.get("calcium") if item.get("calcium") is not None else 0),
                "phos": float(item.get("phos") if item.get("phos") is not None else 0),
                "lysine": float(item.get("lysine") if item.get("lysine") is not None else 0),
                "methionine": float(item.get("methionine") if item.get("methionine") is not None else 0),
                "fiber_max": float(item.get("fiber_max") if item.get("fiber_max") is not None else 5),
                "sodium_min": float(item.get("sodium_min") if item.get("sodium_min") is not None else 0),
                "chloride_min": float(item.get("chloride_min") if item.get("chloride_min") is not None else 0),
                "linoleic_min": float(item.get("linoleic_min") if item.get("linoleic_min") is not None else 0),
            }
        return cleaned

    return safe_clean_ingredients(ing_data), safe_clean_targets(tgt_data), brd_data

ingredients_data, targets_data, breeds_data = fetch_master_data(st.session_state.supabase_url, st.session_state.supabase_key)

if "optimized_weights" not in st.session_state:
    st.session_state.optimized_weights = {name: 0.0 for name in ingredients_data.keys()}

# ==========================================
# 🎉 4. ส่วนหัวแอปพลิเคชัน (Header)
# ==========================================
col_h1, col_h2 = st.columns([8, 2])
with col_h1:
    st.markdown("# 🐔 Mega Feed & Breed Studio")
    st.markdown(f"<p style='color:#38bdf8; font-weight:bold; font-size:1.2rem;'>🔥 เปิดใช้งานระบบฐานข้อมูลขนาดใหญ่สำเร็จ (วัตถุดิบ {len(ingredients_data)} รายการ | สายพันธุ์ครอบคลุม {len(breeds_data)} ชนิด)</p>", unsafe_allow_html=True)
with col_h2:
    st.markdown(f"<p style='text-align:right; margin-bottom:5px;'>👤 <b>{st.session_state.user_email}</b></p>", unsafe_allow_html=True)
    if st.button("ออกจากระบบ (Logout)", use_container_width=True):
        st.session_state.is_authenticated = False
        st.rerun()

# ==========================================
# 📋 5. หน้าจอหลักและการแบ่งแท็บใช้งาน
# ==========================================
page_tabs = st.tabs(["🏠 ระบบผสมสูตร AI", "📊 สถิติ & ใบสั่งซื้อ PO", "📦 คลังวัตถุดิบ & จัดการข้อมูล SQL", "📈 เครื่องจำลองแผนการเติบโต"])

# --- [แท็บ 1]: AI Solver ---
with page_tabs[0]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    
    c_group, c_breed = st.columns(2)
    with c_group:
        st.markdown("#### 🧬 ข้อมูลสายพันธุ์และกลุ่ม")
        breed_options = {f"{b['group_name']} - {b['breed_name']}": b for b in breeds_data}
        selected_breed_label = st.selectbox("เลือกสายพันธุ์ไก่:", list(breed_options.keys()))
        selected_breed = breed_options[selected_breed_label]
        
        bg_c = selected_breed.get('bg_color', '#1e293b')
        tx_c = selected_breed.get('text_color', '#ffffff')
        st.markdown(
            f"""
            <div style='background-color: {bg_c}; padding: 15px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.2);'>
                <h4 style='margin:0; color: {tx_c} !important;'>🎯 สายพันธุ์: {selected_breed.get('breed_name')}</h4>
                <p style='margin:5px 0 0 0; color: {tx_c} !important; font-size:0.95rem;'>
                    <b>ลักษณะสีเปลือกไข่:</b> {selected_breed.get('egg_color')}<br>
                    <b>ความต้องการกินอาหารเฉลี่ย:</b> {selected_breed.get('default_feed')} กรัม/วัน/ตัว<br>
                    <b>คำอธิบาย:</b> {selected_breed.get('description')}
                </p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
    with c_breed:
        st.markdown("#### 📈 ระยะการเลี้ยงและเป้าหมาย")
        target_options = {t["stage_name"]: t["stage_key"] for t in targets_data.values()}
        selected_stage_name = st.selectbox("เลือกโปรไฟล์โภชนาการตามช่วงอายุ:", list(target_options.keys()))
        selected_stage_key = target_options[selected_stage_name]
        req = targets_data[selected_stage_key]

    st.markdown("---")
    st.markdown("### 🧠 เครื่องคำนวณสมการเส้นตรง Least-Cost ด้วย AI")
    st.session_state.use_phytase = st.checkbox("🧪 เปิดใช้งานสารเสริมเอนไซม์ไฟเตส (ลดฟอสฟอรัส/แคลเซียมเป้าหมายลงอัตโนมัติ 0.10% และ 0.05%)")
    
    if st.button("⚡ เดินเครื่องระบบ AI ผสมสูตร (Run LP Solver)", type="primary"):
        with st.spinner("AI กำลังคำนวณราคาต่ำสุดภายใต้ข้อจำกัดโภชนาการ..."):
            prob = pulp.LpProblem("MegaPoultryLinearFeed", pulp.LpMinimize)
            
            ing_vars = {}
            for name, data in ingredients_data.items():
                ing_vars[name] = pulp.LpVariable(name, lowBound=float(data["min_limit"])/100.0, upBound=float(data["max_limit"])/100.0)
            
            prob += pulp.lpSum([ing_vars[name] * float(data["price"]) for name, data in ingredients_data.items()]), "Total_Cost"
            prob += pulp.lpSum([ing_vars[name] for name in ingredients_data.keys()]) == 1.0, "Total_Weight"
            
            adj_p = float(req["phos"]) - 0.10 if st.session_state.use_phytase else float(req["phos"])
            adj_ca = float(req["calcium"]) - 0.05 if st.session_state.use_phytase else float(req["calcium"])
            
            prob += pulp.lpSum([ing_vars[name] * float(data["protein"]) for name, data in ingredients_data.items()]) >= float(req["protein"]), "Min_Protein"
            prob += pulp.lpSum([ing_vars[name] * float(data["me"]) for name, data in ingredients_data.items()]) >= float(req["me"]), "Min_ME"
            prob += pulp.lpSum([ing_vars[name] * float(data["calcium"]) for name, data in ingredients_data.items()]) >= adj_ca, "Min_Calcium"
            prob += pulp.lpSum([ing_vars[name] * float(data["phos"]) for name, data in ingredients_data.items()]) >= adj_p, "Min_Phosphorus"
            prob += pulp.lpSum([ing_vars[name] * float(data["lysine"]) for name, data in ingredients_data.items()]) >= float(req["lysine"]), "Min_Lysine"
            prob += pulp.lpSum([ing_vars[name] * float(data["methionine"]) for name, data in ingredients_data.items()]) >= float(req["methionine"]), "Min_Methionine"
            
            prob += pulp.lpSum([ing_vars[name] * float(data["fiber"]) for name, data in ingredients_data.items()]) <= float(req["fiber_max"]), "Max_Fiber"
            prob += pulp.lpSum([ing_vars[name] * float(data["sodium"]) for name, data in ingredients_data.items()]) >= float(req["sodium_min"]), "Min_Sodium"
            prob += pulp.lpSum([ing_vars[name] * float(data["chloride"]) for name, data in ingredients_data.items()]) >= float(req["chloride_min"]), "Min_Chloride"
            prob += pulp.lpSum([ing_vars[name] * float(data["linoleic"]) for name, data in ingredients_data.items()]) >= float(req["linoleic_min"]), "Min_Linoleic"

            prob.solve(pulp.PULP_CBC_CMD(msg=False))
            
            if pulp.LpStatus[prob.status] == "Optimal":
                st.success(f"✅ AI คำนวณสูตรอาหารสำเร็จ! (ต้นทุนต่ำสุด: {pulp.value(prob.objective):.2f} บาท/กก.)")
                st.session_state.optimized_weights = {name: 0.0 for name in ingredients_data.keys()}
                for name in ingredients_data.keys():
                    st.session_state.optimized_weights[name] = ing_vars[name].varValue * 100.0
            else:
                st.session_state.optimized_weights = {name: 0.0 for name in ingredients_data.keys()}
                st.error("❌ เงื่อนไขโภชนาการแน่นเกินไปสำหรับวัตถุดิบที่มีอยู่ กรุณาปรับลดข้อกำหนดสารอาหาร หรือเพิ่ม Max Limit ของกลุ่มโปรตีน")

    if any(v > 0 for v in st.session_state.optimized_weights.values()):
        res_col1, res_col2 = st.columns([1.2, 1])
        with res_col1:
            st.markdown("#### 📊 สัดส่วนวัตถุดิบในสูตรอาหารปัจจุบัน")
            plot_data = [{"วัตถุดิบ": k, "สัดส่วน (%)": v} for k, v in st.session_state.optimized_weights.items() if v > 0.01]
            df_plot = pd.DataFrame(plot_data).sort_values(by="สัดส่วน (%)", ascending=False)
            fig = px.pie(df_plot, names="วัตถุดิบ", values="สัดส่วน (%)", hole=0.4)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_plot, use_container_width=True, hide_index=True)

        with res_col2:
            st.markdown("#### 🔬 ผลวิเคราะห์โภชนาการที่ได้จริง vs เกณฑ์เป้าหมาย")
            actual_nutrients = {"protein": 0, "me": 0, "calcium": 0, "phos": 0, "lysine": 0, "methionine": 0, "fiber": 0, "sodium": 0, "chloride": 0, "linoleic": 0, "threonine": 0, "fat": 0}
            cost_per_kg = 0
            for name, weight in st.session_state.optimized_weights.items():
                if weight > 0 and name in ingredients_data:
                    frac = weight / 100.0
                    cost_per_kg += frac * float(ingredients_data[name]["price"])
                    for key in actual_nutrients.keys():
                        if key in ingredients_data[name]:
                            actual_nutrients[key] += frac * float(ingredients_data[name][key])
            
            compare_data = [
                {"สารอาหาร": "โปรตีน (%)", "ได้จริง": round(actual_nutrients["protein"], 2), "เป้าหมาย": f">= {req['protein']}"},
                {"สารอาหาร": "พลังงาน (ME kcal/kg)", "ได้จริง": round(actual_nutrients["me"], 0), "เป้าหมาย": f">= {req['me']}"},
                {"สารอาหาร": "แคลเซียม (%)", "ได้จริง": round(actual_nutrients["calcium"], 2), "เป้าหมาย": f">= {req['calcium']}"},
                {"สารอาหาร": "ฟอสฟอรัสที่เป็นประโยชน์ (%)", "ได้จริง": round(actual_nutrients["phos"], 2), "เป้าหมาย": f">= {req['phos']}"},
                {"สารอาหาร": "ไลซีน (%)", "ได้จริง": round(actual_nutrients["lysine"], 2), "เป้าหมาย": f">= {req['lysine']}"},
                {"สารอาหาร": "เมทไธโอนีน (%)", "ได้จริง": round(actual_nutrients["methionine"], 2), "เป้าหมาย": f">= {req['methionine']}"},
                {"สารอาหาร": "ทรีโอนีน (%)", "ได้จริง": round(actual_nutrients["threonine"], 2), "เป้าหมาย": "ตามธรรมชาติ"},
                {"สารอาหาร": "ไขมันดิบ (%)", "ได้จริง": round(actual_nutrients["fat"], 2), "เป้าหมาย": "ตามธรรมชาติ"},
                {"สารอาหาร": "กากใยสูงสุด (%)", "ได้จริง": round(actual_nutrients["fiber"], 2), "เป้าหมาย": f"<= {req['fiber_max']}"},
                {"สารอาหาร": "โซเดียม (%)", "ได้จริง": round(actual_nutrients["sodium"], 2), "เป้าหมาย": f">= {req['sodium_min']}"},
            ]
            st.markdown(f"<h3 style='color:#38bdf8 !important;'>💰 ต้นทุนรวมสูตรผสม: {cost_per_kg:.2f} บาท/กก.</h3>", unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(compare_data), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- [แท็บ 2]: ใบจัดซื้อ (PO) ---
with page_tabs[1]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 📊 ระบบออกใบสั่งซื้อวัตถุดิบและคำนวณต้นทุนถ่วงน้ำหนักจริง")
    
    batch_size = st.number_input("ปริมาณรวมยอดผลิตผสมอาหารในล็อตนี้ (กิโลกรัม):", min_value=10, max_value=500000, value=1000, step=500)
    
    po_data = []
    total_po_cost = 0
    for k, v in st.session_state.optimized_weights.items():
        if v > 0.01 and k in ingredients_data:
            amount_kg = (v / 100.0) * batch_size
            est_price = amount_kg * float(ingredients_data[k]['price'])
            total_po_cost += est_price
            po_data.append({
                "วัตถุดิบที่ต้องจัดซื้อ": k, 
                "ปริมาณ (กก.)": round(amount_kg, 2), 
                "ราคาประเมินรวม (บาท)": round(est_price, 2)
            })
            
    if po_data:
        df_po = pd.DataFrame(po_data)
        st.dataframe(df_po, use_container_width=True, hide_index=True)
        weighted_average_cost = total_po_cost / batch_size
        
        c_m1, c_m2 = st.columns(2)
        with c_m1:
            st.metric("💵 มูลค่ารวมใบสั่งซื้อจัดหาล็อตนี้", f"{total_po_cost:,.2f} บาท")
        with c_m2:
            st.metric("🏷️ ต้นทุนเฉลี่ยถ่วงน้ำหนัก", f"{weighted_average_cost:.2f} บาท/กก.")
            
        csv_buffer = io.StringIO()
        df_po.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 ดาวน์โหลดไฟล์ใบสั่งซื้อ (Export PO to CSV)",
            data=csv_buffer.getvalue(),
            file_name=f"PO_Batch_{batch_size}kg.csv",
            mime="text/csv"
        )
    else:
        st.warning("กรุณากดคำนวณสูตรอาหาร AI ในหน้าแรกก่อนเพื่อสร้างใบสั่งซื้อ")
    st.markdown("</div>", unsafe_allow_html=True)

# --- [แท็บ 3]: จัดการคลังวัตถุดิบ SQL ---
with page_tabs[2]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 📦 ศูนย์ควบคุมคลังข้อมูลโภชนาการวัตถุดิบ & ปรับปรุงแบบสดผ่าน SQL")
    
    if ingredients_data:
        selected_ing_name = st.selectbox("เลือกวัตถุดิบที่ต้องการปรับปรุงข้อมูล:", list(ingredients_data.keys()))
        target_ing = ingredients_data[selected_ing_name]
        
        c_ed1, c_ed2, c_ed3 = st.columns(3)
        with c_ed1:
            new_price = st.number_input("ราคาปรับปรุงใหม่ (บาท/กก.):", value=float(target_ing["price"]), step=0.1)
        with c_ed2:
            new_min = st.number_input("ปรับเกณฑ์ขั้นต่ำสุด Min Limit (%):", value=float(target_ing["min_limit"]), step=1.0)
        with c_ed3:
            new_max = st.number_input("ปรับเกณฑ์สูงสุด Max Limit (%):", value=float(target_ing["max_limit"]), step=1.0)
            
        if st.button("💾 บันทึกและเขียนข้อมูลลงคลาวด์ฐานข้อมูล SQL", type="primary"):
            with st.spinner("กำลังทำการยิง SQL Update ไปยังเซิร์ฟเวอร์..."):
                try:
                    supabase_client = create_client(st.session_state.supabase_url, st.session_state.supabase_key)
                    supabase_client.table("ingredients").update({
                        "price": new_price,
                        "min_limit": new_min,
                        "max_limit": new_max
                    }).eq("name", selected_ing_name).execute()
                    
                    st.success(f"🎉 บันทึกการอัปเดตข้อมูลของ '{selected_ing_name}' เรียบร้อยแล้ว ระบบกำลังรีเฟรช...")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as update_err:
                    st.error(f"❌ บันทึกลงฐานข้อมูลล้มเหลว (คุณกำลังใช้งานระบบข้อมูลสำรองภายใน): {str(update_err)}")
        
        st.markdown("---")
        st.markdown("### 📋 ตารางคลังสารอาหารและวัตถุดิบปัจจุบันทั้งหมด")
        df_ingredients = pd.DataFrame.from_dict(ingredients_data, orient='index')
        if not df_ingredients.empty:
            df_ingredients.rename(columns={
                "price": "ราคา", "protein": "โปรตีน(%)", "me": "พลังงาน(ME)",
                "calcium": "แคลเซียม(%)", "phos": "ฟอสฟอรัส(%)", "lysine": "ไลซีน(%)",
                "methionine": "เมท(%)", "threonine": "ทรีโอนีน(%)", "fat": "ไขมัน(%)", "moisture": "ความชื้น(%)",
                "fiber": "ใย(%)", "sodium": "Na(%)", "chloride": "Cl(%)", "linoleic": "ไลโนเลอิก(%)",
                "min_limit": "Min(%)", "max_limit": "Max(%)"
            }, inplace=True)
            st.dataframe(df_ingredients, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- [แท็บ 4]: เครื่องจำลองแผนการเติบโต ---
with page_tabs[3]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 📈 เครื่องจำลองแผนการเติบโตรายสายพันธุ์ (Growth Simulator)")
    
    c_sim1, c_sim2 = st.columns(2)
    with c_sim1:
        sim_birds = st.number_input("ปริมาณตัวเลขจำนวนไก่ในฝูง (ตัว):", min_value=1, value=2000, step=500)
        sim_days = st.slider("ช่วงอายุวันเลี้ยงที่ต้องการพยากรณ์ผลจำลอง (วัน):", min_value=7, max_value=105, value=42, step=7)
    with c_sim2:
        fcr_target = st.number_input("เป้าหมายสัมประสิทธิ์ FCR ล็อตนี้:", min_value=1.0, max_value=4.5, value=1.60, step=0.05)
        chick_cost = st.number_input("ราคาพันธุ์ต้นทุนลูกไก่แรกเกิด (บาท/ตัว):", min_value=0.0, value=14.0, step=1.0)

    days_list = list(range(1, sim_days + 1))
    weight_gain_daily = []
    feed_intake_daily = []
    
    current_feed_price = 14.50
    if ingredients_data and any(v > 0 for v in st.session_state.optimized_weights.values()):
        current_feed_price = 0
        for name, weight in st.session_state.optimized_weights.items():
            if name in ingredients_data:
                current_feed_price += (weight / 100.0) * float(ingredients_data[name]["price"])

    for d in days_list:
        est_weight = 42 + (3800 / (1 + 48 * math.exp(-0.115 * d))) 
        weight_gain_daily.append(est_weight)
        cumulative_feed = (est_weight / 1000.0) * fcr_target
        feed_intake_daily.append(cumulative_feed * 1000.0)
        
    df_sim = pd.DataFrame({
        "ระยะเวลา (วัน)": days_list,
        "น้ำหนักประเมินรายตัว (กรัม)": weight_gain_daily,
        "ปริมาณอาหารกินสะสม (กรัม)": feed_intake_daily
    })
    
    fig_sim = px.line(df_sim, x="ระยะเวลา (วัน)", y=["น้ำหนักประเมินรายตัว (กรัม)", "ปริมาณอาหารกินสะสม (กรัม)"],
                      title="📊 แนวโน้มการเจริญเติบโตสอดคล้องกับพฤติกรรมการกินอาหาร")
    fig_sim.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
    st.plotly_chart(fig_sim, use_container_width=True)
    
    final_weight_kg = weight_gain_daily[-1] / 1000.0
    total_feed_used_ton = (feed_intake_daily[-1] / 1000.0 * sim_birds) / 1000.0
    total_feed_cost = total_feed_used_ton * 1000 * current_feed_price
    total_investment = total_feed_cost + (sim_birds * chick_cost)
    
    st.markdown("### 📋 สรุปงบประมาณเมื่อสิ้นสุดโครงการ")
    c_r1, c_r2, c_r3 = st.columns(3)
    with c_r1:
        st.metric("⚖️ น้ำหนักตัวจับขายเฉลี่ยรายตัว", f"{final_weight_kg:.2f} กก.")
    with c_r2:
        st.metric("🌾 ความต้องการยอดใช้อาหารรวม", f"{total_feed_used_ton:.3f} ตัน")
    with c_r3:
        st.metric("💰 ประมาณการทุนรวม (พันธุ์ไก่ + อาหาร)", f"{total_investment:,.2f} บาท")
    st.markdown("</div>", unsafe_allow_html=True)
