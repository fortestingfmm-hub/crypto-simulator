import streamlit as st
import pandas as pd
import requests
import time
import json
import os
import hashlib
import uuid
from urllib.parse import quote
from datetime import datetime

# ==========================================
# 0. UI 配置 - Apple 极简白 (Light Mode)
# ==========================================
st.set_page_config(page_title="Crypto Terminal Pro", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;600&display=swap');
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #F5F5F7;
        font-family: 'SF Pro Display', -apple-system, sans-serif;
    }
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }
    
    /* 苹果风格卡片 */
    .apple-card {
        background: #FFFFFF;
        border-radius: 20px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.03);
        border: 1px solid rgba(0,0,0,0.01);
    }
    
    /* 顶部悬浮看板 */
    .balance-header {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: 24px;
        padding: 20px;
        text-align: center;
        margin-bottom: 15px;
        border: 1px solid rgba(0,0,0,0.05);
    }
    
    /* 顶置 AI 助理专用样式 */
    .ai-box {
        background: #FFFFFF;
        border-radius: 18px;
        padding: 15px;
        margin-bottom: 20px;
        border-left: 5px solid #007AFF;
        box-shadow: 0 4px 12px rgba(0,0,0,0.02);
    }
    
    .price-up { color: #34C759; font-weight: 600; }
    .price-down { color: #FF3B30; font-weight: 600; }
    .text-secondary { color: #86868B; font-size: 0.85rem; }
    
    .stButton>button {
        border-radius: 12px;
        background-color: #007AFF;
        color: white;
        font-weight: 600;
        border: none;
        transition: 0.2s;
    }
    
    header {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 数据库引擎
# ==========================================
DATA_FILE = "trading_v15_pro.json"

def load_db():
    if not os.path.exists(DATA_FILE): return {"users": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
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
            db["users"][u]["history"] = st.session_state.get("history", [])
            save_db(db)

# ==========================================
# 2. 账号系统 (含多端同步 & 查重)
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'history' not in st.session_state: st.session_state.history = []
if 'chat_history' not in st.session_state: st.session_state.chat_history = []

db = load_db()
tok = st.query_params.get("token")

if tok and not st.session_state.logged_in:
    for user, info in db["users"].items():
        if info.get("session_token") == tok:
            st.session_state.update({
                "logged_in": True, "username": user,
                "balance": info.get("balance", 5000000.0),
                "positions": info.get("positions", []),
                "history": info.get("history", []),
                "chat_history": []
            })
            break

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align:center;'>Crypto Terminal Pro</h2>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["安全登录", "创建新账户"])
    
    with t1:
        with st.form("login_form"):
            u_raw = st.text_input("用户名")
            p_raw = st.text_input("密码", type="password")
            if st.form_submit_button("立即进入", use_container_width=True):
                u, p = u_raw.strip(), p_raw.strip()
                hp = hashlib.sha256(p.encode()).hexdigest()
                db = load_db()
                if u in db["users"] and db["users"][u]["password"] == hp:
                    tk = db["users"][u].get("session_token") or str(uuid.uuid4())
                    db["users"][u]["session_token"] = tk
                    save_db(db); st.query_params["token"] = tk
                    st.session_state.update({
                        "logged_in": True, "username": u,
                        "balance": db["users"][u].get("balance", 5000000.0),
                        "positions": db["users"][u].get("positions", []),
                        "history": db["users"][u].get("history", []),
                        "chat_history": []
                    })
                    st.rerun()
                else: st.error("用户名或密码不匹配")
                
    with t2:
        with st.form("reg_form"):
            nu_raw = st.text_input("设置新用户名")
            np_raw = st.text_input("设置新密码", type="password")
            if st.form_submit_button("注册获取 500万 U 开户金", use_container_width=True):
                nu, np = nu_raw.strip(), np_raw.strip()
                db = load_db()
                if not nu or not np:
                    st.warning("请完整填写信息")
                elif nu in db["users"]:
                    st.error(f"❌ 注册失败：'{nu}' 已存在，请换一个名称")
                else:
                    db["users"][nu] = {
                        "password": hashlib.sha256(np.encode()).hexdigest(),
                        "balance": 5000000.0, "positions": [], "history": [], "session_token": ""
                    }
                    save_db(db)
                    st.success("🎉 开户成功！请切换到登录页。")
    st.stop()

# ==========================================
# 3. 价格引擎
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
# 4. 顶部账户与 AI 管理区
# ==========================================
c_user, c_sys = st.columns([7, 2])
with c_user: st.markdown(f"🍎 **{st.session_state.username}**")
with c_sys:
    with st.popover("⚙️"):
        if st.button("🔄 重置资金"):
            st.session_state.update({"balance":5000000.0,"positions":[],"history":[]}); sync_data(); st.rerun()
        if st.button("🚪 退出登录"):
            st.query_params.clear(); st.session_state.clear(); st.rerun()

tm = sum(p['占用保证金'] for p in st.session_state.positions)
st.markdown(f"""
<div class="balance-header">
    <div class="text-secondary">实时总资产净值 (USDT)</div>
    <div style="font-size: 2.2rem; font-weight: 600; color: #1D1D1F;">{st.session_state.balance + tm:,.2f}</div>
</div>
""", unsafe_allow_html=True)

# 🌟 修复后的固定顶置 AI 助理
with st.container():
    st.markdown('<div class="ai-box">🤖 <b>AI 投顾助理</b>', unsafe_allow_html=True)
    # 使用 st.text_input + 按钮代替 chat_input，确保它固定在顶部
    ai_col1, ai_col2 = st.columns([4, 1])
    with ai_col1:
        u_msg = st.text_input("搜索币种行情或询问 AI 建议", key="ai_input_box", placeholder="例如：BTC 现在的趋势如何？", label_visibility="collapsed")
    with ai_col2:
        send_btn = st.button("发送", use_container_width=True)
    
    if send_btn and u_msg:
        try:
            ctx = quote(f"你是中文专家。用户余额:{st.session_state.balance}U。问:{u_msg}")
            res = requests.get(f"https://text.pollinations.ai/{ctx}?model=openai", timeout=12)
            if res.status_code == 200:
                st.session_state.chat_history.append({"role": "user", "content": u_msg})
                st.session_state.chat_history.append({"role": "assistant", "content": res.text})
        except: st.error("AI 连接超时")
    
    # 仅显示最近的对话
    if st.session_state.chat_history:
        for m in st.session_state.chat_history[-2:]:
            with st.chat_message(m["role"]): st.markdown(m["content"])
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 5. 主功能标签页
# ==========================================
tabs = st.tabs(["📊 行情", "📈 交易", "💼 持仓", "📜 历史"])

with tabs[0]:
    st.components.v1.html("""
    <style>body { background: transparent; font-family: -apple-system; margin:0; } .list { height: 420px; overflow-y: auto; } .item { display: flex; justify-content: space-between; padding: 15px 8px; border-bottom: 1px solid #E5E5E7; }</style>
    <div class="list" id="l"></div>
    <script>
        const b = document.getElementById('l'), ws = new WebSocket('wss://data-stream.binance.vision:9443/ws/!ticker@arr');
        let c = {};
        ws.onmessage = (e) => {
            JSON.parse(e.data).filter(i => i.s.endswith('USDT')).sort((x, y) => parseFloat(y.q) - parseFloat(x.q)).slice(0, 100).forEach(i => {
                if(!c[i.s]) { let d = document.createElement('div'); d.className = 'item'; b.appendChild(d); c[i.s] = d; }
                const u = parseFloat(i.P) >= 0;
                c[i.s].innerHTML = `<b>${i.s}</b><div style="text-align:right"><b>$${parseFloat(i.c).toFixed(2)}</b><div style="color:${u?'#34C759':'#FF3B30'}">${u?'+':''}${parseFloat(i.P).toFixed(2)}%</div></div>`;
            });
        };
    </script>
    """, height=420)

with tabs[1]:
    target = st.selectbox("选择交易对", all_coins, index=all_coins.index("BTCUSDT"))
    st.components.v1.html(f"""
        <div id="tv" style="height:320px; border-radius:18px; overflow:hidden; border:1px solid #E5E5E7;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize":true,"symbol":"BINANCE:{target}","interval":"1","theme":"light","style":"1","hide_top_toolbar":true,"container_id":"tv"}});</script>
    """, height=320)
    
    st.markdown(f"**可用资金: {st.session_state.balance:,.2f} USDT**")
    # 🌟 独立双滑块
    actual_margin = st.slider("1. 投入本金金额 (USDT)", 0.0, float(st.session_state.balance), float(st.session_state.balance * 0.1), step=100.0)
    leverage = st.slider("2. 杠杆倍数 (Leverage)", 1, 1000, 100)
    notional = actual_margin * leverage
    st.markdown(f"<div style='background:#F2F2F7; padding:12px; border-radius:12px; margin-bottom:15px;'>成交估值: <b style='color:#007AFF;'>{notional:,.2f} U</b></div>", unsafe_allow_html=True)
    
    cb1, cb2 = st.columns(2)
    with cb1:
        if st.button("做多 (Long) 🟢", use_container_width=True, type="primary"):
            p = get_price(target)
            if p > 0 and st.session_state.balance >= actual_margin:
                st.session_state.balance -= actual_margin
                st.session_state.positions.append({"交易对":target,"方向":"多","开仓价":p,"杠杆":leverage,"名义价值":notional,"占用保证金":actual_margin})
                sync_data(); st.success(f"做多已成交: {p}"); time.sleep(0.5); st.rerun()
    with cb2:
        if st.button("做空 (Short) 🔴", use_container_width=True):
            p = get_price(target)
            if p > 0 and st.session_state.balance >= actual_margin:
                st.session_state.balance -= actual_margin
                st.session_state.positions.append({"交易对":target,"方向":"空","开仓价":p,"杠杆":leverage,"名义价值":notional,"占用保证金":actual_margin})
                sync_data(); st.success(f"做空已成交: {p}"); time.sleep(0.5); st.rerun()

with tabs[2]:
    if not st.session_state.positions:
        st.info("当前无持仓")
    else:
        try:
            r_p = requests.get("https://data-api.binance.vision/api/v3/ticker/price", timeout=2).json()
            p_map = {x['symbol']: float(x['price']) for x in r_p}
        except: p_map = {}
        for i, pos in enumerate(st.session_state.positions):
            now_p = p_map.get(pos['交易对'], pos['开仓价'])
            pnl = (now_p - pos['开仓价']) / pos['开仓价'] * pos['名义价值'] if pos['方向'] == "多" else (pos['开仓价'] - now_p) / pos['开仓价'] * pos['名义价值']
            with st.container():
                st.markdown(f"""<div class="apple-card"><div style="display:flex; justify-content:space-between;"><b>{pos['交易对']} · {pos['杠杆']}x</b><span class="{'price-up' if pnl>=0 else 'price-down'}">{pnl:+.2f} U</span></div></div>""", unsafe_allow_html=True)
                m1, m2 = st.columns(2)
                with m1:
                    if st.button("全平结算", key=f"cl_{i}", use_container_width=True):
                        st.session_state.history.insert(0, {"时间": datetime.now().strftime("%m-%d %H:%M"), "币种": pos['交易对'], "方向": pos['方向'], "盈亏": round(pnl, 2), "价格": now_p})
                        st.session_state.balance += (pos['占用保证金'] + pnl); st.session_state.positions.pop(i); sync_data(); st.rerun()
                with m2:
                    with st.popover("调仓", use_container_width=True):
                        adj_v = st.slider("金额", 0.0, float(st.session_state.balance if st.session_state.balance > 0 else 100), 100.0, key=f"as_{i}")
                        if st.button("补仓", key=f"ad_{i}", use_container_width=True):
                            if st.session_state.balance >= adj_v:
                                st.session_state.balance -= adj_v; pos['名义价值'] += (adj_v * pos['杠杆']); pos['占用保证金'] += adj_v; sync_data(); st.rerun()
                        if st.button("减仓", key=f"re_{i}", use_container_width=True, type="primary"):
                            ratio = min(adj_v / pos['占用保证金'], 1.0) if pos['占用保证金']>0 else 0
                            st.session_state.history.insert(0, {"时间": datetime.now().strftime("%m-%d %H:%M"), "币种": pos['交易对'], "方向": f"减-{pos['方向']}", "盈亏": round(pnl * ratio, 2), "价格": now_p})
                            st.session_state.balance += (pos['占用保证金'] * ratio + pnl * ratio); pos['名义价值'] *= (1-ratio); pos['占用保证金'] *= (1-ratio)
                            if pos['名义价值'] < 1: st.session_state.positions.pop(i)
                            sync_data(); st.rerun()

with tabs[3]:
    st.markdown("#### 📜 最近成交流水")
    if not st.session_state.history: st.caption("暂无记录")
    else:
        for h in st.session_state.history[:30]:
            st.markdown(f"""<div style="padding:15px; border-bottom:1px solid #EEE; display:flex; justify-content:space-between; align-items:center; background:white; border-radius:12px; margin-bottom:8px;"><div><b>{h['币种']} · {h['方向']}</b><div style="font-size:11px; color:#8E8E93;">{h['时间']} | {h['价格']}</div></div><div class="{'price-up' if h['盈亏']>=0 else 'price-down'}">{h['盈亏']:+.2f} U</div></div>""", unsafe_allow_html=True)
