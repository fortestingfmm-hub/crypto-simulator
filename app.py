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
# 0. UI 配置 - Apple 极简白
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
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: 24px;
        padding: 24px;
        text-align: center;
        margin-bottom: 25px;
        border: 1px solid rgba(0,0,0,0.05);
    }
    
    .text-secondary { color: #86868B; font-size: 0.85rem; }
    .price-up { color: #34C759; font-weight: 600; }
    .price-down { color: #FF3B30; font-weight: 600; }
    
    .stButton>button { border-radius: 12px; background-color: #007AFF; color: white; font-weight: 600; border: none; }
    header {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 数据库引擎 (含历史记录支持)
# ==========================================
DATA_FILE = "trading_v9_ultimate.json"

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
        if u in db["users"]:
            db["users"][u]["balance"] = st.session_state.balance
            db["users"][u]["positions"] = st.session_state.positions
            db["users"][u]["history"] = st.session_state.get("history", [])
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
            st.session_state.update({
                "logged_in":True,"username":u,"balance":info["balance"],
                "positions":info["positions"],"history":info.get("history", []), "chat_history":[]
            })
            break

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align:center;'>Crypto Terminal</h2>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["登录", "注册"])
    with t1:
        with st.form("l"):
            u = st.text_input("用户名")
            p = st.text_input("密码", type="password")
            if st.form_submit_button("进入终端", use_container_width=True):
                hp = hashlib.sha256(p.encode()).hexdigest()
                if u in db["users"] and db["users"][u]["password"] == hp:
                    tk = str(uuid.uuid4())
                    db["users"][u]["session_token"] = tk
                    save_db(db); st.query_params["token"] = tk
                    st.session_state.update({
                        "logged_in":True,"username":u,"balance":db["users"][u]["balance"],
                        "positions":db["users"][u]["positions"],"history":db["users"][u].get("history", []), "chat_history":[]
                    })
                    st.rerun()
    with t2:
        with st.form("r"):
            nu = st.text_input("用户名")
            np = st.text_input("密码", type="password")
            if st.form_submit_button("注册获取 500w USDT", use_container_width=True):
                if nu and np and nu not in db["users"]:
                    db["users"][nu] = {"password":hashlib.sha256(np.encode()).hexdigest(),"balance":5000000.0,"positions":[],"history":[],"session_token":""}
                    save_db(db); st.success("完成")
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
# 4. 自由拖拽 AI 浮窗
# ==========================================
ai_ctx = f"余额:{st.session_state.balance}U,仓位:{len(st.session_state.positions)}个"
st.components.v1.html(f"""
<div id="ai-win" style="position:fixed; bottom:80px; right:20px; width:280px; z-index:999; background:rgba(255,255,255,0.8); backdrop-filter:blur(15px); border-radius:18px; box-shadow:0 8px 30px rgba(0,0,0,0.1); border:1px solid rgba(0,0,0,0.05); overflow:hidden; display:flex; flex-direction:column;">
    <div id="ai-winheader" style="padding:10px; background:rgba(0,122,255,0.05); cursor:move; display:flex; justify-content:space-between; align-items:center;">
        <span style="font-weight:600; font-size:12px; color:#007AFF;">🤖 AI 助手 (按住拖动)</span>
    </div>
    <div id="ai-body" style="height:200px; padding:10px; overflow-y:auto; font-size:12px; color:#1D1D1F;">
        <div style="background:white; padding:8px; border-radius:10px; border:1px solid rgba(0,0,0,0.05);">我是你的模拟交易助手。</div>
        <div id="msgs"></div>
    </div>
    <div style="padding:10px; background:white;"><input type="text" id="ai-in" placeholder="问我分析..." style="width:100%; border:1px solid #EEE; border-radius:8px; padding:6px; font-size:12px; outline:none;"></div>
</div>
<script>
    function drag(e){{var p1=0,p2=0,p3=0,p4=0; if(document.getElementById(e.id+"header")){{document.getElementById(e.id+"header").onmousedown=md;}} function md(e){{e=e||window.event;e.preventDefault();p3=e.clientX;p4=e.clientY;document.onmouseup=cd;document.onmousemove=ed;}} function ed(e){{e=e||window.event;e.preventDefault();p1=p3-e.clientX;p2=p4-e.clientY;p3=e.clientX;p4=e.clientY;e.target.closest("#ai-win").style.top=(e.target.closest("#ai-win").offsetTop-p2)+"px";e.target.closest("#ai-win").style.left=(e.target.closest("#ai-win").offsetLeft-p1)+"px";e.target.closest("#ai-win").style.bottom="auto";e.target.closest("#ai-win").style.right="auto";}} function cd(){{document.onmouseup=null;document.onmousemove=null;}}}}
    drag(document.getElementById("ai-win"));
    const i=document.getElementById('ai-in'), m=document.getElementById('msgs');
    i.addEventListener('keypress',function(e){{if(e.key==='Enter'&&i.value!==""){{
        const v=i.value; i.value=""; m.innerHTML+=`<div style="text-align:right; margin-top:8px;"><span style="background:#007AFF; color:white; padding:4px 8px; border-radius:8px;">${{v}}</span></div>`;
        fetch(`https://text.pollinations.ai/system:中文专家。资产:{ai_ctx}。问:${{v}}?model=openai`).then(r=>r.text()).then(d=>{{
            m.innerHTML+=`<div style="margin-top:8px;"><span style="background:white; padding:4px 8px; border-radius:8px; border:1px solid #EEE;">${{d}}</span></div>`;
            document.getElementById('ai-body').scrollTop=document.getElementById('ai-body').scrollHeight;
        }});
    }}}});
</script>
""", height=0)

# ==========================================
# 5. 主页面
# ==========================================
# 顶部看板
tm = sum(p['占用保证金'] for p in st.session_state.positions)
st.markdown(f"""
<div class="balance-header">
    <div class="text-secondary">当前总权益 (USDT)</div>
    <div style="font-size: 2.2rem; font-weight: 600; color: #1D1D1F;">{st.session_state.balance + tm:,.2f}</div>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs(["📊 行情", "📈 交易", "💼 持仓", "📜 历史"])

# --- Tab 1: 行情 ---
with tabs[0]:
    st.components.v1.html("""
    <style>body { background: transparent; font-family: -apple-system; margin:0; } .list { height: 400px; overflow-y: auto; } .item { display: flex; justify-content: space-between; padding: 15px 8px; border-bottom: 1px solid #E5E5E7; }</style>
    <div class="list" id="l"></div>
    <script>
        const b = document.getElementById('l'), ws = new WebSocket('wss://data-stream.binance.vision:9443/ws/!ticker@arr');
        let c = {};
        ws.onmessage = (e) => {
            JSON.parse(e.data).filter(i => i.s.endsWith('USDT')).sort((x, y) => parseFloat(y.q) - parseFloat(x.q)).slice(0, 50).forEach(i => {
                if(!c[i.s]) { let d = document.createElement('div'); d.className = 'item'; b.appendChild(d); c[i.s] = d; }
                const u = parseFloat(i.P) >= 0;
                c[i.s].innerHTML = `<b>${i.s}</b><div style="text-align:right"><b>$${parseFloat(i.c).toFixed(2)}</b><div style="color:${u?'#34C759':'#FF3B30'}">${u?'+':''}${parseFloat(i.P).toFixed(2)}%</div></div>`;
            });
        };
    </script>
    """, height=400)

# --- Tab 2: 交易 (独立双滑块) ---
with tabs[1]:
    target = st.selectbox("搜索币种", all_coins, index=all_coins.index("BTCUSDT"))
    st.components.v1.html(f"""
        <div id="tv" style="height:300px; border-radius:18px; overflow:hidden; border:1px solid #E5E5E7;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize":true,"symbol":"BINANCE:{target}","interval":"1","theme":"light","style":"1","hide_top_toolbar":true,"container_id":"tv"}});</script>
    """, height=300)
    
    st.markdown(f"**可用本金: {st.session_state.balance:,.2f} USDT**")
    actual_margin = st.slider("1. 投入保证金金额 (USDT)", 0.0, float(st.session_state.balance), float(st.session_state.balance * 0.1), step=100.0)
    leverage = st.slider("2. 选择杠杆倍数", 1, 1000, 100)
    notional = actual_margin * leverage
    st.caption(f"开仓总值: {notional:,.2f} U")
    
    cb1, cb2 = st.columns(2)
    with cb1:
        if st.button("做多 (Long)", use_container_width=True, type="primary"):
            p = get_price(target);
            if p > 0 and st.session_state.balance >= actual_margin:
                st.session_state.balance -= actual_margin
                st.session_state.positions.append({"交易对":target,"方向":"多","开仓价":p,"杠杆":leverage,"名义价值":notional,"占用保证金":actual_margin})
                sync_data(); st.success(f"做多成功: {p}"); time.sleep(0.5); st.rerun()
    with cb2:
        if st.button("做空 (Short)", use_container_width=True):
            p = get_price(target);
            if p > 0 and st.session_state.balance >= actual_margin:
                st.session_state.balance -= actual_margin
                st.session_state.positions.append({"交易对":target,"方向":"空","开仓价":p,"杠杆":leverage,"名义价值":notional,"占用保证金":actual_margin})
                sync_data(); st.success(f"做空成功: {p}"); time.sleep(0.5); st.rerun()

# --- Tab 3: 持仓管理 ---
with tabs[2]:
    if st.button("重置账户"): 
        st.session_state.update({"balance":5000000.0,"positions":[],"history":[]}); sync_data(); st.rerun()
    
    if not st.session_state.positions:
        st.info("暂无持仓")
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
                c_close, c_adj = st.columns(2)
                with c_close:
                    if st.button("全平结算", key=f"cl_{i}", use_container_width=True):
                        # 🌟 写入历史记录
                        st.session_state.history.insert(0, {
                            "时间": datetime.now().strftime("%m-%d %H:%M"), "币种": pos['交易对'],
                            "方向": pos['方向'], "盈亏": round(pnl, 2), "价格": now_p
                        })
                        st.session_state.balance += (pos['占用保证金'] + pnl)
                        st.session_state.positions.pop(i); sync_data(); st.rerun()
                with c_adj:
                    with st.popover("调整", use_container_width=True):
                        adj_v = st.slider("金额", 0.0, float(st.session_state.balance), 100.0, key=f"as_{i}")
                        if st.button("加仓", key=f"ad_{i}", use_container_width=True):
                            if st.session_state.balance >= adj_v:
                                st.session_state.balance -= adj_v
                                pos['名义价值'] += (adj_v * pos['杠杆']); pos['占用保证金'] += adj_v
                                sync_data(); st.rerun()
                        if st.button("减仓", key=f"re_{i}", use_container_width=True):
                            ratio = min(adj_v / pos['占用保证金'], 1.0) if pos['占用保证金']>0 else 0
                            # 🌟 减仓也记入历史
                            st.session_state.history.insert(0, {"时间": datetime.now().strftime("%m-%d %H:%M"), "币种": pos['交易对'], "方向": f"减仓-{pos['方向']}", "盈亏": round(pnl * ratio, 2), "价格": now_p})
                            st.session_state.balance += (pos['占用保证金'] * ratio + pnl * ratio)
                            pos['名义价值'] *= (1-ratio); pos['占用保证金'] *= (1-ratio)
                            if pos['名义价值'] < 1: st.session_state.positions.pop(i)
                            sync_data(); st.rerun()

# --- Tab 4: 历史交易记录 ---
with tabs[3]:
    st.markdown("#### 📜 最近成交记录")
    if not st.session_state.get("history"):
        st.caption("暂无历史成交记录。")
    else:
        for h in st.session_state.history[:20]: # 显示最近 20 条
            with st.container():
                st.markdown(f"""
                <div style="padding:12px; border-bottom:1px solid #EEE; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-weight:600; font-size:14px;">{h['币种']} · {h['方向']}</div>
                        <div style="font-size:10px; color:#8E8E93;">{h['时间']} | 价格: {h['价格']}</div>
                    </div>
                    <div style="color:{'#34C759' if h['盈亏']>=0 else '#FF3B30'}; font-weight:600;">
                        {h['盈亏']:+.2f} USDT
                    </div>
                </div>
                """, unsafe_allow_html=True)
