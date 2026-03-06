import streamlit as st
import pandas as pd
import requests
import time
from openai import OpenAI

# ==========================================
# 0. 页面全局配置
# ==========================================
st.set_page_config(page_title="Crypto 极速模拟交易终端", layout="wide", initial_sidebar_state="expanded")

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
    st.toast("✅ 余额已重置为 5,000,000 USDT！", icon="💰")

# ==========================================
# 2. 核心功能：获取实时行情
# ==========================================
def get_real_market_data():
    url = 'https://api.binance.com/api/v3/ticker/24hr'
    symbols = '["BTCUSDT","ETHUSDT","SOLUSDT","DOGEUSDT"]'
    
    try:
        # 国内请求币安仍需代理，请根据实际情况配置
        proxies = {'http': 'http://127.0.0.1:7890', 'https': 'http://127.0.0.1:7890'}
        response = requests.get(f"{url}?symbols={symbols}", proxies=proxies, timeout=5)
        
        data = response.json()
        market_list = []
        summary_str = ""
        
        for item in data:
            coin = item['symbol'].replace("USDT", "")
            price = round(float(item['lastPrice']), 4)
            change = f"{float(item['priceChangePercent']):.2f}%"
            market_list.append({"币种": f"{coin}/USDT", "最新价 ($)": price, "24h涨跌幅": change})
            summary_str += f"{coin}目前价格{price}美元，涨跌幅{change}；"
            
        # 更新全局市场摘要，供 AI 读取
        st.session_state.market_summary = summary_str
        return pd.DataFrame(market_list)
    except Exception as e:
        st.error("🔌 币安 API 请求失败，请检查代理配置。")
        return pd.DataFrame()

# ==========================================
# 3. 侧边栏：API 配置
# ==========================================
with st.sidebar:
    st.header("⚙️ 系统设置")
    api_key = st.text_input("🔑 输入 DeepSeek API Key", type="password", help="在此处填入你的 DeepSeek API Key")
    if not api_key:
        st.warning("请先输入 API Key 以激活 AI 顾问功能。")
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
        
        # 聊天记录展示
        chat_container = st.container(height=350)
        with chat_container:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        
        # 聊天输入
        user_input = st.chat_input("问问 DeepSeek (如：当前BTC价格能做多吗？)")
        
        if user_input:
            if not api_key:
                st.error("请先在左侧侧边栏输入 API Key！")
            else:
                # 1. 记录用户输入
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                with chat_container:
                    with st.chat_message("user"):
                        st.markdown(user_input)
                    
                    # 2. 调用 DeepSeek API
                    with st.chat_message("assistant"):
                        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
                        
                        # 注入灵魂：让 AI 知道目前的真实币价
                        system_prompt = f"""你是一个专业的加密货币交易顾问。
                        现在的实时市场行情是：{st.session_state.market_summary}。
                        请结合上述真实价格数据，用简明扼要、专业的语言回答用户的问题。如果涉及高倍杠杆，务必提醒风险。"""
                        
                        messages = [{"role": "system", "content": system_prompt}] + st.session_state.chat_history
                        
                        try:
                            # 开启流式输出 (Stream)
                            response = client.chat.completions.create(
                                model="deepseek-chat",
                                messages=messages,
                                stream=True
                            )
                            # st.write_stream 会实现极其流畅的打字机效果
                            full_response = st.write_stream(response)
                            st.session_state.chat_history.append({"role": "assistant", "content": full_response})
                        except Exception as e:
                            st.error(f"API 请求失败: {e}")

# ==========================================
# 5. 主界面：现货与合约分栏
# ==========================================
tab_market, tab_futures = st.tabs(["📊 实时现货概况", "📈 模拟交易面板"])

with tab_market:
    st.subheader("全网实时行情")
    auto_refresh = st.checkbox("开启自动刷新 (每 2 秒)")
    
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
    
    with col_chart:
        # 预留给 TradingView 的 K线图位置
        st.components.v1.html(
            """
            <div style="height: 380px; background-color: #16181A; color: #888; display: flex; align-items: center; justify-content: center; border-radius: 8px; border: 1px solid #333;">
                <h3>无延迟 K 线图表区域</h3>
            </div>
            """, height=400
        )
        st.subheader("当前持仓管理")
        if not st.session_state.positions:
            st.info("暂无持仓数据。")
        else:
            st.dataframe(pd.DataFrame(st.session_state.positions), use_container_width=True)

    with col_trade:
        st.subheader("💳 极速下单")
        trade_symbol = st.selectbox("选择合约交易对", ["BTC-USDT-PERP", "ETH-USDT-PERP", "SOL-USDT-PERP"])
        leverage = st.slider("杠杆倍数 (Leverage)", min_value=1, max_value=1000, value=100, step=1)
        amount = st.number_input("开仓名义价值 (USDT)", min_value=1.0, value=10000.0, step=1000.0)
        
        margin_required = amount / leverage
        st.caption(f"🚀 实际扣除保证金: **{margin_required:.4f} USDT**")
        
        col_buy, col_sell = st.columns(2)
        with col_buy:
            if st.button("做多 (Long) 🟢", use_container_width=True):
                if st.session_state.balance >= margin_required:
                    st.session_state.balance -= margin_required
                    st.session_state.positions.append({
                        "方向": "🟢 做多", "交易对": trade_symbol, "杠杆": f"{leverage}x", 
                        "名义价值": amount, "占用保证金": round(margin_required, 4)
                    })
                    st.rerun()
                else:
                    st.error("余额不足！")
                    
        with col_sell:
            if st.button("做空 (Short) 🔴", use_container_width=True):
                if st.session_state.balance >= margin_required:
                    st.session_state.balance -= margin_required
                    st.session_state.positions.append({
                        "方向": "🔴 做空", "交易对": trade_symbol, "杠杆": f"{leverage}x", 
                        "名义价值": amount, "占用保证金": round(margin_required, 4)
                    })
                    st.rerun()
                else:
                    st.error("余额不足！")
