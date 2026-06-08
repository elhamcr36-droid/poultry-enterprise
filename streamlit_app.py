import streamlit as st
import pandas as pd
import plotly.express as px
import pulp
from supabase import create_client, Client

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
    /* Style สำหรับ Dataframe ให้สีสว่างขึ้นเพื่อให้อ่านง่าย */
    [data-testid="stDataFrame"] { background-color: rgba(255,255,255,0.9) !important; border-radius: 10px; padding: 5px; }
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================================
# 🔐 2. ระบบล็อคอินและยืนยันตัวตนด้วย Supabase
# ==========================================
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False
if "supabase_url" not in st.session_state:
    st.session_state.supabase_url = ""
if "supabase_key" not in st.session_state:
    st.session_state.supabase_key = ""

def init_supabase(url, key):
    try:
        return create_client(url, key)
    except Exception:
        return None

if not st.session_state.is_authenticated:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center;'>🔐 ยินดีต้อนรับสู่ Mega Feed & Breed Studio</h2>", unsafe_allow_html=True)
    
    with st.expander("☁️ การเชื่อมต่อคลาวด์และฐานข้อมูลหลัก (Supabase Configuration)", expanded=True):
        c_db1, c_db2 = st.columns(2)
        with c_db1:
            try:
                default_url = st.secrets["SUPABASE_URL"]
            except:
                default_url = "https://<รหัสโปรเจกต์ของคุณ>.supabase.co"
            input_url = st.text_input("ลิงก์โปรเจกต์ Supabase", default_url).strip()
            
        with c_db2:
            try:
                default_key = st.secrets["SUPABASE_KEY"]
            except:
                default_key = "sb_publishable_m411zYbsazCAsmmUMIuMkA_ypb1BYPr"
            input_key = st.text_input("รหัสผ่าน API (Anon Key)", default_key, type="password").strip()

    st.markdown("---")
    tab_login, tab_register = st.tabs(["🔑 เข้าสู่ระบบ (Login)", "📝 สมัครสมาชิก (Register)"])
    
    # --- แท็บเข้าสู่ระบบ ---
    with tab_login:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            email_login = st.text_input("📧 อีเมล หรือ ชื่อผู้ใช้", key="login_email")
            pass_login = st.text_input("🔑 รหัสผ่าน", type="password", key="login_pass")
            
            if st.button("เข้าสู่ระบบ (Login)", type="primary", use_container_width=True):
                # Admin Bypass (อัปเดตตามคำขอ)
                if email_login in ["222", "จีเมล222", "222@gmail.com"] and pass_login in ["222", "รหัส222"]:
                    st.session_state.is_authenticated = True
                    st.session_state.user_email = "👑 Admin (Superuser)"
                    st.session_state.supabase_url = input_url
                    st.session_state.supabase_key = input_key
                    st.success("✅ เข้าสู่ระบบแอดมินสำเร็จ!")
                    st.rerun()
                elif input_url and input_key and email_login and pass_login:
                    sb: Client = init_supabase(input_url, input_key)
                    if sb:
                        try:
                            res = sb.auth.sign_in_with_password({"email": email_login, "password": pass_login})
                            st.session_state.is_authenticated = True
                            st.session_state.user_email = res.user.email
                            st.session_state.supabase_url = input_url
                            st.session_state.supabase_key = input_key
                            st.success("✅ เข้าสู่ระบบสำเร็จ!")
                            st.rerun()
                        except Exception as e:
                            st.error("❌ อีเมล หรือรหัสผ่านไม่ถูกต้อง")
                    else:
                        st.error("❌ เชื่อมต่อ Supabase ไม่ได้")
                else:
                    st.warning("⚠️ กรุณากรอกข้อมูลให้ครบถ้วน")

    # --- แท็บสมัครสมาชิก ---
    with tab_register:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            email_reg = st.text_input("📧 อีเมล", key="reg_email")
            pass_reg = st.text_input("🔑 รหัสผ่าน", type="password", key="reg_pass")
            pass_confirm = st.text_input("🔑 ยืนยันรหัสผ่าน", type="password", key="reg_pass_confirm")
            
            if st.button("สมัครสมาชิก (Register)", type="primary", use_container_width=True):
                if input_url and input_key and email_reg and pass_reg and pass_confirm:
                    if pass_reg != pass_confirm:
                        st.error("❌ รหัสผ่านไม่ตรงกัน")
                    elif len(pass_reg) < 6:
                        st.error("❌ รหัสผ่านต้องยาวอย่างน้อย 6 ตัวอักษร")
                    else:
                        sb: Client = init_supabase(input_url, input_key)
                        if sb:
                            try:
                                res = sb.auth.sign_up({"email": email_reg, "password": pass_reg})
                                st.success("✅ สมัครสมาชิกสำเร็จ! กลับไปหน้าเข้าสู่ระบบได้เลย")
                            except Exception as e:
                                st.error(f"❌ ล้มเหลว: {str(e)}")
                else:
                    st.warning("⚠️ กรุณากรอกข้อมูลให้ครบ")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==========================================
# 📥 3. ดึงข้อมูลจากฐานข้อมูล Supabase 
# ==========================================
@st.cache_data(ttl=600)
def fetch_master_data(url, key):
    try:
        supabase: Client = create_client(url, key)
        ing_res = supabase.table("ingredients").select("*").execute()
        tgt_res = supabase.table("nutrition_targets").select("*").execute()
        brd_res = supabase.table("chicken_breeds").select("*").execute()
        
        ing_dict = {item["name"]: item for item in ing_res.data}
        tgt_dict = {item["stage_key"]: item for item in tgt_res.data}
        return ing_dict, tgt_dict, brd_res.data
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลจาก Supabase: {e}")
        return {}, {}, []

ingredients_data, targets_data, breeds_data = fetch_master_data(st.session_state.supabase_url, st.session_state.supabase_key)

if not ingredients_data or not targets_data:
    st.warning("⏳ ไม่พบข้อมูลในระบบ หรือเชื่อมต่อฐานข้อมูลล้มเหลว กรุณาตรวจสอบข้อมูลใน Supabase")
    if st.button("ออกจากระบบเพื่อตั้งค่าใหม่"):
        st.session_state.is_authenticated = False
        st.rerun()
    st.stop()

if "optimized_weights" not in st.session_state:
    st.session_state.optimized_weights = {name: 0.0 for name in ingredients_data.keys()}

# ==========================================
# 🎉 4. ส่วนหัว (Header) ของแอป
# ==========================================
col_h1, col_h2 = st.columns([8, 2])
with col_h1:
    st.markdown("# 🐔 Mega Feed & Breed Studio")
    st.markdown("### ระบบปัญญาประดิษฐ์คำนวณสูตรอาหาร โภชนาการขั้นสูง (14 พารามิเตอร์) และบริหารคลัง")
with col_h2:
    st.markdown(f"<p style='text-align:right; margin-bottom:5px;'>👤 <b>{st.session_state.user_email}</b></p>", unsafe_allow_html=True)
    if st.button("ออกจากระบบ (Logout)", use_container_width=True):
        st.session_state.is_authenticated = False
        st.rerun()

# ==========================================
# 📋 5. แท็บหลักการใช้งาน
# ==========================================
page_tabs = st.tabs(["🏠 ระบบผสมสูตร AI", "📊 สถิติ & PO", "📦 คลังวัตถุดิบ"])

# --- [แท็บ 1]: AI Solver (รวมข้อมูลขั้นสูง) ---
with page_tabs[0]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    c_group, c_breed = st.columns(2)
    
    with c_group:
        st.markdown("#### 🧬 ข้อมูลสายพันธุ์")
        breed_options = {b["breed_name"]: b for b in breeds_data}
        selected_breed_name = st.selectbox("เลือกสายพันธุ์ไก่:", list(breed_options.keys()))
        selected_breed = breed_options[selected_breed_name]
        st.info(f"**ลักษณะ:** {selected_breed['description']} | **การกิน:** {selected_breed['default_feed']} กรัม/วัน")
        
    with c_breed:
        st.markdown("#### 📈 ระยะการเลี้ยง")
        target_options = {t["stage_name"]: t["stage_key"] for t in targets_data.values()}
        selected_stage_name = st.selectbox("เลือกโปรไฟล์โภชนาการตามช่วงอายุ:", list(target_options.keys()))
        selected_stage_key = target_options[selected_stage_name]
        req = targets_data[selected_stage_key]

    st.markdown("---")
    st.markdown("### 🧠 เครื่องคำนวณสมการเส้นตรง Least-Cost ด้วย AI")
    st.session_state.use_phytase = st.checkbox("🧪 เปิดใช้งานสารเสริมเอนไซม์ไฟเตส (ลดฟอสฟอรัส/แคลเซียมเป้าหมายลงอัตโนมัติ)")
    
    if st.button("⚡ เดินเครื่องระบบ AI ผสมสูตร (Run LP Solver)", type="primary"):
        with st.spinner("AI กำลังปรับสมดุลแร่ธาตุ โซเดียม เยื่อใย และคำนวณราคาต่ำสุด..."):
            prob = pulp.LpProblem("MegaPoultryLinearFeed", pulp.LpMinimize)
            
            # ตัวแปรการตัดสินใจ (สัดส่วนวัตถุดิบ)
            ing_vars = {}
            for name, data in ingredients_data.items():
                ing_vars[name] = pulp.LpVariable(name, lowBound=float(data["min_limit"])/100.0, upBound=float(data["max_limit"])/100.0)
            
            # สมการราคาเป้าหมาย
            prob += pulp.lpSum([ing_vars[name] * float(data["price"]) for name, data in ingredients_data.items()]), "Total_Cost"
            
            # ข้อจำกัดน้ำหนักรวม 100%
            prob += pulp.lpSum([ing_vars[name] for name in ingredients_data.keys()]) == 1.0, "Total_Weight"
            
            # ปรับเป้าหมายเมื่อใช้ Phytase
            adj_p = float(req["phos"]) - 0.10 if st.session_state.use_phytase else float(req["phos"])
            adj_ca = float(req["calcium"]) - 0.05 if st.session_state.use_phytase else float(req["calcium"])
            
            # ข้อจำกัดโภชนาการพื้นฐาน
            prob += pulp.lpSum([ing_vars[name] * float(data["protein"]) for name, data in ingredients_data.items()]) >= float(req["protein"]), "Min_Protein"
            prob += pulp.lpSum([ing_vars[name] * float(data["me"]) for name, data in ingredients_data.items()]) >= float(req["me"]), "Min_ME"
            prob += pulp.lpSum([ing_vars[name] * float(data["calcium"]) for name, data in ingredients_data.items()]) >= adj_ca, "Min_Calcium"
            prob += pulp.lpSum([ing_vars[name] * float(data["phos"]) for name, data in ingredients_data.items()]) >= adj_p, "Min_Phosphorus"
            prob += pulp.lpSum([ing_vars[name] * float(data["lysine"]) for name, data in ingredients_data.items()]) >= float(req["lysine"]), "Min_Lysine"
            prob += pulp.lpSum([ing_vars[name] * float(data["methionine"]) for name, data in ingredients_data.items()]) >= float(req["methionine"]), "Min_Methionine"
            
            # ข้อจำกัดโภชนาการขั้นสูง
            prob += pulp.lpSum([ing_vars[name] * float(data["fiber"]) for name, data in ingredients_data.items()]) <= float(req["fiber_max"]), "Max_Fiber"
            prob += pulp.lpSum([ing_vars[name] * float(data["sodium"]) for name, data in ingredients_data.items()]) >= float(req["sodium_min"]), "Min_Sodium"
            prob += pulp.lpSum([ing_vars[name] * float(data["chloride"]) for name, data in ingredients_data.items()]) >= float(req["chloride_min"]), "Min_Chloride"
            prob += pulp.lpSum([ing_vars[name] * float(data["linoleic"]) for name, data in ingredients_data.items()]) >= float(req["linoleic_min"]), "Min_Linoleic"

            prob.solve(pulp.PULP_CBC_CMD(msg=False))
            
            if pulp.LpStatus[prob.status] == "Optimal":
                st.success(f"✅ AI ประมวลผลสำเร็จ! (ราคาประเมิน: {pulp.value(prob.objective):.2f} บาท/กก.)")
                for name in ingredients_data.keys():
                    st.session_state.optimized_weights[name] = ing_vars[name].varValue * 100.0
            else:
                st.error("❌ AI ไม่สามารถหาสูตรที่ตรงตามเงื่อนไขโภชนาการได้ (Infeasible) โปรดตรวจสอบ Min/Max limit ของวัตถุดิบ")

    # ส่วนแสดงผลลัพธ์ (ถ้ามีค่าที่คำนวณได้แล้ว)
    if any(v > 0 for v in st.session_state.optimized_weights.values()):
        res_col1, res_col2 = st.columns([1.2, 1])
        
        with res_col1:
            st.markdown("#### 📊 สัดส่วนวัตถุดิบในสูตร")
            plot_data = [{"วัตถุดิบ": k, "สัดส่วน (%)": v} for k, v in st.session_state.optimized_weights.items() if v > 0.01]
            df_plot = pd.DataFrame(plot_data).sort_values(by="สัดส่วน (%)", ascending=False)
            fig = px.pie(df_plot, names="วัตถุดิบ", values="สัดส่วน (%)", hole=0.4)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_plot, use_container_width=True, hide_index=True)

        with res_col2:
            st.markdown("#### 🔬 โภชนาการที่ได้จริง vs เป้าหมาย")
            actual_nutrients = {
                "protein": 0, "me": 0, "calcium": 0, "phos": 0, "lysine": 0, 
                "methionine": 0, "fiber": 0, "sodium": 0, "chloride": 0, "linoleic": 0
            }
            cost_per_kg = 0
            for name, weight in st.session_state.optimized_weights.items():
                if weight > 0:
                    frac = weight / 100.0
                    cost_per_kg += frac * float(ingredients_data[name]["price"])
                    for key in actual_nutrients.keys():
                        actual_nutrients[key] += frac * float(ingredients_data[name][key])
            
            compare_data = [
                {"สารอาหาร": "โปรตีน (%)", "ได้จริง": round(actual_nutrients["protein"], 2), "เป้าหมาย": f">= {req['protein']}"},
                {"สารอาหาร": "พลังงาน (ME)", "ได้จริง": round(actual_nutrients["me"], 0), "เป้าหมาย": f">= {req['me']}"},
                {"สารอาหาร": "แคลเซียม (%)", "ได้จริง": round(actual_nutrients["calcium"], 2), "เป้าหมาย": f">= {req['calcium']}"},
                {"สารอาหาร": "ฟอสฟอรัส (%)", "ได้จริง": round(actual_nutrients["phos"], 2), "เป้าหมาย": f">= {req['phos']}"},
                {"สารอาหาร": "ไลซีน (%)", "ได้จริง": round(actual_nutrients["lysine"], 2), "เป้าหมาย": f">= {req['lysine']}"},
                {"สารอาหาร": "เมทไธโอนีน (%)", "ได้จริง": round(actual_nutrients["methionine"], 2), "เป้าหมาย": f">= {req['methionine']}"},
                {"สารอาหาร": "กากใย (%)", "ได้จริง": round(actual_nutrients["fiber"], 2), "เป้าหมาย": f"<= {req['fiber_max']}"},
                {"สารอาหาร": "โซเดียม (%)", "ได้จริง": round(actual_nutrients["sodium"], 2), "เป้าหมาย": f">= {req['sodium_min']}"},
                {"สารอาหาร": "คลอไรด์ (%)", "ได้จริง": round(actual_nutrients["chloride"], 2), "เป้าหมาย": f">= {req['chloride_min']}"},
                {"สารอาหาร": "ไลโนเลอิก (%)", "ได้จริง": round(actual_nutrients["linoleic"], 2), "เป้าหมาย": f">= {req['linoleic_min']}"},
            ]
            st.markdown(f"<h3 style='color:#10b981 !important;'>💰 ต้นทุน: {cost_per_kg:.2f} บาท/กก.</h3>", unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(compare_data), use_container_width=True, hide_index=True)

    st.markdown("</div>", unsafe_allow_html=True)

# --- [แท็บ 2]: สถิติฟาร์ม & ใบจัดซื้อ (PO) ---
with page_tabs[1]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 📊 สร้างใบสั่งซื้อวัตถุดิบ (PO Simulator)")
    st.info("จำลองการคำนวณการสั่งซื้อวัตถุดิบตามสัดส่วนสูตรที่ AI คำนวณได้ สำหรับทำอาหาร 1 ตัน (1,000 กก.)")
    
    po_data = []
    total_po_cost = 0
    for k, v in st.session_state.optimized_weights.items():
        if v > 0.01:
            amount_kg = (v / 100.0) * 1000
            est_price = amount_kg * float(ingredients_data[k]['price'])
            total_po_cost += est_price
            po_data.append({
                "รายการวัตถุดิบ": k, 
                "จำนวนที่ต้องสั่ง (กก.)": round(amount_kg, 2), 
                "ราคาประเมิน (บาท)": round(est_price, 2)
            })
            
    if po_data:
        st.dataframe(pd.DataFrame(po_data), use_container_width=True)
        st.markdown(f"#### 🏷️ ยอดรวมใบสั่งซื้อ: {total_po_cost:,.2f} บาท / ตัน")
    else:
        st.warning("กรุณากดคำนวณสูตรอาหาร AI ในหน้าแรกก่อนเพื่อสร้างใบสั่งซื้อ")
    st.markdown("</div>", unsafe_allow_html=True)

# --- [แท็บ 3]: ศูนย์จัดการคลังวัตถุดิบ ---
with page_tabs[2]:
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("## 📦 ศูนย์จัดการคลังวัตถุดิบ (Master Database)")
    st.markdown("ข้อมูลโภชนาการและข้อจำกัดวัตถุดิบ 14 พารามิเตอร์ที่ดึงสดจาก Supabase")
    
    # ปรับรูปแบบ DataFrame ให้สวยงาม
    df_ingredients = pd.DataFrame.from_dict(ingredients_data, orient='index')
    cols_to_display = ["price", "protein", "me", "calcium", "phos", "lysine", "methionine", "fiber", "sodium", "chloride", "linoleic", "min_limit", "max_limit"]
    df_ingredients = df_ingredients[cols_to_display]
    
    df_ingredients.rename(columns={
        "price": "ราคา", "protein": "โปรตีน(%)", "me": "พลังงาน(ME)",
        "calcium": "แคลเซียม(%)", "phos": "ฟอสฟอรัส(%)", "lysine": "ไลซีน(%)",
        "methionine": "เมท(%)", "fiber": "ใย(%)", "sodium": "Na(%)",
        "chloride": "Cl(%)", "linoleic": "ไลโนเลอิก(%)", "min_limit": "Min(%)", "max_limit": "Max(%)"
    }, inplace=True)
    
    st.dataframe(df_ingredients, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
