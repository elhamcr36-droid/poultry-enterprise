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
    page_title="Mega Feed & Breed Studio - Ultimate Layer Pack", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ปรับสไตล์หน้าจอเป็น Cyber Dark Theme พร้อมกล่องโปร่งแสงมองทะลุพื้นหลังภาพ Unsplash
st.markdown(
    """
    <style>
    [data-testid="collapsedControl"] { display: none; }
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.78), rgba(0, 0, 0, 0.78)), 
                          url("https://images.unsplash.com/photo-1548550023-2bdb3c5beed7?q=80&w=1920");
        background-size: cover; background-position: center;
        background-repeat: no-repeat; background-attachment: fixed;
    }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, [data-testid="stHeader"] {
        color: #ffffff !important;
        text-shadow: 2px 2px 5px rgba(0, 0, 0, 0.95) !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(255, 255, 255, 0.12) !important;
        padding: 10px; border-radius: 12px; backdrop-filter: blur(12px);
    }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-weight: bold !important; font-size:1.05rem !important; }
    .content-card {
        background-color: rgba(0, 0, 0, 0.82) !important; padding: 25px;
        border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.22);
        backdrop-filter: blur(10px); margin-bottom: 20px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem !important; color: #ffb703 !important;
        font-weight: bold !important; text-shadow: 1px 1px 3px rgba(0,0,0,0.95);
    }
    [data-testid="stDataFrame"] { background-color: rgba(255,255,255,0.92) !important; border-radius: 10px; padding: 5px; }
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
    st.markdown("<h2 style='text-align: center;'>🔐 ยินดีต้อนรับสู่ ระบบวิเคราะห์โภชนาการไก่ไข่และสายพันธุ์ระดับสากล</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    col_l1, col_l2, col_l3 = st.columns([1, 1.8, 1])
    with col_l2:
        email_login = st.text_input("📧 รหัสอีเมลผู้ใช้งาน (หรือคีย์ทางลัด)", key="login_email")
        pass_login = st.text_input("🔑 รหัสผ่านเข้าใช้งาน", type="password", key="login_pass")
        
        if st.button("ยืนยันสิทธิ์เข้าสู่ระบบ (Login)", type="primary", use_container_width=True):
            if email_login in ["222", "จีเมล222", "222@gmail.com"] and pass_login in ["222", "รหัส222"]:
                st.session_state.is_authenticated = True
                st.session_state.user_email = "👑 Admin Layer-Studio Superuser"
                st.session_state.supabase_url = CORRECT_URL
                st.session_state.supabase_key = CORRECT_KEY
                st.rerun()
            else:
                st.error("❌ ข้อมูลสิทธิ์เข้าใช้งานไม่ถูกต้อง! (กรุณาใช้รหัสทางลัดของแอดมิน '222')")
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

    # --- LOCAL FAILSAFE BACKUP DATASET ---
    if not groups_data:
        groups_data = [
            {"group_name": "ไก่ไข่เปลือกสีน้ำตาล (Commercial Brown)", "bg_color": "#b45309", "text_color": "#ffffff", "market_trend": "ได้รับความนิยมสูงเป็นอันดับ 1 ในทวีปเอเชีย ไทย และยุโรป ผู้บริโภคเชื่อมั่นในคุณภาพเนื้อไข่แดงและขนาดฟอง"},
            {"group_name": "ไก่ไข่เปลือกสีขาว (Commercial White)", "bg_color": "#0284c7", "text_color": "#ffffff", "market_trend": "ครองตลาดใหญ่ในอเมริกาเหนือ โดดเด่นด้านการประหยัดต้นทุนค่าอาหาร (FCR ดีเยี่ยม) เหมาะกับโรงงานอุตสาหกรรมแปรรูปไข่เหลว"},
            {"group_name": "ไก่ไข่ทางเลือก/ตลาดพรีเมียม (Specialty Layers)", "bg_color": "#475569", "text_color": "#ffffff", "market_trend": "เซกเมนต์การเติบโตยุคใหม่ ตอบโจทย์วิถีฟาร์มปล่อยอิสระ (Free-Range), นทท. คาเฟ่สัตว์ และไข่ไก่ออร์แกนิกมูลค่าสูง"}
        ]
    if not breeds_data:
        breeds_data = [
            {"group_name": "ไก่ไข่เปลือกสีน้ำตาล (Commercial Brown)", "breed_key": "Isa Brown", "breed_name": "Isa Brown (ไอซ่า บราวน์)", "egg_color": "🤎 สีน้ำตาลเข้มสม่ำเสมอ", "default_feed": 114, "description": "สายพันธุ์ฝรั่งเศส ยอดนิยมอันดับ 1 ในไทย แข็งแรง ทนสภาพอากาศร้อนชื้นได้ดีเลิศ ไข่ดกยาวนานสม่ำเสมอ"},
            {"group_name": "ไก่ไข่เปลือกสีน้ำตาล (Commercial Brown)", "breed_key": "Lohmann Brown", "breed_name": "Lohmann Brown (โลห์แมน บราวน์)", "egg_color": "🤎 สีน้ำตาลเงางาม", "default_feed": 116, "description": "สายพันธุ์เยอรมัน โดดเด่นเรื่องไข่ฟองใหญ่ (เปอร์เซ็นต์ไข่ไซส์ใหญ่พิเศษ (XL) สูงมาก เปลือกหนาเหนียว"},
            {"group_name": "ไก่ไข่เปลือกสีน้ำตาล (Commercial Brown)", "breed_key": "Hy-Line Brown", "breed_name": "Hy-Line Brown (ไฮ-ไลน์ บราวน์)", "egg_color": "🤎 สีน้ำตาลประกายทอง", "default_feed": 112, "description": "สายพันธุ์อเมริกา นิ่ง ไม่ตื่นตกใจง่าย อัตราการเปลี่ยนอาหารเป็นน้ำหนักไข่ดีเยี่ยม เหมาะกับฟาร์มระบบปิดอีแวป"},
            {"group_name": "ไก่ไข่เปลือกสีขาว (Commercial White)", "breed_key": "Hy-Line W-36", "breed_name": "Hy-Line W-36 (ไฮ-ไลน์ ขาว W-36)", "egg_color": "🥚 สีขาวสะอาดตา", "default_feed": 101, "description": "แชมป์โลกความประหยัด กินอาหารน้อยที่สุดในอุตสาหกรรม ให้ไข่ฟองสีขาวข้นแน่นสูง ปริมาณไข่ขาว (Albumen) หนาตัวดีมาก"},
            {"group_name": "ไก่ไข่เปลือกสีขาว (Commercial White)", "breed_key": "Dekalb White", "breed_name": "Dekalb White (เดคัลบ์ ไวท์)", "egg_color": "🥚 สีขาวพรีเมียมฉลุ", "default_feed": 103, "description": "สายพันธุ์ที่วิจัยมาเพื่อลดปัญหาไข่บุบสลายระหว่างคัดแยก ขนส่งทางไกลได้ดีเยี่ยม ยืนกรงทำผลผลิตพีคได้ยาวนาน"},
            {"group_name": "ไก่ไข่ทางเลือก/ตลาดพรีเมียม (Specialty Layers)", "breed_key": "Novogen Tinted", "breed_name": "Novogen Tinted (โนโวเจน ทินต์)", "egg_color": "💮 สีครีมพาสเทล / ชมพูนวล", "default_feed": 110, "description": "ผลิตไข่เปลือกสีนวลครีมแปลกใหม่ ตลาดพรีเมียมให้ราคาดี พฤติกรรมเรียบร้อย ไม่จิกตีกัน เหมาะกับการเลี้ยงปล่อยลาน"}
        ]
    if not ing_data:
        ing_data = [
            {"name": "ข้าวโพดบดเม็ด (Corn)", "price": 13.5, "protein": 8.5, "me": 3300.0, "calcium": 0.02, "phos": 0.25, "lysine": 0.24, "methionine": 0.18, "threonine": 0.29, "fat": 3.8, "moisture": 12.0, "fiber": 2.2, "sodium": 0.02, "chloride": 0.04, "linoleic": 2.2, "min_limit": 10.0, "max_limit": 65.0},
            {"name": "กากถั่วเหลือง 46% (SBM 46%)", "price": 19.5, "protein": 46.0, "me": 2440.0, "calcium": 0.25, "phos": 0.62, "lysine": 2.85, "methionine": 0.65, "threonine": 1.80, "fat": 1.5, "moisture": 11.0, "fiber": 3.5, "sodium": 0.02, "chloride": 0.05, "linoleic": 0.5, "min_limit": 10.0, "max_limit": 40.0},
            {"name": "ปลาป่นเกรด A 60% (Fish Meal 60%)", "price": 35.0, "protein": 60.0, "me": 2850.0, "calcium": 5.00, "phos": 3.00, "lysine": 4.50, "methionine": 1.80, "threonine": 2.40, "fat": 8.0, "moisture": 10.0, "fiber": 1.0, "sodium": 1.20, "chloride": 1.50, "linoleic": 0.2, "min_limit": 0.0, "max_limit": 8.0},
            {"name": "หินฝุ่นเม็ดหยาบ 2-4 มม. (Limestone)", "price": 2.5, "protein": 0.0, "me": 0.0, "calcium": 38.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 0.5, "fiber": 0.0, "sodium": 0.00, "chloride": 0.00, "linoleic": 0.0, "min_limit": 0.0, "max_limit": 12.0},
            {"name": "ไดแคลเซียมฟอสเฟต (DCP 18%)", "price": 28.0, "protein": 0.0, "me": 0.0, "calcium": 21.00, "phos": 18.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 1.0, "fiber": 0.0, "sodium": 0.00, "chloride": 0.00, "linoleic": 0.0, "min_limit": 0.0, "max_limit": 3.0},
            {"name": "เกลือแกงบริสุทธิ์ (Salt - NaCl)", "price": 6.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 0.3, "fiber": 0.0, "sodium": 39.30, "chloride": 60.00, "linoleic": 0.0, "min_limit": 0.15, "max_limit": 0.45},
            {"name": "พรีมิกซ์วิตามินแร่ธาตุ (Premix)", "price": 160.0, "protein": 0.0, "me": 0.0, "calcium": 5.00, "phos": 1.20, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 2.0, "fiber": 0.0, "sodium": 0.00, "chloride": 0.00, "linoleic": 0.0, "min_limit": 0.25, "max_limit": 0.35}
        ]
    if not tgt_data:
        tgt_data = [
            {"stage_key": "layer_phase_1", "stage_name": "ไก่ไข่ระยะผลิตพีค Phase 1 (19-45 สัปดาห์)", "protein": 17.5, "me": 2750.0, "calcium": 4.10, "phos": 0.42, "lysine": 0.88, "methionine": 0.42, "fiber_max": 4.5, "sodium_min": 0.16, "chloride_min": 0.16, "linoleic_min": 1.50},
            {"stage_key": "layer_phase_2", "stage_name": "ไก่ไข่ระยะกลาง Phase 2 (46-65 สัปดาห์)", "protein": 16.5, "me": 2725.0, "calcium": 4.30, "phos": 0.38, "lysine": 0.82, "methionine": 0.39, "fiber_max": 5.0, "sodium_min": 0.16, "chloride_min": 0.16, "linoleic_min": 1.30}
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
    st.markdown("# 🐔 Mega Feed & Breed Studio <span style='font-size:1.4rem; color:#f59e0b;'>(Universal Edition)</span>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#38bdf8; font-weight:bold;'>🎯 ศูนย์ผสมสูตรอาหารและวิเคราะห์กลุ่มประชากรแม่ไก่ไข่สากลเชิงพาณิชย์</p>", unsafe_allow_html=True)
with col_h2:
    st.markdown(f"<p style='text-align:right; margin:0;'>👤 <b>{st.session_state.user_email}</b></p>", unsafe_allow_html=True)
    if st.button("🔴 ออกจากระบบ (Logout)", use_container_width=True):
        st.session_state.is_authenticated = False
        st.rerun()

# แบ่งส่วนแท็บหลักของหน้าจอโปรแกรม
page_tabs = st.tabs(["🏠 ระบบผสมสูตรอาหาร AI", "📊 แผนสถิติ & เอกสารจัดซื้อ PO", "📦 คลังข้อมูลโครงสร้างระบบ (SQL Editor)"])

# =========================================================
# 🏠 [แท็บที่ 1]: ระบบผสมสูตรอาหาร AI + ปุ่มแยกกลุ่ม/สายพันธุ์
# =========================================================
with page_tabs[0]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("### 🎛️ ตัวเลือกกรองกลุ่มและประชากรแม่ไก่ไข่")
    
    # 📌 จุดแยกเด็ดขาด: ปุ่มเลือกคัดกรองระหว่างกลุ่ม หรือ รายสายพันธุ์เดี่ยว
    filter_mode = st.radio(
        "🔘 เลือกรูปแบบการเจาะลึกความต้องการทางพันธุกรรม:", 
        ["🧬 คัดกรองตามกลุ่มประเภทไก่ไข่หลัก (Breeding Groups)", "🐓 คัดกรองเจาะลึกรายสายพันธุ์การค้า (Commercial Breeds)"], 
        horizontal=True
    )
    
    current_selected_profile = {}
    
    if filter_mode == "🧬 คัดกรองตามกลุ่มประเภทไก่ไข่หลัก (Breeding Groups)":
        group_names = [g["group_name"] for g in groups_list]
        selected_g = st.selectbox("เลือกกลุ่มไก่ไข่เป้าหมายตลาด:", group_names)
        g_meta = next(g for g in groups_list if g["group_name"] == selected_g)
        
        # คำนวณความต้องการโภชนาการเฉลี่ยของกลุ่มย่อย
        associated_breeds = [b for b in breeds_list if b["group_name"] == selected_g]
        calculated_feed = int(sum(b["default_feed"] for b in associated_breeds)/len(associated_breeds)) if associated_breeds else 112
        
        st.markdown(f"""
        <div style='background-color: {g_meta["bg_color"]}; padding: 18px; border-radius: 12px;'>
            <h4 style='margin:0; color:{g_meta["text_color"]} !important;'>📂 โหมดกลุ่มหลัก: {selected_g}</h4>
            <p style='margin:6px 0 0 0; color:{g_meta["text_color"]} !important;'>
                <b>ทิศทางกลยุทธ์การตลาด:</b> {g_meta["market_trend"]}<br>
                <b>สถิติปริมาณอาหารกินเฉลี่ยของกลุ่มประชากรนี้:</b> {calculated_feed} กรัม/วัน/ตัว
            </p>
        </div>
        """, unsafe_allow_html=True)
        current_selected_profile = {"name": selected_g, "default_feed": calculated_feed}
        
    else:
        breed_dict = {b["breed_name"]: b for b in breeds_list}
        selected_b_name = st.selectbox("เลือกรายชื่อสายพันธุ์การค้าสากล:", list(breed_dict.keys()))
        b_meta = breed_dict[selected_b_name]
        g_meta = next((g for g in groups_list if g["group_name"] == b_meta["group_name"]), {"bg_color": "#1e293b", "text_color": "#ffffff"})
        
        st.markdown(f"""
        <div style='background-color: {g_meta["bg_color"]}; padding: 18px; border-radius: 12px;'>
            <h4 style='margin:0; color:{g_meta["text_color"]} !important;'>🐓 โหมดสายพันธุ์เดี่ยว: {b_meta["breed_name"]}</h4>
            <p style='margin:6px 0 0 0; color:{g_meta["text_color"]} !important;'>
                <b>สังกัดกลุ่มเทียร์:</b> {b_meta["group_name"]}<br>
                <b>มาตรฐานสีเปลือกไข่:</b> {b_meta["egg_color"]} | <b>ปริมาณกินอาหารจริง:</b> {b_meta["default_feed"]} กรัม/วัน/ตัว<br>
                <b>คำแนะนำเชิงเทคนิค:</b> {b_meta["description"]}
            </p>
        </div>
        """, unsafe_allow_html=True)
        current_selected_profile = b_meta

    st.markdown("---")
    st.markdown("### 🧬 กำหนดช่วงอายุและเป้าหมายสารอาหารที่เหมาะสม")
    stage_options = {s["stage_name"]: s["stage_key"] for s in targets_data.values()}
    selected_stage_label = st.selectbox("เลือกระยะอายุการให้ผลผลิตของฝูง:", list(stage_options.keys()))
    active_req = targets_data[stage_options[selected_stage_label]]
    
    st.session_state.use_phytase = st.checkbox("🧪 เติมสารเร่งเอนไซม์ไฟเตส (AI จะลดเกณฑ์ Phosphorus ลง 0.10% และ Calcium ลง 0.05% เพื่อประหยัดต้นทุนยิบย่อย)")
    
    if st.button("⚡ เริ่มเดินเครื่อง AI ประมวลผลสูตรต้นทุนต่ำที่สุด (Run LP Solver)", type="primary", use_container_width=True):
        with st.spinner("กระบวนการ Linear Programming กำลังจับคู่กรดอะมิโนและราคาวัตถุดิบ..."):
            prob = pulp.LpProblem("UltimateLayerSplitSolver", pulp.LpMinimize)
            
            # ประกาศตัวแปรตัดสินใจ (สัดส่วนร้อยละ 0.0 - 1.0)
            ing_vars = {name: pulp.LpVariable(name, lowBound=float(d["min_limit"])/100.0, upBound=float(d["max_limit"])/100.0) for name, d in ingredients_data.items()}
            
            # ฟังก์ชันเป้าหมาย: ราคาถูกที่สุด
            prob += pulp.lpSum([ing_vars[name] * float(d["price"]) for name, d in ingredients_data.items()]), "Total_Cost"
            # รวมสัดส่วนน้ำหนักสารอาหารต้องเท่ากับ 100%
            prob += pulp.lpSum([ing_vars[name] for name in ingredients_data.keys()]) == 1.0, "Total_Weight"
            
            # ปรับเกณฑ์สารอาหารตามสิทธิ์ไฟเตส
            final_p = float(active_req["phos"]) - 0.10 if st.session_state.use_phytase else float(active_req["phos"])
            final_ca = float(active_req["calcium"]) - 0.05 if st.session_state.use_phytase else float(active_req["calcium"])
            
            # ข้อจำกัดโภชนาการขั้นต่ำ-ขั้นสูง
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
                st.success(f"✅ AI ประมวลผลสำเร็จ! ได้สูตรอาหารที่สมดุลโภชนาการสูงที่สุดเรียบร้อย")
                st.session_state.optimized_weights = {name: ing_vars[name].varValue * 100.0 for name in ingredients_data.keys()}
            else:
                st.session_state.optimized_weights = {name: 0.0 for name in ingredients_data.keys()}
                st.error("❌ ไม่สามารถหาผลลัพธ์คำตอบได้ เนื่องจากข้อจำกัดวัตถุดิบบางตัวแน่นจนเกินไป โปรดเปิดสิทธิ์ Max Limit ให้กว้างขึ้นในหน้าคลังข้อมูล")

    # แสดงตารางวิเคราะห์และแผนภูมิวงกลมหลังกดคำนวณสูตรอาหารสำเร็จแล้ว
    if any(v > 0 for v in st.session_state.optimized_weights.values()):
        col_res1, col_res2 = st.columns([1.2, 1])
        with col_res1:
            st.markdown("#### 📊 แผนภาพวงกลมสัดส่วนวัตถุดิบอาหารที่ใช้ (%)")
            clean_plot = [{"วัตถุดิบ": k, "สัดส่วนจริง (%)": v} for k, v in st.session_state.optimized_weights.items() if v > 0.01]
            df_cp = pd.DataFrame(clean_plot).sort_values(by="สัดส่วนจริง (%)", ascending=False)
            fig_p = px.pie(df_cp, names="วัตถุดิบ", values="สัดส่วนจริง (%)", hole=0.45, color_discrete_sequence=px.colors.sequential.YlOrBr)
            fig_p.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_p, use_container_width=True)
            st.dataframe(df_cp, use_container_width=True, hide_index=True)

        with col_res2:
            st.markdown("#### 🧪 สรุปผลวิเคราะห์ระดับสารอาหารจริงเปรียบเทียบเกณฑ์")
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
                {"คุณสมบัติทางเคมี": "โปรตีนดิบรวม (Crude Protein %)", "ค่าจริงในสูตร": round(act_nut["protein"], 2), "เกณฑ์ข้อกำหนดขั้นต่ำ": f">= {active_req['protein']}"},
                {"คุณสมบัติทางเคมี": "พลังงานใช้ประโยชน์ได้ (ME kcal/kg)", "ค่าจริงในสูตร": round(act_nut["me"], 0), "เกณฑ์ข้อกำหนดขั้นต่ำ": f">= {active_req['me']}"},
                {"คุณสมบัติทางเคมี": "แคลเซียมเพื่อเปลือกไข่ (Calcium %)", "ค่าจริงในสูตร": round(act_nut["calcium"], 2), "เกณฑ์ข้อกำหนดขั้นต่ำ": f">= {active_req['calcium']}"},
                {"คุณสมบัติทางเคมี": "ฟอสฟอรัสที่เป็นประโยชน์ (Av. Phos %)", "ค่าจริงในสูตร": round(act_nut["phos"], 2), "เกณฑ์ข้อกำหนดขั้นต่ำ": f">= {active_req['phos']}"},
                {"คุณสมบัติทางเคมี": "กรดอะมิโน ไลซีน (Lysine %)", "ค่าจริงในสูตร": round(act_nut["lysine"], 2), "เกณฑ์ข้อกำหนดขั้นต่ำ": f">= {active_req['lysine']}"},
                {"คุณสมบัติทางเคมี": "กรดอะมิโน เมทไธโอนีน (Methionine %)", "ค่าจริงในสูตร": round(act_nut["methionine"], 2), "เกณฑ์ข้อกำหนดขั้นต่ำ": f">= {active_req['methionine']}"},
                {"คุณสมบัติทางเคมี": "กรดไขมันไลโนเลอิกเพื่อไซส์ฟอง (%)", "ค่าจริงในสูตร": round(act_nut["linoleic"], 2), "เกณฑ์ข้อกำหนดขั้นต่ำ": f">= {active_req['linoleic_min']}"},
                {"คุณสมบัติทางเคมี": "ไฟเบอร์กากใยสูงสุด (%)", "ค่าจริงในสูตร": round(act_nut["fiber"], 2), "เกณฑ์ข้อกำหนดสูงสุด": f"<= {active_req['fiber_max']}"}
            ]
            st.markdown(f"<h3 style='color:#ffb703 !important; text-align:center;'>💰 ราคาต้นทุนหน้าโรงงาน: {net_cost:.2f} บาท / กิโลกรัม</h3>", unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# 📊 [แท็บที่ 2]: ระบบออกเอกสารจัดซื้อใบ PO และสถิติล็อตการสั่งผลิต
# =========================================================
with page_tabs[1]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 📊 ระบบประเมินน้ำหนักวัตถุดิบและส่งออกเอกสารการค้า (Purchase Order)")
    
    total_tonnage = st.number_input("ป้อนจำนวนยอดการผลิตอาหารสัตว์รวมสำหรับล๊อตนี้ (กิโลกรัม):", min_value=100, max_value=10000000, value=2000, step=1000)
    
    po_table_buffer = []
    accumulated_po_cost = 0
    
    for ing_title, weight_percentage in st.session_state.optimized_weights.items():
        if weight_percentage > 0.01:
            exact_weight_kg = (weight_percentage / 100.0) * total_tonnage
            item_cost_evaluation = exact_weight_kg * float(ingredients_data[ing_title]["price"])
            accumulated_po_cost += item_cost_evaluation
            po_table_buffer.append({
                "รายการวัตถุดิบอาหารคลัง": ing_title,
                "น้ำหนักสุทธิที่ต้องใช้ (กก.)": round(exact_weight_kg, 2),
                "ราคาจัดซื้อโดยประมาณ (บาท)": round(item_cost_evaluation, 2)
            })
            
    if po_table_buffer:
        df_final_po = pd.DataFrame(po_table_buffer)
        st.dataframe(df_final_po, use_container_width=True, hide_index=True)
        
        stat_c1, stat_c2 = st.columns(2)
        with stat_c1:
            st.metric("💵 ยอดงบประมาณจัดซื้อจัดหาวัตถุดิบทั้งสิ้น", f"{accumulated_po_cost:,.2f} บาท")
        with stat_c2:
            st.metric("🏷️ ต้นทุนเฉลี่ยของสูตรอาหารล็อตนี้", f"{(accumulated_po_cost / total_tonnage):.2f} บาท/กก.")
            
        csv_stream = io.StringIO()
        df_final_po.to_csv(csv_stream, index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 ดาวน์โหลดใบส่งตัววัตถุดิบ (Export PO to CSV File)",
            data=csv_stream.getvalue(),
            file_name=f"PO_Production_Batch_{total_tonnage}KG.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.warning("⚠️ ไม่พบข้อมูลส่วนผสมในสูตรอาหาร กรุณากดปุ่มคำนวณ AI ในแท็บแรกก่อนเสมอ")
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# 📦 [แท็บที่ 3]: ศูนย์จัดการข้อมูลสารอาหาร SQL (ปุ่มแยกกลุ่ม VS สายพันธุ์เดี่ยว)
# =========================================================
with page_tabs[2]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 📦 ส่วนประสานงานระบบข้อมูล SQL และสิทธิ์เขียนทับข้อมูล Cloud")
    
    # 📌 ปุ่มวิทยุแยกเด็ดขาดระหว่างการอัปเดตข้อมูลระดับกลุ่มใหญ่ หรือ ระดับสายพันธุ์ย่อย
    database_action_mode = st.radio(
        "⚡ เลือกเป้าหมายโครงสร้างตารางที่คุณต้องการปรับแต่ง:",
        ["📁 ปรับเปลี่ยนพารามิเตอร์ตารางกลุ่มใหญ่ (chicken_groups)", "🪶 ปรับเปลี่ยนพารามิเตอร์ตารางรายสายพันธุ์เดี่ยว (chicken_breeds)"],
        horizontal=True
    )
    
    if database_action_mode == "📁 ปรับเปลี่ยนพารามิเตอร์ตารางกลุ่มใหญ่ (chicken_groups)":
        st.markdown("#### ✏️ ปรับปรุงแก้ไขตลาดของกลุ่มแม่ไก่ไข่")
        avail_groups = [g["group_name"] for g in groups_list]
        selected_g_to_update = st.selectbox("เลือกชื่อกลุ่มข้อมูลที่ต้องการแก้ไขแนวโน้ม:", avail_groups)
        
        group_current_obj = next(g for g in groups_list if g["group_name"] == selected_g_to_update)
        st.info(f"📝 ค่าปัจจุบันในระบบ: {group_current_obj.get('market_trend')}")
        new_trend_text = st.text_area("ป้อนข้อมูลแนวโน้มตลาดอัปเดตใหม่ล่าสุด:")
        
        if st.button("💾 บันทึกการเปลี่ยนแปลงข้อมูลกลุ่มส่งไปยังฐานข้อมูล SQL Primary Key"):
            if new_trend_text:
                try:
                    sb_engine = create_client(st.session_state.supabase_url, st.session_state.supabase_key)
                    sb_engine.table("chicken_groups").update({"market_trend": new_trend_text}).eq("group_name", selected_g_to_update).execute()
                    st.success(f"🎉 อัปเดตข้อมูลตารางกลุ่ม '{selected_g_to_update}' สำเร็จแล้ว หน้าจอจะทำความสะอาดแคชภายใน 2 วินาที")
                    st.cache_data.clear()
                except Exception as db_err:
                    st.error(f"❌ ล้มเหลวเนื่องจากข้อจำกัดสิทธิ์ผู้ใช้งาน (RLS Lock) หรือ ขาดการเชื่อมต่อ: {str(db_err)}")
            else:
                st.warning("⚠️ โปรดป้อนคำอธิบายแนวโน้มใหม่ลงในช่องข้อความก่อนกดยืนยัน")
                
    else:
        st.markdown("#### ✏️ ปรับปรุงปริมาณการกินอาหารมาตรฐานรายตัวของแต่ละสายพันธุ์")
        avail_breeds_map = {b["breed_name"]: b for b in breeds_list}
        selected_b_to_update_label = st.selectbox("เลือกรายชื่อสายพันธุ์ที่ต้องการปรับปรุงเกณฑ์ป้อน:", list(avail_breeds_map.keys()))
        breed_current_obj = avail_breeds_map[selected_b_to_update_label]
        
        st.info(f"💡 เกณฑ์กินอาหารปัจจุบันของสายพันธุ์นี้คือ: {breed_current_obj.get('default_feed')} กรัม/วัน/ตัว")
        new_feed_intake_value = st.number_input("กำหนดปริมาณการกินอาหารมาตรฐานตัวเลขใหม่ (กรัม):", min_value=70, max_value=160, value=int(breed_current_obj.get('default_feed')))
        
        if st.button("💾 บันทึกพารามิเตอร์สายพันธุ์ลงตารางไก่ไข่โลก"):
            try:
                sb_engine = create_client(st.session_state.supabase_url, st.session_state.supabase_key)
                sb_engine.table("chicken_breeds").update({"default_feed": new_feed_intake_value}).eq("breed_key", breed_current_obj["breed_key"]).execute()
                st.success(f"🎉 อัปเดตปริมาณกินอาหารของสายพันธุ์ '{breed_current_obj['breed_name']}' ลงฐานข้อมูลหลักสำเร็จ!")
                st.cache_data.clear()
            except Exception as db_err:
                st.error(f"❌ ระบบคลาวด์ปลายทางปฏิเสธคำสั่งเขียนทับ (สลับกลับเข้าสู่โครงสร้างเมทริกซ์ Failsafe ภายในแอปเรียบร้อย): {str(db_err)}")
                
    st.markdown("---")
    st.markdown("### 📋 เอกสารแนบสารอาหารวัตถุดิบทั้งหมด 26 ชนิดในระบบขณะนี้")
    df_raw_ing = pd.DataFrame.from_dict(ingredients_data, orient='index')
    if not df_raw_ing.empty:
        df_raw_ing.rename(columns={
            "price": "ราคา(บาท/กก.)", "protein": "โปรตีนดิบ(%)", "me": "พลังงานสัตว์(ME)",
            "calcium": "แคลเซียม(%)", "phos": "ฟอสฟอรัส(%)", "lysine": "กรดไลซีน(%)",
            "methionine": "กรดเมท(%)", "threonine": "ทรีโอนีน(%)", "fat": "ไขมันดิบ(%)", 
            "fiber": "กากใย(%)", "min_limit": "เกณฑ์ขั้นต่ำ(%)", "max_limit": "เกณฑ์สูงสุด(%)"
        }, inplace=True)
        st.dataframe(df_raw_ing, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
