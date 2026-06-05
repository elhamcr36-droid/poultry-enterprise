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
# 2. CUSTOM CSS (แก้ไข Layout ให้ตรงล็อก ไม่หลุดกล่อง)
# ==========================================
def add_custom_styles():
    st.markdown(
        """
        <style>
        /* พื้นหลังหลักสีน้ำเงินไล่เฉดสไตล์ Corporate แบบในรูปภาพ */
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background: linear-gradient(180deg, #4b749f 0%, #243b55 100%) !important;
            background-attachment: fixed !important;
        }
        
        /* หัวข้อระบบด้านบนสุด */
        .app-main-title {
            color: #ffffff !important;
            font-size: 38px !important;
            font-weight: bold !important;
            text-align: center;
            margin-top: 40px;
            margin-bottom: 0px;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            text-shadow: 0px 4px 12px rgba(0, 0, 0, 0.3);
        }
        .app-sub-title {
            color: #ffcc00 !important; 
            font-size: 24px !important;
            font-weight: bold !important;
            text-align: center;
            margin-top: 5px;
            margin-bottom: 30px;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            text-shadow: 0px 2px 8px rgba(0, 0, 0, 0.3);
        }
        
        /* กล่องการ์ดสีขาวที่รวมทุกองค์ประกอบ (แก้ปัญหาหลุดเฟรม) */
        .auth-container {
            max-width: 450px;
            margin: 0 auto;
            background-color: #ffffff !important;
            padding: 35px 35px 30px 35px;
            border-radius: 30px; 
            box-shadow: 0 20px 45px rgba(0, 0, 0, 0.25);
            text-align: center;
        }
        
        /* วงกลมไอคอนไข่ไก่ */
        .avatar-container {
            width: 90px;
            height: 90px;
            background-color: #fff9f0;
            border-radius: 50%;
            margin: 0 auto 15px auto;
            border: 3px solid #ffdfb4;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .avatar-container span {
            font-size: 45px;
        }
        
        /* สไตล์ช่องกรอกข้อมูลภายในกล่องสีขาว */
        .auth-container .stTextInput input {
            border-radius: 12px !important;
            border: 1px solid #d3e2f2 !important;
            padding: 12px 15px !important;
            background-color: #eef5fc !important;
            color: #333333 !important;
            font-size: 16px !important;
        }
        
        /* ปุ่มเข้าสู่ระบบแบบ Gradient กว้างเต็มกล่อง */
        .auth-container div.stButton > button {
            background: linear-gradient(90deg, #4a76a8 0%, #3b5998 100%) !important;
            color: #ffffff !important;
            border-radius: 12px !important;
            padding: 12px 20px !important;
            font-size: 16px !important;
            font-weight: bold !important;
            border: none !important;
            width: 100% !important;
            box-shadow: 0 4px 15px rgba(59, 89, 152, 0.2) !important;
            margin-top: 10px;
        }
        .auth-container div.stButton > button:hover {
            background: linear-gradient(90deg, #3b5998 0%, #243b55 100%) !important;
            transform: translateY(-1px);
        }
        
        /* ปุ่มลิงก์ลืมรหัสผ่าน / สมัครสมาชิกใต้กล่อง (ปรับให้เป็นข้อความกึ่งกลางคลีนๆ) */
        .footer-links {
            text-align: center;
            margin-top: 20px;
        }
        .footer-links div.stButton > button {
            background: transparent !important;
            color: rgba(255, 255, 255, 0.9) !important;
            border: none !important;
            font-size: 14px !important;
            font-weight: normal !important;
            padding: 5px 10px !important;
            width: auto !important;
            box-shadow: none !important;
        }
        .footer-links div.stButton > button:hover {
            color: #ffcc00 !important;
            text-decoration: underline !important;
            background: transparent !important;
        }
        
        /* สไตล์หน้า Dashboard ระบบภายใน */
        div[data-testid="stGridColumn"] > div {
            background-color: rgba(255, 255, 255, 0.95) !important; 
            padding: 25px;
            border-radius: 16px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
        div[data-testid="stMetric"] {
            background-color: #f8fafc !important;
            padding: 15px;
            border-radius: 12px;
            border-left: 5px solid #3b5998;
            border: 1px solid #e2e8f0;
        }
        [data-testid="stMetricValue"] { font-weight: bold; color: #3b5998 !important; }
        [data-testid="stMetricLabel"] { color: #64748b !important; }
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
    if len(password) < 8:
        return False, "รหัสผ่านต้องมีความยาวอย่างน้อย 8 ตัวอักษร"
    if not re.search("[a-z]", password):
        return False, "รหัสผ่านต้องมีตัวอักษรภาษาอังกฤษตัวพิมพ์เล็ก (a-z)"
    if not re.search("[A-Z]", password):
        return False, "รหัสผ่านต้องมีตัวอักษรภาษาอังกฤษตัวพิมพ์ใหญ่ (A-Z)"
    if not re.search("[0-9]", password):
        return False, "รหัสผ่านต้องมีตัวเลข (0-9)"
    return True, "รหัสผ่านปลอดภัยตามมาตรฐาน"

if "auth_page" not in st.session_state:
    st.session_state.auth_page = "login"
if "user" not in st.session_state:
    st.session_state.user = None

# ==========================================
# 4. HARDCODED DATA (คลังข้อมูลสารอาหารไก่ไข่)
# ==========================================
raw_ingredients = [
    ('พลังงาน', 'ข้าวโพด', 'Corn'), ('พลังงาน', 'ปลายข้าว', 'Broken Rice'), ('พลังงาน', 'รำละเอียด', 'Rice Bran'),
    ('โปรตีนจากพืช', 'กากถั่วเหลือง', 'Soybean Meal'), ('โปรตีนจากสัตว์', 'ปลาป่น', 'Fish Meal'),
    ('แร่ธาตุ', 'หินปูนบด', 'Limestone'), ('แร่ธาตุ', 'เปลือกหอยบด', 'Ground Oyster Shell'),
    ('กรดอะมิโน', 'ดีแอล-เมไทโอนีน', 'DL-Methionine'), ('กรดอะมิโน', 'แอล-ไลซีน เอชซีแอล', 'L-Lysine HCl')
]

df_ingredients = pd.DataFrame(raw_ingredients, columns=['category', 'name_th', 'name_en'])
df_ingredients['name'] = df_ingredients['name_th'] + " (" + df_ingredients['name_en'] + ")"

# เซ็ตค่าโภชนาการและราคาจำลองสำหรับการคำนวณเชิงเส้น (Linear Programming)
df_ingredients['price_per_kg'] = [13.5, 14.0, 11.0, 18.5, 32.0, 3.5, 4.0, 95.0, 80.0]
df_ingredients['protein_pct'] = [8.5, 8.0, 12.0, 44.0, 60.0, 0.0, 0.0, 0.0, 0.0]
df_ingredients['me_kcal_per_kg'] = [3300.0, 3200.0, 2400.0, 2420.0, 2850.0, 0.0, 0.0, 0.0, 0.0]
df_ingredients['max_limit_pct'] = [60.0, 40.0, 25.0, 35.0, 10.0, 10.0, 10.0, 1.0, 1.0]

raw_breeds = [
    ('สายพันธุ์เชิงพาณิชย์', 'ไฮไลน์ บราวน์', 'Hy-Line Brown'), 
    ('สายพันธุ์เชิงพาณิชย์', 'โลห์มันน์ บราวน์', 'Lohmann Brown'), 
    ('สายพันธุ์เชิงพาณิชย์', 'ไอเอสเอ บราวน์', 'ISA Brown')
]
df_breeds_raw = pd.DataFrame(raw_breeds, columns=['category', 'name_th', 'name_en'])
df_breeds_raw['display_name'] = df_breeds_raw['name_th'] + " (" + df_breeds_raw['name_en'] + ")"

list_groups = sorted(df_breeds_raw['category'].unique().tolist())
list_stages = [
    "ช่วงอายุ แรกเกิด-6 สัปดาห์ (Starter 0-6 wk)",
    "ช่วงอายุ 6-12 สัปดาห์ (Grower 6-12 wk)",
    "ระยะไก่ไข่ให้ผลผลิต (Laying Period)"
]

if "calculated" not in st.session_state:
    st.session_state.calculated = False
    st.session_state.df_result = None
    st.session_state.total_cost_100kg = 0.0

def reset_calculation():
    st.session_state.calculated = False

# ==========================================
# 5. AUTHENTICATION INTERFACE (FIXED LAYOUT)
# ==========================================
if st.session_state.user is None:
    
    st.markdown('<div class="app-main-title">Smart Layer Feed</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-sub-title">ระบบคำนวณสูตรอาหารไก่ไข่อัจฉริยะ</div>', unsafe_allow_html=True)
    
    _, center_col, _ = st.columns([1, 1.2, 1])
    
    with center_col:
        # ------------------------------------------
        # 🗂️ หน้าเข้าสู่ระบบ (LOGIN)
        # ------------------------------------------
        if st.session_state.auth_page == "login":
            st.markdown(
                """
                <div class="auth-container">
                    <div class="avatar-container"><span>🥚</span></div>
                    <div style="color:#555555; font-size:15px; margin-bottom:20px; font-weight:500;">
                        ลงชื่อเข้าใช้ระบบเพื่อจัดการสูตรอาหารฟาร์ม
                    </div>
                """, 
                unsafe_allow_html=True
            )
            
            login_email = st.text_input("ชื่อผู้ใช้งาน", placeholder="ชื่อผู้ใช้งาน หรือ อีเมลฟาร์ม", key="input_login_email", label_visibility="collapsed")
            login_pass = st.text_input("รหัสผ่าน", placeholder="รหัสผ่าน", type="password", key="input_login_pass", label_visibility="collapsed")
            
            if st.button("ลงชื่อเข้าสู่ระบบฟาร์ม", use_container_width=True):
                try:
                    response = supabase.auth.sign_in_with_password({"email": login_email, "password": login_pass})
                    st.session_state.user = response.user
                    st.rerun()
                except Exception:
                    st.error("❌ ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
                    
            st.markdown("</div>", unsafe_allow_html=True) # ปิดกล่องขาวด้านบน
            
            # ปุ่มสลับลิ้งค์ใต้กล่องขาว (จัดรูปแบบให้อยู่กึ่งกลาง ไม่แตกแถว)
            st.markdown('<div class="footer-links">', unsafe_allow_html=True)
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                if st.button("ลืมรหัสผ่าน?", key="btn_go_forgot"):
                    st.session_state.auth_page = "forgot"
                    st.rerun()
            with f_col2:
                if st.button("สมัครสมาชิกฟาร์มใหม่", key="btn_go_reg"):
                    st.session_state.auth_page = "register"
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # ------------------------------------------
        # 🗂️ หน้าสมัครสมาชิก (REGISTER)
        # ------------------------------------------
        elif st.session_state.auth_page == "register":
            st.markdown(
                """
                <div class="auth-container">
                    <div class="avatar-container"><span>🐔</span></div>
                    <div style="color:#243b55; font-size:18px; margin-bottom:20px; font-weight:bold;">
                        ลงทะเบียนเปิดบัญชีฟาร์มใหม่
                    </div>
                """, 
                unsafe_allow_html=True
            )
            
            reg_fn = st.text_input("ชื่อจริง", placeholder="ชื่อจริงผู้ดูแล", key="reg_fn", label_visibility="collapsed")
            reg_ln = st.text_input("นามสกุล", placeholder="นามสกุล", key="reg_ln", label_visibility="collapsed")
            reg_email = st.text_input("อีเมล", placeholder="ที่อยู่อีเมลสำหรับฟาร์ม", key="reg_email", label_visibility="collapsed")
            reg_password = st.text_input("รหัสผ่าน", placeholder="ตั้งรหัสผ่านใหม่ (8 ตัวขึ้นไป)", type="password", key="reg_password", label_visibility="collapsed")
            farm_name = st.text_input("ชื่อฟาร์ม", placeholder="ชื่อฟาร์มไก่ไข่ของคุณ", key="reg_farm", label_visibility="collapsed")
            
            if reg_password:
                is_valid, msg = is_password_strong(reg_password)
                if is_valid: st.success(f"🟢 {msg}")
                else: st.warning(f"🟡 {msg}")
            
            if st.button("ลงทะเบียนบัญชีฟาร์ม", use_container_width=True):
                is_valid, msg = is_password_strong(reg_password)
                if not (reg_fn and reg_email and reg_password and farm_name):
                    st.error("❌ กรุณากรอกข้อมูลให้ครบถ้วน")
                elif not is_valid:
                    st.error(f"❌ {msg}")
                else:
                    try:
                        supabase.auth.sign_up({
                            "email": reg_email, "password": reg_password,
                            "options": {"data": {"first_name": reg_fn, "last_name": reg_ln, "farm_name": farm_name}}
                        })
                        st.success("📩 ระบบส่งอีเมลยืนยันแล้ว! กรุณาตรวจสอบกล่องข้อความของคุณ")
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {str(e)}")
                        
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown('<div class="footer-links">', unsafe_allow_html=True)
            if st.button("⬅️ กลับไปยังหน้าเข้าสู่ระบบ", key="back_from_reg"):
                st.session_state.auth_page = "login"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # ------------------------------------------
        # 🗂️ หน้าลืมรหัสผ่าน (FORGOT PASSWORD)
        # ------------------------------------------
        elif st.session_state.auth_page == "forgot":
            st.markdown(
                """
                <div class="auth-container">
                    <div class="avatar-container"><span>🔑</span></div>
                    <div style="color:#243b55; font-size:18px; margin-bottom:15px; font-weight:bold;">
                        กู้คืนรหัสผ่านฟาร์ม
                    </div>
                    <p style="color:#666; font-size:14px; margin-bottom:20px;">ระบบจะส่งลิงก์ตั้งรหัสผ่านใหม่ไปที่อีเมลของคุณ</p>
                """, 
                unsafe_allow_html=True
            )
            
            reset_email = st.text_input("อีเมล", placeholder="กรอกอีเมลฟาร์มที่ใช้ลงทะเบียน", key="forgot_email", label_visibility="collapsed")
            
            if st.button("ส่งลิงก์รีเซ็ตรหัสผ่าน", use_container_width=True):
                if reset_email:
                    try:
                        supabase.auth.reset_password_for_email(reset_email)
                        st.success("📩 ลิงก์กู้คืนส่งไปยังอีเมลเรียบร้อยแล้ว!")
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {str(e)}")
                else:
                    st.error("❌ กรุณากรอกอีเมล")
                    
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown('<div class="footer-links">', unsafe_allow_html=True)
            if st.button("⬅️ กลับไปยังหน้าเข้าสู่ระบบ", key="back_from_forgot"):
                st.session_state.auth_page = "login"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 6. MAIN SYSTEM DASHBOARD (เมื่อเข้าสู่ระบบสำเร็จ)
# ==========================================
else:
    user_info = st.session_state.user.user_metadata
    user_name = user_info.get("first_name", "ผู้เลี้ยง")
    farm_title = user_info.get("farm_name", "สมาร์ทฟาร์ม")
    
    st.markdown("<style>h1, h2, h3, h4, h5, h6, p, label { color: #ffffff !important; }</style>", unsafe_allow_html=True)
    
    header_col1, header_col2 = st.columns([8, 2])
    with header_col1:
        st.title(f"🥚 ระบบคำนวณสารอาหารอัจฉริยะ - {farm_title}")
        st.subheader(f"👋 ยินดีต้อนรับคุณ {user_name} (ผู้จัดการข้อมูลสูตรอาหาร)")
    with header_col2:
        st.write("")
        if st.button("🔒 ออกจากระบบ"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

    st.markdown("---")
    st.markdown("### 📋 แผงตั้งค่าสารอาหารตามช่วงอายุและสายพันธุ์ไก่ไข่")
    
    input_col1, input_col2 = st.columns(2, gap="large")
    with input_col1:
        st.markdown("##### 🐔 ข้อมูลฝูงไก่เป้าหมาย")
        selected_group = st.selectbox("เลือกกลุ่มสายพันธุ์ไก่ไข่", list_groups, index=0, on_change=reset_calculation)
        filtered_breeds = sorted(df_breeds_raw[df_breeds_raw['category'] == selected_group]['display_name'].tolist())
        selected_breed = st.selectbox("สายพันธุ์จำเพาะ", filtered_breeds, index=0, on_change=reset_calculation)
        selected_stage = st.selectbox("ช่วงอายุ / ระยะการให้ผลผลิต", list_stages, index=0, on_change=reset_calculation)
        
        st.info("💡 **เกณฑ์โภชนาการแนะนำช่วงอายุแรกเกิด:**\n"
                "- โปรตีน (Protein): ไม่ต่ำกว่า **20.0%**\n"
                "- พลังงานใช้ประโยชน์ได้ (ME): ไม่ต่ำกว่า **2,900 kcal/กก.**")

    with input_col2:
        st.markdown("##### 💰 ข้อมูลการเลี้ยงและราคาเป้าหมาย")
        num_chickens = st.number_input("จำนวนไก่ไข่ทั้งหมดในโรงเรือน (ตัว)", min_value=1, value=500, on_change=reset_calculation)
        feed_rate = st.slider("เป้าหมายปริมาณอาหารเฉลี่ยต่อตัว (กรัม/วัน)", min_value=50, max_value=150, value=115, on_change=reset_calculation)
        egg_price = st.number_input("ราคาไข่ไก่ท้องตลาดเฉลี่ยคาดหวัง (บาท/ฟอง)", min_value=0.0, value=4.10, step=0.1, on_change=reset_calculation)
        laying_rate = st.slider("อัตราการออกไข่ของฝูงเป้าหมาย (%)", min_value=0, max_value=100, value=85, on_change=reset_calculation)

    st.markdown("##")

    # ส่วนประมวลผลโมเดล Linear Programming ด้วย PuLP
    if st.button("🚀 เริ่มคำนวณและประมวลผลสูตรอาหารความคุ้มค่าสูงสุด", use_container_width=True, type="primary"):
        if not df_ingredients.empty:
            REQ_PROTEIN, REQ_ME = 18.0, 2800.0  # ปรับเกณฑ์จำลองโภชนาการขั้นต่ำให้เหมาะสม
            
            prob = pulp.LpProblem("Feed_Optimization", pulp.LpMinimize)
            ingredients_list = df_ingredients['name'].tolist()
            vars_dict = {name: pulp.LpVariable(f"Ing_{i}", lowBound=0) for i, name in enumerate(ingredients_list)}
            
            # Objective: หาต้นทุนที่ต่ำที่สุด
            prob += pulp.lpSum([vars_dict[row['name']] * row['price_per_kg'] for _, row in df_ingredients.iterrows()])
            prob += pulp.lpSum([vars_dict[i] for i in ingredients_list]) == 100.0
            
            for _, row in df_ingredients.iterrows():
                prob += vars_dict[row['name']] <= row['max_limit_pct']
            
            prob += pulp.lpSum([vars_dict[row['name']] * row['protein_pct'] for _, row in df_ingredients.iterrows()]) >= (REQ_PROTEIN * 100)
            prob += pulp.lpSum([vars_dict[row['name']] * row['me_kcal_per_kg'] for _, row in df_ingredients.iterrows()]) >= (REQ_ME * 100)
            
            prob.solve(pulp.PULP_CBC_CMD(msg=False))
            
            if pulp.LpStatus[prob.status] == "Optimal":
                st.session_state.calculated = True
                st.session_state.total_cost_100kg = pulp.value(prob.objective)
                
                result_list = []
                for _, row in df_ingredients.iterrows():
                    w = vars_dict[row['name']].varValue
                    if w and w > 0.01:
                        result_list.append({
                            "วัตถุดิบอาหาร": row['name'], 
                            "สัดส่วน (%)": round(w, 2), 
                            "ปริมาณที่ใช้ (กก./100กก.)": round(w, 2),
                            "ราคา (บาท)": round(w * row['price_per_kg'], 2)
                        })
                
                st.session_state.df_result = pd.DataFrame(result_list)
                st.success("🎉 ล็อกสัดส่วนและวิเคราะห์สูตรอาหารเรียบร้อยแล้ว!")
            else:
                st.error("❌ ไม่สามารถคำนวณสูตรอาหารตามเกณฑ์โภชนาการนี้ได้ กรุณาปรับเปลี่ยนวัตถุดิบ")

    st.markdown("---")
    st.markdown("### 📊 รายงานผลลัพธ์และอัตรากำไรของฟาร์ม")

    if st.session_state.calculated and st.session_state.df_result is not None:
        total_feed_day_kg = (num_chickens * feed_rate) / 1000
        cost_per_day = total_feed_day_kg * (st.session_state.total_cost_100kg / 100)
        expected_eggs_day = num_chickens * (laying_rate / 100)
        revenue_per_day = expected_eggs_day * egg_price
        net_profit_per_day = revenue_per_day - cost_per_day

        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric(label="📉 ต้นทุนค่าอาหาร / วัน", value=f"{cost_per_day:,.2f} ฿")
        with m2: st.metric(label="📈 รายได้รวมไข่ไก่ / วัน", value=f"{revenue_per_day:,.2f} ฿")
        with m3: st.metric(label="🏆 กำไรสุทธิประเมิน / วัน", value=f"{net_profit_per_day:,.2f} ฿")
        with m4: st.metric(label="💰 ต้นทุนอาหารเฉลี่ย (ต่อกก.)", value=f"{st.session_state.total_cost_100kg / 100:.2f} ฿")

        st.markdown("##")
        report_left, report_right = st.columns([1.1, 0.9], gap="large")
        
        with report_left:
            st.markdown("##### 🍩 แผนภูมิสัดส่วนสูตรอาหาร")
            fig = px.pie(st.session_state.df_result, values='สัดส่วน (%)', names='วัตถุดิบอาหาร', hole=0.45)
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320, font=dict(color="black"), paper_bgcolor='rgba(255,255,255,0.95)')
            st.plotly_chart(fig, use_container_width=True)

        with report_right:
            st.markdown("##### 📋 ตารางจัดซื้อและจัดสรรวัตถุดิบ (ผสมต่องวด 100 กิโลกรัม)")
            st.dataframe(st.session_state.df_result, use_container_width=True, hide_index=True, height=320)
    else:
        st.info("💡 **ระบบพร้อมคำนวณ:** ตั้งค่าพารามิเตอร์ของฟาร์มด้านบน จากนั้นคลิกปุ่มประมวลผลเพื่อดูผลลัพธ์สูตรอาหารที่นี่ได้ทันทีครับ")
