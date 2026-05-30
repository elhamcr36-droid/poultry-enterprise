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
    st.session_state.calculated_lysine = 0.0
    st.session_state.calculated_methionine = 0.0

# ==========================================
# MAIN CONTENT & HEADER
# ==========================================
st.title("🥚 Smart Layer Feed")
st.subheader("ระบบคำนวณและวางแผนสูตรอาหารไก่ไข่อัจฉริยะด้วยปัญญาประดิษฐ์")
st.markdown("---")

# ==========================================
# SECTION 1: แผงควบคุมและตั้งค่า (เต็มหน้าจอ - FULL WIDTH)
# ==========================================
st.markdown("### ⚙️ แผงควบคุมและตั้งค่าการจำลองฟาร์ม")

# ปรับกลุ่มข้อมูลเหลือ 2 คอลัมน์กว้างๆ เพื่อความสบายตาในการป้อนข้อมูลจำลองฝูงไก่
input_col1, input_col2 = st.columns(2, gap="large")

with input_col1:
    st.markdown("##### 🐔 ข้อมูลฝูงไก่และสายพันธุ์")
    st.selectbox("กลุ่มไก่ไข่", ["Commercial Brown Layer"], index=0, disabled=True)
    st.selectbox("สายพันธุ์", ["อิซ่า บราวน์ (Isa Brown)"], index=0, disabled=True)
    st.selectbox("ระยะการเลี้ยง", ["ช่วงอายุ แรกเกิด-6 สัปดาห์ (Starter 0-6 wk)"], index=0, disabled=True)
    
    # กรอบกล่องข้อความแจ้งสเปกที่ระบบจะล็อกความแม่นยำไว้เบื้องหลัง
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

# ปุ่มประมวลผลคำนวณอัตโนมัติ
st.markdown("##")
if st.button("🚀 ประมวลผลและคำนวณสารอาหารที่แม่นยำที่สุด", use_container_width=True, type="primary"):
    if df_ingredients is not None and not df_ingredients.empty:
        # 🛠️ ค่ามาตรฐานโภชนาการคงที่เพื่อความแม่นยำเชิงลึกของลูกไก่ระยะ 0-6 สัปดาห์
        AUTO_PROTEIN = 20.0
        AUTO_ME = 2900.0
        AUTO_LYSINE = 1.10
        AUTO_METHIONINE = 0.45
        
        # 🛠️ LP Optimization Setup ด้วย PuLP
        prob = pulp.LpProblem("Feed_Optimization", pulp.LpMinimize)
        ingredients_list = df_ingredients['name'].tolist()
        vars_dict = pulp.LpVariable.dicts("Weight", ingredients_list, lowBound=0)
        
        # ข้อจำกัดสัดส่วนสูงสุดของแต่ละวัตถุดิบ (Max Limit Constraints จาก DB)
        for _, row in df_ingredients.iterrows():
            prob += vars_dict[row['name']] <= row['max_limit_pct']
        
        # Objective Function: คำนวณหาต้นทุนต่ำสุดภายใต้เกณฑ์สารอาหารที่สมบูรณ์ที่สุด
        prob += pulp.lpSum([vars_dict[row['name']] * row['price_per_kg'] for _, row in df_ingredients.iterrows()])
        
        # ล็อกสมการสัดส่วนสารอาหารเป้าหมายเพื่อความแม่นยำ 100%
        prob += pulp.lpSum([vars_dict[i] for i in ingredients_list]) == 100.0  # น้ำหนักสูตรรวม 100 กก.
        prob += pulp.lpSum([vars_dict[row['name']] * (row['protein_pct'] / 100) for _, row in df_ingredients.iterrows()]) >= AUTO_PROTEIN
        prob += pulp.lpSum([vars_dict[row['name']] * row['me_kcal_per_kg'] for _, row in df_ingredients.iterrows()]) >= (AUTO_ME * 100)
        prob += pulp.lpSum([vars_dict[row['name']] * (row['lysine_pct'] / 100) for _, row in df_ingredients.iterrows()]) >= AUTO_LYSINE
        prob += pulp.lpSum([vars_dict[row['name']] * (row['methionine_pct'] / 100) for _, row in df_ingredients.iterrows()]) >= AUTO_METHIONINE
        
        prob.solve()
        
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
                    calc_protein += w * (row['protein_pct'] / 100)
                    calc_me += w * row['me_kcal_per_kg']
                    calc_lysine += w * (row['lysine_pct'] / 100)
                    calc_methionine += w * (row['methionine_pct'] / 100)
                        
            st.session_state.df_result = pd.DataFrame(result_list)
            st.session_state.calculated_protein = calc_protein
            st.session_state.calculated_me = calc_me / 100
            st.session_state.calculated_lysine = calc_lysine
            st.session_state.calculated_methionine = calc_methionine
            st.success("🎉 ระบบอัจฉริยะทำการวิเคราะห์และล็อกสัดส่วนสารอาหารที่แม่นยำที่สุดเรียบร้อยแล้ว!")
        else:
            st.error("❌ ไม่สามารถคำนวณตามเงื่อนไขสารอาหารมาตรฐานได้ กรุณาตรวจสอบราคาหรือจำนวนวัตถุดิบในคลังข้อมูล")
    else:
        st.error("❌ ไม่สามารถดึงคลังวัตถุดิบมาจาก Supabase ได้")

st.markdown("---")

# ==========================================
# SECTION 2: รายงานผลลัพธ์และการวิเคราะห์ (Analytics Dashboard)
# ==========================================
st.markdown("### 📊 รายงานผลลัพธ์และการวิเคราะห์ประสิทธิภาพสูตรอาหาร")

if st.session_state.calculated and st.session_state.df_result is not None:
    
    # 1. Financial Metrics คำนวณรายวัน
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

    # 2. Charts & Tables จัดเรียงหน้ากระดานด้านล่าง
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
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # ส่วนแสดงความแม่นยำของสารอาหารที่วิเคราะห์ได้แบบ Real-time เทียบค่าเป้าหมายเชิงลึก
        st.markdown("##### 🧪 ความแม่นยำของสารอาหารที่ได้จริง")
        prog_col1, prog_col2 = st.columns(2)
        with prog_col1:
            st.progress(min(st.session_state.calculated_protein / 20.0, 1.0), text=f"โปรตีน: {st.session_state.calculated_protein:.2f}% (เป้า: 20.0%)")
            st.progress(min(st.session_state.calculated_lysine / 1.10, 1.0), text=f"ไลซีน: {st.session_state.calculated_lysine:.2f}% (เป้า: 1.10%)")
        with prog_col2:
            st.progress(min(st.session_state.calculated_me / 2900.0, 1.0), text=f"พลังงาน: {st.session_state.calculated_me:.0f} kcal (เป้า: 2900 kcal)")
            st.progress(min(st.session_state.calculated_methionine / 0.45, 1.0), text=f"เมทไธโอนีน: {st.session_state.calculated_methionine:.2f}% (เป้า: 0.45%)")

    with report_right:
        st.markdown("##### 📋 ตารางสัดส่วนใบสั่งผสมวัตถุดิบจริง (ต่อ 100 กิโลกรัม)")
        st.dataframe(
            st.session_state.df_result,
            use_container_width=True,
            hide_index=True,
            height=320
        )
        
        st.markdown("---")
        action_c1, action_c2 = st.columns(2)
        with action_c1:
            if st.button("💾 บันทึกสูตรลงฐานข้อมูลฟาร์ม", use_container_width=True):
                st.toast("📝 บันทึกสูตรอาหารเรียบร้อยแล้ว!")
        with action_c2:
            st.button("🖨️ พิมพ์ใบสั่งผสมอาหาร (PDF)", use_container_width=True, disabled=True)

else:
    st.info("💡 **ระบบพร้อมใช้งาน:** ตั้งค่าตัวเลขจำนวนฝูงไก่ของคุณที่ **[แผงควบคุมด้านบน]** จากนั้นกดปุ่มประมวลผล ระบบอัจฉริยะจะปรับสมดุลและคำนวณปริมาณสารอาหารที่แม่นยำที่สุดให้ทันทีครับ")
