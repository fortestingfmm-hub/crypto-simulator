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
# 0. UI 配置 - Apple 极简白 (Light Style)
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
        padding: 22px;
        margin-bottom: 15px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.04);
        border: 1px solid rgba(0,0,0,0.02);
    }
    
    .balance-header {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: 24px;
        padding: 24px;
        text-align: center;
        margin-bottom: 25px;
        border: 1px solid rgba(0,0,0,0.05);
        box-shadow: 0 4px 20px rgba(0,0,0,0.02);
    }
    
    .text-secondary { color: #86868B; font-size: 0.85rem; }
    .price-up { color: #34C759; font-weight: 600; }
    .price-down { color: #FF3B30; font-weight: 600; }
    
    .stButton>button { border-radius: 12px; background-color: #007AFF; color: white; font-weight: 600; border: none; }
    header {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 数据库引擎 (自愈机制)
# ==========================================
DATA_FILE = "trading_v11_final.json"

def load_db():
    if not os.path.exists(DATA_FILE): return {"users": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {"users": {}}
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
# 2. 账号系统 (强制初始化 history)
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'history' not in st.session_state: st.session_state.history = []

db = load_db()
tok = st.query_params.get("token")

if tok and not st.session_state.logged_in:
    for u, info in db["users"].items():
        if info.get("session_token") == tok:
            st.session_state.update({
                "logged_in": True, "username": u,
                "balance": info.get("balance", 5000000.0),
                "positions": info.get("positions", []),
                "history": info.get("history", []),
                "chat_history": []
            })
            break

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align:center;'>Crypto Terminal</h2>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["安全登录", "新开账户"])
    with t1:
        with st.form("l"):
            u = st.text_input("用户名")
            p = st.text_input("密码", type="password")
            if st.form_submit_button("登录", use_container_width=True):
                hp = hashlib.sha256(p.encode()).hexdigest()
                if u in db["users"] and db["users"][u]["password"] == hp:
                    tk = str(uuid.uuid4())
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
                else: st.error("登录失败")
    with t2:
        with st.form("r"):
            nu = st.text_input("新用户名")
            np = st.text_input("设置密码", type="password")
            if st.form_submit_button("注册并领取 500w USDT", use_container_width=True):
                if nu and np and nu not in db["users"]:
                    db["users"][nu] = {"password":hashlib.sha256(np.encode()).hexdigest(),"balance":5000000.0,"positions":[],"history":[],"session_token":""}
                    save_db(db); st.success("开户成功！请登录")
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
# 4. 【重置与系统】挪到顶部账户区
# ==========================================
c_user, c_sys = st.columns([7, 2])
with c_user: st.markdown(f"**{st.session_state.username}** · Terminal Pro")
with c_sys:
    with st.popover("⚙️ 管理"):
        if st.button("🔄 重置账户 (5M U)", use_container_width=True):
            st.session_state.update({"balance":5000000.0, "positions":[], "history":[]})
            sync_data(); st.rerun()
        if st.button("🚪 安全退出", use_container_width=True):
            st.query_params.clear(); st.session_state.clear(); st.rerun()

# ==========================================
# 5. 【AI 浮窗】增强注入 - 确保可见且可拖拽
# ==========================================
st.components.v1.html(f"""
<div id="ai-drag-container" style="position:fixed; top:150px; right:20px; width:300px; z-index:999999; pointer-events:auto;">
    <div id="ai-window" style="background:rgba(255,255,255,0.9); backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px); border-radius:20px; box-shadow:0 10px 40px rgba(0,0,0,0.15); border:1px solid rgba(0,0,0,0.1); overflow:hidden; display:flex; flex-direction:column; font-family:-apple-system, sans-serif;">
        <div id="ai-header" style="padding:15px; background:rgba(0,122,255,0.1); cursor:move; display:flex; justify-content:space-between; align-items:center; user-select:none;">
            <span style="font-weight:600; font-size:14px; color:#007AFF;">🤖 AI 交易助理 (按住此栏拖动)</span>
            <div style="width:8px; height:8px; background:#34C759; border-radius:50%;"></div>
        </div>
        <div id="ai-body" style="height:250px; padding:15px; overflow-y:auto; font-size:13px; color:#1D1D1F;">
            <div style="background:white; padding:10px; border-radius:12px; margin-bottom:12px; border:1px solid #F0F0F0;">
                你好！我是内置助理。当前余额: <b>{st.session_state.balance:,.0f} U</b>。有什么可以帮你的？
            </div>
            <div id="msgs"></div>
        </div>
        <div style="padding:12px; background:white; border-top:1px solid #F0F0F0;">
            <input type="text" id="ai-in" placeholder="问问市场趋势..." style="width:100%; border:1px solid #E5E5E7; border-radius:10px; padding:8px; outline:none; font-size:13px;">
        </div>
    </div>
</div>
<script>
    function makeDraggable(el) {{
        var pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
        const header = document.getElementById(el.id + "header");
        header.onmousedown = dragMouseDown;
        function dragMouseDown(e) {{
            e = e || window.event; e.preventDefault();
            pos3 = e.clientX; pos4 = e.clientY;
            document.onmouseup = closeDragElement;
            document.onmousemove = elementDrag;
        }}
        function elementDrag(e) {{
            e = e || window.event; e.preventDefault();
            pos1 = pos3 - e.clientX; pos2 = pos4 - e.clientY;
            pos3 = e.clientX; pos4 = e.clientY;
            const container = document.getElementById("ai-drag-container");
            container.style.top = (container.offsetTop - pos2) + "px";
            container.style.left = (container.offsetLeft - pos1) + "px";
        }}
        function closeDragElement() {{
            document.onmouseup = null; document.onmousemove = null;
        }}
    }}
    makeDraggable(document.getElementById("ai-window"));
    
    const input = document.getElementById('ai-in'), msgs = document.getElementById('msgs');
    input.addEventListener('keypress', function(e){{
        if(e.key === 'Enter' && input.value.trim() !== "") {{
            const val = input.value; input.value = "";
            msgs.innerHTML += `<div style="text-align:right; margin-bottom:10px;"><span style="background:#007AFF; color:white; padding:6px 12px; border-radius:12px; display:inline-block;">${{val}}</span></div>`;
            fetch(`https://text.pollinations.ai/你是中文加密专家。当前余额:{st.session_state.balance}。用户问:${{val}}?model=openai`)
                .then(r => r.text()).then(d => {{
                    msgs.innerHTML += `<div style="margin-bottom:10px;"><span style="background:white; padding:6px 12px; border-radius:12px; border:1px solid #EEE; display:inline-block;">${{d}}</span></div>`;
                    document.getElementById('ai-body').scrollTop = document.getElementById('ai-body').scrollHeight;
                }});
        }}
    }});
</script>
""", height=1)

# ==========================================
# 6. 资产看板与 Tab 分页
# ==========================================
tm = sum(p['占用保证金'] for p in st.session_state.positions)
st.markdown(f"""
<div class="balance-header">
    <div class="text-secondary">当前总权益 (USDT)</div>
    <div style="font-size: 2.2rem; font-weight: 600; color: #1D1D1F; letter-spacing: -1px;">
        {st.session_state.balance + tm:,.2f}
    </div>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs(["📊 实时行情", "📈 极速交易", "💼 仓位管理", "📜 历史记录"])

# --- Tab 1: 行情 ---
with tabs[0]:
    st.components.v1.html("""
    <style>body { background: transparent; font-family: -apple-system; margin:0; } .list { height: 420px; overflow-y: auto; } .item { display: flex; justify-content: space-between; padding: 16px 8px; border-bottom: 1px solid #E5E5E7; }</style>
    <div class="list" id="l"></div>
    <script>
        const b = document.getElementById('l'), ws = new WebSocket('wss://data-stream.binance.vision:9443/ws/!ticker@arr');
        let cache = {};
        ws.onmessage = (e) => {
            JSON.parse(e.data).filter(i => i.s.endswith('USDT')).sort((x, y) => parseFloat(y.q) - parseFloat(x.q)).slice(0, 80).forEach(i => {
                if(!cache[i.s]) { let d = document.createElement('div'); d.className = 'item'; b.appendChild(d); cache[i.s] = d; }
                const up = parseFloat(i.P) >= 0;
                cache[i.s].innerHTML = `<b>${i.s.replace('USDT','')}</b><div style="text-align:right"><b>$${parseFloat(i.c).toFixed(i.s.includes('PEPE')?6:2)}</b><div style="color:${up?'#34C759':'#FF3B30'}">${up?'+':''}${parseFloat(i.P).toFixed(2)}%</div></div>`;
            });
        };
    </script>
    """, height=420)

# --- Tab 2: 交易 (独立双金额滑块) ---
with tabs[1]:
    target = st.selectbox("搜索币种", all_coins, index=all_coins.index("BTCUSDT"))
    st.components.v1.html(f"""
        <div id="tv" style="height:320px; border-radius:18px; overflow:hidden; border:1px solid #E5E5E7;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize":true,"symbol":"BINANCE:{target}","interval":"1","theme":"light","style":"1","hide_top_toolbar":true,"container_id":"tv"}});</script>
    """, height=320)
    
    st.markdown(f"**可用余额: {st.session_state.balance:,.2f} USDT**")
    
    # 🌟 独立双滑块
    actual_margin = st.slider("1. 选择投入本金 (保证金金额)", 0.0, float(st.session_state.balance), float(st.session_state.balance * 0.1), step=100.0)
    leverage = st.slider("2. 选择杠杆倍数 (Leverage)", 1, 1000, 100)
    notional = actual_margin * leverage
    st.markdown(f"<div style='background:#F2F2F7; padding:15px; border-radius:14px; margin-bottom:15px;'>开仓总额: <b style='color:#007AFF;'>{notional:,.2f} U</b></div>", unsafe_allow_html=True)
    
    cb1, cb2 = st.columns(2)
    with cb1:
        if st.button("🟢 做多 (Long)", use_container_width=True, type="primary"):
            p = get_price(target)
            if p > 0 and st.session_state.balance >= actual_margin:
                st.session_state.balance -= actual_margin
                st.session_state.positions.append({"交易对":target,"方向":"多","开仓价":p,"杠杆":leverage,"名义价值":notional,"占用保证金":actual_margin})
                sync_data(); st.success(f"✅ 做多成功: {p}"); time.sleep(0.5); st.rerun()
    with cb2:
        if st.button("🔴 做空 (Short)", use_container_width=True):
            p = get_price(target)
            if p > 0 and st.session_state.balance >= actual_margin:
                st.session_state.balance -= actual_margin
                st.session_state.positions.append({"交易对":target,"方向":"空","开仓价":p,"杠杆":leverage,"名义价值":notional,"占用保证金":actual_margin})
                sync_data(); st.success(f"✅ 做空成功: {p}"); time.sleep(0.5); st.rerun()

# --- Tab 3: 持仓管理 ---
with tabs[2]:
    if not st.session_state.positions:
        st.info("当前暂无持仓")
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
                st.markdown(f"""<div class="apple-card"><div style="display:flex; justify-content:space-between;"><b>{pos['交易对']} · {pos['方向']} · {pos['杠杆']}x</b><span class="{'price-up' if pnl>=0 else 'price-down'}">{pnl:+.2f} U</span></div></div>""", unsafe_allow_html=True)
                m1, m2 = st.columns(2)
                with m1:
                    if st.button("全平结算", key=f"cl_{i}", use_container_width=True):
                        st.session_state.history.insert(0, {"时间": datetime.now().strftime("%m-%d %H:%M"), "币种": pos['交易对'], "方向": pos['方向'], "盈亏": round(pnl, 2), "价格": now_p})
                        st.session_state.balance += (pos['占用保证金'] + pnl)
                        st.session_state.positions.pop(i); sync_data(); st.rerun()
                with m2:
                    with st.popover("调整规模", use_container_width=True):
                        adj_v = st.slider("金额", 0.0, float(st.session_state.balance), 1000.0, key=f"as_{i}")
                        if st.button("加仓 (Add)", key=f"ad_{i}", use_container_width=True):
                            if st.session_state.balance >= adj_v:
                                st.session_state.balance -= adj_v
                                pos['名义价值'] += (adj_v * pos['杠杆']); pos['占用保证金'] += adj_v
                                sync_data(); st.rerun()
                        if st.button("减仓 (Reduce)", key=f"re_{i}", use_container_width=True, type="primary"):
                            ratio = min(adj_v / pos['占用保证金'], 1.0) if pos['占用保证金']>0 else 0
                            st.session_state.history.insert(0, {"时间": datetime.now().strftime("%m-%d %H:%M"), "币种": pos['交易对'], "方向": f"减仓-{pos['方向']}", "盈亏": round(pnl * ratio, 2), "价格": now_p})
                            st.session_state.balance += (pos['占用保证金'] * ratio + pnl * ratio)
                            pos['名义价值'] *= (1-ratio); pos['占用保证金'] *= (1-ratio)
                            if pos['名义价值'] < 1: st.session_state.positions.pop(i)
                            sync_data(); st.rerun()

# --- Tab 4: 历史记录 ---
with tabs[3]:
    st.markdown("#### 📜 最近成交流水")
    if not st.session_state.history:
        st.caption("暂无成交历史")
    else:
        for h in st.session_state.history[:30]:
            st.markdown(f"""
            <div style="padding:15px; border-bottom:1px solid #EEE; display:flex; justify-content:space-between; align-items:center; background:white; border-radius:12px; margin-bottom:8px;">
                <div>
                    <div style="font-weight:600;">{h['币种']} · {h['方向']}</div>
                    <div style="font-size:11px; color:#8E8E93;">{h['时间']} | 成交价: {h['价格']}</div>
                </div>
                <div class="{'price-up' if h['盈亏']>=0 else 'price-down'}" style="font-size:1.1rem;">
                    {h['盈亏']:+.2f} USDT
                </div>
            </div>
            """, unsafe_allow_html=True)
