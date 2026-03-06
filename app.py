import streamlit as st
import pandas as pd
import requests
import time
import json
import os
import hashlib
import uuid

# ==========================================
# 0. UI 配置与样式
# ==========================================
st.set_page_config(page_title="Crypto 模拟终端 PRO", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .block-container { padding-top: 3.5rem; padding-bottom: 5rem; }
    .title-text { font-size: 1.6rem; font-weight: bold; color: #fff; }
    .balance-card { background: linear-gradient(135deg, #1e222d 0%, #161a25 100%); padding: 15px; border-radius: 12px; border: 1px solid #2b3139; margin-bottom: 15px; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 40px; border-radius: 4px; padding: 0px 16px; }
    div[data-testid="stExpander"] { border: 1px solid #2b3139; background: #0e1117; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 数据库与同步
# ==========================================
DATA_FILE = "trading_data.json"

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
# 2. 账号安全系统
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
db = load_db()

# 自动登录
tok = st.query_params.get("token")
if tok and not st.session_state.logged_in:
    for user, info in db["users"].items():
        if info.get("session_token") == tok:
            st.session_state.update({"logged_in":True,"username":user,"balance":info["balance"],"positions":info["positions"]})
            break

if not st.session_state.logged_in:
    st.markdown('<div class="title-text">⚡ Crypto 模拟引擎</div>', unsafe_allow_html=True)
    t_l, t_r = st.tabs(["🔑 登录", "📝 注册"])
    with t_l:
        with st.form("login"):
            u = st.text_input("用户名")
            p = st.text_input("密码", type="password")
            if st.form_submit_button("登 录", use_container_width=True):
                hp = hashlib.sha256(p.encode()).hexdigest()
                if u in db["users"] and db["users"][u]["password"] == hp:
                    tk = str(uuid.uuid4())
                    db["users"][u]["session_token"] = tk
                    save_db(db); st.query_params["token"] = tk
                    st.session_state.update({"logged_in":True,"username":u,"balance":db[u]["balance"],"positions":db[u]["positions"]})
                    st.rerun()
                else: st.error("账号或密码不对")
    with t_r:
        with st.form("reg"):
            nu = st.text_input("新用户名")
            np = st.text_input("新密码", type="password")
            if st.form_submit_button("注册账号", use_container_width=True):
                if nu and np and nu not in db["users"]:
                    db["users"][nu] = {"password":hashlib.sha256(np.encode()).hexdigest(),"balance":5000000.0,"positions":[],"session_token":""}
                    save_db(db); st.success("成功！请登录")
    st.stop()

# ==========================================
# 3. 价格与 API 引擎
# ==========================================
def get_price(sym):
    nodes = ['https://api.mexc.com', 'https://data-api.binance.vision']
    for n in nodes:
        try:
            r = requests.get(f"{n}/api/v3/ticker/price?symbol={sym}", timeout=3)
            return float(r.json()['price'])
        except: continue
    return 0.0

@st.cache_data(ttl=600)
def get_all_symbols():
    try:
        r = requests.get("https://api.mexc.com/api/v3/exchangeInfo", timeout=5)
        return [s['symbol'] for s in r.json()['symbols'] if s['symbol'].endswith('USDT')]
    except: return ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

all_coins = get_all_symbols()

# ==========================================
# 4. 核心逻辑：加仓/减仓计算
# ==========================================
def handle_add_position(idx, add_notional, current_price):
    pos = st.session_state.positions[idx]
    add_margin = add_notional / pos['杠杆']
    
    if st.session_state.balance < add_margin:
        st.error("余额不足，无法加仓！")
        return
    
    # 计算新均价: (旧价值 * 旧均价 + 新价值 * 新现价) / 总价值
    new_notional = pos['名义价值'] + add_notional
    new_avg_price = (pos['名义价值'] * pos['开仓价'] + add_notional * current_price) / new_notional
    
    st.session_state.balance -= add_margin
    pos['名义价值'] = new_notional
    pos['开仓价'] = new_avg_price
    pos['占用保证金'] += add_margin
    sync_data(); st.toast("补仓成功！均价已摊平"); time.sleep(0.5); st.rerun()

def handle_reduce_position(idx, reduce_notional, current_price):
    pos = st.session_state.positions[idx]
    if reduce_notional >= pos['名义价值']:
        # 如果减仓金额大于等于当前持仓，执行全平
        ratio = 1.0
        is_full_close = True
    else:
        ratio = reduce_notional / pos['名义价值']
        is_full_close = False

    # 计算减持部分的盈亏
    if pos["方向"] == "做多 🟢":
        pnl = (current_price - pos["开仓价"]) / pos["开仓价"] * (pos["名义价值"] * ratio)
    else:
        pnl = (pos["开仓价"] - current_price) / pos["开仓价"] * (pos["名义价值"] * ratio)
    
    returned_margin = pos['占用保证金'] * ratio
    st.session_state.balance += (returned_margin + pnl)
    
    if is_full_close:
        st.session_state.positions.pop(idx)
    else:
        pos['名义价值'] -= reduce_notional
        pos['占用保证金'] -= returned_margin
    
    sync_data(); st.toast(f"减仓成功！结算盈亏: {pnl:.2f} U"); time.sleep(0.5); st.rerun()

# ==========================================
# 5. 主界面布局
# ==========================================
c_t, c_ai, c_out = st.columns([5, 2, 2])
with c_t: st.markdown('<div class="title-text">⚡ PRO 模拟终端</div>', unsafe_allow_html=True)
with c_out: 
    if st.button("🚪 退出"): st.query_params.clear(); st.session_state.clear(); st.rerun()

# 资产看板
tab1, tab2, tab3 = st.tabs(["📊 实时行情", "📈 极速交易", "💼 仓位管理"])

# --- Tab 1: 毫秒行情 ---
with tab1:
    st.components.v1.html("""
    <script>
        const ws = new WebSocket('wss://data-stream.binance.vision:9443/ws/!ticker@arr');
        const coins = ['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','DOGEUSDT','PEPEUSDT','ORDIUSDT'];
        ws.onmessage = (e) => {
            JSON.parse(e.data).forEach(i => {
                if(coins.includes(i.s)) {
                    const el = document.getElementById(i.s);
                    if(el) el.innerHTML = `<span style="color:#848e9c">${i.s.replace('USDT','')}</span> <span style="color:${i.P>=0?'#0ecb81':'#f6465d'}">$${parseFloat(i.c).toFixed(2)} (${parseFloat(i.P).toFixed(2)}%)</span>`;
                }
            });
        };
    </script>
    <div id="BTCUSDT" style="padding:10px; border-bottom:1px solid #2b3139; font-family:sans-serif;">加载中...</div>
    <div id="ETHUSDT" style="padding:10px; border-bottom:1px solid #2b3139; font-family:sans-serif;">加载中...</div>
    <div id="SOLUSDT" style="padding:10px; border-bottom:1px solid #2b3139; font-family:sans-serif;">加载中...</div>
    <div id="BNBUSDT" style="padding:10px; border-bottom:1px solid #2b3139; font-family:sans-serif;">加载中...</div>
    <div id="PEPEUSDT" style="padding:10px; border-bottom:1px solid #2b3139; font-family:sans-serif;">加载中...</div>
    """, height=350)

# --- Tab 2: 交易下单 ---
with tab2:
    target = st.selectbox("搜索交易对", all_coins, index=all_coins.index("BTCUSDT"))
    st.components.v1.html(f"""
        <div id="tv" style="height:300px;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize":true,"symbol":"BINANCE:{target}","interval":"1","theme":"dark","style":"1","hide_top_toolbar":true,"container_id":"tv"}});</script>
    """, height=300)
    
    st.markdown(f"💰 可用余额: **{st.session_state.balance:,.2f} USDT**")
    
    # 比例输入逻辑
    col_per1, col_per2, col_per3, col_per4 = st.columns(4)
    amount_input = st.number_input("下单金额 (名义价值 USDT)", min_value=1.0, value=10000.0, key="new_order_amt")
    
    # 比例按钮
    with col_per1: 
        if st.button("10%", key="p1"): st.session_state.new_order_amt = st.session_state.balance * 0.1 * 100 # 假设默认100倍
    with col_per2:
        if st.button("50%", key="p2"): st.session_state.new_order_amt = st.session_state.balance * 0.5 * 100
    with col_per3:
        if st.button("100%", key="p3"): st.session_state.new_order_amt = st.session_state.balance * 1.0 * 100

    lev = st.slider("选择杠杆", 1, 1000, 100)
    m_needed = amount_input / lev
    st.caption(f"预计占用保证金: {m_needed:.2f} U")
    
    cb1, cb2 = st.columns(2)
    with cb1:
        if st.button("🟢 做多 (Buy/Long)", use_container_width=True):
            p = get_price(target)
            if p > 0 and st.session_state.balance >= m_needed:
                st.session_state.balance -= m_needed
                st.session_state.positions.append({"交易对":target,"方向":"做多 🟢","开仓价":p,"杠杆":lev,"名义价值":amount_input,"占用保证金":m_needed})
                sync_data(); st.rerun()
    with cb2:
        if st.button("🔴 做空 (Sell/Short)", use_container_width=True):
            p = get_price(target)
            if p > 0 and st.session_state.balance >= m_needed:
                st.session_state.balance -= m_needed
                st.session_state.positions.append({"交易对":target,"方向":"做空 🔴","开仓价":p,"杠杆":lev,"名义价值":amount_input,"占用保证金":m_needed})
                sync_data(); st.rerun()

# --- Tab 3: 持仓管理 ---
with tab3:
    if st.button("🔄 重置 500 万 U 体验金", use_container_width=True):
        st.session_state.balance = 5000000.0; st.session_state.positions = []; sync_data(); st.rerun()

    # 计算总资产
    cur_prices = {}
    try:
        res = requests.get("https://data-api.binance.vision/api/v3/ticker/price", timeout=2).json()
        for i in res: cur_prices[i['symbol']] = float(i['price'])
    except: pass

    total_pnl = 0
    for p in st.session_state.positions:
        now_p = cur_prices.get(p["交易对"], p["开仓价"])
        p["now_p"] = now_p
        if p["方向"] == "做多 🟢": p["pnl"] = (now_p - p["开仓价"]) / p["开仓价"] * p["名义价值"]
        else: p["pnl"] = (p["开仓价"] - now_p) / p["开仓价"] * p["名义价值"]
        total_pnl += p["pnl"]

    st.markdown(f"""
        <div class="balance-card">
            <div style="color:#848e9c; font-size:12px;">总权益 (USDT)</div>
            <div style="font-size:32px; font-weight:bold; color:{'#0ecb81' if total_pnl>=0 else '#f6465d'};">
                {st.session_state.balance + sum(x['占用保证金'] for x in st.session_state.positions) + total_pnl:,.2f}
            </div>
            <div style="font-size:12px; color:#848e9c;">可用余额: {st.session_state.balance:,.2f}</div>
        </div>
    """, unsafe_allow_html=True)

    if not st.session_state.positions:
        st.info("📦 暂无持仓")
    else:
        for idx, pos in enumerate(st.session_state.positions):
            with st.expander(f"{pos['交易对']} | {pos['方向']} | 盈亏: {pos['pnl']:.2f}U", expanded=True):
                st.write(f"均价: {pos['开仓价']:.4f} | 现价: {pos['now_p']:.4f}")
                st.write(f"保证金: {pos['占用保证金']:.2f} | 杠杆: {pos['杠杆']}x")
                
                # 持仓管理子页签
                m_tab1, m_tab2 = st.tabs(["➕ 加仓/补仓", "➖ 减仓/平仓"])
                
                with m_tab1:
                    st.caption(f"可用余额: {st.session_state.balance:,.2f} U")
                    add_val = st.number_input("加仓名义价值", min_value=0.0, key=f"add_{idx}")
                    # 比例按钮 (按余额比例)
                    c_a1, c_a2, c_a3 = st.columns(3)
                    if c_a1.button("余额 10%", key=f"ab1_{idx}"): add_val = st.session_state.balance * 0.1 * pos['杠杆']
                    if c_a2.button("余额 50%", key=f"ab2_{idx}"): add_val = st.session_state.balance * 0.5 * pos['杠杆']
                    if c_a3.button("余额 100%", key=f"ab3_{idx}"): add_val = st.session_state.balance * 1.0 * pos['杠杆']
                    
                    if st.button("确认加仓", key=f"cfm_add_{idx}", use_container_width=True):
                        handle_add_position(idx, add_val, pos['now_p'])
                
                with m_tab2:
                    st.caption(f"当前总价值: {pos['名义价值']:.2f} U")
                    red_val = st.number_input("减仓名义价值", min_value=0.0, key=f"red_{idx}")
                    # 比例按钮 (按持仓比例)
                    c_r1, c_r2, c_r3, c_r4 = st.columns(4)
                    if c_r1.button("25%", key=f"rb1_{idx}"): red_val = pos['名义价值'] * 0.25
                    if c_r2.button("50%", key=f"rb2_{idx}"): red_val = pos['名义价值'] * 0.5
                    if c_r3.button("75%", key=f"rb3_{idx}"): red_val = pos['名义价值'] * 0.75
                    if c_r4.button("100%", key=f"rb4_{idx}"): red_val = pos['名义价值'] * 1.0
                    
                    if st.button("确认减仓/平仓", key=f"cfm_red_{idx}", use_container_width=True, type="primary"):
                        handle_reduce_position(idx, red_val, pos['now_p'])
