import streamlit as st
import pandas as pd
import requests
import time
import json
import os
import hashlib
from openai import OpenAI

# ==========================================
# 0. 页面全局配置 (适配手机端)
# ==========================================
st.set_page_config(page_title="Crypto 模拟终端", layout="centered", initial_sidebar_state="collapsed")

# 1. 修复顶部被挡住的问题 (加大 padding-top)
st.markdown("""
<style>
    .block-container { padding-top: 3.5rem; padding-bottom: 5rem; }
    .balance-text { font-size: 1.8rem; font-weight: bold; color: #0ecb81; margin-bottom: 10px; }
    .title-text { font-size: 1.5rem; font-weight: bold; color: #fff; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 本地数据库引擎 (JSON 持久化)
# ==========================================
DATA_FILE = "trading_data.json"

def load_db():
    if not os.path.exists(DATA_FILE):
        return {"users": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def sync_current_user_data():
    """将当前 session 的资金和持仓同步保存到数据库"""
    if st.session_state.get('logged_in'):
        db = load_db()
        username = st.session_state.username
        db["users"][username]["balance"] = st.session_state.balance
        db["users"][username]["positions"] = st.session_state.positions
        save_db(db)

# ==========================================
# 2. 账号注册与登录系统
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown('<div class="title-text">⚡ Crypto 模拟引擎系统</div>', unsafe_allow_html=True)
    st.caption("请先登录或注册账号以保存您的交易数据")
    
    tab_login, tab_register = st.tabs(["🔑 登录", "📝 注册新账号"])
    
    with tab_login:
        with st.form("login_form"):
            l_user = st.text_input("用户名")
            l_pass = st.text_input("密码", type="password")
            submit_login = st.form_submit_button("登 录", use_container_width=True)
            
            if submit_login:
                db = load_db()
                if l_user in db["users"] and db["users"][l_user]["password"] == hash_password(l_pass):
                    st.session_state.logged_in = True
                    st.session_state.username = l_user
                    st.session_state.balance = db["users"][l_user]["balance"]
                    st.session_state.positions = db["users"][l_user]["positions"]
                    st.session_state.chat_history = []
                    st.session_state.market_summary = "暂无最新行情"
                    st.success("登录成功！正在进入交易终端...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("用户名或密码错误！")
                    
    with tab_register:
        with st.form("register_form"):
            r_user = st.text_input("设置用户名")
            r_pass = st.text_input("设置密码", type="password")
            submit_register = st.form_submit_button("注 册", use_container_width=True)
            
            if submit_register:
                db = load_db()
                if not r_user or not r_pass:
                    st.warning("用户名和密码不能为空！")
                elif r_user in db["users"]:
                    st.error("该用户名已被注册，请换一个！")
                else:
                    db["users"][r_user] = {
                        "password": hash_password(r_pass),
                        "balance": 5000000.0, # 初始资金
                        "positions": []
                    }
                    save_db(db)
                    st.success("注册成功！请切换到【登录】面板进行登录。")
                    
    st.stop() # 阻断后续代码运行，直到用户登录成功

# ==========================================
# 3. 核心功能 (仅登录后可见)
# ==========================================
def reset_balance():
    st.session_state.balance = 5000000.0
    st.session_state.positions = []
    sync_current_user_data() # 同步到数据库
    st.toast("✅ 资金已重置为 5,000,000 USDT，并保存至云端！", icon="💰")

def logout():
    st.session_state.clear()
    st.rerun()

@st.cache_data(ttl=600) 
def get_all_usdt_symbols():
    try:
        res = requests.get("https://data-api.binance.vision/api/v3/exchangeInfo", timeout=5)
        data = res.json()
        symbols = [s['symbol'] for s in data['symbols'] if s['symbol'].endswith('USDT') and s['status'] == 'TRADING']
        main_coins = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT", "XRPUSDT"]
        others = [s for s in symbols if s not in main_coins]
        return main_coins + others
    except:
        return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"] 

all_symbols = get_all_usdt_symbols()

def get_single_price(symbol):
    try:
        res = requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbol={symbol}", timeout=3)
        return float(res.json().get('price', 0))
    except:
        return 0.0

# ==========================================
# 4. 顶部导航、全局余额与 AI
# ==========================================
col_title, col_ai, col_exit = st.columns([5, 2, 2])
with col_title:
    st.markdown('<div class="title-text">⚡ Crypto 模拟引擎</div>', unsafe_allow_html=True)
with col_ai:
    with st.popover("🤖 AI", use_container_width=True):
        api_key = st.text_input("DeepSeek Key", type="password", placeholder="填入 API Key")
        user_input = st.chat_input("向 AI 提问...")
        if user_input and api_key:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            try:
                client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
                prompt = "你是交易顾问。简短回答，提醒风险。"
                messages = [{"role": "system", "content": prompt}] + st.session_state.chat_history
                resp = client.chat.completions.create(model="deepseek-chat", messages=messages, stream=True)
                full_res = st.write_stream(resp)
                st.session_state.chat_history.append({"role": "assistant", "content": full_res})
            except:
                st.error("API 异常")
with col_exit:
    if st.button("🚪 退出", use_container_width=True):
        logout()

# 🚨 全局高亮余额展示
st.caption(f"欢迎回来，交易员：**{st.session_state.username}**")
st.markdown(f'<div class="balance-text">💰 余额: {st.session_state.balance:,.2f} U</div>', unsafe_allow_html=True)
st.divider()

# ==========================================
# 5. 移动端优化三大核心板块
# ==========================================
tab_market, tab_trade, tab_assets = st.tabs(["📊 行情", "📈 交易", "💼 资产与持仓"])

@st.fragment(run_every=3)
def render_market_tab():
    try:
        res = requests.get("https://data-api.binance.vision/api/v3/ticker/24hr", timeout=3)
        data = res.json()
        usdt_data = [d for d in data if d['symbol'].endswith('USDT')]
        usdt_data.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        
        market_list = []
        for item in usdt_data[:150]: 
            coin = item['symbol'].replace("USDT", "")
            market_list.append({
                "全市场币种": f"{coin}/USDT", 
                "最新价($)": round(float(item['lastPrice']), 6), 
                "24h涨跌": f"{float(item['priceChangePercent']):.2f}%"
            })
        st.caption("🔄 行情每 3 秒自动更新 (按全网成交量排序)")
        st.dataframe(pd.DataFrame(market_list), use_container_width=True, hide_index=True)
    except:
        st.error("网络异常，拉取全市场行情失败。")

with tab_market:
    render_market_tab()

with tab_trade:
    tv_symbol = st.selectbox("选择交易对", all_symbols, format_func=lambda x: x.replace("USDT", "/USDT"), label_visibility="collapsed")
    
    st.components.v1.html(
        f"""
        <div class="tradingview-widget-container" style="height:350px;width:100%">
          <div id="tv_{tv_symbol}" style="height:calc(100% - 32px);width:100%"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget({{"autosize": true, "symbol": "BINANCE:{tv_symbol}", "interval": "1", "theme": "dark", "style": "1", "hide_top_toolbar": true, "backgroundColor": "#0E1117", "container_id": "tv_{tv_symbol}"}});
        </script></div>
        """, height=350
    )
    
    st.markdown("#### ⚡ 极速开仓 (1x - 1000x)")
    leverage = st.slider("杠杆倍数", 1, 1000, 100, label_visibility="collapsed")
    amount = st.number_input("开仓名义价值 (U)", min_value=10.0, value=10000.0, step=1000.0)
    
    margin_req = amount / leverage
    st.caption(f"🛡️ 实际冻结保证金: **{margin_req:.2f} U**")
    
    col_buy, col_sell = st.columns(2)
    with col_buy:
        if st.button("🟢 做多 (Long)", use_container_width=True):
            price = get_single_price(tv_symbol)
            if price > 0 and st.session_state.balance >= margin_req:
                st.session_state.balance -= margin_req
                st.session_state.positions.append({"方向": "做多 🟢", "交易对": tv_symbol, "杠杆": leverage, "名义价值": amount, "占用保证金": margin_req, "开仓价": price})
                sync_current_user_data() # 落库保存
                st.toast(f"✅ 做多 {tv_symbol} 成功！数据已保存。")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("失败：余额不足或网络波动")
    with col_sell:
        if st.button("🔴 做空 (Short)", use_container_width=True):
            price = get_single_price(tv_symbol)
            if price > 0 and st.session_state.balance >= margin_req:
                st.session_state.balance -= margin_req
                st.session_state.positions.append({"方向": "做空 🔴", "交易对": tv_symbol, "杠杆": leverage, "名义价值": amount, "占用保证金": margin_req, "开仓价": price})
                sync_current_user_data() # 落库保存
                st.toast(f"✅ 做空 {tv_symbol} 成功！数据已保存。")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("失败：余额不足或网络波动")

@st.fragment(run_every=2)
def render_positions_and_pnl():
    if not st.session_state.positions:
        st.info("📦 当前暂无持仓")
        return

    symbols_needed = list(set([p['交易对'] for p in st.session_state.positions]))
    symbols_query = '["' + '","'.join(symbols_needed) + '"]'
    prices_dict = {}
    try:
        res = requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbols={symbols_query}", timeout=2)
        for item in res.json():
            prices_dict[item['symbol']] = float(item['price'])
    except:
        pass 

    active_positions = []
    for pos in st.session_state.positions:
        sym = pos["交易对"]
        current_price = prices_dict.get(sym, pos.get("当前价", pos["开仓价"]))
        
        if pos["方向"] == "做多 🟢":
            pnl = (current_price - pos["开仓价"]) / pos["开仓价"] * pos["名义价值"]
        else: 
            pnl = (pos["开仓价"] - current_price) / pos["开仓价"] * pos["名义价值"]
        
        if pnl <= -pos["占用保证金"]:
            st.error(f"🚨 爆仓！{sym} {pos['方向']} 遭强平！")
            sync_current_user_data() # 爆仓后立刻保存
            continue 
        
        pos["当前价"] = current_price
        pos["未实现盈亏"] = pnl
        active_positions.append(pos)
        
    # 如果因为爆仓导致仓位减少，同步数据库
    if len(active_positions) != len(st.session_state.positions):
        st.session_state.positions = active_positions
        sync_current_user_data()
    else:
        st.session_state.positions = active_positions

    st.caption("🔄 持仓盈亏每 2 秒自动跳动更新")
    for pos in active_positions:
        with st.container(border=True):
            pnl = pos["未实现盈亏"]
            pnl_color = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
            
            st.markdown(f"**{pos['交易对'].replace('USDT','/USDT')}** | {pos['方向']} | **{pos['杠杆']}x**")
            
            c1, c2 = st.columns(2)
            c1.metric("未实现盈亏 (U)", f"{pnl_color} {pnl:.2f}")
            c2.metric("收益率 (ROE)", f"{(pnl / pos['占用保证金'] * 100):.2f}%")
            
            c3, c4 = st.columns(2)
            c3.caption(f"开仓价: {pos['开仓价']:.6f}")
            c4.caption(f"当前价: {pos['当前价']:.6f}")
            c3.caption(f"保证金: {pos['占用保证金']:.2f}")
            c4.caption(f"名义价值: {pos['名义价值']:.2f}")

with tab_assets:
    col_reset, col_close = st.columns(2)
    with col_reset:
        st.button("🔄 重置资金", on_click=reset_balance, use_container_width=True)
    with col_close:
        if st.button("⚡ 一键全平", type="primary", use_container_width=True):
            if st.session_state.positions:
                total_return = sum([p["占用保证金"] + p.get("未实现盈亏", 0) for p in st.session_state.positions])
                st.session_state.balance += total_return
                st.session_state.positions = [] 
                sync_current_user_data() # 落库保存结算后的总资金
                st.toast(f"✅ 平仓结算成功！总资产已更新保存。", icon="💸")
                time.sleep(0.5)
                st.rerun()
            else:
                st.toast("当前无持仓", icon="ℹ️")
                
    st.divider()
    render_positions_and_pnl()
