import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pulp
from datetime import datetime
from supabase import create_client, Client

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
    .content-card {
        background-color: rgba(0, 0, 0, 0.75) !important; padding: 25px;
        border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(8px); margin-bottom: 20px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem !important; color: #38bdf8 !important;
        font-weight: bold !important; text-shadow: 1px 1px 2px rgba(0,0,0,0.9);
    }
    /* Style สำหรับ Dataframe ให้สีสว่างขึ้นเพื่อให้อ่านง่าย */
    [data-testid="stDataFrame"] { background-color: rgba(255,255,255,0.9) !important; border-radius: 10px; padding: 5px; }
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================================
# 🔐 2. ระบบล็อคอินและยืนยันตัวตนด้วย Supabase
# ==========================================
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"  # สถานะหน้าต่าง: login, register, forgot

def switch_auth_mode(mode):
    st.session_state.auth_mode = mode

def init_supabase(url, key):
    try:
        return create_client(url, key)
    except Exception:
        return None

if not st.session_state.is_authenticated:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center;'>🔐 ยินดีต้อนรับสู่ Mega Feed & Breed Studio</h2>", unsafe_allow_html=True)
    
    with st.expander("☁️ การเชื่อมต่อคลาวด์และฐานข้อมูลหลัก (Supabase Configuration)", expanded=False):
        c_db1, c_db2 = st.columns(2)
        with c_db1:
            SUPABASE_URL = st.text_input("ลิงก์โปรเจกต์ Supabase", "https://your-mega-project.supabase.co").strip()
        with c_db2:
            SUPABASE_KEY = st.text_input("รหัสผ่าน API (Anon Key)", "your-anon-key", type="password").strip()

    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # ---------------------------------
        # โหมด: เข้าสู่ระบบ (Login)
        # ---------------------------------
        if st.session_state.auth_mode == "login":
            st.markdown("<h3 style='text-align: center;'>🔑 เข้าสู่ระบบ</h3>", unsafe_allow_html=True)
            email_login = st.text_input("📧 อีเมล หรือ ชื่อผู้ใช้ (Email / Username)", key="login_email")
            pass_login = st.text_input("🔑 รหัสผ่าน (Password)", type="password", key="login_pass")
            
            if st.button("เข้าสู่ระบบ (Login)", type="primary", use_container_width=True):
                # 1. เช็ครหัสแอดมิน (ข้ามระบบ Supabase ทันที)
                if email_login == "222" and pass_login == "222":
                    st.session_state.is_authenticated = True
                    st.session_state.user_email = "👑 Admin (222)"
                    st.success("✅ เข้าสู่ระบบสำเร็จ! ยินดีต้อนรับผู้ดูแลระบบ...")
                    st.rerun()
                    
                # 2. ถ้ารหัสแอดมินไม่ตรง ให้ไปเช็คกับฐานข้อมูล Supabase ตามปกติ
                elif SUPABASE_URL and SUPABASE_KEY and email_login and pass_login:
                    supabase: Client = init_supabase(SUPABASE_URL, SUPABASE_KEY)
                    if supabase:
                        try:
                            res = supabase.auth.sign_in_with_password({"email": email_login, "password": pass_login})
                            st.session_state.is_authenticated = True
                            st.session_state.user_email = res.user.email
                            st.success("✅ เข้าสู่ระบบสำเร็จ! กำลังเข้าสู่แอปพลิเคชัน...")
                            st.rerun()
                        except Exception as e:
                            st.error("❌ อีเมล/ชื่อผู้ใช้ หรือรหัสผ่านไม่ถูกต้อง")
                    else:
                        st.error("❌ ไม่สามารถเชื่อมต่อ Supabase ได้ กรุณาตรวจสอบ URL/Key")
                else:
                    st.warning("⚠️ กรุณากรอกข้อมูลให้ครบถ้วน (หรือใช้รหัสแอดมินเพื่อข้ามระบบฐานข้อมูล)")
            
            st.markdown("<br>", unsafe_allow_html=True)
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                st.button("📝 สมัครสมาชิกใหม่", on_click=switch_auth_mode, args=("register",), use_container_width=True)
            with c_btn2:
                st.button("❓ ลืมรหัสผ่าน", on_click=switch_auth_mode, args=("forgot",), use_container_width=True)

        # ---------------------------------
        # โหมด: สมัครสมาชิก (Register)
        # ---------------------------------
        elif st.session_state.auth_mode == "register":
            st.markdown("<h3 style='text-align: center;'>📝 สมัครสมาชิกใหม่</h3>", unsafe_allow_html=True)
            email_reg = st.text_input("📧 อีเมล (Email)", key="reg_email")
            pass_reg = st.text_input("🔑 รหัสผ่าน (Password)", type="password", key="reg_pass")
            pass_confirm = st.text_input("🔑 ยืนยันรหัสผ่าน (Confirm Password)", type="password", key="reg_pass_confirm")
            
            if st.button("ยืนยันการสมัครสมาชิก", type="primary", use_container_width=True):
                if SUPABASE_URL and SUPABASE_KEY and email_reg and pass_reg and pass_confirm:
                    if pass_reg != pass_confirm:
                        st.error("❌ รหัสผ่านไม่ตรงกัน กรุณาพิมพ์ใหม่อีกครั้ง")
                    elif len(pass_reg) < 6:
                        st.error("❌ รหัสผ่านต้องมีความยาวอย่างน้อย 6 ตัวอักษร")
                    else:
                        supabase: Client = init_supabase(SUPABASE_URL, SUPABASE_KEY)
                        if supabase:
                            try:
                                res = supabase.auth.sign_up({"email": email_reg, "password": pass_reg})
                                st.success("✅ สมัครสมาชิกสำเร็จ! กรุณายืนยันอีเมล (ถ้าตั้งค่าไว้) หรือล็อคอินได้เลย")
                            except Exception as e:
                                st.error(f"❌ สมัครสมาชิกล้มเหลว: {str(e)}")
                        else:
                            st.error("❌ ไม่สามารถเชื่อมต่อ Supabase ได้")
                else:
                    st.warning("⚠️ กรุณากรอกข้อมูลการเชื่อมต่อ Supabase และข้อมูลสมัครสมาชิกให้ครบถ้วน")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("⬅️ กลับไปหน้าเข้าสู่ระบบ", on_click=switch_auth_mode, args=("login",), use_container_width=True)

        # ---------------------------------
        # โหมด: ลืมรหัสผ่าน (Forgot Password)
        # ---------------------------------
        elif st.session_state.auth_mode == "forgot":
            st.markdown("<h3 style='text-align: center;'>❓ ลืมรหัสผ่าน</h3>", unsafe_allow_html=True)
            st.info("ระบบจะส่งลิงก์สำหรับตั้งรหัสผ่านใหม่ไปยังอีเมลของคุณ")
            email_forgot = st.text_input("📧 กรอกอีเมลที่ใช้สมัคร (Email)", key="forgot_email")
            
            if st.button("ส่งลิงก์รีเซ็ตรหัสผ่าน", type="primary", use_container_width=True):
                if SUPABASE_URL and SUPABASE_KEY and email_forgot:
                    supabase: Client = init_supabase(SUPABASE_URL, SUPABASE_KEY)
                    if supabase:
                        try:
                            supabase.auth.reset_password_email(email_forgot)
                            st.success(f"✅ ส่งลิงก์ไปยัง {email_forgot} เรียบร้อยแล้ว! กรุณาตรวจสอบในกล่องจดหมายของคุณ")
                        except Exception as e:
                            st.error(f"❌ ไม่สามารถส่งอีเมลได้: {str(e)}")
                    else:
                        st.error("❌ ไม่สามารถเชื่อมต่อ Supabase ได้")
                else:
                    st.warning("⚠️ กรุณากรอกอีเมลให้ครบถ้วน")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("⬅️ กลับไปหน้าเข้าสู่ระบบ", on_click=switch_auth_mode, args=("login",), use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==========================================
# 🎉 3. ส่วนหัว (Header) สำหรับผู้ใช้ที่ล็อคอินแล้ว
# ==========================================
col_h1, col_h2 = st.columns([8, 2])
with col_h1:
    st.markdown("# 🐔 Mega Feed & Breed Studio")
    st.markdown("### ระบบปัญญาประดิษฐ์คำนวณสูตรอาหาร โภชนาการขั้นสูง และบริหารคลังสายพันธุ์สัตว์ปีกแห่งประเทศไทย")
with col_h2:
    st.markdown(f"<p style='text-align:right; margin-bottom:5px;'>👤 <b>{st.session_state.user_email}</b></p>", unsafe_allow_html=True)
    if st.button("ออกจากระบบ (Logout)", use_container_width=True):
        st.session_state.is_authenticated = False
        st.session_state.auth_mode = "login" # รีเซ็ตกลับไปหน้า login เสมอเมื่อออกจากระบบ
        st.rerun()

# ==========================================
# 📋 4. ฐานข้อมูลวัตถุดิบและสายพันธุ์
# ==========================================
MASTER_INGREDIENT_DICTIONARY = {
    "ข้าวโพดบดเม็ด": {"price": 13.5, "protein": 8.5, "me": 3300.0, "calcium": 0.02, "phos": 0.25, "lysine": 0.24, "methionine": 0.18, "threonine": 0.29, "fat": 3.8, "moisture": 12.0, "min_limit": 10.0, "max_limit": 70.0},
    "รำข้าวละเอียดดิบ": {"price": 11.0, "protein": 12.0, "me": 2400.0, "calcium": 0.05, "phos": 1.35, "lysine": 0.54, "methionine": 0.22, "threonine": 0.43, "fat": 13.0, "moisture": 10.5, "min_limit": 0.0, "max_limit": 25.0},
    "กากถั่วเหลือง (โปรตีน 44%)": {"price": 18.5, "protein": 44.0, "me": 2420.0, "calcium": 0.25, "phos": 0.60, "lysine": 2.70, "methionine": 0.62, "threonine": 1.72, "fat": 1.5, "moisture": 11.5, "min_limit": 5.0, "max_limit": 45.0},
    "ปลาป่นพรีเมียม (โปรตีน 60%)": {"price": 32.0, "protein": 60.0, "me": 2850.0, "calcium": 5.00, "phos": 3.00, "lysine": 4.50, "methionine": 1.80, "threonine": 2.40, "fat": 8.0, "moisture": 10.0, "min_limit": 0.0, "max_limit": 12.0},
    "น้ำมันปาล์มดิบกระสอบ": {"price": 34.0, "protein": 0.0, "me": 8400.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 99.0, "moisture": 0.5, "min_limit": 0.0, "max_limit": 4.0},
    "แอล-ไลซีน (L-Lysine HCl)": {"price": 85.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 78.40, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 1.0, "min_limit": 0.0, "max_limit": 1.2},
    "ดีแอล-เมทไธโอนีน (DL-Methionine)": {"price": 140.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 99.00, "threonine": 0.00, "fat": 0.0, "moisture": 0.5, "min_limit": 0.0, "max_limit": 1.0},
    "เปลือกหอยทะเลบดละเอียด": {"price": 4.0, "protein": 0.0, "me": 0.0, "calcium": 38.00, "phos": 0.04, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 0.5, "min_limit": 0.0, "max_limit": 12.0},
    "ไดแคลเซียมฟอสเฟต (DCP 18%)": {"price": 28.0, "protein": 0.0, "me": 0.0, "calcium": 21.00, "phos": 18.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 1.0, "min_limit": 0.0, "max_limit": 4.0},
    "เกลือแกงบริสุทธิ์ (NaCl)": {"price": 6.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 0.3, "min_limit": 0.1, "max_limit": 0.4},
    "พรีมิกซ์แร่ธาตุและวิตามินเข้มข้น": {"price": 120.0, "protein": 0.0, "me": 0.0, "calcium": 5.00, "phos": 1.20, "lysine": 0.00, "methionine": 0.00, "threonine": 0.00, "fat": 0.0, "moisture": 2.0, "min_limit": 0.2, "max_limit": 0.5}
}

BREED_PROFILES = {
    "ไก่ไข่ (Layers)": {
        "Isa Brown": {"name": "ไอซ่า บราวน์ (Isa Brown)", "egg_color": "🤎 น้ำตาล", "bg_color": "#b45309", "text_color": "#ffffff", "default_feed": 115, "desc": "ทนร้อน แผงเปลือกไข่หนา แตกหักยาก"},
    },
    "ไก่เนื้อ (Broilers)": {
        "Cobb 500": {"name": "ค็อบบ์ 500 (Cobb 500)", "egg_color": "❌ ไม่เน้นไข่", "bg_color": "#1e3a8a", "text_color": "#ffffff", "default_feed": 160, "desc": "โตไว อกหนา ค่า FCR ต่ำ"},
    }
}

STAGE_NUTRITION_TARGETS = {
    "starter": {"name": "ลูกไก่ (Starter)", "protein": 20.0, "me": 2900.0, "calcium": 1.00, "phos": 0.45, "lysine": 1.10, "methionine": 0.45},
    "grower": {"name": "ไก่รุ่น (Grower)", "protein": 16.0, "me": 2750.0, "calcium": 0.90, "phos": 0.40, "lysine": 0.85, "methionine": 0.38},
    "laying": {"name": "ไก่ไข่ระยะให้ผลผลิต (Laying)", "protein": 17.5, "me": 2750.0, "calcium": 4.10, "phos": 0.42, "lysine": 0.88, "methionine": 0.42}
}

# ==========================================
# ⚙️ 5. ตั้งค่า Session State และฟังก์ชัน
# ==========================================
if "chicken_count" not in st.session_state: st.session_state.chicken_count = 100
if "use_phytase" not in st.session_state: st.session_state.use_phytase = False
if "ingredient_data" not in st.session_state: st.session_state.ingredient_data = MASTER_INGREDIENT_DICTIONARY.copy()

if "optimized_weights" not in st.session_state:
    st.session_state.optimized_weights = {name: 0.0 for name in st.session_state.ingredient_data.keys()}
    st.session_state.optimized_weights["ข้าวโพดบดเม็ด"] = 55.0
    st.session_state.optimized_weights["กากถั่วเหลือง (โปรตีน 44%)"] = 30.0

def calculate_current_formulation():
    nut_calc = {"protein": 0.0, "me": 0.0, "calcium": 0.0, "phos": 0.0, "lysine": 0.0, "methionine": 0.0}
    cost = 0.0
    for name, weight in st.session_state.optimized_weights.items():
        f = weight / 100.0
        ing = st.session_state.ingredient_data.get(name, {})
        if ing:
            for k in nut_calc.keys():
                nut_calc[k] += ing.get(k, 0.0) * f
            cost += ing.get("price", 0.0) * f
    return nut_calc, cost

# ==========================================
# 📥 6. ส่วนแท็บและ UI (Tabs)
# ==========================================
page_tabs = st.tabs(["🏠 ระบบผสมสูตร AI", "📊 สถิติ & PO", "📦 คลังวัตถุดิบ"])

# --- [แท็บ 1]: AI Solver ---
with page_tabs[0]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    c_group, c_breed = st.columns(2)
    with c_group:
        sel_group = st.selectbox("เลือกกลุ่มสัตว์ปีก:", list(BREED_PROFILES.keys()))
    with c_breed:
        sel_breed_key = st.selectbox("เลือกสายพันธุ์:", list(BREED_PROFILES[sel_group].keys()), format_func=lambda x: BREED_PROFILES[sel_group][x]["name"])
    
    sel_stage = st.selectbox("โปรไฟล์โภชนาการตามช่วงอายุ:", list(STAGE_NUTRITION_TARGETS.keys()), format_func=lambda x: STAGE_NUTRITION_TARGETS[x]["name"])
    target = STAGE_NUTRITION_TARGETS[sel_stage]

    st.markdown("---")
    st.markdown("### 🧠 เครื่องคำนวณสมการเส้นตรง Least-Cost ด้วย AI")
    st.session_state.use_phytase = st.checkbox("🧪 เปิดใช้งานสารเสริมเอนไซม์ไฟเตส (ลดฟอสฟอรัส/แคลเซียมเป้าหมายลงอัตโนมัติ)")
    
    if st.button("⚡ เดินเครื่องระบบ AI ผสมสูตร (Run LP Solver)", type="primary"):
        # 1. กำหนดสมการ Minimize Cost
        prob = pulp.LpProblem("MegaPoultryLinearFeed", pulp.LpMinimize)
        
        # 2. สร้างตัวแปร
        ing_vars = {name: pulp.LpVariable(f"var_{i}", lowBound=data["min_limit"]/100.0, upBound=data["max_limit"]/100.0) 
                    for i, (name, data) in enumerate(st.session_state.ingredient_data.items())}
        
        # 3. Objective Function (ลดราคาให้ต่ำที่สุด)
        prob += pulp.lpSum([ing_vars[n] * data["price"] for n, data in st.session_state.ingredient_data.items()]), "Total_Cost"
        
        # 4. Constraints (ข้อจำกัด)
        # 4.1 น้ำหนักรวมต้องเท่ากับ 100% (1.0)
        prob += pulp.lpSum([ing_vars[n] for n in st.session_state.ingredient_data.keys()]) == 1.0, "Total_Weight"
        
        # 4.2 ปรับเป้าหมายถ้าใช้ Phytase
        adj_p = target["phos"] - 0.10 if st.session_state.use_phytase else target["phos"]
        adj_ca = target["calcium"] - 0.05 if st.session_state.use_phytase else target["calcium"]
        
        # 4.3 ข้อจำกัดโภชนาการขั้นต่ำ
        prob += pulp.lpSum([ing_vars[n] * data["protein"] for n, data in st.session_state.ingredient_data.items()]) >= target["protein"], "Min_Protein"
        prob += pulp.lpSum([ing_vars[n] * data["me"] for n, data in st.session_state.ingredient_data.items()]) >= target["me"], "Min_ME"
        prob += pulp.lpSum([ing_vars[n] * data["calcium"] for n, data in st.session_state.ingredient_data.items()]) >= adj_ca, "Min_Calcium"
        prob += pulp.lpSum([ing_vars[n] * data["phos"] for n, data in st.session_state.ingredient_data.items()]) >= adj_p, "Min_Phosphorus"
        prob += pulp.lpSum([ing_vars[n] * data["lysine"] for n, data in st.session_state.ingredient_data.items()]) >= target["lysine"], "Min_Lysine"
        prob += pulp.lpSum([ing_vars[n] * data["methionine"] for n, data in st.session_state.ingredient_data.items()]) >= target["methionine"], "Min_Methionine"

        # 5. สั่งแก้สมการ
        prob.solve()
        
        if pulp.LpStatus[prob.status] == "Optimal":
            st.success(f"✅ AI ประมวลผลสำเร็จ! (ราคาประเมิน: {pulp.value(prob.objective):.2f} บาท/กก.)")
            for n in st.session_state.ingredient_data.keys():
                st.session_state.optimized_weights[n] = ing_vars[n].varValue * 100.0
        else:
            st.error("❌ AI ไม่สามารถหาสูตรที่ตรงตามเงื่อนไขโภชนาการได้ (Infeasible) โปรดตรวจสอบ Min/Max limit ของวัตถุดิบ")

    # แสดงผลสูตรปัจจุบัน
    current_nut, current_cost = calculate_current_formulation()
    st.markdown(f"#### 💰 ต้นทุนสูตรอาหารปัจจุบัน: {current_cost:.2f} บาท / กก.")
    
    # วาดกราฟสัดส่วนวัตถุดิบ (เฉพาะที่มีค่า > 0)
    plot_data = [{"วัตถุดิบ": k, "สัดส่วน (%)": v} for k, v in st.session_state.optimized_weights.items() if v > 0.01]
    if plot_data:
        df_plot = pd.DataFrame(plot_data)
        fig = px.pie(df_plot, names="วัตถุดิบ", values="สัดส่วน (%)", hole=0.4, title="สัดส่วนวัตถุดิบในสูตร")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- [แท็บ 2]: สถิติฟาร์ม & ใบจัดซื้อ (PO) ---
with page_tabs[1]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 📊 บันทึกสถิติและสร้างใบสั่งซื้อ (PO)")
    st.info("กำลังพัฒนาฟีเจอร์: บันทึกข้อมูลการบริโภครายวัน การออกไข่ และการเชื่อมต่อระบบสั่งซื้อ (Purchase Order) เข้ากับซัพพลายเออร์อัตโนมัติ")
    
    # จำลองตารางใบสั่งซื้อที่คำนวณจากสูตรอาหาร
    st.markdown("#### 🛒 จำลองใบสั่งซื้อวัตถุดิบประจำสัปดาห์ (ตัน)")
    po_data = []
    for k, v in st.session_state.optimized_weights.items():
        if v > 0.01:
            po_data.append({"รายการ": k, "จำนวนที่ต้องสั่ง (กก.)": f"{(v / 100) * 1000 * 7:.2f}", "ราคาประเมิน (บาท)": f"{(v / 100) * 1000 * 7 * st.session_state.ingredient_data[k]['price']:,.2f}"})
    if po_data:
        st.dataframe(pd.DataFrame(po_data), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- [แท็บ 3]: ศูนย์จัดการคลังวัตถุดิบ ---
with page_tabs[2]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 📦 ศูนย์จัดการคลังวัตถุดิบ (Master Database)")
    st.markdown("ตารางข้อมูลโภชนาการและราคาของวัตถุดิบทั้งหมดที่มีในระบบ")
    
    # จัดเรียงข้อมูลเพื่อแสดงผลบน DataFrame
    df_ingredients = pd.DataFrame.from_dict(st.session_state.ingredient_data, orient='index')
    # เปลี่ยนชื่อคอลัมน์ให้อ่านง่าย
    df_ingredients.rename(columns={
        "price": "ราคา (บาท)", "protein": "โปรตีน (%)", "me": "พลังงาน (kcal)",
        "calcium": "แคลเซียม (%)", "phos": "ฟอสฟอรัส (%)", "lysine": "ไลซีน (%)",
        "methionine": "เมทไธโอนีน (%)", "min_limit": "Limit ต่ำสุด (%)", "max_limit": "Limit สูงสุด (%)"
    }, inplace=True)
    
    st.dataframe(df_ingredients, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
