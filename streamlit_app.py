import streamlit as st
import pandas as pd
import plotly.express as px
import pulp
from supabase import create_client, Client
import io

# ==========================================
# 🔱 1. ตั้งค่าคอนฟิกแอปพลิเคชันและหน้าจอ
# ==========================================
st.set_page_config(
    page_title="Mega Feed & Breed Studio", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(
    """
    <style>
    [data-testid="collapsedControl"] { display: none; }
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), 
                          url("https://images.unsplash.com/photo-1548550023-2bdb3c5beed7?q=80&w=1920");
        background-size: cover; background-position: center;
        background-repeat: no-repeat; background-attachment: fixed;
    }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, [data-testid="stHeader"] {
        color: #ffffff !important;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.9) !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(255, 255, 255, 0.12) !important;
        padding: 10px; border-radius: 12px; backdrop-filter: blur(10px);
    }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-weight: bold !important; }
    .content-card {
        background-color: rgba(0, 0, 0, 0.75) !important; padding: 25px;
        border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(8px); margin-bottom: 20px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem !important; color: #38bdf8 !important;
        font-weight: bold !important; text-shadow: 1px 1px 2px rgba(0,0,0,0.9);
    }
    [data-testid="stDataFrame"] { background-color: rgba(255,255,255,0.9) !important; border-radius: 10px; padding: 5px; }
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================================
# 🔐 2. ระบบล็อกอินและการเชื่อมต่อฐานข้อมูล
# ==========================================
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False
if "supabase_url" not in st.session_state:
    st.session_state.supabase_url = ""
if "supabase_key" not in st.session_state:
    st.session_state.supabase_key = ""

CORRECT_URL = "https://nxyncxqbtntlpzqessou.supabase.co"
CORRECT_KEY = "sb_publishable_m411zYbsazCAsmmUMIuMkA_ypb1BYPr"

if not st.session_state.is_authenticated:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center;'>🔐 ยินดีต้อนรับสู่ Mega Feed & Breed Studio</h2>", unsafe_allow_html=True)
    
    input_url = CORRECT_URL
    input_key = CORRECT_KEY

    st.markdown("---")
    tab_login, _ = st.tabs(["🔑 เข้าสู่ระบบ (Login)", "📝 สมัครสมาชิก (ปิดใช้งานชั่วคราว)"])
    
    with tab_login:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            email_login = st.text_input("📧 อีเมล หรือ ชื่อผู้ใช้", key="login_email")
            pass_login = st.text_input("🔑 รหัสผ่าน", type="password", key="login_pass")
            
            if st.button("เข้าสู่ระบบ (Login)", type="primary", use_container_width=True):
                if email_login in ["222", "จีเมล222", "222@gmail.com"] and pass_login in ["222", "รหัส222"]:
                    st.session_state.is_authenticated = True
                    st.session_state.user_email = "👑 Admin (SQL Superuser)"
                    st.session_state.supabase_url = input_url
                    st.session_state.supabase_key = input_key
                    st.success("✅ เชื่อมต่อฐานข้อมูลสำเร็จ!")
                    st.rerun()
                else:
                    st.error("❌ ข้อมูลไม่ถูกต้อง กรุณาเข้าใช้งานด้วยรหัสแอดมิน '222'")
                    
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==========================================
# 📥 3. ฟังก์ชันดึงข้อมูลจาก SQL (Supabase Multi-Table Fetch)
# ==========================================
@st.cache_data(ttl=3) 
def fetch_master_data(url, key):
    supabase: Client = create_client(url, key)
    ing_res = supabase.table("ingredients").select("*").execute()
    tgt_res = supabase.table("nutrition_targets").select("*").execute()
    brd_res = supabase.table("chicken_breeds").select("*").execute()
    
    ing_dict = {item["name"]: item for item in ing_res.data}
    tgt_dict = {item["stage_key"]: item for item in tgt_res.data}
    return ing_dict, tgt_dict, brd_res.data

try:
    ingredients_data, targets_data, breeds_data = fetch_master_data(st.session_state.supabase_url, st.session_state.supabase_key)
except Exception as e:
    st.error("❌ [Supabase SQL Error] ระบบไม่สามารถดึงข้อมูลลงมาจากฐานข้อมูลคลาวด์ได้")
    st.info(f"🔍 รายละเอียดความผิดพลาด: {str(e)}")
    if st.button("🔄 รีเฟรชและลองเชื่อมต่อใหม่อีกครั้ง"):
        st.rerun()
    st.stop()

if "optimized_weights" not in st.session_state:
    st.session_state.optimized_weights = {name: 0.0 for name in ingredients_data.keys()}

# ==========================================
# 🎉 4. ส่วนหัวแอปพลิเคชัน (Header)
# ==========================================
col_h1, col_h2 = st.columns([8, 2])
with col_h1:
    st.markdown("# 🐔 Mega Feed & Breed Studio")
    st.markdown("<p style='color:#10b981; font-weight:bold; font-size:1.2rem;'>🟢 เชื่อมต่อคลาวด์ฐานข้อมูล Supabase SQL พร้อม Schema ใหม่สำเร็จแล้ว</p>", unsafe_allow_html=True)
with col_h2:
    st.markdown(f"<p style='text-align:right; margin-bottom:5px;'>👤 <b>{st.session_state.user_email}</b></p>", unsafe_allow_html=True)
    if st.button("ออกจากระบบ (Logout)", use_container_width=True):
        st.session_state.is_authenticated = False
        st.rerun()

# ==========================================
# 📋 5. หน้าจอหลักและการแบ่งแท็บใช้งาน (4 แท็บหลัก)
# ==========================================
page_tabs = st.tabs(["🏠 ระบบผสมสูตร AI", "📊 สถิติ & ใบสั่งซื้อ PO", "📦 คลังวัตถุดิบ & จัดการข้อมูล SQL", "📈 เครื่องจำลองแผนการเติบโต"])

# --- [แท็บ 1]: AI Solver (ปรับโครงสร้างสีตาม Database) ---
with page_tabs[0]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    if not breeds_data or not targets_data:
        st.warning("⚠️ มีโครงสร้างตารางเรียบร้อย แต่ตรวจไม่พบแถวข้อมูล กรุณารันสคริปต์ SQL บนเว็บ Supabase ก่อนครับ")
    else:
        c_group, c_breed = st.columns(2)
        with c_group:
            st.markdown("#### 🧬 ข้อมูลสายพันธุ์และกลุ่ม")
            breed_options = {f"{b['group_name']} - {b['breed_name']}": b for b in breeds_data}
            selected_breed_label = st.selectbox("เลือกสายพันธุ์ไก่:", list(breed_options.keys()))
            selected_breed = breed_options[selected_breed_label]
            
            # 🎨 ระบบ Dynamic Color Card ตบแต่งตามสีที่ตั้งไว้ใน SQL Database ของสายพันธุ์นั้นๆ
            bg_c = selected_breed['bg_color'] if selected_breed['bg_color'] else '#1e293b'
            tx_c = selected_breed['text_color'] if selected_breed['text_color'] else '#ffffff'
            st.markdown(
                f"""
                <div style='background-color: {bg_c}; padding: 15px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.2);'>
                    <h4 style='margin:0; color: {tx_c} !important;'>🎯 สายพันธุ์: {selected_breed['breed_name']}</h4>
                    <p style='margin:5px 0 0 0; color: {tx_c} !important; font-size:0.95rem;'>
                        <b>ลักษณะสีเปลือกไข่:</b> {selected_breed['egg_color']}<br>
                        <b>ความต้องการกินอาหารเฉลี่ย:</b> {selected_breed['default_feed']} กรัม/วัน/ตัว<br>
                        <b>คำอธิบาย:</b> {selected_breed['description']}
                    </p>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
        with c_breed:
            st.markdown("#### 📈 ระยะการเลี้ยงและเป้าหมาย")
            target_options = {t["stage_name"]: t["stage_key"] for t in targets_data.values()}
            selected_stage_name = st.selectbox("เลือกโปรไฟล์โภชนาการตามช่วงอายุ:", list(target_options.keys()))
            selected_stage_key = target_options[selected_stage_name]
            req = targets_data[selected_stage_key]

        st.markdown("---")
        st.markdown("### 🧠 เครื่องคำนวณสมการเส้นตรง Least-Cost ด้วย AI")
        st.session_state.use_phytase = st.checkbox("🧪 เปิดใช้งานสารเสริมเอนไซม์ไฟเตส (ลดฟอสฟอรัส/แคลเซียมเป้าหมายลงอัตโนมัติ 0.10% และ 0.05%)")
        
        if st.button("⚡ เดินเครื่องระบบ AI ผสมสูตร (Run LP Solver)", type="primary"):
            with st.spinner("AI กำลังคำนวณราคาต่ำสุดภายใต้ข้อจำกัดโภชนาการ..."):
                prob = pulp.LpProblem("MegaPoultryLinearFeed", pulp.LpMinimize)
                
                ing_vars = {}
                for name, data in ingredients_data.items():
                    ing_vars[name] = pulp.LpVariable(name, lowBound=float(data["min_limit"])/100.0, upBound=float(data["max_limit"])/100.0)
                
                # Objective Function: ต้นทุนต่ำที่สุด
                prob += pulp.lpSum([ing_vars[name] * float(data["price"]) for name, data in ingredients_data.items()]), "Total_Cost"
                # Constraint: รวมกันต้องได้ 100% (1.0)
                prob += pulp.lpSum([ing_vars[name] for name in ingredients_data.keys()]) == 1.0, "Total_Weight"
                
                # คำนวณการชดเชยของไฟเตส (ถ้าเปิดใช้งาน)
                adj_p = float(req["phos"]) - 0.10 if st.session_state.use_phytase else float(req["phos"])
                adj_ca = float(req["calcium"]) - 0.05 if st.session_state.use_phytase else float(req["calcium"])
                
                # Constraints ด้านโภชนาการ
                prob += pulp.lpSum([ing_vars[name] * float(data["protein"]) for name, data in ingredients_data.items()]) >= float(req["protein"]), "Min_Protein"
                prob += pulp.lpSum([ing_vars[name] * float(data["me"]) for name, data in ingredients_data.items()]) >= float(req["me"]), "Min_ME"
                prob += pulp.lpSum([ing_vars[name] * float(data["calcium"]) for name, data in ingredients_data.items()]) >= adj_ca, "Min_Calcium"
                prob += pulp.lpSum([ing_vars[name] * float(data["phos"]) for name, data in ingredients_data.items()]) >= adj_p, "Min_Phosphorus"
                prob += pulp.lpSum([ing_vars[name] * float(data["lysine"]) for name, data in ingredients_data.items()]) >= float(req["lysine"]), "Min_Lysine"
                prob += pulp.lpSum([ing_vars[name] * float(data["methionine"]) for name, data in ingredients_data.items()]) >= float(req["methionine"]), "Min_Methionine"
                
                prob += pulp.lpSum([ing_vars[name] * float(data["fiber"]) for name, data in ingredients_data.items()]) <= float(req["fiber_max"]), "Max_Fiber"
                prob += pulp.lpSum([ing_vars[name] * float(data["sodium"]) for name, data in ingredients_data.items()]) >= float(req["sodium_min"]), "Min_Sodium"
                prob += pulp.lpSum([ing_vars[name] * float(data["chloride"]) for name, data in ingredients_data.items()]) >= float(req["chloride_min"]), "Min_Chloride"
                prob += pulp.lpSum([ing_vars[name] * float(data["linoleic"]) for name, data in ingredients_data.items()]) >= float(req["linoleic_min"]), "Min_Linoleic"

                prob.solve(pulp.PULP_CBC_CMD(msg=False))
                
                if pulp.LpStatus[prob.status] == "Optimal":
                    st.success(f"✅ AI คำนวณสูตรอาหารสำเร็จ! (ต้นทุนต่ำสุด: {pulp.value(prob.objective):.2f} บาท/กก.)")
                    for name in ingredients_data.keys():
                        st.session_state.optimized_weights[name] = ing_vars[name].varValue * 100.0
                else:
                    st.error("❌ เงื่อนไขหรือขอบเขตโภชนาการแน่นเกินไป ไม่สามารถหาทางผสมอาหารให้ผ่านเกณฑ์นี้ได้ กรุณาผ่อนปรนข้อจำกัดคลังวัตถุดิบ")

        if any(v > 0 for v in st.session_state.optimized_weights.values()):
            res_col1, res_col2 = st.columns([1.2, 1])
            with res_col1:
                st.markdown("#### 📊 สัดส่วนวัตถุดิบในสูตรอาหารปัจจุบัน")
                plot_data = [{"วัตถุดิบ": k, "สัดส่วน (%)": v} for k, v in st.session_state.optimized_weights.items() if v > 0.01]
                df_plot = pd.DataFrame(plot_data).sort_values(by="สัดส่วน (%)", ascending=False)
                fig = px.pie(df_plot, names="วัตถุดิบ", values="สัดส่วน (%)", hole=0.4)
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df_plot, use_container_width=True, hide_index=True)

            with res_col2:
                st.markdown("#### 🔬 ผลวิเคราะห์โภชนาการที่ได้จริง vs เกณฑ์เป้าหมาย")
                actual_nutrients = {"protein": 0, "me": 0, "calcium": 0, "phos": 0, "lysine": 0, "methionine": 0, "fiber": 0, "sodium": 0, "chloride": 0, "linoleic": 0, "threonine": 0, "fat": 0, "moisture": 0}
                cost_per_kg = 0
                for name, weight in st.session_state.optimized_weights.items():
                    if weight > 0:
                        frac = weight / 100.0
                        cost_per_kg += frac * float(ingredients_data[name]["price"])
                        for key in actual_nutrients.keys():
                            if key in ingredients_data[name] and ingredients_data[name][key] is not None:
                                actual_nutrients[key] += frac * float(ingredients_data[name][key])
                
                compare_data = [
                    {"สารอาหาร": "โปรตีน (%)", "ได้จริง": round(actual_nutrients["protein"], 2), "เป้าหมาย": f">= {req['protein']}"},
                    {"สารอาหาร": "พลังงาน (ME kcal/kg)", "ได้จริง": round(actual_nutrients["me"], 0), "เป้าหมาย": f">= {req['me']}"},
                    {"สารอาหาร": "แคลเซียม (%)", "ได้จริง": round(actual_nutrients["calcium"], 2), "เป้าหมาย": f">= {req['calcium']}"},
                    {"สารอาหาร": "ฟอสฟอรัสที่เป็นประโยชน์ (%)", "ได้จริง": round(actual_nutrients["phos"], 2), "เป้าหมาย": f">= {req['phos']}"},
                    {"สารอาหาร": "ไลซีน (%)", "ได้จริง": round(actual_nutrients["lysine"], 2), "เป้าหมาย": f">= {req['lysine']}"},
                    {"สารอาหาร": "เมทไธโอนีน (%)", "ได้จริง": round(actual_nutrients["methionine"], 2), "เป้าหมาย": f">= {req['methionine']}"},
                    {"สารอาหาร": "ทรีโอนีน (%) *ใหม่*", "ได้จริง": round(actual_nutrients["threonine"], 2), "เป้าหมาย": "ตามวัตถุดิบ"},
                    {"สารอาหาร": "ไขมันดิบ (%) *ใหม่*", "ได้จริง": round(actual_nutrients["fat"], 2), "เป้าหมาย": "ตามวัตถุดิบ"},
                    {"สารอาหาร": "ความชื้น (%) *ใหม่*", "ได้จริง": round(actual_nutrients["moisture"], 2), "เป้าหมาย": "ตามวัตถุดิบ"},
                    {"สารอาหาร": "กากใยสูงสุด (%)", "ได้จริง": round(actual_nutrients["fiber"], 2), "เป้าหมาย": f"<= {req['fiber_max']}"},
                    {"สารอาหาร": "โซเดียม (%)", "ได้จริง": round(actual_nutrients["sodium"], 2), "เป้าหมาย": f">= {req['sodium_min']}"},
                    {"สารอาหาร": "คลอไรด์ (%)", "ได้จริง": round(actual_nutrients["chloride"], 2), "เป้าหมาย": f">= {req['chloride_min']}"},
                    {"สารอาหาร": "กรดไลโนเลอิก (%)", "ได้จริง": round(actual_nutrients["linoleic"], 2), "เป้าหมาย": f">= {req['linoleic_min']}"},
                ]
                st.markdown(f"<h3 style='color:#10b981 !important;'>💰 ต้นทุนรวมสูตรผสม: {cost_per_kg:.2f} บาท/กก.</h3>", unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(compare_data), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- [แท็บ 2]: ใบจัดซื้อ (PO) & ราคาเฉลี่ยถ่วงน้ำหนัก ---
with page_tabs[1]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 📊 ระบบออกใบสั่งซื้อวัตถุดิบและคำนวณต้นทุนถ่วงน้ำหนักจริง")
    
    batch_size = st.number_input("ปริมาณรวมยอดผลิตผสมอาหารในล็อตนี้ (กิโลกรัม):", min_value=10, max_value=500000, value=1000, step=500)
    
    po_data = []
    total_po_cost = 0
    for k, v in st.session_state.optimized_weights.items():
        if v > 0.01:
            amount_kg = (v / 100.0) * batch_size
            est_price = amount_kg * float(ingredients_data[k]['price'])
            total_po_cost += est_price
            po_data.append({
                "วัตถุดิบที่ต้องจัดซื้อ": k, 
                "ปริมาณ (กก.)": round(amount_kg, 2), 
                "ราคาประเมินรวม (บาท)": round(est_price, 2)
            })
            
    if po_data:
        df_po = pd.DataFrame(po_data)
        st.dataframe(df_po, use_container_width=True, hide_index=True)
        
        weighted_average_cost = total_po_cost / batch_size
        
        c_m1, c_m2 = st.columns(2)
        with c_m1:
            st.metric("💵 มูลค่ารวมใบสั่งซื้อจัดหาล็อตนี้", f"{total_po_cost:,.2f} บาท")
        with c_m2:
            st.metric("🏷️ ต้นทุนเฉลี่ยถ่วงน้ำหนัก (Weighted Average)", f"{weighted_average_cost:.2f} บาท/กก.")
            
        csv_buffer = io.StringIO()
        df_po.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 ดาวน์โหลดไฟล์ใบสั่งซื้อ (Export PO to CSV)",
            data=csv_buffer.getvalue(),
            file_name=f"PO_Batch_{batch_size}kg.csv",
            mime="text/csv"
        )
    else:
        st.warning("กรุณากดคำนวณสูตรอาหาร AI ในหน้าแรกก่อนเพื่อสร้างใบสั่งซื้อ")
    st.markdown("</div>", unsafe_allow_html=True)

# --- [แท็บ 3]: จัดการคลังวัตถุดิบ & ส่งข้อมูลกลับ SQL ---
with page_tabs[2]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 📦 ศูนย์ควบคุมคลังข้อมูลโภชนาการวัตถุดิบ & ปรับปรุงแบบสดผ่าน SQL")
    st.info("คุณสามารถปรับแกราคา ข้อจำกัดขั้นต่ำ/สูงสุดได้จากฟอร์มนี้ และระบบจะส่งคำสั่ง UPDATE ไปยัง Supabase ให้ทันที")
    
    if ingredients_data:
        selected_ing_name = st.selectbox("เลือกวัตถุดิบที่ต้องการปรับปรุงข้อมูล:", list(ingredients_data.keys()))
        target_ing = ingredients_data[selected_ing_name]
        
        c_ed1, c_ed2, c_ed3 = st.columns(3)
        with c_ed1:
            new_price = st.number_input("ราคาปรับปรุงใหม่ (บาท/กก.):", value=float(target_ing["price"]), step=0.1)
        with c_ed2:
            new_min = st.number_input("ปรับเกณฑ์ขั้นต่ำสุด Min Limit (%):", value=float(target_ing["min_limit"]), step=1.0)
        with c_ed3:
            new_max = st.number_input("ปรับเกณฑ์สูงสุด Max Limit (%):", value=float(target_ing["max_limit"]), step=1.0)
            
        if st.button("💾 บันทึกและเขียนข้อมูลลงคลาวด์ฐานข้อมูล SQL", type="primary"):
            with st.spinner("กำลังทำการยิง SQL Update ไปยังเซิร์ฟเวอร์..."):
                try:
                    supabase_client = create_client(st.session_state.supabase_url, st.session_state.supabase_key)
                    supabase_client.table("ingredients").update({
                        "price": new_price,
                        "min_limit": new_min,
                        "max_limit": new_max
                    }).eq("name", selected_ing_name).execute()
                    
                    st.success(f"🎉 บันทึกการอัปเดตข้อมูลของ '{selected_ing_name}' เรียบร้อยแล้ว ระบบกำลังดึงโครงสร้างใหม่...")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as update_err:
                    st.error(f"❌ บันทึกลงฐานข้อมูลล้มเหลว: {str(update_err)}")
        
        st.markdown("---")
        st.markdown("### 📋 ตารางคลังสารอาหารและวัตถุดิบปัจจุบันทั้งหมด (Schema ล่าสุด)")
        df_ingredients = pd.DataFrame.from_dict(ingredients_data, orient='index')
        cols_to_display = ["price", "protein", "me", "calcium", "phos", "lysine", "methionine", "threonine", "fat", "moisture", "fiber", "sodium", "chloride", "linoleic", "min_limit", "max_limit"]
        df_ingredients = df_ingredients[cols_to_display]
        df_ingredients.rename(columns={
            "price": "ราคา", "protein": "โปรตีน(%)", "me": "พลังงาน(ME)",
            "calcium": "แคลเซียม(%)", "phos": "ฟอสฟอรัส(%)", "lysine": "ไลซีน(%)",
            "methionine": "เมท(%)", "threonine": "ทรีโอนีน(%)", "fat": "ไขมัน(%)", "moisture": "ความชื้น(%)",
            "fiber": "ใย(%)", "sodium": "Na(%)", "chloride": "Cl(%)", "linoleic": "ไลโนเลอิก(%)",
            "min_limit": "Min(%)", "max_limit": "Max(%)"
        }, inplace=True)
        st.dataframe(df_ingredients, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- [แท็บ 4]: เครื่องจำลองแผนการเติบโต ---
with page_tabs[3]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 📈 เครื่องจำลองแผนการเติบโตรายสายพันธุ์ (Growth & Feed Intake Simulator)")
    
    if breeds_data:
        c_sim1, c_sim2 = st.columns(2)
        with c_sim1:
            sim_birds = st.number_input("ปริมาณตัวเลขจำนวนไก่ในฝูง (ตัว):", min_value=1, value=2000, step=500)
            sim_days = st.slider("ช่วงอายุวันเลี้ยงที่ต้องการพยากรณ์ผลจำลอง (วัน):", min_value=7, max_value=105, value=42, step=7)
        with c_sim2:
            fcr_target = st.number_input("เป้าหมายสัมประสิทธิ์ FCR ล็อตนี้:", min_value=1.0, max_value=4.5, value=1.60, step=0.05)
            chick_cost = st.number_input("ราคาพันธุ์ต้นทุนลูกไก่แรกเกิด (บาท/ตัว):", min_value=0.0, value=14.0, step=1.0)

        days_list = list(range(1, sim_days + 1))
        weight_gain_daily = []
        feed_intake_daily = []
        
        current_feed_price = 14.50
        if any(v > 0 for v in st.session_state.optimized_weights.values()):
            current_feed_price = 0
            for name, weight in st.session_state.optimized_weights.items():
                current_feed_price += (weight / 100.0) * float(ingredients_data[name]["price"])

        for d in days_list:
            # สมการ Sigmoid curve วิเคราะห์อัตราเติบโตน้ำหนักตัวไก่สะสม
            est_weight = 42 + (3800 / (1 + 48 * (2.718 ** (-0.115 * d)))) 
            weight_gain_daily.append(est_weight)
            
            cumulative_feed = (est_weight / 1000.0) * fcr_target
            feed_intake_daily.append(cumulative_feed * 1000.0)
            
        df_sim = pd.DataFrame({
            "ระยะเวลา (วัน)": days_list,
            "น้ำหนักประเมินรายตัว (กรัม)": weight_gain_daily,
            "ปริมาณอาหารกินสะสม (กรัม)": feed_intake_daily
        })
        
        fig_sim = px.line(df_sim, x="ระยะเวลา (วัน)", y=["น้ำหนักประเมินรายตัว (กรัม)", "ปริมาณอาหารกินสะสม (กรัม)"],
                          title="📊 แนวโน้มการเจริญเติบโตสอดคล้องกับพฤติกรรมการกินอาหาร")
        fig_sim.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
        st.plotly_chart(fig_sim, use_container_width=True)
        
        final_weight_kg = weight_gain_daily[-1] / 1000.0
        total_feed_used_ton = (feed_intake_daily[-1] / 1000.0 * sim_birds) / 1000.0
        total_feed_cost = total_feed_used_ton * 1000 * current_feed_price
        total_investment = total_feed_cost + (sim_birds * chick_cost)
        
        st.markdown("### 📋 สรุปงบประมาณและข้อมูลตัวเลขเมื่อสิ้นสุดอายุโครงการ")
        c_r1, c_r2, c_r3 = st.columns(3)
        with c_r1:
            st.metric("⚖️ น้ำหนักตัวจับขายเฉลี่ยรายตัว", f"{final_weight_kg:.2f} กก.")
        with c_r2:
            st.metric("🌾 ความต้องการยอดใช้อาหารรวม", f"{total_feed_used_ton:.3f} ตัน")
        with c_r3:
            st.metric("💰 ประมาณการทุนรวม (พันธุ์ไก่ + อาหารผสม)", f"{total_investment:,.2f} บาท")
    st.markdown("</div>", unsafe_allow_html=True)
