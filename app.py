import streamlit as st
import pandas as pd
import requests
import time
from openai import OpenAI

# ==========================================
# 0. 页面全局配置
# ==========================================
st.set_page_config(page_title="Crypto 极速模拟交易终端", layout="wide", initial_sidebar_state="collapsed")

if 'balance' not in st.session_state:
    st.session_state.balance = 5000000.0  
if 'positions' not in st.session_state:
    st.session_state.positions = []       
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'market_summary' not in st.session_state:
    st.session_state.market_summary = "暂无最新行情"
if 'latest_prices' not in st.session_state:
    st.session_state.latest_prices = {}   

def reset_balance():
    st.session_state.balance = 5000000.0
    st.session_state.positions = []
    st.toast("✅ 余额已重置为 5,000,000 USDT！", icon="💰")

# ==========================================
# 1. 核心功能：获取实时行情 (修复了云端报错)
# ==========================================
def get_real_market_data():
    """获取所有关注币种的市场概况"""
    url = 'https://api.binance.com/api/v3/ticker/24hr'
    symbols = '["BTCUSDT","ETHUSDT","SOLUSDT","DOGEUSDT","BNBUSDT","XRPUSDT"]'
    
    try:
        # ⚠️ 修复点1：移除了本地代理。Streamlit Cloud 服务器在海外，直接请求即可畅通无阻！
        response = requests.get(f"{url}?symbols={symbols}", timeout=5)
        
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
            prices_dict[symbol_raw] = price 
            
        st.session_state.market_summary = summary_str
        st.session_state.latest_prices = prices_dict
        return pd.DataFrame(market_list)
    except Exception as e:
        return pd.DataFrame({"错误": [f"API 请求失败: {str(e)}"]})

def get_single_price(symbol):
    """下单瞬间获取极速精准价格，防止买不进去"""
    try:
        res = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=3)
        return float(res.json()['price'])
    except:
        return 0.0

# ==========================================
# 2. 侧边栏与 AI 悬浮窗
# ==========================================
with st.sidebar:
    st.header("⚙️ 系统设置")
    api_key = st.text_input("🔑 DeepSeek API Key", type="password")
    st.divider()
    st.header("💳 资产管理")
    st.metric(label="可用体验金 (USDT)", value=f"{st.session_state.balance:,.2f}")
    st.button("🔄 重置 500 万体验金", on_click=reset_balance, use_container_width=True)

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
                st.error("请先输入 API Key！")
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
# 3. 主界面：现货与合约分栏
# ==========================================
tab_market, tab_futures = st.tabs(["📊 实时现货概况", "📈 模拟合约 (1000x 引擎)"])

# 获取最新全局数据以供展示
_ = get_real_market_data()

with tab_market:
    st.subheader("全网实时行情")
    # ⚠️ 修复点2：移除了会导致页面狂闪的 auto_refresh 循环代码。提供一个手动刷新按钮。
    if st.button("🔄 获取最新现货报价"):
        st.rerun()
        
    real_data_df = get_real_market_data()
    if not real_data_df.empty and "错误" not in real_data_df.columns:
        st.dataframe(real_data_df, use_container_width=True, hide_index=True)
    else:
        st.error(real_data_df.iloc[0]["错误"])

with tab_futures:
    col_chart, col_trade = st.columns([2, 1])
    
    trade_symbol_display = st.selectbox("选择交易对", ["BTC-USDT", "ETH-USDT", "SOL-USDT", "DOGE-USDT"])
    tv_symbol = trade_symbol_display.replace("-", "") # 转换为 Binance 格式: BTCUSDT
    
    with col_chart:
        # TradingView K线图 (自带 WebSocket，不刷新网页也能实时跳动)
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
        
        st.subheader("当前持仓与实时盈亏")
        col_pnl_refresh, col_close_all = st.columns([1, 1])
        with col_pnl_refresh:
            if st.button("🔄 刷新最新盈亏 (PnL)"):
                st.rerun() # 点击时重算盈亏，避免图表一直狂闪
        
        # 盈亏计算引擎
        active_positions = []
        for pos in st.session_state.positions:
            sym = pos["交易对"]
            # 抓取当前最新价用于结算
            pos_price = st.session_state.latest_prices.get(sym, pos["开仓价"]) 
            
            if pos["方向"] == "🟢 做多":
                pnl = (pos_price - pos["开仓价"]) / pos["开仓价"] * pos["名义价值"]
            else: 
                pnl = (pos["开仓价"] - pos_price) / pos["开仓价"] * pos["名义价值"]
            
            if pnl <= -pos["占用保证金"]:
                st.error(f"🚨 爆仓通知：您的 {sym} {pos['方向']} 仓位已遭强平！损失保证金：{pos['占用保证金']:.2f} USDT")
                continue 
            
            pos_display = pos.copy()
            pos_display["当前价"] = round(pos_price, 4)
            pos_display["未实现盈亏(USDT)"] = round(pnl, 2)
            pos_display["收益率(ROE)"] = f"{(pnl / pos['占用保证金'] * 100):.2f}%"
            active_positions.append(pos_display)
            
        st.session_state.positions = [{"方向": p["方向"], "交易对": p["交易对"], "杠杆": p["杠杆"], "名义价值": p["名义价值"], "占用保证金": p["占用保证金"], "开仓价": p["开仓价"]} for p in active_positions]

        if not active_positions:
            st.info("暂无持仓数据。")
        else:
            df_pos = pd.DataFrame(active_positions)
            def color_pnl(val):
                if isinstance(val, (int, float)):
                    return 'color: #0ecb81' if val > 0 else 'color: #f6465d' if val < 0 else 'color: white'
                return ''
            st.dataframe(df_pos.style.map(color_pnl, subset=['未实现盈亏(USDT)']), use_container_width=True)
            
            with col_close_all:
                if st.button("⚡ 一键市价全平", type="primary"):
                    total_pnl = sum([p["未实现盈亏(USDT)"] for p in active_positions])
                    returned_margin = sum([p["占用保证金"] for p in active_positions])
                    st.session_state.balance += (returned_margin + total_pnl)
                    st.session_state.positions = [] 
                    st.success(f"✅ 全平成功！释放资金 {returned_margin + total_pnl:.2f} USDT。")
                    time.sleep(1)
                    st.rerun()

    with col_trade:
        st.subheader("💳 极速下单")
        # ⚠️ 修复点3：下单时不再依赖全局刷新出的价格，改为点击瞬间后台拉取
        display_price = st.session_state.latest_prices.get(tv_symbol, 0.0)
        st.metric("参考标记价格", f"${display_price:,.4f}" if display_price > 0 else "加载中...")
        st.divider()
        
        leverage = st.slider("杠杆倍数 (Leverage)", min_value=1, max_value=1000, value=100, step=1)
        amount = st.number_input("开仓名义价值 (USDT)", min_value=1.0, value=10000.0, step=1000.0)
        
        margin_required = amount / leverage
        st.caption(f"🚀 实际扣除保证金: **{margin_required:.4f} USDT**")
        
        col_buy, col_sell = st.columns(2)
        with col_buy:
            if st.button("做多 (Long) 🟢", use_container_width=True):
                # 点击瞬间获取精准成交价
                exec_price = get_single_price(tv_symbol)
                if exec_price == 0:
                    st.error("网络异常，无法获取成交价！")
                elif st.session_state.balance >= margin_required:
                    st.session_state.balance -= margin_required
                    st.session_state.positions.append({
                        "方向": "🟢 做多", "交易对": tv_symbol, "杠杆": leverage, 
                        "名义价值": amount, "占用保证金": margin_required, "开仓价": exec_price
                    })
                    st.success(f"做多成功！成交均价：{exec_price}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("余额不足，无法开仓！")
                    
        with col_sell:
            if st.button("做空 (Short) 🔴", use_container_width=True):
                exec_price = get_single_price(tv_symbol)
                if exec_price == 0:
                    st.error("网络异常，无法获取成交价！")
                elif st.session_state.balance >= margin_required:
                    st.session_state.balance -= margin_required
                    st.session_state.positions.append({
                        "方向": "🔴 做空", "交易对": tv_symbol, "杠杆": leverage, 
                        "名义价值": amount, "占用保证金": margin_required, "开仓价": exec_price
                    })
                    st.success(f"做空成功！成交均价：{exec_price}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("余额不足，无法开仓！")
