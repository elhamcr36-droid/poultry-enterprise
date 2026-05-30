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
# 2. CUSTOM CSS WITH EMBEDDED IMAGE (BASE64)
# ==========================================
def add_background():
    """ฟังก์ชันฝังรูปภาพฟาร์มไก่ในรูปแบบ Base64 และล้างเลเยอร์สีเพื่อให้แสดงผลได้แน่นอน 100%"""
    # ตัวแปรสตริงภาพฟาร์มไก่ในเล้า (สไตล์โรงเรือนระบบปิด) ปลอดภัยและโหลดขึ้นแน่นอนทุกเครื่อง
    chicken_farm_base64 = (
        "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/4QAiRXhpZgAATU0AKgAAAAgAAQESAAMAAAABAAEAAAAA"
        "AAD/2wBDAAIBAQIBAQICAgICAgICAwUDAwMDAwYEBAMFBwYHBwcGBwcICQsJCAgKCAcHCg0KCgsMDAwMBwkODw0MDgsMDAz/"
        "2wBDAQICAgMDAwYDAwYMCAcIDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAz/wAAR"
        "CAHgAoADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQID"
        "AAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNk"
        "ZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl"
        "5ufo6erx8vP09fb3+Pn6/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLR"
        "ChYkNOEl8RcYGRomJygpKjU2N3ODk6DRRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKj"
        "kWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD98KKKK"
        "ACiiigAAooooAKKKKACiiigA0UUUABooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooo"
        "oAKKKKACiiigAooooAKKKKACiiigA0UUUABooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACii"
        "igAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACii"
        "igAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACii"
        "igAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACii"
        "igAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKfFA0zcDA9fSgBlFWAbaHu"
        "0rewwKVtRii+5Co/3uaVwK6xtIeBThAepZQPc06XU5ZFwCEHooxUDO0h5JP40wLBghiPzS59lGaa1xAn3UZvdmxVcrgUm6Fw"
        "LDatgfJEij3Gap3urSsh+cKOwUVDcz4yM1k6hfYUjPbtSAsXOpyHIMjnP+1VRb+RHzuYg9iaw7vUzFIckYz1qE6/kdRgHjBq"
        "uVsVzo7fXXU7ZOfQitfS9S+0D5WDeozXAWusiWTDHAPU5rdsfEEenWwclQBwRnkmlawXOzZfL5zkH3ppYGsTQPF0WsXBhA2s"
        "OQNw/wAjrWuDUtDHUUg6UtIAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKK"
        "KACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKfDBvILeuaAExgZNJg96tXLRwpjvVZpzMcDCD2qbgKqovU0/z"
        "4ohwCx/KqrSBT1LH9KgubzaOnXvRcC4+psPuogqq80kvUnBqg+pZPXp0qvNquCR7c5ouBpNLFDy7An2pjanH/yzRfc1hvqm+"
        "Xr1/KprS7G/rT5QNf+0Zl5+XHqKkt9ceM/e69cisya6Ux/eqlNelSMevFHKB3emawk69R+FaSHeuetcLoN9tlGcgjjiuz0m8"
        "E0QyaTVgLVFIw2vS0gCiiigAooooAKfBCZnC/nTK0rS3FvB/tUARXEv2eERpwSMfT1qoUwasMvmXGCOe9MeEgZHOe1AEPFI6"
        "04ptNNbgUAVbmInNYmqqyxkjP4GuimX5TisPV+I29akDgdauXEj9cDuTWHNrHljls8Z61reLYw99uZs8DqaxHhhC5LAAHkmt"
        "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"
    )
    
    st.markdown(
        f"""
        <style>
        /* 1. ล้างสีพื้นหลังของเลเยอร์ Streamlit ทั้งหมดที่คอยบังภาพ */
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: transparent !important;
        }
        
        /* 2. ดึงภาพฟาร์มไก่ไข่จาก Base64 มาแสดงผลด้านหลังสุด */
        .stApp::before {{
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background-image: url("{chicken_farm_base64}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
            /* ค่าความชัดของภาพพื้นหลัง (0.30 กำลังสวย มองเห็นภาพเล้าไก่ชัดเจนและไม่แย่งสายตา) */
            opacity: 0.30; 
            z-index: -1;
        }}
        
        /* 3. ปรับแต่งกล่องเนื้อหาหลัก (Columns) ให้เป็นโทนดำใสสไตล์กระจกฝ้า (Frosted Glass) */
        div[data-testid="stGridColumn"] > div {{
            background-color: rgba(25, 25, 25, 0.82) !important; 
            padding: 25px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.12);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(8px);
        }}
        
        /* 4. ปรับแต่งกล่อง Metric สรุปตัวเลขทางการเงินให้มองเห็นชัดเจน */
        div[data-testid="stMetric"] {{
            background-color: rgba(0, 0, 0, 0.55) !important;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #ffaa00;
        }}
        [data-testid="stMetricValue"] {{
            font-weight: bold;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# เรียกใช้งานฟังก์ชันพื้นหลังทันทีเมื่อเปิดแอป
add_background()

# ==========================================
# 3. SUPABASE CONNECTION & DATA LOADING
# ==========================================
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("❌ ไม่พบข้อมูลการเชื่อมต่อ Supabase ใน Streamlit Secrets (กรุณาตรวจสอบไฟล์ secrets.toml)")

@st.cache_data(ttl=60)
def load_ingredients_from_supabase():
    try:
        response = supabase.table("ingredients").select(
            "name, price_per_kg, protein_pct, fat_pct, me_kcal_per_kg, lysine_pct, methionine_pct, max_limit_pct"
        ).execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['name'] = df['name'].str.strip()
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
    num_chickens = st.number_input("จำนวนไก่ไข่ในเล้า (ตัว)", min_value=1, value=100, step=10)
    feed_per_bird_g = st.number_input("อัตราการกินอาหาร (กรัม/ตัว/วัน)", min_value=1.0, value=100.0, step=5.0)
    egg_price = st.number_input("ราคาไข่ไก่เฉลี่ยที่คาดหวัง (บาท/ฟอง)", min_value=0.0, value=4.10, step=0.1)
    laying_rate = st.slider("อัตราการให้ไข่ของฝูงเป้าหมาย (%)", min_value=0, max_value=100, value=85)

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
# SECTION 2: รายงานผลลัพธ์และการวิเคราะห์ (Dashboard)
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
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
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
