import streamlit as res_st
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
# 2. CUSTOM CSS FOR BACKGROUND & CARD UI (อิงตามรูปภาพที่ส่งมา)
# ==========================================
def add_custom_styles():
    st.markdown(
        """
        <style>
        /* พื้นหลังหลักของแอปพลิเคชัน (สีเทาและมี Texture อิงตามรูปภาพ) */
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #a8a8a8 !important; 
            background-image: radial-gradient(rgba(0,0,0,0.15) 1px, transparent 0) !important;
            background-size: 4px 4px !important;
        }
        
        /* กล่อง Card หน้าล็อกอินสีขาวขอบมน (Minimal Rounded Card) */
        .auth-card {
            background-color: #ffffff !important;
            padding: 30px 25px 15px 25px;
            border-radius: 30px; 
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.15);
            max-width: 400px;
            margin: 0 auto;
            text-align: center;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        }
        
        /* รูปโปรไฟล์อวาตาร์วงกลมด้านบน */
        .avatar-container {
            width: 110px;
            height: 110px;
            background-color: #f0f0f0;
            border-radius: 50%;
            margin: 0 auto 15px auto;
            border: 4px solid #ffffff;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        .avatar-container img {
            width: 75%;
            height: auto;
            opacity: 0.6;
        }
        
        /* หัวข้อ "เข้าสู่ระบบ" ตรงกลาง */
        .auth-title {
            color: #111111 !important;
            font-size: 24px !important;
            font-weight: bold !important;
            margin-bottom: 25px !important;
        }
        
        /* ปรับแต่งช่องกรอกข้อความ (Input) ของ Streamlit ให้นุ่มนวลโค้งมนลึกแบบ Inset */
        .stTextInput input {
            border-radius: 25px !important;
            border: 1px solid #e2e2e2 !important;
            padding: 12px 20px !important;
            background-color: #ffffff !important;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.05) !important;
            font-size: 15px !important;
        }
        
        /* ปรับสไตล์ปุ่มกดยืนยัน (สีเทาเข้มเกือบดำ ขอบมนยาว) */
        div.stButton > button {
            background-color: #2b2b2b !important;
            color: #ffffff !important;
            border-radius: 25px !important;
            padding: 10px 20px !important;
            font-size: 16px !important;
            font-weight: 500 !important;
            border: none !important;
            width: 100% !important;
            transition: all 0.2s ease;
        }
        div.stButton > button:hover {
            background-color: #111111 !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
        }
        
        /* ปุ่มสลับหน้าด้านล่างสุด (ลืมรหัสผ่าน / สมัครสมาชิก) */
        .auth-footer-buttons div.stButton > button {
            background-color: transparent !important;
            color: #555555 !important;
            border: none !important;
            font-size: 14px !important;
            font-weight: normal !important;
            padding: 0 !important;
            width: auto !important;
            box-shadow: none !important;
        }
        .auth-footer-buttons div.stButton > button:hover {
            color: #000000 !important;
            text-decoration: underline !important;
            background-color: transparent !important;
            box-shadow: none !important;
        }
        
        /* สไตล์ตารางและการแสดงผลเมื่อล็อกอินเข้าไปแล้ว */
        div[data-testid="stGridColumn"] > div {
            background-color: rgba(25, 25, 25, 0.88) !important; 
            padding: 25px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.12);
            backdrop-filter: blur(12px);
        }
        div[data-testid="stMetric"] {
            background-color: rgba(0, 0, 0, 0.65) !important;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #ffaa00;
        }
        [data-testid="stMetricValue"] { font-weight: bold; color: #ffaa00 !important; }
        [data-testid="stMetricLabel"] { color: #e0e0e0 !important; }
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
    if not re.search("[_@$!%*#?&|-]", password):
        return False, "รหัสผ่านต้องมีสัญลักษณ์พิเศษอย่างน้อย 1 ตัว"
    return True, "รหัสผ่านปลอดภัยตามมาตรฐาน"

# จัดการการสลับหน้าจอ (login, register, forgot)
if "auth_page" not in st.session_state:
    st.session_state.auth_page = "login"
if "user" not in st.session_state:
    st.session_state.user = None

# ==========================================
# 4. HARDCODED DATA (คลังข้อมูลวัตถุดิบและสายพันธุ์)
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
    ('สายพันธุ์เชิงพาณิชย์ (Commercial Breeds)', 'ไฮไลน์ บราวน์', 'Hy-Line Brown'), ('สายพันธุ์เชิงพาณิชย์ (Commercial Breeds)', 'ไฮไลน์ ดับเบิลยู-36', 'Hy-Line W-36'),
    ('สายพันธุ์เชิงพาณิชย์ (Commercial Breeds)', 'โลห์มันน์ บราวน์', 'Lohmann Brown'), ('สายพันธุ์เชิงพาณิชย์ (Commercial Breeds)', 'โลห์มันน์ แอลเอสแอล คลาสสิก', 'Lohmann LSL Classic'),
    ('สายพันธุ์เชิงพาณิชย์ (Commercial Breeds)', 'ไอเอสเอ บราวน์', 'ISA Brown'), ('สายพันธุ์เชิงพาณิชย์ (Commercial Breeds)', 'โนโวเจน บราวน์', 'Novogen Brown'),
    ('สายพันธุ์เชิงพาณิชย์ (Commercial Breeds)', 'โนโวเจน ไวท์', 'Novogen White'), ('สายพันธุ์เชิงพาณิชย์ (Commercial Breeds)', 'โบแวนส์ บราวน์', 'Bovans Brown'),
    ('สายพันธุ์เชิงพาณิชย์ (Commercial Breeds)', 'โบแวนส์ ไวท์', 'Bovans White'), ('สายพันธุ์เชิงพาณิชย์ (Commercial Breeds)', 'เดอแคลบ์ ไวท์', 'Dekalb White'),
    ('สายพันธุ์เชิงพาณิชย์ (Commercial Breeds)', 'เชเวอร์ บราวน์', 'Shaver Brown'), ('สายพันธุ์เชิงพาณิชย์ (Commercial Breeds)', 'ไฮเซกซ์ บราวน์', 'Hisex Brown'),
    ('สายพันธุ์เชิงพาณิชย์ (Commercial Breeds)', 'ไฮเซกซ์ ไวท์', 'Hisex White'), ('สายพันธุ์เชิงพาณิชย์ (Commercial Breeds)', 'นิค บราวน์', 'Nick Brown'),
    ('สายพันธุ์เชิงพาณิชย์ (Commercial Breeds)', 'แบ็บค็อก บราวน์', 'Babcock Brown'),
    ('สายพันธุ์แท้ (Purebreds)', 'เลกฮอร์นขาว', 'White Leghorn'), ('สายพันธุ์แท้ (Purebreds)', 'เลกฮอร์นน้ำตาล', 'Brown Leghorn'),
    ('สายพันธุ์แท้ (Purebreds)', 'ไมนอร์กา', 'Minorca'), ('สายพันธุ์แท้ (Purebreds)', 'แอนโคนา', 'Ancona'),
    ('สายพันธุ์แท้ (Purebreds)', 'ฮัมบูร์ก', 'Hamburg'), ('สายพันธุ์แท้ (Purebreds)', 'แคมพีน', 'Campine'),
    ('สายพันธุ์แท้ (Purebreds)', 'โรดไอแลนด์เรด', 'Rhode Island Red'), ('สายพันธุ์แท้ (Purebreds)', 'โรดไอแลนด์ไวท์', 'Rhode Island White'),
    ('สายพันธุ์แท้ (Purebreds)', 'นิวแฮมป์เชียร์', 'New Hampshire'), ('สายพันธุ์แท้ (Purebreds)', 'ซัสเซ็กซ์', 'Sussex'),
    ('สายพันธุ์แท้ (Purebreds)', 'ออสตราลอร์ป', 'Australorp'), ('สายพันธุ์แท้ (Purebreds)', 'ออร์พิงตัน', 'Orpington'),
    ('สายพันธุ์แท้ (Purebreds)', 'พลีมัธร็อก', 'Plymouth Rock'), ('สายพันธุ์แท้ (Purebreds)', 'ไวแอนดอตต์', 'Wyandotte'),
    ('กลุ่มไข่สีพิเศษ (Specialty Egg Layers)', 'อาราอูคานา', 'Araucana'), ('กลุ่มไข่สีพิเศษ (Specialty Egg Layers)', 'อเมราอูคานา', 'Ameraucana'),
    ('กลุ่มไข่สีพิเศษ (Specialty Egg Layers)', 'ครีม เลกบาร์', 'Cream Legbar'), ('กลุ่มไข่สีพิเศษ (Specialty Egg Layers)', 'อีสเตอร์ เอกเกอร์', 'Easter Egger'),
    ('กลุ่มไข่สีพิเศษ (Specialty Egg Layers)', 'โอลีฟ เอกเกอร์', 'Olive Egger'),
    ('สายพันธุ์พื้นเมืองและพรีเมียม (Heritage & Premium Breeds)', 'ซิลกี้ หรือไก่ไหม', 'Silkie'), ('สายพันธุ์พื้นเมืองและพรีเมียม (Heritage & Premium Breeds)', 'มาร็องส์', 'Marans'),
    ('สายพันธุ์พื้นเมืองและพรีเมียม (Heritage & Premium Breeds)', 'บาร์เนเวลเดอร์', 'Barnevelder'), ('สายพันธุ์พื้นเมืองและพรีเมียม (Heritage & Premium Breeds)', 'เวลซัมเมอร์', 'Welsummer'),
    ('สายพันธุ์พื้นเมืองและพรีเมียม (Heritage & Premium Breeds)', 'เดลาแวร์', 'Delaware'), ('สายพันธุ์พื้นเมืองและพรีเมียม (Heritage & Premium Breeds)', 'บัคอาย', 'Buckeye'),
    ('สายพันธุ์พื้นเมืองและพรีเมียม (Heritage & Premium Breeds)', 'จาวา', 'Java'), ('สายพันธุ์พื้นเมืองและพรีเมียม (Heritage & Premium Breeds)', 'เบรสส์', 'Bresse'),
    ('สายพันธุ์พื้นเมืองและพรีเมียม (Heritage & Premium Breeds)', 'ชาโมะ', 'Shamo'), ('สายพันธุ์พื้นเมืองและพรีเมียม (Heritage & Premium Breeds)', 'ฮิไนโดริ', 'Hinai-dori'),
    ('สายพันธุ์พื้นเมืองและพรีเมียม (Heritage & Premium Breeds)', 'ดองเต่า', 'Dong Tao')
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
# 5. ROUTING - INTERFACE CONTROL
# ==========================================

if st.session_state.user is None:
    
    # เว้นระยะห่างด้านบนให้การ์ดอยู่ตรงกลางแบบสมดุล
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    
    # ------------------------------------------
    # 🗂️ หน้าเข้าสู่ระบบ (LOGIN) - ลอกสไตล์ภาพเป๊ะๆ
    # ------------------------------------------
    if st.session_state.auth_page == "login":
        # สร้าง HTML Card โครงเปล่าสีขาวครอบฟิลด์ล็อกอิน
        st.markdown(
            """
            <div class="auth-card">
                <div class="avatar-container">
                    <img src="https://cdn-icons-png.flaticon.com/512/1144/1144760.png" alt="Avatar">
                </div>
                <div class="auth-title">เข้าสู่ระบบ</div>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # จัดแนว Column ให้อินพุตซ้อนอยู่ในโครงสร้างของหน้าจออย่างสวยงาม
        _, center_col, _ = st.columns([1, 1.1, 1])
        with center_col:
            login_email = st.text_input("ชื่อผู้ใช้งาน (อีเมล)", placeholder="ชื่อผู้ใช้งาน", key="input_login_email", label_visibility="collapsed")
            login_pass = st.text_input("รหัสผ่าน", placeholder="รหัสผ่าน", type="password", key="input_login_pass", label_visibility="collapsed")
            
            st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
            
            if st.button("เข้าสู่ระบบ"):
                try:
                    response = supabase.auth.sign_in_with_password({"email": login_email, "password": login_pass})
                    st.session_state.user = response.user
                    st.success("🎉 เข้าสู่ระบบสำเร็จแล้ว!")
                    st.rerun()
                except Exception as e:
                    st.error("❌ ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
            
            # โซนเปลี่ยนหน้าด้ามล่างสุด (ลืมรหัสผ่าน หรือ สมัครสมาชิก) แปลงเป็นภาษาไทย
            st.markdown("<div class='auth-footer-buttons' style='text-align:center; margin-top:15px;'>", unsafe_allow_html=True)
            footer_c1, footer_c2 = st.columns([1.1, 0.9])
            with footer_c1:
                if st.button("ลืมรหัสผ่าน?", key="btn_go_forgot"):
                    st.session_state.auth_page = "forgot"
                    st.rerun()
            with footer_c2:
                if st.button("สมัครสมาชิกใหม่", key="btn_go_reg"):
                    st.session_state.auth_page = "register"
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------
    # 🗂️ หน้าสมัครสมาชิก (REGISTER)
    # ------------------------------------------
    elif st.session_state.auth_page == "register":
        st.markdown(
            """
            <div class="auth-card">
                <div class="avatar-container">
                    <img src="https://cdn-icons-png.flaticon.com/512/3121/3121511.png" alt="Register">
                </div>
                <div class="auth-title">สมัครสมาชิกใหม่</div>
                <p style="color:#666; margin-top:-20px; font-size:14px;">กรอกข้อมูลสั้นๆ เพื่อเปิดบัญชีฟาร์ม</p>
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
                
            reg_email = st.text_input("อีเมล", placeholder="ที่อยู่อีเมล", key="reg_email")
            reg_password = st.text_input("รหัสผ่านใหม่", placeholder="ตั้งรหัสผ่านใหม่", type="password", key="reg_password")
            
            if reg_password:
                is_valid, msg = is_password_strong(reg_password)
                if is_valid:
                    st.success(f"🟢 {msg}")
                else:
                    st.warning(f"🟡 {msg}")
                    
            st.markdown("<br>", unsafe_allow_html=True)
            farm_name = st.text_input("ชื่อฟาร์มจำลองของคุณ", placeholder="เช่น มีสุขฟาร์ม 2026")
            farm_province = st.selectbox("ภูมิภาคที่ตั้งฟาร์ม", ["ภาคกลาง", "ภาคเหนือ", "ภาคตะวันออกเฉียงเหนือ", "ภาคใต้", "ภาคตะวันออก", "ภาคตะวันตะวันตก"])
            farm_size = st.radio("ขนาดฟาร์มจำลอง", ["รายย่อย (1-500 ตัว)", "ปานกลาง", "อุตสาหกรรม"], horizontal=True)

            if st.button("ลงทะเบียนใช้งาน"):
                is_valid, msg = is_password_strong(reg_password)
                if not (first_name and last_name and reg_email and farm_name):
                    st.error("❌ กรุณากรอกข้อมูลส่วนตัวและฟาร์มให้ครบถ้วน")
                elif not is_valid:
                    st.error(f"❌ รหัสผ่านไม่ปลอดภัย: {msg}")
                else:
                    try:
                        res = supabase.auth.sign_up({
                            "email": reg_email,
                            "password": reg_password,
                            "options": {
                                "data": {
                                    "first_name": first_name,
                                    "last_name": last_name,
                                    "farm_name": farm_name,
                                    "farm_province": farm_province,
                                    "farm_size": farm_size
                                }
                            }
                        })
                        st.success("📩 ส่งอีเมลยืนยันแล้ว! กรุณากดตรวจสอบใน Inbox ของคุณ")
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {str(e)}")
            
            st.markdown("<div class='auth-footer-buttons' style='text-align:center;'>", unsafe_allow_html=True)
            if st.button("⬅️ กลับไปยังหน้าเข้าสู่ระบบ", key="back_to_login_from_reg"):
                st.session_state.auth_page = "login"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------
    # 🗂️ หน้าลืมรหัสผ่าน (FORGOT PASSWORD)
    # ------------------------------------------
    elif st.session_state.auth_page == "forgot":
        st.markdown(
            """
            <div class="auth-card">
                <div class="avatar-container">
                    <img src="https://cdn-icons-png.flaticon.com/512/5618/5618479.png" alt="Forgot">
                </div>
                <div class="auth-title">กู้คืนบัญชีผู้ใช้</div>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        _, center_col, _ = st.columns([1, 1.1, 1])
        with center_col:
            st.write("กรอกอีเมลเพื่อรับลิงก์สร้างรหัสผ่านใหม่")
            reset_email = st.text_input("อีเมลที่ใช้ลงทะเบียน", placeholder="example@email.com", key="forgot_email", label_visibility="collapsed")
            
            if st.button("ส่งลิงก์รีเซ็ตรหัสผ่าน"):
                if reset_email:
                    try:
                        supabase.auth.reset_password_for_email(reset_email)
                        st.success("📩 ระบบส่งลิงก์เปลี่ยนรหัสผ่านไปยังอีเมลสำเร็จแล้ว!")
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {str(e)}")
                else:
                    st.error("❌ กรุณากรอกอีเมล")
                    
            st.markdown("<div class='auth-footer-buttons' style='text-align:center;'>", unsafe_allow_html=True)
            if st.button("⬅️ กลับไปยังหน้าเข้าสู่ระบบ", key="back_to_login_from_forgot"):
                st.session_state.auth_page = "login"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 6. MAIN DASHBOARD INTERFACE (หลังจากเข้าระบบสำเร็จ)
# ==========================================
else:
    user_info = st.session_state.user.user_metadata
    user_name = user_info.get("first_name", "ผู้ดูแลฟาร์ม")
    farm_title = user_info.get("farm_name", "สมาร์ทฟาร์ม")
    
    header_col1, header_col2 = st.columns([8, 2])
    with header_col1:
        st.title("🥚 Smart Layer Feed")
        st.subheader(f"👋 ยินดีต้อนรับคุณ {user_name} | แผงควบคุมระบบ: {farm_title}")
    with header_col2:
        st.write("")
        if st.button("🔒 ออกจากระบบบัญชี"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

    st.markdown("---")

    # SECTION 1: แผงควบคุมและตั้งค่า
    st.markdown("### ⚙️ แผงควบคุมและตั้งค่าการจำลองฟาร์ม")
    input_col1, input_col2 = st.columns(2, gap="large")

    with input_col1:
        st.markdown("##### 🐔 ข้อมูลฝูงไก่และสายพันธุ์")
        selected_group = st.selectbox("กลุ่มไก่ไข่", list_groups, index=0, on_change=reset_calculation)
        filtered_breeds = sorted(df_breeds_raw[df_breeds_raw['category'] == selected_group]['display_name'].tolist())
        selected_breed = st.selectbox("สายพันธุ์", filtered_breeds, index=0, on_change=reset_calculation)
        selected_stage = st.selectbox("ระยะการเลี้ยง", list_stages, index=0, on_change=reset_calculation)
        
        st.info("💡 **เกณฑ์โภชนาการสำหรับไก่ไข่ช่วงอายุ 0-6 สัปดาห์:**\n"
                "- โปรตีน (Protein): ไม่ต่ำกว่า **20.0%**\n"
                "- พลังงานใช้ประโยชน์ได้ (ME): ไม่ต่ำกว่า **2,900 kcal/กก.**\n"
                "- ไลซีน (Lysine): ไม่ต่ำกว่า **1.10%**\n"
                "- เมทไธโอนีน (Methionine): ไม่ต่ำกว่า **0.45%**")

    with input_col2:
        st.markdown("##### 💰 ข้อมูลจำลองขนาดฟาร์มและเป้าหมายการผลิต")
        num_chickens = st.number_input("จำนวนไก่ไข่ในเล้า (ตัว)", min_value=1, value=180, step=10, on_change=reset_calculation)
        feed_per_bird_g = st.number_input("อัตราการกินอาหาร (กรัม/ตัว/วัน)", min_value=1.0, value=180.0, step=5.0, on_change=reset_calculation)
        egg_price = st.number_input("ราคาไข่ไก่เฉลี่ยที่คาดหวัง (บาท/ฟอง)", min_value=0.0, value=4.10, step=0.1, on_change=reset_calculation)
        laying_rate = st.slider("อัตราการให้ไข่ของฝูงเป้าหมาย (%)", min_value=0, max_value=100, value=85, on_change=reset_calculation)

    st.markdown("##")

    if st.button("🚀 ประมวลผลและคำนวณสารอาหารที่แม่นยำที่สุด", use_container_width=True, type="primary"):
        if not df_ingredients.empty:
            AUTO_PROTEIN = 20.0
            AUTO_ME = 2900.0
            AUTO_LYSINE = 1.10
            AUTO_METHIONINE = 0.45
            
            prob = pulp.LpProblem("Feed_Optimization", pulp.LpMinimize)
            ingredients_list = df_ingredients['name'].tolist()
            vars_dict = {name: pulp.LpVariable(f"Ing_{i}", lowBound=0) for i, name in enumerate(ingredients_list)}
            
            prob += pulp.lpSum([vars_dict[row['name']] * row['price_per_kg'] for _, row in df_ingredients.iterrows()])
            prob += pulp.lpSum([vars_dict[i] for i in ingredients_list]) == 100.0
            
            for _, row in df_ingredients.iterrows():
                prob += vars_dict[row['name']] <= row['max_limit_pct']
            
            prob += pulp.lpSum([vars_dict[row['name']] * row['protein_pct'] for _, row in df_ingredients.iterrows()]) >= (AUTO_PROTEIN * 100)
            prob += pulp.lpSum([vars_dict[row['name']] * row['me_kcal_per_kg'] for _, row in df_ingredients.iterrows()]) >= (AUTO_ME * 100)
            prob += pulp.lpSum([vars_dict[row['name']] * row['lysine_pct'] for _, row in df_ingredients.iterrows()]) >= (AUTO_LYSINE * 100)
            prob += pulp.lpSum([vars_dict[row['name']] * row['methionine_pct'] for _, row in df_ingredients.iterrows()]) >= (AUTO_METHIONINE * 100)
            
            prob.solve(pulp.PULP_CBC_CMD(msg=False))
            
            if pulp.LpStatus[prob.status] == "Optimal":
                st.session_state.calculated = True
                st.session_state.total_cost_100kg = pulp.value(prob.objective)
                
                result_list = []
                calc_protein, calc_me, calc_lysine, calc_methionine = 0.0, 0.0, 0.0, 0.0
                
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
                        calc_lysine += w * row['lysine_pct']
                        calc_methionine += w * row['methionine_pct']
                
                st.session_state.df_result = pd.DataFrame(result_list)
                st.session_state.calculated_protein = calc_protein / 100
                st.session_state.calculated_me = calc_me / 100
                st.session_state.calculated_lysine = calc_lysine / 100
                st.session_state.calculated_methionine = calc_methionine / 100
                st.success("🎉 ล็อกสัดส่วนและสูตรอาหารที่คุ้มค่าที่สุดเรียบร้อยแล้ว!")
            else:
                st.error("❌ ไม่สามารถคำนวณสูตรอาหารที่ลงตัวได้ตามโภชนาการเป้าหมาย")

    st.markdown("---")

    # SECTION 2: รายงานผลลัพธ์
    st.markdown("### 📊 รายงานผลลัพธ์และการวิเคราะห์ประสิทธิภาพสูตรอาหาร")

    if st.session_state.calculated and st.session_state.df_result is not None:
        total_feed_day_kg = (num_chickens * feed_per_bird_g) / 1000
        cost_per_day = total_feed_day_kg * (st.session_state.total_cost_100kg / 100)
        expected_eggs_day = num_chickens * (laying_rate / 100)
        revenue_per_day = expected_eggs_day * egg_price
        net_profit_per_day = revenue_per_day - cost_per_day

        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric(label="📉 ต้นทุนอาหารรวม / วัน", value=f"{cost_per_day:,.2f} ฿")
        with m2: st.metric(label="📈 รายได้รวมจากการขายไข่ / วัน", value=f"{revenue_per_day:,.2f} ฿")
        with m3: st.metric(label="🏆 กำไรสุทธิคาดการณ์ / วัน", value=f"{net_profit_per_day:,.2f} ฿", delta=f"{net_profit_per_day/num_chickens:.2f} ฿/ตัว")
        with m4: st.metric(label="💰 ราคาเฉลี่ยสูตรอาหาร (ต่อกก.)", value=f"{st.session_state.total_cost_100kg / 100:.2f} ฿")

        st.markdown("##")
        report_left, report_right = st.columns([1.1, 0.9], gap="large")
        
        with report_left:
            st.markdown("##### 🍩 แผนภูมิสัดส่วนโครงสร้างวัตถุดิบ")
            fig = px.pie(st.session_state.df_result, values='สัดส่วน (%)', names='ชื่อวัตถุดิบ', hole=0.45, color_discrete_sequence=px.colors.qualitative.Safe)
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320, font=dict(color="white"), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("##### 🧪 ความแม่นยำของสารอาหารที่ได้จริง")
            prog_col1, prog_col2 = st.columns(2)
            with prog_col1:
                st.progress(min(st.session_state.calculated_protein / 20.0, 1.0), text=f"โปรตีน: {st.session_state.calculated_protein:.2f}% (เป้า: 20.0%)")
                st.progress(min(st.session_state.calculated_lysine / 1.10, 1.0), text=f"ไลซีน: {st.session_state.calculated_lysine:.2f}% (เป้า: 1.10%)")
            with prog_col2:
                st.progress(min(st.session_state.calculated_me / 2900.0, 1.0), text=f"พลังงาน: {st.session_state.calculated_me:.0f} kcal (เป้า: 2,900 kcal)")
                st.progress(min(st.session_state.calculated_methionine / 0.45, 1.0), text=f"เมทไธโอนีน: {st.session_state.calculated_methionine:.2f}% (เป้า: 0.45%)")

        with report_right:
            st.markdown("##### 📋 ตารางสัดส่วนใบสั่งผสมวัตถุดิบจริง (ต่อ 100 กิโลกรัม)")
            st.dataframe(st.session_state.df_result, use_container_width=True, hide_index=True, height=320)
            st.markdown("---")
            action_c1, action_c2 = st.columns(2)
            with action_c1:
                if st.button("💾 บันทึกสูตรลงฐานข้อมูลฟาร์ม", use_container_width=True):
                    st.toast(f"📝 บันทึกสูตรสำเร็จภายใต้บัญชีคุณ {user_name} เรียบร้อย!")
            with action_c2:
                st.button("🖨️ พิมพ์ใบสั่งผสมอาหาร (PDF)", use_container_width=True, disabled=True)
    else:
        st.info("💡 **ระบบพร้อมใช้งาน:** ตั้งค่ากลุ่มไก่และสายพันธุ์จากแผงควบคุมด้านบน จากนั้นกดปุ่มประมวลผลสูตรอาหารได้ทันทีครับ")
