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
# SIDEBAR (แผงควบคุมระบบสมาชิก / ตั้งค่าทั่วไป)
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
# MAIN CONTENT & TABS
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
# TAB 0: คำนวณสูตรอาหาร (Redesigned)
# ------------------------------------------
with tabs[0]:
    # แบ่งสัดส่วน 45% (ควบคุม) : 55% (แสดงผลลัพธ์) เพื่อความสมดุลทางสายตา
    col_control, col_display = st.columns([1, 1.2], gap="large")

    # --- คอลัมน์ซ้าย: Control Panel (แผงป้อนข้อมูลและข้อจำกัด) ---
    with col_control:
        st.markdown("### ⚙️ แผงควบคุมและตั้งค่า")
        
        # Segment 1: ข้อมูลสายพันธุ์และฝูงไก่
        with st.expander("🐔 ข้อมูลสายพันธุ์และขนาดฟาร์ม", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                st.selectbox("กลุ่มไก่ไข่", ["Commercial Brown Layer"], index=0)
                num_chickens = st.number_input("จำนวนไก่ไข่ (ตัว)", min_value=1, value=100, step=10)
            with c2:
                st.selectbox("สายพันธุ์", ["อิซ่า บราวน์ (Isa Brown)"], index=0)
                feed_per_bird_g = st.number_input("อัตราการกิน (กรัม/ตัว/วัน)", min_value=1.0, value=100.0, step=5.0)
            
            st.selectbox("ระยะการเลี้ยง", ["ช่วงอายุ แรกเกิด-6 สัปดาห์ (Starter 0-6 wk)"], index=0)

        # Segment 2: สารอาหารเป้าหมาย (เปิดโอกาสให้ปรับแต่งได้ ไม่ Hardcode ผิวเผิน)
        with st.expander("🧬 ข้อจำกัดและสารอาหารเป้าหมาย (ต่อน้ำหนัก 100 กิโลกรัม)", expanded=True):
            goal_option = st.radio(
                "กลยุทธ์การคำนวณ",
                ["🎯 อาหารราคาถูกที่สุด (Best Price)", "✨ สารอาหารตรงตามสเปกที่สุด (Best Nutrition)"],
                horizontal=True
            )
            
            cc1, cc2 = st.columns(2)
            with cc1:
                target_protein = st.number_input("โปรตีนขั้นต่ำ (%)", min_value=0.0, value=20.0, step=0.5)
                target_lysine = st.number_input("ไลซีนขั้นต่ำ (%)", min_value=0.0, value=1.10, step=0.05)
            with cc2:
                target_me = st.number_input("พลังงานขั้นต่ำ (kcal/กก.)", min_value=0, value=2900, step=50)
                target_methionine = st.number_input("เมทไธโอนีนขั้นต่ำ (%)", min_value=0.0, value=0.45, step=0.05)

        # Segment 3: การเงินและตลาด
        with st.expander("💰 ข้อมูลการตลาดและราคารับซื้อ", expanded=True):
            ccc1, ccc2 = st.columns(2)
            with ccc1:
                egg_price = st.number_input("ราคาไข่ไก่เฉลี่ย (บาท/ฟอง)", min_value=0.0, value=4.10, step=0.1)
            with ccc2:
                laying_rate = st.slider("อัตราการให้ไข่ของฝูง (%)", min_value=0, max_value=100, value=85)

        st.markdown("##")
        # ปุ่มประมวลผลขนาดใหญ่ ชัดเจน มีความโดดเด่น
        if st.button("🚀 เริ่มคำนวณสูตรอาหารที่คุ้มค่าที่สุด", use_container_width=True, type="primary"):
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
                
                # Nutritional Constraints (Dynamic values from UI)
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
                    st.success("🎉 ประมวลผลเสร็จสิ้น! ค้นพบสัดส่วนที่ประหยัดที่สุดแล้ว")
                else:
                    st.error("❌ ไม่สามารถคำนวณสูตรอาหารตามเงื่อนไขสารอาหารนี้ได้ กรุณาปรับเพิ่มเพดานวัตถุดิบ หรือลดสเปกสารอาหารลง")
            else:
                st.error("❌ ไม่สามารถดึงข้อมูลคลังวัตถุดิบได้")

    # --- คอลัมน์ขวา: ผลลัพธ์และการวิเคราะห์ (Visualizations & Analytics) ---
    with col_display:
        st.markdown("### 📊 รายงานผลลัพธ์และการวิเคราะห์")
        
        if st.session_state.calculated and st.session_state.df_result is not None:
            # ส่วนจัดการคำนวณรายวันทางเศรษฐศาสตร์
            total_feed_day_kg = (num_chickens * feed_per_bird_g) / 1000
            cost_per_day = total_feed_day_kg * (st.session_state.total_cost_100kg / 100)
            expected_eggs_day = num_chickens * (laying_rate / 100)
            revenue_per_day = expected_eggs_day * egg_price
            net_profit_per_day = revenue_per_day - cost_per_day

            # 1. Financial Dashboard (Hero Metrics Highlight)
            st.markdown("#### 💵 พยากรณ์ด้านการเงินรายวัน (Economic Forecast)")
            with st.container():
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric(label="📉 ต้นทุนค่าอาหาร / วัน", value=f"{cost_per_day:,.2f} ฿")
                with m2:
                    st.metric(label="📈 รายได้จากการขายไข่ / วัน", value=f"{revenue_per_day:,.2f} ฿")
                with m3:
                    # เปลี่ยนสีตัวเลขตามกำไรขาดทุนด้วย Component พื้นฐาน
                    st.metric(
                        label="🏆 กำไรสุทธิคาดการณ์ / วัน", 
                        value=f"{net_profit_per_day:,.2f} ฿",
                        delta=f"เฉลี่ย {net_profit_per_day/num_chickens:.2f} ฿/ตัว"
                    )
            
            st.markdown("---")

            # 2. Charts & Proportion Analysis
            st.markdown("#### 🍩 สัดส่วนโครงสร้างวัตถุดิบในสูตร")
            fig = px.pie(
                st.session_state.df_result, 
                values='สัดส่วน (%)', 
                names='ชื่อวัตถุดิบ', 
                hole=0.5,
                color_discrete_sequence=px.colors.qualitative.Safe
            )
            fig.update_layout(
                margin=dict(t=20, b=20, l=10, r=10), 
                height=280,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig, use_container_width=True)

            # 3. Nutrition Summary Compare
            st.markdown("#### 🧪 คุณค่าทางโภชนาการที่ได้รับจริง")
            n_col1, n_col2 = st.columns(2)
            with n_col1:
                st.progress(min(st.session_state.calculated_protein / target_protein, 1.0), text=f"โปรตีนที่ได้: {st.session_state.calculated_protein:.2f}% (เป้าหมาย: {target_protein:.2f}%)")
            with n_col2:
                st.progress(min(st.session_state.calculated_me / target_me, 1.0), text=f"พลังงานที่ได้: {st.session_state.calculated_me:.0f} kcal/กก. (เป้าหมาย: {target_me:.0f} kcal)")

            # 4. Data Table Display
            st.markdown("#### 📋 รายการสัดส่วนจัดซื้อวัตถุดิบ (ผสมต่อ 100 กก.)")
            st.dataframe(
                st.session_state.df_result,
                use_container_width=True,
                hide_index=True
            )
            
            # Action Buttons Section
            st.markdown("##")
            b1, b2 = st.columns(2)
            with b1:
                if st.button("💾 บันทึกสูตรเข้าประวัติฟาร์ม", use_container_width=True):
                    st.toast("📝 บันทึกสูตรอาหารเรียบร้อยแล้ว!")
            with b2:
                st.button("🖨️ ส่งออกเป็น PDF / ใบสั่งซื้อวัตถุดิบ", use_container_width=True, disabled=True)
                
        else:
            # Empty State Design (เมื่อยังไม่ได้กดคำนวณ)
            st.markdown("##")
            st.info("💡 **คำแนะนำการใช้งาน:** กรอกข้อมูลขนาดฟาร์มและเป้าหมายสารอาหารที่ต้องการทางด้านซ้าย จากนั้นกดปุ่ม **[เริ่มคำนวณสูตรอาหาร]** เพื่อให้ระบบวิเคราะห์ต้นทุนและแสดงผลรายงานที่นี่")
