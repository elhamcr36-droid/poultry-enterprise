import streamlit as st
import pandas as pd
import pulp
import plotly.express as px

# ==========================================
# 1. PAGE CONFIGURATION & THEME
# ==========================================
st.set_page_config(
    layout="wide", 
    page_title="Smart Layer Feed - ระบบคำนวณสูตรอาหารไก่ไข่อัจฉริยะ",
    page_icon="🥚"
)

# ==========================================
# 2. CUSTOM CSS FOR BACKGROUND & UI
# ==========================================
def add_background():
    st.markdown(
        """
        <style>
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: transparent !important;
        }
        .stApp::before {
            content: "";
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background-image: url("https://images.unsplash.com/photo-1516448620398-c5f44bf9f441?auto=format&fit=crop&q=80&w=1920");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
            opacity: 0.12; 
            z-index: -1;
        }
        div[data-testid="stGridColumn"] > div {
            background-color: rgba(25, 25, 25, 0.88) !important; 
            padding: 25px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.12);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(12px);
        }
        label, [data-testid="stWidgetLabel"] p {
            color: #ffffff !important;
            font-weight: 500 !important;
        }
        div[data-testid="stMetric"] {
            background-color: rgba(0, 0, 0, 0.65) !important;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #ffaa00;
        }
        [data-testid="stMetricValue"] {
            font-weight: bold;
            color: #ffaa00 !important;
        }
        [data-testid="stMetricLabel"] {
            color: #e0e0e0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

add_background()

# ==========================================
# 3. HARDCODED DATA (แทนการดึงจาก SUPABASE)
# ==========================================

# --- 3.1 ข้อมูลวัตถุดิบ (Ingredients) ครบทุกตัวตามหมวดหมู่ใน SQL ---
raw_ingredients = [
    # พลังงาน
    ('พลังงาน', 'ข้าวโพด', 'Corn'), ('พลังงาน', 'ข้าวฟ่าง', 'Sorghum'), ('พลังงาน', 'ข้าวสาลี', 'Wheat'),
    ('พลังงาน', 'ข้าวบาร์เลย์', 'Barley'), ('พลังงาน', 'ข้าวโอ๊ต', 'Oat'), ('พลังงาน', 'ข้าวไรย์', 'Rye'),
    ('พลังงาน', 'ข้าวเปลือก', 'Paddy Rice'), ('พลังงาน', 'ปลายข้าว', 'Broken Rice'), ('พลังงาน', 'รำละเอียด', 'Rice Bran'),
    ('พลังงาน', 'รำหยาบ', 'Rice Polish'), ('พลังงาน', 'รำสกัดน้ำมัน', 'Defatted Rice Bran'), ('พลังงาน', 'มันสำปะหลังเส้น', 'Cassava Chips'),
    ('พลังงาน', 'มันสำปะหลังบด', 'Cassava Meal'), ('พลังงาน', 'กากมันสำปะหลัง', 'Cassava Pulp'), ('พลังงาน', 'มันเทศ', 'Sweet Potato'),
    ('พลังงาน', 'กากน้ำตาล', 'Molasses'), ('พลังงาน', 'แป้งข้าวโพด', 'Corn Starch'), ('พลังงาน', 'แป้งสาลี', 'Wheat Flour'),
    # โปรตีนจากพืช
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
    # โปรตีนจากสัตว์
    ('โปรตีนจากสัตว์', 'ปลาป่น', 'Fish Meal'), ('โปรตีนจากสัตว์', 'เนื้อป่น', 'Meat Meal'),
    ('โปรตีนจากสัตว์', 'เนื้อและกระดูกป่น', 'Meat and Bone Meal'), ('โปรตีนจากสัตว์', 'เลือดป่น', 'Blood Meal'),
    ('โปรตีนจากสัตว์', 'ขนนกป่น', 'Feather Meal'), ('โปรตีนจากสัตว์', 'เครื่องในสัตว์ปีกป่น', 'Poultry By-Product Meal'),
    ('โปรตีนจากสัตว์', 'กุ้งป่น', 'Shrimp Meal'), ('โปรตีนจากสัตว์', 'ปูป่น', 'Crab Meal'),
    ('โปรตีนจากสัตว์', 'หอยป่น', 'Shellfish Meal'), ('โปรตีนจากสัตว์', 'แมลงป่น', 'Insect Meal'),
    ('โปรตีนจากสัตว์', 'หนอนแมลงวันลายป่น', 'Black Soldier Fly Meal'), ('โปรตีนจากสัตว์', 'ไส้เดือนป่น', 'Earthworm Meal'),
    # แร่ธาตุ
    ('แร่ธาตุ', 'หินปูนบด', 'Limestone'), ('แร่ธาตุ', 'เปลือกหอยบด', 'Ground Oyster Shell'),
    ('แร่ธาตุ', 'เปลือกไข่บด', 'Eggshell Meal'), ('แร่ธาตุ', 'ไดแคลเซียมฟอสเฟต', 'Dicalcium Phosphate'),
    ('แร่ธาตุ', 'โมโนแคลเซียมฟอสเฟต', 'Monocalcium Phosphate'), ('แร่ธาตุ', 'กระดูกป่น', 'Bone Meal'),
    ('แร่ธาตุ', 'เกลือ', 'Salt'), ('แร่ธาตุ', 'โซเดียมไบคาร์บอเนต', 'Sodium Bicarbonate'),
    ('แร่ธาตุ', 'โพแทสเซียมคลอไรด์', 'Potassium Chloride'), ('แร่ธาตุ', 'แมกนีเซียมออกไซด์', 'Magnesium Oxide'),
    # กรดอะมิโน
    ('กรดอะมิโน', 'ดีแอล-เมไทโอนีน', 'DL-Methionine'), ('กรดอะมิโน', 'แอล-ไลซีน เอชซีแอล', 'L-Lysine HCl'),
    ('กรดอะมิโน', 'แอล-ไลซีน ซัลเฟต', 'L-Lysine Sulfate'), ('กรดอะมิโน', 'แอล-ทรีโอนีน', 'L-Threonine'),
    ('กรดอะมิโน', 'แอล-ทริปโตเฟน', 'L-Tryptophan'), ('กรดอะมิโน', 'แอล-วาลีน', 'L-Valine'),
    ('กรดอะมิโน', 'แอล-ไอโซลิวซีน', 'L-Isoleucine'), ('กรดอะมิโน', 'แอล-อาร์จินีน', 'L-Arginine'),
    # วิตามิน
    ('วิตามิน', 'วิตามินเอ', 'Vitamin A'), ('วิตามิน', 'วิตามินดี3', 'Vitamin D3'), ('วิตามิน', 'วิตามินอี', 'Vitamin E'),
    ('วิตามิน', 'วิตามินเค3', 'Vitamin K3'), ('วิตามิน', 'วิตามินบี1', 'Vitamin B1'), ('วิตามิน', 'วิตามินบี2', 'Vitamin B2'),
    ('วิตามิน', 'วิตามินบี6', 'Vitamin B6'), ('วิตามิน', 'วิตามินบี12', 'Vitamin B12'), ('วิตามิน', 'ไนอาซิน', 'Niacin'),
    ('วิตามิน', 'กรดโฟลิก', 'Folic Acid'), ('วิตามิน', 'ไบโอติน', 'Biotin'), ('วิตามิน', 'กรดแพนโททีนิก', 'Pantothenic Acid'),
    ('วิตามิน', 'โคลีนคลอไรด์', 'Choline Chloride'),
    # แร่ธาตุรอง
    ('แร่ธาตุรอง', 'เหล็ก', 'Iron'), ('แร่ธาตุรอง', 'สังกะสี', 'Zinc'), ('แร่ธาตุรอง', 'แมงกานีส', 'Manganese'),
    ('แร่ธาตุรอง', 'ทองแดง', 'Copper'), ('แร่ธาตุรอง', 'ไอโอดีน', 'Iodine'), ('แร่ธาตุรอง', 'ซีลีเนียม', 'Selenium'),
    ('แร่ธาตุรอง', 'โคบอลต์', 'Cobalt'),
    # ไขมันและน้ำมัน
    ('ไขมันและน้ำมัน', 'น้ำมันปาล์ม', 'Palm Oil'), ('ไขมันและน้ำมัน', 'น้ำมันถั่วเหลือง', 'Soybean Oil'),
    ('ไขมันและน้ำมัน', 'น้ำมันข้าวโพด', 'Corn Oil'), ('ไขมันและน้ำมัน', 'น้ำมันคาโนลา', 'Canola Oil'),
    ('ไขมันและน้ำมัน', 'น้ำมันดอกทานตะวัน', 'Sunflower Oil'), ('ไขมันและน้ำมัน', 'น้ำมันปลา', 'Fish Oil'),
    ('ไขมันและน้ำมัน', 'ไขมันสัตว์', 'Animal Fat'), ('ไขมันและน้ำมัน', 'น้ำมันมะพร้าว', 'Coconut Oil'),
    # วัตถุดิบทางเลือก
    ('วัตถุดิบทางเลือก', 'ใบกระถินป่น', 'Leucaena Leaf Meal'), ('วัตถุดิบทางเลือก', 'ใบมะรุมป่น', 'Moringa Leaf Meal'),
    ('วัตถุดิบทางเลือก', 'ใบมันสำปะหลังป่น', 'Cassava Leaf Meal'), ('วัตถุดิบทางเลือก', 'ใบอัลฟัลฟาป่น', 'Alfalfa Meal'),
    ('วัตถุดิบทางเลือก', 'ผักตบชวาแห้ง', 'Dried Water Hyacinth'), ('วัตถุดิบทางเลือก', 'สาหร่ายทะเล', 'Seaweed Meal'),
    ('วัตถุดิบทางเลือก', 'แหนแดง', 'Azolla'), ('วัตถุดิบทางเลือก', 'จอกแหน', 'Duckweed'),
    ('วัตถุดิบทางเลือก', 'ต้นกล้วยหมัก', 'Fermented Banana Stem'), ('วัตถุดิบทางเลือก', 'หญ้าเนเปียร์หมัก', 'Fermented Napier Grass'),
    ('วัตถุดิบทางเลือก', 'กากเบียร์', "Brewer's Grain"), ('วัตถุดิบทางเลือก', 'กากยีสต์', 'Yeast Residue'),
    ('วัตถุดิบทางเลือก', 'กากกาแฟ', 'Coffee Pulp'), ('วัตถุดิบทางเลือก', 'กากชา', 'Tea Residue'),
    ('วัตถุดิบทางเลือก', 'กากผลไม้', 'Fruit Pomace'), ('วัตถุดิบทางเลือก', 'เศษผักผลไม้', 'Vegetable and Fruit Waste'),
    # สารเสริมอาหาร
    ('สารเสริมอาหาร', 'เอนไซม์', 'Enzyme'), ('สารเสริมอาหาร', 'โปรไบโอติก', 'Probiotic'), ('สารเสริมอาหาร', 'พรีไบโอติก', 'Prebiotic'),
    ('สารเสริมอาหาร', 'ยีสต์', 'Yeast'), ('สารเสริมอาหาร', 'สารต้านเชื้อรา', 'Antifungal Agent'),
    ('สารเสริมอาหาร', 'สารกันหืน', 'Antioxidant'), ('สารเสริมอาหาร', 'สารจับสารพิษ', 'Mycotoxin Binder'),
    ('สารเสริมอาหาร', 'กรดอินทรีย์', 'Organic Acid'), ('สารเสริมอาหาร', 'สารเพิ่มการย่อย', 'Digestive Enhancer'),
    ('สารเสริมอาหาร', 'สารเพิ่มสีไข่แดง', 'Yolk Pigment')
]

df_ingredients = pd.DataFrame(raw_ingredients, columns=['category', 'name_th', 'name_en'])
df_ingredients['name'] = df_ingredients['name_th'] + " (" + df_ingredients['name_en'] + ")"

# เติมตัวเลขทางโภชนาการจำลองเพื่อใช้คำนวณสมการ Optimization
df_ingredients['price_per_kg'] = 15.0
df_ingredients['protein_pct'] = 22.0
df_ingredients['me_kcal_per_kg'] = 3000.0
df_ingredients['lysine_pct'] = 1.2
df_ingredients['methionine_pct'] = 0.5
df_ingredients['max_limit_pct'] = 100.0


# --- 3.2 ข้อมูลสายพันธุ์ไก่ ครบทั้ง 45 สายพันธุ์ตาม SQL ---
raw_breeds = [
    # สายพันธุ์เชิงพาณิชย์
    ('สายพันธุ์เชิงพาณิชย์', 'ไฮไลน์ บราวน์', 'Hy-Line Brown'), ('สายพันธุ์เชิงพาณิชย์', 'ไฮไลน์ ดับเบิลยู-36', 'Hy-Line W-36'),
    ('สายพันธุ์เชิงพาณิชย์', 'โลห์มันน์ บราวน์', 'Lohmann Brown'), ('สายพันธุ์เชิงพาณิชย์', 'โลห์มันน์ แอลเอสแอล คลาสสิก', 'Lohmann LSL Classic'),
    ('สายพันธุ์เชิงพาณิชย์', 'ไอเอสเอ บราวน์', 'ISA Brown'), ('สายพันธุ์เชิงพาณิชย์', 'โนโวเจน บราวน์', 'Novogen Brown'),
    ('สายพันธุ์เชิงพาณิชย์', 'โนโวเจน ไวท์', 'Novogen White'), ('สายพันธุ์เชิงพาณิชย์', 'โบแวนส์ บราวน์', 'Bovans Brown'),
    ('สายพันธุ์เชิงพาณิชย์', 'โบแวนส์ ไวท์', 'Bovans White'), ('สายพันธุ์เชิงพาณิชย์', 'เดอแคลบ์ ไวท์', 'Dekalb White'),
    ('สายพันธุ์เชิงพาณิชย์', 'เชเวอร์ บราวน์', 'Shaver Brown'), ('สายพันธุ์เชิงพาณิชย์', 'ไฮเซกซ์ บราวน์', 'Hisex Brown'),
    ('สายพันธุ์เชิงพาณิชย์', 'ไฮเซกซ์ ไวท์', 'Hisex White'), ('สายพันธุ์เชิงพาณิชย์', 'นิค บราวน์', 'Nick Brown'),
    ('สายพันธุ์เชิงพาณิชย์', 'แบ็บค็อก บราวน์', 'Babcock Brown'),
    # สายพันธุ์แท้
    ('สายพันธุ์แท้', 'เลกฮอร์นขาว', 'White Leghorn'), ('สายพันธุ์แท้', 'เลกฮอร์นน้ำตาล', 'Brown Leghorn'),
    ('สายพันธุ์แท้', 'ไมนอร์กา', 'Minorca'), ('สายพันธุ์แท้', 'แอนโคนา', 'Ancona'),
    ('สายพันธุ์แท้', 'ฮัมบูร์ก', 'Hamburg'), ('สายพันธุ์แท้', 'แคมพีน', 'Campine'),
    ('สายพันธุ์แท้', 'โรดไอแลนด์เรด', 'Rhode Island Red'), ('สายพันธุ์แท้', 'โรดไอแลนด์ไวท์', 'Rhode Island White'),
    ('สายพันธุ์แท้', 'นิวแฮมป์เชียร์', 'New Hampshire'), ('สายพันธุ์แท้', 'ซัสเซ็กซ์', 'Sussex'),
    ('สายพันธุ์แท้', 'ออสตราลอร์ป', 'Australorp'), ('สายพันธุ์แท้', 'ออร์พิงตัน', 'Orpington'),
    ('สายพันธุ์แท้', 'พลีมัธร็อก', 'Plymouth Rock'), ('สายพันธุ์แท้', 'ไวแอนดอตต์', 'Wyandotte'),
    # กลุ่มไข่สีพิเศษ
    ('กลุ่มไข่สีพิเศษ', 'อาราอูคานา', 'Araucana'), ('กลุ่มไข่สีพิเศษ', 'อเมราอูคานา', 'Ameraucana'),
    ('กลุ่มไข่สีพิเศษ', 'ครีม เลกบาร์', 'Cream Legbar'), ('กลุ่มไข่สีพิเศษ', 'อีสเตอร์ เอกเกอร์', 'Easter Egger'),
    ('กลุ่มไข่สีพิเศษ', 'โอลีฟ เอกเกอร์', 'Olive Egger'),
    # สายพันธุ์พื้นเมืองและพรีเมียม
    ('สายพันธุ์พื้นเมืองและพรีเมียม', 'ซิลกี้ หรือไก่ไหม', 'Silkie'), ('สายพันธุ์พื้นเมืองและพรีเมียม', 'มาร็องส์', 'Marans'),
    ('สายพันธุ์พื้นเมืองและพรีเมียม', 'บาร์เนเวลเดอร์', 'Barnevelder'), ('สายพันธุ์พื้นเมืองและพรีเมียม', 'เวลซัมเมอร์', 'Welsummer'),
    ('สายพันธุ์พื้นเมืองและพรีเมียม', 'เดลาแวร์', 'Delaware'), ('สายพันธุ์พื้นเมืองและพรีเมียม', 'บัคอาย', 'Buckeye'),
    ('สายพันธุ์พื้นเมืองและพรีเมียม', 'จาวา', 'Java'), ('สายพันธุ์พื้นเมืองและพรีเมียม', 'เบรสส์', 'Bresse'),
    ('สายพันธุ์พื้นเมืองและพรีเมียม', 'ชาโมะ', 'Shamo'), ('สายพันธุ์พื้นเมืองและพรีเมียม', 'ฮิไนโดริ', 'Hinai-dori'),
    ('สายพันธุ์พื้นเมืองและพรีเมียม', 'ดองเต่า', 'Dong Tao')
]

df_breeds_raw = pd.DataFrame(raw_breeds, columns=['category', 'name_th', 'name_en'])
df_breeds_raw['display_name'] = df_breeds_raw['name_th'] + " (" + df_breeds_raw['name_en'] + ")"

# ดึงกลุ่มสายพันธุ์แบบไดนามิก
list_groups = sorted(df_breeds_raw['category'].unique().tolist())

list_stages = [
    "ช่วงอายุ แรกเกิด-6 สัปดาห์ (Starter 0-6 wk)",
    "ช่วงอายุ 6-12 สัปดาห์ (Grower 6-12 wk)",
    "ช่วงอายุ 12-18 สัปดาห์ (Developer 12-18 wk)",
    "ระยะไก่ไข่ให้ผลผลิต (Laying Period)"
]

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

def reset_calculation():
    st.session_state.calculated = False

# ==========================================
# 5. MAIN CONTENT & HEADER
# ==========================================
st.title("🥚 Smart Layer Feed")
st.subheader("ระบบคำนวณและวางแผนสูตรอาหารไก่ไข่อัจฉริยะด้วยปัญญาประดิษฐ์")
st.markdown("---")

# ==========================================
# SECTION 1: แผงควบคุมและตั้งค่า
# ==========================================
st.markdown("### ⚙️ แผงควบคุมและตั้งค่าการจำลองฟาร์ม")

input_col1, input_col2 = st.columns(2, gap="large")

with input_col1:
    st.markdown("##### 🐔 ข้อมูลฝูงไก่และสายพันธุ์")
    
    selected_group = st.selectbox("กลุ่มไก่ไข่", list_groups, index=0, on_change=reset_calculation)
    
    # กรองสายพันธุ์ตามกลุ่มที่เลือกแบบรวดเร็ว (ไม่ต้องโหลดผ่านเน็ต)
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

# ปุ่มเริ่มคำนวณสูตรอาหาร
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
            calc_protein = 0.0
            calc_me = 0.0
            calc_lysine = 0.0
            calc_methionine = 0.0
            
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
            st.error("❌ ไม่สามารถคำนวณหาจุดคุ้มค่าได้ คลังวัตถุดิบปัจจุบันอาจมีสารอาหารต่ำเกินไป หรือเงื่อนไขขัดกันเอง")

st.markdown("---")

# ==========================================
# SECTION 2: รายงานผลลัพธ์
# ==========================================
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
        fig = px.pie(
            st.session_state.df_result, 
            values='สัดส่วน (%)', 
            names='ชื่อวัตถุดิบ', 
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig.update_layout(
            margin=dict(t=10, b=10, l=10, r=10), 
            height=320, 
            font=dict(color="white"), 
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)'
        )
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
                st.toast("📝 บันทึกสูตรอาหารเรียบร้อยแล้ว (Simulated)!")
        with action_c2:
            st.button("🖨️ พิมพ์ใบสั่งผสมอาหาร (PDF)", use_container_width=True, disabled=True)
else:
    st.info("💡 **ระบบพร้อมใช้งาน:** ตั้งค่ากลุ่มไก่และสายพันธุ์จากแผงควบคุมด้านบน จากนั้นกดปุ่มประมวลผลสูตรอาหารได้ทันทีครับ")
