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
    html, body, [data-testid="stAppViewContainer"] { background-color: #F5F5F7; font-family: 'SF Pro Display', sans-serif; color: #1D1D1F; }
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    .apple-card { background: #FFFFFF; border-radius: 20px; padding: 20px; margin-bottom: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.03); border: 1px solid rgba(0,0,0,0.01); }
    .balance-header { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(20px); border-radius: 24px; padding: 20px; text-align: center; margin-bottom: 15px; border: 1px solid rgba(0,0,0,0.05); position: sticky; top: 0; z-index: 999; }
    .ai-box { background: #FFFFFF; border-radius: 18px; padding: 15px; margin-bottom: 15px; border-left: 5px solid #007AFF; box-shadow: 0 4px 12px rgba(0,0,0,0.02); }
    .price-up { color: #34C759; font-weight: 600; }
    .price-down { color: #FF3B30; font-weight: 600; }
    .stButton>button { border-radius: 12px; background-color: #007AFF; color: white; font-weight: 600; border: none; }
    header {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 数据库持久化 - 永久锁定文件名
# ==========================================
DEEPSEEK_KEY = "sk-9de5a0aa88744f7d94fc2a3a6b140f75"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DATA_FILE = "trading_permanent_data.json" # 🔒 永久固定文件名，不再变动

def load_db():
    if not os.path.exists(DATA_FILE): return {"users": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if "users" in data else {"users": {}}
    except: return {"users": {}}

def save_db(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: 
        json.dump(data, f, ensure_ascii=False, indent=4)

def sync_data():
    if st.session_state.get('logged_in'):
        # 实时存盘，确保刷新不丢数据
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
# 2. 账号系统 (Token 持久化)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.update({"logged_in": False, "history": [], "favorites": [], "chat_history": []})

db = load_db()
tok = st.query_params.get("token")

# 自动重登逻辑
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
                db = load_db() # 登录瞬间刷新DB
                if u in db["users"] and db["users"][u]["password"] == hp:
                    tk = db["users"][u].get("session_token") or str(uuid.uuid4())
                    db["users"][u]["session_token"] = tk
                    save_db(db)
                    st.query_params["token"] = tk 
                    st.session_state.update({"logged_in": True, "username": u, "balance": db["users"][u]["balance"], "positions": db["users"][u]["positions"], "history": db["users"][u].get("history", []), "favorites": db["users"][u].get("favorites", [])})
                    st.rerun()
                else: st.error("账号或密码不匹配")
    with t2:
        with st.form("r_f"):
            nu = st.text_input("设置新用户名").strip()
            np = st.text_input("设置新密码", type="password").strip()
            if st.form_submit_button("注册获取 500万 U", use_container_width=True):
                db = load_db()
                if nu in db["users"]: st.error("该用户名已被占用")
                elif nu and np:
                    db["users"][nu] = {"password": hashlib.sha256(np.encode()).hexdigest(), "balance": 5000000.0, "positions": [], "history": [], "favorites": [], "session_token": ""}
                    save_db(db); st.success("开户成功！")
    st.stop()

# ==========================================
# 3. 价格引擎
# ==========================================
@st.cache_data(ttl=15)
def get_market_df():
    try:
        res = requests.get("https://data-api.binance.vision/api/v3/ticker/24hr", timeout=5).json()
        df = pd.DataFrame(res)
        df = df[df['symbol'].str.endswith('USDT')]
        df[['lastPrice', 'priceChangePercent', 'quoteVolume']] = df[['lastPrice', 'priceChangePercent', 'quoteVolume']].astype(float)
        return df
    except: return pd.DataFrame()

market_df = get_market_df()

def get_price(symbol):
    if not market_df.empty and symbol in market_df['symbol'].values:
        return market_df[market_df['symbol'] == symbol]['lastPrice'].values[0]
    try:
        r = requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbol={symbol}", timeout=2).json()
        return float(r['price'])
    except: return 0.0

# ==========================================
# 4. 实时总权益计算 (Header 逻辑)
# ==========================================
current_total_pnl = 0.0
current_total_margin = 0.0
for p in st.session_state.positions:
    now_p = get_price(p['交易对']) or p['开仓价']
    pnl = (now_p - p['开仓价']) / p['开仓价'] * p['名义价值'] if p['方向'] == "多" else (p['开仓价'] - now_p) / p['开仓价'] * p['名义价值']
    current_total_pnl += pnl
    current_total_margin += p['占用保证金']
    p['temp_pnl'] = pnl # 暂存盈亏供显示

net_equity = st.session_state.balance + current_total_margin + current_total_pnl

# ==========================================
# 5. 顶置 UI 看板
# ==========================================
c_u, c_s = st.columns([7, 2])
with c_u: st.markdown(f"**{st.session_state.username}** · 专业模式")
with c_s:
    with st.popover("⚙️"):
        if st.button("🔄 重置账户"):
            st.session_state.update({"balance": 5000000.0, "positions": [], "history": [], "favorites": []})
            sync_data(); st.rerun()
        if st.button("🚪 安全退出"):
            st.query_params.clear(); st.session_state.clear(); st.rerun()

st.markdown(f"""
<div class="balance-header">
    <div class="text-secondary">实时总权益估值 (USDT)</div>
    <div style="font-size: 2.2rem; font-weight: 600; color: #1D1D1F;">{net_equity:,.2f}</div>
    <div style="display:flex; justify-content:center; gap:15px; margin-top:5px; font-size:0.8rem;">
        <span class="text-secondary">可用余额: <b style="color:#1D1D1F">{st.session_state.balance:,.2f}</b></span>
        <span class="text-secondary">当前盈亏: <b class="{'price-up' if current_total_pnl>=0 else 'price-down'}">{current_total_pnl:+.2f}</b></span>
    </div>
</div>
""", unsafe_allow_html=True)

# DeepSeek 助理
with st.container():
    st.markdown('<div class="ai-box">🤖 <b>DeepSeek 智能投顾</b>', unsafe_allow_html=True)
    a1, a2 = st.columns([4, 1])
    u_q = a1.text_input("向 AI 咨询行情或建议...", key="ds_q", label_visibility="collapsed")
    if a2.button("发送", use_container_width=True) and u_q:
        try:
            sys_msg = f"你是中文专家。当前用户总资产:{net_equity:.0f}U。行情:{market_df.head(2).to_string()}。简短专业。"
            headers = {"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"}
            payload = {"model": "deepseek-chat", "messages": [{"role": "system", "content": sys_msg}, {"role": "user", "content": u_q}]}
            res = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=12)
            st.session_state.chat_history.append({"role": "user", "content": u_q})
            st.session_state.chat_history.append({"role": "assistant", "content": res.json()['choices'][0]['message']['content']})
        except: st.error("AI 繁忙")
    if st.session_state.chat_history:
        for m in st.session_state.chat_history[-2:]:
            with st.chat_message(m["role"]): st.markdown(m["content"])
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 6. 功能标签页
# ==========================================
tabs = st.tabs(["📊 行情", "📈 交易", "💼 持仓", "📜 历史"])

with tabs[0]:
    m_sub = st.tabs(["⭐ 自选", "🔥 涨幅榜", "💎 主流", "🆕 新币", "🌐 DEX"])
    def render_list(df, tag):
        if df.empty: st.caption("载入中..."); return
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
    with m_sub[0]: render_list(market_df[market_df['symbol'].isin(st.session_state.favorites)], "fav")
    with m_sub[1]: render_list(market_df.sort_values('priceChangePercent', ascending=False).head(20), "gain")
    with m_sub[2]: render_list(market_df.sort_values('quoteVolume', ascending=False).head(15), "main")
    with m_sub[3]: render_list(market_df.tail(15), "new")
    with m_sub[4]: render_list(market_df[market_df['symbol'].isin(["UNIUSDT","CAKEUSDT","SUSHIUSDT","AAVEUSDT"])], "dex")

with tabs[1]:
    all_syms = market_df['symbol'].tolist() if not market_df.empty else ["BTCUSDT"]
    target = st.selectbox("资产选择", all_syms, index=all_syms.index("BTCUSDT") if "BTCUSDT" in all_syms else 0)
    st.components.v1.html(f"""
        <div id="tv" style="height:320px; border-radius:18px; overflow:hidden; border:1px solid #E5E5E7;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize":true,"symbol":"BINANCE:{target}","interval":"1","theme":"light","style":"1","hide_top_toolbar":true,"container_id":"tv"}});</script>
    """, height=320)
    st.markdown(f"**现金余额: {st.session_state.balance:,.2f} USDT**")
    # 🌟 独立双滑块
    act_m = st.slider("1. 投入本金 (保证金)", 0.0, float(st.session_state.balance), float(st.session_state.balance * 0.1), step=100.0)
    lev = st.slider("2. 选择杠杆倍数", 1, 1000, 100)
    not_v = act_m * lev
    st.markdown(f"<div style='background:#F2F2F7; padding:12px; border-radius:12px; margin-bottom:15px;'>成交估值: <b style='color:#007AFF;'>{not_v:,.2f} U</b></div>", unsafe_allow_html=True)
    cb1, cb2 = st.columns(2)
    with cb1:
        if st.button("做多 (Long) 🟢", use_container_width=True, type="primary"):
            p = get_price(target)
            if p > 0 and st.session_state.balance >= act_m:
                st.session_state.balance -= act_m
                st.session_state.positions.append({"交易对":target,"方向":"多","开仓价":p,"杠杆":lev,"名义价值":not_v,"占用保证金":act_m})
                sync_data(); st.success(f"做多已成交: {p}"); time.sleep(0.5); st.rerun()
    with cb2:
        if st.button("做空 (Short) 🔴", use_container_width=True):
            p = get_price(target)
            if p > 0 and st.session_state.balance >= act_m:
                st.session_state.balance -= act_m
                st.session_state.positions.append({"交易对":target,"方向":"空","开仓价":p,"杠杆":lev,"名义价值":not_v,"占用保证金":act_m})
                sync_data(); st.success(f"做空已成交: {p}"); time.sleep(0.5); st.rerun()

with tabs[2]:
    if not st.session_state.positions: st.info("暂无持仓")
    else:
        for i, pos in enumerate(st.session_state.positions):
            pnl = pos.get('temp_pnl', 0.0)
            now_p = get_price(pos['交易对']) or pos['开仓价']
            with st.container():
                st.markdown(f"""<div class="apple-card"><div style="display:flex; justify-content:space-between;"><b>{pos['交易对']} · {pos['杠杆']}x</b><span class="{'price-up' if pnl>=0 else 'price-down'}">{pnl:+.2f} U</span></div></div>""", unsafe_allow_html=True)
                m1, m2 = st.columns(2)
                with m1:
                    if st.button("全平结算", key=f"cl_{i}", use_container_width=True):
                        st.session_state.history.insert(0, {"时间": datetime.now().strftime("%H:%M"), "币种": pos['交易对'], "方向": pos['方向'], "盈亏": round(pnl, 2), "价格": now_p})
                        st.session_state.balance += (pos['占用保证金'] + pnl); st.session_state.positions.pop(i); sync_data(); st.rerun()
                with m2:
                    with st.popover("调仓 (加/减)"):
                        # 🌟 减仓逻辑核心优化
                        adj = st.slider("调整金额", 0.0, float(max(st.session_state.balance, pos['占用保证金'])), 500.0, key=f"as_{i}")
                        c_a, c_r = st.columns(2)
                        if c_a.button("补仓"):
                            if st.session_state.balance >= adj:
                                st.session_state.balance -= adj
                                pos['名义价值'] += (adj * pos['杠杆']); pos['占用保证金'] += adj; sync_data(); st.rerun()
                        if c_r.button("减仓", type="primary"):
                            ratio = min(adj / pos['占用保证金'], 1.0) if pos['占用保证金'] > 0 else 0
                            returned = (pos['占用保证金'] * ratio) + (pnl * ratio)
                            st.session_state.history.insert(0, {"时间": datetime.now().strftime("%H:%M"), "币种": pos['交易对'], "方向": f"减-{pos['方向']}", "盈亏": round(pnl * ratio, 2), "价格": now_p})
                            st.session_state.balance += returned # 资金回流
                            pos['名义价值'] *= (1-ratio); pos['占用保证金'] *= (1-ratio)
                            if pos['名义价值'] < 1: st.session_state.positions.pop(i)
                            sync_data(); st.rerun() # 🌟 强制刷新，让顶部看板重算权益

with tabs[3]:
    st.markdown("#### 📜 成交流水")
    for h in st.session_state.history[:30]:
        st.markdown(f"""<div style="padding:15px; border-bottom:1px solid #EEE; display:flex; justify-content:space-between; align-items:center;"><div><b>{h['币种']} · {h['方向']}</b><div style="font-size:11px; color:#8E8E93;">{h['时间']} | {h['价格']}</div></div><div class="{'price-up' if h['盈亏']>=0 else 'price-down'}">{h['盈亏']:+.2f} U</div></div>""", unsafe_allow_html=True)
