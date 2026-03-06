import streamlit as st
import pandas as pd
import requests
import time
import json
import os
import hashlib
import uuid

# ==========================================
# 0. 页面全局配置
# ==========================================
st.set_page_config(page_title="Crypto 模拟终端", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .block-container { padding-top: 3.5rem; padding-bottom: 5rem; }
    .title-text { font-size: 1.5rem; font-weight: bold; color: #fff; margin-bottom: 10px; }
    .stButton>button { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 数据库与同步引擎
# ==========================================
DATA_FILE = "trading_data.json"

def load_db():
    if not os.path.exists(DATA_FILE): return {"users": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)

def save_db(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

def hash_password(password): return hashlib.sha256(password.encode()).hexdigest()

def sync_current_user_data():
    if st.session_state.get('logged_in'):
        db = load_db()
        username = st.session_state.username
        db["users"][username]["balance"] = st.session_state.balance
        db["users"][username]["positions"] = st.session_state.positions
        save_db(db)

# ==========================================
# 2. 账号系统
# ==========================================
db = load_db()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

url_token = st.query_params.get("token")
if url_token and not st.session_state.logged_in:
    for user, u_data in db["users"].items():
        if u_data.get("session_token") == url_token:
            st.session_state.logged_in = True
            st.session_state.username = user
            st.session_state.balance = u_data["balance"]
            st.session_state.positions = u_data["positions"]
            st.session_state.chat_history = []
            break

if not st.session_state.logged_in:
    st.markdown('<div class="title-text">⚡ Crypto 模拟引擎</div>', unsafe_allow_html=True)
    tab_login, tab_register = st.tabs(["🔑 登录", "📝 注册新账号"])
    with tab_login:
        with st.form("login_form"):
            l_user = st.text_input("用户名")
            l_pass = st.text_input("密码", type="password")
            if st.form_submit_button("登 录", use_container_width=True):
                if l_user in db["users"] and db["users"][l_user]["password"] == hash_password(l_pass):
                    new_token = str(uuid.uuid4())
                    db["users"][l_user]["session_token"] = new_token
                    save_db(db)
                    st.query_params["token"] = new_token
                    st.session_state.logged_in = True
                    st.session_state.username = l_user
                    st.session_state.balance = db["users"][l_user]["balance"]
                    st.session_state.positions = db["users"][l_user]["positions"]
                    st.session_state.chat_history = []
                    st.rerun()
                else: st.error("密码错误！")
    with tab_register:
        with st.form("register_form"):
            r_user = st.text_input("设置用户名")
            r_pass = st.text_input("设置密码", type="password")
            if st.form_submit_button("注 册", use_container_width=True):
                if r_user not in db["users"]:
                    db["users"][r_user] = {"password": hash_password(r_pass), "balance": 5000000.0, "positions": [], "session_token": ""}
                    save_db(db)
                    st.success("注册成功！")
    st.stop() 

# ==========================================
# 3. 网络与价格引擎
# ==========================================
API_NODES = ['https://data-api.binance.vision', 'https://api.mexc.com']
@st.cache_data(ttl=3600) 
def get_all_usdt_symbols():
    for url in API_NODES:
        try:
            res = requests.get(f"{url}/api/v3/exchangeInfo", timeout=8)
            return [s['symbol'] for s in res.json()['symbols'] if s['symbol'].endswith('USDT') and s['status'] in ['TRADING', 'ENABLED']]
        except: continue
    return ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

all_symbols = get_all_usdt_symbols()

def get_single_price(symbol):
    for url in API_NODES:
        try:
            res = requests.get(f"{url}/api/v3/ticker/price?symbol={symbol}", timeout=3)
            return float(res.json().get('price', 0))
        except: continue
    return 0.0

def settle_liquidations():
    active = []
    for pos in st.session_state.positions:
        price = get_single_price(pos["交易对"])
        pnl = (price - pos["开仓价"]) / pos["开仓价"] * pos["名义价值"] if pos["方向"] == "做多 🟢" else (pos["开仓价"] - price) / pos["开仓价"] * pos["名义价值"]
        if pnl <= -pos["占用保证金"]: continue
        active.append(pos)
    st.session_state.positions = active
    sync_current_user_data()

# ==========================================
# 4. 顶部导航与 AI
# ==========================================
col_t, col_ai, col_ex = st.columns([5, 2, 2])
with col_t: st.markdown('<div class="title-text">⚡ Crypto 模拟引擎</div>', unsafe_allow_html=True)
with col_ex:
    if st.button("🚪 退出", use_container_width=True): 
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()

with col_ai:
    with st.popover("🤖 AI", use_container_width=True):
        u_in = st.chat_input("问问 AI...")
        if u_in:
            st.session_state.chat_history.append({"role": "user", "content": u_in})
            prompt = f"你是顾问。当前余额:{st.session_state.balance}U。仓位:{len(st.session_state.positions)}个。"
            res = requests.post("https://text.pollinations.ai/", json={"messages": [{"role":"system","content":prompt}]+st.session_state.chat_history})
            st.markdown(res.text)
            st.session_state.chat_history.append({"role": "assistant", "content": res.text})

st.divider()

# ==========================================
# 5. 主板块
# ==========================================
tab_market, tab_trade, tab_assets = st.tabs(["📊 毫秒行情", "📈 极速交易", "💼 资产持仓"])

with tab_market:
    st.components.v1.html("""
        <style>body { background-color:#0E1117; color:white; font-family:sans-serif; margin:0; } table { width:100%; border-collapse:collapse; font-size:14px; } th, td { padding:12px 8px; text-align:left; border-bottom:1px solid #2b3139; } th { color:#848e9c; } .g { color:#0ecb81; } .r { color:#f6465d; } </style>
        <table><thead><tr><th>币种</th><th>最新价</th><th>涨跌</th></tr></thead><tbody id="m"></tbody></table>
        <script>
            const ws = new WebSocket('wss://data-stream.binance.vision:9443/ws/!ticker@arr');
            const coins = ['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','DOGEUSDT','PEPEUSDT'];
            const b = document.getElementById('m'); let r = {};
            coins.forEach(c => { let tr = document.createElement('tr'); tr.innerHTML = `<td>${c}</td><td id="p-${c}">-</td><td id="c-${c}">-</td>`; b.appendChild(tr); r[c] = { p:document.getElementById(`p-${c}`), c:document.getElementById(`c-${c}`) }; });
            ws.onmessage = (e) => { JSON.parse(e.data).forEach(i => { if(r[i.s]) { r[i.s].p.innerText = '$'+parseFloat(i.c).toFixed(2); r[i.s].c.innerText = parseFloat(i.P).toFixed(2)+'%'; r[i.s].c.className = i.P>=0?'g':'r'; } }); };
        </script>
    """, height=400)

with tab_trade:
    sym = st.selectbox("选择币种", all_symbols, format_func=lambda x: x.replace("USDT", "/USDT"), label_visibility="collapsed")
    st.components.v1.html(f"""
        <div id="tv_{sym}" style="height:350px;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize":true,"symbol":"BINANCE:{sym}","interval":"1","theme":"dark","style":"1","hide_top_toolbar":true,"container_id":"tv_{sym}"}});</script>
    """, height=350)
    
    st.markdown("#### ⚡ 快速下单")
    # 🌟 优化：建仓时显示可用余额
    st.metric("当前可用余额", f"{st.session_state.balance:,.2f} USDT")
    
    lev = st.slider("杠杆倍数", 1, 1000, 100)
    amt = st.number_input("开仓名义价值 (USDT)", min_value=1.0, value=10000.0)
    m_req = amt / lev
    st.caption(f"🛡️ 所需保证金: **{m_req:.2f} U**")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🟢 做多", use_container_width=True):
            settle_liquidations()
            p = get_single_price(sym)
            if p > 0 and st.session_state.balance >= m_req:
                st.session_state.balance -= m_req
                st.session_state.positions.append({"方向": "做多 🟢", "交易对": sym, "杠杆": lev, "名义价值": amt, "占用保证金": m_req, "开仓价": p})
                sync_current_user_data(); st.toast("开仓成功！"); time.sleep(0.5); st.rerun()
            else: st.error("资金不足或网络错误")
    with c2:
        if st.button("🔴 做空", use_container_width=True):
            settle_liquidations()
            p = get_single_price(sym)
            if p > 0 and st.session_state.balance >= m_req:
                st.session_state.balance -= m_req
                st.session_state.positions.append({"方向": "做空 🔴", "交易对": sym, "杠杆": lev, "名义价值": amt, "占用保证金": m_req, "开仓价": p})
                sync_current_user_data(); st.toast("开仓成功！"); time.sleep(0.5); st.rerun()
            else: st.error("资金不足或网络错误")

with tab_assets:
    # 🌟 资产看板逻辑
    if st.button("🔄 重置 500 万资金", use_container_width=True):
        st.session_state.balance = 5000000.0; st.session_state.positions = []; sync_current_user_data(); st.rerun()
    
    # 获取实时价格用于显示
    prices = {}
    if st.session_state.positions:
        try:
            res = requests.get("https://data-api.binance.vision/api/v3/ticker/price", timeout=2)
            for i in res.json(): prices[i['symbol']] = float(i['price'])
        except: pass

    total_pnl = 0
    total_margin = 0
    for pos in st.session_state.positions:
        cur_p = prices.get(pos["交易对"], pos["开仓价"])
        if pos["方向"] == "做多 🟢": p_pnl = (cur_p - pos["开仓价"]) / pos["开仓价"] * pos["名义价值"]
        else: p_pnl = (pos["开仓价"] - cur_p) / pos["开仓价"] * pos["名义价值"]
        total_pnl += p_pnl
        total_margin += pos["占用保证金"]
        pos["temp_pnl"] = p_pnl
        pos["temp_price"] = cur_p

    st.markdown(f"""
    <div style="background:#1e222d; padding:15px; border-radius:10px; text-align:center; border:1px solid #2b3139;">
        <div style="color:#848e9c; font-size:12px;">实时总净资产 (U)</div>
        <div style="font-size:32px; font-weight:bold; color:{'#0ecb81' if total_pnl >= 0 else '#f6465d'};">{(st.session_state.balance + total_margin + total_pnl):,.2f}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("#### 当前持仓")
    if not st.session_state.positions:
        st.info("暂无持仓")
    else:
        # 🌟 重点优化：循环渲染持仓，支持单独平仓
        for idx, pos in enumerate(st.session_state.positions):
            with st.container(border=True):
                c_h, c_b = st.columns([3, 1])
                with c_h:
                    st.markdown(f"**{pos['交易对']}** | {pos['方向']} | {pos['杠杆']}x")
                    st.write(f"盈亏: {pos['temp_pnl']:.2f} U ({(pos['temp_pnl']/pos['占用保证金']*100):.2f}%)")
                with c_b:
                    # 🔴 单独平仓按钮
                    if st.button("平仓", key=f"btn_{idx}", type="primary"):
                        cur_p = get_single_price(pos["交易对"])
                        if cur_p == 0: cur_p = pos["temp_price"]
                        # 重新计算最终盈亏
                        if pos["方向"] == "做多 🟢": final_pnl = (cur_p - pos["开仓价"]) / pos["开仓价"] * pos["名义价值"]
                        else: final_pnl = (pos["开仓价"] - cur_p) / pos["开仓价"] * pos["名义价值"]
                        # 返还资金：保证金 + 盈亏
                        st.session_state.balance += (pos["占用保证金"] + final_pnl)
                        # 移除该持仓
                        st.session_state.positions.pop(idx)
                        sync_current_user_data()
                        st.toast(f"{pos['交易对']} 已平仓结算")
                        time.sleep(0.5)
                        st.rerun()
