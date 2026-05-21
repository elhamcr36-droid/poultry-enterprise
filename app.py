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

# ---------------- DATABASE CONNECTION ---------------- #

DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn():
    return psycopg2.connect(
        DATABASE_URL,
        sslmode="require"
    )

# ---------------- CONFIG ---------------- #

st.markdown("""
<style>

/* Sidebar background */
section[data-testid="stSidebar"]{
    background-color:#0f172a !important;
}

/* ข้อความทั้งหมดใน sidebar */
section[data-testid="stSidebar"] *{
    color:white !important;
}

/* ปุ่ม logout */
section[data-testid="stSidebar"] div.stButton > button{
    background-color:#ef4444 !important;
    color:white !important;
    border:none !important;
    border-radius:8px !important;
    width:100% !important;
}

/* hover */
section[data-testid="stSidebar"] div.stButton > button:hover{
    background-color:#dc2626 !important;
    color:white !important;
}

</style>
""", unsafe_allow_html=True)
# ---------------- DATABASE ---------------- #

def init_db():

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        username TEXT PRIMARY KEY,
        fullname TEXT,
        email TEXT,
        password TEXT,
        birthdate TEXT,
        age INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS suggestions(
        id SERIAL PRIMARY KEY,
        username TEXT,
        message TEXT,
        rating INTEGER,
        timestamp TIMESTAMP
    )
    """)

    conn.commit()
    cur.close()
    conn.close()


# ---------------- PASSWORD ---------------- #

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ---------------- USER FUNCTIONS ---------------- #

def register_user(username, fullname, email, password, birthdate, age):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO users (username,fullname,email,password,birthdate,age)
        VALUES (%s,%s,%s,%s,%s,%s)
        """,
        (username, fullname, email, hash_password(password), birthdate, age)
    )

    conn.commit()
    cur.close()
    conn.close()


def login_user(username, password):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM users WHERE username=%s AND password=%s",
        (username, hash_password(password))
    )

    user = cur.fetchone()

    cur.close()
    conn.close()

    return user


# ---------------- FEED OPTIMIZATION ---------------- #

def optimize_feed(costs, protein, min_protein):

    c = costs
    A = [[-p for p in protein]]
    b = [-min_protein]

    bounds = [(0, None) for _ in costs]

    result = linprog(c, A_ub=A, b_ub=b, bounds=bounds)

    return result.x


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
        "btn_forgot": "ลืมรหัสผ่าน",
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
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # 1. สร้างตาราง users ก่อนเป็นอันดับแรกสุด!
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        fullname TEXT,
        email TEXT,
        password TEXT,
        birthdate TEXT,
        age INTEGER
    )
    """)

    # 2. สร้างตาราง suggestions
    cur.execute("""
    CREATE TABLE IF NOT EXISTS suggestions (
        id SERIAL PRIMARY KEY,
        username TEXT,
        message TEXT,
        rating INTEGER,
        timestamp TIMESTAMP
    )
    """)

    # ตรวจสอบโครงสร้างตาราง suggestions เผื่อสำหรับคอลัมน์ rating
    cur.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name='suggestions'
    """)
    columns = [column[0] for column in cur.fetchall()]
    if 'rating' not in columns:
        cur.execute("ALTER TABLE suggestions ADD COLUMN rating INTEGER DEFAULT 5")

    # 3. สร้างตาราง ingredients
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ingredients (
        name_th TEXT,
        name_en TEXT,
        protein REAL,
        energy REAL,
        fiber REAL,
        calcium REAL,
        phosphorus REAL,
        lysine REAL,
        methionine REAL,
        cost REAL
    )
    """)

    # 4. สร้างตาราง saved_recipes
    cur.execute("""
    CREATE TABLE IF NOT EXISTS saved_recipes (
        id SERIAL PRIMARY KEY,
        username TEXT,
        breed_name TEXT,
        stage_name TEXT,
        chicken_count INTEGER,
        details TEXT,
        cost_per_kg REAL,
        date TEXT
    )
    """)

    # ตรวจสอบและเพิ่มบัญชีแอดมินเริ่มต้น (ทำงานได้แล้วเพราะตาราง users ถูกสร้างด้านบนแล้ว)
    cur.execute("SELECT * FROM users WHERE username='ang'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users VALUES (%s,%s,%s,%s,%s,%s)",
            (
                'ang',
                'Admin System',
                'admin@test.com',
                make_hashes('222'),
                '1995-01-01',
                30
            )
        )

    # ตรวจสอบและเพิ่มข้อมูลวัตถุดิบมาตรฐานเริ่มต้น
    cur.execute("SELECT COUNT(*) FROM ingredients")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO ingredients VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            STANDARD_INGREDIENTS
        )

    conn.commit()
    cur.close()
    conn.close()

# เรียกใช้งานฟังก์ชันสร้างฐานข้อมูล
init_db()

# --- 4. STYLE ---
st.markdown("""
<style>

.stApp {
    background: linear-gradient(135deg,#eef2f7 0%,#d7e1ec 100%);
}

/* ทำให้ข้อความเข้ม */
h1, h2, h3, h4, h5, h6 {
    color:#1f2937 !important;
    font-weight:700;
}

p, label, span {
    color:#1f2937 !important;
}

/* กล่อง input */
input {
    background-color:white !important;
    color:black !important;
}

/* ปุ่มทั้งหมด */
div.stButton > button {
    border-radius:10px;
    font-weight:bold;
}

/* ปุ่มหลัก Login */
button[kind="primary"] {
    background-color:#2e59d9 !important;
    color:white !important;
}

/* ปุ่มรอง (สมัครสมาชิก / ลืมรหัสผ่าน) */
div.stButton > button:not([kind="primary"]) {
    background-color:white !important;
    color:#1f2937 !important;
    border:1px solid #cbd5e1 !important;
}

/* hover effect */
div.stButton > button:not([kind="primary"]):hover {
    background-color:#f1f5f9 !important;
}

/* กล่อง UI */
.stTable, div[data-testid="stExpander"] {
    background-color:white;
    border-radius:15px;
    box-shadow:0 4px 12px rgba(0,0,0,0.08);
}

</style>
""", unsafe_allow_html=True)
# --- 5. AUTHENTICATION PAGES ---
def auth_page(T):

    if 'auth_mode' not in st.session_state:
        st.session_state.auth_mode = "login"

    col1, col2, col3 = st.columns([1,1.6,1])

    with col2:

        msg_area = st.empty()

        # ---------------- LOGIN ----------------
        if st.session_state.auth_mode == "login":

            st.markdown("## 🔐 เข้าสู่ระบบ")

            u_input = st.text_input(f"{T['user_label']} / {T['em_label']}")
            p = st.text_input(T["pass_label"], type="password")

            if st.button(T["btn_login"], use_container_width=True, type="primary"):

                if not u_input or not p:
                    msg_area.warning("กรุณากรอกข้อมูลให้ครบ")
                else:

                    conn = get_conn()
                    cur = conn.cursor()

                    cur.execute(
                        """
                        SELECT fullname, username
                        FROM users
                        WHERE (username=%s OR email=%s) AND password=%s
                        """,
                        (u_input, u_input, make_hashes(p))
                    )

                    res = cur.fetchone()
                    conn.close()

                    if res:

                        st.session_state.logged_in = True
                        st.session_state.fullname = res[0]
                        st.session_state.username = res[1]

                        st.rerun()

                    else:
                        msg_area.error(T["msg_error"])

            st.button(
                T["btn_reg"],
                on_click=lambda: st.session_state.update({"auth_mode":"register"}),
                use_container_width=True
            )

            st.button(
                T["btn_forgot"],
                on_click=lambda: st.session_state.update({"auth_mode":"forgot"}),
                use_container_width=True
            )


        # ---------------- REGISTER ----------------
        elif st.session_state.auth_mode == "register":

            st.markdown("## 📝 สมัครสมาชิก")

            fn = st.text_input(T["fn_label"])
            em = st.text_input(T["em_label"])
            un = st.text_input(T["user_label"])

            pw = st.text_input(T["pass_label"], type="password")
            cpw = st.text_input(T["cp_label"], type="password")

            if st.button(T["btn_reg_submit"], type="primary", use_container_width=True):

                if not fn or not em or not un or not pw:

                    msg_area.warning("กรุณากรอกข้อมูลให้ครบ")

                elif pw != cpw:

                    msg_area.error("รหัสผ่านไม่ตรงกัน")

                else:

                    conn = get_conn()
                    cur = conn.cursor()

                    try:

                        cur.execute(
                            """
                            INSERT INTO users
                            (username, fullname, email, password, birthdate, age)
                            VALUES (%s,%s,%s,%s,%s,%s)
                            """,
                            (un, fn, em, make_hashes(pw), "2000-01-01", 24)
                        )

                        conn.commit()
                        conn.close()

                        msg_area.success(T["msg_success"])

                        st.session_state.auth_mode = "login"

                        time.sleep(0.8)
                        st.rerun()

                    except Exception as e:

                        conn.close()
                        msg_area.error(f"{T['msg_error']}: {e}")

            st.button(
                T["btn_back"],
                on_click=lambda: st.session_state.update({"auth_mode":"login"}),
                use_container_width=True
            )


        # ---------------- FORGOT PASSWORD ----------------
        elif st.session_state.auth_mode == "forgot":

            st.markdown("## 🔎 ลืมรหัสผ่าน")

            f_em = st.text_input(T["em_label"], placeholder="example@email.com")

            if st.button(T["btn_check"], type="primary", use_container_width=True):

                if not f_em:

                    msg_area.warning("กรุณากรอกอีเมล")

                else:

                    conn = get_conn()
                    cur = conn.cursor()

                    cur.execute(
                        "SELECT username FROM users WHERE email=%s",
                        (f_em,)
                    )

                    u_data = cur.fetchone()
                    conn.close()

                    if u_data:

                        st.session_state.reset_target = u_data[0]
                        st.session_state.auth_mode = "reset_confirm"

                        st.rerun()

                    else:

                        msg_area.error(T["msg_email_not_found"])

            st.button(
                T["btn_back"],
                on_click=lambda: st.session_state.update({"auth_mode":"login"}),
                use_container_width=True
            )


        # ---------------- RESET PASSWORD ----------------
        elif st.session_state.auth_mode == "reset_confirm":

            st.markdown("## 🔑 ตั้งรหัสผ่านใหม่")

            st.info(f"User: {st.session_state.reset_target}")

            n_pw = st.text_input(T["pass_label"], type="password")

            if st.button(T["btn_save"], type="primary", use_container_width=True):

                if not n_pw:

                    msg_area.warning("กรุณากรอกรหัสผ่านใหม่")

                else:

                    conn = get_conn()
                    cur = conn.cursor()

                    cur.execute(
                        """
                        UPDATE users
                        SET password=%s
                        WHERE username=%s
                        """,
                        (make_hashes(n_pw), st.session_state.reset_target)
                    )

                    conn.commit()
                    conn.close()

                    msg_area.success(T["msg_success"])

                    time.sleep(1)

                    st.session_state.auth_mode = "login"
                    st.rerun()
                    
# ==========================================
# 6. USER DASHBOARD
# ==========================================
def user_page(T, L_CODE):
    st.title(T["title"])

    tabs = st.tabs([
        T["tab_calc"],
        T["tab_hist"],
        T["tab_stock"],
        T["tab_feed"],
        T["tab_profile"]
    ])

    # ------------------ TAB 0: CALCULATOR (ระบบคำนวณ) ------------------
    with tabs[0]:
        c1, c2 = st.columns([1, 2])

        # -------- LEFT PANEL (แผงตั้งค่าด้านซ้าย) --------
        with c1:
            st.subheader(T["config_sec"])
            cur_master = ANIMAL_MASTER[L_CODE]

            g_key = st.selectbox(T["group_label"], list(cur_master.keys()))
            b_key = st.selectbox(T["breed_label"], cur_master[g_key]["breeds"])
            s_key = st.selectbox(T["stage_label"], list(cur_master[g_key]["stages"].keys()))

            num = st.number_input(T["count_label"], 1, 1000000, 100)
            batch = st.number_input(T["batch_label"], 1, 5000, 100)
            opt_mode = st.radio(T["opt_label"], [T["mode_price"], T["mode_nutri"]])

            st.divider()
            st.subheader(T["income_sec"])

            egg_p = st.number_input(T["egg_price_label"], 1.0, 10.0, 4.3)
            lay_r = st.slider(T["lay_rate_label"], 50, 100, 85)

            target = cur_master[g_key]["stages"][s_key]["vals"]

            if st.button(T["btn_ai"], use_container_width=True, type="primary"):
                conn = get_conn()
                df = pd.read_sql("SELECT * FROM ingredients", conn)
                conn.close()

                costs = df["cost"].tolist()
                A = [
                    [-p for p in df["protein"]],
                    [-e for e in df["energy"]],
                    [f for f in df["fiber"]]
                ]
                b_ub = [-target[0], -target[1], target[2]]

                res = linprog(
                    costs if opt_mode == T["mode_price"] else [c*1.2 for c in costs],
                    A_ub=A,
                    b_ub=b_ub,
                    A_eq=[[1.0]*len(df)],
                    b_eq=[1.0],
                    method="highs"
                )

                if res.success:
                    st.session_state.calc = {
                        "x": res.x,
                        "df": df,
                        "cost": res.fun,
                        "b": b_key,
                        "s": s_key,
                        "n": num,
                        "batch": batch,
                        "target": target,
                        "egg_p": egg_p,
                        "lay_r": lay_r
                    }
                    st.balloons()
                else:
                    st.error(T["msg_no_balance"])

        # -------- RIGHT PANEL (แผงแสดงผลด้านขวา) --------
        with c2:
            if "calc" in st.session_state and st.session_state.calc is not None:
                r = st.session_state.calc
                st.subheader(T["res_header"])
                st.info(f"สายพันธุ์: {r['b']} | ช่วงอายุ: {r['s']}")

                # เตรียมข้อมูลแสดงผลวัตถุดิบ
                res_df = r["df"].copy()
                res_df["Ratio (%)"] = (r["x"] * 100).round(2)
                res_df = res_df[res_df["Ratio (%)"] > 0]
                name_col = "name_th" if L_CODE == "TH" else "name_en"

                # แสดงแผนภูมิวงกลมสัดส่วนวัตถุดิบ
                st.plotly_chart(
                    px.pie(
                        res_df,
                        values="Ratio (%)",
                        names=name_col,
                        title=T["chart_title"],
                        hole=0.4
                    ),
                    use_container_width=True
                )

                # สรุปค่าสารอาหารเปรียบเทียบกับเป้าหมาย
                m1, m2 = st.columns(2)
                m1.metric(
                    T["protein_actual"],
                    f"{(r['df']['protein']*r['x']).sum():.2f}%",
                    f"Target {r['target'][0]}%"
                )
                m2.metric(
                    T["energy_actual"],
                    f"{(r['df']['energy']*r['x']).sum():.0f} kcal",
                    f"Target {r['target'][1]}"
                )

                # ตารางสรุปวัตถุดิบ น้ำหนัก และสัดส่วน
                table_disp = res_df[[name_col, "Ratio (%)"]].copy()
                table_disp[T["table_need"]] = (res_df["Ratio (%)"] / 100 * r["batch"]).round(3)
                table_disp.columns = [T["table_name"], T["table_ratio"], T["table_need"]]
                st.table(table_disp)

                st.divider()
                st.subheader(T["profit_sec"])

                # คำนวณต้นทุน-รายได้-กำไรเชิงเศรษฐศาสตร์
                daily_feed = (r["n"] * 120) / 1000
                d_cost = daily_feed * r["cost"]
                d_rev = (r["n"] * r["lay_r"] / 100) * r["egg_p"]

                p1, p2, p3 = st.columns(3)
                p1.metric(T["cost_day"], f"{d_cost:,.2f} ฿")
                p2.metric(T["rev_day"], f"{d_rev:,.2f} ฿")
                p3.metric(T["profit_month"], f"{(d_rev - d_cost) * 30:,.2f} ฿")

                st.write("") 
                
                # -------- ปุ่มบันทึกสูตรอาหาร --------
                if st.button("💾 บันทึกสูตรอาหารนี้ลงประวัติการคำนวณ", use_container_width=True, type="secondary"):
                    try:
                        items_summary = ", ".join([f"{row[T['table_name']]} ({row[T['table_ratio']]}%)" for _, row in table_disp.iterrows()])
                        conn = get_conn()
                        curr = conn.cursor()
                        curr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='saved_recipes'")
                        col_list = [col[0] for col in curr.fetchall()]
                        
                        c_user = "username" if "username" in col_list else col_list[1]
                        c_breed = "breed" if "breed" in col_list else ([c for c in col_list if "breed" in c or "type" in c] + [col_list[2]])[0]
                        c_stage = "stage" if "stage" in col_list else ([c for c in col_list if "stage" in c or "age" in c] + [col_list[3]])[0]
                        c_cost = "total_cost" if "total_cost" in col_list else ([c for c in col_list if "cost" in c or "price" in c] + [col_list[4]])[0]
                        c_det = "details" if "details" in col_list else col_list[5]
                        c_date = "date" if "date" in col_list else col_list[-1]

                        query = f"""
                            INSERT INTO saved_recipes ({c_user}, {c_breed}, {c_stage}, {c_cost}, {c_det}, {c_date})
                            VALUES (%s, %s, %s, %s, %s, NOW())
                        """
                        curr.execute(query, (st.session_state.username, str(r["b"]), str(r["s"]), float(r["cost"]), str(items_summary)))
                        conn.commit()
                        curr.close()
                        conn.close()
                        st.success("🎉 บันทึกสูตรอาหารเข้าสู่แท็บประวัติสำเร็จแล้ว!")
                    except Exception as e:
                        st.error(f"ไม่สามารถบันทึกได้เนื่องจากชื่อคอลัมน์ไม่ตรง: {e}")
            else:
                st.write("👉 กรุณากรอกข้อมูลและกดปุ่มคำนวณสูตรอาหารระบบ AI ด้านซ้ายมือเพื่อเริ่มคำนวณ")

    # ------------------ TAB 1: HIST (ประวัติการคำนวณ) ------------------
    with tabs[1]:
        st.subheader(T["tab_hist"])
        try:
            conn = get_conn()
            df = pd.read_sql("SELECT * FROM saved_recipes ORDER BY date DESC", conn)
            conn.close()

            if df.empty:
                st.info("ยังไม่มีสูตรที่บันทึกไว้สำหรับบัญชีของคุณ")
            else:
                st.dataframe(df, use_container_width=True)
        except Exception as e:
            try:
                conn = get_conn()
                df = pd.read_sql("SELECT * FROM saved_recipes", conn)
                conn.close()
                st.dataframe(df, use_container_width=True)
            except Exception as e2:
                st.error(f"ไม่สามารถดึงข้อมูลประวัติได้เนื่องจากโครงสร้างตารางหลังบ้าน: {e2}")

    # ------------------ TAB 2: STOCK (คลังวัตถุดิบ) ------------------
    with tabs[2]:
        st.subheader(T["tab_stock"])
        conn = get_conn()
        df = pd.read_sql("SELECT name_th, protein, energy, fiber, cost FROM ingredients", conn)
        conn.close()
        st.dataframe(df, use_container_width=True)

    # ------------------ TAB 3: FEEDBACK (แนะนำติชม & ติดต่อแอดมิน) ------------------
    with tabs[3]:
        st.subheader("💬 แนะนำติชม & ติดต่อแอดมิน")
        st.write("คะแนนความพึงพอใจและข้อเสนอแนะของคุณจะถูกส่งตรงไปให้ผู้พัฒนาเพื่อปรับปรุงระบบในเวอร์ชันถัดไป")
        
        with st.form("feedback_form", clear_on_submit=True):
            rating_star = st.select_slider(
                "⭐ ให้คะแนนความพึงพอใจแอปพลิเคชันของคุณ:",
                options=[1, 2, 3, 4, 5],
                value=5,
                format_func=lambda x: "⭐" * x + f" ({x} ดาว)"
            )
            
            comment_text = st.text_area(
                "📝 ข้อเสนอแนะเพิ่มเติม หรือปัญหาที่ต้องการแจ้งแอดมิน:",
                placeholder="พิมพ์ข้อความของคุณที่นี่..."
            )
            
            submit_feed = st.form_submit_button(
                label="🚀 ส่งความคิดเห็นให้แอดมิน",
                use_container_width=True,
                type="primary"
            )
            
            if submit_feed:
                if comment_text.strip() == "":
                    st.warning("⚠️ กรุณาพิมพ์ข้อความแนะนำติชมก่อนกดส่ง")
                else:
                    try:
                        conn = get_conn()
                        curr = conn.cursor()
                        
                        # --- ตรวจสอบชื่อคอลัมน์ของตาราง suggestions บนระบบจริงเพื่อความปลอดภัย ---
                        curr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='suggestions'")
                        sug_cols = [col[0] for col in curr.fetchall()]
                        
                        # ไล่จับคู่ตัวแปรตามระบบจริงหลังบ้าน
                        f_user = "username" if "username" in sug_cols else sug_cols[1]
                        f_rate = "rating" if "rating" in sug_cols else sug_cols[2]
                        
                        # ค้นหาคอลัมน์ที่จะเก็บ Text (ป้องกันกรณีไม่ได้ชื่อ comment)
                        f_text = "comment"
                        if "comment" not in sug_cols:
                            for alternate in ["details", "detail", "msg", "message", "text", "feedback"]:
                                if alternate in sug_cols:
                                    f_text = alternate
                                    break
                            if f_text == "comment": # ถ้ายังไม่เจอกลุ่มชื่อทั่วไป ให้หยิบคอลัมน์ที่เหลือมาแทน
                                f_text = sug_cols[3] if len(sug_cols) > 3 else sug_cols[-1]

                        f_time = "timestamp" if "timestamp" in sug_cols else sug_cols[-1]

                        # สร้างคิวรี่ด้วยชื่อฟิลด์จริงที่ถูกต้องบนระบบ
                        query_sug = f"""
                            INSERT INTO suggestions ({f_user}, {f_rate}, {f_text}, {f_time})
                            VALUES (%s, %s, %s, NOW())
                        """
                        
                        curr.execute(query_sug, (st.session_state.username, int(rating_star), str(comment_text)))
                        conn.commit()
                        curr.close()
                        conn.close()
                        st.success("🎉 ส่งข้อมูลคำติชมสำเร็จ! ขอบพระคุณสำหรับความคิดเห็นครับ")
                        st.rerun()
                    except Exception as e:
                        st.error(f"ไม่สามารถส่งข้อมูลได้เนื่องจากโครงสร้างตารางฐานข้อมูล: {e}")

    # ------------------ TAB 4: PROFILE (โปรไฟล์ส่วนตัว) ------------------
    with tabs[4]:
        st.subheader(T["tab_profile"])
        st.write("Username:", st.session_state.username)


# ==========================================
# 7. ADMIN PANEL
# ==========================================
def admin_page(T):
    st.title(T["nav_admin"])
    t1, t2 = st.tabs([T["admin_user_tab"], T["admin_feed_tab"]])

    with t1:
        st.subheader(T["admin_user_tab"])
        conn = get_conn()
        u_df = pd.read_sql("SELECT username, fullname, email, age FROM users", conn)
        conn.close()

        edited_u = st.data_editor(u_df, num_rows="dynamic", use_container_width=True)

        if st.button(T["admin_save_user_btn"]):
            old_u = u_df["username"].tolist()
            new_u = edited_u["username"].tolist()
            deleted = [u for u in old_u if u not in new_u]

            conn = get_conn()
            curr = conn.cursor()
            for d in deleted:
                curr.execute("DELETE FROM users WHERE username = %s", (d,))
                curr.execute("DELETE FROM saved_recipes WHERE username = %s", (d,))
            
            conn.commit()
            curr.close()
            conn.close()
            st.success(T["msg_success"])
            st.rerun()

    with t2:
        st.subheader(T["admin_feed_tab"])
        try:
            conn = get_conn()
            s_df = pd.read_sql("SELECT * FROM suggestions ORDER BY timestamp DESC", conn)
            
            curr = conn.cursor()
            curr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='suggestions'")
            sug_cols = [col[0] for col in curr.fetchall()]
            curr.close()
            conn.close()

            if not s_df.empty:
                # 1. ค้นหาคอลัมน์ Rating
                f_rate = "rating" if "rating" in s_df.columns else s_df.columns[2]
                s_df[f_rate] = s_df[f_rate].fillna(0).astype(int)
                avg_rating = s_df[f_rate].mean()

                # 2. ค้นหาคอลัมน์ข้อความ (Comment)
                f_text = "comment"
                for alternate in ["comment", "details", "detail", "msg", "message", "text", "feedback"]:
                    if alternate in s_df.columns:
                        f_text = alternate
                        break

                # แสดงผลสรุปคะแนนเฉลี่ยและกราฟวงกลม
                c1, c2 = st.columns([1, 2])
                c1.metric("คะแนนเฉลี่ยรวม", f"⭐ {avg_rating:.2f} / 5.0")

                fig = px.pie(s_df, names=f_rate, title="สัดส่วนคะแนนความพึงพอใจ (%)")
                c2.plotly_chart(fig, use_container_width=True)

                st.divider()
                st.subheader("📥 กล่องข้อความจากผู้ใช้งานล่าสุด")

                # จัดการเปลี่ยนชื่อหัวคอลัมน์ให้แอดมินอ่านง่าย
                disp_df = s_df.copy()
                rename_dict = {}
                if "username" in disp_df.columns: rename_dict["username"] = "ผู้ส่งข้อความ"
                if f_rate in disp_df.columns: rename_dict[f_rate] = "คะแนนที่ให้"
                if f_text in disp_df.columns: rename_dict[f_text] = "ข้อความแนะนำติชม/แจ้งปัญหา"
                if "timestamp" in disp_df.columns: rename_dict["timestamp"] = "เวลาที่ส่ง"
                
                disp_df = disp_df.rename(columns=rename_dict)
                st.dataframe(disp_df, use_container_width=True)

                # -------- ส่วนที่เพิ่มใหม่: เครื่องมือสำหรับลบข้อความ --------
                st.divider()
                st.subheader("🗑️ เครื่องมือจัดการและลบข้อความ")
                
                # สร้างตัวเลือกรายการข้อความเพื่อกดลบรายบุคคล
                delete_options = ["--- เลือกข้อความที่ต้องการลบ ---", "⚠️ ลบข้อความทั้งหมด (Clear All)"]
                for idx, row in s_df.iterrows():
                    time_str = str(row["timestamp"])[:19] if "timestamp" in s_df.columns else f"ID: {idx}"
                    delete_options.append(f"ผู้ส่ง: {row['username']} | เวลา: {time_str} | ข้อความ: {str(row[f_text])[:20]}...")
                
                selected_delete = st.selectbox("เลือกรายการที่ต้องการลบออก", delete_options, index=0)
                
                if st.button("❌ ยืนยันการลบข้อความ", type="primary", use_container_width=True):
                    if selected_delete == "--- เลือกข้อความที่ต้องการลบ ---":
                        st.warning("โปรดเลือกรายการข้อความที่ต้องการลบก่อนครับ")
                    
                    elif selected_delete == "⚠️ ลบข้อความทั้งหมด (Clear All)":
                        conn = get_conn()
                        curr = conn.cursor()
                        curr.execute("DELETE FROM suggestions")
                        conn.commit()
                        curr.close()
                        conn.close()
                        st.success("💥 ลบข้อความทั้งหมดในกล่องข้อความเรียบร้อยแล้ว!")
                        st.rerun()
                    
                    else:
                        # แกะค่า username และข้อความที่เลือกเพื่อระบุตัวที่จะลบในฐานข้อมูล
                        # ค้นหาข้อความที่ตรงกันจาก list ตัวแปรที่เลือก
                        opt_idx = delete_options.index(selected_delete) - 2 # ปรับ Index ให้ตรงกับ s_df
                        target_row = s_df.iloc[opt_idx]
                        
                        conn = get_conn()
                        curr = conn.cursor()
                        
                        # ใช้เงื่อนไขระบุตัวลบผ่าน username และข้อความ/หรือเวลา
                        if "timestamp" in s_df.columns:
                            curr.execute(
                                f"DELETE FROM suggestions WHERE username = %s AND timestamp = %s", 
                                (str(target_row['username']), target_row['timestamp'])
                            )
                        else:
                            curr.execute(
                                f"DELETE FROM suggestions WHERE username = %s AND {f_text} = %s", 
                                (str(target_row['username']), str(target_row[f_text]))
                            )
                            
                        conn.commit()
                        curr.close()
                        conn.close()
                        st.success(f"🗑️ ลบข้อความของ {target_row['username']} สำเร็จแล้ว!")
                        st.rerun()
            else:
                st.info("ยังไม่มีข้อมูลการติชมเข้ามา")
                
        except Exception as e:
            st.error(f"ไม่สามารถดึงข้อมูลกล่องข้อความมาแสดงผลให้แอดมินได้: {e}")


# ==========================================
# 8. MAIN NAVIGATION
# ==========================================
def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    # ระบบสลับภาษาใน Sidebar
    st.sidebar.markdown("### 🌐 Language / ภาษา")
    lang_choice = st.sidebar.selectbox("Language", ["ไทย", "English"], label_visibility="collapsed")
    L_CODE = "TH" if lang_choice == "ไทย" else "EN"
    T = LANG[L_CODE]

    if not st.session_state.logged_in:
        auth_page(T)
    else:
        st.sidebar.title(f"👤 {st.session_state.fullname}")
        nav_opts = [T["nav_home"]]
        
        # แสดงเมนูผู้ดูแลระบบเฉพาะคนชื่อ 'ang' เท่านั้น
        if st.session_state.username == 'ang':
            nav_opts.append(T["nav_admin"])
        
        choice = st.sidebar.radio("MENU", nav_opts, label_visibility="collapsed")
        
        if st.sidebar.button(T["nav_logout"], use_container_width=True):
            st.session_state.clear()
            st.rerun()
        
        # ควบคุมทิศทางการเปิดหน้าเพจหลัก
        if choice == T["nav_home"]:
            user_page(T, L_CODE)
        elif choice == T["nav_admin"]:
            admin_page(T)

if __name__ == "__main__":
    main()
