import streamlit as st
import pandas as pd
import requests
import time
import json
import os
import hashlib
import uuid

# ==========================================
# 0. UI 配置 - Apple 极简白
# ==========================================
st.set_page_config(page_title="Crypto Terminal", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;600&display=swap');
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #F5F5F7;
        font-family: 'SF Pro Display', -apple-system, sans-serif;
        color: #1D1D1F;
    }
    .block-container { padding-top: 4rem; padding-bottom: 5rem; }
    
    .apple-card {
        background: #FFFFFF;
        border-radius: 20px;
        padding: 22px;
        margin-bottom: 18px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.04);
        border: 1px solid rgba(0,0,0,0.02);
    }
    
    .balance-header {
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: 24px;
        padding: 24px;
        position: sticky;
        top: 10px;
        z-index: 1000;
        border: 1px solid rgba(0,0,0,0.05);
        text-align: center;
        margin-bottom: 30px;
    }
    
    .text-secondary { color: #86868B; font-size: 0.85rem; }
    .price-up { color: #34C759; font-weight: 600; }
    .price-down { color: #FF3B30; font-weight: 600; }
    
    .stButton>button {
        border-radius: 14px;
        border: none;
        background-color: #007AFF;
        color: white;
        font-weight: 600;
        padding: 10px 20px;
    }
    
    header {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 数据库自愈引擎
# ==========================================
DATA_FILE = "trading_v5_final.json" # 统一新文件名

def load_db():
    if not os.path.exists(DATA_FILE):
        return {"users": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            return json.loads(content) if content else {"users": {}}
    except:
        return {"users": {}}

def save_db(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def sync_data():
    if st.session_state.get('logged_in'):
        db = load_db()
        u = st.session_state.username
        if u in db["users"]:
            db["users"][u]["balance"] = st.session_state.balance
            db["users"][u]["positions"] = st.session_state.positions
            save_db(db)

# ==========================================
# 2. 账号系统 (逻辑增强版)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

db = load_db()

# 自动登录拦截
url_token = st.query_params.get("token")
if url_token and not st.session_state.logged_in:
    for user, info in db["users"].items():
        if info.get("session_token") == url_token:
            st.session_state.update({
                "logged_in": True,
                "username": user,
                "balance": info["balance"],
                "positions": info["positions"],
                "chat_history": []
            })
            break

# 登录/注册界面
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align:center;'>Crypto Terminal</h2>", unsafe_allow_html=True)
    t_in, t_up = st.tabs(["登录", "注册"])
    
    with t_in:
        with st.form("login"):
            u = st.text_input("用户名")
            p = st.text_input("密码", type="password")
            if st.form_submit_button("进入终端", use_container_width=True):
                hp = hashlib.sha256(p.encode()).hexdigest()
                if u in db["users"] and db["users"][u]["password"] == hp:
                    tk = str(uuid.uuid4())
                    db["users"][u]["session_token"] = tk
                    save_db(db)
                    st.query_params["token"] = tk
                    st.session_state.update({
                        "logged_in": True,
                        "username": u,
                        "balance": db["users"][u]["balance"],
                        "positions": db["users"][u]["positions"],
                        "chat_history": []
                    })
                    st.rerun()
                else:
                    st.error("用户名或密码不对，请检查。")
    
    with t_up:
        with st.form("reg"):
            nu = st.text_input("新用户名")
            np = st.text_input("设置密码", type="password")
            if st.form_submit_button("注册新账号", use_container_width=True):
                if nu and np:
                    if nu in db["users"]:
                        st.error("此用户名已被占用")
                    else:
                        db["users"][nu] = {
                            "password": hashlib.sha256(np.encode()).hexdigest(),
                            "balance": 5000000.0,
                            "positions": [],
                            "session_token": ""
                        }
                        save_db(db)
                        st.success("注册成功！现在请切换到登录页。")
                else:
                    st.warning("请填完信息。")
    st.stop()

# ==========================================
# 3. 实时价格引擎 (全市场)
# ==========================================
@st.cache_data(ttl=600)
def get_all_symbols():
    try:
        r = requests.get("https://data-api.binance.vision/api/v3/exchangeInfo", timeout=5)
        return [s['symbol'] for s in r.json()['symbols'] if s['symbol'].endswith('USDT') and s['status']=='TRADING']
    except:
        return ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

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
# 4. 主 UI 渲染
# ==========================================
st.markdown(f"**{st.session_state.username}** · 极简模拟终端")

# 顶部 AI
with st.expander("🤖 AI 投资助理"):
    u_ask = st.chat_input("问问 AI 关于行情或你的持仓...")
    if u_ask:
        st.session_state.chat_history.append({"role": "user", "content": u_ask})
        try:
            res = requests.post("https://text.pollinations.ai/", json={"messages": [{"role":"system","content":"你是一个专业的中文加密货币分析师"}] + st.session_state.chat_history}, timeout=10)
            st.session_state.chat_history.append({"role": "assistant", "content": res.text})
        except: st.error("AI 暂时离线")
    for m in st.session_state.chat_history[-2:]:
        with st.chat_message(m["role"]): st.markdown(m["content"])

# 苹果风格资产看板
total_margin = sum(p['占用保证金'] for p in st.session_state.positions)
st.markdown(f"""
<div class="balance-header">
    <div class="text-secondary">实时总资产估值 (USDT)</div>
    <div style="font-size: 2.4rem; font-weight: 600; color: #1D1D1F; letter-spacing: -1.2px;">
        {st.session_state.balance + total_margin:,.2f}
    </div>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs(["📊 行情", "📈 交易", "💼 资产"])

with tabs[0]:
    st.components.v1.html("""
    <style>body { background: transparent; color: #1D1D1F; font-family: -apple-system; } .row { display: flex; justify-content: space-between; padding: 15px 5px; border-bottom: 1px solid #E5E5E7; }</style>
    <div id="m-list"></div>
    <script>
        const ws = new WebSocket('wss://data-stream.binance.vision:9443/ws/!ticker@arr');
        const ts = ['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','DOGEUSDT'];
        let rows = {};
        ts.forEach(t => {
            let d = document.createElement('div'); d.className = 'row';
            d.innerHTML = `<b>${t}</b><span id="p-${t}">-</span><span id="c-${t}">-</span>`;
            document.getElementById('m-list').appendChild(d);
            rows[t] = {p: document.getElementById(`p-${t}`), c: document.getElementById(`c-${t}`)};
        });
        ws.onmessage = (e) => {
            JSON.parse(e.data).forEach(i => { if(rows[i.s]) {
                rows[i.s].p.innerText = '$' + parseFloat(i.c).toFixed(2);
                rows[i.s].c.innerText = parseFloat(i.P).toFixed(2) + '%';
                rows[i.s].c.style.color = i.P >= 0 ? '#34C759' : '#FF3B30';
            }});
        };
    </script>
    """, height=350)

# --- 交易页 (独立双金额滑块) ---
with tabs[1]:
    target_coin = st.selectbox("搜索所有币种", all_coins, index=all_coins.index("BTCUSDT"))
    st.components.v1.html(f"""
        <div id="tv_chart" style="height:300px; border-radius:18px; overflow:hidden; border:1px solid #E5E5E7;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>
            new TradingView.widget({{"autosize":true,"symbol":"BINANCE:{target_coin}","interval":"1","theme":"light","style":"1","hide_top_toolbar":true,"container_id":"tv_chart"}});
        </script>
    """, height=300)
    
    st.markdown(f"**可用现金余额: {st.session_state.balance:,.2f} USDT**")
    
    # 滑块 1: 选择本金
    st.write("1. 拖动选择投入本金金额 (USDT)")
    actual_margin = st.slider("保证金金额", 0.0, float(st.session_state.balance), float(st.session_state.balance * 0.1), step=10.0)
    
    # 滑块 2: 选择杠杆
    st.write("2. 拖动选择杠杆倍数")
    leverage = st.slider("杠杆 (Leverage)", 1, 1000, 100)
    
    notional = actual_margin * leverage
    
    st.markdown(f"""
    <div style="background:#F2F2F7; padding:15px; border-radius:14px; margin: 15px 0;">
        <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
            <span style="color:#8E8E93;">实际本金投入:</span>
            <span style="font-weight:600;">{actual_margin:,.2f} U</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
            <span style="color:#8E8E93;">开仓总额 (名义价值):</span>
            <span style="font-weight:600; color:#007AFF;">{notional:,.2f} U</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    cb1, cb2 = st.columns(2)
    with cb1:
        if st.button("做多 (Long)", use_container_width=True, type="primary"):
            p = get_price(target_coin)
            if p > 0 and st.session_state.balance >= actual_margin:
                st.session_state.balance -= actual_margin
                st.session_state.positions.append({"交易对":target_coin,"方向":"多","开仓价":p,"杠杆":leverage,"名义价值":notional,"占用保证金":actual_margin})
                sync_data(); st.rerun()
    with cb2:
        if st.button("做空 (Short)", use_container_width=True):
            p = get_price(target_coin)
            if p > 0 and st.session_state.balance >= actual_margin:
                st.session_state.balance -= actual_margin
                st.session_state.positions.append({"交易对":target_coin,"方向":"空","开仓价":p,"杠杆":leverage,"名义价值":notional,"占用保证金":actual_margin})
                sync_data(); st.rerun()

# --- 持仓页 (独立滑块加减仓) ---
with tabs[2]:
    st.button("重置账户 (5,000,000 U)", on_click=lambda: (st.session_state.update({"balance":5000000.0,"positions":[]}), sync_data()), use_container_width=True)
    
    if not st.session_state.positions:
        st.info("暂无活跃持仓")
    else:
        try:
            r_p = requests.get("https://data-api.binance.vision/api/v3/ticker/price", timeout=2).json()
            p_map = {x['symbol']: float(x['price']) for x in r_p}
        except: p_map = {}

        for i, pos in enumerate(st.session_state.positions):
            now_p = p_map.get(pos['交易对'], pos['开仓价'])
            if pos['方向'] == "多": pnl = (now_p - pos['开仓价']) / pos['开仓价'] * pos['名义价值']
            else: pnl = (pos['开仓价'] - now_p) / pos['开仓价'] * pos['名义价值']
            
            with st.container():
                st.markdown(f"""
                <div class="apple-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span style="font-weight:600;">{pos['交易对']}</span>
                            <span class="text-secondary"> · {pos['方向']} · {pos['杠杆']}x</span>
                        </div>
                        <span class="{'price-up' if pnl>=0 else 'price-down'}" style="font-size:1.1rem;">{pnl:+.2f} U</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                m1, m2 = st.columns(2)
                with m1:
                    if st.button("全平结算", key=f"f_{i}", use_container_width=True):
                        st.session_state.balance += (pos['占用保证金'] + pnl)
                        st.session_state.positions.pop(i); sync_data(); st.rerun()
                with m2:
                    with st.popover("加/减仓", use_container_width=True):
                        st.write("选择调整的本金金额 (USDT)")
                        adj_val = st.slider("金额", 0.0, float(st.session_state.balance if st.session_state.balance > 0 else 1000), 10.0, key=f"adj_s_{i}")
                        
                        st.write(f"对应总价值: {adj_val * pos['杠杆']:,.2f}")
                        if st.button("补仓 (Add)", key=f"ad_{i}", use_container_width=True):
                            if st.session_state.balance >= adj_val:
                                st.session_state.balance -= adj_val
                                pos['名义价值'] += (adj_val * pos['杠杆'])
                                pos['占用保证金'] += adj_val
                                sync_data(); st.rerun()
                        if st.button("减仓 (Reduce)", key=f"re_{i}", use_container_width=True):
                            ratio = min(adj_val / pos['占用保证金'], 1.0) if pos['占用保证金']>0 else 0
                            st.session_state.balance += (pos['占用保证金'] * ratio + pnl * ratio)
                            pos['名义价值'] *= (1-ratio); pos['占用保证金'] *= (1-ratio)
                            if pos['名义价值'] < 1: st.session_state.positions.pop(i)
                            sync_data(); st.rerun()
