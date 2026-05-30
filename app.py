import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# ตั้งค่าหน้าเว็บให้เป็นแบบกว้าง (Wide mode)
st.set_page_config(layout="wide", page_title="คำนวณสูตรอาหารไก่ไข่อัจฉริยะ")

# นำเข้าฟอนต์ภาษาไทยเพื่อให้กราฟแสดงผลภาษาไทยได้ถูกต้อง (ปรับเปลี่ยนตามระบบของคุณ)
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Tahome', 'Leelawadee', 'Handthaifont', 'Arial']

# ==========================================
# SIDEBAR (แถบเมนูด้านข้าง)
# ==========================================
with st.sidebar:
    st.selectbox("Language / ภาษา", ["ไทย", "English"])
    st.write("👤 **ang sa**")
    st.caption("🟢 หน้าหลัก")
    if st.button("ออกจากระบบ", type="primary"):
        pass

# ==========================================
# MAIN CONTENT (เนื้อหาหลัก)
# ==========================================
st.title("🥚 คำนวณสูตรอาหารไก่ไข่อัจฉริยะ")

# แท็บเมนูด้านบน
tabs = st.tabs(["📊 คำนวณสูตรอาหาร", "⏳ ประวัติสูตรอาหาร", "🐓 ตัวชี้วัดฟาร์ม", "🌾 คลังวัตถุดิบ", "👥 จัดการสมาชิก", "ℹ️ เกี่ยวกับ"])

with tabs[0]: # ทำงานในแท็บ "คำนวณสูตรอาหาร"
    
    # แบ่งหน้าจอเป็น 2 คอลัมน์หลักตามภาพ (ซ้าย: ตั้งค่าและพยากรณ์รายได้ | ขวา: ผลลัพธ์และกำไร)
    col_left, col_right = st.columns([1, 1.2])

    # ------------------------------------------
    # คอลัมน์ซ้าย: ตั้งค่าเงื่อนไข & พยากรณ์รายได้
    # ------------------------------------------
    with col_left:
        st.subheader("⚙️ ตั้งค่าเงื่อนไข")
        
        st.selectbox("กลุ่มไก่ไข่", ["Commercial Brown Layer..."], index=0)
        st.selectbox("สายพันธุ์", ["อิซ่า บราวน์ (Isa Brown)"], index=0)
        st.selectbox("ระยะการเลี้ยง", ["ช่วงอายุ แรกเกิด-6 สัปดาห์ (Starter 0-6 wk)"], index=0)
        
        st.number_input("จำนวนไก่ไข่ (ตัว)", min_value=0, value=100, step=1)
        st.number_input("ปริมาณอาหารที่กิน (กรัม/ตัว/วัน)", min_value=0, value=100, step=1)
        
        st.write("เป้าหมายการคำนวณ")
        goal_option = st.radio(
            "เลือกเป้าหมาย",
            ["🔴 อาหารราคาถูกที่สุด (Best Price)", "⚫ สารอาหารตรงตามความต้องการที่สุด (Best Nutrition)"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        st.subheader("💰 พยากรณ์รายได้")
        st.number_input("ราคาไข่ไก่เฉลี่ย (บาท/ฟอง)", min_value=0.0, value=4.10, step=0.1)
        st.slider("อัตราการให้ไข่ (%)", min_value=0, max_value=100, value=85)
        
        if st.button("🚀 ประมวลผลสูตรอาหาร", use_container_width=True, type="primary"):
            st.success("คำนวณสำเร็จ!")

    # ------------------------------------------
    # คอลัมน์ขวา: ผลลัพธ์สัดส่วนวัตถุดิบ & พยากรณ์กำไร
    # ------------------------------------------
    with col_right:
        st.subheader("📊 ผลลัพธ์สัดส่วนวัตถุดิบ")
        st.info("สายพันธุ์: อิซ่า บราวน์ (Isa Brown) | ช่วงอายุ: แรกเกิด-6 สัปดาห์ (Starter 0-6 wk)")
        
        # ส่วนของกราฟวงกลม (Pie Chart) จำลองตามภาพ
        labels = ['มันสำปะหลังบด', 'ปลายข้าว', 'กากถั่วเหลือง']
        sizes = [60.62, 0.88, 38.51]
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
        
        fig, ax = plt.subplots(figsize=(4, 4))
        # กำหนดสีพื้นหลังของตัวกราฟให้เข้ากับหน้าเว็บ
        fig.patch.set_facecolor('#f0f2f6')
        ax.set_facecolor('#f0f2f6')
        
        wedges, texts, autotexts = ax.pie(
            sizes, 
            labels=labels, 
            autopct='%1.2f%%', 
            startangle=140, 
            colors=colors,
            textprops=dict(color="black", size=8)
        )
        # ปรับรูปแบบเป็น Donut Chart ตามภาพ
        centre_circle = plt.Circle((0,0),0.50,fc='#f0f2f6')
        fig.gca().add_artist(centre_circle)
        ax.axis('equal')  
        
        st.pyplot(fig)
        
        # ส่วนแสดงค่าโปรตีนและพลังงาน
        metric_col1, metric_col2 = st.columns(2)
        with metric_col1:
            st.metric(label="โปรตีนรวมที่ได้ (%)", value="20.00%")
            st.caption("🟢 Target: 20.00%")
        with metric_col2:
            st.metric(label="พลังงานรวมที่ได้ (kcal)", value="2900 kcal")
            st.caption("🟢 Target: 2900")
            
        # ตารางแสดงข้อมูลวัตถุดิบ
        data = {
            "ชื่อวัตถุดิบ": ["มันสำปะหลังบด", "ปลายข้าว", "กากถั่วเหลือง"],
            "สัดส่วน (%)": [60.6200, 0.8800, 38.5100],
            "ต้องใช้ (กก.)": [60.6200, 0.8800, 38.5100]
        }
        df = pd.DataFrame(data)
        st.table(df)
        
        st.markdown("---")
        
        # ส่วนพยากรณ์กำไรรายวัน
        st.subheader("📈 พยากรณ์กำไรรายวัน")
        
        profit_col1, profit_col2, profit_col3 = st.columns(3)
        with profit_col1:
            st.metric(label="ต้นทุนอาหาร/วัน", value="171.81 ฿")
        with profit_col2:
            st.metric(label="รายได้เฉลี่ย/วัน", value="365.50 ฿")
        with profit_col3:
            st.metric(label="กำไรสุทธิ/วัน", value="5,810.56 ฿")
            
        if st.button("💾 บันทึกสูตรอาหารและประวัติการคำนวณ", use_container_width=True):
            st.toast("บันทึกข้อมูลเรียบร้อยแล้ว!")
