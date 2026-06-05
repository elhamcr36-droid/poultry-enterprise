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
    page_title="ระบบบริหารจัดการสินทรัพย์",
    page_icon="🏢"
)

# ==========================================
# 2. CUSTOM CSS (ถอดดีไซน์จากภาพ image_b541a8.png และ image_b59f60.png)
# ==========================================
def add_custom_styles():
    st.markdown(
        """
        <style>
        /* 1. พื้นหลังแอปสีน้ำเงินไล่เฉดสไตล์ Corporate แบบในรูป image_b541a8.png */
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background: linear-gradient(180deg, #4b749f 0%, #243b55 100%) !important;
            background-attachment: fixed !important;
        }
        
        /* 2. ข้อความพาดหัวระบบตัวเบิ้มด้านบน */
        .app-main-title {
            color: #ffffff !important;
            font-size: 38px !important;
            font-weight: bold !important;
            text-align: center;
            margin-top: 50px;
            margin-bottom: 0px;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            text-shadow: 0px 4px 12px rgba(0, 0, 0, 0.3);
        }
        .app-sub-title {
            color: #ffffff !important;
            font-size: 38px !important;
            font-weight: bold !important;
            text-align: center;
            margin-top: -10px;
            margin-bottom: 40px;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            text-shadow: 0px 4px 12px rgba(0, 0, 0, 0.3);
        }
        
        /* 3. กล่องการ์ดสีขาวขอบมนหนาสวยงามตรงกลางจอ */
        .auth-card {
            background-color: #ffffff !important;
            padding: 40px 30px 20px 30px;
            border-radius: 35px; 
            box-shadow: 0 20px 45px rgba(0, 0, 0, 0.25);
            max-width: 420px;
            margin: 0 auto;
            text-align: center;
        }
        
        /* 4. ช่องกรอกข้อมูล (Input) สีฟ้าพาสเทลอ่อนๆ นุ่มนวลตามภาพอันใหม่ */
        .stTextInput input {
            border-radius: 12px !important;
            border: 1px solid #d3e2f2 !important;
            padding: 14px 20px !important;
            background-color: #eef5fc !important;
            color: #333333 !important;
            font-size: 16px !important;
        }
        
        /* 5. ปุ่มกดหลัก ไล่เฉดสีฟ้า-น้ำเงินเงางาม (Gradient Buttons) */
        div.stButton > button {
            background: linear-gradient(90deg, #4a76a8 0%, #3b5998 100%) !important;
            color: #ffffff !important;
            border-radius: 14px !important;
            padding: 12px 20px !important;
            font-size: 16px !important;
            font-weight: bold !important;
            border: none !important;
            width: 100% !important;
            box-shadow: 0 4px 15px rgba(59, 89, 152, 0.3) !important;
            transition: all 0.2s ease;
        }
        div.stButton > button:hover {
            background: linear-gradient(90deg, #3b5998 0%, #243b55 100%) !important;
            box-shadow: 0 6px 20px rgba(59, 89, 152, 0.5) !important;
            transform: translateY(-1px);
        }
        
        /* 6. ปุ่มลิงก์สลับหน้าด้านล่างสุด (ใช้ปุ่มโปร่งใส) */
        .auth-footer-buttons div.stButton > button {
            background: transparent !important;
            color: #ffffff !important;
            border: none !important;
            font-size: 14px !important;
            font-weight: normal !important;
            padding: 0 !important;
            width: auto !important;
            box-shadow: none !important;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        .auth-footer-buttons div.stButton > button:hover {
            color: #d3e2f2 !important;
            text-decoration: underline !important;
            background: transparent !important;
            box-shadow: none !important;
        }
        
        /* 7. สไตล์การตกแต่ง Dashboard หน้าในเมื่อล็อกอินเสร็จแล้ว */
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

# สเตทการจำหน้าล็อกอิน
if "auth_page" not in st.session_state:
    st.session_state.auth_page = "login"
if "user" not in st.session_state:
    st.session_state.user = None

# ==========================================
# 4. HARDCODED DATA (คลังข้อมูลดั้งเดิมของระบบ)
# ==========================================
raw_ingredients = [
    ('พลังงาน', 'ข้าวโพด', 'Corn'), ('พลังงาน', 'ข้าวฟ่าง', 'Sorghum'), ('พลังงาน', 'ข้าวสาลี', 'Wheat'),
    ('พลังงาน', 'ข้าวบาร์เลย์', 'Barley'), ('พลังงาน', 'ข้าวโอ๊ต', 'Oat'), ('พลังงาน', 'ข้าวไรย์', 'Rye'),
    ('พลังงาน', 'ข้าวเปลือก', 'Paddy Rice'), ('พลังงาน', 'ปลายข้าว', 'Broken Rice'), ('พลังงาน', 'รำละเอียด', 'Rice Bran'),
    ('พลังงาน', 'รำหยาบ', 'Rice Polish'), ('พลังงาน', 'รำสกัดน้ำมัน', 'Defatted Rice Bran'), ('พลังงาน', 'มันสำปะหลังเส้น', 'Cassava Chips'),
    ('พลังงาน', 'มันสำปะหลังบด', 'Cassava Meal'), ('พลังงาน', 'กากมันสำปะหลัง', 'Cassava Pulp'), ('พลังงาน', 'มันเทศ', 'Sweet Potato'),
    ('พลังงาน', 'กากน้ำตาล', 'Molasses'), ('พลังงาน', 'แป้งข้าวโพด', 'Corn Starch'), ('พลังงาน', 'แป้งสาลี', 'Wheat Flour'),
    ('โปรตีนจากพืช', 'กากถั่วเหลือง', 'Soybean Meal'), ('โปรตีนจากพืช', 'ถั่วเหลืองเต็มเมล็ด', 'Full-Fat Soybean'),
    ('โปรตีนจากพืช', 'ถั่วเหลืองอบ', 'Roasted Soybean'), ('โปรตีนจากพืช', 'ถั่วเหลืองคั่ว', 'Toasted Soybean'),
    ('โปรตีนจากพืช', 'กากคาโนลา', 'Canola Meal'), ('โปรตีนจากพืช', 'กากเรปซีด', 'Rapeseed Meal'),
    ('โปรตีนจากพืช', 'กากเมล็ดทานตะวัน', 'Sunflower Meal'), ('โปรตีนจากพืช', 'กากเมล็ดฝ้าย', 'Cottonseed Meal'),
    ('โปรตีนจากพืช', 'กากปาล์ม', 'Palm Kernel Meal'), ('โปรตีนจากพืช', 'กากมะพร้าว', 'Coconut Meal'),
    ('โปรตีนจากพืช', 'กากถั่วลิสง', 'Peanut Meal'), ('โปรตีนจากพืช', 'กากงา', 'Sesame Meal'),
    ('โปรตีนจากพืช', 'กากเมล็ดแฟลกซ์', 'Flaxseed Meal'), ('โปรตีนจากพืช', 'ถั่วลันเตา', 'Pea'),
    ('โปรตีนจากพืช', 'กากถั่วลันเตา', 'Pea Meal'), ('โปรตีนจากพืช', 'กากถั่วเขียว', 'Mung Bean Meal'),
    ('โปรตีนจากพืช', 'ลูพิน', 'Lupin'), ('โปรตีนจากพืช', 'กากข้าวโพดโปรตีนสูง', 'High Protein Corn Meal'),
    ('โปรตีนจากพืช', 'ดีดีจีเอส', 'DDGS'), ('โปรตีนจากพืช', 'คอร์นกลูเตนมีล', 'Corn Gluten Meal'),
    ('โปรตีนจากพืช', 'คอร์นกลูเตนฟีด', 'Corn Gluten Feed'),
    ('โปรตีนจากสัตว์', 'ปลาป่น', 'Fish Meal'), ('โปรตีนจากสัตว์', 'เนื้อป่น', 'Meat Meal'),
    ('โปรตีนจากสัตว์', 'เนื้อและกระดูกป่น', 'Meat and Bone Meal'), ('โปรตีนจากสัตว์', 'เลือดป่น', 'Blood Meal'),
    ('โปรตีนจากสัตว์', 'ขนนกป่น', 'Feather Meal'), ('โปรตีนจากสัตว์', 'เครื่องในสัตว์ปีกป่น', 'Poultry By-Product Meal'),
    ('โปรตีนจากสัตว์', 'กุ้งป่น', 'Shrimp Meal'), ('โปรตีนจากสัตว์', 'ปูป่น', 'Crab Meal'),
    ('โปรตีนจากสัตว์', 'หอยป่น', 'Shellfish Meal'), ('โปรตีนจากสัตว์', 'แมลงป่น', 'Insect Meal'),
    ('โปรตีนจากสัตว์', 'หนอนแมลงวันลายป่น', 'Black Soldier Fly Meal'), ('โปรตีนจากสัตว์', 'ไส้เดือนป่น', 'Earthworm Meal'),
    ('แร่ธาตุ', 'หินปูนบด', 'Limestone'), ('แร่ธาตุ', 'เปลือกหอยบด', 'Ground Oyster Shell'),
    ('แร่ธาตุ', 'เปลือกไข่บด', 'Eggshell Meal'), ('แร่ธาตุ', 'ไดแคลเซียมฟอสเฟต', 'Dicalcium Phosphate'),
    ('แร่ธาตุ', 'โมโนแคลเซียมฟอสเฟต', 'Monocalcium Phosphate'), ('แร่ธาตุ', 'กระดูกป่น', 'Bone Meal'),
    ('แร่ธาตุ', 'เกลือ', 'Salt'), ('แร่ธาตุ', 'โซเดียมไบคาร์บอเนต', 'Sodium Bicarbonate'),
    ('แร่ธาตุ', 'โพแทสเซียมคลอไรด์', 'Potassium Chloride'), ('แร่ธาตุ', 'แมกนีเซียมออกไซด์', 'Magnesium Oxide'),
    ('กรดอะมิโน', 'ดีแอล-เมไทโอนีน', 'DL-Methionine'), ('กรดอะมิโน', 'แอล-ไลซีน เอชซีแอล', 'L-Lysine HCl'),
    ('กรดอะมิโน', 'แอล-ไลซีน ซัลเฟต', 'L-Lysine Sulfate'), ('กรดอะมิโน', 'แอล-ทรีโอนีน', 'L-Threonine'),
    ('กรดอะมิโน', 'แอล-ทริปโตเฟน', 'L-Tryptophan'), ('กรดอะมิโน', 'แอล-วาลีน', 'L-Valine'),
    ('กรดอะมิโน', 'แอล-ไอโซลิวซีน', 'L-Isoleucine'), ('กรดอะมิโน', 'แอล-อาร์จินีน', 'L-Arginine'),
    ('วิตามิน', 'วิตามินเอ', 'Vitamin A'), ('วิตามิน', 'วิตามินดี3', 'Vitamin D3'), ('วิตามิน', 'วิตามินอี', 'Vitamin E'),
    ('วิตามิน', 'วิตามินเค3', 'Vitamin K3'), ('วิตามิน', 'วิตามินบี1', 'Vitamin B1'), ('วิตามิน', 'วิตามินบี2', 'Vitamin B2'),
    ('วิตามิน', 'วิตามินบี6', 'Vitamin B6'), ('วิตามิน', 'วิตามินบี12', 'Vitamin B12'), ('วิตามิน', 'ไนอาซิน', 'Niacin'),
    ('วิตามิน', 'กรดโฟลิก', 'Folic Acid'), ('วิตามิน', 'ไบโอติน', 'Biotin'), ('วิตามิน', 'กรดแพนโททีนิก', 'Pantothenic Acid'),
    ('วิตามิน', 'โคลีนคลอไรด์', 'Choline Chloride'),
    ('แร่ธาตุรอง', 'เหล็ก', 'Iron'), ('แร่ธาตุรอง', 'สังกะสี', 'Zinc'), ('แร่ธาตุรอง', 'แมงกานีส', 'Manganese'),
    ('แร่ธาตุรอง', 'ทองแดง', 'Copper'), ('แร่ธาตุรอง', 'ไอโอดีน', 'Iodine'), ('แร่ธาตุรอง', 'ซีลีเนียม', 'Selenium'),
    ('แร่ธาตุรอง', 'โคบอลต์', 'Cobalt'),
    ('ไขมันและน้ำมัน', 'น้ำมันปาล์ม', 'Palm Oil'), ('ไขมันและน้ำมัน', 'น้ำมันถั่วเหลือง', 'Soybean Oil'),
    ('ไขมันและน้ำมัน', 'น้ำมันข้าวโพด', 'Corn Oil'), ('ไขมันและน้ำมัน', 'น้ำมันคาโนลา', 'Canola Oil'),
    ('ไขมันและน้ำมัน', 'น้ำมันดอกทานตะวัน', 'Sunflower Oil'), ('ไขมันและน้ำมัน', 'น้ำมันปลา', 'Fish Oil'),
    ('ไขมันและน้ำมัน', 'ไขมันสัตว์', 'Animal Fat'), ('ไขมันและน้ำมัน', 'น้ำมันมะพร้าว', 'Coconut Oil'),
    ('วัตถุดิบทางเลือก', 'ใบกระถินป่น', 'Leucaena Leaf Meal'), ('วัตถุดิบทางเลือก', 'ใบมะรุมป่น', 'Moringa Leaf Meal'),
    ('วัตถุดิบทางเลือก', 'ใบมันสำปะหลังป่น', 'Cassava Leaf Meal'), ('วัตถุดิบทางเลือก', 'ใบอัลฟัลฟาป่น', 'Alfalfa Meal'),
    ('วัตถุดิบทางเลือก', 'ผักตบชวาแห้ง', 'Dried Water Hyacinth'), ('วัตถุดิบทางเลือก', 'สาหร่ายทะเล', 'Seaweed Meal'),
    ('วัตถุดิบทางเลือก', 'แหนแดง', 'Azolla'), ('วัตถุดิบทางเลือก', 'จอกแหน', 'Duckweed'),
    ('วัตถุดิบทางเลือก', 'ต้นกล้วยหมัก', 'Fermented Banana Stem'), ('วัตถุดิบทางเลือก', 'หญ้าเนเปียร์หมัก', 'Fermented Napier Grass'),
    ('วัตถุดิบทางเลือก', 'กากเบียร์', "Brewer's Grain"), ('วัตถุดิบทางเลือก', 'กากยีสต์', 'Yeast Residue'),
    ('วัตถุดิบทางเลือก', 'กากกาแฟ', 'Coffee Pulp'), ('วัตถุดิบทางเลือก', 'กากชา', 'Tea Residue'),
    ('วัตถุดิบทางเลือก', 'กากผลไม้', 'Fruit Pomace'), ('วัตถุดิบทางเลือก', 'เศษผักผลไม้', 'Vegetable and Fruit Waste'),
    ('สารเสริมอาหาร', 'เอนไซม์', 'Enzyme'), ('สารเสริมอาหาร', 'โปรไบโอติก', 'Probiotic'), ('สารเสริมอาหาร', 'พรีไบโอติก', 'Prebiotic'),
    ('สารเสริมอาหาร', 'ยีสต์', 'Yeast'), ('สารเสริมอาหาร', 'สารต้านเชื้อรา', 'Antifungal Agent'),
    ('สารเสริมอาหาร', 'สารกันหืน', 'Antioxidant'), ('สารเสริมอาหาร', 'สารจับสารพิษ', 'Mycotoxin Binder'),
    ('สารเสริมอาหาร', 'กรดอินทรีย์', 'Organic Acid'), ('สารเสริมอาหาร', 'สารเพิ่มการย่อย', 'Digestive Enhancer'),
    ('สารเสริมอาหาร', 'สารเพิ่มสีไข่แดง', 'Yolk Pigment')
]

df_ingredients = pd.DataFrame(raw_ingredients, columns=['category', 'name_th', 'name_en'])
df_ingredients['name'] = df_ingredients['name_th'] + " (" + df_ingredients['name_en'] + ")"

df_ingredients['price_per_kg'] = 15.0
df_ingredients['protein_pct'] = 22.0
df_ingredients['me_kcal_per_kg'] = 3000.0
df_ingredients['lysine_pct'] = 1.2
df_ingredients['methionine_pct'] = 0.5
df_ingredients['max_limit_pct'] = 100.0

raw_breeds = [
    ('สายพันธุ์เชิงพาณิชย์', 'ไฮไลน์ บราวน์', 'Hy-Line Brown'), ('สายพันธุ์เชิงพาณิชย์', 'ไฮไลน์ ดับเบิลยู-36', 'Hy-Line W-36'),
    ('สายพันธุ์เชิงพาณิชย์', 'โลห์มันน์ บราวน์', 'Lohmann Brown'), ('สายพันธุ์เชิงพาณิชย์', 'โลห์มันน์ แอลเอสแอล คลาสสิก', 'Lohmann LSL Classic'),
    ('สายพันธุ์เชิงพาณิชย์', 'ไอเอสเอ บราวน์', 'ISA Brown'), ('สายพันธุ์เชิงพาณิชย์', 'โนโวเจน บราวน์', 'Novogen Brown'),
    ('สายพันธุ์แท้', 'เลกฮอร์นขาว', 'White Leghorn'), ('สายพันธุ์แท้', 'เลกฮอร์นน้ำตาล', 'Brown Leghorn'),
    ('สายพันธุ์พื้นเมืองและพรีเมียม', 'ซิลกี้ หรือไก่ไหม', 'Silkie'), ('สายพันธุ์พื้นเมืองและพรีเมียม', 'มาร็องส์', 'Marans')
]

df_breeds_raw = pd.DataFrame(raw_breeds, columns=['category', 'name_th', 'name_en'])
df_breeds_raw['display_name'] = df_breeds_raw['name_th'] + " (" + df_breeds_raw['name_en'] + ")"

list_groups = sorted(df_breeds_raw['category'].unique().tolist())
list_stages = [
    "ช่วงอายุ แรกเกิด-6 สัปดาห์ (Starter 0-6 wk)",
    "ช่วงอายุ 6-12 สัปดาห์ (Grower 6-12 wk)",
    "ช่วงอายุ 12-18 สัปดาห์ (Developer 12-18 wk)",
    "ระยะไก่ไข่ให้ผลผลิต (Laying Period)"
]

if "calculated" not in st.session_state:
    st.session_state.calculated = False
    st.session_state.df_result = None
    st.session_state.total_cost_100kg = 0.0
    st.session_state.calculated_protein = 0.0
    st.session_state.calculated_me = 0.0
    st.session_state.calculated_lysine = 0.0
    st.session_state.calculated_methionine = 0.0

def reset_calculation():
    st.session_state.calculated = False


# ==========================================
# 5. ROUTING - INTERFACE CONTROLLER
# ==========================================
if st.session_state.user is None:
    
    # พาดหัวเว็บบนพื้นหลังสีน้ำเงินตรงตามรูปภาพภาพที่สอง
    st.markdown('<div class="app-main-title">ระบบบริหารจัดการ</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-sub-title">สินทรัพย์</div>', unsafe_allow_html=True)
    
    # ------------------------------------------
    # 🗂️ หน้าเข้าสู่ระบบ (LOGIN CARD VIEW)
    # ------------------------------------------
    if st.session_state.auth_page == "login":
        st.markdown(
            """
            <div class="auth-card">
                </div>
            """, 
            unsafe_allow_html=True
        )
        
        # วางกล่องกรอกฟิลด์ให้อยู่กึ่งกลางการ์ด
        _, center_col, _ = st.columns([1, 1.1, 1])
        with center_col:
            login_email = st.text_input("ชื่อผู้ใช้งาน", placeholder="ชื่อผู้ใช้งาน", key="input_login_email", label_visibility="collapsed")
            login_pass = st.text_input("รหัสผ่าน", placeholder="รหัสผ่าน", type="password", key="input_login_pass", label_visibility="collapsed")
            
            st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
            
            if st.button("ลงชื่อเข้าใช้ระบบ"):
                try:
                    response = supabase.auth.sign_in_with_password({"email": login_email, "password": login_pass})
                    st.session_state.user = response.user
                    st.success("🎉 เข้าสู่ระบบสำเร็จแล้ว!")
                    st.rerun()
                except Exception as e:
                    st.error("❌ ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
            
            # โซนปุ่มกดสลับหน้าภาษาไทยด้านล่างการ์ดขาว
            st.markdown("<div class='auth-footer-buttons' style='text-align:center; margin-top:25px;'>", unsafe_allow_html=True)
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                if st.button("ลืมรหัสผ่าน?", key="goto_forgot_pwd"):
                    st.session_state.auth_page = "forgot"
                    st.rerun()
            with f_col2:
                if st.button("สมัครสมาชิก", key="goto_register_form"):
                    st.session_state.auth_page = "register"
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------
    # 🗂️ หน้าสมัครสมาชิก (REGISTER CARD VIEW)
    # ------------------------------------------
    elif st.session_state.auth_page == "register":
        st.markdown(
            """
            <div class="auth-card">
                <h3 style="color:#243b55; margin-top:0; font-weight:bold;">ลงทะเบียนผู้ใช้งานใหม่</h3>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        _, center_col, _ = st.columns([1, 1.3, 1])
        with center_col:
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                first_name = st.text_input("ชื่อจริง", placeholder="ชื่อจริง", key="reg_fn")
            with f_col2:
                last_name = st.text_input("นามสกุล", placeholder="นามสกุล", key="reg_ln")
                
            reg_email = st.text_input("อีเมลสมัครงาน", placeholder="ที่อยู่อีเมล", key="reg_email")
            reg_password = st.text_input("รหัสผ่าน", placeholder="ตั้งรหัสผ่านใหม่", type="password", key="reg_password")
            
            if reg_password:
                is_valid, msg = is_password_strong(reg_password)
                if is_valid: st.success(f"🟢 {msg}")
                else: st.warning(f"🟡 {msg}")
                    
            st.markdown("<br>", unsafe_allow_html=True)
            farm_name = st.text_input("ชื่อหน่วยงาน / บริษัทจำลอง", placeholder="เช่น บริษัท มั่นคงสินทรัพย์ จำกัด")

            if st.button("ลงทะเบียนบัญชี"):
                is_valid, msg = is_password_strong(reg_password)
                if not (first_name and last_name and reg_email and farm_name):
                    st.error("❌ กรุณากรอกข้อมูลส่วนตัวให้ครบถ้วน")
                elif not is_valid:
                    st.error(f"❌ {msg}")
                else:
                    try:
                        res = supabase.auth.sign_up({
                            "email": reg_email,
                            "password": reg_password,
                            "options": {
                                "data": {
                                    "first_name": first_name,
                                    "last_name": last_name,
                                    "farm_name": farm_name
                                }
                            }
                        })
                        st.success("📩 ระบบส่งลิงก์ยืนยันแล้ว! กรุณาเปิดตรวจสอบในกล่องอีเมลของคุณ")
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {str(e)}")
            
            st.markdown("<div class='auth-footer-buttons' style='text-align:center;'>", unsafe_allow_html=True)
            if st.button("⬅️ กลับไปยังหน้าเข้าสู่ระบบ", key="back_from_reg"):
                st.session_state.auth_page = "login"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------
    # 🗂️ หน้าลืมรหัสผ่าน (FORGOT CARD VIEW)
    # ------------------------------------------
    elif st.session_state.auth_page == "forgot":
        st.markdown(
            """
            <div class="auth-card">
                <h3 style="color:#243b55; margin-top:0; font-weight:bold;">กู้คืนบัญชีผู้ใช้งาน</h3>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        _, center_col, _ = st.columns([1, 1.1, 1])
        with center_col:
            st.write("ระบบจะส่งลิงก์ตั้งรหัสผ่านใหม่ไปที่อีเมลของคุณ")
            reset_email = st.text_input("อีเมลที่ใช้ลงทะเบียน", placeholder="example@email.com", key="forgot_email")
            
            if st.button("ส่งลิงก์กู้คืนรหัสผ่าน"):
                if reset_email:
                    try:
                        supabase.auth.reset_password_for_email(reset_email)
                        st.success("📩 ส่งลิงก์รีเซ็ตรหัสผ่านไปยังกล่องข้อความสำเร็จ!")
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {str(e)}")
                else:
                    st.error("❌ กรุณากรอกอีเมล")
                    
            st.markdown("<div class='auth-footer-buttons' style='text-align:center;'>", unsafe_allow_html=True)
            if st.button("⬅️ กลับไปยังหน้าเข้าสู่ระบบ", key="back_from_forgot"):
                st.session_state.auth_page = "login"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 6. MAIN SYSTEM DASHBOARD (เมื่อล็อกอินสำเร็จแล้ว)
# ==========================================
else:
    user_info = st.session_state.user.user_metadata
    user_name = user_info.get("first_name", "ผู้ดูแลระบบ")
    farm_title = user_info.get("farm_name", "ระบบบริหารจัดการ")
    
    # ปรับแต่งสีข้อความและลาเบลหน้าหลังบ้านให้อ่านง่ายบนพื้นสีเข้ม
    st.markdown(
        """
        <style>
        h1, h2, h3, h4, h5, h6, p, label { color: #ffffff !important; }
        .stSelectbox label, .stNumberInput label, .stSlider label { color: #ffffff !important; }
        </style>
        """, unsafe_allow_html=True
    )
    
    header_col1, header_col2 = st.columns([8, 2])
    with header_col1:
        st.title("🏢 ระบบบริหารจัดการและคำนวณสัดส่วนอัจฉริยะ")
        st.subheader(f"👋 ยินดีต้อนรับคุณ {user_name} | หน่วยงาน: {farm_title}")
    with header_col2:
        st.write("")
        if st.button("🔒 ออกจากระบบ"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

    st.markdown("---")

    # ส่วนที่ 1: หน้าคอนฟิกควบคุมหลัก
    st.markdown("### ⚙️ แผงควบคุมและตั้งค่าพารามิเตอร์จำลอง")
    input_col1, input_col2 = st.columns(2, gap="large")

    with input_col1:
        st.markdown("##### 🐔 ข้อมูลฝูงไก่และสายพันธุ์")
        selected_group = st.selectbox("กลุ่มไก่ไข่", list_groups, index=0, on_change=reset_calculation)
        filtered_breeds = sorted(df_breeds_raw[df_breeds_raw['category'] == selected_group]['display_name'].tolist())
        selected_breed = st.selectbox("สายพันธุ์", filtered_breeds, index=0, on_change=reset_calculation)
        selected_stage = st.selectbox("ระยะการเลี้ยง", list_stages, index=0, on_change=reset_calculation)
        
        st.info("💡 **เกณฑ์โภชนาการสำหรับไก่ไข่ช่วงอายุ 0-6 สัปดาห์:**\n"
                "- โปรตีน (Protein): ไม่ต่ำกว่า **20.0%**\n"
                "- พลังงานใช้ประโยชน์ได้ (ME): ไม่ต่ำกว่า **2,900 kcal/กก.**")

    with input_col2:
        st.markdown("##### 💰 ข้อมูลจำลองขนาดฟาร์มและเป้าหมายการผลิต")
        num_chickens = st.number_input("จำนวนไก่ไข่ในเล้า (ตัว)", min_value=1, value=180, step=10, on_change=reset_calculation)
        feed_per_bird_g = st.number_input("อัตราการกินอาหาร (กรัม/ตัว/วัน)", min_value=1.0, value=180.0, step=5.0, on_change=reset_calculation)
        egg_price = st.number_input("ราคาไข่ไก่เฉลี่ยที่คาดหวัง (บาท/ฟอง)", min_value=0.0, value=4.10, step=0.1, on_change=reset_calculation)
        laying_rate = st.slider("อัตราการให้ไข่ของฝูงเป้าหมาย (%)", min_value=0, max_value=100, value=85, on_change=reset_calculation)

    st.markdown("##")

    if st.button("🚀 ประมวลผลและคำนวณสารอาหารที่แม่นยำที่สุด", use_container_width=True, type="primary"):
        if not df_ingredients.empty:
            AUTO_PROTEIN, AUTO_ME, AUTO_LYSINE, AUTO_METHIONINE = 20.0, 2900.0, 1.10, 0.45
            
            prob = pulp.LpProblem("Feed_Optimization", pulp.LpMinimize)
            ingredients_list = df_ingredients['name'].tolist()
            vars_dict = {name: pulp.LpVariable(f"Ing_{i}", lowBound=0) for i, name in enumerate(ingredients_list)}
            
            prob += pulp.lpSum([vars_dict[row['name']] * row['price_per_kg'] for _, row in df_ingredients.iterrows()])
            prob += pulp.lpSum([vars_dict[i] for i in ingredients_list]) == 100.0
            
            for _, row in df_ingredients.iterrows():
                prob += vars_dict[row['name']] <= row['max_limit_pct']
            
            prob += pulp.lpSum([vars_dict[row['name']] * row['protein_pct'] for _, row in df_ingredients.iterrows()]) >= (AUTO_PROTEIN * 100)
            prob += pulp.lpSum([vars_dict[row['name']] * row['me_kcal_per_kg'] for _, row in df_ingredients.iterrows()]) >= (AUTO_ME * 100)
            
            prob.solve(pulp.PULP_CBC_CMD(msg=False))
            
            if pulp.LpStatus[prob.status] == "Optimal":
                st.session_state.calculated = True
                st.session_state.total_cost_100kg = pulp.value(prob.objective)
                
                result_list = []
                calc_protein, calc_me = 0.0, 0.0
                for _, row in df_ingredients.iterrows():
                    w = vars_dict[row['name']].varValue
                    if w and w > 0.01:
                        result_list.append({
                            "ชื่อวัตถุดิบ": row['name'], 
                            "สัดส่วน (%)": round(w, 2), 
                            "ปริมาณที่ต้องใช้ (กก.)": round(w, 2),
                            "ราคาประเมิน (บาท)": round(w * row['price_per_kg'], 2)
                        })
                        calc_protein += w * row['protein_pct']
                        calc_me += w * row['me_kcal_per_kg']
                
                st.session_state.df_result = pd.DataFrame(result_list)
                st.session_state.calculated_protein = calc_protein / 100
                st.session_state.calculated_me = calc_me / 100
                st.success("🎉 ล็อกสัดส่วนเรียบร้อยแล้ว!")

    st.markdown("---")

    # ส่วนที่ 2: แสดงตารางกราฟริพอร์ตหลังบ้าน
    st.markdown("### 📊 รายงานผลลัพธ์และการวิเคราะห์ประสิทธิภาพ")

    if st.session_state.calculated and st.session_state.df_result is not None:
        total_feed_day_kg = (num_chickens * feed_per_bird_g) / 1000
        cost_per_day = total_feed_day_kg * (st.session_state.total_cost_100kg / 100)
        expected_eggs_day = num_chickens * (laying_rate / 100)
        revenue_per_day = expected_eggs_day * egg_price
        net_profit_per_day = revenue_per_day - cost_per_day

        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric(label="📉 ต้นทุนรวม / วัน", value=f"{cost_per_day:,.2f} ฿")
        with m2: st.metric(label="📈 รายได้รวมคาดการณ์ / วัน", value=f"{revenue_per_day:,.2f} ฿")
        with m3: st.metric(label="🏆 กำไรสุทธิประเมิน / วัน", value=f"{net_profit_per_day:,.2f} ฿")
        with m4: st.metric(label="💰 ราคาเฉลี่ย (ต่อกก.)", value=f"{st.session_state.total_cost_100kg / 100:.2f} ฿")

        st.markdown("##")
        report_left, report_right = st.columns([1.1, 0.9], gap="large")
        
        with report_left:
            st.markdown("##### 🍩 แผนภูมิสัดส่วนโครงสร้าง")
            fig = px.pie(st.session_state.df_result, values='สัดส่วน (%)', names='ชื่อวัตถุดิบ', hole=0.45)
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320, font=dict(color="black"), paper_bgcolor='rgba(255,255,255,0.95)')
            st.plotly_chart(fig, use_container_width=True)

        with report_right:
            st.markdown("##### 📋 ตารางสัดส่วนจัดซื้อจริง (ต่อ 100 กิโลกรัม)")
            st.dataframe(st.session_state.df_result, use_container_width=True, hide_index=True, height=320)
    else:
        st.info("💡 **ระบบพร้อมใช้งาน:** ตั้งค่าข้อมูลจากแผงควบคุมด้านบน จากนั้นกดปุ่มประมวลผลสูตรได้ทันทีครับ")
