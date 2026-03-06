import streamlit as st
import pandas as pd
import requests
import time
import json
import os
import hashlib
import uuid
from datetime import datetime

# ==========================================
# 0. UI 配置 - Apple 极简白
# ==========================================
st.set_page_config(page_title="Crypto Terminal Pro", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;600&display=swap');
    html, body, [data-testid="stAppViewContainer"] { background-color: #F5F5F7; font-family: 'SF Pro Display', sans-serif; }
    .block-container { padding-top: 1.5rem; padding-bottom: 5rem; }
    .apple-card { background: #FFFFFF; border-radius: 20px; padding: 18px; margin-bottom: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.02); border: 1px solid rgba(0,0,0,0.01); }
    .balance-header { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(20px); border-radius: 24px; padding: 20px; text-align: center; margin-bottom: 15px; border: 1px solid rgba(0,0,0,0.05); }
    .price-up { color: #34C759; font-weight: 600; }
    .price-down { color: #FF3B30; font-weight: 600; }
    .stButton>button { border-radius: 12px; background-color: #007AFF; color: white; font-weight: 600; border: none; }
    header {visibility: hidden;} footer {visibility: hidden;}
    .ai-bubble-user { background: #007AFF; color: white; padding: 10px; border-radius: 15px 15px 2px 15px; margin-bottom: 10px; text-align: right; }
    .ai-bubble-bot { background: #E9E9EB; color: #1D1D1F; padding: 10px; border-radius: 15px 15px 15px 2px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 核心配置与 DeepSeek
# ==========================================
DEEPSEEK_KEY = "sk-9de5a0aa88744f7d94fc2a3a6b140f75"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DATA_FILE = "trading_v17_deepseek.json"

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
    st.session_state.update({"logged_in": False, "history": [], "favorites": [], "chat_history": [], "market_snapshot": ""})

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
                "favorites": info.get("favorites", [])
            })
            break

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align:center;'>Terminal Pro</h2>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["安全登录", "创建账户"])
    with t1:
        with st.form("login"):
            u = st.text_input("用户名").strip()
            p = st.text_input("密码", type="password").strip()
            if st.form_submit_button("进入终端", use_container_width=True):
                hp = hashlib.sha256(p.encode()).hexdigest()
                db = load_db()
                if u in db["users"] and db["users"][u]["password"] == hp:
                    tk = str(uuid.uuid4())
                    db["users"][u]["session_token"] = tk
                    save_db(db); st.query_params["token"] = tk
                    st.session_state.update({"logged_in": True, "username": u, "balance": db[u]["balance"], "positions": db[u]["positions"], "history": db[u].get("history", []), "favorites": db[u].get("favorites", [])})
                    st.rerun()
                else: st.error("登录信息有误")
    with t2:
        with st.form("reg"):
            nu = st.text_input("设置用户名").strip()
            np = st.text_input("设置密码", type="password").strip()
            if st.form_submit_button("注册新账户", use_container_width=True):
                db = load_db()
                if nu in db["users"]: st.error("用户名已存在")
                elif nu and np:
                    db["users"][nu] = {"password": hashlib.sha256(np.encode()).hexdigest(), "balance": 5000000.0, "positions": [], "history": [], "favorites": []}
                    save_db(db); st.success("开户成功！")
    st.stop()

# ==========================================
# 3. 实时市场分析引擎
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

# ==========================================
# 4. 系统管理区
# ==========================================
c_u, c_s = st.columns([7, 2])
with c_u: st.markdown(f"**{st.session_state.username}** · DeepSeek 驱动模式")
with c_s:
    with st.popover("⚙️"):
        if st.button("🔄 重置账户", use_container_width=True):
            st.session_state.update({"balance": 5000000.0, "positions": [], "history": [], "favorites": []})
            sync_data(); st.rerun()
        if st.button("🚪 安全退出", use_container_width=True):
            st.query_params.clear(); st.session_state.clear(); st.rerun()

# 资产看板
tm = sum(p['占用保证金'] for p in st.session_state.positions)
st.markdown(f"""
<div class="balance-header">
    <div class="text-secondary">总权益估值 (USDT)</div>
    <div style="font-size: 2.2rem; font-weight: 600; color: #1D1D1F;">{st.session_state.balance + tm:,.2f}</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 5. DeepSeek AI 顶置助理 (读取市场)
# ==========================================
if not market_df.empty:
    top3 = market_df.sort_values('priceChangePercent', ascending=False).head(3)
    snap = " | ".join([f"{r['symbol']}: ${r['lastPrice']}({r['priceChangePercent']}%)" for _, r in top3.iterrows()])
    st.session_state.market_snapshot = snap

with st.container():
    st.markdown('<div class="apple-card" style="border-left: 5px solid #007AFF;">🤖 <b>DeepSeek 智能投顾</b>', unsafe_allow_html=True)
    a_in, a_btn = st.columns([4, 1])
    u_q = a_in.text_input("询问 DeepSeek 市场建议", key="ds_input", placeholder="例如：分析现在的涨幅榜，我该买哪个？", label_visibility="collapsed")
    if a_btn.button("咨询", use_container_width=True) and u_q:
        try:
            sys_msg = f"你是专业中文加密货币专家。当前市场热门:{st.session_state.market_snapshot}。用户可用余额:{st.session_state.balance}U。请基于此数据给出犀利简短的建议。"
            headers = {"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "system", "content": sys_msg}, {"role": "user", "content": u_q}],
                "stream": False
            }
            res = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=15)
            ans = res.json()['choices'][0]['message']['content']
            st.session_state.chat_history.append({"role": "user", "content": u_q})
            st.session_state.chat_history.append({"role": "assistant", "content": ans})
        except: st.error("DeepSeek API 连接繁忙，请检查密钥或稍后重试")
    
    if st.session_state.chat_history:
        for m in st.session_state.chat_history[-2:]:
            if m["role"] == "user": st.markdown(f'<div class="ai-bubble-user">{m["content"]}</div>', unsafe_allow_html=True)
            else: st.markdown(f'<div class="ai-bubble-bot">{m["content"]}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 6. 分类行情与交易系统
# ==========================================
tabs = st.tabs(["📊 全球行情", "📈 极速交易", "💼 仓位管理", "📜 历史记录"])

with tabs[0]:
    m_sub = st.tabs(["⭐ 自选", "🔥 涨幅榜", "💎 主流", "🆕 新币", "🌐 DEX"])
    def show_list(df, tag):
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
        dex_coins = ["UNIUSDT", "SUSHIUSDT", "CAKEUSDT", "AAVEUSDT", "CRVUSDT", "1INCHUSDT"]
        show_list(market_df[market_df['symbol'].isin(dex_coins)], "dex")

with tabs[1]:
    all_syms = market_df['symbol'].tolist() if not market_df.empty else ["BTCUSDT"]
    target = st.selectbox("选择交易资产", all_syms, index=all_syms.index("BTCUSDT"))
    st.components.v1.html(f"""
        <div id="tv" style="height:300px; border-radius:18px; overflow:hidden; border:1px solid #E5E5E7;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize":true,"symbol":"BINANCE:{target}","interval":"1","theme":"light","style":"1","hide_top_toolbar":true,"container_id":"tv"}});</script>
    """, height=300)
    
    st.markdown(f"**可用本金: {st.session_state.balance:,.2f} USDT**")
    # 🌟 独立双滑块
    act_margin = st.slider("1. 投入本金 (USDT)", 0.0, float(st.session_state.balance), float(st.session_state.balance * 0.1), step=100.0)
    lev = st.slider("2. 选择杠杆倍数", 1, 1000, 100)
    notional = act_margin * lev
    st.markdown(f"<div style='background:#F2F2F7; padding:12px; border-radius:12px; margin-bottom:15px;'>成交总额 (名义价值): <b style='color:#007AFF;'>{notional:,.2f} U</b></div>", unsafe_allow_html=True)
    
    cb1, cb2 = st.columns(2)
    with cb1:
        if st.button("做多 (Long) 🟢", use_container_width=True, type="primary"):
            p = get_price(target)
            if p > 0 and st.session_state.balance >= act_margin:
                st.session_state.balance -= act_margin
                st.session_state.positions.append({"交易对":target,"方向":"多","开仓价":p,"杠杆":lev,"名义价值":notional,"占用保证金":act_margin})
                sync_data(); st.success(f"做多成功: {p}"); time.sleep(0.5); st.rerun()
    with cb2:
        if st.button("做空 (Short) 🔴", use_container_width=True):
            p = get_price(target)
            if p > 0 and st.session_state.balance >= act_margin:
                st.session_state.balance -= act_margin
                st.session_state.positions.append({"交易对":target,"方向":"空","开仓价":p,"杠杆":lev,"名义价值":notional,"占用保证金":act_margin})
                sync_data(); st.success(f"做空成功: {p}"); time.sleep(0.5); st.rerun()

with tabs[2]:
    if not st.session_state.positions:
        st.info("暂无持仓")
    else:
        for i, pos in enumerate(st.session_state.positions):
            now_p = get_price(pos['交易对']) or pos['开仓价']
            pnl = (now_p - pos['开仓价']) / pos['开仓价'] * pos['名义价值'] if pos['方向'] == "多" else (pos['开仓价'] - now_p) / pos['开仓价'] * pos['名义价值']
            with st.container():
                st.markdown(f"""<div class="apple-card"><div style="display:flex; justify-content:space-between;"><b>{pos['交易对']} · {pos['方向']}</b><span class="{'price-up' if pnl>=0 else 'price-down'}">{pnl:+.2f} U</span></div></div>""", unsafe_allow_html=True)
                m1, m2 = st.columns(2)
                with m1:
                    if st.button("平仓结算", key=f"cl_{i}", use_container_width=True):
                        st.session_state.history.insert(0, {"时间": datetime.now().strftime("%H:%M"), "币种": pos['交易对'], "方向": pos['方向'], "盈亏": round(pnl, 2), "价格": now_p})
                        st.session_state.balance += (pos['占用保证金'] + pnl); st.session_state.positions.pop(i); sync_data(); st.rerun()
                with m2:
                    with st.popover("调仓", use_container_width=True):
                        adj = st.slider("金额", 0.0, float(st.session_state.balance), 500.0, key=f"as_{i}")
                        if st.button("补仓", key=f"ad_{i}"):
                            st.session_state.balance -= adj; pos['名义价值'] += (adj * pos['杠杆']); pos['占用保证金'] += adj; sync_data(); st.rerun()
                        if st.button("减仓", key=f"re_{i}"):
                            ratio = min(adj/pos['占用保证金'], 1.0) if pos['占用保证金']>0 else 0
                            st.session_state.balance += (pos['占用保证金']*ratio + pnl*ratio); pos['名义价值'] *= (1-ratio); pos['占用保证金'] *= (1-ratio)
                            if pos['名义价值'] < 1: st.session_state.positions.pop(i)
                            sync_data(); st.rerun()

with tabs[3]:
    st.markdown("#### 📜 交易流水")
    for h in st.session_state.history[:30]:
        st.markdown(f"""<div style="padding:15px; border-bottom:1px solid #EEE; display:flex; justify-content:space-between;"><div><b>{h['币种']} · {h['方向']}</b><div style="font-size:11px; color:#8E8E93;">{h['时间']} | {h['价格']}</div></div><div class="{'price-up' if h['盈亏']>=0 else 'price-down'}">{h['盈亏']:+.2f} U</div></div>""", unsafe_allow_html=True)
