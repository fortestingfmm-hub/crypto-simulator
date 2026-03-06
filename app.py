import streamlit as st
import pandas as pd
import requests
import time
import json
import os
import hashlib
import uuid

# ==========================================
# 0. UI 配置 - Apple 极简白 (Light Mode)
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
    
    /* 苹果风格卡片 */
    .apple-card {
        background: #FFFFFF;
        border-radius: 20px;
        padding: 22px;
        margin-bottom: 18px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.04);
        border: 1px solid rgba(0,0,0,0.02);
    }
    
    /* 顶部悬浮余额栏 (毛玻璃) */
    .balance-header {
        background: rgba(255, 255, 255, 0.85);
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
        box-shadow: 0 10px 40px rgba(0,0,0,0.03);
    }
    
    .text-secondary { color: #86868B; font-size: 0.85rem; }
    .price-up { color: #34C759; font-weight: 600; }
    .price-down { color: #FF3B30; font-weight: 600; }
    
    /* 苹果蓝按钮 */
    .stButton>button {
        border-radius: 12px;
        border: none;
        background-color: #007AFF;
        color: white;
        font-weight: 600;
        padding: 12px 24px;
        transition: all 0.2s ease;
    }
    .stButton>button:active { transform: scale(0.96); }
    
    header {visibility: hidden;} footer {visibility: hidden;}
    
    /* 隐藏表格索引 */
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 数据库引擎
# ==========================================
DATA_FILE = "trading_v6_full.json"

def load_db():
    if not os.path.exists(DATA_FILE): return {"users": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            c = f.read()
            return json.loads(c) if c else {"users": {}}
    except: return {"users": {}}

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
# 2. 账号安全系统
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
db = load_db()

tok = st.query_params.get("token")
if tok and not st.session_state.logged_in:
    for u, info in db["users"].items():
        if info.get("session_token") == tok:
            st.session_state.update({"logged_in":True,"username":u,"balance":info["balance"],"positions":info["positions"],"chat_history":[]})
            break

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align:center; color:#1D1D1F;'>Crypto Terminal</h2>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["登录账户", "创建新账户"])
    with t1:
        with st.form("l"):
            u = st.text_input("用户名")
            p = st.text_input("密码", type="password")
            if st.form_submit_button("安全登录", use_container_width=True):
                hp = hashlib.sha256(p.encode()).hexdigest()
                if u in db["users"] and db["users"][u]["password"] == hp:
                    tk = str(uuid.uuid4())
                    db["users"][u]["session_token"] = tk
                    save_db(db); st.query_params["token"] = tk
                    st.session_state.update({"logged_in":True,"username":u,"balance":db["users"][u]["balance"],"positions":db["users"][u]["positions"],"chat_history":[]})
                    st.rerun()
                else: st.error("登录失败")
    with t2:
        with st.form("r"):
            nu = st.text_input("新用户名")
            np = st.text_input("设置密码", type="password")
            if st.form_submit_button("注册获取 500万 U", use_container_width=True):
                if nu and np and nu not in db["users"]:
                    db["users"][nu] = {"password":hashlib.sha256(np.encode()).hexdigest(),"balance":5000000.0,"positions":[],"session_token":""}
                    save_db(db); st.success("注册成功！")
    st.stop()

# ==========================================
# 3. 实时价格与 AI
# ==========================================
@st.cache_data(ttl=600)
def get_all_symbols():
    try:
        r = requests.get("https://data-api.binance.vision/api/v3/exchangeInfo", timeout=5)
        return [s['symbol'] for s in r.json()['symbols'] if s['symbol'].endswith('USDT')]
    except: return ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

def get_price(sym):
    try:
        r = requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbol={sym}", timeout=3)
        return float(r.json()['price'])
    except: return 0.0

all_coins = get_all_symbols()

# ==========================================
# 4. 主 UI 渲染
# ==========================================
with st.expander("🤖 AI 投资助理 (中文)"):
    u_q = st.chat_input("询问市场趋势...")
    if u_q:
        st.session_state.chat_history.append({"role": "user", "content": u_q})
        try:
            res = requests.post("https://text.pollinations.ai/", json={"messages": [{"role":"system","content":"Crypto Pro"}] + st.session_state.chat_history}, timeout=10)
            st.session_state.chat_history.append({"role": "assistant", "content": res.text})
        except: st.error("AI 暂时休息")
    for m in st.session_state.chat_history[-2:]:
        with st.chat_message(m["role"]): st.markdown(m["content"])

# 苹果风格资产看板
total_margin = sum(p['占用保证金'] for p in st.session_state.positions)
st.markdown(f"""
<div class="balance-header">
    <div class="text-secondary">实时总资产 (USDT)</div>
    <div style="font-size: 2.2rem; font-weight: 600; color: #1D1D1F; letter-spacing: -1.2px;">
        {st.session_state.balance + total_margin:,.2f}
    </div>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs(["📊 行情", "📈 交易", "💼 资产"])

# --- Tab 1: 全市场毫秒行情瀑布流 ---
with tabs[0]:
    st.components.v1.html("""
    <style>
        body { background: transparent; color: #1D1D1F; font-family: -apple-system; margin:0; }
        .list-container { height: 450px; overflow-y: auto; padding-right: 5px; }
        .item { display: flex; justify-content: space-between; padding: 14px 8px; border-bottom: 1px solid #E5E5E7; align-items: center; }
        .sym { font-weight: 600; font-size: 15px; }
        .vol { font-size: 10px; color: #8E8E93; }
        .up { color: #34C759; } .down { color: #FF3B30; }
    </style>
    <div class="list-container" id="l"></div>
    <script>
        const b = document.getElementById('l');
        const ws = new WebSocket('wss://data-stream.binance.vision:9443/ws/!ticker@arr');
        let cache = {};
        
        ws.onmessage = (e) => {
            const data = JSON.parse(e.data).filter(i => i.s.endsWith('USDT'));
            // 按成交额排序取前 200 个，保证流畅度
            data.sort((x, y) => parseFloat(y.q) - parseFloat(x.q)).slice(0, 200).forEach(i => {
                if(!cache[i.s]) {
                    let d = document.createElement('div'); d.className = 'item'; d.id = 'row-'+i.s;
                    b.appendChild(d);
                    cache[i.s] = d;
                }
                const colorClass = parseFloat(i.P) >= 0 ? 'up' : 'down';
                cache[i.s].innerHTML = `
                    <div><div class="sym">${i.s.replace('USDT','')}</div><div class="vol">Vol: ${(parseFloat(i.q)/1000000).toFixed(1)}M</div></div>
                    <div style="text-align:right"><div style="font-weight:600">$${parseFloat(i.c).toFixed(i.s.includes('PEPE')?6:2)}</div><div class="${colorClass}">${parseFloat(i.P).toFixed(2)}%</div></div>
                `;
            });
        };
    </script>
    """, height=450)

# --- Tab 2: 极速交易 (独立双滑块 + 下单成功提示) ---
with tabs[1]:
    target_coin = st.selectbox("搜索币种", all_coins, index=all_coins.index("BTCUSDT"))
    st.components.v1.html(f"""
        <div id="tv" style="height:320px; border-radius:18px; overflow:hidden; border:1px solid #E5E5E7;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize":true,"symbol":"BINANCE:{target_coin}","interval":"1","theme":"light","style":"1","hide_top_toolbar":true,"container_id":"tv"}});</script>
    """, height=320)
    
    st.markdown(f"**可用现金: {st.session_state.balance:,.2f} USDT**")
    
    # 独立双滑块
    actual_margin = st.slider("1. 投入保证金金额 (USDT)", 0.0, float(st.session_state.balance), float(st.session_state.balance * 0.1), step=10.0)
    leverage = st.slider("2. 杠杆倍数 (Leverage)", 1, 1000, 100)
    
    notional = actual_margin * leverage
    st.markdown(f"<div style='background:#F2F2F7; padding:12px; border-radius:12px; margin-bottom:15px;'>开仓总额: <b style='color:#007AFF;'>{notional:,.2f} USDT</b></div>", unsafe_allow_html=True)
    
    cb1, cb2 = st.columns(2)
    with cb1:
        if st.button("做多 (Long) 🟢", use_container_width=True, type="primary"):
            p = get_price(target_coin)
            if p > 0 and st.session_state.balance >= actual_margin:
                st.session_state.balance -= actual_margin
                st.session_state.positions.append({"交易对":target_coin,"方向":"多","开仓价":p,"杠杆":leverage,"名义价值":notional,"占用保证金":actual_margin})
                sync_data()
                st.success(f"✅ 做多成功！成交价: {p}") # 成功小提示
                time.sleep(1); st.rerun()
    with cb2:
        if st.button("做空 (Short) 🔴", use_container_width=True):
            p = get_price(target_coin)
            if p > 0 and st.session_state.balance >= actual_margin:
                st.session_state.balance -= actual_margin
                st.session_state.positions.append({"交易对":target_coin,"方向":"空","开仓价":p,"杠杆":leverage,"名义价值":notional,"占用保证金":actual_margin})
                sync_data()
                st.success(f"✅ 做空成功！成交价: {p}") # 成功小提示
                time.sleep(1); st.rerun()

# --- Tab 3: 资产中心 ---
with tabs[2]:
    st.button("重置 5,000,000 U 账户", on_click=lambda: (st.session_state.update({"balance":5000000.0,"positions":[]}), sync_data()), use_container_width=True)
    
    if not st.session_state.positions:
        st.info("暂无活跃持仓")
    else:
        # 获取实时行情用于计算资产卡片
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
                        <div><b>{pos['交易对']} · {pos['方向']}</b><div class="text-secondary">{pos['杠杆']}x · 均价 {pos['开仓价']:.4f}</div></div>
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
                    with st.popover("调整", use_container_width=True):
                        adj_val = st.slider("调整本金金额 (USDT)", 0.0, float(st.session_state.balance if st.session_state.balance > 0 else 1000), 10.0, key=f"adj_s_{i}")
                        st.write(f"对应总价值: {adj_val * pos['杠杆']:,.2f}")
                        if st.button("补仓 (Add)", key=f"ad_{i}", use_container_width=True):
                            if st.session_state.balance >= adj_val:
                                st.session_state.balance -= adj_val
                                pos['名义价值'] += (adj_val * pos['杠杆'])
                                pos['占用保证金'] += adj_val
                                sync_data(); st.rerun()
                        if st.button("减仓 (Reduce)", key=f"re_{i}", use_container_width=True, type="primary"):
                            ratio = min(adj_val / pos['占用保证金'], 1.0) if pos['占用保证金']>0 else 0
                            st.session_state.balance += (pos['占用保证金'] * ratio + pnl * ratio)
                            pos['名义价值'] *= (1-ratio); pos['占用保证金'] *= (1-ratio)
                            if pos['名义价值'] < 1: st.session_state.positions.pop(i)
                            sync_data(); st.rerun()
