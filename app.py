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
              "timezone": "Asia/Shanghai",
              "theme": "dark",
              "style": "1",
              "locale": "zh_CN",
              "enable_publishing": false,
              "backgroundColor": "#121212",
              "hide_top_toolbar": false,
              "save_image": false,
              "container_id": "tradingview_{tv_symbol}"
            }});
            </script>
            </div>
            """, height=450
        )
        
        st.subheader("持仓与实时盈亏 (刷新页面更新盈亏)")
        
        # 2. 核心：计算实时盈亏与强平逻辑
        active_positions = []
        for pos in st.session_state.positions:
            sym = pos["交易对"]
            pos_price = st.session_state.latest_prices.get(sym, pos["开仓价"])
            
            # 计算未实现盈亏 (PnL)
            if pos["方向"] == "🟢 做多":
                pnl = (pos_price - pos["开仓价"]) / pos["开仓价"] * pos["名义价值"]
            else: # 做空
                pnl = (pos["开仓价"] - pos_price) / pos["开仓价"] * pos["名义价值"]
            
            # 爆仓(强平)判定：如果亏损大于等于保证金，直接爆仓
            if pnl <= -pos["占用保证金"]:
                st.error(f"🚨 爆仓通知：您的 {sym} {pos['方向']} 仓位已遭强平！损失保证金：{pos['占用保证金']:.2f} USDT")
                continue # 剔除该仓位
            
            # 更新显示数据
            pos_display = pos.copy()
            pos_display["当前价"] = round(pos_price, 4)
            pos_display["未实现盈亏(USDT)"] = round(pnl, 2)
            pos_display["收益率(ROE)"] = f"{(pnl / pos['占用保证金'] * 100):.2f}%"
            active_positions.append(pos_display)
            
        # 同步存活的仓位
        st.session_state.positions = [{"方向": p["方向"], "交易对": p["交易对"], "杠杆": p["杠杆"], "名义价值": p["名义价值"], "占用保证金": p["占用保证金"], "开仓价": p["开仓价"]} for p in active_positions]

        if not active_positions:
            st.info("暂无持仓数据。")
        else:
            # 高亮显示盈亏颜色 (Streamlit dataframe style)
            df_pos = pd.DataFrame(active_positions)
            def color_pnl(val):
                if isinstance(val, (int, float)):
                    color = '#0ecb81' if val > 0 else '#f6465d' if val < 0 else 'white'
                    return f'color: {color}'
                return ''
            st.dataframe(df_pos.style.map(color_pnl, subset=['未实现盈亏(USDT)']), use_container_width=True)
            
            # 一键平仓功能
            if st.button("⚡ 一键市价全平 (Close All)"):
                total_pnl = sum([p["未实现盈亏(USDT)"] for p in active_positions])
                returned_margin = sum([p["占用保证金"] for p in active_positions])
                st.session_state.balance += (returned_margin + total_pnl)
                st.session_state.positions = [] # 清空仓位
                st.success(f"✅ 全平成功！释放保证金及盈亏共计 {returned_margin + total_pnl:.2f} USDT，已转入余额。")
                time.sleep(1)
                st.rerun()

    with col_trade:
        st.subheader("💳 极速下单")
        st.metric("最新标记价格", f"${current_price:,.4f}" if current_price > 0 else "获取中...")
        st.divider()
        
        leverage = st.slider("杠杆倍数 (Leverage)", min_value=1, max_value=1000, value=100, step=1)
        amount = st.number_input("开仓名义价值 (USDT)", min_value=1.0, value=10000.0, step=1000.0)
        
        margin_required = amount / leverage
        st.caption(f"🚀 实际扣除保证金: **{margin_required:.4f} USDT**")
        
        col_buy, col_sell = st.columns(2)
        with col_buy:
            if st.button("做多 (Long) 🟢", use_container_width=True):
                if current_price == 0:
                    st.error("价格获取中，请稍后再试！")
                elif st.session_state.balance >= margin_required:
                    st.session_state.balance -= margin_required
                    st.session_state.positions.append({
                        "方向": "🟢 做多", "交易对": tv_symbol, "杠杆": leverage, 
                        "名义价值": amount, "占用保证金": margin_required, "开仓价": current_price
                    })
                    st.success(f"做多成功！开仓价：{current_price}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("余额不足！")
                    
        with col_sell:
            if st.button("做空 (Short) 🔴", use_container_width=True):
                if current_price == 0:
                    st.error("价格获取中，请稍后再试！")
                elif st.session_state.balance >= margin_required:
                    st.session_state.balance -= margin_required
                    st.session_state.positions.append({
                        "方向": "🔴 做空", "交易对": tv_symbol, "杠杆": leverage, 
                        "名义价值": amount, "占用保证金": margin_required, "开仓价": current_price
                    })
                    st.success(f"做空成功！开仓价：{current_price}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("余额不足！")
