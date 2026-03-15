import streamlit as st
import psycopg2
import os
import hashlib
import pandas as pd
from datetime import datetime
from scipy.optimize import linprog
import plotly.express as px
import numpy as np
import time

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Layer Smart AI System v4.2", layout="wide")

DATABASE_URL = os.getenv("DATABASE_URL")

# -------------------------
# PostgreSQL CONNECTION
# -------------------------
def get_conn():
    conn = psycopg2.connect(
        DATABASE_URL,
        sslmode="require"
    )
    return conn


LANG = {
    "TH": {
        "title": "🥚 ระบบ Smart Layer AI Professional v4.2",
        "login_header": "🔐 เข้าสู่ระบบ",
        "reg_header": "📝 สมัครสมาชิก",
        "forgot_header": "❓ กู้คืนรหัสผ่าน",
        "reset_header": "🔄 ตั้งรหัสผ่านใหม่",
        "user_label": "ชื่อผู้ใช้",
        "pass_label": "รหัสผ่าน",
        "fn_label": "ชื่อ-นามสกุล",
        "em_label": "อีเมล",
        "bd_label": "วันเกิด",
        "cp_label": "ยืนยันรหัสผ่าน",
        "btn_login": "เข้าสู่ระบบ",
        "btn_reg": "สมัครสมาชิกใหม่",
        "btn_forgot": "ลืมรหัสผ่าน%s",
        "btn_reg_submit": "ตกลงสมัคร",
        "btn_back": "กลับ",
        "btn_check": "ตรวจสอบอีเมล",
        "btn_save": "บันทึก",
        "nav_home": "หน้าหลัก",
        "nav_admin": "ระบบแอดมิน",
        "nav_logout": "ออกจากระบบ",
        "tab_calc": "🧮 คำนวณสูตรอาหาร",
        "tab_hist": "📜 ประวัติสูตรอาหารที่บันทึก",
        "tab_stock": "🌾 คลังวัตถุดิบ",
        "tab_feed": "💬 แนะนำติชม&ติดต่อเเอดมิน",
        "tab_profile": "👤 โปรไฟล์",
        "config_sec": "⚙️ ตั้งค่าเงื่อนไข",
        "group_label": "กลุ่มไก่ไข่",
        "breed_label": "สายพันธุ์",
        "stage_label": "ระยะการให้ไข่",
        "count_label": "จำนวนไก่ (ตัว)",
        "batch_label": "ปริมาณที่จะผสม (กก.)",
        "opt_label": "เป้าหมายการประมวลผล:",
        "mode_price": "💰 ราคาถูกที่สุด (Best Price)",
        "mode_nutri": "✨ สารอาหารแม่นยำที่สุด (Best Nutrition)",
        "income_sec": "💰 พยากรณ์รายได้",
        "egg_price_label": "ราคาไข่คาดการณ์ (บาท/ฟอง)",
        "lay_rate_label": "อัตราการให้ไข่ (%)",
        "btn_ai": "🚀 ประมวลผลสูตร AI",
        "res_header": "📊 ผลลัพธ์สัดส่วนวัตถุดิบ",
        "chart_title": "สัดส่วนการผสมวัตถุดิบ (%)",
        "protein_actual": "โปรตีนที่ได้จริง (%)",
        "energy_actual": "พลังงานที่ได้จริง (kcal)",
        "target_label": "เป้าหมาย",
        "table_name": "ชื่อวัตถุดิบ",
        "table_ratio": "สัดส่วน (%)",
        "table_need": "ต้องใช้ (กก.)",
        "profit_sec": "📈 พยากรณ์กำไรรายวัน",
        "cost_day": "ต้นทุนอาหาร/วัน",
        "rev_day": "รายได้ไข่/วัน",
        "profit_month": "กำไร/เดือน",
        "btn_save_rec": "💾 บันทึกสูตรส่วนตัว",
        "hist_header": "📜 รายการสูตรของคุณ",
        "btn_del": "🗑️ ลบ",
        "stock_header": "🌾 จัดการคลังวัตถุดิบ",
        "btn_update_stock": "🔄 อัปเดตข้อมูลคลัง",
        "feed_header": "ส่งข้อความถึงระบบ",
        "rating_label": "⭐️ คะแนนความพึงพอใจ (1-5)",
        "btn_feed_send": "ส่งข้อมูล",
        "admin_user_tab": "👥 รายชื่อผู้ใช้",
        "admin_feed_tab": "📩 ข้อความติชม",
        "admin_del_msg": "ลบข้อความนี้",
        "admin_save_user_btn": "💾 บันทึกการเปลี่ยนแปลงรายชื่อผู้ใช้",
        "admin_info_del": "💡 วิธีการลบผู้ใช้: คลิกเลือกแถวที่ต้องการแล้วกด Delete",
        "msg_success": "✅ ดำเนินการสำเร็จ",
        "msg_error": "❌ ข้อมูลไม่ถูกต้อง หรือเกิดข้อผิดพลาด",
        "msg_email_not_found": "❌ ไม่พบอีเมลนี้ในระบบ กรุณาตรวจสอบอีกครั้ง",
        "msg_no_balance": "❌ ไม่พบจุดสมดุลที่เหมาะสม",
        "new_un_label": "ชื่อผู้ใช้ใหม่",
        "btn_update_un": "อัปเดตชื่อผู้ใช้"
    },
    "EN": {
        "title": "🥚 Smart Layer AI Professional v4.2",
        "login_header": "🔐 Login",
        "reg_header": "📝 Registration",
        "forgot_header": "❓ Forgot Password",
        "reset_header": "🔄 Reset Password",
        "user_label": "Username",
        "pass_label": "Password",
        "fn_label": "Full Name",
        "em_label": "Email",
        "bd_label": "Birthdate",
        "cp_label": "Confirm Password",
        "btn_login": "Login",
        "btn_reg": "Register New Account",
        "btn_forgot": "Forgot Password%s",
        "btn_reg_submit": "Submit Registration",
        "btn_back": "Back",
        "btn_check": "Check Email",
        "btn_save": "Save",
        "nav_home": "Home",
        "nav_admin": "Admin Panel",
        "nav_logout": "Logout",
        "tab_calc": "🧮 Calculator",
        "tab_hist": "📜 My Recipes",
        "tab_stock": "🌾 Stock",
        "tab_feed": "💬 Feedback",
        "tab_profile": "👤 Profile",
        "config_sec": "⚙️ Configuration",
        "group_label": "Layer Group",
        "breed_label": "Breed",
        "stage_label": "Laying Stage",
        "count_label": "Bird Count",
        "batch_label": "Batch Size (kg)",
        "opt_label": "Optimization Goal:",
        "mode_price": "💰 Best Price",
        "mode_nutri": "✨ Best Nutrition",
        "income_sec": "💰 Revenue Forecast",
        "egg_price_label": "Exp. Price (THB/Egg)",
        "lay_rate_label": "Lay Rate (%)",
        "btn_ai": "🚀 Run AI Optimization",
        "res_header": "📊 Ingredient Results",
        "chart_title": "Mixing Ratio (%)",
        "protein_actual": "Actual Protein (%)",
        "energy_actual": "Actual Energy (kcal)",
        "target_label": "Target",
        "table_name": "Ingredient",
        "table_ratio": "Ratio (%)",
        "table_need": "Required (kg)",
        "profit_sec": "📈 Daily Profit Forecast",
        "cost_day": "Feed Cost/Day",
        "rev_day": "Revenue/Day",
        "profit_month": "Profit/Month",
        "btn_save_rec": "💾 Save My Recipe",
        "hist_header": "📜 Your Saved Recipes",
        "btn_del": "🗑️ Delete",
        "stock_header": "🌾 Stock Management",
        "btn_update_stock": "🔄 Update Stock",
        "feed_header": "Send Feedback",
        "rating_label": "Satisfaction Rating (1-5)",
        "btn_feed_send": "Submit",
        "admin_user_tab": "👥 Users",
        "admin_feed_tab": "📩 Feedbacks",
        "admin_del_msg": "Delete Message",
        "admin_save_user_btn": "💾 Save User Changes",
        "admin_info_del": "💡 To delete: select row and press Delete key",
        "msg_success": "✅ Success",
        "msg_error": "❌ Invalid data or error occurred",
        "msg_email_not_found": "❌ Email not found in our system.",
        "msg_no_balance": "❌ Balanced formulation not found",
        "new_un_label": "New Username",
        "btn_update_un": "Update Username"
    }
}

# --- 2. MASTER DATA ---
STANDARD_INGREDIENTS = [
    ("ข้าวโพดบด", "Ground Corn", 8.5, 3350, 2.2, 0.02, 0.28, 0.24, 0.18, 12.5),
    ("ปลายข้าว", "Broken Rice", 8.0, 3400, 1.0, 0.03, 0.08, 0.23, 0.15, 14.0),
    ("รำละเอียด", "Rice Bran", 12.5, 2450, 12.0, 0.12, 1.35, 0.60, 0.22, 10.0),
    ("มันสำปะหลังเส้น", "Cassava Chips", 2.5, 3100, 3.5, 0.18, 0.09, 0.07, 0.03, 8.5),
    ("น้ำมันปาล์ม/ไขมัน", "Vegetable Oil", 0.0, 8800, 0.0, 0.0, 0.0, 0.0, 0.0, 35.0),
    ("กากถั่วเหลือง (48%)", "Soybean Meal 48%", 48.0, 2450, 3.5, 0.27, 0.62, 3.10, 0.65, 23.0),
    ("ปลาป่น (60%)", "Fish Meal 60%", 60.0, 2800, 1.0, 5.00, 3.00, 4.50, 1.70, 38.0),
    ("เปลือกหอยบด/แคลเซียม", "Limestone", 0.0, 0, 0.0, 38.0, 0.0, 0.0, 0.0, 5.0),
    ("ดีแคลเซียมฟอสเฟต (DCP)", "DCP", 0.0, 0, 0.0, 21.0, 18.0, 0.0, 0.0, 28.0),
    ("พรีมิกซ์ไก่ไข่", "Layer Premix", 2.0, 500, 0.0, 12.0, 4.0, 1.0, 0.5, 150.0),
    ("ใบกระถินป่น", "Leucaena Meal", 22.0, 1200, 12.0, 1.5, 0.2, 0.0, 0.0, 7.0),
    ("เกลือ", "Salt", 0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 5.0),
    ("ดีแอล-เมทไธโอนีน", "DL-Methionine", 99.0, 0, 0.0, 0.0, 0.0, 0.0, 99.0, 180.0),
    ("แอล-ไลซีน", "L-Lysine", 78.0, 0, 0.0, 0.0, 0.0, 78.0, 0.0, 95.0)
]

ANIMAL_MASTER = {
    "TH": {
        "Commercial Brown Layers (ไก่ไข่สีน้ำตาล)": {
            "breeds": ["อิซ่า บราวน์ (Isa Brown)", "ไฮ-ไลน์ บราวน์ (Hy-Line Brown)", "โลมัน บราวน์ (Lohmann Brown)", "โนโวเจน บราวน์ (Novogen Brown)", "ซีพี บราวน์ (CP Brown)", "บาวานส์ บราวน์ (Bovans Brown)"],
            "stages": {
                "ระยะเริ่มแรก (Starter 0-6 wk)": {"vals": [20.0, 2900, 4.0]},
                "ระยะไก่รุ่น (Grower 6-18 wk)": {"vals": [16.0, 2750, 5.0]},
                "ระยะให้ไข่สูงสุด (Peak Production)": {"vals": [17.5, 2850, 3.5]},
                "ระยะให้ไข่ช่วงท้าย (Late Laying)": {"vals": [16.5, 2750, 4.0]}
            }
        },
        "Commercial White Layers (ไก่ไข่สีขาว)": {
            "breeds": ["ไฮ-ไลน์ W-36 (Hy-Line White)", "โลมัน แอลเอสแอล (Lohmann LSL)", "ดีคัลบ์ ไวท์ (Dekalb White)", "บาวานส์ ไวท์ (Bovans White)"],
            "stages": {
                "ระยะเริ่มแรก (Starter 0-6 wk)": {"vals": [21.0, 2950, 3.5]},
                "ระยะให้ไข่สูงสุด (Peak Production)": {"vals": [18.5, 2900, 3.0]},
                "ระยะให้ไข่ช่วงท้าย (Late Laying)": {"vals": [17.0, 2800, 3.5]}
            }
        },
        "Heritage & Specialty (สายพันธุ์มรดก/พื้นเมือง)": {
            "breeds": ["โร้ดไอแลนด์เรด (Rhode Island Red)", "บาร์ พลีมัธร็อค (Barred Rock)", "ออสตราลอป (Australorp)", "อาราอูคาน่า (Araucana - ไข่สีฟ้า)", "มารันส์ (Marans - ไข่สีช็อกโกแลต)"],
            "stages": {
                "ระยะเจริญเติบโต (Grower Period)": {"vals": [15.5, 2700, 6.0]},
                "ระยะให้ไข่ (Laying Period)": {"vals": [16.5, 2750, 5.0]}
            }
        }
    },
    "EN": {
        "Commercial Brown Layers": {
            "breeds": ["Isa Brown", "Hy-Line Brown", "Lohmann Brown", "Novogen Brown", "CP Brown", "Bovans Brown"],
            "stages": {
                "Starter (0-6 wk)": {"vals": [20.0, 2900, 4.0]},
                "Grower (6-18 wk)": {"vals": [16.0, 2750, 5.0]},
                "Peak Production": {"vals": [17.5, 2850, 3.5]},
                "Late Laying": {"vals": [16.5, 2750, 4.0]}
            }
        },
        "Commercial White Layers": {
            "breeds": ["Hy-Line W-36", "Lohmann LSL", "Dekalb White", "Bovans White"],
            "stages": {
                "Starter (0-6 wk)": {"vals": [21.0, 2950, 3.5]},
                "Peak Production": {"vals": [18.5, 2900, 3.0]},
                "Late Laying": {"vals": [17.0, 2800, 3.5]}
            }
        },
        "Heritage & Specialty Breeds": {
            "breeds": ["Rhode Island Red", "Barred Plymouth Rock", "Australorp", "Araucana (Blue Egg)", "Marans (Dark Egg)"],
            "stages": {
                "Grower Period": {"vals": [15.5, 2700, 6.0]},
                "Laying Period": {"vals": [16.5, 2750, 5.0]}
            }
        }
    }
}

# --- 3. DATABASE LOGIC ---
def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()

def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, fullname TEXT, email TEXT UNIQUE, password TEXT, birthdate TEXT, age INTEGER)")
        
        # สร้างตาราง suggestions และทำ Migration ถ้าจำเป็น
        c.execute("""CREATE TABLE IF NOT EXISTS suggestions 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      username TEXT, 
                      message TEXT, 
                      rating INTEGER, 
                      timestamp DATETIME)""")
        
        # ตรวจสอบว่าคอลัมน์ rating มีหรือยัง
        c.execute("PRAGMA table_info(suggestions)")
        columns = [column[1] for column in c.fetchall()]
        if 'rating' not in columns:
            c.execute("ALTER TABLE suggestions ADD COLUMN rating INTEGER DEFAULT 5")

        c.execute("CREATE TABLE IF NOT EXISTS ingredients (name_th TEXT, name_en TEXT, protein REAL, energy REAL, fiber REAL, calcium REAL, phosphorus REAL, lysine REAL, methionine REAL, cost REAL)")
        c.execute("""CREATE TABLE IF NOT EXISTS saved_recipes 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      username TEXT, 
                      breed_name TEXT, 
                      stage_name TEXT, 
                      chicken_count INTEGER, 
                      details TEXT, 
                      cost_per_kg REAL, 
                      date TEXT)""")
        
        if not c.execute("SELECT * FROM users WHERE username='ang'").fetchone():
            c.execute("INSERT INTO users VALUES (%s,%s,%s,%s,%s,%s)", ('ang', 'Admin System', 'admin@test.com', make_hashes('222'), '1995-01-01', 30))
        
        if c.execute("SELECT COUNT(*) FROM ingredients").fetchone()[0] == 0:
            c.executemany("INSERT INTO ingredients VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", STANDARD_INGREDIENTS)
        conn.commit()

init_db()

# --- 4. STYLE FIX TEXT + BUTTON UI ---
import streamlit as st

st.markdown("""
<style>

/* APP BACKGROUND */
.stApp{
    background: linear-gradient(135deg,#f5f7fa 0%,#c3cfe2 100%);
}

/* HEADERS */
h1,h2,h3,h4,h5,h6{
    color:#000000 !important;
}

/* LABEL TEXT */
label{
    color:#000000 !important;
    font-weight:600;
}

/* NORMAL TEXT */
p,span,div{
    color:#000000 !important;
}

/* INPUT TEXT */
input,textarea{
    color:#000000 !important;
}

/* INPUT BOX */
.stTextInput input{
    background:white !important;
    color:black !important;
    border-radius:8px;
}

/* PASSWORD BOX */
.stTextInput div[data-baseweb="input"]{
    background:white !important;
}

/* SELECT BOX */
.stSelectbox div{
    color:black !important;
}

/* ===== BUTTON STYLE FIX ===== */

/* LOGIN BUTTON */
.stButton button{
    background-color:#2e59d9;
    color:white;
    width:100%;
    border-radius:10px;
    font-weight:bold;
    padding:10px;
}

/* SECONDARY BUTTON */
.stButton button:hover{
    background-color:#1f3ea3;
    color:white;
}

/* LIGHT BUTTON (สมัครสมาชิก) */
button[kind="secondary"]{
    background:#e9ecef !important;
    color:black !important;
}

/* EXPANDER CARD */
div[data-testid="stExpander"]{
    background:white;
    border-radius:12px;
    padding:10px;
}

/* TABLE */
.stTable{
    background:white;
}

</style>
""", unsafe_allow_html=True)

# --- 5. AUTHENTICATION PAGES ---
def auth_page(T):
    if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'
    
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        msg_area = st.empty()

        if st.session_state.auth_mode == 'login':
            st.title(T["login_header"])
            u_input = st.text_input(f"{T['user_label']} / {T['em_label']}")
            p = st.text_input(T["pass_label"], type='password')
            if st.button(T["btn_login"], use_container_width=True, type="primary"):
                with get_conn() as conn:
                    res = conn.execute("SELECT fullname, username FROM users WHERE (username=%s OR email=%s) AND password=%s", (u_input, u_input, make_hashes(p))).fetchone()
                    if res:
                        st.session_state.logged_in, st.session_state.fullname, st.session_state.username = True, res[0], res[1]
                        st.rerun()
                    else: msg_area.error(T["msg_error"])
            
            st.button(T["btn_reg"], on_click=lambda: st.session_state.update({"auth_mode": "register"}), use_container_width=True)
            st.button(T["btn_forgot"], on_click=lambda: st.session_state.update({"auth_mode": "forgot"}), use_container_width=True)
        
        elif st.session_state.auth_mode == 'register':
            st.title(T["reg_header"])
            fn = st.text_input(T["fn_label"])
            em = st.text_input(T["em_label"])
            un = st.text_input(T["user_label"])
            pw = st.text_input(T["pass_label"], type="password")
            cpw = st.text_input(T["cp_label"], type="password")
            
            if st.button(T["btn_reg_submit"], type="primary", use_container_width=True):
                if pw == cpw and un and em:
                    with get_conn() as conn:
                        try:
                            conn.execute("INSERT INTO users VALUES (%s,%s,%s,%s,%s,%s)", (un, fn, em, make_hashes(pw), "2000-01-01", 24))
                            conn.commit()
                            msg_area.success(T["msg_success"])
                            st.session_state.auth_mode = 'login'
                            time.sleep(0.8)
                            st.rerun()
                        except psycopg2.IntegrityError:
                            msg_area.error("❌ ชื่อผู้ใช้หรืออีเมลนี้ถูกใช้งานไปแล้ว")
                        except Exception as e:
                            msg_area.error(f"{T['msg_error']}: {e}")
                else:
                    msg_area.warning("❌ กรุณากรอกข้อมูลให้ครบและรหัสผ่านต้องตรงกัน")
            st.button(T["btn_back"], on_click=lambda: st.session_state.update({"auth_mode": "login"}), use_container_width=True)

        elif st.session_state.auth_mode == 'forgot':
            st.title(T["forgot_header"])
            f_em = st.text_input(T["em_label"], placeholder="example@email.com")
            if st.button(T["btn_check"], type="primary", use_container_width=True):
                if f_em:
                    with get_conn() as conn:
                        u_data = conn.execute("SELECT username FROM users WHERE email=%s", (f_em,)).fetchone()
                        if u_data:
                            st.session_state.reset_target = u_data[0]
                            st.session_state.auth_mode = 'reset_confirm'
                            st.rerun()
                        else:
                            msg_area.error(T["msg_email_not_found"])
            st.button(T["btn_back"], on_click=lambda: st.session_state.update({"auth_mode": "login"}), use_container_width=True)

        elif st.session_state.auth_mode == 'reset_confirm':
            st.title(T["reset_header"])
            st.info(f"Target: {st.session_state.reset_target}")
            n_pw = st.text_input(T["pass_label"], type="password")
            if st.button(T["btn_save"], type="primary", use_container_width=True):
                with get_conn() as conn:
                    conn.execute("UPDATE users SET password=%s WHERE username=%s", (make_hashes(n_pw), st.session_state.reset_target))
                msg_area.success(T["msg_success"])
                time.sleep(1)
                st.session_state.auth_mode = 'login'
                st.rerun()

# --- 6. USER DASHBOARD ---
def user_page(T, L_CODE):
    st.title(T["title"])
    tabs = st.tabs([T["tab_calc"], T["tab_hist"], T["tab_stock"], T["tab_feed"], T["tab_profile"]])

    with tabs[0]:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader(T["config_sec"])
            cur_master = ANIMAL_MASTER[L_CODE]
            g_key = st.selectbox(T["group_label"], list(cur_master.keys()))
            b_key = st.selectbox(T["breed_label"], cur_master[g_key]['breeds'])
            s_key = st.selectbox(T["stage_label"], list(cur_master[g_key]['stages'].keys()))
            num = st.number_input(T["count_label"], 1, 1000000, 100)
            batch = st.number_input(T["batch_label"], 1, 5000, 100)
            opt_mode = st.radio(T["opt_label"], [T["mode_price"], T["mode_nutri"]])
            
            st.divider()
            st.subheader(T["income_sec"])
            egg_p = st.number_input(T["egg_price_label"], 1.0, 10.0, 4.3)
            lay_r = st.slider(T["lay_rate_label"], 50, 100, 85)
            
            target = cur_master[g_key]['stages'][s_key]['vals']
            
            if st.button(T["btn_ai"], use_container_width=True, type="primary"):
                df = pd.read_sql("SELECT * FROM ingredients", get_conn())
                costs = df["cost"].tolist()
                A = [[-p for p in df["protein"]], [-e for e in df["energy"]], [f for f in df["fiber"]]]
                b_ub = [-target[0], -target[1], target[2]]
                
                res = linprog(costs if T["mode_price"] in opt_mode else [c*1.2 for c in costs], 
                              A_ub=A, b_ub=b_ub, A_eq=[[1.0]*len(df)], b_eq=[1.0], method="highs")
                
                if res.success:
                    st.session_state.calc = {"x": res.x, "df": df, "cost": res.fun, "b": b_key, "s": s_key, "n": num, "batch": batch, "target": target, "egg_p": egg_p, "lay_r": lay_r}
                    st.balloons()
                else: st.error(T["msg_no_balance"])

        with c2:
            if "calc" in st.session_state:
                r = st.session_state.calc
                st.subheader(T["res_header"])
                res_df = r['df'].copy()
                res_df["Ratio (%)"] = (r['x'] * 100).round(2)
                res_df = res_df[res_df["Ratio (%)"] > 0]
                name_col = "name_th" if L_CODE == "TH" else "name_en"
                
                st.plotly_chart(px.pie(res_df, values='Ratio (%)', names=name_col, title=T["chart_title"], hole=0.4), use_container_width=True)
                
                m1, m2 = st.columns(2)
                m1.metric(T["protein_actual"], f"{(r['df']['protein']*r['x']).sum():.2f}%", f"Target {r['target'][0]}%")
                m2.metric(T["energy_actual"], f"{(r['df']['energy']*r['x']).sum():.0f}", f"Target {r['target'][1]}")

                table_disp = res_df[[name_col, "Ratio (%)"]].copy()
                table_disp[T["table_need"]] = (res_df["Ratio (%)"] / 100 * r['batch']).round(3)
                table_disp.columns = [T["table_name"], T["table_ratio"], T["table_need"]]
                st.table(table_disp)
                
                st.divider()
                st.subheader(T["profit_sec"])
                daily_feed = (r['n'] * 120) / 1000 
                d_cost = daily_feed * r['cost']
                d_rev = (r['n'] * r['lay_r']/100) * r['egg_p']
                p1, p2, p3 = st.columns(3)
                p1.metric(T["cost_day"], f"{d_cost:,.2f} ฿")
                p2.metric(T["rev_day"], f"{d_rev:,.2f} ฿")
                p3.metric(T["profit_month"], f"{(d_rev-d_cost)*30:,.2f} ฿")

                if st.button(T["btn_save_rec"]):
                    details = ", ".join([f"{row[T['table_name']]} {row[T['table_need']]}kg" for _, row in table_disp.iterrows()])
                    with get_conn() as conn:
                        conn.execute("""INSERT INTO saved_recipes 
                                        (username, breed_name, stage_name, chicken_count, details, cost_per_kg, date) 
                                        VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                                     (st.session_state.username, r['b'], r['s'], r['n'], details, round(r['cost'], 2), datetime.now().strftime("%Y-%m-%d %H:%M")))
                    st.success(T["msg_success"])

    with tabs[1]:
        st.subheader(T["hist_header"])
        h_df = pd.read_sql("SELECT * FROM saved_recipes WHERE username=%s ORDER BY date DESC", 
                           get_conn(), params=(st.session_state.username,))
        for _, row in h_df.iterrows():
            with st.expander(f"📅 {row['date']} | {row['breed_name']} | {row['cost_per_kg']} ฿/kg"):
                st.write(row['details'])
                if st.button(T["btn_del"], key=f"del_h_{row['id']}"):
                    with get_conn() as conn: 
                        conn.execute("DELETE FROM saved_recipes WHERE id=%s AND username=%s", (row['id'], st.session_state.username))
                    st.rerun()

    with tabs[2]:
        st.subheader(T["stock_header"])
        ing_data = pd.read_sql("SELECT * FROM ingredients", get_conn())
        edited = st.data_editor(ing_data, num_rows="dynamic", use_container_width=True)
        if st.button(T["btn_update_stock"]):
            with get_conn() as conn:
                conn.execute("DELETE FROM ingredients")
                edited.to_sql("ingredients", conn, index=False)
            st.success(T["msg_success"])

    with tabs[3]:
        st.subheader(T["tab_feed"])
        with st.form("feedback_form"):
            rating = st.select_slider(T["rating_label"], options=[1, 2, 3, 4, 5], value=5)
            msg = st.text_area(T["feed_header"])
            if st.form_submit_button(T["btn_feed_send"]):
                if msg:
                    with get_conn() as conn:
                        conn.execute("INSERT INTO suggestions (username, message, rating, timestamp) VALUES (%s,%s,%s,%s)", 
                                     (st.session_state.username, msg, int(rating), datetime.now()))
                    st.success(T["msg_success"])
                else:
                    st.warning("กรุณากรอกข้อความ")

    with tabs[4]:
        st.subheader(T["tab_profile"])
        with get_conn() as conn:
            u_info = conn.execute("SELECT email FROM users WHERE username=%s", (st.session_state.username,)).fetchone()
            st.info(f"📧 {T['em_label']}: {u_info[0]}")
            
            new_un = st.text_input(T["new_un_label"], value=st.session_state.username)
            if st.button(T["btn_update_un"]):
                if new_un != st.session_state.username and new_un != "":
                    try:
                        conn.execute("UPDATE users SET username=%s WHERE username=%s", (new_un, st.session_state.username))
                        conn.execute("UPDATE suggestions SET username=%s WHERE username=%s", (new_un, st.session_state.username))
                        conn.execute("UPDATE saved_recipes SET username=%s WHERE username=%s", (new_un, st.session_state.username))
                        conn.commit()
                        st.session_state.username = new_un
                        st.success(T["msg_success"])
                        st.rerun()
                    except: st.error(T["msg_error"])

# --- 7. ADMIN PANEL ---
def admin_page(T):
    st.title(T["nav_admin"])
    t1, t2 = st.tabs([T["admin_user_tab"], T["admin_feed_tab"]])
    
    with t1:
        st.subheader(T["admin_user_tab"])
        st.info(T["admin_info_del"])
        with get_conn() as conn:
            u_df = pd.read_sql("SELECT username, fullname, email, age FROM users", conn)
            edited_u = st.data_editor(u_df, num_rows="dynamic", use_container_width=True, key="admin_u_edit")
            if st.button(T["admin_save_user_btn"]):
                old_u = u_df['username'].tolist()
                new_u = edited_u['username'].tolist()
                deleted = [u for u in old_u if u not in new_u]
                for d_un in deleted:
                    conn.execute("DELETE FROM users WHERE username=%s", (d_un,))
                    conn.execute("DELETE FROM saved_recipes WHERE username=%s", (d_un,))
                conn.commit()
                st.success(T["msg_success"])
                st.rerun()
    
    with t2:
        st.subheader(T["admin_feed_tab"])
        with get_conn() as conn:
            s_df = pd.read_sql("SELECT * FROM suggestions ORDER BY timestamp DESC", conn)
            
            if not s_df.empty:
                # จัดการค่าว่างและคำนวณคะแนนเฉลี่ย
                s_df['rating'] = s_df['rating'].fillna(0).astype(int)
                avg_rating = s_df['rating'].mean()
                
                c1, c2 = st.columns([1, 2])
                c1.metric("คะแนนเฉลี่ยรวม", f"⭐️ {avg_rating:.2f} / 5.0")
                
                # แสดงกราฟวงกลมสรุปคะแนน (แก้จุดสีที่ Error)
                fig = px.pie(s_df, 
                             names='rating', 
                             title="สัดส่วนคะแนนความพึงพอใจ (%)", 
                             color_discrete_sequence=px.colors.sequential.YlOrBr)
                c2.plotly_chart(fig, use_container_width=True)

                st.divider()
                
                for _, r in s_df.iterrows():
                    star_display = "⭐️" * r['rating']
                    with st.expander(f"{star_display} | {r['username']} | {r['timestamp']}"):
                        st.write(f"**ข้อความ:** {r['message']}")
                        if st.button(T["admin_del_msg"], key=f"del_msg_{r['id']}"):
                            conn.execute("DELETE FROM suggestions WHERE id=%s", (r['id'],))
                            conn.commit()
                            st.rerun()
            else:
                st.info("ยังไม่มีข้อมูลการติชมเข้ามา")

# --- 8. MAIN NAVIGATION ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

st.sidebar.markdown("### 🌐 Language / ภาษา")
lang_choice = st.sidebar.selectbox("Language", ["ไทย", "English"], label_visibility="collapsed")
L_CODE = "TH" if lang_choice == "ไทย" else "EN"
T = LANG[L_CODE]

if not st.session_state.logged_in:
    auth_page(T)
else:
    st.sidebar.title(f"👤 {st.session_state.fullname}")
    nav_opts = [T["nav_home"]]
    if st.session_state.username == 'ang': nav_opts.append(T["nav_admin"])
    
    choice = st.sidebar.radio("MENU", nav_opts, label_visibility="collapsed")
    
    if st.sidebar.button(T["nav_logout"], use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    
    if choice == T["nav_home"]: user_page(T, L_CODE)
    elif choice == T["nav_admin"]: admin_page(T)
