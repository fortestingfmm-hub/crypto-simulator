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

st.markdown("""
<style>
    .block-container { padding-top: 3.5rem; padding-bottom: 5rem; }
    .balance-text { font-size: 1.8rem; font-weight: bold; color: #0ecb81; margin-bottom: 10px; }
    .title-text { font-size: 1.5rem; font-weight: bold; color: #fff; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 本地数据库引擎
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
                    db["users"][r_user] = {"password": hash_password(r_pass), "balance": 5000000.0, "positions": []}
                    save_db(db)
                    st.success("注册成功！请切换到【登录】面板进行登录。")
    st.stop() 

# ==========================================
# 3. 核心网络引擎 (专为国内网络环境优化)
# ==========================================
def reset_balance():
    st.session_state.balance = 5000000.0
    st.session_state.positions = []
    sync_current_user_data() 
    st.toast("✅ 资金已重置为 5,000,000 USDT！", icon="💰")

def logout():
    st.session_state.clear()
    st.rerun()

# 节点列表：首选对国内友好的 MEXC 接口，其次是币安备用节点
API_NODES = ['https://api.mexc.com', 'https://data-api.binance.vision']

@st.cache_data(ttl=3600) 
def get_all_usdt_symbols():
    """获取全市场币种（缓存1小时，极度节省网络请求）"""
    for url in API_NODES:
        try:
            res = requests.get(f"{url}/api/v3/exchangeInfo", timeout=8)
            data = res.json()
            symbols = [s['symbol'] for s in data['symbols'] if s['symbol'].endswith('USDT') and s['status'] in ['TRADING', 'ENABLED']]
            main_coins = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT"]
            return main_coins + [s for s in symbols if s not in main_coins]
        except:
            continue
    return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"] # 极限断网保底

all_symbols = get_all_usdt_symbols()

def get_single_price(symbol):
    """下单瞬间精准获取单币价格（带重试机制）"""
    for url in API_NODES:
        try:
            res = requests.get(f"{url}/api/v3/ticker/price?symbol={symbol}", timeout=5)
            if res.status_code == 200:
                return float(res.json().get('price', 0))
        except:
            continue
    return 0.0

# ==========================================
# 4. 顶部导航、全局余额与 AI
# ==========================================
col_title, col_ai, col_exit = st.columns([5, 2, 2])
with col_title:
    st.markdown('<div class="title-text">⚡ Crypto 模拟引擎</div>', unsafe_allow_html=True)
with col_ai:
    with st.popover("🤖 AI", use_container_width=True):
        api_key = st.text_input("DeepSeek Key", type="password")
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

st.caption(f"交易员：**{st.session_state.username}**")
st.markdown(f'<div class="balance-text">💰 余额: {st.session_state.balance:,.2f} U</div>', unsafe_allow_html=True)
st.divider()

# ==========================================
# 5. 移动端优化三大核心板块
# ==========================================
tab_market, tab_trade, tab_assets = st.tabs(["📊 行情", "📈 交易", "💼 资产持仓"])

# --- 模块 1：全市场行情 (放宽至 8 秒刷新，极度抗网络波动) ---
@st.fragment(run_every=8)
def render_market_tab():
    success = False
    for url in API_NODES:
        try:
            res = requests.get(f"{url}/api/v3/ticker/24hr", timeout=6)
            if res.status_code == 200 and isinstance(res.json(), list):
                data = res.json()
                usdt_data = [d for d in data if d['symbol'].endswith('USDT')]
                
                # 兼容不同API的字段命名差异
                sort_key = 'quoteVolume' if 'quoteVolume' in usdt_data[0] else 'volume'
                usdt_data.sort(key=lambda x: float(x.get(sort_key, 0)), reverse=True)
                
                market_list = []
                for item in usdt_data[:150]: 
                    coin = item['symbol'].replace("USDT", "")
                    market_list.append({
                        "币种": f"{coin}/USDT", 
                        "最新价($)": round(float(item['lastPrice']), 6), 
                        "涨跌幅": f"{float(item['priceChangePercent']):.2f}%"
                    })
                st.caption(f"🔄 行情已更新 (当前节点: {'主节点' if 'mexc' in url else '备用节点'})")
                st.dataframe(pd.DataFrame(market_list), use_container_width=True, hide_index=True)
                success = True
                break
        except:
            continue
            
    if not success:
        st.warning("📡 当前网络拥堵，正在等待下一轮数据拉取...")

with tab_market:
    render_market_tab()

# --- 模块 2：交易面板 ---
with tab_trade:
    tv_symbol = st.selectbox("选择交易对", all_symbols, format_func=lambda x: x.replace("USDT", "/USDT"), label_visibility="collapsed")
    
    #  TradingView 图表（TV 的国内连通率一般还可以，如果图出不来，建议挂一下后台梯子）
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
                sync_current_user_data() 
                st.toast(f"✅ 做多 {tv_symbol} 成功！")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("失败：余额不足或网络拥堵未获取到价格")
    with col_sell:
        if st.button("🔴 做空 (Short)", use_container_width=True):
            price = get_single_price(tv_symbol)
            if price > 0 and st.session_state.balance >= margin_req:
                st.session_state.balance -= margin_req
                st.session_state.positions.append({"方向": "做空 🔴", "交易对": tv_symbol, "杠杆": leverage, "名义价值": amount, "占用保证金": margin_req, "开仓价": price})
                sync_current_user_data() 
                st.toast(f"✅ 做空 {tv_symbol} 成功！")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("失败：余额不足或网络拥堵未获取到价格")

# --- 模块 3：资产与持仓 (放宽至 5 秒自动结算，减少卡顿) ---
@st.fragment(run_every=5)
def render_positions_and_pnl():
    if not st.session_state.positions:
        st.info("📦 当前暂无持仓")
        return

    # 拉取当前持仓的最新价 (带重试引擎)
    prices_dict = {}
    for url in API_NODES:
        try:
            res = requests.get(f"{url}/api/v3/ticker/price", timeout=4)
            if res.status_code == 200:
                for item in res.json():
                    prices_dict[item['symbol']] = float(item['price'])
                break # 获取成功直接跳出循环
        except:
            continue

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
            continue 
        
        pos["当前价"] = current_price
        pos["未实现盈亏"] = pnl
        active_positions.append(pos)
        
    if len(active_positions) != len(st.session_state.positions):
        st.session_state.positions = active_positions
        sync_current_user_data()
    else:
        st.session_state.positions = active_positions

    st.caption("🔄 持仓盈亏后台自动核算中...")
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
                sync_current_user_data() 
                st.toast(f"✅ 平仓结算成功！", icon="💸")
                time.sleep(0.5)
                st.rerun()
            else:
                st.toast("当前无持仓", icon="ℹ️")
                
    st.divider()
    render_positions_and_pnl()
