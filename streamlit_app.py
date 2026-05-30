import streamlit as st
import pandas as pd
import pulp
import plotly.express as px
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
# 2. CUSTOM CSS FOR BACKGROUND & UI (FIXED)
# ==========================================
def add_background():
    """ฟังก์ชัน CSS ล้างเลเยอร์สีทับซ้อน เพื่อให้ภาพพื้นหลังฟาร์มไก่แสดงผลได้ 100%"""
    st.markdown(
        """
        <style>
        /* 1. ล้างสีพื้นหลังของเลเยอร์ Streamlit ทั้งหมดที่คอยบังภาพ */
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: transparent !important;
        }
        
        /* 2. สร้างเลเยอร์พื้นหลังรูปฟาร์มไก่ไข่ไว้ด้านหลังสุด */
        .stApp::before {
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            /* เปลี่ยนลิงก์เป็นรูปฟาร์มไก่ไข่สีน้ำตาลในโรงเรือนระบบปิด */
            background-image: url("https://images.unsplash.com/photo-1548550022-c3f910408542?q=80&w=1920");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
            /* ปรับค่าความชัดของภาพพื้นหลัง (0.35 ช่วยให้เห็นภาพฟาร์มชัดเจนขึ้นในธีมมืด) */
            opacity: 0.35; 
            z-index: -1;
        }
        
        /* 3. ปรับแต่งกล่องเนื้อหาหลัก (Columns) ให้เป็นสีพื้นหลังโปร่งแสงสไตล์กระจกฝ้า (Frosted Glass) */
        div[data-testid="stGridColumn"] > div {
            background-color: rgba(20, 20, 20, 0.8) !important; /* ปรับให้ทึบขึ้นเล็กน้อยเพื่อตัดกับรูปพื้นหลังที่ชัดขึ้น */
            padding: 25px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.15);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(8px); /* ปรับให้ฉากหลังเบลอสวยงามขึ้น */
        }
        
        /* 4. ปรับแต่งกล่อง Metric สรุปตัวเลขทางการเงินให้มองเห็นชัดเจน */
        div[data-testid="stMetric"] {
            background-color: rgba(0, 0, 0, 0.5) !important;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #ffaa00;
        }
        [data-testid="stMetricValue"] {
            font-weight: bold;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# เรียกใช้งานฟังก์ชันพื้นหลังทันทีเมื่อเปิดแอป
add_background()

# ==========================================
# 3. SUPABASE CONNECTION & DATA LOADING
# ==========================================
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("❌ ไม่พบข้อมูลการเชื่อมต่อ Supabase ใน Streamlit Secrets (กรุณาตรวจสอบไฟล์ secrets.toml)")

@st.cache_data(ttl=60)
def load_ingredients_from_supabase():
    try:
        response = supabase.table("ingredients").select(
            "name, price_per_kg, protein_pct, fat_pct, me_kcal_per_kg, lysine_pct, methionine_pct, max_limit_pct"
        ).execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            # ล้างช่องว่างในชื่อวัตถุดิบป้องกันปัญหาคีย์ขัดข้องในไลบรารี PuLP
            df['name'] = df['name'].str.strip()
        return df
    except Exception as e:
        st.error(f"❌ ไม่สามารถดึงข้อมูลผ่าน API ของ Supabase ได้: {e}")
        return None

df_ingredients = load_ingredients_from_supabase()

# ==========================================
# 4. INITIALIZE SESSION STATE
# ==========================================
if "calculated" not in st.session_state:
    st.session_state.calculated = False
    st.session_state.df_result = None
    st.session_state.total_cost_100kg = 0.0
    st.session_state.calculated_protein = 0.0
    st.session_state.calculated_me = 0.0
    st.session_state.calculated_lysine = 0.0
    st.session_state.calculated_methionine = 0.0

# ==========================================
# 5. MAIN CONTENT & HEADER
# ==========================================
st.title("🥚 Smart Layer Feed")
st.subheader("ระบบคำนวณและวางแผนสูตรอาหารไก่ไข่อัจฉริยะด้วยปัญญาประดิษฐ์")
st.markdown("---")

# ==========================================
# SECTION 1: แผงควบคุมและตั้งค่า (FULL WIDTH)
# ==========================================
st.markdown("### ⚙️ แผงควบคุมและตั้งค่าการจำลองฟาร์ม")

input_col1, input_col2 = st.columns(2, gap="large")

with input_col1:
    st.markdown("##### 🐔 ข้อมูลฝูงไก่และสายพันธุ์")
    st.selectbox("กลุ่มไก่ไข่", ["Commercial Brown Layer"], index=0, disabled=True)
    st.selectbox("สายพันธุ์", ["อิซ่า บราวน์ (Isa Brown)"], index=0, disabled=True)
    st.selectbox("ระยะการเลี้ยง", ["ช่วงอายุ แรกเกิด-6 สัปดาห์ (Starter 0-6 wk)"], index=0, disabled=True)
    
    st.info("💡 **เกณฑ์โภชนาการสำหรับไก่ไข่ช่วงอายุ 0-6 สัปดาห์:**\n"
            "- โปรตีน (Protein): ไม่ต่ำกว่า **20.0%**\n"
            "- พลังงานใช้ประโยชน์ได้ (ME): ไม่ต่ำกว่า **2,900 kcal/กก.**\n"
            "- ไลซีน (Lysine): ไม่ต่ำกว่า **1.10%**\n"
            "- เมทไธโอนีน (Methionine): ไม่ต่ำกว่า **0.45%**")

with input_col2:
    st.markdown("##### 💰 ข้อมูลจำลองขนาดฟาร์มและเป้าหมายการผลิต")
    num_chickens = st.number_input("จำนวนไก่ไข่ในเล้า (ตัว)", min_value=1, value=100, step=10)
    feed_per_bird_g = st.number_input("อัตราการกินอาหาร (กรัม/ตัว/วัน)", min_value=1.0, value=100.0, step=5.0)
    egg_price = st.number_input("ราคาไข่ไก่เฉลี่ยที่คาดหวัง (บาท/ฟอง)", min_value=0.0, value=4.10, step=0.1)
    laying_rate = st.slider("อัตราการให้ไข่ของฝูงเป้าหมาย (%)", min_value=0, max_value=100, value=85)

st.markdown("##")

# ปุ่มประมวลผลคำนวณสูตรอาหารแบบกำหนดสมการเชิงเส้นต่ำสุด
if st.button("🚀 ประมวลผลและคำนวณสารอาหารที่แม่นยำที่สุด", use_container_width=True, type="primary"):
    if df_ingredients is not None and not df_ingredients.empty:
        # ค่ามาตรฐานโภชนาการคงที่สำหรับระยะลูกไก่
        AUTO_PROTEIN = 20.0
        AUTO_ME = 2900.0
        AUTO_LYSINE = 1.10
        AUTO_METHIONINE = 0.45
        
        # LP Optimization Setup ด้วย PuLP
        prob = pulp.LpProblem("Feed_Optimization", pulp.LpMinimize)
        ingredients_list = df_ingredients['name'].tolist()
        
        # ป้องกันอักขระพิเศษขัดแย้งใน Dictionary คีย์ตัวแปรด้วยการ Map ดัชนี
        vars_dict = {name: pulp.LpVariable(f"Ing_{i}", lowBound=0) for i, name in enumerate(ingredients_list)}
        
        # Objective Function: คำนวณหาต้นทุนที่ต่ำที่สุด
        prob += pulp.lpSum([vars_dict[row['name']] * row['price_per_kg'] for _, row in df_ingredients.iterrows()])
        
        # Constraints: กำหนดสมการน้ำหนักสูตรรวม 100 กก.
        prob += pulp.lpSum([vars_dict[i] for i in ingredients_list]) == 100.0
        
        # ข้อจำกัดสัดส่วนเพดานสูงสุดของแต่ละวัตถุดิบ (Max Limit Constraints จากฐานข้อมูล)
        for _, row in df_ingredients.iterrows():
            prob += vars_dict[row['name']] <= row['max_limit_pct']
        
        # สมการคำนวณสารอาหารเป้าหมายตามสัดส่วนฐาน 100 กิโลกรัม
        prob += pulp.lpSum([vars_dict[row['name']] * row['protein_pct'] for _, row in df_ingredients.iterrows()]) >= (AUTO_PROTEIN * 100)
        prob += pulp.lpSum([vars_dict[row['name']] * row['me_kcal_per_kg'] for _, row in df_ingredients.iterrows()]) >= (AUTO_ME * 100)
        prob += pulp.lpSum([vars_dict[row['name']] * row['lysine_pct'] for _, row in df_ingredients.iterrows()]) >= (AUTO_LYSINE * 100)
        prob += pulp.lpSum([vars_dict[row['name']] * row['methionine_pct'] for _, row in df_ingredients.iterrows()]) >= (AUTO_METHIONINE * 100)
        
        prob.solve(pulp.PULP_CBC_CMD(msg=False))
        
        if pulp.LpStatus[prob.status] == "Optimal":
            st.session_state.calculated = True
            st.session_state.total_cost_100kg = pulp.value(prob.objective)
            
            result_list = []
            calc_protein = 0.0
            calc_me = 0.0
            calc_lysine = 0.0
            calc_methionine = 0.0
