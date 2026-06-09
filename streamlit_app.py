import streamlit as st
import pandas as pd
import plotly.express as px
import pulp
from supabase import create_client, Client
import io

# ==========================================
# 🔱 1. INITIAL APP CONFIGURATION & THEME
# ==========================================
st.set_page_config(
    page_title="ระบบคำนวณโภชนาการและจัดการสายพันธุ์ไก่ไข่ (Layer Nutrition Studio)", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ปรับแต่งธีมสไตล์ Cyber Dark พร้อมสไตล์เพิ่มขนาด Radio Buttons ให้ใหญ่พิเศษ สะดวกต่อการเลือกกด
st.markdown(
    """
    <style>
    [data-testid="collapsedControl"] { display: none; }
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0.8)), 
                          url("https://images.unsplash.com/photo-1548550023-2bdb3c5beed7?q=80&w=1920");
        background-size: cover; background-position: center;
        background-repeat: no-repeat; background-attachment: fixed;
    }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, [data-testid="stHeader"] {
        color: #ffffff !important;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.9) !important;
    }
    
    /* 🎯 จุดปรับแต่งขนาดปุ่มตัวเลือก (Radio Buttons) ให้ใหญ่เป็นพิเศษ */
    div[data-testid="stRadio"] > label {
        font-size: 1.35rem !important;
        font-weight: bold !important;
        color: #f59e0b !important;
        margin-bottom: 10px !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label {
        background-color: rgba(255, 255, 255, 0.08) !important;
        padding: 14px 24px !important;
        border-radius: 12px !important;
        border: 2px solid rgba(255, 255, 255, 0.2) !important;
        margin-right: 12px !important;
        margin-bottom: 10px !important;
        transition: all 0.25s ease-in-out;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label:hover {
        background-color: rgba(245, 158, 11, 0.15) !important;
        border-color: #f59e0b !important;
        cursor: pointer;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label p {
        font-size: 1.25rem !important; /* ปรับตัวหนังสือของตัวเลือกให้ใหญ่เด่นชัด */
        font-weight: 600 !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(255, 255, 255, 0.1) !important;
        padding: 8px; border-radius: 10px; backdrop-filter: blur(10px);
    }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-weight: bold !important; font-size:1.1rem !important; }
    .content-card {
        background-color: rgba(0, 0, 0, 0.85) !important; padding: 25px;
        border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(8px); margin-bottom: 20px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem !important; color: #ffb703 !important;
        font-weight: bold !important;
    }
    [data-testid="stDataFrame"] { background-color: rgba(255,255,255,0.95) !important; border-radius: 8px; padding: 5px; }
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================================
# 🔐 2. SECURITY & LOGIN GATEWAY
# ==========================================
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False

CORRECT_URL = "https://nxyncxqbtntlpzqessou.supabase.co"
CORRECT_KEY = "sb_publishable_m411zYbsazCAsmmUMIuMkA_ypb1BYPr"

if not st.session_state.is_authenticated:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center;'>🔐 ระบบวิเคราะห์โภชนาการและจัดการสายพันธุ์ไก่ไข่ระดับสากล (Layer Nutrition Studio)</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    col_l1, col_l2, col_l3 = st.columns([1, 1.8, 1])
    with col_l2:
        email_login = st.text_input("📧 อีเมลผู้ใช้งานหรือรหัสทางลัด (Email / Shortcut Key):", key="login_email")
        pass_login = st.text_input("🔑 รหัสผ่านเข้าใช้งาน (Password):", type="password", key="login_pass")
        
        if st.button("ยืนยันสิทธิ์เข้าสู่ระบบ (Login)", type="primary", use_container_width=True):
            if email_login in ["222", "222@gmail.com"] and pass_login in ["222"]:
                st.session_state.is_authenticated = True
                st.session_state.user_email = "👑 ผู้ดูแลระบบระดับสูง (Superuser Administrator)"
                st.session_state.supabase_url = CORRECT_URL
                st.session_state.supabase_key = CORRECT_KEY
                st.rerun()
            else:
                st.error("❌ ข้อมูลสิทธิ์เข้าใช้งานไม่ถูกต้อง! (กรุณาใช้รหัสทางลัดแอดมิน '222')")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==========================================
# 📥 3. DATA ACQUISITION & BIG-DATA FAILSAFE
# ==========================================
@st.cache_data(ttl=2)
def fetch_complete_layer_data(url, key):
    ing_data, tgt_data, groups_data, breeds_data = [], [], [], []
    try:
        supabase: Client = create_client(url, key)
        try: ing_data = supabase.table("ingredients").select("*").execute().data or []
        except: pass
        try: tgt_data = supabase.table("nutrition_targets").select("*").execute().data or []
        except: pass
        try: groups_data = supabase.table("chicken_groups").select("*").execute().data or []
        except: pass
        try: breeds_data = supabase.table("chicken_breeds").select("*").execute().data or []
        except: pass
    except: pass

    # --- โครงสร้างข้อมูลสำรองเมื่อระบบ Cloud ขัดข้อง (Failsafe Backup Dataset) ---
    if not groups_data:
        groups_data = [
            {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "bg_color": "#b45309", "text_color": "#ffffff", "market_trend": "ได้รับความนิยมสูงเป็นอันดับ 1 ในทวีปเอเชีย ประเทศไทย และยุโรป ผู้บริโภคเชื่อมั่นในคุณภาพเนื้อไข่แดงและขนาดฟอง"},
            {"group_name": "กลุ่มไก่ไข่เปลือกสีขาว (Commercial White Layers)", "bg_color": "#0284c7", "text_color": "#ffffff", "market_trend": "ครองตลาดใหญ่ในอเมริกาเหนือ โดดเด่นด้านการประหยัดต้นทุนค่าอาหาร เหมาะกับโรงงานอุตสาหกรรมแปรรูปไข่เหลว"},
            {"group_name": "กลุ่มไก่ไข่ทางเลือกและตลาดพรีเมียม (Specialty Layers Market)", "bg_color": "#475569", "text_color": "#ffffff", "market_trend": "เซกเมนต์การเติบโตยุคใหม่ ตอบโจทย์วิถีฟาร์มปล่อยอิสระ (Free-Range) และไข่ไก่ออร์แกนิกมูลค่าสูง"}
        ]
    if not breeds_data:
        breeds_data = [
            {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "breed_key": "Isa Brown", "breed_name": "สายพันธุ์ ไอซ่า บราวน์ (Isa Brown)", "egg_color": "สีน้ำตาลเข้ม (Dark Brown Egg)", "default_feed": 114, "description": "สายพันธุ์ฝรั่งเศส ยอดนิยมอันดับ 1 ในไทย แข็งแรง ทนสภาพอากาศร้อนชื้นได้ดีเลิศ ไข่ดกยาวนานสม่ำเสมอ"},
            {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "breed_key": "Lohmann Brown", "breed_name": "สายพันธุ์ โลห์แมน บราวน์ (Lohmann Brown)", "egg_color": "สีน้ำตาลเงางาม (Glossy Brown Egg)", "default_feed": 116, "description": "สายพันธุ์เยอรมัน โดดเด่นเรื่องไข่ฟองใหญ่ ให้เปอร์เซ็นต์ไข่ไซส์ใหญ่พิเศษ (XL) สูงมาก เปลือกหนาเหนียว"},
            {"group_name": "กลุ่มไก่ไข่เปลือกสีน้ำตาล (Commercial Brown Layers)", "breed_key": "Hy-Line Brown", "breed_name": "สายพันธุ์ ไฮ-ไลน์ บราวน์ (Hy-Line Brown)", "egg_color": "สีน้ำตาลประกายทอง (Golden Brown Egg)", "default_feed": 112, "description": "สายพันธุ์อเมริกา นิ่ง ไม่ตื่นตกใจง่าย อัตราการเปลี่ยนอาหารเป็นน้ำหนักไข่ดีเยี่ยม เหมาะกับฟาร์มระบบปิด"},
            {"group_name": "กลุ่มไก่ไข่เปลือกสีขาว (Commercial White Layers)", "breed_key": "Hy-Line W-36", "breed_name": "สายพันธุ์ ไฮ-ไลน์ ขาว ดับบลิว-36 (Hy-Line W-36)", "egg_color": "สีขาวสะอาดตา (Pure White Egg)", "default_feed": 101, "description": "แชมป์โลกความประหยัด กินอาหารน้อยที่สุดในอุตสาหกรรม ให้ไข่ฟองสีขาวข้นแน่นสูง ปริมาณไข่ขาวหนาตัวดีมาก"},
            {"group_name": "กลุ่มไก่ไข่เปลือกสีขาว (Commercial White Layers)", "breed_key": "Dekalb White", "breed_name": "สายพันธุ์ เดคัลบ์ ไวท์ (Dekalb White)", "egg_color": "สีขาวพรีเมียม (Premium White Egg)", "default_feed": 103, "description": "ลดปัญหาไข่บุบสลายระหว่างคัดแยก ขนส่งทางไกลได้ดีเยี่ยม ยืนกรงทำผลผลิตพีคได้ยาวนาน"},
            {"group_name": "กลุ่มไก่ไข่ทางเลือกและตลาดพรีเมียม (Specialty Layers Market)", "breed_key": "Novogen Tinted", "breed_name": "สายพันธุ์ โนโวเจน ทินต์ (Novogen Tinted)", "egg_color": "สีครีมพาสเทล (Creamy Tinted Egg)", "default_feed": 110, "description": "ผลิตไข่เปลือกสีนวลครีมแปลกใหม่ ตลาดพรีเมียมให้ราคาดี พฤติกรรมเรียบร้อย เหมาะกับการเลี้ยงปล่อยลาน"}
        ]
    if not ing_data:
        ing_data = [
            {"name": "ข้าวโพดบดเม็ด (Ground Corn)", "price": 13.5, "protein": 8.5, "me": 3300.0, "calcium": 0.02, "phos": 0.25, "lysine": 0.24, "methionine": 0.18, "threonine": 0.29, "fat": 3.8, "moisture": 12.0, "fiber": 2.2, "sodium": 0.02, "chloride": 0.04, "linoleic": 2.2, "min_limit": 10.0, "max_limit": 65.0},
            {"name": "กากถั่วเหลือง 46% (Soybean Meal 46%)", "price": 19.5, "protein": 46.0, "me": 2440.0, "calcium": 0.25, "phos": 0.62, "lysine": 2.85, "methionine": 0.65, "threonine": 1.80, "fat": 1.5, "moisture": 11.0, "fiber": 3.5, "sodium": 0.02, "chloride": 0.05, "linoleic": 0.5, "min_limit": 10.0, "max_limit": 40.0},
            {"name": "ปลาป่นเกรด A 60% (Fish Meal 60%)", "price": 35.0, "protein": 60.0, "me": 2850.0, "calcium": 5.00, "phos": 3.00, "lysine": 4.50, "methionine": 1.80, "threonine": 2.40, "fat": 8.0, "moisture": 10.0, "fiber": 1.0, "sodium": 1.20, "chloride": 1.50, "linoleic": 0.2, "min_limit": 0.0, "max_limit": 8.0},
            {"name": "หินฝุ่นเม็ดหยาบ (Coarse Limestone)", "price": 2.5, "protein": 0.0, "me": 0.0, "calcium": 38.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 0.5, "fiber": 0.0, "sodium": 0.00, "chloride": 0.00, "linoleic": 0.0, "min_limit": 0.0, "max_limit": 12.0},
            {"name": "ไดแคลเซียมฟอสเฟต (DCP 18%)", "price": 28.0, "protein": 0.0, "me": 0.0, "calcium": 21.00, "phos": 18.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 1.0, "fiber": 0.0, "sodium": 0.00, "chloride": 0.00, "linoleic": 0.0, "min_limit": 0.0, "max_limit": 3.0},
            {"name": "เกลือแกงบริสุทธิ์ (Refined Salt)", "price": 6.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 0.3, "fiber": 0.0, "sodium": 39.30, "chloride": 60.00, "linoleic": 0.0, "min_limit": 0.15, "max_limit": 0.45},
            {"name": "พรีมิกซ์วิตามินแร่ธาตุ (Vitamin-Mineral Premix)", "price": 160.0, "protein": 0.0, "me": 0.0, "calcium": 5.00, "phos": 1.20, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 2.0, "fiber": 0.0, "sodium": 0.00, "chloride": 0.00, "linoleic": 0.25, "min_limit": 0.25, "max_limit": 0.35}
        ]
    if not tgt_data:
        tgt_data = [
            {"stage_key": "layer_phase_1", "stage_name": "ระยะผลิตไข่พีค ช่วงที่ 1 อายุ 19-45 สัปดาห์ (Production Phase 1)", "protein": 17.5, "me": 2750.0, "calcium": 4.10, "phos": 0.42, "lysine": 0.88, "methionine": 0.42, "fiber_max": 4.5, "sodium_min": 0.16, "chloride_min": 0.16, "linoleic_min": 1.50},
            {"stage_key": "layer_phase_2", "stage_name": "ระยะกลาง ช่วงที่ 2 อายุ 46-65 สัปดาห์ (Production Phase 2)", "protein": 16.5, "me": 2725.0, "calcium": 4.30, "phos": 0.38, "lysine": 0.82, "methionine": 0.39, "fiber_max": 5.0, "sodium_min": 0.16, "chloride_min": 0.16, "linoleic_min": 1.30}
        ]

    ing_dict = {i["name"]: i for i in ing_data}
    tgt_dict = {t["stage_key"]: t for t in tgt_data}
    return ing_dict, tgt_dict, groups_data, breeds_data

ingredients_data, targets_data, groups_list, breeds_list = fetch_complete_layer_data(st.session_state.supabase_url, st.session_state.supabase_key)

if "optimized_weights" not in st.session_state:
    st.session_state.optimized_weights = {name: 0.0 for name in ingredients_data.keys()}

# ==========================================
# 🎉 4. HEADER CONTROL PANEL
# ==========================================
col_h1, col_h2 = st.columns([7.5, 2.5])
with col_h1:
    st.markdown("# 🐔 สตูดิโอคำนวณสูตรอาหารและจัดการสายพันธุ์ไก่ไข่ (Layer Nutrition Studio)", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#38bdf8; font-weight:bold; font-size:1.15rem;'>🎯 ระบบจัดการโภชนาการแม่ไก่ไข่เชิงพาณิชย์และจัดซื้อวัตถุดิบแม่นยำสูง (Precision Feed & Procurement Matrix)</p>", unsafe_allow_html=True)
with col_h2:
    st.markdown(f"<p style='text-align:right; margin:0;'>👤 ผู้ใช้งาน (User): <b>{st.session_state.user_email}</b></p>", unsafe_allow_html=True)
    if st.button("🔴 ออกจากระบบ (Logout)", use_container_width=True):
        st.session_state.is_authenticated = False
        st.rerun()

page_tabs = st.tabs(["🏠 ระบบผสมสูตรอาหารปัญญาประดิษฐ์ (AI Feed Optimization)", "📊 แผนสถิติและใบสั่งซื้อวัตถุดิบ (Procurement & PO Sheet)", "📦 คลังข้อมูลระบบและตารางโครงสร้าง (SQL Editor Control)"])

# =========================================================================================
# 🏠 [แท็บที่ 1]: ระบบผสมสูตรอาหารปัญญาประดิษฐ์ (ปรับปรุงระบบคัดกรองอัตโนมัติ Cascade Filter)
# =========================================================================================
with page_tabs[0]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    
    st.markdown("### 🧬 1. เลือกคัดกรองตามกลุ่มประเภทไก่ไข่หลัก (Breeding Groups Mode)")
    group_names = [g["group_name"] for g in groups_list]
    
    # 📌 ปุ่มกดวิทยุขนาดใหญ่พิเศษสำหรับเลือกกลุ่มหลักหลัก (Large Radio Buttons)
    selected_group = st.radio(
        "🔘 คลิกเลือกกลุ่มประเภทไก่ไข่หลักของคุณ (Select Primary Breeding Group):", 
        group_names,
        index=0
    )
    
    # ดึงค่าข้อมูล Meta ของกลุ่มที่เลือก
    g_meta = next(g for g in groups_list if g["group_name"] == selected_group)
    
    # 🔄 ตัวกรองอัตโนมัติ: ดึงเฉพาะรายชื่อสายพันธุ์ที่อยู่ภายใต้กลุ่มหลักที่เลือกข้างต้นเท่านั้น
    filtered_breeds = [b for b in breeds_list if b["group_name"] == selected_group]
    breed_options_map = {b["breed_name"]: b for b in filtered_breeds}
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🐓 2. คัดกรองเจาะลึกรายสายพันธุ์การค้าอัตโนมัติ (Commercial Breeds Mode)")
    
    # ช่อง Selectbox จะเปลี่ยนรายชื่อสายพันธุ์ตามกลุ่มที่กดด้านบนทันทีโดยอัตโนมัติ
    if breed_options_map:
        selected_breed_name = st.selectbox(
            f"👇 รายชื่อสายพันธุ์การค้าที่สอดคล้องกับ {selected_group} (Select Linked Commercial Breed):", 
            list(breed_options_map.keys())
        )
        b_meta = breed_options_map[selected_breed_name]
        
        # 📊 แสดงผลข้อมูลกล่องสายพันธุ์แบบไดนามิก
        st.markdown(f"""
        <div style='background-color: {g_meta["bg_color"]}; padding: 22px; border-radius: 14px; border: 2px solid rgba(255,255,255,0.2);'>
            <h4 style='margin:0; color:{g_meta["text_color"]} !important;'>🐓 โปรไฟล์สายพันธุ์ปัจจุบัน: {b_meta["breed_name"]}</h4>
            <p style='margin:10px 0 0 0; color:{g_meta["text_color"]} !important; font-size:1.15rem; line-height: 1.6;'>
                <b>🧬 กลุ่มหลักสังกัด (Breeding Group):</b> {b_meta["group_name"]}<br>
                <b>🥚 มาตรฐานสีเปลือกไข่ (Egg Shell Color):</b> {b_meta["egg_color"]}<br>
                <b>🍽️ ปริมาณการกินอาหารมาตรฐาน (Default Daily Feed Intake):</b> <span style='color:#f59e0b; font-weight:bold;'>{b_meta["default_feed"]}</span> กรัม/วัน/ตัว (g/day/bird)<br>
                <b>💡 คำแนะนำเชิงพฤติกรรมศาสตร์ (Technical Description):</b> {b_meta["description"]}
            </p>
        </div>
        """, unsafe_allow_html=True)
        active_breed_profile = b_meta
    else:
        st.warning("⚠️ ไม่พบข้อมูลสายพันธุ์ที่เชื่อมโยงกับกลุ่มนี้ในฐานข้อมูล")
        active_breed_profile = {"breed_name": "Unknown", "default_feed": 110}

    st.markdown("---")
    st.markdown("### 🧬 3. กำหนดระยะอายุและเป้าหมายสารอาหารที่เหมาะสม (Nutrition Target & Stage)")
    stage_options = {s["stage_name"]: s["stage_key"] for s in targets_data.values()}
    selected_stage_label = st.selectbox("เลือกระยะอายุการให้ผลผลิตของฝูง (Select Production Stage):", list(stage_options.keys()))
    active_req = targets_data[stage_options[selected_stage_label]]
    
    st.session_state.use_phytase = st.checkbox("🧪 เปิดใช้งานเอนไซม์ไฟเตสเสริม (Enable Phytase Enzyme Optimization) - AI จะลดเกณฑ์ Phosphorus ลง 0.10% และ Calcium ลง 0.05% อัตโนมัติ")
    
    if st.button("⚡ เริ่มเดินเครื่องคำนวณสูตรอาหารต้นทุนต่ำสุด (Run AI Low-Cost Linear Solver)", type="primary", use_container_width=True):
        with st.spinner("กระบวนการคำนวณเชิงเส้นกำลังจับคู่ราคาวัตถุดิบและกรดอะมิโน..."):
            prob = pulp.LpProblem("LayerLinearSolver", pulp.LpMinimize)
            ing_vars = {name: pulp.LpVariable(name, lowBound=float(d["min_limit"])/100.0, upBound=float(d["max_limit"])/100.0) for name, d in ingredients_data.items()}
            
            prob += pulp.lpSum([ing_vars[name] * float(d["price"]) for name, d in ingredients_data.items()]), "Total_Cost"
            prob += pulp.lpSum([ing_vars[name] for name in ingredients_data.keys()]) == 1.0, "Total_Weight"
            
            final_p = float(active_req["phos"]) - 0.10 if st.session_state.use_phytase else float(active_req["phos"])
            final_ca = float(active_req["calcium"]) - 0.05 if st.session_state.use_phytase else float(active_req["calcium"])
            
            prob += pulp.lpSum([ing_vars[name] * float(d["protein"]) for name, d in ingredients_data.items()]) >= float(active_req["protein"])
            prob += pulp.lpSum([ing_vars[name] * float(d["me"]) for name, d in ingredients_data.items()]) >= float(active_req["me"])
            prob += pulp.lpSum([ing_vars[name] * float(d["calcium"]) for name, d in ingredients_data.items()]) >= final_ca
            prob += pulp.lpSum([ing_vars[name] * float(d["phos"]) for name, d in ingredients_data.items()]) >= final_p
            prob += pulp.lpSum([ing_vars[name] * float(d["lysine"]) for name, d in ingredients_data.items()]) >= float(active_req["lysine"])
            prob += pulp.lpSum([ing_vars[name] * float(d["methionine"]) for name, d in ingredients_data.items()]) >= float(active_req["methionine"])
            prob += pulp.lpSum([ing_vars[name] * float(d["fiber"]) for name, d in ingredients_data.items()]) <= float(active_req["fiber_max"])
            prob += pulp.lpSum([ing_vars[name] * float(d["sodium"]) for name, d in ingredients_data.items()]) >= float(active_req["sodium_min"])
            prob += pulp.lpSum([ing_vars[name] * float(d["chloride"]) for name, d in ingredients_data.items()]) >= float(active_req["chloride_min"])
            prob += pulp.lpSum([ing_vars[name] * float(d["linoleic"]) for name, d in ingredients_data.items()]) >= float(active_req["linoleic_min"])

            prob.solve(pulp.PULP_CBC_CMD(msg=False))
            
            if pulp.LpStatus[prob.status] == "Optimal":
                st.success(f"✅ AI ประมวลผลสำเร็จ! ได้สูตรอาหารที่สมดุลและมีราคาประหยัดที่สุดตามความต้องการเรียบร้อย")
                st.session_state.optimized_weights = {name: ing_vars[name].varValue * 100.0 for name in ingredients_data.keys()}
            else:
                st.session_state.optimized_weights = {name: 0.0 for name in ingredients_data.keys()}
                st.error("❌ ไม่สามารถหาคำตอบที่ลงตัวได้ เนื่องจากข้อจำกัดวัตถุดิบบางตัวแน่นจนเกินไป โปรดเปิดสิทธิ์ขีดจำกัดสูงสุด (Max Limit) ในหน้าคลังข้อมูลให้กว้างขึ้น")

    if any(v > 0 for v in st.session_state.optimized_weights.values()):
        col_res1, col_res2 = st.columns([1.2, 1])
        with col_res1:
            st.markdown("#### 📊 แผนภาพวงกลมสัดส่วนวัตถุดิบอาหารที่ใช้ (Ingredient Proportion %)")
            clean_plot = [{"วัตถุดิบอาหาร (Ingredients)": k, "สัดส่วนที่ใช้ (Percentage %)": v} for k, v in st.session_state.optimized_weights.items() if v > 0.01]
            df_cp = pd.DataFrame(clean_plot).sort_values(by="สัดส่วนที่ใช้ (Percentage %)", ascending=False)
            fig_p = px.pie(df_cp, names="วัตถุดิบอาหาร (Ingredients)", values="สัดส่วนที่ใช้ (Percentage %)", hole=0.45, color_discrete_sequence=px.colors.sequential.YlOrBr)
            fig_p.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_p, use_container_width=True)
            st.dataframe(df_cp, use_container_width=True, hide_index=True)

        with col_res2:
            st.markdown("#### 🧪 สรุปผลวิเคราะห์ระดับสารอาหารจริงเปรียบเทียบเกณฑ์ (Nutrition Matrix Audit)")
            act_nut = {"protein": 0, "me": 0, "calcium": 0, "phos": 0, "lysine": 0, "methionine": 0, "fiber": 0, "sodium": 0, "linoleic": 0}
            net_cost = 0
            for name, w in st.session_state.optimized_weights.items():
                if w > 0:
                    ratio = w / 100.0
                    net_cost += ratio * float(ingredients_data[name]["price"])
                    for n_key in act_nut.keys():
                        if n_key in ingredients_data[name]:
                            act_nut[n_key] += ratio * float(ingredients_data[name][n_key])
            
            comparison_rows = [
                {"โภชนาการที่วิเคราะห์ (Nutrient Profiles)": "โปรตีนดิบรวม (Crude Protein %)", "ค่าจริงในสูตร (Actual)": round(act_nut["protein"], 2), "เกณฑ์กำหนด (Target Constraint)": f">= {active_req['protein']}"},
                {"โภชนาการที่วิเคราะห์ (Nutrient Profiles)": "พลังงานใช้ประโยชน์ได้ (Metabolizable Energy kcal/kg)", "ค่าจริงในสูตร (Actual)": round(act_nut["me"], 0), "เกณฑ์กำหนด (Target Constraint)": f">= {active_req['me']}"},
                {"โภชนาการที่วิเคราะห์ (Nutrient Profiles)": "แคลเซียมเพื่อเปลือกไข่ (Calcium %)", "ค่าจริงในสูตร (Actual)": round(act_nut["calcium"], 2), "เกณฑ์กำหนด (Target Constraint)": f">= {active_req['calcium']}"},
                {"โภชนาการที่วิเคราะห์ (Nutrient Profiles)": "ฟอสฟอรัสที่เป็นประโยชน์ (Available Phosphorus %)", "ค่าจริงในสูตร (Actual)": round(act_nut["phos"], 2), "เกณฑ์กำหนด (Target Constraint)": f">= {active_req['phos']}"},
                {"โภชนาการที่วิเคราะห์ (Nutrient Profiles)": "กรดอะมิโน ไลซีน (Lysine %)", "ค่าจริงในสูตร (Actual)": round(act_nut["lysine"], 2), "เกณฑ์กำหนด (Target Constraint)": f">= {active_req['lysine']}"},
                {"โภชนาการที่วิเคราะห์ (Nutrient Profiles)": "กรดอะมิโน เมทไธโอนีน (Methionine %)", "ค่าจริงในสูตร (Actual)": round(act_nut["methionine"], 2), "เกณฑ์กำหนด (Target Constraint)": f">= {active_req['methionine']}"},
                {"โภชนาการที่วิเคราะห์ (Nutrient Profiles)": "กรดไขมันไลโนเลอิกเพื่อไซส์ฟอง (Linoleic Acid %)", "ค่าจริงในสูตร (Actual)": round(act_nut["linoleic"], 2), "เกณฑ์กำหนด (Target Constraint)": f">= {active_req['linoleic_min']}"},
                {"โภชนาการที่วิเคราะห์ (Nutrient Profiles)": "ไฟเบอร์กากใยสูงสุด (Crude Fiber Max %)", "ค่าจริงในสูตร (Actual)": round(act_nut["fiber"], 2), "เกณฑ์กำหนด (Target Constraint)": f"<= {active_req['fiber_max']}"}
            ]
            st.markdown(f"<h3 style='color:#ffb703 !important; text-align:center;'>💰 ต้นทุนค่าอาหาร: {net_cost:.2f} บาท / กิโลกรัม (THB/KG)</h3>", unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# 📊 [แท็บที่ 2]: แผนสถิติและใบสั่งซื้อวัตถุดิบ (Procurement & PO Sheet)
# =========================================================
with page_tabs[1]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 📊 ระบบประเมินน้ำหนักวัตถิบและส่งออกใบสั่งซื้อ (Purchase Order Document)")
    
    total_tonnage = st.number_input("ป้อนจำนวนยอดการผลิตอาหารสัตว์รวมสำหรับล๊อตนี้ (น้ำหนักกิโลกรัม / Total Batch Weight KG):", min_value=100, max_value=10000000, value=2000, step=1000)
    
    po_table_buffer = []
    accumulated_po_cost = 0
    
    for ing_title, weight_percentage in st.session_state.optimized_weights.items():
        if weight_percentage > 0.01:
            exact_weight_kg = (weight_percentage / 100.0) * total_tonnage
            item_cost_evaluation = exact_weight_kg * float(ingredients_data[ing_title]["price"])
            accumulated_po_cost += item_cost_evaluation
            po_table_buffer.append({
                "รายการวัตถุดิบในคลัง (Material Description)": ing_title,
                "น้ำหนักสุทธิที่ต้องใช้ (Net Weight KG)": round(exact_weight_kg, 2),
                "ราคารวมโดยประมาณ (Total Cost THB)": round(item_cost_evaluation, 2)
            })
            
    if po_table_buffer:
        df_final_po = pd.DataFrame(po_table_buffer)
        st.dataframe(df_final_po, use_container_width=True, hide_index=True)
        
        stat_c1, stat_c2 = st.columns(2)
        with stat_c1:
            st.metric("💵 ยอดงบประมาณรวมจัดซื้อวัตถุดิบล็อตนี้ (Estimated Budget)", f"{accumulated_po_cost:,.2f} บาท (THB)")
        with stat_c2:
            st.metric("🏷️ ต้นทุนเฉลี่ยของสูตรล็อตนี้ (Average Cost per KG)", f"{(accumulated_po_cost / total_tonnage):.2f} บาท/กก.")
            
        csv_stream = io.StringIO()
        df_final_po.to_csv(csv_stream, index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 ดาวน์โหลดใบส่งสั่งซื้อวัตถุดิบอาหารสัตว์ (Export Purchase Order to CSV)",
            data=csv_stream.getvalue(),
            file_name=f"PO_Batch_{total_tonnage}KG.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.warning("⚠️ ไม่พบโครงสร้างส่วนผสมอาหาร กรุณากดปุ่มคำนวณสูตรอาหารปัญญาประดิษฐ์ในแท็บแรกก่อน")
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# 📦 [แท็บที่ 3]: คลังข้อมูลระบบและตารางโครงสร้าง (SQL Editor Control)
# =========================================================
with page_tabs[2]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 📦 ส่วนประสานงานข้อมูลระบบ SQL และเขียนทับคลาวด์ข้อมูล (SQL Sync & Database Management)")
    
    database_action_mode = st.radio(
        "⚡ เลือกเป้าหมายโครงสร้างตารางที่คุณต้องการปรับแต่ง (Select Target SQL Table to Update):",
        [
            "📁 ปรับเปลี่ยนพารามิเตอร์ตารางกลุ่มใหญ่ (Chicken Groups Table)", 
            "🪶 ปรับเปลี่ยนพารามิเตอร์ตารางรายสายพันธุ์เดี่ยว (Chicken Breeds Table)"
        ],
        horizontal=True
    )
    st.markdown("<br>", unsafe_allow_html=True)
    
    if database_action_mode == "📁 ปรับเปลี่ยนพารามิเตอร์ตารางกลุ่มใหญ่ (Chicken Groups Table)":
        st.markdown("#### ✏️ แก้ไขข้อมูลแนวโน้มตลาดกลุ่มแม่ไก่ไข่ (Update Breeding Group Trend)")
        avail_groups = [g["group_name"] for g in groups_list]
        selected_g_to_update = st.selectbox("เลือกชื่อกลุ่มข้อมูลที่ต้องการแก้ไข (Select Group Name):", avail_groups)
        
        group_current_obj = next(g for g in groups_list if g["group_name"] == selected_g_to_update)
        st.info(f"📝 ค่าปัจจุบันในระบบ (Current Data): {group_current_obj.get('market_trend')}")
        new_trend_text = st.text_area("ป้อนข้อมูลแนวโน้มตลาดอัปเดตใหม่ล่าสุด (Enter New Market Trend):")
        
        if st.button("💾 บันทึกการเปลี่ยนแปลงข้อมูลกลุ่มใหญ่ (Save Group Changes to SQL)"):
            if new_trend_text:
                try:
                    sb_engine = create_client(st.session_state.supabase_url, st.session_state.supabase_key)
                    sb_engine.table("chicken_groups").update({"market_trend": new_trend_text}).eq("group_name", selected_g_to_update).execute()
                    st.success(f"🎉 อัปเดตข้อมูลตารางกลุ่มเสร็จสิ้น! ระบบกำลังทำความสะอาดแคชใน 2 วินาที...")
                    st.cache_data.clear()
                except Exception as db_err:
                    st.error(f"❌ ล้มเหลวเนื่องจากข้อจำกัดสิทธิ์ผู้ใช้หรือ RLS Lock: {str(db_err)}")
            else:
                st.warning("⚠️ โปรดเขียนข้อความคำอธิบายใหม่ลงในช่องว่างก่อนกดยืนยัน")
                
    else:
        st.markdown("#### ✏️ แก้ไขเกณฑ์ปริมาณการกินอาหารมาตรฐานรายสายพันธุ์ (Update Breed Intake Parameter)")
        avail_breeds_map = {b["breed_name"]: b for b in breeds_list}
        selected_b_to_update_label = st.selectbox("เลือกรายชื่อสายพันธุ์ที่ต้องการแก้ไข (Select Breed Target):", list(avail_breeds_map.keys()))
        breed_current_obj = avail_breeds_map[selected_b_to_update_label]
        
        st.info(f"💡 เกณฑ์กินอาหารปัจจุบันของสายพันธุ์นี้คือ (Current Intake): {breed_current_obj.get('default_feed')} กรัม/วัน/ตัว")
        new_feed_intake_value = st.number_input("กำหนดตัวเลขเกณฑ์การกินอาหารใหม่ (กรัม / Enter New Feed Intake g):", min_value=70, max_value=160, value=int(breed_current_obj.get('default_feed')))
        
        if st.button("💾 บันทึกพารามิเตอร์สายพันธุ์ลงฐานข้อมูล (Save Breed Parameters to SQL)"):
            try:
                sb_engine = create_client(st.session_state.supabase_url, st.session_state.supabase_key)
                sb_engine.table("chicken_breeds").update({"default_feed": new_feed_intake_value}).eq("breed_key", breed_current_obj["breed_key"]).execute()
                st.success(f"🎉 อัปเดตปริมาณการกินอาหารมาตรฐานรายสายพันธุ์สำเร็จเรียบร้อย!")
                st.cache_data.clear()
            except Exception as db_err:
                st.error(f"❌ ระบบคลาวด์ปลายทางปฏิเสธคำสั่งเขียนทับ (สลับกลับเข้าโครงสร้าง Failsafe เรียบร้อย): {str(db_err)}")
                
    st.markdown("---")
    st.markdown("### 📋 เอกสารระบุระดับสารอาหารของวัตถุดิบทั้งหมดที่มีในฐานข้อมูล (All Ingredients Analytical Profile)")
    df_raw_ing = pd.DataFrame.from_dict(ingredients_data, orient='index')
    if not df_raw_ing.empty:
        df_raw_ing.rename(columns={
            "price": "ราคา(บาท/กก.)", "protein": "โปรตีนดิบ(%)", "me": "พลังงานสัตว์(ME)",
            "calcium": "แคลเซียม(%)", "phos": "ฟอสฟอรัส(%)", "lysine": "กรดไลซีน(%)",
            "methionine": "กรดเมท(%)", "threonine": "ทรีโอนีน(%)", "fat": "ไขมันดิบ(%)", 
            "fiber": "กากใย(%)", "min_limit": "ขั้นต่ำ(%)", "max_limit": "สูงสุด(%)"
        }, inplace=True)
        st.dataframe(df_raw_ing, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
