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
    html, body, [data-testid="stAppViewContainer"] { background-color: #F5F5F7; font-family: 'SF Pro Display', sans-serif; color: #1D1D1F; }
    .block-container { padding-top: 1.5rem; padding-bottom: 5rem; }
    .apple-card { background: #FFFFFF; border-radius: 20px; padding: 20px; margin-bottom: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.03); border: 1px solid rgba(0,0,0,0.01); }
    .balance-header { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border-radius: 24px; padding: 20px; text-align: center; margin-bottom: 15px; border: 1px solid rgba(0,0,0,0.05); }
    .ai-box { background: #FFFFFF; border-radius: 18px; padding: 15px; margin-bottom: 20px; border-left: 5px solid #007AFF; box-shadow: 0 4px 12px rgba(0,0,0,0.02); }
    .price-up { color: #34C759; font-weight: 600; }
    .price-down { color: #FF3B30; font-weight: 600; }
    .stButton>button { border-radius: 12px; background-color: #007AFF; color: white; font-weight: 600; border: none; }
    header {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 配置与数据库引擎
# ==========================================
DEEPSEEK_KEY = "sk-9de5a0aa88744f7d94fc2a3a6b140f75"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DATA_FILE = "trading_v19_final.json"

def load_db():
    if not os.path.exists(DATA_FILE): return {"users": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
            return d if "users" in d else {"users": {}}
    except: return {"users": {}}

def save_db(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

def sync_data():
    if st.session_state.get('logged_in'):
        db = load_db()
        u = st.session_state.username
        if u in db["users"]:
            db["users"][u].update({
                "balance": st.session_state.balance,
                "positions": st.session_state.positions,
                "history": st.session_state.get("history", []),
                "favorites": st.session_state.get("favorites", [])
            })
            save_db(db)

# ==========================================
# 2. 账号系统
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.update({"logged_in": False, "history": [], "favorites": [], "chat_history": []})

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
                "favorites": info.get("favorites", [])
            })
            break

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align:center;'>Terminal Pro</h2>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["安全登录", "新开账户"])
    with t1:
        with st.form("l_f"):
            u_raw = st.text_input("用户名")
            p_raw = st.text_input("密码", type="password")
            if st.form_submit_button("登录", use_container_width=True):
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
                        "favorites": db["users"][u].get("favorites", []),
                        "chat_history": []
                    })
                    st.rerun()
                else: st.error("登录失败")
    with t2:
        with st.form("r_f"):
            nu = st.text_input("设置新用户名").strip()
            np = st.text_input("设置新密码", type="password").strip()
            if st.form_submit_button("注册", use_container_width=True):
                db = load_db()
                if nu in db["users"]: st.error("用户名已存在")
                else:
                    db["users"][nu] = {"password": hashlib.sha256(np.encode()).hexdigest(), "balance": 5000000.0, "positions": [], "history": [], "favorites": [], "session_token": ""}
                    save_db(db); st.success("开户成功！")
    st.stop()

# ==========================================
# 3. 实时行情与价格获取
# ==========================================
@st.cache_data(ttl=20)
def get_market_df():
    try:
        res = requests.get("https://data-api.binance.vision/api/v3/ticker/24hr", timeout=5).json()
        df = pd.DataFrame(res)
        df = df[df['symbol'].str.endswith('USDT')]
        df[['lastPrice', 'priceChangePercent', 'quoteVolume']] = df[['lastPrice', 'priceChangePercent', 'quoteVolume']].astype(float)
        return df
    except: return pd.DataFrame()

market_df = get_market_df()

# 🛠 修复函数：从当前内存或网络获取价格
def get_target_price(symbol):
    if not market_df.empty and symbol in market_df['symbol'].values:
        return market_df[market_df['symbol'] == symbol]['lastPrice'].values[0]
    try:
        r = requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbol={symbol}", timeout=2).json()
        return float(r['price'])
    except: return 0.0

# ==========================================
# 4. 账户与系统管理
# ==========================================
c_u, c_s = st.columns([7, 2])
with c_u: st.markdown(f"**{st.session_state.username}** · 极简模拟终端")
with c_s:
    with st.popover("⚙️"):
        if st.button("🔄 重置账户"):
            st.session_state.update({"balance": 5000000.0, "positions": [], "history": [], "favorites": []})
            sync_data(); st.rerun()
        if st.button("🚪 安全退出"):
            st.query_params.clear(); st.session_state.clear(); st.rerun()

tm = sum(p['占用保证金'] for p in st.session_state.positions)
st.markdown(f"""
<div class="balance-header">
    <div class="text-secondary">当前总权益 (USDT)</div>
    <div style="font-size: 2.2rem; font-weight: 600; color: #1D1D1F;">{st.session_state.balance + tm:,.2f}</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 5. DeepSeek 智能投顾 (顶置固定)
# ==========================================
with st.container():
    st.markdown('<div class="ai-box">🤖 <b>DeepSeek 智能投顾</b>', unsafe_allow_html=True)
    a1, a2 = st.columns([4, 1])
    u_q = a1.text_input("咨询 AI 关于行情", key="ds_input", placeholder="例如：BTC 现在的趋势如何？", label_visibility="collapsed")
    if a2.button("发送", use_container_width=True) and u_q:
        try:
            snap = " | ".join([f"{r['symbol']}: ${r['lastPrice']}" for _, r in market_df.head(3).iterrows()]) if not market_df.empty else "数据同步中"
            sys_msg = f"你是中文专家。当前行情:{snap}。余额:{st.session_state.balance}U。简短回答建议。"
            headers = {"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"}
            payload = {"model": "deepseek-chat", "messages": [{"role": "system", "content": sys_msg}, {"role": "user", "content": u_q}]}
            res = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=12)
            ans = res.json()['choices'][0]['message']['content']
            st.session_state.chat_history.append({"role": "user", "content": u_q})
            st.session_state.chat_history.append({"role": "assistant", "content": ans})
        except: st.error("AI 忙碌，请稍后重试")
    if st.session_state.chat_history:
        for m in st.session_state.chat_history[-2:]:
            with st.chat_message(m["role"]): st.markdown(m["content"])
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 6. 功能板块
# ==========================================
tabs = st.tabs(["📊 行情", "📈 交易", "💼 持仓", "📜 历史"])

# --- 行情表 ---
with tabs[0]:
    m_sub = st.tabs(["⭐ 自选", "🔥 涨幅榜", "💎 主流", "🆕 新币", "🌐 DEX"])
    def show_list(df, tag):
        if df.empty: st.caption("暂无数据"); return
        for _, r in df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([1, 4, 3])
                is_fav = r['symbol'] in st.session_state.favorites
                if c1.button("⭐" if is_fav else "☆", key=f"f_{tag}_{r['symbol']}"):
                    if is_fav: st.session_state.favorites.remove(r['symbol'])
                    else: st.session_state.favorites.append(r['symbol'])
                    sync_data(); st.rerun()
                c2.markdown(f"**{r['symbol'].replace('USDT','')}**")
                color = "price-up" if r['priceChangePercent'] >= 0 else "price-down"
                c3.markdown(f"<div style='text-align:right'><b>${r['lastPrice']:.2f}</b><br><span class='{color}'>{r['priceChangePercent']:+.2f}%</span></div>", unsafe_allow_html=True)

    with m_sub[0]: show_list(market_df[market_df['symbol'].isin(st.session_state.favorites)], "fav")
    with m_sub[1]: show_list(market_df.sort_values('priceChangePercent', ascending=False).head(20), "gain")
    with m_sub[2]: show_list(market_df.sort_values('quoteVolume', ascending=False).head(15), "main")
    with m_sub[3]: show_list(market_df.tail(15), "new")
    with m_sub[4]: 
        dex_tokens = ["UNIUSDT", "SUSHIUSDT", "CAKEUSDT", "AAVEUSDT", "CRVUSDT", "RAYUSDT"]
        show_list(market_df[market_df['symbol'].isin(dex_tokens)], "dex")

# --- 交易区 (独立双滑块) ---
with tabs[1]:
    all_syms = market_df['symbol'].tolist() if not market_df.empty else ["BTCUSDT"]
    target = st.selectbox("选择交易资产", all_syms, index=all_syms.index("BTCUSDT") if "BTCUSDT" in all_syms else 0)
    st.components.v1.html(f"""
        <div id="tv" style="height:320px; border-radius:18px; overflow:hidden; border:1px solid #E5E5E7;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize":true,"symbol":"BINANCE:{target}","interval":"1","theme":"light","style":"1","hide_top_toolbar":true,"container_id":"tv"}});</script>
    """, height=320)
    
    st.markdown(f"**可用本金: {st.session_state.balance:,.2f} USDT**")
    # 🌟 核心：本金与杠杆完全独立
    actual_margin = st.slider("1. 投入本金金额 (USDT)", 0.0, float(st.session_state.balance), float(st.session_state.balance * 0.1), step=100.0)
    leverage = st.slider("2. 选择杠杆倍数 (Leverage)", 1, 1000, 100)
    notional = actual_margin * leverage
    st.markdown(f"<div style='background:#F2F2F7; padding:12px; border-radius:12px; margin-bottom:15px;'>成交估值: <b style='color:#007AFF;'>{notional:,.2f} U</b></div>", unsafe_allow_html=True)
    
    cb1, cb2 = st.columns(2)
    with cb1:
        if st.button("做多 (Long) 🟢", use_container_width=True, type="primary"):
            p = get_target_price(target)
            if p > 0 and st.session_state.balance >= actual_margin:
                st.session_state.balance -= actual_margin
                st.session_state.positions.append({"交易对":target,"方向":"多","开仓价":p,"杠杆":leverage,"名义价值":notional,"占用保证金":actual_margin})
                sync_data(); st.success(f"做多成功: {p}"); time.sleep(0.5); st.rerun()
    with cb2:
        if st.button("做空 (Short) 🔴", use_container_width=True):
            p = get_target_price(target)
            if p > 0 and st.session_state.balance >= actual_margin:
                st.session_state.balance -= actual_margin
                st.session_state.positions.append({"交易对":target,"方向":"空","开仓价":p,"杠杆":leverage,"名义价值":notional,"占用保证金":actual_margin})
                sync_data(); st.success(f"做空成功: {p}"); time.sleep(0.5); st.rerun()

# --- 持仓与历史 ---
with tabs[2]:
    if not st.session_state.positions: st.info("暂无持仓")
    else:
        for i, pos in enumerate(st.session_state.positions):
            now_p = get_target_price(pos['交易对']) or pos['开仓价']
            pnl = (now_p - pos['开仓价']) / pos['开仓价'] * pos['名义价值'] if pos['方向'] == "多" else (pos['开仓价'] - now_p) / pos['开仓价'] * pos['名义价值']
            with st.container():
                st.markdown(f"""<div class="apple-card"><div style="display:flex; justify-content:space-between;"><b>{pos['交易对']} · {pos['杠杆']}x</b><span class="{'price-up' if pnl>=0 else 'price-down'}">{pnl:+.2f} U</span></div></div>""", unsafe_allow_html=True)
                m1, m2 = st.columns(2)
                with m1:
                    if st.button("全平结算", key=f"cl_{i}", use_container_width=True):
                        st.session_state.history.insert(0, {"时间": datetime.now().strftime("%H:%M"), "币种": pos['交易对'], "方向": pos['方向'], "盈亏": round(pnl, 2), "价格": now_p})
                        st.session_state.balance += (pos['占用保证金'] + pnl); st.session_state.positions.pop(i); sync_data(); st.rerun()
                with m2:
                    with st.popover("调仓"):
                        adj = st.slider("金额", 0.0, float(st.session_state.balance), 1000.0, key=f"as_{i}")
                        if st.button("加仓", key=f"ad_{i}"):
                            st.session_state.balance -= adj; pos['名义价值'] += (adj * pos['杠杆']); pos['占用保证金'] += adj; sync_data(); st.rerun()

with tabs[3]:
    st.markdown("#### 📜 历史流水")
    for h in st.session_state.history[:30]:
        st.markdown(f"""<div style="padding:15px; border-bottom:1px solid #EEE; display:flex; justify-content:space-between;"><div><b>{h['币种']} · {h['方向']}</b><div style="font-size:11px; color:#8E8E93;">{h['时间']} | {h['价格']}</div></div><div class="{'price-up' if h['盈亏']>=0 else 'price-down'}">{h['盈亏']:+.2f} U</div></div>""", unsafe_allow_html=True)
