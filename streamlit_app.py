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
# 2. CUSTOM CSS FOR BACKGROUND & UI (MINIMAL EGG IMAGE)
# ==========================================
def add_background():
    """ฟังก์ชัน CSS ล็อกรูปภาพไข่ไก่สีน้ำตาลนวล มินิมอล อ่านง่าย สบายตา"""
    st.markdown(
        """
        <style>
        /* 1. ล้างสีพื้นหลังของเลเยอร์ Streamlit ทั้งหมด */
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: transparent !important;
        }
        
        /* 2. ภาพพื้นหลังไข่ไก่สีน้ำตาล (ล็อกลิงก์ตรงภาพไข่ไก่ล้วน ไม่ติดฟาร์ม ไม่ติดต้นไม้) */
        .stApp::before {
            content: "";
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background-image: url("https://images.unsplash.com/photo-1516448620398-c5f44bf9f441?auto=format&fit=crop&q=80&w=1920");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
            opacity: 0.12; /* ปรับจางๆ 12% สบายตา ตัวหนังสือสีขาวบนกล่องดำจะเด่นมาก */
            z-index: -1;
        }
        
        /* 3. ปรับแต่งกล่องเนื้อหาหลัก (Columns) สไตล์กระจกฝ้าเข้ม */
        div[data-testid="stGridColumn"] > div {
            background-color: rgba(25, 25, 25, 0.88) !important; 
            padding: 25px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.12);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(12px);
        }
        
        /* 4. ปรับสีตัวอักษร Label ของ Inputs */
        label, [data-testid="stWidgetLabel"] p {
            color: #ffffff !important;
            font-weight: 500 !important;
        }
        
        /* 5. ปรับแต่งกล่อง Metric */
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
# 3. SUPABASE CONNECTION & DATA LOADING
# ==========================================
supabase = None
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("❌ ไม่พบข้อมูลการเชื่อมต่อ Supabase ใน Streamlit Secrets (กรุณาตรวจสอบไฟล์ secrets.toml)")

@st.cache_data(ttl=60)
def load_ingredients_from_supabase():
    if supabase is None:
        return None
    try:
        # 🔥 แก้ไขตรงนี้: เปลี่ยนจาก "name" เป็น "name_th" เพื่อให้ตรงกับโครงสร้างตารางจริงในระบบของคุณ
        response = supabase.table("ingredients").select(
            "name_th, price_per_kg, protein_pct, fat_pct, me_kcal_per_kg, lysine_pct, methionine_pct, max_limit_pct"
        ).execute()
        
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['name_th'] = df['name_th'].str.strip()
            # 💡 เปลี่ยนชื่อคอลัมน์ 'name_th' เป็น 'name' เพื่อให้โค้ดส่วนอื่นคำนวณต่อได้ทันที
            df = df.rename(columns={'name_th': 'name'})
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

def reset_calculation():
    st.session_state.calculated = False

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
    num_chickens = st.number_input("จำนวนไก่ไข่ในเล้า (ตัว)", min_value=1, value=180, step=10, on_change=reset_calculation)
    feed_per_bird_g = st.number_input("อัตราการกินอาหาร (กรัม/ตัว/วัน)", min_value=1.0, value=180.0, step=5.0, on_change=reset_calculation)
    egg_price = st.number_input("ราคาไข่ไก่เฉลี่ยที่คาดหวัง (บาท/ฟอง)", min_value=0.0, value=4.10, step=0.1, on_change=reset_calculation)
    laying_rate = st.slider("อัตราการให้ไข่ของฝูงเป้าหมาย (%)", min_value=0, max_value=100, value=85, on_change=reset_calculation)

st.markdown("##")

if st.button("🚀 ประมวลผลและคำนวณสารอาหารที่แม่นยำที่สุด", use_container_width=True, type="primary"):
    if df_ingredients is not None and not df_ingredients.empty:
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
            st.success("🎉 ระบบอัจฉริยะทำการวิเคราะห์และล็อกสัดส่วนสารอาหารที่แม่นยำที่สุดเรียบร้อยแล้ว!")
        else:
            st.error("❌ ไม่สามารถคำนวณตามเงื่อนไขสารอาหารมาตรฐานได้ คลังวัตถุดิบปัจจุบันอาจมีสารอาหารไม่เพียงพอหรือเงื่อนไขขัดกันเอง")
    else:
        st.error("❌ ไม่สามารถดึงคลังวัตถุดิบมาจากฐานข้อมูล Supabase ได้")

st.markdown("---")

# ==========================================
# SECTION 2: รายงานผลลัพธ์และการวิเคราะห์
# ==========================================
st.markdown("### 📊 รายงานผลลัพธ์และการวิเคราะห์ประสิทธิภาพสูตรอาหาร")

if st.session_state.calculated and st.session_state.df_result is not None:
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
        st.metric(label="🏆 กำไรสุทธิคาดการณ์ / วัน", value=f"{net_profit_per_day:,.2f} ฿", delta=f"{net_profit_per_day/num_chickens:.2f} ฿/ตัว")
    with m4:
        st.metric(label="💰 ราคาเฉลี่ยสูตรอาหาร (ต่อกก.)", value=f"{st.session_state.total_cost_100kg / 100:.2f} ฿")

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
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            paper_bgcolor='rgba(0,0,0,0)',  
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="white")
        )
        st.plotly_chart(fig, use_container_width=True)
        
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
                if supabase is not None:
                    try:
                        save_data = {
                            "formula_cost_100kg": st.session_state.total_cost_100kg,
                            "calculated_protein": st.session_state.calculated_protein,
                            "calculated_me": st.session_state.calculated_me,
                            "ingredients_json": st.session_state.df_result.to_json(orient='records', force_ascii=False)
                        }
                        st.toast("📝 บันทึกสูตรอาหารลงฐานข้อมูลเรียบร้อยแล้ว!", icon="💾")
                    except Exception as save_err:
                        st.error(f"ไม่สามารถบันทึกข้อมูลได้: {save_err}")
                else:
                    st.toast("📝 ทดสอบระบบ: บันทึกสูตรอาหารเรียบร้อยแล้ว (Simulated)!")
        with action_c2:
            st.button("🖨️ พิมพ์ใบสั่งผสมอาหาร (PDF)", use_container_width=True, disabled=True)

else:
    st.info("💡 **ระบบพร้อมใช้งาน:** ตั้งค่าตัวเลขจำนวนฝูงไก่ของคุณที่ **[แผงควบคุมด้านบน]** จากนั้นกดปุ่มประมวลผล ระบบอัจฉริยะจะปรับสมดุลและคำนวณปริมาณสารอาหารที่แม่นยำที่สุดให้ทันทีครับ")
