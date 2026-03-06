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
st.set_page_config(page_title="Crypto Terminal PRO", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #000000;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .block-container { padding-top: 4rem; padding-bottom: 5rem; }
    .apple-card {
        background: #1C1C1E;
        border-radius: 18px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.5);
    }
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
    .text-secondary { color: #8E8E93; font-size: 0.8rem; }
    .price-up { color: #34C759; font-weight: 600; }
    .price-down { color: #FF453A; font-weight: 600; }
    .stButton>button { border-radius: 12px; font-weight: 600; }
    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 后端引擎
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
# 2. 账号系统 (修复 KeyError)
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
    st.markdown("<h2 style='text-align:center; color:white;'>Terminal</h2>", unsafe_allow_html=True)
    t_login, t_reg = st.tabs(["Sign In", "Register"])
    with t_login:
        with st.form("l"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Access", use_container_width=True):
                hp = hashlib.sha256(p.encode()).hexdigest()
                # 🛠 修复点：确保使用 db["users"][u]
                if u in db["users"] and db["users"][u]["password"] == hp:
                    tk = str(uuid.uuid4())
                    db["users"][u]["session_token"] = tk
                    save_db(db); st.query_params["token"] = tk
                    st.session_state.update({
                        "logged_in":True,
                        "username":u,
                        "balance":db["users"][u]["balance"],
                        "positions":db["users"][u]["positions"],
                        "chat_history":[]
                    })
                    st.rerun()
                else: st.error("Error")
    with t_reg:
        with st.form("r"):
            nu = st.text_input("New User")
            np = st.text_input("New Pass", type="password")
            if st.form_submit_button("Create", use_container_width=True):
                if nu and np and nu not in db["users"]:
                    db["users"][nu] = {"password":hashlib.sha256(np.encode()).hexdigest(),"balance":5000000.0,"positions":[],"session_token":""}
                    save_db(db); st.success("Done")
    st.stop()

# ==========================================
# 3. 数据引擎 (全市场)
# ==========================================
@st.cache_data(ttl=600)
def get_all_symbols():
    try:
        r = requests.get("https://data-api.binance.vision/api/v3/exchangeInfo", timeout=5)
        return [s['symbol'] for s in r.json()['symbols'] if s['symbol'].endswith('USDT') and s['status']=='TRADING']
    except: return ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

def get_price(sym):
    try:
        r = requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbol={sym}", timeout=3)
        return float(r.json()['price'])
    except: return 0.0

all_coins = get_all_symbols()

# ==========================================
# 4. UI 渲染
# ==========================================
st.markdown(f"**{st.session_state.username}** · Terminal Pro")

# 苹果风格余额栏
total_margin = sum(p['占用保证金'] for p in st.session_state.positions)
st.markdown(f"""
<div class="balance-header">
    <div class="text-secondary">Equity Value (USDT)</div>
    <div style="font-size: 2.2rem; font-weight: 600; color: #FFFFFF; letter-spacing: -1px;">
        {st.session_state.balance + total_margin:,.2f}
    </div>
</div>
""", unsafe_allow_html=True)

# 找回 AI 顾问
with st.expander("🤖 AI Market Assistant"):
    u_q = st.chat_input("Ask AI...")
    if u_q:
        st.session_state.chat_history.append({"role": "user", "content": u_q})
        try:
            res = requests.post("https://text.pollinations.ai/", json={"messages": [{"role":"system","content":"Crypto Expert. Short answer."}] + st.session_state.chat_history}, timeout=10)
            st.session_state.chat_history.append({"role": "assistant", "content": res.text})
        except: st.error("AI Error")
    for m in st.session_state.chat_history[-4:]:
        with st.chat_message(m["role"]): st.markdown(m["content"])

tab_market, tab_trade, tab_assets = st.tabs(["📊 Market", "📈 Trade", "💼 Assets"])

with tab_market:
    st.components.v1.html("""
    <style>body { background: transparent; color: white; font-family: -apple-system; } .row { display: flex; justify-content: space-between; padding: 12px 5px; border-bottom: 1px solid #2C2C2E; font-size:14px; }</style>
    <div id="l"></div>
    <script>
        const ws = new WebSocket('wss://data-stream.binance.vision:9443/ws/!ticker@arr');
        const ts = ['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','DOGEUSDT','PEPEUSDT','ORDIUSDT'];
        let els = {};
        ts.forEach(t => {
            let d = document.createElement('div'); d.className = 'row';
            d.innerHTML = `<b>${t}</b><span id="p-${t}">-</span><span id="c-${t}">-</span>`;
            document.getElementById('l').appendChild(d);
            els[t] = {p: document.getElementById(`p-${t}`), c: document.getElementById(`c-${t}`)};
        });
        ws.onmessage = (e) => {
            JSON.parse(e.data).forEach(i => { if(els[i.s]) {
                els[i.s].p.innerText = '$' + parseFloat(i.c).toFixed(2);
                els[i.s].c.innerText = parseFloat(i.P).toFixed(2) + '%';
                els[i.s].c.style.color = i.P >= 0 ? '#34C759' : '#FF453A';
            }});
        };
    </script>
    """, height=400)

with tab_trade:
    target = st.selectbox("Market", all_coins, index=all_coins.index("BTCUSDT"))
    st.components.v1.html(f"""
        <div id="tv" style="height:300px; border-radius:15px; overflow:hidden;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize":true,"symbol":"BINANCE:{target}","interval":"1","theme":"dark","style":"1","hide_top_toolbar":true,"container_id":"tv"}});</script>
    """, height=300)
    
    st.markdown(f"<div class='text-secondary'>Available: {st.session_state.balance:,.2f} USDT</div>", unsafe_allow_html=True)
    
    # 🌟 核心优化：建仓比例滑动条
    lev = st.slider("Leverage", 1, 1000, 100)
    # 用户拖动百分比，自动计算名义价值 (Notional = Balance * % * Leverage)
    balance_percent = st.slider("Use % of Balance", 0, 100, 10)
    suggested_amt = (st.session_state.balance * (balance_percent / 100)) * lev
    
    amt = st.number_input("Order Size (Notional USDT)", min_value=0.0, value=float(suggested_amt))
    m_needed = amt / lev
    st.caption(f"Margin Required: {m_needed:.2f} USDT")
    
    cb1, cb2 = st.columns(2)
    with cb1:
        if st.button("BUY / LONG", use_container_width=True, type="primary"):
            p = get_price(target)
            if p > 0 and st.session_state.balance >= m_needed:
                st.session_state.balance -= m_needed
                st.session_state.positions.append({"交易对":target,"方向":"LONG","开仓价":p,"杠杆":lev,"名义价值":amt,"占用保证金":m_needed})
                sync_data(); st.rerun()
    with cb2:
        if st.button("SELL / SHORT", use_container_width=True):
            p = get_price(target)
            if p > 0 and st.session_state.balance >= m_needed:
                st.session_state.balance -= m_needed
                st.session_state.positions.append({"交易对":target,"方向":"SHORT","开仓价":p,"杠杆":lev,"名义价值":amt,"占用保证金":m_needed})
                sync_data(); st.rerun()

with tab_assets:
    if st.button("Reset Account", use_container_width=True):
        st.session_state.update({"balance":5000000.0,"positions":[]}); sync_data(); st.rerun()
    
    if not st.session_state.positions:
        st.info("No Positions")
    else:
        # 获取实时价格
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
                        <b>{pos['交易对']} · {pos['方向']}</b>
                        <span class="{'price-up' if pnl>=0 else 'price-down'}">{pnl:+.2f} U</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                m1, m2 = st.columns(2)
                with m1:
                    if st.button("Close", key=f"c_{idx}", use_container_width=True):
                        st.session_state.balance += (pos['占用保证金'] + pnl)
                        st.session_state.positions.pop(idx)
                        sync_data(); st.rerun()
                with m2:
                    with st.popover("Adjust", use_container_width=True):
                        st.caption(f"Available: {st.session_state.balance:,.2f}")
                        # 🌟 减仓比例滑动条
                        adj_percent = st.slider("Adjust % of Position", 0, 100, 50, key=f"sl_{idx}")
                        adj_amt = pos['名义价值'] * (adj_percent / 100)
                        
                        st.write(f"Adjusting: {adj_amt:.2f} USDT")
                        if st.button("Add", key=f"a_{idx}"):
                            m_add = adj_amt / pos['杠杆']
                            if st.session_state.balance >= m_add:
                                st.session_state.balance -= m_add
                                pos['名义价值'] += adj_amt; pos['占用保证金'] += m_add
                                sync_data(); st.rerun()
                        if st.button("Reduce", key=f"r_{idx}"):
                            ratio = adj_percent / 100
                            st.session_state.balance += (pos['占用保证金'] * ratio + pnl * ratio)
                            pos['名义价值'] -= adj_amt; pos['占用保证金'] *= (1-ratio)
                            if pos['名义价值'] < 1: st.session_state.positions.pop(idx)
                            sync_data(); st.rerun()
