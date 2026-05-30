import streamlit as st
import pandas as pd
import pulp
import plotly.express as px
from supabase import create_client, Client

# 1. Page Configuration & Theme
st.set_page_config(
    layout="wide", 
    page_title="Smart Layer Feed - ระบบคำนวณสูตรอาหารไก่ไข่อัจฉริยะ",
    page_icon="🥚"
)

# ดึงข้อมูลจาก Streamlit Secrets สำหรับเชื่อมต่อ Supabase
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

@st.cache_data(ttl=60)
def load_ingredients_from_supabase():
    try:
        response = supabase.table("ingredients").select(
            "name, price_per_kg, protein_pct, fat_pct, me_kcal_per_kg, lysine_pct, methionine_pct, max_limit_pct"
        ).execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"❌ ไม่สามารถดึงข้อมูลผ่าน API ของ Supabase ได้: {e}")
        return None

df_ingredients = load_ingredients_from_supabase()

# Initialize Session State
if "calculated" not in st.session_state:
    st.session_state.calculated = False
    st.session_state.df_result = None
    st.session_state.total_cost_100kg = 0.0
    st.session_state.calculated_protein = 0.0
    st.session_state.calculated_me = 0.0

# ==========================================
# SIDEBAR (เมนูด้านข้างสำหรับการจัดการระบบ)
# ==========================================
with st.sidebar:
    st.markdown("### 🌐 ตั้งค่าระบบ")
    st.selectbox("Language / ภาษา", ["ไทย", "English"], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("### 👤 ผู้ใช้งานปัจจุบัน")
    st.info("**ang sa**\n\nสถานะ: ผู้ดูแลระบบ (Admin)")
    st.caption("🟢 กำลังออนไลน์")
    if st.button("ออกจากระบบ", type="primary", use_container_width=True):
        pass

# ==========================================
# MAIN CONTENT & HEADER
# ==========================================
st.title("🥚 Smart Layer Feed")
st.subheader("ระบบคำนวณและวางแผนสูตรอาหารไก่ไข่อัจฉริยะด้วยปัญญาประดิษฐ์")

tabs = st.tabs([
    "📊 ประมวลผลสูตรอาหาร", 
    "⏳ ประวัติสูตรอาหาร", 
    "🐓 ตัวชี้วัดฟาร์ม", 
    "🌾 คลังวัตถุดิบ", 
    "👥 จัดการสมาชิก", 
    "ℹ️ เกี่ยวกับ"
])

# ------------------------------------------
# TAB 0: คำนวณสูตรอาหาร (Full-Width Redesign)
# ------------------------------------------
with tabs[0]:
    
    # ==========================================
    # SECTION 1: แผงควบคุมและตั้งค่า (เต็มหน้าจอ - FULL WIDTH)
    # ==========================================
    st.markdown("### ⚙️ แผงควบคุมและตั้งค่า (Control Panel)")
    
    # แบ่งกลุ่มข้อมูลออกเป็น 3 คอลัมน์ใหญ่เท่าๆ กันในแนวนอน
    input_col1, input_col2, input_col3 = st.columns(3, gap="medium")
    
    with input_col1:
        st.markdown("##### 🐔 ข้อมูลฝูงไก่และสายพันธุ์")
        st.selectbox("กลุ่มไก่ไข่", ["Commercial Brown Layer"], index=0)
        st.selectbox("สายพันธุ์", ["อิซ่า บราวน์ (Isa Brown)"], index=0)
        st.selectbox("ระยะการเลี้ยง", ["ช่วงอายุ แรกเกิด-6 สัปดาห์ (Starter 0-6 wk)"], index=0)
        num_chickens = st.number_input("จำนวนไก่ไข่ในเล้า (ตัว)", min_value=1, value=100, step=10)
        feed_per_bird_g = st.number_input("อัตราการกิน (กรัม/ตัว/วัน)", min_value=1.0, value=100.0, step=5.0)

    with input_col2:
        st.markdown("##### 🧬 โภชนาการเป้าหมาย (ต่ออาหาร 100 กก.)")
        goal_option = st.radio(
            "กลยุทธ์ที่ใช้คำนวณ",
            ["🎯 อาหารราคาถูกที่สุด (Best Price)", "✨ สารอาหารตรงตามสเปกที่สุด (Best Nutrition)"],
            horizontal=False
        )
        st.markdown("##") # ปรับระยะช่องไฟ
        target_protein = st.number_input("โปรตีนขั้นต่ำ (%)", min_value=0.0, value=20.0, step=0.5)
        target_me = st.number_input("พลังงานขั้นต่ำ (kcal/กก.)", min_value=0, value=2900, step=50)
        
    with input_col3:
        st.markdown("##### 💰 ข้อมูลตลาด & กรดอะมิโนสำคัญ")
        egg_price = st.number_input("ราคาไข่ไก่เฉลี่ย (บาท/ฟอง)", min_value=0.0, value=4.10, step=0.1)
        laying_rate = st.slider("อัตราการให้ไข่ของฝูง (%)", min_value=0, max_value=100, value=85)
        st.markdown("---")
        target_lysine = st.number_input("ไลซีนขั้นต่ำ (%)", min_value=0.0, value=1.10, step=0.05)
        target_methionine = st.number_input("เมทไธโอนีนขั้นต่ำ (%)", min_value=0.0, value=0.45, step=0.05)

    # ปุ่มประมวลผลขนาดใหญ่ ขึงกว้างเต็มหน้าจอแยกส่วนชัดเจน
    st.markdown("##")
    if st.button("🚀 เริ่มต้นประมวลผลสูตรอาหารที่คุ้มค่าที่สุด", use_container_width=True, type="primary"):
        if df_ingredients is not None and not df_ingredients.empty:
            # 🛠️ LP Optimization Setup
            prob = pulp.LpProblem("Feed_Optimization", pulp.LpMinimize)
            ingredients_list = df_ingredients['name'].tolist()
            vars_dict = pulp.LpVariable.dicts("Weight", ingredients_list, lowBound=0)
            
            # Constraints Max Limit
            for _, row in df_ingredients.iterrows():
                prob += vars_dict[row['name']] <= row['max_limit_pct']
            
            # Objective Function
            prob += pulp.lpSum([vars_dict[row['name']] * row['price_per_kg'] for _, row in df_ingredients.iterrows()])
            
            # Nutritional Constraints
            prob += pulp.lpSum([vars_dict[i] for i in ingredients_list]) == 100.0
            prob += pulp.lpSum([vars_dict[row['name']] * (row['protein_pct'] / 100) for _, row in df_ingredients.iterrows()]) >= target_protein
            prob += pulp.lpSum([vars_dict[row['name']] * row['me_kcal_per_kg'] for _, row in df_ingredients.iterrows()]) >= (target_me * 100)
            prob += pulp.lpSum([vars_dict[row['name']] * (row['lysine_pct'] / 100) for _, row in df_ingredients.iterrows()]) >= target_lysine
            prob += pulp.lpSum([vars_dict[row['name']] * (row['methionine_pct'] / 100) for _, row in df_ingredients.iterrows()]) >= target_methionine
            
            prob.solve()
            
            if pulp.LpStatus[prob.status] == "Optimal":
                st.session_state.calculated = True
                st.session_state.total_cost_100kg = pulp.value(prob.objective)
                
                result_list = []
                calc_protein = 0.0
                calc_me = 0.0
                for _, row in df_ingredients.iterrows():
                    w = vars_dict[row['name']].varValue
                    if w and w > 0.01:
                        result_list.append({
                            "ชื่อวัตถุดิบ": row['name'], 
                            "สัดส่วน (%)": round(w, 2), 
                            "ปริมาณที่ต้องใช้ (กก.)": round(w, 2),
                            "ราคาประเมิน (บาท)": round(w * row['price_per_kg'], 2)
                        })
                        calc_protein += w * (row['protein_pct'] / 100)
                        calc_me += w * row['me_kcal_per_kg']
                        
                st.session_state.df_result = pd.DataFrame(result_list)
                st.session_state.calculated_protein = calc_protein
                st.session_state.calculated_me = calc_me / 100
                st.success("🎉 ค้นพบสัดส่วนวัตถุดิบที่คุ้มค่าที่สุดเรียบร้อยแล้ว! ตรวจสอบรายงานด้านล่าง")
            else:
                st.error("❌ ไม่สามารถคำนวณสูตรอาหารตามเงื่อนไขสารอาหารนี้ได้ กรุณาปรับเพิ่มเพดานวัตถุดิบ หรือลดเป้าหมายสารอาหารลง")
        else:
            st.error("❌ ไม่พบข้อมูลวัตถุดิบในฐานข้อมูล")

    st.markdown("---")

    # ==========================================
    # SECTION 2: รายงานผลลัพธ์และการวิเคราะห์ (อยู่ด้านล่าง - ยิ่งใหญ่ เต็มตา)
    # ==========================================
    st.markdown("### 📊 รายงานผลลัพธ์และการวิเคราะห์ (Analytics Dashboard)")
    
    if st.session_state.calculated and st.session_state.df_result is not None:
        
        # 1. Financial Metrics - ขยายใหญ่เด่นชัด 3 ส่วนหลัก
        total_feed_day_kg = (num_chickens * feed_per_bird_g) / 1000
        cost_per_day = total_feed_day_kg * (st.session_state.total_cost_100kg / 100)
        expected_eggs_day = num_chickens * (laying_rate / 100)
        revenue_per_day = expected_eggs_day * egg_price
        net_profit_per_day = revenue_per_day - cost_per_day

        st.markdown("##### 💵 สรุปตัวเลขคาดการณ์ทางการเงินรายวัน")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric(label="📉 ต้นทุนอาหารรวม / วัน", value=f"{cost_per_day:,.2f} ฿")
        with m2:
            st.metric(label="📈 รายได้รวมจากการขายไข่ / วัน", value=f"{revenue_per_day:,.2f} ฿")
        with m3:
            st.metric(label="🏆 กำไรสุทธิคาดการณ์ / วัน", value=f"{net_profit_per_day:,.2f} ฿", delta=f"เฉลี่ย {net_profit_per_day/num_chickens:.2f} ฿/ตัว")
        with m4:
            st.metric(label="💰 ราคาเฉลี่ยสูตรอาหาร (ต่อกก.)", value=f"{st.session_state.total_cost_100kg / 100:.2f} ฿")

        st.markdown("##")

        # 2. ปรับโครงสร้างข้อมูลรายงานแบบ 2 คอลัมน์ด้านล่าง: "ซ้าย: กราฟและเกจสารอาหาร" | "ขวา: ตารางจัดซื้อวัตถุดิบจริง"
        report_left, report_right = st.columns([1.1, 0.9], gap="large")
        
        with report_left:
            st.markdown("##### 🍩 สัดส่วนการผสมวัตถุดิบและคุณค่าโภชนาการ")
            
            # กราฟโดนัทขยายกว้างเห็นชื่อวัตถุดิบชัดๆ
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
                legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # แถบแสดงความแม่นยำของสารอาหารที่คำนวณได้จริง
            st.markdown("##")
            st.progress(min(st.session_state.calculated_protein / target_protein, 1.0), text=f"🧪 โปรตีนที่ได้จริง: {st.session_state.calculated_protein:.2f}% (เป้าหมายขั้นต่ำ: {target_protein:.2f}%)")
            st.progress(min(st.session_state.calculated_me / target_me, 1.0), text=f"⚡ พลังงานที่ได้จริง: {st.session_state.calculated_me:.0f} kcal/กก. (เป้าหมายขั้นต่ำ: {target_me:.0f} kcal)")

        with report_right:
            st.markdown("##### 📋 ตารางใบสั่งจัดซื้อและผสมวัตถุดิบ (สัดส่วนต่อ 100 กิโลกรัม)")
            
            # แสดงตารางแบบ Dataframe ที่ผู้ใช้สามารถเรียงลำดับข้อมูลหรือค้นหาวัตถุดิบได้เอง
            st.dataframe(
                st.session_state.df_result,
                use_container_width=True,
                hide_index=True,
                height=300
            )
            
            st.markdown("---")
            # ปุ่มปฏิบัติการสำหรับหน้างานฟาร์ม
            action_c1, action_c2 = st.columns(2)
            with action_c1:
                if st.button("💾 บันทึกสูตรลงฐานข้อมูลฟาร์ม", use_container_width=True):
                    st.toast("📝 บันทึกสูตรอาหารเข้าประวัติเรียบร้อยแล้ว!")
            with action_c2:
                st.button("🖨️ พิมพ์ใบสั่งผสมอาหาร (PDF)", use_container_width=True, disabled=True)

    else:
        # State ว่างเปล่าแสดงข้อความแนะแนวแบบกว้างเต็มตา
        st.info("💡 **ยินดีต้อนรับสู่ระบบคำนวณอัจฉริยะ:** โปรดกรอกหรือปรับแต่งเงื่อนไขที่ต้องการใน **[แผงควบคุมด้านบน]** จากนั้นกดปุ่มคำนวณ ระบบจะแสดงรายงานสรุปผลกำไร, กราฟวงกลมแยกวัตถุดิบ และตารางจัดซื้อให้คุณที่นี่ทันทีครับ")
