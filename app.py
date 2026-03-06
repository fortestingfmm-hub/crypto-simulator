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
# 0. UI 配置 - Apple 极简白 (100% 沉浸式静默)
# ==========================================
st.set_page_config(page_title="Crypto Terminal Pro", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;600&display=swap');
    html, body, [data-testid="stAppViewContainer"] { background-color: #F5F5F7; font-family: 'SF Pro Display', sans-serif; color: #1D1D1F; }
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    .apple-card { background: #FFFFFF; border-radius: 20px; padding: 18px; margin-bottom: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.03); border: 1px solid rgba(0,0,0,0.01); }
    .balance-header { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border-radius: 24px; padding: 20px; text-align: center; margin-bottom: 15px; border: 1px solid rgba(0,0,0,0.05); }
    .ai-box { background: #FFFFFF; border-radius: 18px; padding: 15px; margin-bottom: 15px; border-left: 5px solid #007AFF; box-shadow: 0 4px 12px rgba(0,0,0,0.02); }
    .price-up { color: #34C759 !important; font-weight: 600; }
    .price-down { color: #FF3B30 !important; font-weight: 600; }
    .stButton>button { border-radius: 12px; background-color: #007AFF; color: white; font-weight: 600; border: none; }
    
    /* 屏蔽所有加载指示器 */
    header { visibility: hidden; } footer { visibility: hidden; }
    div[data-testid="stStatusWidget"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    .stSpinner { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 核心持久化引擎 (锁定文件名)
# ==========================================
DEEPSEEK_KEY = "sk-9de5a0aa88744f7d94fc2a3a6b140f75"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DATA_FILE = "trading_permanent_data.json"

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
        db = load_db()
        u = st.session_state.username
        if u in db["users"]:
            db["users"][u].update({
                "balance": st.session_state.balance, "positions": st.session_state.positions,
                "history": st.session_state.get("history", []), "favorites": st.session_state.get("favorites", [])
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
                "logged_in": True, "username": user, "balance": info.get("balance", 5000000.0),
                "positions": info.get("positions", []), "history": info.get("history", []), "favorites": info.get("favorites", [])
            })
            break

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align:center;'>Terminal Pro</h2>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["安全登录", "快速开户"])
    with t1:
        with st.form("l_f"):
            u = st.text_input("用户名").strip()
            p = st.text_input("密码", type="password").strip()
            if st.form_submit_button("进入终端", use_container_width=True):
                hp = hashlib.sha256(p.encode()).hexdigest()
                db = load_db()
                if u in db["users"] and db["users"][u]["password"] == hp:
                    tk = db["users"][u].get("session_token") or str(uuid.uuid4())
                    db["users"][u]["session_token"] = tk; save_db(db); st.query_params["token"] = tk
                    st.session_state.update({"logged_in": True, "username": u, "balance": db["users"][u]["balance"], "positions": db["users"][u]["positions"], "history": db["users"][u].get("history", []), "favorites": db["users"][u].get("favorites", [])})
                    st.rerun()
                else: st.error("登录失败")
    with t2:
        with st.form("r_f"):
            nu = st.text_input("设置用户名").strip()
            np = st.text_input("设置密码", type="password").strip()
            if st.form_submit_button("注册新账户"):
                db = load_db()
                if nu in db["users"]: st.error("已占用")
                elif nu and np:
                    db["users"][nu] = {"password": hashlib.sha256(np.encode()).hexdigest(), "balance": 5000000.0, "positions": [], "history": [], "favorites": []}
                    save_db(db); st.success("开户成功！")
    st.stop()

# ==========================================
# 3. 极速行情快照
# ==========================================
@st.cache_data(ttl=1)
def get_market_snapshot():
    try:
        res = requests.get("https://data-api.binance.vision/api/v3/ticker/24hr", timeout=1.5).json()
        df = pd.DataFrame(res)
        df = df[df['symbol'].str.endswith('USDT')]
        df[['lastPrice', 'priceChangePercent', 'quoteVolume']] = df[['lastPrice', 'priceChangePercent', 'quoteVolume']].astype(float)
        return df
    except: return pd.DataFrame()

# ==========================================
# 4. 局部静默刷新碎片 (Fragments)
# ==========================================

@st.fragment(run_every=1)
def fragment_equity_board():
    m_df = get_market_snapshot()
    total_pnl = 0.0
    total_margin = 0.0
    for p in st.session_state.positions:
        now_p = m_df[m_df['symbol'] == p['交易对']]['lastPrice'].values[0] if not m_df.empty and p['交易对'] in m_df['symbol'].values else p['开仓价']
        pnl = (now_p - p['开仓价']) / p['开仓价'] * p['名义价值'] if p['方向'] == "多" else (p['开仓价'] - now_p) / p['开仓价'] * p['名义价值']
        total_pnl += pnl; total_margin += p['占用保证金']
    
    st.markdown(f"""
    <div class="balance-header">
        <div class="text-secondary">实时总权益净值 (USDT)</div>
        <div style="font-size: 2.2rem; font-weight: 600; color: #1D1D1F; letter-spacing: -1.2px;">{st.session_state.balance + total_margin + total_pnl:,.2f}</div>
        <div style="display:flex; justify-content:center; gap:15px; margin-top:5px; font-size:0.8rem;">
            <span>可用现金: <b>{st.session_state.balance:,.2f}</b></span>
            <span class="{'price-up' if total_pnl>=0 else 'price-down'}">未实现盈亏: {total_pnl:+.2f}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 5. 主页面渲染
# ==========================================
c_u, c_s = st.columns([7, 2])
with c_u: st.markdown(f"**{st.session_state.username}** · 终端模式")
with c_s:
    with st.popover("⚙️"):
        if st.button("🔄 重置"): st.session_state.update({"balance":5000000.0,"positions":[],"history":[]}); sync_data(); st.rerun()
        if st.button("🚪 退出"): st.query_params.clear(); st.session_state.clear(); st.rerun()

fragment_equity_board()

# AI 投顾
with st.container():
    st.markdown('<div class="ai-box">🤖 <b>DeepSeek 智能投顾</b>', unsafe_allow_html=True)
    a1, a2 = st.columns([4, 1])
    u_q = a1.text_input("向 AI 咨询行情建议...", key="ds_input", label_visibility="collapsed")
    if a2.button("发送", use_container_width=True) and u_q:
        try:
            sys_msg = "你是中文专家。简短专业建议。"
            headers = {"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"}
            payload = {"model": "deepseek-chat", "messages": [{"role":"system","content":sys_msg}, {"role":"user","content":u_q}]}
            res = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=10)
            st.session_state.chat_history.append({"role": "user", "content": u_q})
            st.session_state.chat_history.append({"role": "assistant", "content": res.json()['choices'][0]['message']['content']})
        except: st.error("AI 忙碌")
    if st.session_state.chat_history:
        for m in st.session_state.chat_history[-2:]:
            with st.chat_message(m["role"]): st.markdown(m["content"])
    st.markdown('</div>', unsafe_allow_html=True)

tabs = st.tabs(["📊 行情分类", "📈 极速交易", "💼 仓位管理", "📜 历史记录"])

# --- Tab 0: 恢复后的分类行情 ---
with tabs[0]:
    m_tabs = st.tabs(["⭐ 自选", "🔥 涨幅榜", "💎 主流", "🆕 新币", "🌐 DEX"])
    m_df = get_market_snapshot()
    
    def render_market_list(df_subset, tag):
        if df_subset.empty: 
            st.caption("暂无数据")
            return
        for _, r in df_subset.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([1, 4, 3])
                is_fav = r['symbol'] in st.session_state.favorites
                if c1.button("⭐" if is_fav else "☆", key=f"f_{tag}_{r['symbol']}"):
                    if is_fav: st.session_state.favorites.remove(r['symbol'])
                    else: st.session_state.favorites.append(r['symbol'])
                    sync_data(); st.rerun()
                c2.markdown(f"**{r['symbol'].replace('USDT','')}**")
                up = r['priceChangePercent'] >= 0
                c3.markdown(f"<div style='text-align:right'><b>${r['lastPrice']:.2f}</b><br><span class='{'price-up' if up else 'price-down'}'>{r['priceChangePercent']:+.2f}%</span></div>", unsafe_allow_html=True)

    with m_tabs[0]: # 自选
        render_market_list(m_df[m_df['symbol'].isin(st.session_state.favorites)], "fav")
    with m_tabs[1]: # 涨幅榜
        render_market_list(m_df.sort_values('priceChangePercent', ascending=False).head(20), "gain")
    with m_tabs[2]: # 主流币 (按成交量前15)
        render_market_list(m_df.sort_values('quoteVolume', ascending=False).head(15), "main")
    with m_tabs[3]: # 新币 (取列表底部 15 个，模拟币安新上线顺序)
        render_market_list(m_df.tail(15), "new")
    with m_tabs[4]: # DEX
        dex_set = ["UNIUSDT","CAKEUSDT","SUSHIUSDT","AAVEUSDT","CRVUSDT","RAYUSDT","JOEUSDT","1INCHUSDT"]
        render_market_list(m_df[m_df['symbol'].isin(dex_set)], "dex")

# --- Tab 1: 极速交易 ---
with tabs[1]:
    all_syms = m_df['symbol'].tolist() if not m_df.empty else ["BTCUSDT"]
    target = st.selectbox("选择资产", all_syms, index=all_syms.index("BTCUSDT") if "BTCUSDT" in all_syms else 0)
    st.components.v1.html(f"""
        <div id="tv" style="height:320px; border-radius:18px; overflow:hidden; border:1px solid #E5E5E7;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize":true,"symbol":"BINANCE:{target}","interval":"1","theme":"light","style":"1","hide_top_toolbar":true,"container_id":"tv"}});</script>
    """, height=320)
    st.markdown(f"**现金可用: {st.session_state.balance:,.2f} USDT**")
    act_m = st.slider("1. 投入保证金 (USDT)", 0.0, float(st.session_state.balance), float(st.session_state.balance * 0.1), step=100.0)
    lev = st.slider("2. 选择杠杆倍数", 1, 1000, 100)
    st.markdown(f"<div style='background:#F2F2F7; padding:15px; border-radius:12px; margin-bottom:15px;'>成交估值: <b style='color:#007AFF;'>{act_m * lev:,.2f} U</b></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("做多 🟢", use_container_width=True, type="primary"):
            p = m_df[m_df['symbol']==target]['lastPrice'].values[0] if not m_df.empty else 0.0
            if p > 0 and st.session_state.balance >= act_m:
                st.session_state.balance -= act_m
                st.session_state.positions.append({"交易对":target,"方向":"多","开仓价":p,"杠杆":lev,"名义价值":act_m*lev,"占用保证金":act_m})
                sync_data(); st.success(f"已开多: {p}"); time.sleep(0.5); st.rerun()
    with c2:
        if st.button("做空 🔴", use_container_width=True):
            p = m_df[m_df['symbol']==target]['lastPrice'].values[0] if not m_df.empty else 0.0
            if p > 0 and st.session_state.balance >= act_m:
                st.session_state.balance -= act_m
                st.session_state.positions.append({"交易对":target,"方向":"空","开仓价":p,"杠杆":lev,"名义价值":act_m*lev,"占用保证金":act_m})
                sync_data(); st.success(f"已开空: {p}"); time.sleep(0.5); st.rerun()

# --- Tab 2: 仓位管理 (局部刷新) ---
@st.fragment(run_every=2)
def fragment_positions():
    if not st.session_state.positions: st.info("暂无持仓")
    else:
        m_df = get_market_snapshot()
        for i, pos in enumerate(st.session_state.positions):
            now_p = m_df[m_df['symbol'] == pos['交易对']]['lastPrice'].values[0] if not m_df.empty and pos['交易对'] in m_df['symbol'].values else pos['开仓价']
            pnl = (now_p - pos['开仓价']) / pos['开仓价'] * pos['名义价值'] if pos['方向'] == "多" else (pos['开仓价'] - now_p) / pos['开仓价'] * pos['名义价值']
            with st.container():
                st.markdown(f"""<div class="apple-card"><div style="display:flex; justify-content:space-between;"><b>{pos['交易对']} · {pos['杠杆']}x</b><span class="{'price-up' if pnl>=0 else 'price-down'}">{pnl:+.2f} U</span></div></div>""", unsafe_allow_html=True)
                ca, cb = st.columns(2)
                with ca:
                    if st.button("全平", key=f"cl_{i}", use_container_width=True):
                        st.session_state.history.insert(0, {"时间": datetime.now().strftime("%H:%M"), "币种": pos['交易对'], "方向": pos['方向'], "盈亏": round(pnl, 2), "价格": now_p})
                        st.session_state.balance += (pos['占用保证金'] + pnl); st.session_state.positions.pop(i); sync_data(); st.rerun()
                with cb:
                    with st.popover("调仓"):
                        adj = st.slider("金额", 0.0, float(max(st.session_state.balance, 100)), 500.0, key=f"as_{i}")
                        if st.button("加仓", key=f"ad_{i}"):
                            if st.session_state.balance >= adj:
                                st.session_state.balance -= adj; pos['名义价值'] += (adj * pos['杠杆']); pos['占用保证金'] += adj; sync_data(); st.rerun()
                        if st.button("减仓", key=f"re_{i}", type="primary"):
                            ratio = min(adj/pos['占用保证金'], 1.0) if pos['占用保证金']>0 else 0
                            st.session_state.balance += (pos['占用保证金']*ratio + pnl*ratio)
                            pos['名义价值'] *= (1-ratio); pos['占用保证金'] *= (1-ratio)
                            if pos['名义价值'] < 1: st.session_state.positions.pop(i)
                            sync_data(); st.rerun()

with tabs[2]:
    fragment_positions()

with tabs[3]:
    st.markdown("#### 📜 历史记录")
    for h in st.session_state.history[:30]:
        st.markdown(f"""<div style="padding:15px; border-bottom:1px solid #EEE; display:flex; justify-content:space-between; align-items:center;"><div><b>{h['币种']} · {h['方向']}</b><div style="font-size:11px; color:#8E8E93;">{h['时间']} | {h['价格']}</div></div><div class="{'price-up' if h['盈亏']>=0 else 'price-down'}">{h['盈亏']:+.2f} U</div></div>""", unsafe_allow_html=True)
