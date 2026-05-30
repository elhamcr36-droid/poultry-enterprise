import streamlit as st
import pandas as pd
import pulp
import plotly.express as px
import psycopg2

# ตั้งค่าหน้าเว็บให้เป็นแบบกว้าง (Wide mode)
st.set_page_config(layout="wide", page_title="คำนวณสูตรอาหารไก่ไข่อัจฉริยะ")

# ดึง Connection String จาก Streamlit Secrets สำหรับเชื่อมต่อ Supabase
conn_str = st.secrets["DB_CONNECTION_STRING"]

@st.cache_data(ttl=60)  # แคชข้อมูลไว้ 1 นาที เพื่อไม่ให้โหลดฐานข้อมูลบ่อยเกินไป
def load_ingredients_from_supabase():
    try:
        conn = psycopg2.connect(conn_str)
        # ดึงสารอาหารทั้งหมดรวมถึง ตัวที่เพิ่งเพิ่มใหม่ (ME, Lysine, Methionine)
        query = """
            SELECT name, price_per_kg, protein_pct, fat_pct, 
                   me_kcal_per_kg, lysine_pct, methionine_pct, max_limit_pct 
            FROM ingredients;
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ ไม่สามารถเชื่อมต่อ Supabase ได้: {e}")
        return None

# โหลดข้อมูลเตรียมไว้
df_ingredients = load_ingredients_from_supabase()

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
    
    # ดึงค่าสถานะการคำนวณมาเก็บไว้ใน Session State ป้องกันค่าหายเวลารีเฟรช
    if "calculated" not in st.session_state:
        st.session_state.calculated = False
        st.session_state.df_result = None
        st.session_state.total_cost_100kg = 0.0
        st.session_state.calculated_protein = 0.0
        st.session_state.calculated_me = 0.0

    # แบ่งหน้าจอเป็น 2 คอลัมน์หลักตามสัดส่วนเดิมของคุณ
    col_left, col_right = st.columns([1, 1.2])

    # ------------------------------------------
    # คอลัมน์ซ้าย: ตั้งค่าเงื่อนไข & พยากรณ์รายได้
    # ------------------------------------------
    with col_left:
        st.subheader("⚙️ ตั้งค่าเงื่อนไข")
        
        st.selectbox("กลุ่มไก่ไข่", ["Commercial Brown Layer..."], index=0)
        st.selectbox("สายพันธุ์", ["อิซ่า บราวน์ (Isa Brown)"], index=0)
        st.selectbox("ระยะการเลี้ยง", ["ช่วงอายุ แรกเกิด-6 สัปดาห์ (Starter 0-6 wk)"], index=0)
        
        num_chickens = st.number_input("จำนวนไก่ไข่ (ตัว)", min_value=1, value=100, step=1)
        feed_per_bird_g = st.number_input("ปริมาณอาหารที่กิน (กรัม/ตัว/วัน)", min_value=1.0, value=100.0, step=5.0)
        
        st.write("เป้าหมายการคำนวณ")
        goal_option = st.radio(
            "เลือกเป้าหมาย",
            ["🔴 อาหารราคาถูกที่สุด (Best Price)", "⚫ สารอาหารตรงตามความต้องการที่สุด (Best Nutrition)"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        st.subheader("💰 พยากรณ์รายได้")
        egg_price = st.number_input("ราคาไข่ไก่เฉลี่ย (บาท/ฟอง)", min_value=0.0, value=4.10, step=0.1)
        laying_rate = st.slider("อัตราการให้ไข่ (%)", min_value=0, max_value=100, value=85)
        
        # เมื่อกดปุ่ม ประมวลผลสูตรอาหาร ให้เรียกใช้งาน PuLP คำนวณจริงจากฐานข้อมูล
        if st.button("🚀 ประมวลผลสูตรอาหาร", use_container_width=True, type="primary"):
            if df_ingredients is not None:
                # 🛠️ เริ่มต้นตั้งโจทย์ Linear Programming ด้วย PuLP
                prob = pulp.LpProblem("Feed_Optimization", pulp.LpMinimize)
                
                ingredients_list = df_ingredients['name'].tolist()
                vars_dict = pulp.LpVariable.dicts("Weight", ingredients_list, lowBound=0)
                
                # ข้อจำกัดเพดานสูงสุดของวัตถุดิบ (Max Limit) ที่ดึงมาจาก Supabase
                for _, row in df_ingredients.iterrows():
                    prob += vars_dict[row['name']] <= row['max_limit_pct']
                
                # Objective Function: หาผลรวมราคาสูตรที่ต่ำที่สุด (ราคาต่อกิโลกรัม * ปริมาณ)
                prob += pulp.lpSum([vars_dict[row['name']] * row['price_per_kg'] for _, row in df_ingredients.iterrows()])
                
                # Constraints บังคับสัดส่วนสารอาหารมาตรฐานสำหรับช่วงอายุ 0-6 สัปดาห์
                prob += pulp.lpSum([vars_dict[i] for i in ingredients_list]) == 100.0  # สูตรอาหารต่อ 100 กก.
                prob += pulp.lpSum([vars_dict[row['name']] * (row['protein_pct'] / 100) for _, row in df_ingredients.iterrows()]) >= 20.0  # โปรตีนไม่ต่ำกว่า 20%
                prob += pulp.lpSum([vars_dict[row['name']] * row['me_kcal_per_kg'] for _, row in df_ingredients.iterrows()]) >= (2900 * 100)  # พลังงานไม่ต่ำกว่า 2900 kcal/กก.
                prob += pulp.lpSum([vars_dict[row['name']] * (row['lysine_pct'] / 100) for _, row in df_ingredients.iterrows()]) >= 1.10  # ไลซีนไม่ต่ำกว่า 1.1%
                prob += pulp.lpSum([vars_dict[row['name']] * (row['methionine_pct'] / 100) for _, row in df_ingredients.iterrows()]) >= 0.45  # เมทไธโอนีนไม่ต่ำกว่า 0.45%
                
                prob.solve()
                
                if pulp.LpStatus[prob.status] == "Optimal":
                    st.session_state.calculated = True
                    st.session_state.total_cost_100kg = pulp.value(prob.objective)
                    
                    # คัดแยกวัตถุดิบที่มีการนำมาใช้งานจริงในสูตร
                    result_list = []
                    calc_protein = 0.0
                    calc_me = 0.0
                    for _, row in df_ingredients.iterrows():
                        w = vars_dict[row['name']].varValue
                        if w and w > 0.01:
                            result_list.append({"ชื่อวัตถุดิบ": row['name'], "สัดส่วน (%)": round(w, 2), "ต้องใช้ (กก.)": round(w, 2)})
                            calc_protein += w * (row['protein_pct'] / 100)
                            calc_me += w * row['me_kcal_per_kg']
                            
                    st.session_state.df_result = pd.DataFrame(result_list)
                    st.session_state.calculated_protein = calc_protein
                    st.session_state.calculated_me = calc_me / 100
                    st.success("คำนวณสำเร็จ!")
                else:
                    st.error("❌ ไม่สามารถหาจุดคุ้มทุนตามสารอาหารที่กำหนดได้ กรุณาตรวจสอบราคาวัตถุดิบในคลัง")
            else:
                st.error("ไม่พบข้อมูลวัตถุดิบในฐานข้อมูล")

    # ------------------------------------------
    # คอลัมน์ขวา: ผลลัพธ์สัดส่วนวัตถุดิบ & พยากรณ์กำไร
    # ------------------------------------------
    with col_right:
        st.subheader("📊 ผลลัพธ์สัดส่วนวัตถุดิบ")
        st.info("สายพันธุ์: อิซ่า บราวน์ (Isa Brown) | ช่วงอายุ: แรกเกิด-6 สัปดาห์ (Starter 0-6 wk)")
        
        if st.session_state.calculated and st.session_state.df_result is not None:
            # 🍩 ปรับมาใช้ Plotly Express แทน Matplotlib เพื่อลดปัญหาฟอนต์ภาษาไทยและวาดกราฟโดนัทสวยงามขึ้นโดยอัตโนมัติ
            fig = px.pie(
                st.session_state.df_result, 
                values='สัดส่วน (%)', 
                names='ชื่อวัตถุดิบ', 
                hole=0.5,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)
            st.plotly_chart(fig, use_container_width=True)
            
            # ส่วนแสดงค่าโปรตีนและพลังงานคำนวณจริงเทียบเป้าหมาย
            metric_col1, metric_col2 = st.columns(2)
            with metric_col1:
                st.metric(label="โปรตีนรวมที่ได้ (%)", value=f"{st.session_state.calculated_protein:.2f}%")
                st.caption("🟢 Target: 20.00%")
            with metric_col2:
                st.metric(label="พลังงานรวมที่ได้ (kcal)", value=f"{st.session_state.calculated_me:.0f} kcal")
                st.caption("🟢 Target: 2900 kcal")
                
            # แสดงตารางผลลัพธ์ข้อมูลวัตถุดิบ
            st.table(st.session_state.df_result)
            
            st.markdown("---")
            
            # ---- ส่วนพยากรณ์กำไรรายวัน (คำนวณแบบ Real Dynamic) ----
            st.subheader("📈 พยากรณ์กำไรรายวัน")
            
            # คำนวณปริมาณอาหารที่ต้องใช้จริงต่อวันของทั้งเล้า (หน่วยเป็นกิโลกรัม)
            total_feed_day_kg = (num_chickens * feed_per_bird_g) / 1000
            # คำนวณต้นทุนอาหารต่อวัน (ราคาต่อ 100 กก. หาร 100 จะได้ราคาต่อกิโลกรัม)
            cost_per_day = total_feed_day_kg * (st.session_state.total_cost_100kg / 100)
            # พยากรณ์จำนวนไข่ต่อวันตามอัตราการให้ไข่ และคำนวณรายได้ต่อวัน
            expected_eggs_day = num_chickens * (laying_rate / 100)
            revenue_per_day = expected_eggs_day * egg_price
            # คำนวณกำไรสุทธิ
            net_profit_per_day = revenue_per_day - cost_per_day
            
            profit_col1, profit_col2, profit_col3 = st.columns(3)
            with profit_col1:
                st.metric(label="ต้นทุนอาหาร/วัน", value=f"{cost_per_day:,.2f} ฿")
            with profit_col2:
                st.metric(label="รายได้เฉลี่ย/วัน", value=f"{revenue_per_day:,.2f} ฿")
            with profit_col3:
                st.metric(label="กำไรสุทธิ/วัน", value=f"{net_profit_per_day:,.2f} ฿")
                
            if st.button("💾 บันทึกสูตรอาหารและประวัติการคำนวณ", use_container_width=True):
                st.toast("บันทึกข้อมูลเรียบร้อยแล้ว!")
        else:
            st.warning("💡 กรุณากดปุ่ม 🚀 ประมวลผลสูตรอาหาร เพื่อแสดงผลลัพธ์และตัวเลขพยากรณ์")
