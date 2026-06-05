import streamlit as st
import pandas as pd
import pulp
import plotly.express as px
import re
from supabase import create_client, Client

# ==========================================
# 1. PAGE CONFIGURATION & THEME
# ==========================================
st.set_page_config(
    layout="wide", 
    page_title="Smart Layer Feed - ระบบคำนวณสูตรอาหารไก่ไข่อัจฉริยะ",
    page_icon="🥚"
)

# ==========================================
# 2. CUSTOM CSS & STYLES
# ==========================================
def add_custom_styles():
    st.markdown(
        """
        <style>
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background: linear-gradient(180deg, #4b749f 0%, #243b55 100%) !important;
            background-attachment: fixed !important;
        }
        .app-main-title {
            color: #ffffff !important; font-size: 38px !important; font-weight: bold !important;
            text-align: center; margin-top: 40px; margin-bottom: 0px;
            text-shadow: 0px 4px 12px rgba(0, 0, 0, 0.3);
        }
        .app-sub-title {
            color: #ffcc00 !important; font-size: 24px !important; font-weight: bold !important;
            text-align: center; margin-top: 5px; margin-bottom: 30px;
            text-shadow: 0px 2px 8px rgba(0, 0, 0, 0.3);
        }
        .auth-container {
            max-width: 400px; margin: 0 auto; background-color: #ffffff !important;
            padding: 40px 30px; border-radius: 28px; box-shadow: 0 20px 45px rgba(0, 0, 0, 0.25); text-align: center;
        }
        .avatar-container {
            width: 85px; height: 85px; background-color: #fff9f0; border-radius: 50%;
            margin: 0 auto 20px auto; border: 3px solid #ffdfb4; display: flex; align-items: center; justify-content: center;
        }
        .avatar-container span { font-size: 42px; }
        .auth-container .stTextInput { margin-bottom: 12px !important; }
        .auth-container .stTextInput input {
            border-radius: 12px !important; border: 1px solid #d3e2f2 !important;
            padding: 12px 15px !important; background-color: #eef5fc !important; color: #333333 !important;
        }
        .auth-container div.stButton > button {
            background: linear-gradient(90deg, #4a76a8 0%, #3b5998 100%) !important;
            color: #ffffff !important; border-radius: 12px !important; padding: 12px 20px !important;
            font-size: 16px !important; font-weight: bold !important; width: 100% !important; margin-top: 15px;
        }
        /* Dashboard Card styling */
        div[data-testid="stGridColumn"] > div {
            background-color: rgba(255, 255, 255, 0.95) !important; 
            padding: 25px; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
        div[data-testid="stMetric"] {
            background-color: #f8fafc !important; padding: 15px; border-radius: 12px;
            border-left: 5px solid #3b5998; border: 1px solid #e2e8f0;
        }
        [data-testid="stMetricValue"] { font-weight: bold; color: #3b5998 !important; }
        [data-testid="stMetricLabel"] { color: #64748b !important; }
        
        /* Profile Active Button */
        div.profile-box {
            padding: 15px; border-radius: 12px; text-align: center; background-color: #f0f4f8;
            border: 2px solid #cbd5e1; cursor: pointer; transition: 0.3s;
        }
        div.profile-box-active {
            padding: 15px; border-radius: 12px; text-align: center; background-color: #eff6ff;
            border: 2px solid #3b82f6; box-shadow: 0 0 10px rgba(59,130,246,0.3);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

add_custom_styles()

# ==========================================
# 3. SUPABASE AUTH INTEGRATION & VALIDATION
# ==========================================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def is_password_strong(password):
    if len(password) < 8: return False, "รหัสผ่านต้องมีความยาวอย่างน้อย 8 ตัวอักษร"
    if not re.search("[a-z]", password): return False, "รหัสผ่านต้องมีตัวอักษรภาษาอังกฤษตัวพิมพ์เล็ก (a-z)"
    if not re.search("[A-Z]", password): return False, "รหัสผ่านต้องมีตัวอักษรภาษาอังกฤษตัวพิมพ์ใหญ่ (A-Z)"
    if not re.search("[0-9]", password): return False, "รหัสผ่านต้องมีตัวเลข (0-9)"
    return True, "รหัสผ่านปลอดภัยตามมาตรฐาน"

if "auth_page" not in st.session_state: st.session_state.auth_page = "login"
if "user" not in st.session_state: st.session_state.user = None
if "is_admin" not in st.session_state: st.session_state.is_admin = False

# ==========================================
# 4. DATA DICTIONARIES (ฐานข้อมูลสารอาหารแนะนำและวัตถุดิบ)
# ==========================================
# เกณฑ์ความต้องการโภชนาการจำแนกตามช่วงอายุ (Animal Profile Targets)
STAGE_NUTRITION_TARGETS = {
    "starter": {
        "title": "ลูกไก่ (แรกเกิด - 6 สัปดาห์)",
        "desc": "🐥 เน้นโปรตีนสูงเพื่อสร้างกล้ามเนื้อและโครงสร้างหลัก",
        "protein": 18.5, "me": 2850.0, "calcium": 1.00, "phos": 0.45, "amino": 0.40
    },
    "grower": {
        "title": "ไก่สาวรุ่น (6 - 12 สัปดาห์)",
        "desc": "🐓 คุมน้ำหนักตัว ไม่ให้อ้วนเกินไปก่อนเริ่มไข่",
        "protein": 15.5, "me": 2750.0, "calcium": 0.90, "phos": 0.40, "amino": 0.32
    },
    "laying": {
        "title": "ไก่ระยะให้ผลผลิตไข่",
        "desc": "🥚 เน้นแคลเซียมสูงมาก เพื่อความแข็งแรงของเปลือกไข่",
        "protein": 17.5, "me": 2800.0, "calcium": 4.00, "phos": 0.45, "amino": 0.38
    }
}

# ฐานข้อมูลสารอาหารในวัตถุดิบ (ต่อ 1 กิโลกรัม)
INGREDIENT_DATA = {
    "ข้าวโพดบด": {"price": 13.5, "protein": 8.5, "me": 3300.0, "calcium": 0.02, "phos": 0.25, "amino": 0.18},
    "กากถั่วเหลือง": {"price": 18.5, "protein": 44.0, "me": 2420.0, "calcium": 0.25, "phos": 0.60, "amino": 0.65},
    "รำละเอียด": {"price": 11.0, "protein": 12.0, "me": 2400.0, "calcium": 0.05, "phos": 1.35, "amino": 0.22},
    "ปลาป่น": {"price": 32.0, "protein": 60.0, "me": 2850.0, "calcium": 5.00, "phos": 3.00, "amino": 0.95},
    "เปลือกหอยบด": {"price": 4.0, "protein": 0.0, "me": 0.0, "calcium": 38.00, "phos": 0.04, "amino": 0.00},
    "ไดแคลเซียมฟอสเฟต": {"price": 28.0, "protein": 0.0, "me": 0.0, "calcium": 21.00, "phos": 18.00, "amino": 0.00},
    "กรดอะมิโนสังเคราะห์": {"price": 95.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "amino": 99.00}
}

if "selected_stage_key" not in st.session_state:
    st.session_state.selected_stage_key = "laying"

# ==========================================
# 5. AUTHENTICATION INTERFACE
# ==========================================
if st.session_state.user is None and not st.session_state.is_admin:
    st.markdown('<div class="app-main-title">Smart Layer Feed</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-sub-title">ระบบคำนวณสูตรอาหารไก่ไข่อัจฉริยะ</div>', unsafe_allow_html=True)
    _, center_col, _ = st.columns([1, 1.1, 1])
    
    with center_col:
        if st.session_state.auth_page == "login":
            st.markdown('<div class="auth-container"><div class="avatar-container"><span>🥚</span></div><div style="color:#555555; font-size:15px; margin-bottom:25px; font-weight:500;">ลงชื่อเข้าใช้ระบบเพื่อจัดการสูตรอาหารฟาร์ม</div>', unsafe_allow_html=True)
            login_email = st.text_input("ชื่อผู้ใช้งาน", placeholder="ชื่อผู้ใช้งาน หรือ อีเมลฟาร์ม", key="input_login_email", label_visibility="collapsed")
            login_pass = st.text_input("รหัสผ่าน", placeholder="รหัสผ่าน", type="password", key="input_login_pass", label_visibility="collapsed")
            
            if st.button("ลงชื่อเข้าสู่ระบบฟาร์ม", use_container_width=True):
                if login_email == "222" and login_pass == "222":
                    st.session_state.is_admin = True
                    st.success("🎉 เข้าสู่ระบบสำเร็จ!")
                    st.rerun()
                else:
                    try:
                        response = supabase.auth.sign_in_with_password({"email": login_email, "password": login_pass})
                        st.session_state.user = response.user
                        st.rerun()
                    except Exception: st.error("❌ ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown('<div class="footer-links">', unsafe_allow_html=True)
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                if st.button("ลืมรหัสผ่าน?", key="btn_go_forgot"):
                    st.session_state.auth_page = "forgot"; st.rerun()
            with f_col2:
                if st.button("สมัครสมาชิกฟาร์มใหม่", key="btn_go_reg"):
                    st.session_state.auth_page = "register"; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
        elif st.session_state.auth_page == "register":
            st.markdown('<div class="auth-container"><div class="avatar-container"><span>🐔</span></div><div style="color:#243b55; font-size:18px; margin-bottom:25px; font-weight:bold;">ลงทะเบียนเปิดบัญชีฟาร์มใหม่</div>', unsafe_allow_html=True)
            reg_fn = st.text_input("ชื่อจริง", placeholder="ชื่อจริงผู้ดูแล", key="reg_fn", label_visibility="collapsed")
            reg_ln = st.text_input("นามสกุล", placeholder="นามสกุล", key="reg_ln", label_visibility="collapsed")
            reg_email = st.text_input("อีเมล", placeholder="ที่อยู่อีเมลสำหรับฟาร์ม", key="reg_email", label_visibility="collapsed")
            reg_password = st.text_input("รหัสผ่าน", placeholder="ตั้งรหัสผ่านใหม่", type="password", key="reg_password", label_visibility="collapsed")
            farm_name = st.text_input("ชื่อฟาร์ม", placeholder="ชื่อฟาร์มไก่ไข่ของคุณ", key="reg_farm", label_visibility="collapsed")
            
            if st.button("ลงทะเบียนบัญชีฟาร์ม", use_container_width=True):
                is_valid, msg = is_password_strong(reg_password)
                if not (reg_fn and reg_email and reg_password and farm_name): st.error("❌ กรุณากรอกข้อมูลให้ครบถ้วน")
                elif not is_valid: st.error(f"❌ {msg}")
                else:
                    try:
                        supabase.auth.sign_up({"email": reg_email, "password": reg_password, "options": {"data": {"first_name": reg_fn, "last_name": reg_ln, "farm_name": farm_name}}})
                        st.success("📩 ตรวจสอบกล่องข้อความอีเมลของคุณเพื่อยืนยัน!")
                    except Exception as e: st.error(f"เกิดข้อผิดพลาด: {str(e)}")
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 6. MAIN SYSTEM DASHBOARD
# ==========================================
else:
    if st.session_state.is_admin:
        user_name = "แอดมินฟาร์ม"; farm_title = "ระบบจัดการหลังบ้านสูงสุด"
    else:
        user_info = st.session_state.user.user_metadata
        user_name = user_info.get("first_name", "ผู้เลี้ยง"); farm_title = user_info.get("farm_name", "สมาร์ทฟาร์ม")
    
    st.markdown("<style>h1, h2, h3, h4, h5, h6, p, label { color: #ffffff !important; }</style>", unsafe_allow_html=True)
    
    header_col1, header_col2 = st.columns([8, 2])
    with header_col1:
        st.title(f"🥚 Smart Layer Feed - {farm_title}")
        st.subheader(f"👋 ยินดีต้อนรับคุณ {user_name} (โหมดผสมและวิเคราะห์สูตรอาหาร Real-time)")
    with header_col2:
        st.write("")
        if st.button("🔒 ออกจากระบบ"):
            if not st.session_state.is_admin: supabase.auth.sign_out()
            st.session_state.user = None; st.session_state.is_admin = False; st.rerun()

    st.markdown("---")

    # ------------------------------------------
    # FEATURE 1: ANIMAL PROFILE (เลือกช่วงอายุไก่ผ่านปุ่มรูปภาพ/การ์ด)
    # ------------------------------------------
    st.markdown("### 🐔 1. Animal Profile (เลือกช่วงอายุไก่เป้าหมาย)")
    p_col1, p_col2, p_col3 = st.columns(3)
    
    with p_col1:
        is_active = "profile-box-active" if st.session_state.selected_stage_key == "starter" else "profile-box"
        st.markdown(f'<div class="{is_active}"><h3>🐥</h3><b>ลูกไก่</b><br><small>แรกเกิด - 6 สัปดาห์</small></div>', unsafe_allow_html=True)
        if st.button("เลือกกลุ่มลูกไก่", use_container_width=True, key="set_starter"):
            st.session_state.selected_stage_key = "starter"; st.rerun()

    with p_col2:
        is_active = "profile-box-active" if st.session_state.selected_stage_key == "grower" else "profile-box"
        st.markdown(f'<div class="{is_active}"><h3>🐓</h3><b>ไก่สาวรุ่น</b><br><small>6 - 12 สัปดาห์</small></div>', unsafe_allow_html=True)
        if st.button("เลือกกลุ่มไก่สาว", use_container_width=True, key="set_grower"):
            st.session_state.selected_stage_key = "grower"; st.rerun()

    with p_col3:
        is_active = "profile-box-active" if st.session_state.selected_stage_key == "laying" else "profile-box"
        st.markdown(f'<div class="{is_active}"><h3>🥚</h3><b>ไก่ระยะไข่</b><br><small>ให้ผลผลิตสูง</small></div>', unsafe_allow_html=True)
        if st.button("เลือกกลุ่มไก่ระยะไข่", use_container_width=True, key="set_laying"):
            st.session_state.selected_stage_key = "laying"; st.rerun()

    # โหลดค่าสารอาหารเป้าหมายตามช่วงอายุที่เลือก
    current_key = st.session_state.selected_stage_key
    target = STAGE_NUTRITION_TARGETS[current_key]
    
    st.info(f"📋 **กลุ่มที่เลือก:** {target['title']} | {target['desc']}")

    st.markdown("---")

    # ------------------------------------------
    # FEATURE 2 & 3: RECIPE CREATOR & NUTRITION ALERT (Real-time)
    # ------------------------------------------
    st.markdown("### 🎛️ 2. Recipe Creator & Nutrition Alert (จำลองการผสมสูตรอาหาร)")
    
    creator_left, creator_right = st.columns([4, 6], gap="large")
    
    # ฝั่งซ้าย: สไลเดอร์ปรับเปลี่ยนอัตราส่วนวัตถุดิบ (รวมกันต้องให้ได้ 100%)
    with creator_left:
        st.markdown("##### 🌽 สัดส่วนวัตถุดิบอาหารดิบ (%)")
        w_corn = st.slider("ข้าวโพดบด", 0, 100, 55, key="slide_corn")
        w_soy = st.slider("กากถั่วเหลือง", 0, 100, 25, key="slide_soy")
        w_bran = st.slider("รำละเอียด", 0, 100, 10, key="slide_bran")
        w_fish = st.slider("ปลาป่น (โปรตีนสัตว์)", 0, 100, 4, key="slide_fish")
        w_shell = st.slider("เปลือกหอยบด (แคลเซียม)", 0, 100, 5, key="slide_shell")
        w_dcp = st.slider("ไดแคลเซียมฟอสเฟต", 0, 100, 1, key="slide_dcp")
        w_amino = st.slider("กรดอะมิโนสังเคราะห์", 0, 5, 0, key="slide_amino")
        
        total_weight_pct = w_corn + w_soy + w_bran + w_fish + w_shell + w_dcp + w_amino
        
        if total_weight_pct == 100:
            st.success(f"⚖️ สัดส่วนผสมครบถ้วน: {total_weight_pct}% พอดี")
        else:
            st.error(f"⚠️ สัดส่วนผสมรวมต้องเท่ากับ 100% (ขณะนี้รวมได้: {total_weight_pct}%)")

    # คำนวณคุณค่าทางอาหารที่ได้ตามสูตรจริง ณ ปัจจุบัน
    current_nutrition = {"protein": 0.0, "me": 0.0, "calcium": 0.0, "phos": 0.0, "amino": 0.0}
    weights = [w_corn, w_soy, w_bran, w_fish, w_shell, w_dcp, w_amino]
    
    for idx, (name, nutrients) in enumerate(INGREDIENT_DATA.items()):
        factor = weights[idx] / 100.0
        current_nutrition["protein"] += nutrients["protein"] * factor
        current_nutrition["me"] += nutrients["me"] * factor
        current_nutrition["calcium"] += nutrients["calcium"] * factor
        current_nutrition["phos"] += nutrients["phos"] * factor
        current_nutrition["amino"] += nutrients["amino"] * factor

    # ฝั่งขวา: แถบวัดผลวิเคราะห์สารอาหารและการแจ้งเตือนสารอาหาร (Nutrition Alert)
    with creator_right:
        st.markdown("##### 📊 เกณฑ์สารอาหารที่ได้ vs ค่าแนะนำ")
        
        # ฟังก์ชันวาด Progress Bar แสดงค่าจริงเทียบเป้าหมาย
        def render_nutrient_row(label, current, required, unit):
            pct_of_target = min(1.0, current / required) if required > 0 else 1.0
            st.write(f"**{label}**: {current:.2f} {unit} / เป้าหมายต่ำกว่าไม่ได้ {required:.2f} {unit}")
            st.progress(pct_of_target)

        render_nutrient_row("โปรตีน (Protein)", current_nutrition["protein"], target["protein"], "%")
        render_nutrient_row("พลังงาน (ME)", current_nutrition["me"], target["me"], "kcal/กก.")
        render_nutrient_row("แคลเซียม (Calcium)", current_nutrition["calcium"], target["calcium"], "%")
        render_nutrient_row("ฟอสฟอรัส (Phosphorus)", current_nutrition["phos"], target["phos"], "%")
        render_nutrient_row("กรดอะมิโนจำเป็น (Amino Acid)", current_nutrition["amino"], target["amino"], "%")
        
        st.markdown("##### 🚨 Nutrition Alert (วิเคราะห์ข้อผิดพลาด)")
        
        # ข้อความเตือนความผิดพลาดทางโภชนาการแบบ Real-time
        alerts_triggered = False
        
        if current_nutrition["calcium"] < target["calcium"]:
            st.markdown(f"🔴 **อันตราย! แคลเซียมต่ำเกินไป ({current_nutrition['calcium']:.2f}%)**: อาจทำให้แม่ไก่ดึงแคลเซียมจากกระดูกมาใช้ ส่งผลให้ไข่มีเปลือกบาง แตกหักง่าย หรือไก่เป็นอัมพาต")
            alerts_triggered = True
            
        if w_fish > 8:
            st.markdown(f"🟡 **คำเตือน! ใส่ปลาป่นมากเกินไป ({w_fish}%)**: การใส่ปลาป่นเกิน 8% จะสะสมสาร Trimethylamine ทำให้ไข่ไก่ส่งกลิ่นคาวปลา ตลาดไม่ต้องการ")
            alerts_triggered = True
            
        if current_nutrition["protein"] < target["protein"]:
            st.markdown(f"🔴 **โปรตีนไม่เพียงพอ**: ไก่จะให้ไข่ฟองเล็ก อัตราการไข่ลดลงอย่างรวดเร็ว")
            alerts_triggered = True
            
        if not alerts_triggered and total_weight_pct == 100:
            st.markdown("🟢 **สูตรอาหารสมบูรณ์แบบ** คุณค่าทางโภชนาการปลอดภัยและเหมาะสมสำหรับกลุ่มไก่เป้าหมายแล้ว")

    st.markdown("---")

    # ------------------------------------------
    # FEATURE 4: BATCH & CHECKLIST (ใบสั่งชั่งและเครื่องมือหน้าเล้า)
    # ------------------------------------------
    st.markdown("### 📋 3. Batch & Checklist (ใบสั่งจัดเตรียมวัตถุดิบจริงหน้าเล้า)")
    
    batch_col1, batch_col2 = st.columns([4, 6], gap="large")
    
    with batch_col1:
        st.markdown("##### 📦 ตั้งค่าจำนวนการผสม")
        mix_volume_kg = st.number_input("ต้องการผสมอาหารต่องวดรวมทั้งหมดกี่กิโลกรัม (กก.)", min_value=1.0, value=50.0, step=5.0)
        st.write(f"💡 ระบบจะทำการแปลงสัดส่วนอาหารเป็นน้ำหนักจริงชั่งจากฐานสูตรอาหารปัจจุบัน")

    with batch_col2:
        st.markdown(f"##### 📱 Mobile Checklist สำหรับตักส่วนผสมหน้าเล้า (เป้าหมาย {mix_volume_kg} กก.)")
        st.caption("เกษตรกรสามารถถือมือถือเดินตักวัตถุดิบและกดติ๊กเลือกเมื่อตักลงถังผสมเสร็จสิ้น")
        
        # คำนวณและแปลงสัดส่วนน้ำหนักตามปริมาณรวมที่ตั้งค่าไว้
        ingredient_names = list(INGREDIENT_DATA.keys())
        for idx, name in enumerate(ingredient_names):
            calc_weight = (weights[idx] / 100.0) * mix_volume_kg
            if calc_weight > 0:
                st.checkbox(f"⬜ ชั่ง **{name}** ➔ ปริมาณสุทธิ **{calc_weight:,.2f} กก.** (สัดส่วน {weights[idx]}%)", key=f"chk_{idx}")
