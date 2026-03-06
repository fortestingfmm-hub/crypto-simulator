import streamlit as st
import pandas as pd
import requests
import time
from openai import OpenAI

# ==========================================
# 0. 页面全局配置
# ==========================================
st.set_page_config(page_title="Crypto 极速模拟交易终端", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 1. 初始化系统状态 (Session State)
# ==========================================
if 'balance' not in st.session_state:
    st.session_state.balance = 5000000.0  # 初始 500 万 U 体验金
if 'positions' not in st.session_state:
    st.session_state.positions = []       # 仓位列表
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'market_summary' not in st.session_state:
    st.session_state.market_summary = "暂无最新行情"
if 'latest_prices' not in st.session_state:
    st.session_state.latest_prices = {}   # 存储最新价格，用于计算盈亏

def reset_balance():
    st.session_state.balance = 5000000.0
    st.session_state.positions = []
    st.toast("✅ 余额已重置为 5,000,000 USDT！", icon="💰")

# ==========================================
# 2. 核心功能：获取实时行情
# ==========================================
def get_real_market_data():
    url = 'https://api.binance.com/api/v3/ticker/24hr'
    symbols = '["BTCUSDT","ETHUSDT","SOLUSDT","DOGEUSDT","BNBUSDT","XRPUSDT"]'
    
    try:
        # ⚠️ 国内环境请按需开启代理
        proxies = {'http': 'http://127.0.0.1:7890', 'https': 'http://127.0.0.1:7890'}
        response = requests.get(f"{url}?symbols={symbols}", proxies=proxies, timeout=5)
        # response = requests.get(f"{url}?symbols={symbols}", timeout=5) # 海外/畅通网络用这个
        
        data = response.json()
        market_list = []
        summary_str = ""
        prices_dict = {}
        
        for item in data:
            symbol_raw = item['symbol']
            coin = symbol_raw.replace("USDT", "")
            price = float(item['lastPrice'])
            change = f"{float(item['priceChangePercent']):.2f}%"
            
            market_list.append({"币种": f"{coin}/USDT", "最新价 ($)": round(price, 4), "24h涨跌幅": change})
            summary_str += f"{coin}价格{round(price, 2)}，涨跌幅{change}；"
            prices_dict[symbol_raw] = price # 记录纯数字价格用于计算
            
        st.session_state.market_summary = summary_str
        st.session_state.latest_prices = prices_dict
        return pd.DataFrame(market_list)
    except Exception as e:
        st.error(f"🔌 API 请求失败，请检查网络或代理: {e}")
        return pd.DataFrame()

# ==========================================
# 3. 侧边栏：API 配置与资产
# ==========================================
with st.sidebar:
    st.header("⚙️ 系统设置")
    api_key = st.text_input("🔑 DeepSeek API Key", type="password")
    st.divider()
    st.header("💳 资产管理")
    st.metric(label="可用体验金 (USDT)", value=f"{st.session_state.balance:,.2f}")
    st.button("🔄 重置 500 万体验金", on_click=reset_balance, use_container_width=True)

# ==========================================
# 4. 顶部与 AI 悬浮窗
# ==========================================
col_header, col_ai = st.columns([4, 1])
with col_header:
    st.title("⚡ Crypto 极速模拟交易面板")

with col_ai:
    st.write("") 
    with st.popover("🤖 唤醒 DeepSeek 顾问", use_container_width=True):
        st.markdown("### DeepSeek 智能分析")
        chat_container = st.container(height=350)
        with chat_container:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        
        user_input = st.chat_input("向 AI 提问...")
        if user_input:
            if not api_key:
                st.error("请先在左侧输入 API Key！")
            else:
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                with chat_container:
                    with st.chat_message("user"):
                        st.markdown(user_input)
                    with st.chat_message("assistant"):
                        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
                        system_prompt = f"你是一个专业的加密货币交易顾问。现在的实时市场行情是：{st.session_state.market_summary}。请结合上述真实价格数据回答问题，若涉及高倍杠杆务必提醒强平风险。"
                        messages = [{"role": "system", "content": system_prompt}] + st.session_state.chat_history
                        try:
                            response = client.chat.completions.create(model="deepseek-chat", messages=messages, stream=True)
                            full_response = st.write_stream(response)
                            st.session_state.chat_history.append({"role": "assistant", "content": full_response})
                        except Exception as e:
                            st.error(f"API 请求失败: {e}")

# ==========================================
# 5. 主界面：现货与合约分栏
# ==========================================
tab_market, tab_futures = st.tabs(["📊 实时现货概况", "📈 模拟合约 (1000x 引擎)"])

# 每次页面加载都获取一次最新价格（用于计算盈亏）
_ = get_real_market_data()

with tab_market:
    st.subheader("全网实时行情")
    auto_refresh = st.checkbox("开启行情自动刷新 (每 2 秒)")
    
    price_container = st.empty()
    with price_container.container():
        real_data_df = get_real_market_data()
        if not real_data_df.empty:
            st.dataframe(real_data_df, use_container_width=True, hide_index=True)
        
    if auto_refresh:
        time.sleep(2)
        st.rerun()

with tab_futures:
    col_chart, col_trade = st.columns([2, 1])
    
    # 提取当前选中的交易对标识 (BTCUSDT)
    trade_symbol_display = st.selectbox("选择交易对", ["BTC-USDT", "ETH-USDT", "SOL-USDT", "DOGE-USDT"], key="trade_sym")
    tv_symbol = trade_symbol_display.replace("-", "") # 转换为 Binance 格式: BTCUSDT
    current_price = st.session_state.latest_prices.get(tv_symbol, 0.0)
    
    with col_chart:
        # 1. 嵌入 TradingView 无延迟实时 K 线图 (通过 iframe)
        st.components.v1.html(
            f"""
            <div class="tradingview-widget-container" style="height:450px;width:100%">
              <div id="tradingview_{tv_symbol}" style="height:calc(100% - 32px);width:100%"></div>
              <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
              <script type="text/javascript">
              new TradingView.widget({{
              "autosize": true,
              "symbol": "BINANCE:{tv_symbol}",
              "interval": "1",
              "
