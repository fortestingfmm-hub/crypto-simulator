import streamlit as st
import pandas as pd
import requests
import time
import json
import os
import hashlib
import uuid

# ==========================================
# 0. Apple 简约科技风格 CSS
# ==========================================
st.set_page_config(page_title="Crypto Terminal", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* 全局背景与字体 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #000000;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* 顶部间距下沉 */
    .block-container { padding-top: 4rem; padding-bottom: 5rem; }
    
    /* 苹果风格卡片 */
    .apple-card {
        background: #1C1C1E;
        border-radius: 18px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.5);
    }
    
    /* 渐变余额栏 */
    .balance-header {
        background: rgba(28, 28, 30, 0.8);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: 20px;
        padding: 20px;
        position: sticky;
        top: 10px;
        z-index: 1000;
        border: 1px solid rgba(255,255,255,0.1);
        text-align: center;
        margin-bottom: 25px;
    }
    
    /* 文字颜色 */
    .text-secondary { color: #8E8E93; font-size: 0.8rem; }
    .price-up { color: #34C759; font-weight: 600; }
    .price-down { color: #FF453A; font-weight: 600; }
    
    /* 按钮美化 */
    .stButton>button {
        border-radius: 12px;
        border: none;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton>button:hover { transform: scale(1.02); }
    
    /* 隐藏默认元素 */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 后端引擎 (数据库/同步)
# ==========================================
DATA_FILE = "trading_data_v3.json"
def load_db():
    if not os.path.exists(DATA_FILE): return {"users": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {"users": {}}

def save_db(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

def sync_data():
    if st.session_state.get('logged_in'):
        db = load_db()
        u = st.session_state.username
        db["users"][u]["balance"] = st.session_state.balance
        db["users"][u]["positions"] = st.session_state.positions
        save_db(db)

# ==========================================
# 2. 账号系统
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
db = load_db()
tok = st.query_params.get("token")
if tok and not st.session_state.logged_in:
    for user, info in db["users"].items():
        if info.get("session_token") == tok:
            st.session_state.update({"logged_in":True,"username":user,"balance":info["balance"],"positions":info["positions"],"chat_history":[]})
            break

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align:center; color:white;'>Terminal Login</h2>", unsafe_allow_html=True)
    t_login, t_reg = st.tabs(["Sign In", "Register"])
    with t_login:
        with st.form("l"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Access Terminal", use_container_width=True):
                hp = hashlib.sha256(p.encode()).hexdigest()
                if u in db["users"] and db["users"][u]["password"] == hp:
                    tk = str(uuid.uuid4())
                    db["users"][u]["session_token"] = tk
                    save_db(db); st.query_params["token"] = tk
                    st.session_state.update({"logged_in":True,"username":u,"balance":db[u]["balance"],"positions":db[u]["positions"],"chat_history":[]})
                    st.rerun()
                else: st.error("Invalid Credentials")
    with t_reg:
        with st.form("r"):
            nu = st.text_input("New Username")
            np = st.text_input("New Password", type="password")
            if st.form_submit_button("Create Account", use_container_width=True):
                if nu and np and nu not in db["users"]:
                    db["users"][nu] = {"password":hashlib.sha256(np.encode()).hexdigest(),"balance":5000000.0,"positions":[],"session_token":""}
                    save_db(db); st.success("Account Ready")
    st.stop()

# ==========================================
# 3. 数据引擎 (全市场支持)
# ==========================================
@st.cache_data(ttl=600)
def get_all_symbols():
    try:
        # 使用币安 API 获取全量 USDT 交易对
        r = requests.get("https://data-api.binance.vision/api/v3/exchangeInfo", timeout=5)
        return [s['symbol'] for s in r.json()['symbols'] if s['symbol'].endswith('USDT') and s['status']=='TRADING']
    except: return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT"]

def get_price(sym):
    nodes = ['https://data-api.binance.vision', 'https://api.mexc.com']
    for n in nodes:
        try:
            r = requests.get(f"{n}/api/v3/ticker/price?symbol={sym}", timeout=3)
            return float(r.json()['price'])
        except: continue
    return 0.0

all_coins = get_all_symbols()

# ==========================================
# 4. 界面渲染
# ==========================================
# AI 抽屉式对话框 (集成回到顶部)
with st.container():
    col_l, col_r = st.columns([6, 1])
    with col_l:
        st.markdown(f"**Hello, {st.session_state.username}** ⚡ Pro Terminal")
    with col_r:
        if st.button("🚪"): 
            st.query_params.clear(); st.session_state.clear(); st.rerun()

# 苹果风格余额展示栏
# 计算当前浮动盈亏用于显示实时净资产
cur_prices = {} # 暂存价格
total_pnl = 0
total_margin = 0
for p in st.session_state.positions:
    total_margin += p['占用保证金']
    # 模拟持仓页外的快速估算，持仓页会有WSS
    
st.markdown(f"""
<div class="balance-header">
    <div class="text-secondary">Equity Value (USDT)</div>
    <div style="font-size: 2.2rem; font-weight: 600; color: #FFFFFF; letter-spacing: -1px;">
        {st.session_state.balance + total_margin:,.2f}
    </div>
    <div style="display: flex; justify-content: center; gap: 20px; margin-top: 10px;">
        <div class="text-secondary">Available: <span style="color:white">{st.session_state.balance:,.0f}</span></div>
        <div class="text-secondary">AI Consultant: <span style="color:#007AFF">Online</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# 重新找回 AI 顾问
with st.expander("🤖 Ask AI Assistant (Market Analysis)"):
    u_q = st.chat_input("Ask about market trends or your portfolio...")
    if u_q:
        st.session_state.chat_history.append({"role": "user", "content": u_q})
        try:
            prompt = f"System: User balance is {st.session_state.balance}U. Respond briefly in Chinese."
            res = requests.post("https://text.pollinations.ai/", json={"messages": [{"role":"system","content":prompt}] + st.session_state.chat_history}, timeout=10)
            if res.status_code == 200:
                reply = res.text
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
            else: st.error("AI Node Busy")
        except: st.error("AI Connection Failed")
    
    for m in st.session_state.chat_history[-4:]: # 只显示最近4条
        with st.chat_message(m["role"]): st.markdown(m["content"])

# 分页
tab_market, tab_trade, tab_assets = st.tabs(["📊 Market", "📈 Trade", "💼 Portfolio"])

# --- 行情页 ---
with tab_market:
    st.components.v1.html("""
    <style>
        body { background: transparent; color: white; font-family: -apple-system; }
        .row { display: flex; justify-content: space-between; padding: 15px 5px; border-bottom: 1px solid #2C2C2E; }
        .sym { font-weight: 600; }
    </style>
    <div id="list"></div>
    <script>
        const ws = new WebSocket('wss://data-stream.binance.vision:9443/ws/!ticker@arr');
        const list = document.getElementById('list');
        const targets = ['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','DOGEUSDT','PEPEUSDT','ORDIUSDT','WLDUSDT'];
        let els = {};
        targets.forEach(t => {
            let d = document.createElement('div'); d.className = 'row';
            d.innerHTML = `<span class="sym">${t.replace('USDT','')}</span><span id="p-${t}">-</span><span id="c-${t}">-</span>`;
            list.appendChild(d);
            els[t] = {p: document.getElementById(`p-${t}`), c: document.getElementById(`c-${t}`)};
        });
        ws.onmessage = (e) => {
            JSON.parse(e.data).forEach(i => {
                if(els[i.s]) {
                    els[i.s].p.innerText = '$' + parseFloat(i.c).toFixed(i.s.includes('PEPE')?6:2);
                    els[i.s].c.innerText = (i.P >= 0 ? '+' : '') + parseFloat(i.P).toFixed(2) + '%';
                    els[i.s].c.style.color = i.P >= 0 ? '#34C759' : '#FF453A';
                }
            });
        };
    </script>
    """, height=450)

# --- 交易页 (全币种) ---
with tab_trade:
    # 全市场币种选择
    target = st.selectbox("Select Asset", all_coins, index=all_coins.index("BTCUSDT"))
    
    st.components.v1.html(f"""
        <div id="tv" style="height:320px; border-radius:15px; overflow:hidden;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>
            new TradingView.widget({{
                "autosize": true, "symbol": "BINANCE:{target}", "interval": "1",
                "theme": "dark", "style": "1", "hide_top_toolbar": true, "container_id": "tv"
            }});
        </script>
    """, height=320)
    
    st.markdown(f"<div class='text-secondary'>Available Balance: {st.session_state.balance:,.2f} USDT</div>", unsafe_allow_html=True)
    
    # 金额输入与比例
    amt = st.number_input("Order Size (Notional USDT)", min_value=1.0, value=10000.0, step=1000.0)
    col_p1, col_p2, col_p3 = st.columns(3)
    if col_p1.button("25% Balance"): amt = st.session_state.balance * 0.25 * 100 # 假设估算
    if col_p2.button("50% Balance"): amt = st.session_state.balance * 0.50 * 100
    if col_p3.button("100% Balance"): amt = st.session_state.balance * 1.0 * 100
    
    lev = st.slider("Leverage", 1, 1000, 100)
    m_needed = amt / lev
    
    c_buy, c_sell = st.columns(2)
    with c_buy:
        if st.button("BUY / LONG", use_container_width=True, type="primary"):
            p = get_price(target)
            if p > 0 and st.session_state.balance >= m_needed:
                st.session_state.balance -= m_needed
                st.session_state.positions.append({"交易对":target,"方向":"LONG","开仓价":p,"杠杆":lev,"名义价值":amt,"占用保证金":m_needed})
                sync_data(); st.toast("Long Position Opened"); time.sleep(0.5); st.rerun()
    with c_sell:
        if st.button("SELL / SHORT", use_container_width=True):
            p = get_price(target)
            if p > 0 and st.session_state.balance >= m_needed:
                st.session_state.balance -= m_needed
                st.session_state.positions.append({"交易对":target,"方向":"SHORT","开仓价":p,"杠杆":lev,"名义价值":amt,"占用保证金":m_needed})
                sync_data(); st.toast("Short Position Opened"); time.sleep(0.5); st.rerun()

# --- 持仓管理页 ---
with tab_assets:
    st.button("🔄 Full Reset (5M USDT)", on_click=lambda: (st.session_state.update({"balance":5000000.0,"positions":[]}), sync_data()))
    
    if not st.session_state.positions:
        st.info("No active positions.")
    else:
        # 实时盈亏计算逻辑
        try:
            r_p = requests.get("https://data-api.binance.vision/api/v3/ticker/price", timeout=2).json()
            p_map = {x['symbol']: float(x['price']) for x in r_p}
        except: p_map = {}

        for idx, pos in enumerate(st.session_state.positions):
            now_p = p_map.get(pos['交易对'], pos['开仓价'])
            if pos['方向'] == "LONG": pnl = (now_p - pos['开仓价']) / pos['开仓价'] * pos['名义价值']
            else: pnl = (pos['开仓价'] - now_p) / pos['开仓价'] * pos['名义价值']
            
            with st.container():
                st.markdown(f"""
                <div class="apple-card">
                    <div style="display:flex; justify-content:space-between;">
                        <span style="font-weight:600;">{pos['交易对']} · {pos['方向']}</span>
                        <span class="{'price-up' if pnl >=0 else 'price-down'}">{pnl:+.2f} USDT</span>
                    </div>
                    <div class="text-secondary" style="margin-top:5px;">
                        Avg: {pos['开仓价']:.4f} | Cur: {now_p:.4f} | Lev: {pos['杠杆']}x
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 操作：平仓/加仓/减仓
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    if st.button("Close Position", key=f"c_{idx}", use_container_width=True):
                        st.session_state.balance += (pos['占用保证金'] + pnl)
                        st.session_state.positions.pop(idx)
                        sync_data(); st.rerun()
                with col_m2:
                    with st.popover("Adjust Size", use_container_width=True):
                        st.caption("Add or Reduce Position")
                        adj_amt = st.number_input("Amount (USDT)", key=f"adj_{idx}")
                        if st.button("Confirm Add", key=f"add_{idx}"):
                            # 简化加仓逻辑
                            m_add = adj_amt / pos['杠杆']
                            if st.session_state.balance >= m_add:
                                st.session_state.balance -= m_add
                                pos['名义价值'] += adj_amt
                                pos['占用保证金'] += m_add
                                sync_data(); st.rerun()
                        if st.button("Confirm Reduce", key=f"red_{idx}"):
                            # 简化减仓逻辑
                            ratio = min(adj_amt / pos['名义价值'], 1.0)
                            pnl_realized = pnl * ratio
                            st.session_state.balance += (pos['占用保证金'] * ratio + pnl_realized)
                            pos['名义价值'] -= adj_amt
                            pos['占用保证金'] *= (1-ratio)
                            if pos['名义价值'] <= 0: st.session_state.positions.pop(idx)
                            sync_data(); st.rerun()
