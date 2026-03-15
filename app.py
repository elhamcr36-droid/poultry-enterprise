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

# ---------------- CONFIG ---------------- #

st.markdown("""
<style>

/* ปุ่มทั้งหมดใน sidebar */
section[data-testid="stSidebar"] button {
    background-color: #ef4444 !important;
    color: white !important;
    border-radius: 8px !important;
    border: none !important;
    width: 100%;
}

/* hover */
section[data-testid="stSidebar"] button:hover {
    background-color: #dc2626 !important;
}

/* เอาพื้นหลังขาวของ container ออก */
section[data-testid="stSidebar"] div[data-testid="stButton"] {
    background-color: transparent !important;
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
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # ตาราง suggestions
    cur.execute("""
    CREATE TABLE IF NOT EXISTS suggestions (
        id SERIAL PRIMARY KEY,
        username TEXT,
        message TEXT,
        rating INTEGER,
        timestamp TIMESTAMP
    )
    """)

    # ตรวจสอบว่าคอลัมน์ rating มีหรือยัง
    cur.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name='suggestions'
    """)

    columns = [column[0] for column in cur.fetchall()]

    if 'rating' not in columns:
        cur.execute("ALTER TABLE suggestions ADD COLUMN rating INTEGER DEFAULT 5")

    # ตาราง ingredients
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

    # ตาราง saved_recipes
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

    # ตรวจสอบ admin
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

    # ตรวจสอบ ingredients
    cur.execute("SELECT COUNT(*) FROM ingredients")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO ingredients VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            STANDARD_INGREDIENTS
        )

    conn.commit()


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
# --- 6. USER DASHBOARD ---
def user_page(T, L_CODE):

    st.title(T["title"])

    tabs = st.tabs([
        T["tab_calc"],
        T["tab_hist"],
        T["tab_stock"],
        T["tab_feed"],
        T["tab_profile"]
    ])

    with tabs[0]:
        

        c1, c2 = st.columns([1, 2])

        # ---------------- LEFT PANEL ----------------
        with c1:

            st.subheader(T["config_sec"])

            cur_master = ANIMAL_MASTER[L_CODE]

            g_key = st.selectbox(
                T["group_label"],
                list(cur_master.keys())
            )

            b_key = st.selectbox(
                T["breed_label"],
                cur_master[g_key]["breeds"]
            )

            s_key = st.selectbox(
                T["stage_label"],
                list(cur_master[g_key]["stages"].keys())
            )

            num = st.number_input(
                T["count_label"],
                1,
                1000000,
                100
            )

            batch = st.number_input(
                T["batch_label"],
                1,
                5000,
                100
            )

            opt_mode = st.radio(
                T["opt_label"],
                [T["mode_price"], T["mode_nutri"]]
            )

            st.divider()

            st.subheader(T["income_sec"])

            egg_p = st.number_input(
                T["egg_price_label"],
                1.0,
                10.0,
                4.3
            )

            lay_r = st.slider(
                T["lay_rate_label"],
                50,
                100,
                85
            )

            target = cur_master[g_key]["stages"][s_key]["vals"]

                  # --- 6. USER DASHBOARD ---
def user_page(T, L_CODE):

    st.title(T["title"])

    tabs = st.tabs([
        T["tab_calc"],
        T["tab_hist"],
        T["tab_stock"],
        T["tab_feed"],
        T["tab_profile"]
    ])

    # ================= TAB CALCULATOR =================
    with tabs[0]:

        c1, c2 = st.columns([1,2])

        # -------- LEFT PANEL --------
        with c1:

            st.subheader(T["config_sec"])

            cur_master = ANIMAL_MASTER[L_CODE]

            g_key = st.selectbox(T["group_label"], list(cur_master.keys()))
            b_key = st.selectbox(T["breed_label"], cur_master[g_key]["breeds"])
            s_key = st.selectbox(T["stage_label"], list(cur_master[g_key]["stages"].keys()))

            num = st.number_input(T["count_label"],1,1000000,100)
            batch = st.number_input(T["batch_label"],1,5000,100)

            opt_mode = st.radio(T["opt_label"],[T["mode_price"],T["mode_nutri"]])

            st.divider()

            st.subheader(T["income_sec"])

            egg_p = st.number_input(T["egg_price_label"],1.0,10.0,4.3)
            lay_r = st.slider(T["lay_rate_label"],50,100,85)

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

        # -------- RESULT PANEL --------
        with c2:

            if "calc" in st.session_state:

                r = st.session_state.calc

                st.subheader(T["res_header"])

                res_df = r["df"].copy()
                res_df["Ratio (%)"] = (r["x"]*100).round(2)
                res_df = res_df[res_df["Ratio (%)"]>0]

                name_col = "name_th" if L_CODE=="TH" else "name_en"

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

                m1,m2 = st.columns(2)

                m1.metric(
                    T["protein_actual"],
                    f"{(r['df']['protein']*r['x']).sum():.2f}%",
                    f"Target {r['target'][0]}%"
                )

                m2.metric(
                    T["energy_actual"],
                    f"{(r['df']['energy']*r['x']).sum():.0f}",
                    f"Target {r['target'][1]}"
                )

                table_disp = res_df[[name_col,"Ratio (%)"]].copy()

                table_disp[T["table_need"]] = (
                    res_df["Ratio (%)"]/100*r["batch"]
                ).round(3)

                table_disp.columns=[
                    T["table_name"],
                    T["table_ratio"],
                    T["table_need"]
                ]

                st.table(table_disp)

                st.divider()

                st.subheader(T["profit_sec"])

                daily_feed = (r["n"]*120)/1000
                d_cost = daily_feed*r["cost"]
                d_rev = (r["n"]*r["lay_r"]/100)*r["egg_p"]

                p1,p2,p3 = st.columns(3)

                p1.metric(T["cost_day"],f"{d_cost:,.2f} ฿")
                p2.metric(T["rev_day"],f"{d_rev:,.2f} ฿")
                p3.metric(T["profit_month"],f"{(d_rev-d_cost)*30:,.2f} ฿")

                if st.button(T["btn_save_rec"]):

                    details = ", ".join([
                        f"{row[T['table_name']]} {row[T['table_need']]}kg"
                        for _,row in table_disp.iterrows()
                    ])

                    conn = get_conn()

                    conn.execute(
                        """
                        INSERT INTO saved_recipes
                        (username,breed_name,stage_name,chicken_count,details,cost_per_kg,date)
                        VALUES (%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            st.session_state.username,
                            r['b'],
                            r['s'],
                            r['n'],
                            details,
                            round(r['cost'],2),
                            datetime.now().strftime("%Y-%m-%d %H:%M")
                        )
                    )

                    conn.commit()

                    st.success(T["msg_success"])

    # ================= TAB HISTORY =================
    with tabs[1]:

        st.subheader(T["tab_hist"])

        conn = get_conn()
        df = pd.read_sql("SELECT * FROM saved_recipes ORDER BY date DESC", conn)
        conn.close()

        if df.empty:
            st.info("ยังไม่มีสูตรที่บันทึก")
        else:
            st.dataframe(df,use_container_width=True)

    # ================= TAB STOCK =================
    with tabs[2]:

        st.subheader(T["tab_stock"])

        conn = get_conn()
        df = pd.read_sql(
            "SELECT name_th,protein,energy,fiber,cost FROM ingredients",
            conn
        )
        conn.close()

        st.dataframe(df,use_container_width=True)

    # ================= TAB FEED =================
    with tabs[3]:

        st.subheader(T["tab_feed"])
        st.info("ระบบแนะนำวัตถุดิบ AI จะเพิ่มในเวอร์ชันถัดไป")

    # ================= TAB PROFILE =================
    with tabs[4]:

        st.subheader(T["tab_profile"])
        st.write("Username:",st.session_state.username)


# --- 7. ADMIN PANEL ---
def admin_page(T):

    st.title(T["nav_admin"])

    t1,t2 = st.tabs([T["admin_user_tab"],T["admin_feed_tab"]])

    with t1:

        st.subheader(T["admin_user_tab"])

        conn = get_conn()

        u_df = pd.read_sql(
            "SELECT username,fullname,email,age FROM users",
            conn
        )

        edited_u = st.data_editor(
            u_df,
            num_rows="dynamic",
            use_container_width=True
        )

        if st.button(T["admin_save_user_btn"]):

            old_u = u_df["username"].tolist()
            new_u = edited_u["username"].tolist()

            deleted=[u for u in old_u if u not in new_u]

            for d in deleted:
                conn.execute("DELETE FROM users WHERE username=%s",(d,))
                conn.execute("DELETE FROM saved_recipes WHERE username=%s",(d,))

            conn.commit()

            st.success(T["msg_success"])
            st.rerun()

    with t2:

        st.subheader(T["admin_feed_tab"])

        conn = get_conn()

        s_df = pd.read_sql(
            "SELECT * FROM suggestions ORDER BY timestamp DESC",
            conn
        )

        if not s_df.empty:

            s_df["rating"]=s_df["rating"].fillna(0).astype(int)
            avg_rating=s_df["rating"].mean()

            c1,c2 = st.columns([1,2])

            c1.metric("คะแนนเฉลี่ยรวม",f"⭐ {avg_rating:.2f} / 5.0")

            fig = px.pie(
                s_df,
                names="rating",
                title="สัดส่วนคะแนนความพึงพอใจ (%)"
            )

            c2.plotly_chart(fig,use_container_width=True)

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
