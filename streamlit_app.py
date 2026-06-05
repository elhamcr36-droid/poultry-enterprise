import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pulp
from datetime import datetime

# ==========================================
# 🔱 1. ตั้งค่าคอนฟิกแอปพลิเคชันและหน้าจอ (Application Configuration)
# ==========================================
st.set_page_config(
    page_title="Smart Layer Feed - ระบบคำนวณอาหารไก่ไข่อัจฉริยะ", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# แถบข้างซ้ายเหลือไว้เฉพาะการเชื่อมต่อ Cloud เท่านั้น เมนูนำทางเดิมในวงกลมแดงถูกย้ายออกแล้วตามภาพ edited-image.png
st.sidebar.markdown("### ☁️ การเชื่อมต่อคลาวด์ระดับองค์กร")
SUPABASE_URL = st.sidebar.text_input("ลิงก์โปรเจกต์ Supabase", "https://your-project.supabase.co").strip()
SUPABASE_KEY = st.sidebar.text_input("รหัสผ่าน API (Anon Key)", "your-anon-key", type="password").strip()

# ==========================================
# 🧭 ระบบปุ่มนำทางขนาดใหญ่แนวนอนด้านบนสุด (Top Tabs Navigation)
# ==========================================
st.markdown("# 🐔 Smart Layer Feed")
st.markdown("### ระบบคำนวณสูตรอาหารและบริหารจัดการฟาร์มไก่ไข่อัจฉริยะ")

# สร้างปุ่มกดขนาดใหญ่ด้านบนสุดเพื่อสลับหน้าจอแทนเมนูเดิมในแถบข้าง
page_tabs = st.tabs([
    "🏠 หน้าแรก & ตั้งค่าสายพันธุ์", 
    "🧠 คำนวณสูตรอาหาร (AI Optimizer)", 
    "📦 แผนการจัดซื้อวัตถุดิบ", 
    "📈 สถิติผลผลิต & บัญชีฟาร์ม"
])

# ==========================================
# 📋 2. ฐานข้อมูลโภชนาการเป้าหมายและวัตถุดิบ (จัดเต็ม 15 ชนิด + สารอาหารครบทุกมิติ)
# ==========================================
STAGE_NUTRITION_TARGETS = {
    "starter": {"name": "ลูกไก่ไข่ 0 - 6 สัปดาห์ (Starter)", "protein": 20.0, "me": 2900.0, "calcium": 1.00, "phos": 0.45, "amino": 0.42, "fiber": 4.0, "fat": 3.5},
    "grower": {"name": "ไก่รุ่นไข่ 6 - 16 สัปดาห์ (Grower)", "protein": 16.0, "me": 2750.0, "calcium": 0.90, "phos": 0.40, "amino": 0.32, "fiber": 4.5, "fat": 3.0},
    "laying": {"name": "ไก่ไข่ระยะให้ผลผลิต 16 สัปดาห์ขึ้นไป (Laying)", "protein": 17.5, "me": 2750.0, "calcium": 4.10, "phos": 0.42, "amino": 0.38, "fiber": 4.0, "fat": 3.5}
}

if "ingredient_data" not in st.session_state:
    st.session_state.ingredient_data = {
        # 🌾 กลุ่มแหล่งพลังงาน (Carbohydrates)
        "ข้าวโพดบด": {"price": 13.5, "protein": 8.5, "me": 3300.0, "calcium": 0.02, "phos": 0.25, "amino": 0.18, "moisture": 12.0, "fiber": 2.2, "fat": 3.8, "tox_risk": 3, "min_limit": 20.0, "max_limit": 70.0},
        "รำละเอียด": {"price": 11.0, "protein": 12.0, "me": 2400.0, "calcium": 0.05, "phos": 1.35, "amino": 0.22, "moisture": 10.5, "fiber": 12.0, "fat": 13.0, "tox_risk": 3, "min_limit": 0.0, "max_limit": 30.0},
        "ปลายข้าว": {"price": 14.5, "protein": 8.0, "me": 3360.0, "calcium": 0.04, "phos": 0.10, "amino": 0.15, "moisture": 12.0, "fiber": 1.0, "fat": 1.5, "tox_risk": 1, "min_limit": 0.0, "max_limit": 40.0},
        "มันเส้นบด": {"price": 9.5, "protein": 2.0, "me": 3000.0, "calcium": 0.18, "phos": 0.09, "amino": 0.04, "moisture": 13.0, "fiber": 3.5, "fat": 0.5, "tox_risk": 2, "min_limit": 0.0, "max_limit": 20.0},
        
        # 🌿 กลุ่มแหล่งโปรตีนพืชและสัตว์ (Proteins)
        "กากถั่วเหลือง": {"price": 18.5, "protein": 44.0, "me": 2420.0, "calcium": 0.25, "phos": 0.60, "amino": 0.65, "moisture": 11.5, "fiber": 5.5, "fat": 1.5, "tox_risk": 1, "min_limit": 5.0, "max_limit": 40.0},
        "ปลาป่น": {"price": 32.0, "protein": 60.0, "me": 2850.0, "calcium": 5.00, "phos": 3.00, "amino": 0.95, "moisture": 10.0, "fiber": 1.0, "fat": 8.0, "tox_risk": 1, "min_limit": 0.0, "max_limit": 15.0},
        "กากเนื้อปาล์ม": {"price": 8.0, "protein": 15.0, "me": 1650.0, "calcium": 0.30, "phos": 0.60, "amino": 0.25, "moisture": 10.0, "fiber": 16.0, "fat": 7.0, "tox_risk": 2, "min_limit": 0.0, "max_limit": 10.0},
        "กากเบียร์แห้ง": {"price": 10.5, "protein": 26.0, "me": 2100.0, "calcium": 0.30, "phos": 0.50, "amino": 0.40, "moisture": 11.0, "fiber": 15.0, "fat": 6.0, "tox_risk": 2, "min_limit": 0.0, "max_limit": 10.0},
        "กากถั่วลิสง": {"price": 16.0, "protein": 45.0, "me": 2600.0, "calcium": 0.20, "phos": 0.55, "amino": 0.50, "moisture": 10.0, "fiber": 6.0, "fat": 1.8, "tox_risk": 4, "min_limit": 0.0, "max_limit": 10.0},

        # 🌽 กลุ่มไขมันและพลังงานเข้มข้น (Lipids)
        "น้ำมันปาล์มดิบ": {"price": 34.0, "protein": 0.0, "me": 8400.0, "calcium": 0.00, "phos": 0.00, "amino": 0.00, "moisture": 0.5, "fiber": 0.0, "fat": 99.0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 4.0},

        # 🦴 กลุ่มแร่ธาตุ กรดอะมิโน และวิตามิน (Minerals & Additives)
        "เปลือกหอยบด": {"price": 4.0, "protein": 0.0, "me": 0.0, "calcium": 38.00, "phos": 0.04, "amino": 0.00, "moisture": 0.5, "fiber": 0.0, "fat": 0.0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 12.0},
        "ไดแคลเซียมฟอสเฟต": {"price": 28.0, "protein": 0.0, "me": 0.0, "calcium": 21.00, "phos": 18.00, "amino": 0.00, "moisture": 1.0, "fiber": 0.0, "fat": 0.0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 5.0},
        "เกลือแกง": {"price": 6.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "amino": 0.00, "moisture": 1.0, "fiber": 0.0, "fat": 0.0, "tox_risk": 0, "min_limit": 0.1, "max_limit": 0.4},
        "กรดอะมิโนสังเคราะห์": {"price": 95.0, "protein": 0.0, "me": 0.0, "calcium": 0.00, "phos": 0.00, "amino": 99.00, "moisture": 0.2, "fiber": 0.0, "fat": 0.0, "tox_risk": 0, "min_limit": 0.0, "max_limit": 2.0},
        "พรีมิกซ์ไก่ไข่ (วิตามิน)": {"price": 120.0, "protein": 0.0, "me": 0.0, "calcium": 4.00, "phos": 1.00, "amino": 0.00, "moisture": 2.0, "fiber": 0.0, "fat": 0.0, "tox_risk": 0, "min_limit": 0.2, "max_limit": 0.5}
    }

BREED_PROFILES = {
    "1. กลุ่มไฮบริดสีน้ำตาลพาณิชย์ (Commercial Brown Hybrids)": {
        "Isa Brown": {"name": "ไอซ่า บราวน์ (Isa Brown)", "egg_color": "🤎 น้ำตาลเข้ม", "bg_color": "#b45309", "text_color": "#ffffff", "default_feed": 115, "desc": "เบอร์ 1 ในไทย ไข่ดก 300-320 ฟอง/ปี เปลือกหนา ทนความร้อนเมืองไทยได้ดีเยี่ยม"},
        "Hy-Line Brown": {"name": "ไฮไลน์ บราวน์ (Hy-Line Brown)", "egg_color": "🤎 น้ำตาลนวล", "bg_color": "#d97706", "text_color": "#ffffff", "default_feed": 110, "desc": "กินน้อย FCR ดีมาก อัตราผลิตสม่ำเสมอยาวนาน เปลือกแข็งแรงแตกยาก"},
        "Hisex Brown": {"name": "ไฮ-เซ็กส์ บราวน์ (Hisex Brown)", "egg_color": "🤎 น้ำตาลสว่าง", "bg_color": "#c2410c", "text_color": "#ffffff", "default_feed": 113, "desc": "สายพันธุ์อึด ให้ผลผลิตสูงช่วงต้นของการไข่เร็วมาก นิยมมากในฟาร์มระบบปิด"},
        "Bovans Brown": {"name": "โบแวนส์ บราวน์ (Bovans Brown)", "egg_color": "🤎 น้ำตาลเข้มจัด", "bg_color": "#9a3412", "text_color": "#ffffff", "default_feed": 114, "desc": "โครงสร้างแข็งแรง ปรับตัวเข้ากับสภาพแวดล้อมระบบเปิดได้ดี ไข่ฟองใหญ่ไซส์จัมโบ้"},
        "Novogen Brown": {"name": "โนโวเจน บราวน์ (Novogen Brown)", "egg_color": "🤎 น้ำตาลช็อกโกแลต", "bg_color": "#78350f", "text_color": "#ffffff", "default_feed": 112, "desc": "สายพันธุ์ฝรั่งเศส นิสัยเชื่อง เลี้ยงง่าย อัตราการจิกตีกระทบกระทั่งกันต่ำมาก"},
        "Lohmann Brown Classic": {"name": "โลห์แมน บราวน์ คลาสสิก", "egg_color": "🤎 น้ำตาลทอง", "bg_color": "#854d0e", "text_color": "#ffffff", "default_feed": 114, "desc": "สายพันธุ์เยอรมันยอดนิยม ปรับตัวเก่ง มีเสถียรภาพการไข่สูงและให้ขนาดไข่สม่ำเสมอ"},
        "Dekalb Brown": {"name": "เดคัลบ์ บราวน์ (Dekalb Brown)", "egg_color": "🤎 น้ำตาลเงา", "bg_color": "#a16207", "text_color": "#ffffff", "default_feed": 111, "desc": "ไข่ดกตั้งแต่สัปดาห์แรกๆ คุณภาพภายในของไข่ (ยูนิตฮอว์) ดีเด่น ไข่ขาวข้นเนื้อแน่น"}
    },
    "2. กลุ่มไฮบริดสีขาวพาณิชย์ (Commercial White Hybrids)": {
        "Hy-Line W-36": {"name": "ไฮไลน์ ดับบลิว-36 (Hy-Line W-36)", "egg_color": "🤍 ขาวสะอาด", "bg_color": "#f1f5f9", "text_color": "#0f172a", "default_feed": 101, "desc": "กินอาหารน้อยที่สุดในกลุ่มพาณิชย์ น้ำหนักตัวเบา ค่า FCR ต่ำมาก จัดการง่ายประหยัดทุน"},
        "Lohmann White": {"name": "โลห์แมน ไวท์ (Lohmann White)", "egg_color": "🤍 ขาวมุก", "bg_color": "#e2e8f0", "text_color": "#0f172a", "default_feed": 105, "desc": "ให้ผลผลิตเปอร์เซ็นต์ไข่สูงยาวนาน นิยมในอุตสาหกรรมแปรรูปไข่เหลว"},
        "Bovans White": {"name": "โบแวนส์ ไวท์ (Bovans White)", "egg_color": "🤍 ขาวนวล", "bg_color": "#cbd5e1", "text_color": "#0f172a", "default_feed": 104, "desc": "ทนต่อความเครียดในโรงเรือนหนาแน่นได้ดี ให้ไข่เปลือกขาวที่เหนียวและแตกหักยาก"},
        "Hisex White": {"name": "ไฮ-เซ็กส์ ไวท์ (Hisex White)", "egg_color": "🤍 ขาวเงา", "bg_color": "#94a3b8", "text_color": "#ffffff", "default_feed": 103, "desc": "สายพันธุ์เบา ไข่ดกจัดเฉลี่ยสูงสุดถึง 330 ฟอง/ปี ตอบสนองต่ออาหารโปรตีนสูงได้ยอดเยี่ยม"}
    },
    "3. กลุ่มสายพันธุ์แท้ / อนุรักษ์ (Pure Breeds & Heritage)": {
        "Rhode Island Red": {"name": "โรดไอแลนด์เรด (Rhode Island Red)", "egg_color": "🤎 น้ำตาลอ่อน", "bg_color": "#8b4513", "text_color": "#ffffff", "default_feed": 125, "desc": "ไก่เนื้อแน่นสีน้ำตาลแดง ขนเงางาม อึด ทนโรค ทนแดด เหมาะสำหรับเลี้ยงปล่อยธรรมชาติ"},
        "White Leghorn": {"name": "เลกฮอร์นขาว (White Leghorn)", "egg_color": "🤍 ขาวสะอาด", "bg_color": "#e2e8f0", "text_color": "#1e293b", "default_feed": 105, "desc": "ต้นตระกูลไก่ไข่ขาว ตัวเล็ก ปราดเปรียว บินเก่ง ตกใจง่าย ไม่ชอบให้ขังในที่แคับ"},
        "Barred Plymouth Rock": {"name": "บาร์ พลีมัธร็อค (Barred Rock)", "egg_color": "🤎 น้ำตาลอมชมพู", "bg_color": "#475569", "text_color": "#ffffff", "default_feed": 130, "desc": "ไก่ลายเสือตัวใหญ่ เป็นทั้งไก่เนื้อและไก่ไข่ (Dual-purpose) นิสัยเป็นมิตร เลี้ยงสวนหลังบ้านดี"},
        "Australorp": {"name": "ออสตร้าลอป (Black Australorp)", "egg_color": "🤎 น้ำตาลครีม", "bg_color": "#1e293b", "text_color": "#ffffff", "default_feed": 122, "desc": "ไก่สีดำขลับจากออสเตรเลีย อารมณ์ดี อึดทน เคยทำสถิติวางไข่ดกที่สุดในกลุ่มพันธุ์แท้ มักไข่ไม่หยุดแม้หน้าหนาว"}
    },
    "4. กลุ่มไก่ไข่แฟนซี / ไข่สีพิเศษ (Designer & Heritage Eggers)": {
        "Ameraucana": {"name": "อเมรอกาน่า (Ameraucana)", "egg_color": "🩵 ฟ้าพาสเทล / เขียวมินต์", "bg_color": "#0ea5e9", "text_color": "#ffffff", "default_feed": 110, "desc": "ไก่หน้าเครา มีเสน่ห์ที่ยีนพิเศษทำให้ไข่ออกมาเป็นสีฟ้าพาสเทล ตลาดพรีเมียมต้องการสูงและราคาแพง"},
        "Marans": {"name": "มารันส์ (Black Copper Marans)", "egg_color": "🤎 น้ำตาลช็อกโกแลตเข้มจัด", "bg_color": "#451a03", "text_color": "#ffffff", "default_feed": 120, "desc": "ฉายา 'ไข่ไก่ช็อกโกแลต' เปลือกไข่มีสีน้ำตาลไหม้เงางาม ฝรั่งเศสนิยมทานดิบเพราะเปลือกหนาเชื้อโรคเข้ายาก"},
        "Olive Egger": {"name": "โอลีฟ เอ็กเกอร์ (Olive Egger)", "egg_color": "💚 เขียวมะกอก / เขียวทหาร", "bg_color": "#3f6212", "text_color": "#ffffff", "default_feed": 115, "desc": "ไก่ลูกผสมสายดีไซเนอร์ (Marans x Ameraucana) ได้ไข่เปลือกสีเขียวมะกอกแปลกใหม่ ดึงดูดผู้บริโภคสายสุขภาพ"},
        "Easter Egger": {"name": "อีสเตอร์ เอ็กเกอร์ (Easter Egger)", "egg_color": "🌈 คละสี (ชมพู/เขียว/ฟ้า)", "bg_color": "#6366f1", "text_color": "#ffffff", "default_feed": 108, "desc": "ไก่ลูกผสมที่ไม่ได้จำกัดสายพันธุ์แท้ ให้ไข่ลุ้นสนุกคละสีพาสเทลในฝูงเดียวกัน เพิ่มมูลค่าการขายแบบกล่องแฟนซี"}
    },
    "5. กลุ่มไก่ไข่พื้นเมือง / พัฒนาโดยกรมปศุสัตว์ไทย (Thai Layer Breeds)": {
        "Pradu Hang Dam Taku": {"name": "ประดู่หางดำ (กรมปศุสัตว์)", "egg_color": "🧡 ครีมอมชมพู", "bg_color": "#14532d", "text_color": "#ffffff", "default_feed": 95, "desc": "ไก่พื้นเมืองแท้ของไทย ทนทานโรคระบาดและสภาพความร้อนชื้นได้ดีที่สุด ไข่ใบเล็กแต่ไข่แดงมันวาวฟองใหญ่"},
        "Kai Khai Krom Pa-Sut": {"name": "ไก่ไข่กรมปศุสัตว์ (สายพันธุ์พัฒนา)", "egg_color": "🤎 น้ำตาลอ่อนนวล", "bg_color": "#166534", "text_color": "#ffffff", "default_feed": 112, "desc": "ปรับปรุงพันธุ์โดยกรมปศุสัตว์ไทยเพื่อให้เกษตรกรรายย่อยเลี้ยงง่าย ทนทาน แแข็งแรง ไข่ดกเฉลี่ย 260-280 ฟอง/ปี"}
    },
    "6. กลุ่มไก่ไข่ขนาดเล็ก / พันธุ์จิ๋วทนร้อน (Miniature Layers & Game Fowls)": {
        "Japanese Bantam": {"name": "ไก่แจ้ญี่ปุ่น (Japanese Bantam)", "egg_color": "💛 ครีมขาวใบจิ๋ว", "bg_color": "#581c87", "text_color": "#ffffff", "default_feed": 55, "desc": "ไก่ไข่ขนาดมินิ กินอาหารน้อยมากเพียงครึ่งเดียวของไก่ปกติ เหมาะสำหรับฟาร์มทางเลือกที่เน้นขายไข่ใบเล็กตลาดออร์แกนิก"},
        "Thai Game Fowl": {"name": "ไก่ชนไทยสายประกวด/เพาะพันธุ์", "egg_color": "💛 ครีมไข่ไก่", "bg_color": "#4c1d95", "text_color": "#ffffff", "default_feed": 100, "desc": "สายพันธุ์ไก่ชนพื้นบ้าน เน้นเสริมสร้างกล้ามเนื้อ ความหนาแน่นกระดูก โครงสร้างเด่น และความสมบูรณ์พันธุ์"}
    }
}

LIFECYCLE_FEED_BUDGET = {"starter": 1.2, "grower": 2.8, "laying": 48.0}

# ==========================================
# 🛡️ 3. ระบบจัดการสถานะและป้องกัน Bug (Safe State Validation)
# ==========================================
if "selected_group" not in st.session_state: st.session_state.selected_group = list(BREED_PROFILES.keys())[0]
if st.session_state.selected_group not in BREED_PROFILES: st.session_state.selected_group = list(BREED_PROFILES.keys())[0]

if "selected_breed_key" not in st.session_state: st.session_state.selected_breed_key = list(BREED_PROFILES[st.session_state.selected_group].keys())[0]
if st.session_state.selected_breed_key not in BREED_PROFILES[st.session_state.selected_group]: st.session_state.selected_breed_key = list(BREED_PROFILES[st.session_state.selected_group].keys())[0]

if "current_key" not in st.session_state: st.session_state.current_key = "laying"
if "weather_env" not in st.session_state: st.session_state.weather_env = "🌡️ อากาศปกติ (25-32°C)"
if "chicken_count" not in st.session_state: st.session_state.chicken_count = 1000

# 🔥 [แก้ไขบั๊กล็อกอินแรกสุด] ป้องกัน AttributeError บังคับประกาศสถานะ use_phytase เป็น False ทันทีหากพึ่งเปิดแอป
if "use_phytase" not in st.session_state: 
    st.session_state.use_phytase = False

if "optimized_weights" not in st.session_state:
    st.session_state.optimized_weights = {name: 0.0 for name in st.session_state.ingredient_data.keys()}
    st.session_state.optimized_weights["ข้าวโพดบด"] = 52.0
    st.session_state.optimized_weights["กากถั่วเหลือง"] = 24.0
    st.session_state.optimized_weights["รำละเอียด"] = 14.0
    st.session_state.optimized_weights["ปลาป่น"] = 5.0
    st.session_state.optimized_weights["เปลือกหอยบด"] = 4.4
    st.session_state.optimized_weights["ไดแคลเซียมฟอสเฟต"] = 0.4
    st.session_state.optimized_weights["พรีมิกซ์ไก่ไข่ (วิตามิน)"] = 0.2

for name in st.session_state.ingredient_data.keys():
    if name not in st.session_state.optimized_weights:
        st.session_state.optimized_weights[name] = 0.0

def calculate_current_formulation():
    nut_calc = {"protein": 0.0, "me": 0.0, "calcium": 0.0, "phos": 0.0, "amino": 0.0, "fiber": 0.0, "fat": 0.0}
    cost, moisture, risk = 0.0, 0.0, 0.0
    for name, weight in st.session_state.optimized_weights.items():
        f = weight / 100.0
        ing = st.session_state.ingredient_data.get(name, {})
        if ing:
            nut_calc["protein"] += ing.get("protein", 0.0) * f
            nut_calc["me"] += ing.get("me", 0.0) * f
            nut_calc["calcium"] += ing.get("calcium", 0.0) * f
            nut_calc["phos"] += ing.get("phos", 0.0) * f
            nut_calc["amino"] += ing.get("amino", 0.0) * f
            nut_calc["fiber"] += ing.get("fiber", 0.0) * f
            nut_calc["fat"] += ing.get("fat", 0.0) * f
            cost += ing.get("price", 0.0) * f
            moisture += ing.get("moisture", 0.0) * f
            risk += ing.get("tox_risk", 0) * f
    return nut_calc, cost, moisture, risk

current_nutrition, current_formula_cost, total_moisture, total_risk_score = calculate_current_formulation()

# ==========================================
# 📥 4. ส่วนแสดงผลเนื้อหาแต่ละหน้าจอ (Tabs Navigation)
# ==========================================

# --- [แท็บที่ 1]: หน้าแรก & ตั้งค่าสายพันธุ์ ---
with page_tabs[0]:
    st.markdown("## 🏠 ข้อมูลสายพันธุ์หลักและสภาพแวดล้อมฟาร์ม")
    
    c_group, c_breed = st.columns(2)
    with c_group:
        st.session_state.selected_group = st.selectbox(
            "เลือกกลุ่มสายพันธุ์ไก่ไข่/ไก่ชน:", 
            list(BREED_PROFILES.keys()), 
            index=list(BREED_PROFILES.keys()).index(st.session_state.selected_group)
        )
    with c_breed:
        breed_options = BREED_PROFILES[st.session_state.selected_group]
        if st.session_state.selected_breed_key not in breed_options:
            st.session_state.selected_breed_key = list(breed_options.keys())[0]
        default_index = list(breed_options.keys()).index(st.session_state.selected_breed_key)
        st.session_state.selected_breed_key = st.selectbox(
            "สายพันธุ์หลักในโรงเรือน:", 
            options=list(breed_options.keys()), 
            index=default_index, 
            format_func=lambda x: breed_options[x]["name"]
        )
    
    breed_info = breed_options[st.session_state.selected_breed_key]
    st.markdown(f"""
    <div style='background-color:{breed_info['bg_color']}; padding:20px; border-radius:10px; color:{breed_info['text_color']}; margin-bottom:15px;'>
        <h3>🧬 สายพันธุ์ปัจจุบัน: {breed_info['name']}</h3>
        <b>🎨 สีเปลือกไข่:</b> {breed_info['egg_color']} | <b>🥣 อัตรากินอาหารเฉลี่ย:</b> {breed_info['default_feed']} กรัม/วัน/ตัว <br>
        <p style='margin: 10px 0;'><i>ℹ️ {breed_info['desc']}</i></p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### ⛅ การจัดการอายุและสภาพแวดล้อม")
    c_age, c_weather = st.columns(2)
    with c_age:
        st.session_state.current_key = st.selectbox(
            "เลือกช่วงอายุ/โปรไฟล์ของไก่:", 
            options=list(STAGE_NUTRITION_TARGETS.keys()), 
            index=list(STAGE_NUTRITION_TARGETS.keys()).index(st.session_state.current_key), 
            format_func=lambda x: STAGE_NUTRITION_TARGETS[x]["name"]
        )
    with c_weather:
        weather_list = ["🌡️ อากาศปกติ (25-32°C)", "🔥 อากาศร้อนจัด (> 32°C)", "❄️ อากาศหนาว (< 25°C)"]
        st.session_state.weather_env = st.radio(
            "สภาพอากาศและอุณหภูมิวันนี้:", 
            weather_list, 
            index=weather_list.index(st.session_state.weather_env), 
            horizontal=True
        )

    st.markdown("### 💧 ระบบคำนวณปริมาณน้ำดื่มประจำวัน (Water Calculator)")
    st.session_state.chicken_count = st.number_input("จำนวนไก่ในฟาร์มทั้งหมด (ตัว):", min_value=1, value=st.session_state.chicken_count, step=100)
    
    base_water = (breed_info['default_feed'] / 1000.0) * 2.2 if st.session_state.current_key == "laying" else 0.15
    calc_water = st.session_state.chicken_count * base_water
    if "ร้อนจัด" in st.session_state.weather_env:
        calc_water *= 1.25
        st.error("🔥 อากาศร้อนจัด! ระบบคำนวณให้ฝูงไก่ดื่มน้ำเพิ่มขึ้น 25% เพื่อลดภาวะขาดน้ำจากความเครียด")
    st.metric("ปริมาณน้ำที่ฝูงไก่ต้องบริโภคต่อวันรวม", f"{calc_water:,.1f} ลิตร (Liters)")


# --- [แท็บที่ 2]: คำนวณสูตรอาหาร (AI Optimizer ตัวเต็ม + กล่อง Responsive ราคางอกตามได้) ---
with page_tabs[1]:
    st.markdown("## 🧠 ห้องปฏิบัติการสูตรอาหาร & ปัญญาประดิษฐ์")
    
    target = STAGE_NUTRITION_TARGETS[st.session_state.current_key]
    density_factor = 1.08 if "ร้อนจัด" in st.session_state.weather_env else (0.95 if "หนาว" in st.session_state.weather_env else 1.0)
    adjusted_target = {
        "protein": target["protein"] * density_factor, "me": target["me"],
        "calcium": target["calcium"] * density_factor, "phos": target["phos"] * density_factor,
        "amino": target["amino"] * density_factor, "fiber": target.get("fiber", 4.0), "fat": target.get("fat", 3.5)
    }

    # 🔥 [แก้ไขส่วนในวงกลมแดงรูปภาพที่ 2] แสดงผลบล็อกราคารองรับแบบไดนามิก แถวละ 5 ช่องอัตโนมัติ ไม่จำกัดวัตถุดิบเดิมและวัตถุดิบใหม่
    st.markdown("#### 💰 ⚙️ อัปเดตราคาวัตถุดิบหน้าฟาร์มปัจจุบัน (บาท/กิโลกรัม)")
    all_ingredients = list(st.session_state.ingredient_data.keys())
    
    chunk_size = 5 
    for i in range(0, len(all_ingredients), chunk_size):
        chunk_slice = all_ingredients[i:i+chunk_size]
        cols = st.columns(len(chunk_slice))
        for idx, name in enumerate(chunk_slice):
            with cols[idx]:
                st.session_state.ingredient_data[name]["price"] = st.number_input(
                    f"{name}", min_value=0.0, 
                    value=float(st.session_state.ingredient_data[name]["price"]), 
                    step=0.1, key=f"p_{name}"
                )

    st.session_state.use_phytase = st.checkbox("🧪 ใส่เอนไซม์ไฟเตส (ลดเป้าหมายฟอสฟอรัสลง 0.10% อัตโนมัติ)", value=st.session_state.use_phytase)
    if st.session_state.use_phytase:
        adjusted_target["phos"] = max(0.30, adjusted_target["phos"] - 0.10)

    # ปุ่มรัน AI ลิเนียร์โปรแกรมมิ่งคำนวณราคาต่ำสุด
    if st.button("⚡ สั่งคำนวณสูตรอาหารต้นทุนต่ำที่สุดด้วย AI (Run AI Least-Cost Optimizer)"):
        prob = pulp.LpProblem("LeastCostLayerFeed", pulp.LpMinimize)
        ingredient_vars = {name: pulp.LpVariable(name, lowBound=data.get("min_limit", 0.0), upBound=data.get("max_limit", 100.0)) for name, data in st.session_state.ingredient_data.items()}
        
        # Objective Function: ต้นทุนต่ำที่สุด
        prob += pulp.lpSum([ingredient_vars[name] * (st.session_state.ingredient_data[name]["price"] / 100.0) for name in st.session_state.ingredient_data.keys()])
        # Constraints นํ้าหนักรวมต้องได้ 100%
        prob += pulp.lpSum([ingredient_vars[name] for name in st.session_state.ingredient_data.keys()]) == 100.0
        
        # Constraints คุณค่าโภชนาการสัตว์ครบทุกมิติจากระบบเดิม
        prob += pulp.lpSum([ingredient_vars[name] * (st.session_state.ingredient_data[name]["protein"] / 100.0) for name in st.session_state.ingredient_data.keys()]) >= adjusted_target["protein"]
        prob += pulp.lpSum([ingredient_vars[name] * (st.session_state.ingredient_data[name]["me"] / 100.0) for name in st.session_state.ingredient_data.keys()]) >= adjusted_target["me"]
        prob += pulp.lpSum([ingredient_vars[name] * (st.session_state.ingredient_data[name]["calcium"] / 100.0) for name in st.session_state.ingredient_data.keys()]) >= adjusted_target["calcium"]
        prob += pulp.lpSum([ingredient_vars[name] * (st.session_state.ingredient_data[name]["phos"] / 100.0) for name in st.session_state.ingredient_data.keys()]) >= adjusted_target["phos"]
        prob += pulp.lpSum([ingredient_vars[name] * (st.session_state.ingredient_data[name]["amino"] / 100.0) for name in st.session_state.ingredient_data.keys()]) >= adjusted_target["amino"]
        
        status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
        if pulp.LpStatus[status] == "Optimal":
            for name in st.session_state.ingredient_data.keys():
                st.session_state.optimized_weights[name] = round(ingredient_vars[name].varValue, 1)
            st.success("🎉 AI ค้นพบสัดส่วนสูตรที่ราคาประหยัดและสารอาหารปลอดภัยที่สุดแล้ว!")
            st.rerun()
        else:
            st.error("❌ เงื่อนไขสารอาหารแน่นเกินไป วัตถุดิบในคลังไม่พอผสานสูตรได้ กรุณาปรับเพิ่ม-ลดช่วงขีดจำกัด Min/Max Limit ของวัตถุดิบ")

    st.markdown("---")
    creator_left, creator_right = st.columns(2, gap="large")
    
    with creator_left:
        st.markdown("#### 🔧 1. สไลเดอร์ปรับสัดส่วนผสมด้วยมือ / เพิ่มวัตถุดิบเสริม")
        
        # ➕ ช่องไว้เพิ่มวัตถุดิบเองอิสระ (เพิ่มสารอาหารได้ครบถ้วนทุกลำดับ)
        with st.expander("➕ เพิ่มสารอาหารเสริม/วัตถุดิบตัวใหม่ที่คุณหาได้เอง"):
            with st.form("add_custom_ingredient_mega"):
                new_name = st.text_input("ชื่อวัตถุดิบใหม่ (เช่น รำหยาบ, ใบกระถินบด, ข้าวเปลือก):")
                n_p = st.number_input("ราคาแนะนำ (บาท/กก.):", value=10.0)
                n_pro = st.number_input("โปรตีน (%):", value=12.0)
                n_me = st.number_input("พลังงานใช้ประโยชน์ได้ (kcal/kg):", value=2200.0)
                n_ca = st.number_input("แคลเซียม (%):", value=0.1)
                n_ph = st.number_input("ฟอสฟอรัส (%):", value=0.2)
                n_fib = st.number_input("กากใยอาหาร (%):", value=4.0)
                n_fat = st.number_input("ไขมัน (%):", value=2.0)
                
                if st.form_submit_button("💾 บันทึกวัตถุดิบใหม่เข้าฐานระบบ"):
                    if new_name.strip() and new_name not in st.session_state.ingredient_data:
                        st.session_state.ingredient_data[new_name] = {
                            "price": n_p, "protein": n_pro, "me": n_me, "calcium": n_ca, "phos": n_ph, 
                            "amino": 0.2, "moisture": 11.0, "fiber": n_fib, "fat": n_fat, "tox_risk": 1, "min_limit": 0.0, "max_limit": 30.0
                        }
                        st.session_state.optimized_weights[new_name] = 0.0
                        st.success(f"เพิ่ม '{new_name}' เรียบร้อย ช่องกรอกราคาแถวด้านบนจะเปิดรองรับทันที!")
                        st.rerun()

        user_weights = {}
        for name in list(st.session_state.ingredient_data.keys()):
            val = float(st.session_state.optimized_weights.get(name, 0.0))
            user_weights[name] = st.slider(f"{name} (%)", 0.0, 100.0, val, step=0.1, key=f"form_sl_{name}")
        st.session_state.optimized_weights = user_weights

        total_sum = sum(user_weights.values())
        st.markdown(f"**🔢 น้ำหนักรวมสูตรตอนนี้:** `{total_sum:.1f}%` (เป้าหมายคือ 100%)")
        if not (99.9 <= total_sum <= 100.1):
            st.warning("⚠️ สัดส่วนรวมยังไม่ครบ 100% อาหารจะไม่สมบูรณ์ตามเกณฑ์เติบโต")

    with creator_right:
        st.markdown("#### 🩺 2. หน้าจอตรวจสอบระดับคุณค่าสารอาหารเรียลไทม์")
        nutrient_display = [
            ("🥩 โปรตีนรวม (Crude Protein)", "protein", "%"),
            ("⚡ พลังงานใช้ประโยชน์ได้ (ME)", "me", "kcal/kg"),
            ("🦴 แคลเซียม (Calcium)", "calcium", "%"),
            ("🧪 ฟอสฟอรัสที่เป็นประโยชน์ (Phosphorus)", "phos", "%"),
            ("🧬 กรดอะมิโนจำเป็นรวม (Amino Acids)", "amino", "%"),
            ("🌾 กากใยรวม (Crude Fiber)", "fiber", "%"),
            ("🌽 ไขมันรวม (Crude Fat)", "fat", "%")
        ]
        for label, key_name, unit in nutrient_display:
            cur = current_nutrition[key_name]
            req = adjusted_target.get(key_name, 1.0)
            st.write(f"**{label}**: {cur:.2f} / {req:.2f} {unit}")
            st.progress(min(max(cur / req, 0.0), 1.0) if req > 0 else 0.0)
            
        st.markdown("---")
        if total_moisture > 12.0:
            st.markdown(f"💧 **ความชื้นสะสมสูตร:** <span style='color:red;'>{total_moisture:.1f}% 🔴 เสี่ยงเกิดเชื้อราในอาหารสูง</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"💧 **ความชื้นสะสมสูตร:** <span style='color:green;'>{total_moisture:.1f}% 🟢 ปลอดภัย จัดเก็บง่าย</span>", unsafe_allow_html=True)
            
        st.metric("💰 ต้นทุนสูตรผสมอาหารปัจจุบันของคุณ", f"{current_formula_cost:.2f} บาท / กิโลกรัม")


# --- [แท็บที่ 3]: แผนการจัดซื้อวัตถุดิบ (ตัวเต็มดั้งเดิม) ---
with page_tabs[2]:
    st.markdown("## 📦 แผนจัดซื้อวัตถุดิบอาหารสัตว์และควบคุมความเสี่ยง")
    total_feed_needed_kg = st.session_state.chicken_count * LIFECYCLE_FEED_BUDGET[st.session_state.current_key]
    st.info(f"📊 ปริมาณอาหารรวมที่ฟาร์มคุณต้องเตรียมจัดสำรองรอบนี้: **{total_feed_needed_kg/1000.0:,.2f} ตัน** (ประเมินจากฝูงสัตว์ {st.session_state.chicken_count:,} ตัว)")
    
    budget_data = []
    for name, weight in st.session_state.optimized_weights.items():
        w_kg = (weight / 100.0) * total_feed_needed_kg
        if w_kg > 0:
            p_unit = st.session_state.ingredient_data.get(name, {}).get("price", 0.0)
            budget_data.append({
                "วัตถุดิบ": name, "สัดส่วน (%)": f"{weight}%",
                "ปริมาณรวมที่ต้องซื้อ (กก.)": round(w_kg, 1),
                "งบประมาณโดยประมาณ (บาท)": round(w_kg * p_unit, 2)
            })
            
    df_budget = pd.DataFrame(budget_data)
    if not df_budget.empty:
        st.dataframe(df_budget, use_container_width=True, hide_index=True)
        csv = df_budget.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 ดาวน์โหลดใบจัดซื้อวัตถุดิบอาหารสัตว์ (Download PO CSV)", data=csv, file_name="ใบจัดซื้อวัตถุดิบ_SmartLayer.csv", mime="text/csv")
    else:
        st.info("💡 สัดส่วนอาหารยังเป็น 0% กรุณาตั้งค่าอาหารที่หน้า AI Optimizer ก่อน")

    st.markdown("---")
    st.markdown("#### 🛡️ การบริหารจัดการความปลอดภัยทางชีวภาพ (Biosecurity Control)")
    if total_risk_score >= 2.0:
        st.error(f"⚠️ ดัชนีสารพิษเชื้อรารวมอยู่ที่ {total_risk_score:.2f} (เสี่ยงสูง) แนะนำให้ผสมสารจับสารพิษเชื้อรา (Toxin Binder) เพิ่มจำนวน {2.0 * (total_feed_needed_kg/1000.0):,.1f} กก. ผสมเข้าไปด้วยเพื่อความปลอดภัย")
    else:
        st.success("🟢 วัตถุดิบในสูตรมีความปลอดภัยจากสารพิษเชื้อราสูง จัดเก็บได้ตามมาตรฐาน")


# --- [แท็บที่ 4]: สถิติผลผลิต & บัญชีฟาร์ม (คำนวณ FCR ตัวเต็มย้อนหลัง) ---
with page_tabs[3]:
    st.markdown("## 📈 สมุดจดบันทึกสถิติและวิเคราะห์ผลกำไรฟาร์ม")
    if "tracker_data" not in st.session_state:
        st.session_state.tracker_data = pd.DataFrame([
            {"วันที่": "01/06", "สูตรอาหาร": "สูตรเดิม", "อัตราการไข่ (%)": 82.0, "อัตราไข่บุบแตก (%)": 4.5, "น้ำหนักไข่รวม (กก.)": 52.0, "ตาย/คัดทิ้ง (ตัว)": 0, "กำไรสุทธิวันนี้ (บาท)": 420.0},
            {"วันที่": "02/06", "สูตรอาหาร": "สูตรเดิม", "อัตราการไข่ (%)": 81.5, "อัตราไข่บุบแตก (%)": 5.0, "น้ำหนักไข่รวม (กก.)": 51.5, "ตาย/คัดทิ้ง (ตัว)": 1, "กำไรสุทธิวันนี้ (บาท)": 395.0},
        ])
    
    df_track = st.session_state.tracker_data.copy()
    daily_feed_consumed_kg = (st.session_state.chicken_count * breed_info['default_feed']) / 1000.0
    daily_feed_cost = daily_feed_consumed_kg * current_formula_cost
    
    # คำนวณ FCR และตัวชี้วัดรายวันย้อนหลัง
    df_track["FCR"] = (daily_feed_consumed_kg / df_track["น้ำหนักไข่รวม (กก.)"]).round(2)
    
    avg_lay = df_track["อัตราการไข่ (%)"].mean()
    total_profit_accum = df_track["กำไรสุทธิวันนี้ (บาท)"].sum()
    avg_fcr = df_track["FCR"].mean()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("🥚 อัตราการให้ไข่เฉลี่ย", f"{avg_lay:.1f} %")
    m2.metric("🥣 ประสิทธิภาพอาหาร (FCR เฉลี่ย)", f"{avg_fcr:.2f}")
    m3.metric("💵 กำไรสุทธิรวมสะสมรอบนี้", f"{total_profit_accum:,.1f} บาท")
    
    st.markdown("---")
    track_col1, track_col2 = st.columns([4, 6], gap="large")
    
    with track_col1:
        st.markdown("##### 📝 จดบันทึกผลผลิตประจำวัน")
        with st.form("ledger_input_mega_form"):
            in_date = st.text_input("วันที่บันทึก (เช่น 03/06):", value=datetime.now().strftime("%d/%m"))
            lay_r = st.number_input("อัตราการไข่วันนี้ (%):", value=84.0)
            crack_r = st.number_input("อัตราไข่แตกเสียหาย (%):", value=1.5)
            egg_w = st.number_input("น้ำหนักไข่รวมหน้าแผง (กก.):", value=53.0)
            dead_c = st.number_input("ไก่ตาย/คัดออกวันนี้ (ตัว):", value=0, step=1)
            
            st.success(f"💰 ต้นทุนค่าอาหารฝูงวันนี้ตามจริง: {daily_feed_cost:,.2f} บาท")
            estimated_rev = egg_w * 65.0
            suggested_profit = max(0.0, estimated_rev - daily_feed_cost)
            
            p_today = st.number_input("กำไรสุทธิประเมินวันนี้ (บาท):", value=round(suggested_profit, 2))
            
            if st.form_submit_button("💾 กดบันทึกข้อมูลเข้าฐานระบบ"):
                new_row = {
                    "วันที่": in_date, "สูตรอาหาร": "สูตรปัจจุบัน",
                    "อัตราการไข่ (%)": lay_r, "อัตราไข่บุบแตก (%)": crack_r, 
                    "น้ำหนักไข่รวม (กก.)": egg_w, "ตาย/คัดทิ้ง (ตัว)": dead_c, 
                    "กำไรสุทธิวันนี้ (บาท)": p_today
                }
                st.session_state.tracker_data = pd.concat([st.session_state.tracker_data, pd.DataFrame([new_row])], ignore_index=True)
                st.success("บันทึกข้อมูลสถิติประจำวันสำเร็จ!")
                st.rerun()
                
    with track_col2:
        st.markdown("##### 📊 กราฟวิเคราะห์แนวโน้มอัตราผลิตไข่")
        fig_prod = go.Figure()
        fig_prod.add_trace(go.Scatter(x=df_track["วันที่"], y=df_track["อัตราการไข่ (%)"], name="อัตราการไข่ (%)", line=dict(color='#22c55e', width=3)))
        fig_prod.add_trace(go.Bar(x=df_track["วันที่"], y=df_track["อัตราไข่บุบแตก (%)"], name="ไข่แตกเสียหาย (%)", marker_color='#ef4444', opacity=0.4))
        fig_prod.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=280, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_prod, use_container_width=True)

    st.markdown("##### 📄 ตารางบัญชีและสถิติประวัติย้อนหลัง (Historical Ledger)")
    st.dataframe(df_track, use_container_width=True, hide_index=True)

# ==========================================
# 🏁 ส่วนท้ายของแอปพลิเคชัน
# ==========================================
st.markdown("---")
st.markdown("<div style='text-align: center; color: #64748b; font-size: 0.8em;'>© 2026 Smart Layer Feed | แก้ไขปัญหา AttributeError สำหรับสถานะเริ่มต้นครบถ้วนเสร็จสมบูรณ์</div>", unsafe_allow_html=True)
