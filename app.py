import streamlit as pd
import pandas as pd
import datetime
import io
from pulp import *
import plotly.express as px

# 1. การตั้งค่าหน้าจอและหน้าตาเว็บ (Page Configuration)
st.set_page_config(
    page_title="ระบบบริหารจัดการสูตรอาหารและตัวชี้วัดฟาร์มไก่ไข่อัจฉริยะ",
    page_icon="🐓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ปรับแต่ง CSS เพื่อความสวยงาม สไตล์ธีมมืด (Dark Mode Farm)
st.markdown("""
    <style>
    .main { background-color: #0f172a; color: #f8fafc; }
    .farmer-card {
        background-color: #1e293b;
        padding: 20,px;
        border-radius: 12px;
        border: 1px solid #334155;
        margin-bottom: 20px;
    }
    .big-metric-value { font-size: 28px; font-weight: bold; color: #38bdf8; }
    .big-metric-label { font-size: 14px; color: #94a3b8; }
    </style>
""", unsafe_allow_html=True)

# 2. การเชื่อมต่อฐานข้อมูลอย่างปลอดภัย (ดึงค่าจาก Streamlit Secrets แทนการอัปโหลดไฟล์)
try:
    # แก้ปัญหาความปลอดภัย: ดึงข้อมูลผ่าน st.secrets ของระบบ Cloud
    from supabase import create_client, Client
    
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error(f"❌ ระบบความปลอดภัย: ไม่พบการตั้งค่าโครงสร้างคีย์เชื่อมต่อฐานข้อมูลในระบบ Cloud (Secrets Error): {e}")
    st.info("💡 คำแนะนำ: กรุณานำค่าใน secrets.toml ไปใส่ในหน้าต่าง Settings -> Secrets บน Streamlit Cloud")
    st.stop()

# 3. จัดเตรียม Session State สำหรับเก็บข้อมูลภายในแอปพลิเคชัน
if "user_email" not in st.session_state:
    st.session_state.user_email = "owner@smartpoultry.com"  # อีเมลสมมุติสำหรับผูกโครงสร้างข้อมูล

# โครงสร้างสารอาหารเริ่มต้น (Master Data) ของวัตถุดิบ
if "db_ingredients" not in st.session_state:
    st.session_state.db_ingredients = {
        "ข้าวโพดบด": {"price": 12.5, "protein": 8.0, "me": 3370, "calcium": 0.02, "phos": 0.25},
        "รำละเอียด": {"price": 10.0, "protein": 12.0, "me": 2860, "calcium": 0.04, "phos": 1.35},
        "กากถั่วเหลือง (44%)": {"price": 22.0, "protein": 44.0, "me": 2240, "calcium": 0.29, "phos": 0.65},
        "ปลาป่น (60%)": {"price": 35.0, "protein": 60.0, "me": 2800, "calcium": 5.00, "phos": 2.80},
        "เปลือกหอยบด": {"price": 5.0, "protein": 0.0, "me": 0, "calcium": 38.00, "phos": 0.00},
        "ไดแคลเซียม (DCP)": {"price": 28.0, "protein": 0.0, "me": 0, "calcium": 21.00, "phos": 18.00},
        "กรดอะมิโนรวม/พรีมิกซ์": {"price": 85.0, "protein": 50.0, "me": 0, "calcium": 0.00, "phos": 0.00},
        "น้ำมันปาล์ม": {"price": 42.0, "protein": 0.0, "me": 8800, "calcium": 0.00, "phos": 0.00}
    }

# คีย์ระบบสารอาหารที่รองรับแบบสากล
if "db_nutrient_keys" not in st.session_state:
    st.session_state.db_nutrient_keys = {
        "protein": {"label": "โปรตีนดิบ (% Crude Protein)", "unit": "%"},
        "me": {"label": "พลังงานใช้ประโยชน์ได้ (ME)", "unit": "kcal/kg"},
        "calcium": {"label": "แคลเซียม (% Calcium)", "unit": "%"},
        "phos": {"label": "ฟอสฟอรัสที่เป็นประโยชน์ (% Av. Phosphorus)", "unit": "%"}
    }

if "current_weights" not in st.session_state:
    st.session_state.current_weights = {k: 0.0 for k in st.session_state.db_ingredients.keys()}

# 4. ฟังก์ชัน AI Solver (Linear Programming) คำนวณสูตรอาหารต้นทุนต่ำสุด
def run_ai_solver(req_p, req_m, req_c, req_ph, ca_buffer=0.5, p_buffer=0.2):
    prob = LpProblem("Poultry_Feed_Optimization", LpMinimize)
    
    # สร้างตัวแปรการคำนวณตามรายชื่อวัตถุดิบ
    ing_names = list(st.session_state.db_ingredients.keys())
    vars_dict = LpVariable.dicts("Ing", ing_names, lowBound=0.0, upBound=100.0, cat="Continuous")
    
    # Objective Function: ต้นทุนรวมต้องต่ำที่สุด
    prob += lpSum([vars_dict[i] * float(st.session_state.db_ingredients[i]["price"]) for i in ing_names])
    
    # Constraints เงื่อนไขสัดส่วนโภชนาการ
    prob += lpSum([vars_dict[i] for i in ing_names]) == 100.0, "Total_Percentage"
    prob += lpSum([vars_dict[i] * float(st.session_state.db_ingredients[i]["protein"]) for i in ing_names]) >= req_p, "Min_Protein"
    prob += lpSum([vars_dict[i] * float(st.session_state.db_ingredients[i]["me"]) for i in ing_names]) >= req_m, "Min_ME"
    
    # ช่วงควบคุมแคลเซียมและฟอสฟอรัสเพื่อป้องกันไข่เปลือกบางหรือไตวาย
    prob += lpSum([vars_dict[i] * float(st.session_state.db_ingredients[i]["calcium"]) for i in ing_names]) >= (req_c - ca_buffer), "Min_Ca"
    prob += lpSum([vars_dict[i] * float(st.session_state.db_ingredients[i]["calcium"]) for i in ing_names]) <= (req_c + ca_buffer), "Max_Ca"
    prob += lpSum([vars_dict[i] * float(st.session_state.db_ingredients[i]["phos"]) for i in ing_names]) >= (req_ph - p_buffer), "Min_Phos"
    
    # ข้อจำกัดพฤติกรรมการกินวัตถุดิบหนาแน่นเกินไป (Inclusion Limits)
    if "น้ำมันปาล์ม" in vars_dict:
        prob += vars_dict["น้ำมันปาล'ม"] <= 4.0
    
    status = prob.solve(PULP_CBC_CMD(msg=False))
    
    if LpStatus[status] == "Optimal":
        return {i: max(0.0, round(vars_dict[i].varValue, 2)) for i in ing_names}
    else:
        # กรณีหาคำตอบที่ลงตัวไม่ได้ ให้คืนค่าพื้นฐานกลับไปก่อน
        return {i: 100.0 / len(ing_names) for i in ing_names}
# =============================================================================
# ส่วนที่ 2: โครงสร้างเมนู และระบบควบคุมมาตรฐานสายพันธุ์ (Breed Criteria & Layout)
# =============================================================================

# 1. แถบควบคุมด้านข้าง (Sidebar) สำหรับเลือกสายพันธุ์และระยะการเจริญเติบโต
with st.sidebar:
    st.markdown("## 🐔 ตั้งค่าสายพันธุ์และเกณฑ์")
    
    # ฐานข้อมูลมาตรฐานความต้องการโภชนาการตามสายพันธุ์หลักในไทย
    breed_db = {
        "Isa Brown (อีซ่า บราวน์)": {
            "ไข่ระยะที่ 1 (เริ่มไข่ - 45 สัปดาห์)": {"protein": 17.5, "me": 2750, "calcium": 4.10, "phos": 0.42, "feed": 115.0},
            "ไข่ระยะที่ 2 (46 - 65 สัปดาห์)": {"protein": 16.5, "me": 2700, "calcium": 4.30, "phos": 0.38, "feed": 118.0},
            "ไข่ระยะที่ 3 (66 สัปดาห์ขึ้นไป)": {"protein": 15.5, "me": 2650, "calcium": 4.50, "phos": 0.35, "feed": 120.0}
        },
        "Hy-Line Brown (ไฮ-ไลน์ บราวน์)": {
            "ไข่ระยะที่ 1 (เริ่มไข่ - 40 สัปดาห์)": {"protein": 17.8, "me": 2770, "calcium": 4.20, "phos": 0.45, "feed": 112.0},
            "ไข่ระยะที่ 2 (41 - 60 สัปดาห์)": {"protein": 16.8, "me": 2720, "calcium": 4.40, "phos": 0.40, "feed": 115.0},
            "ไข่ระยะที่ 3 (61 สัปดาห์ขึ้นไป)": {"protein": 15.8, "me": 2680, "calcium": 4.60, "phos": 0.36, "feed": 118.0}
        },
        "สูตรกำหนดเอง (Custom Layout)": {
            "ระยะกำหนดเอง": {"protein": 17.0, "me": 2750, "calcium": 4.20, "phos": 0.40, "feed": 115.0}
        }
    }
    
    selected_b_name = st.selectbox("เลือกสายพันธุ์ไก่ไข่:", list(breed_db.keys()))
    select_stage_crud = st.selectbox("เลือกระยะการให้ไข่:", list(breed_db[selected_b_name].keys()))
    
    # ดึงค่าเกณฑ์มาตรฐานมาเป็นตัวแปรตั้งต้น
    base_req = breed_db[selected_b_name][select_stage_crud]
    st.session_state['current_breed_default_feed'] = base_req["feed"]
    
    st.markdown("---")
    st.markdown("### 🛠️ ปรับค่าเป้าหมายโภชนาการโจทย์")
    edit_p = st.number_input("โปรตีนเป้าหมาย (% CP):", 10.0, 30.0, float(base_req["protein"]), step=0.1)
    edit_m = st.number_input("พลังงานเป้าหมาย (ME kcal/kg):", 1500, 4000, int(base_req["me"]), step=50)
    edit_c = st.number_input("แแคลเซียมเป้าหมาย (% Ca):", 1.0, 6.0, float(base_req["calcium"]), step=0.05)
    edit_ph = st.number_input("ฟอสฟอรัสเป้าหมาย (% P):", 0.1, 2.0, float(base_req["phos"]), step=0.02)
    
    # ปุ่มกดสั่งให้ AI Solver คำนวณหาจุดคุ้มทุนอัตโนมัติ
    if st.button("🤖 สั่ง AI คำนวณสูตรอาหารต้นทุนต่ำสุด", use_container_width=True):
        st.session_state.current_weights = run_ai_solver(edit_p, edit_m, edit_c, edit_ph)
        st.success("🤖 AI จัดสัดส่วนอาหารให้เรียบร้อย!")

# 2. ส่วนโครงสร้างหน้าจอหลักแบ่งเป็น 3 แท็บ (Main Tabs Layout)
page_tabs = st.tabs([
    "🥣 1. ปรับปรุงสูตรอาหาร & สรุปโภชนาการ", 
    "☀️ 2. บันทึกผลผลิตประจำวัน & Cashflow", 
    "📊 3. ใบสั่งงานผสมอาหารสำหรับคนงาน"
])

# เข้าสู่เนื้อหาแท็บที่ 1: ส่วนการประมวลผลคำนวณสารอาหารจริงในสูตรปัจจุบัน
with page_tabs[0]:
    st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
    st.markdown(f"<h2>🌾 ระบบคำนวณและปรับสัดส่วนอาหารป้อนฟาร์ม ({selected_b_name})</h2>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # ตัวแปรสำหรับรวบรวมค่าน้ำหนักรวม และค่าใช้จ่ายสุทธิ
    divisor = float(sum(st.session_state.current_weights.values()))
    if divisor < 0.1: 
        divisor = 100.0  # ระบบป้องกันการหารด้วยศูนย์ (Zero Division Protection)
        
    net_cost = 0.0
    act_nut = {k: 0.0 for k in st.session_state.db_nutrient_keys.keys()}
    
    # ลูปสะสมข้อมูลสารอาหารที่ได้จริงและต้นทุนตามน้ำหนักเปอร์เซ็นต์
    for name, w_val in st.session_state.current_weights.items():
        ratio = w_val / divisor
        if name in st.session_state.db_ingredients:
            # คำนวณต้นทุนต่อกิโลกรัมรวม
            net_cost += ratio * float(st.session_state.db_ingredients[name]["price"])
            
            # ลูปดึงค่าสารอาหารที่แอดมินหรือระบบตั้งไว้แบบ Dynamic
            for nut_key in st.session_state.db_nutrient_keys.keys():
                act_nut[nut_key] += ratio * float(st.session_state.db_ingredients[name].get(nut_key, 0.0))
# =============================================================================
    # ส่วนที่ 3: แถบปรับสัดส่วนอาหารแบบ 2 คอลัมน์ย่อย และตารางผลลัพธ์
    # =============================================================================
    col_left, col_right = st.columns([1.1, 0.9])
    
    with col_left:
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        cl_title, cl_reset = st.columns([6, 4])
        with cl_title:
            st.markdown("### 🥣 แถบปรับสัดส่วนวัตถุดิบ (%)")
        with cl_reset:
            if st.button("🔄 รีเซ็ตค่าใหม่ทั้งหมด", use_container_width=True):
                st.session_state.current_weights = run_ai_solver(edit_p, edit_m, edit_c, edit_ph)
                st.rerun()
        
        temp_weights = {}
        running_total = 0.0
        
        # เกณฑ์จำกัดการใช้วัตถุดิบไม่ให้เกินมาตรฐาน (Inclusion Limits) ป้องกันไก่ท้องเสีย/ไข่ลด
        inclusion_limits = {
            "กากเบียร์แห้ง": 10.0, "กากน้ำตาล": 5.0, "น้ำมันปาล์ม": 4.0, 
            "น้ำมันถั่วเหลือง": 4.0, "ข้าวนก": 15.0, "กากดีดีจีเอส": 15.0, "DDGS": 15.0
        }
        
        ing_keys = list(st.session_state.db_ingredients.keys())
        ing_col1, ing_col2 = st.columns(2)
        
        # ลูปสร้างสไลเดอร์แบ่งเป็น 2 ฝั่ง ซ้าย-ขวา เพื่อความประหยัดพื้นที่และอ่านง่าย
        for idx, name in enumerate(ing_keys):
            d = st.session_state.db_ingredients[name]
            saved_w = float(st.session_state.current_weights.get(name, 0.0))
            saved_w = max(0.0, min(100.0, saved_w))
            
            target_col = ing_col1 if idx % 2 == 0 else ing_col2
            with target_col:
                user_val = st.slider(
                    f"🌽 {name} ({d['price']} บ./กก.)", 
                    min_value=0.0, max_value=100.0, value=saved_w, step=0.1, key=f"sld_user_{name}"
                )
                # ตรวจสอบระบบเตือนภัยข้อจำกัดโภชนาการสัตว์
                if name in inclusion_limits and user_val > inclusion_limits[name]:
                    st.markdown(f"<p style='color:#f87171; font-size:14px; font-weight:bold; margin:-8px 0px 10px 0px;'>⚠️ ห้ามเกิน {inclusion_limits[name]}% ไก่จะท้องเสีย</p>", unsafe_allow_html=True)
            
            temp_weights[name] = user_val
            running_total += user_val
        
        st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
        
        # ตรวจสอบว่าสัดส่วนผสมรวมกันได้ 100% หรือไม่
        if abs(running_total - 100.0) > 0.1:
            st.markdown(f"<div style='background-color:#991b1b; padding:15px; border-radius:8px; font-size:18px; font-weight:bold; text-align:center;'>⚠️ สัดส่วนอาหารรวมได้: {running_total:.1f}% (กรุณาปรับให้ครบ 100%)</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='background-color:#065f46; padding:15px; border-radius:8px; font-size:18px; font-weight:bold; text-align:center;'>🟢 ส่วนผสมครบถ้วนสมบูรณ์ 100%</div>", unsafe_allow_html=True)
        
        st.session_state.current_weights = temp_weights
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("### 🧪 ผลลัพธ์โภชนาการจริงในสูตร")
        
        # สร้างตารางเปรียบเทียบค่าที่คำนวณได้จริงกับค่าเป้าหมายที่ตั้งไว้
        comparison_table = [
            {"โภชนาการสำคัญ": "โปรตีนดิบ (% CP)", "เป้าหมาย": f"{edit_p:.2f} %", "ได้จริงในสูตร": f"{act_nut.get('protein', 0.0):.2f} %"},
            {"โภชนาการสำคัญ": "พลังงานใช้ประโยชน์ (ME)", "เป้าหมาย": f"{edit_m:.0f} kcal", "ได้จริงในสูตร": f"{act_nut.get('me', 0.0):.0f} kcal"},
            {"โภชนาการสำคัญ": "แคลเซียม (% Ca)", "เป้าหมาย": f"{edit_c:.2f} %", "ได้จริงในสูตร": f"{act_nut.get('calcium', 0.0):.2f} %"},
            {"โภชนาการสำคัญ": "ฟอสฟอรัส (% P)", "เป้าหมาย": f"{edit_ph:.2f} %", "ได้จริงในสูตร": f"{act_nut.get('phos', 0.0):.2f} %"},
        ]
        st.dataframe(pd.DataFrame(comparison_table), use_container_width=True, hide_index=True)
        
        # แสดงกล่องสรุปต้นทุนเฉลี่ยต่อกิโลกรัม
        st.markdown(f"<div style='background-color:#1e293b; padding:15px; border-radius:10px; border:2px solid #38bdf8; text-align:center; font-size:24px; font-weight:bold; margin: 15px 0;'>💰 ต้นทุนค่าอาหารสูตรนี้: {net_cost:.2f} บาท/กก.</div>", unsafe_allow_html=True)
        
        # ฟังก์ชันบันทึกข้อมูลสูตรอาหารลงในหน่วยความจำชั่วคราว
        breed_display_name = selected_b_name.split()[-1] if selected_b_name else "สูตรผสมเอง"
        save_name_input = st.text_input("💾 ตั้งชื่อเล่นสูตรอาหารเพื่อกดเซฟ:", value=f"สูตร {breed_display_name} {net_cost:.1f} บาท")
        
        if st.button("📥 ยืนยันกดบันทึกสูตรอาหารลงคลัง", use_container_width=True):
            if "saved_formulas" not in st.session_state:
                st.session_state.saved_formulas = []
            st.session_state.saved_formulas.append({
                "date": str(datetime.date.today()), 
                "name": save_name_input, 
                "cost": round(net_cost, 2), 
                "breed": selected_b_name, 
                "stage": select_stage_crud,
                "protein": round(act_nut.get("protein", 0.0), 2), 
                "me": round(act_nut.get("me", 0.0), 0), 
                "calcium": round(act_nut.get("calcium", 0.0), 2), 
                "weights": st.session_state.current_weights.copy()
            })
            st.success("บันทึกสูตรเรียบร้อย!")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
# =============================================================================
    # TAB 2: DAILY LOG & CASHFLOW (บันทึกข้อมูลและคำนวณตัวชี้วัดประสิทธิภาพฟาร์ม)
    # =============================================================================
    with page_tabs[1]:
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("<h2>☀️ บันทึกตัวชี้วัดฟาร์ม & รายรับ-รายจ่ายประจำวัน</h2>", unsafe_allow_html=True)
        st.markdown("<div style='border-bottom: 2px solid #475569; margin:15px 0;'></div>", unsafe_allow_html=True)
        
        # ฟังก์ชันดึงประวัติเก่ามาสวมสิทธิ์เพื่อความรวดเร็วในการพิมพ์
        if st.session_state.get("daily_logs"):
            if st.button("📋 ดึงข้อมูลจากประวัติล่าสุด (ไม่ต้องพิมพ์ใหม่หมด)", use_container_width=True):
                last_log = st.session_state.daily_logs[-1]
                birds_val = last_log.get("bird_count", last_log.get("จำนวนไก่ (ตัว)", 5000))
                revenue_val = last_log.get("total_revenue", last_log.get("รายได้ขายไข่ (บาท)", 0))
                eggs_val = last_log.get("collected_eggs", last_log.get("ไข่ที่เก็บได้ (ฟอง)", 1))
                
                st.session_state["shortcut_birds"] = birds_val
                st.session_state["shortcut_price"] = revenue_val / eggs_val if eggs_val > 0 else 4.10
                st.success("ดึงข้อมูลเดิมเรียบร้อย! กรุณาตรวจสอบและอัปเดตจำนวนไข่ประจำวันนี้")

        log_col1, log_col2 = st.columns(2)
        with log_col1:
            st.markdown("#### 📝 ส่วนที่ 1: ข้อมูลฝูงไก่วันนี้")
            log_date = st.date_input("วันที่บันทึกข้อมูล:", datetime.date.today(), key="farm_log_date")
            flock_age_weeks = st.number_input("🐣 อายุฝูงไก่ปัจจุบัน (สัปดาห์):", min_value=1, max_value=100, value=25, step=1)
            
            default_birds = st.session_state.get("shortcut_birds", 5000)
            bird_count = st.number_input("จำนวนไก่ไข่ทั้งหมดในเล้าวันนี้ (ตัว):", min_value=1, value=int(default_birds), step=100)
            env_temp = st.slider("🌡️ อุณหภูมิสูงสุดในเล้าวันนี้ (°C):", 15.0, 45.0, 28.0, step=0.5, key="temp_slider")
            
            # ระบบคำนวณปริมาณอาหารที่ควรให้ตามเกณฑ์สายพันธุ์
            breed_default_feed = st.session_state.get('current_breed_default_feed', 115.0)
            recommended_feed = float(bird_count * breed_default_feed / 1000.0)
            st.markdown(f"<p style='color:#6366f1; font-size:16px; font-weight:bold; margin-bottom:-5px;'>💡 ปริมาณอาหารแนะนำตามสายพันธุ์: {recommended_feed:,.1f} กก.</p>", unsafe_allow_html=True)
            actual_feed_given_kg = st.number_input("🍽️ น้ำหนักอาหารที่ให้ไก่กินรวมวันนี้ (กิโลกรัม):", min_value=10.0, value=recommended_feed, step=10.0)
            
        with log_col2:
            st.markdown("#### 💰 ส่วนที่ 2: จำนวนไข่และราคาส่งวันนี้")
            collected_eggs = st.number_input("จำนวนฟองไข่ที่เก็บได้จริงวันนี้ (ฟอง):", min_value=0, value=4200)
            
            default_price = st.session_state.get("shortcut_price", 4.10)
            egg_sale_price = st.number_input("💵 ราคารับซื้อไข่หน้าฟาร์มวันนี้ (บาท/ฟอง):", min_value=1.0, value=float(default_price), step=0.1)
            dead_birds = st.number_input("จำนวนไก่ตาย/คัดทิ้งวันนี้ (ตัว):", min_value=0, value=2)
            avg_egg_weight_g = st.number_input("⚖️ น้ำหนักไข่เฉลี่ยวันนี้ (กรัม/ฟอง):", min_value=30.0, max_value=80.0, value=62.0, step=0.5)

        # --- ปฏิทินแจ้งเตือนงานรูทีนวัคซีนและแสงสว่างตามอายุไก่ ---
        st.markdown("<div style='background-color:#1e1b4b; padding:20px; border-radius:12px; border:2px solid #6366f1; margin: 20px 0;'>", unsafe_allow_html=True)
        st.markdown(f"### 📋 ปฏิทินเตือนงานสำคัญสำหรับไก่อายุ {flock_age_weeks} สัปดาห์:")
        if flock_age_weeks <= 3:
            st.markdown("<p style='color:#38bdf8; font-size:22px; font-weight:bold;'>• ต้องทำวัคซีนนิวคาสเซิล + หลอดลมอักเสบ และตรวจเช็กระบบไฟกก</p>", unsafe_allow_html=True)
        elif flock_age_weeks <= 8:
            st.markdown("<p style='color:#38bdf8; font-size:22px; font-weight:bold;'>• ต้องทำวัคซีนฝีดาษ และทำวัคซีนอหิวาต์ไก่รอบที่ 1</p>", unsafe_allow_html=True)
        elif flock_age_weeks <= 16:
            st.markdown("<p style='color:#38bdf8; font-size:22px; font-weight:bold;'>• ต้องถ่ายพยาธิไก่ก่อนย้ายเข้ากรงตับ และทำวัคซีนรวมก่อนเริ่มไข่</p>", unsafe_allow_html=True)
        elif flock_age_weeks <= 24:
            st.markdown("<p style='color:#fbbf24; font-size:22px; font-weight:bold;'>• ไก่เริ่มไข่แล้ว: [ระวัง] ห้ามลดแสงสว่างในเล้าเด็ดขาด! แสงต้องสม่ำเสมอ</p>", unsafe_allow_html=True)
        elif flock_age_weeks <= 60:
            st.markdown("<p style='color:#10b981; font-size:22px; font-weight:bold;'>• ช่วงไข่ดก: สุ่มเช็กความหนาเปลือกไข่ และล้างทำความสะอาดหัวนิปเปิ้ลน้ำทุกสัปดาห์</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p style='color:#f87171; font-size:22px; font-weight:bold;'>• ไก่แก่ท้ายชุด: ให้คนงานเสริมเปลือกหอยบดในรางช่วงเย็น ป้องกันไข่เปลือกบางแตกหัก</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
            
        st.markdown("<div style='border-bottom: 2px dashed #475569; margin:20px 0;'></div>", unsafe_allow_html=True)
        
        # สมการประมวลผลประสิทธิภาพสถิติวิเคราะห์เชิงลึก (FCR / % Hen-Day)
        total_revenue = collected_eggs * egg_sale_price
        total_feed_cost = actual_feed_given_kg * net_cost
        net_profit_day = total_revenue - total_feed_cost
        
        henday_pct = (collected_eggs / bird_count) * 100.0 if bird_count > 0 else 0.0
        total_egg_mass_kg = (collected_eggs * avg_egg_weight_g) / 1000.0
        fcr_ratio = actual_feed_given_kg / total_egg_mass_kg if total_egg_mass_kg > 0 else 0.0
        cost_per_egg = total_feed_cost / collected_eggs if collected_eggs > 0 else 0.0

        # ระบบแจ้งเตือนวิกฤตภัยเงียบในฟาร์ม (Smart Alerts)
        if henday_pct < 65.0 and henday_pct > 0:
            st.markdown(f"<div style='background-color:#7c2d12; padding:15px; border-radius:8px; font-size:18px; font-weight:bold; margin-bottom:15px;'>⚠️ เตือน: เปอร์เซ็นต์การไข่ต่ำกว่าเกณฑ์มาตรฐาน ({henday_pct:.1f}%) ตรวจเช็กพฤติกรรมการกินและสุ่มคัดไก่ป่วยด่วน</div>", unsafe_allow_html=True)
        if dead_birds > (bird_count * 0.001):
            st.markdown(f"<div style='background-color:#991b1b; padding:15px; border-radius:8px; font-size:18px; font-weight:bold; margin-bottom:15px;'>🚨 วิกฤต: วันนี้ไก่ตายผิดปกติ ({dead_birds} ตัว) สูงเกินเกณฑ์ ระวังสภาพอากาศร้อนจัดหรือโรคระบาดติดต่อ!</div>", unsafe_allow_html=True)
        if env_temp >= 32.0:
            st.error(f"🚨 เล้าร้อนจัด ({env_temp}°C) ไก่เสี่ยงช็อกตาย! คนงานต้องเปิดระบบพ่นหมอกและเร่งพัดลมทันที")

        st.markdown("### 📊 สรุปผลกำไรสุทธิและตัวชี้วัดวันนี้")
        profit_box_color = "#065f46" if net_profit_day >= 0 else "#991b1b"
        st.markdown(f"<div style='background-color:{profit_box_color}; padding:20px; border-radius:12px; text-align:center; font-size:26px; font-weight:bold; margin-bottom:20px;'>💸 เงินกำไรสุทธิประจำวัน (หักค่าอาหารแล้ว): {net_profit_day:,.2f} บาท</div>", unsafe_allow_html=True)

        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.markdown(f"<div style='background-color:#0f172a; padding:15px; border-radius:10px; border:1px solid #334155; text-align:center;'><span class='big-metric-label'>🥚 เปอร์เซ็นต์การไข่</span><br><span class='big-metric-value'>{henday_pct:.1f} %</span></div>", unsafe_allow_html=True)
        with m_col2:
            st.markdown(f"<div style='background-color:#0f172a; padding:15px; border-radius:10px; border:1px solid #334155; text-align:center;'><span class='big-metric-label'>🥣 อัตราแลกไข่ (FCR)</span><br><span class='big-metric-value'>{fcr_ratio:.2f}</span></div>", unsafe_allow_html=True)
        with m_col3:
            st.markdown(f"<div style='background-color:#0f172a; padding:15px; border-radius:10px; border:1px solid #334155; text-align:center;'><span class='big-metric-label'>🥚 ค่าอาหารต่อไข่ 1 ฟอง</span><br><span class='big-metric-value'>{cost_per_egg:.2f} บาท</span></div>", unsafe_allow_html=True)
            
        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
            
        # ปุ่มส่งข้อมูลยิงเข้าคลาวด์ฐานข้อมูล Supabase
        if st.button("💾 กดปุ่มนี้เพื่อบันทึกประวัติประจำวันลงระบบคลาวด์", use_container_width=True):
            log_payload = {
                "user_email": st.session_state.user_email,
                "log_date": str(log_date),
                "flock_age_weeks": int(flock_age_weeks),
                "bird_count": int(bird_count),
                "env_temp": float(env_temp),
                "actual_feed_given_kg": float(actual_feed_given_kg),
                "collected_eggs": int(collected_eggs),
                "total_revenue": round(total_revenue, 2),
                "total_feed_cost": round(total_feed_cost, 2),
                "net_profit_day": round(net_profit_day, 2),
                "henday_pct": round(henday_pct, 1),
                "fcr_ratio": round(fcr_ratio, 2)
            }
            try:
                supabase.table("daily_logs").insert(log_payload).execute()
                
                legacy_format = {
                    "วันที่": str(log_date), "อายุฝูง (สัปดาห์)": flock_age_weeks, "จำนวนไก่ (ตัว)": bird_count, "อุณหภูมิ (°C)": env_temp,
                    "อาหารที่กิน (KG)": actual_feed_given_kg, "ไข่ที่เก็บได้ (ฟอง)": collected_eggs, 
                    "รายได้ขายไข่ (บาท)": round(total_revenue, 2), "ต้นทุนอาหาร (บาท)": round(total_feed_cost, 2),
                    "กำไรสุทธิ (บาท)": round(net_profit_day, 2), "อัตราไข่ (%)": round(henday_pct, 1), "FCR": round(fcr_ratio, 2)
                }
                if "daily_logs" not in st.session_state:
                    st.session_state.daily_logs = []
                st.session_state.daily_logs.append(legacy_format)
                
                st.success("บันทึกข้อมูลลงฐานข้อมูลคลาวด์เรียบร้อย!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ ไม่สามารถเซฟลงระบบคลาวด์ได้: {e}")
            
        st.markdown("<div style='border-bottom: 2px dashed #475569; margin:25px 0;'></div>", unsafe_allow_html=True)
        st.markdown("### 📋 ตารางประวัติฟาร์มย้อนหลัง")
        if not st.session_state.get("daily_logs"):
            st.info("💡 ยังไม่มีข้อมูลย้อนหลังในเซสชันนี้")
        else:
            st.dataframe(pd.DataFrame(st.session_state.daily_logs), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
# =============================================================================
    # TAB 3: BATCH MIXER & LABELS (ระบบแปลงน้ำหนักถังผสม และใบสั่งงานคนงาน)
    # =============================================================================
    with page_tabs[2]:
        st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
        st.markdown("<h2>📊 ใบสั่งงานผสมอาหารสัตว์สำหรับคนงานหน้าเล้า</h2>", unsafe_allow_html=True)
        st.markdown("<div style='border-bottom: 2px solid #475569; margin:15px 0;'></div>", unsafe_allow_html=True)
        
        # ป้อนปริมาณน้ำหนักรวมที่ต้องการให้เครื่องจักรหรือคนงานผสมใน 1 รอบ (1 Batch)
        batch_size_kg = st.number_input("⚖️ กำหนดน้ำหนักรวมที่ต้องการผสมต่อรอบ (กิโลกรัม):", min_value=1.0, value=100.0, step=10.0)
        
        st.markdown(f"#### 📝 รายการวัตถุดิบที่ต้องชั่งตวง (สำหรับยอดผสมรวม {batch_size_kg:,} กก.)")
        
        # ลูปคำนวณสัดส่วนออกมาเป็นกิโลกรัมจริงตามขนาด Batch
        mixer_data = []
        line_msg_items = []
        
        divisor_m = float(sum(st.session_state.current_weights.values()))
        if divisor_m < 0.1: 
            divisor_m = 100.0
            
        for name, w_val in st.session_state.current_weights.items():
            if w_val > 0:
                calc_kg = (w_val / divisor_m) * batch_size_kg
                mixer_data.append({
                    "วัตถุดิบ": name,
                    "สัดส่วนเดิม (%)": f"{w_val:.2f} %",
                    "น้ำหนักที่ต้องชั่งจริง (กก.)": f"{calc_kg:.2f} กก.",
                    "สถานะคนงาน": "🔲 ยังไม่ได้ตัก"
                })
                line_msg_items.append(f"- {name}: {calc_kg:.2f} กก.")
                
        if not mixer_data:
            st.info("💡 ยังไม่มีวัตถุดิบในสูตรอาหารปัจจุบัน (กรุณาไปปรับสัดส่วนในแท็บที่ 1 ก่อน)")
        else:
            # แสดงตารางใบสั่งงานเพื่อให้คนงานดูและชั่งตามได้ทันที
            st.dataframe(pd.DataFrame(mixer_data), use_container_width=True, hide_index=True)
            
            # --- ฟังก์ชันพิเศษ: สรุปรายงานย่อสำหรับส่ง LINE ---
            st.markdown("### 📱 ระบบคัดลอกข้อความส่งกลุ่ม LINE คนงาน")
            
            line_text_summary = (
                f"📝 [ใบสั่งผสมอาหารประจำวันที่: {datetime.date.today().strftime('%d/%m/%Y')}]\n"
                f"🐔 สำหรับสายพันธุ์: {selected_b_name}\n"
                f"⚖️ ยอดผสมรวมต่อรอบ: {batch_size_kg:,} กิโลกรัม\n"
                f"-------------------------\n"
                + "\n".join(line_msg_items) + "\n"
                f"-------------------------\n"
                f"💰 ต้นทุนเฉลี่ย: {net_cost:.2f} บาท/กก.\n"
                f"⚠️ รบกวนชั่งน้ำหนักให้แม่นยำ และคลุกเคล้าให้เข้ากันก่อนตักแจกไก่นะครับ!"
            )
            
            # กล่อง Text Area สำหรับให้คลิก Copy ได้สะดวกบนมือถือ
            st.text_area("📋 ก๊อปปี้ข้อความในกล่องนี้ไปวางในแอป LINE ได้เลย:", value=line_text_summary, height=220)
            
            # ปุ่มดาวน์โหลดใบสั่งงานออกมาเป็นไฟล์ TXT
            st.download_button(
                label="📥 ดาวน์โหลดใบสั่งงานเป็นไฟล์ .txt",
                data=line_text_summary,
                file_name=f"feed_order_{datetime.date.today()}.txt",
                mime="text/plain"
            )
            
        st.markdown("</div>", unsafe_allow_html=True)

# =============================================================================
# สิ้นสุดโครงสร้างโค้ดแอปพลิเคชันอย่างสมบูรณ์
# =============================================================================
