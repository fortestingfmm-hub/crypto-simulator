import streamlit as st
import pandas as pd
import requests
import time
from openai import OpenAI

# ==========================================
# 0. 页面全局配置 (适配手机端)
# ==========================================
st.set_page_config(page_title="Crypto 模拟终端", layout="centered", initial_sidebar_state="collapsed")

# 优化手机端间距、大字号余额
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 5rem; }
    .balance-text { font-size: 1.8rem; font-weight: bold; color: #0ecb81; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 初始化系统状态
# ==========================================
if 'balance' not in st.session_state:
    st.session_state.balance = 5000000.0  
if 'positions' not in st.session_state:
    st.session_state.positions = []       
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'market_summary' not in st.session_state:
    st.session_state.market_summary = "暂无最新行情"

def reset_balance():
    st.session_state.balance = 5000000.0
    st.session_state.positions = []
    st.toast("✅ 资金已重置为 5,000,000 USDT！", icon="💰")

# ==========================================
# 2. 全市场币种获取 (缓存防卡顿)
# ==========================================
@st.cache_data(ttl=600) # 缓存10分钟，避免每次刷新重新拉取几千个币种列表
def get_all_usdt_symbols():
    """获取币安所有正在交易的 USDT 合约/现货全市场币种"""
    try:
        res = requests.get("https://data-api.binance.vision/api/v3/exchangeInfo", timeout=5)
        data = res.json()
        # 过滤出所有以 USDT 结尾且状态为 TRADING 的币种
        symbols = [s['symbol'] for s in data['symbols'] if s['symbol'].endswith('USDT') and s['status'] == 'TRADING']
        # 把主流币排在前面
        main_coins = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT", "XRPUSDT"]
        others = [s for s in symbols if s not in main_coins]
        return main_coins + others
    except:
        return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"] # 断网时的后备方案

all_symbols = get_all_usdt_symbols()

def get_single_price(symbol):
    """下单瞬间精准获取单币价格"""
    try:
        res = requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbol={symbol}", timeout=3)
        return float(res.json().get('price', 0))
    except:
        return 0.0

# ==========================================
# 3. 顶部导航、全局余额与 AI
# ==========================================
col_title, col_ai = st.columns([3, 1])
with col_title:
    st.markdown("### ⚡ Crypto 模拟引擎")
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

# 🚨 全局高亮余额显示，无论切到哪个 Tab 都能看到！
st.markdown(f'<div class="balance-text">💰 余额: {st.session_state.balance:,.2f} U</div>', unsafe_allow_html=True)
st.divider()

# ==========================================
# 4. 移动端优化三大核心板块
# ==========================================
tab_market, tab_trade, tab_assets = st.tabs(["📊 行情", "📈 交易", "💼 资产与持仓"])

# --- 模块 1：全市场行情 (使用 Fragment 实现每 3 秒无感自动刷新) ---
@st.fragment(run_every=3)
def render_market_tab():
    try:
        # 抓取全网 24h 行情
        res = requests.get("https://data-api.binance.vision/api/v3/ticker/24hr", timeout=3)
        data = res.json()
        # 过滤并排序（按成交量排名前 150，防止手机浏览器卡顿）
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

# --- 模块 2：交易面板 (图表与下单) ---
with tab_trade:
    # 下拉框现在支持全市场几千个币种！格式化显示为 BTC/USDT
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
                st.toast(f"✅ 做多 {tv_symbol} 成功！")
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
                st.toast(f"✅ 做空 {tv_symbol} 成功！")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("失败：余额不足或网络波动")

# --- 模块 3：资产与持仓 (使用 Fragment 实现每 2 秒无感自动结算盈亏) ---
@st.fragment(run_every=2)
def render_positions_and_pnl():
    if not st.session_state.positions:
        st.info("📦 当前暂无持仓")
        return

    # 1. 极速精准拉取当前所有持仓币种的最新价
    symbols_needed = list(set([p['交易对'] for p in st.session_state.positions]))
    symbols_query = '["' + '","'.join(symbols_needed) + '"]'
    prices_dict = {}
    try:
        res = requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbols={symbols_query}", timeout=2)
        for item in res.json():
            prices_dict[item['symbol']] = float(item['price'])
    except:
        pass # 断网时暂时使用上一次的价格

    # 2. 计算实时盈亏与爆仓拦截
    active_positions = []
    for pos in st.session_state.positions:
        sym = pos["交易对"]
        current_price = prices_dict.get(sym, pos.get("当前价", pos["开仓价"]))
        
        if pos["方向"] == "做多 🟢":
            pnl = (current_price - pos["开仓价"]) / pos["开仓价"] * pos["名义价值"]
        else: 
            pnl = (pos["开仓价"] - current_price) / pos["开仓价"] * pos["名义价值"]
        
        # 爆仓判定 (1000倍杠杆核心机制)
        if pnl <= -pos["占用保证金"]:
            st.error(f"🚨 爆仓！{sym} {pos['方向']} 遭强平！损失保证金: {pos['占用保证金']:.2f} U")
            continue 
        
        pos["当前价"] = current_price
        pos["未实现盈亏"] = pnl
        active_positions.append(pos)
        
    st.session_state.positions = active_positions

    # 3. 渲染炫酷的动态卡片
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
        st.button("🔄 重置 500 万体验金", on_click=reset_balance, use_container_width=True)
    with col_close:
        # 一键平仓按钮放在自动刷新区域之外，点击触发全局重载交割
        if st.button("⚡ 一键全部平仓", type="primary", use_container_width=True):
            if st.session_state.positions:
                total_return = sum([p["占用保证金"] + p.get("未实现盈亏", 0) for p in st.session_state.positions])
                st.session_state.balance += total_return
                st.session_state.positions = [] 
                st.toast(f"✅ 成功平仓！连本带利返回 {total_return:.2f} USDT", icon="💸")
                time.sleep(0.5)
                st.rerun()
            else:
                st.toast("当前无持仓", icon="ℹ️")
                
    st.divider()
    # 挂载局部自动刷新的持仓监控台
    render_positions_and_pnl()
