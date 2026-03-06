import streamlit as st
import pandas as pd
import requests
import time
import json
import os
import hashlib
import uuid
from openai import OpenAI

# ==========================================
# 0. 页面全局配置
# ==========================================
st.set_page_config(page_title="Crypto 模拟终端", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .block-container { padding-top: 3.5rem; padding-bottom: 5rem; }
    .title-text { font-size: 1.5rem; font-weight: bold; color: #fff; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 本地数据库引擎
# ==========================================
DATA_FILE = "trading_data.json"

def load_db():
    if not os.path.exists(DATA_FILE): return {"users": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)

def save_db(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

def hash_password(password): return hashlib.sha256(password.encode()).hexdigest()

def sync_current_user_data():
    if st.session_state.get('logged_in'):
        db = load_db()
        username = st.session_state.username
        db["users"][username]["balance"] = st.session_state.balance
        db["users"][username]["positions"] = st.session_state.positions
        save_db(db)

# ==========================================
# 2. 账号注册与免密登录
# ==========================================
db = load_db()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

url_token = st.query_params.get("token")
if url_token and not st.session_state.logged_in:
    for user, u_data in db["users"].items():
        if u_data.get("session_token") == url_token:
            st.session_state.logged_in = True
            st.session_state.username = user
            st.session_state.balance = u_data["balance"]
            st.session_state.positions = u_data["positions"]
            st.session_state.chat_history = []
            break

if not st.session_state.logged_in:
    st.markdown('<div class="title-text">⚡ Crypto 模拟引擎</div>', unsafe_allow_html=True)
    tab_login, tab_register = st.tabs(["🔑 登录", "📝 注册新账号"])
    
    with tab_login:
        with st.form("login_form"):
            l_user = st.text_input("用户名")
            l_pass = st.text_input("密码", type="password")
            if st.form_submit_button("登 录", use_container_width=True):
                if l_user in db["users"] and db["users"][l_user]["password"] == hash_password(l_pass):
                    new_token = str(uuid.uuid4())
                    db["users"][l_user]["session_token"] = new_token
                    save_db(db)
                    st.query_params["token"] = new_token
                    st.session_state.logged_in = True
                    st.session_state.username = l_user
                    st.session_state.balance = db["users"][l_user]["balance"]
                    st.session_state.positions = db["users"][l_user]["positions"]
                    st.session_state.chat_history = []
                    st.rerun()
                else:
                    st.error("密码错误！")
                    
    with tab_register:
        with st.form("register_form"):
            r_user = st.text_input("设置用户名")
            r_pass = st.text_input("设置密码", type="password")
            if st.form_submit_button("注 册", use_container_width=True):
                if r_user not in db["users"]:
                    db["users"][r_user] = {"password": hash_password(r_pass), "balance": 5000000.0, "positions": [], "session_token": ""}
                    save_db(db)
                    st.success("注册成功！请登录。")
    st.stop() 

# ==========================================
# 3. 核心工具函数
# ==========================================
def reset_balance():
    st.session_state.balance = 5000000.0
    st.session_state.positions = []
    sync_current_user_data() 
    st.toast("✅ 资金重置！", icon="💰")

def logout():
    st.query_params.clear()
    st.session_state.clear()
    st.rerun()

API_NODES = ['https://data-api.binance.vision', 'https://api.mexc.com']
@st.cache_data(ttl=3600) 
def get_all_usdt_symbols():
    for url in API_NODES:
        try:
            res = requests.get(f"{url}/api/v3/exchangeInfo", timeout=8)
            symbols = [s['symbol'] for s in res.json()['symbols'] if s['symbol'].endswith('USDT') and s['status'] in ['TRADING', 'ENABLED']]
            main_coins = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT"]
            return main_coins + [s for s in symbols if s not in main_coins]
        except: continue
    return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"]

all_symbols = get_all_usdt_symbols()

def get_single_price(symbol):
    for url in API_NODES:
        try:
            res = requests.get(f"{url}/api/v3/ticker/price?symbol={symbol}", timeout=3)
            if res.status_code == 200: return float(res.json().get('price', 0))
        except: continue
    return 0.0

def settle_liquidations():
    active = []
    for pos in st.session_state.positions:
        price = get_single_price(pos["交易对"])
        if price == 0: price = pos["开仓价"] 
        pnl = (price - pos["开仓价"]) / pos["开仓价"] * pos["名义价值"] if pos["方向"] == "做多 🟢" else (pos["开仓价"] - price) / pos["开仓价"] * pos["名义价值"]
        if pnl <= -pos["占用保证金"]:
            st.toast(f"🚨 {pos['交易对']} 已爆仓！", icon="💥")
            continue
        active.append(pos)
    st.session_state.positions = active
    sync_current_user_data()

# ==========================================
# 4. 顶部导航
# ==========================================
col_title, col_ai, col_exit = st.columns([5, 2, 2])
with col_title: st.markdown('<div class="title-text">⚡ Crypto 模拟引擎</div>', unsafe_allow_html=True)
with col_exit:
    if st.button("🚪 退出", use_container_width=True): logout()
st.caption(f"交易员：**{st.session_state.username}** | 数据源: WebSocket 实盘直连")
st.divider()

tab_market, tab_trade, tab_assets = st.tabs(["📊 毫秒级行情", "📈 极速交易", "💼 动态资产持仓"])

# ==========================================
# 模块 1: 行情榜
# ==========================================
with tab_market:
    st.components.v1.html(
        """
        <style>
            body { background-color: #0E1117; color: white; font-family: sans-serif; margin: 0; }
            table { width: 100%; border-collapse: collapse; font-size: 14px; }
            th, td { padding: 12px 8px; text-align: left; border-bottom: 1px solid #2b3139; }
            th { color: #848e9c; font-weight: normal; }
            .flash-green { animation: flashG 0.5s; color: #0ecb81 !important; }
            .flash-red { animation: flashR 0.5s; color: #f6465d !important; }
            @keyframes flashG { 0% { background-color: rgba(14,203,129,0.3); } 100% { background-color: transparent; } }
            @keyframes flashR { 0% { background-color: rgba(246,70,93,0.3); } 100% { background-color: transparent; } }
        </style>
        <div style="padding: 10px; color:#848e9c; font-size:12px;">🟢 WSS 毫秒实时流已连接...</div>
        <table>
            <thead><tr><th>币种</th><th>最新价 (USDT)</th><th>24h 涨跌</th></tr></thead>
            <tbody id="market-body"></tbody>
        </table>
        <script>
            const ws = new WebSocket('wss://data-stream.binance.vision:9443/ws/!ticker@arr');
            const targetCoins = ['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','DOGEUSDT','XRPUSDT','PEPEUSDT','WLDUSDT','ORDIUSDT','AVAXUSDT'];
            const tbody = document.getElementById('market-body');
            let rows = {};

            targetCoins.forEach(coin => {
                let tr = document.createElement('tr');
                tr.innerHTML = `<td><b>${coin.replace('USDT','')}</b></td><td id="p-${coin}">加载中</td><td id="c-${coin}">-</td>`;
                tbody.appendChild(tr);
                rows[coin] = { p: document.getElementById(`p-${coin}`), c: document.getElementById(`c-${coin}`), last: 0 };
            });

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                data.forEach(item => {
                    const sym = item.s;
                    if(rows[sym]) {
                        const price = parseFloat(item.c).toFixed(4);
                        const change = parseFloat(item.P).toFixed(2);
                        
                        if(price !== rows[sym].last) {
                            rows[sym].p.innerText = '$' + price;
                            rows[sym].p.className = price > rows[sym].last ? 'flash-green' : 'flash-red';
                            rows[sym].last = price;
                        }
                        
                        rows[sym].c.innerText = change + '%';
                        rows[sym].c.style.color = change >= 0 ? '#0ecb81' : '#f6465d';
                    }
                });
            };
        </script>
        """, height=550
    )

# ==========================================
# 模块 2: 极速交易面板 (1秒级图表)
# ==========================================
with tab_trade:
    tv_symbol = st.selectbox("选择交易对", all_symbols, format_func=lambda x: x.replace("USDT", "/USDT"), label_visibility="collapsed")
    
    # 🌟 修复：退回免费版支持的最低时间级别（1分钟线），当前价格线依然是实时跳动的！
    st.components.v1.html(
        f"""
        <div class="tradingview-widget-container" style="height:350px;width:100%">
          <div id="tv_{tv_symbol}" style="height:calc(100% - 32px);width:100%"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget({{"autosize": true, "symbol": "BINANCE:{tv_symbol}", "interval": "1", "theme": "dark", "style": "1", "hide_top_toolbar": true, "backgroundColor": "#0E1117"}});
        </script></div>
        """, height=350
    )
    
    st.markdown("#### ⚡ 极速开仓")
    leverage = st.slider("杠杆倍数", 1, 1000, 100, label_visibility="collapsed")
    amount = st.number_input("输入开仓名义价值 (USDT，无上限)", min_value=1.0, value=10000.0, step=1000.0)
    margin_req = amount / leverage
    st.caption(f"🛡️ 实际冻结保证金: **{margin_req:.2f} U**")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🟢 做多", use_container_width=True):
            settle_liquidations() 
            price = get_single_price(tv_symbol)
            if price > 0 and st.session_state.balance >= margin_req:
                st.session_state.balance -= margin_req
                st.session_state.positions.append({"方向": "做多 🟢", "交易对": tv_symbol, "杠杆": leverage, "名义价值": amount, "占用保证金": margin_req, "开仓价": price})
                sync_current_user_data() 
                st.toast("✅ 做多成功！")
            else: st.error("网络异常或余额不足")
    with c2:
        if st.button("🔴 做空", use_container_width=True):
            settle_liquidations()
            price = get_single_price(tv_symbol)
            if price > 0 and st.session_state.balance >= margin_req:
                st.session_state.balance -= margin_req
                st.session_state.positions.append({"方向": "做空 🔴", "交易对": tv_symbol, "杠杆": leverage, "名义价值": amount, "占用保证金": margin_req, "开仓价": price})
                sync_current_user_data() 
                st.toast("✅ 做空成功！")
            else: st.error("网络异常或余额不足")

# ==========================================
# 模块 3: JS WebSocket 注入 (动态总资产)
# ==========================================
with tab_assets:
    col_r, col_c = st.columns(2)
    with col_r: st.button("🔄 重置资金", on_click=reset_balance, use_container_width=True)
    with col_c:
        if st.button("⚡ 结算平仓", type="primary", use_container_width=True):
            settle_liquidations() 
            if st.session_state.positions:
                total_return = 0
                for p in st.session_state.positions:
                    pr = get_single_price(p["交易对"])
                    pnl = (pr - p["开仓价"]) / p["开仓价"] * p["名义价值"] if p["方向"] == "做多 🟢" else (p["开仓价"] - pr) / p["开仓价"] * p["名义价值"]
                    total_return += (p["占用保证金"] + pnl)
                st.session_state.balance += total_return
                st.session_state.positions = []
                sync_current_user_data()
                st.toast("✅ 已全部市价平仓！")
                st.rerun()

    pos_json = json.dumps(st.session_state.positions)
    base_balance = st.session_state.balance

    st.components.v1.html(
        f"""
        <style>
            body {{ background-color: #0E1117; color: white; font-family: sans-serif; margin: 0; }}
            .dashboard {{ background: linear-gradient(135deg, #1e222d 0%, #151822 100%); padding: 20px; border-radius: 12px; border: 1px solid #2b3139; text-align: center; margin-bottom: 20px; }}
            .equity-num {{ font-size: 38px; margin: 10px 0; font-family: 'Trebuchet MS'; transition: color 0.2s; }}
            .metrics {{ display: flex; justify-content: space-between; font-size: 13px; color: #848e9c; padding-top: 10px; border-top: 1px solid #2b3139; }}
            .card {{ border: 1px solid #2b3139; border-radius: 8px; padding: 15px; margin-bottom: 10px; background: #161a25; }}
            .card-header {{ font-weight: bold; margin-bottom: 10px; display: flex; justify-content: space-between; }}
            .val-green {{ color: #0ecb81; }} .val-red {{ color: #f6465d; }}
        </style>
        
        <div class="dashboard">
            <div style="color:#848e9c; font-size:14px;">⚡ 实盘毫秒净资产 (U)</div>
            <h1 id="total-equity" class="equity-num val-green">计算中...</h1>
            <div class="metrics">
                <span>可用余额<br><strong style="color:#eaecef">{base_balance:,.2f}</strong></span>
                <span>占用保证金<br><strong id="total-margin" style="color:#eaecef">0.00</strong></span>
                <span>未实现盈亏<br><strong id="total-pnl">0.00</strong></span>
            </div>
        </div>
        
        <div id="positions-container"></div>

        <script>
            const positions = {pos_json};
            const baseBalance = {base_balance};
            const container = document.getElementById('positions-container');
            
            let totalMargin = 0;
            let streams = [];
            
            positions.forEach((pos, index) => {{
                totalMargin += pos['占用保证金'];
                streams.push(pos['交易对'].toLowerCase() + '@ticker');
                
                const card = document.createElement('div');
                card.className = 'card';
                card.innerHTML = `
                    <div class="card-header">
                        <span>${{pos['交易对']}} | ${{pos['方向']}} | ${{pos['杠杆']}}x</span>
                        <span id="pnl-${{index}}" style="font-size: 16px;">0.00 U</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:12px; color:#848e9c;">
                        <span>开仓价: ${{pos['开仓价'].toFixed(4)}}</span>
                        <span>现价: <span id="price-${{index}}" style="color:white;">加载中</span></span>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:12px; color:#848e9c; margin-top:5px;">
                        <span>ROE: <span id="roe-${{index}}">0.00%</span></span>
                        <span>名义价值: ${{pos['名义价值'].toFixed(2)}}</span>
                    </div>
                `;
                container.appendChild(card);
            }});
            
            document.getElementById('total-margin').innerText = totalMargin.toFixed(2);
            if (positions.length === 0) container.innerHTML = '<div style="color:#848e9c; text-align:center;">暂无持仓</div>';

            if(streams.length > 0) {{
                const wsUrl = 'wss://data-stream.binance.vision:9443/ws/' + streams.join('/');
                const ws = new WebSocket(wsUrl);
                let currentPnLs = new Array(positions.length).fill(0);
                
                ws.onmessage = (event) => {{
                    const data = JSON.parse(event.data);
                    const currentSymbol = data.s;
                    const currentPrice = parseFloat(data.c);
                    let globalPnL = 0;
                    
                    positions.forEach((pos, i) => {{
                        if (pos['交易对'] === currentSymbol) {{
                            let pnl = 0;
                            if(pos['方向'] === '做多 🟢') pnl = (currentPrice - pos['开仓价']) / pos['开仓价'] * pos['名义价值'];
                            else pnl = (pos['开仓价'] - currentPrice) / pos['开仓价'] * pos['名义价值'];
                            
                            currentPnLs[i] = pnl;
                            document.getElementById(`price-${{i}}`).innerText = currentPrice.toFixed(4);
                            
                            const elPnl = document.getElementById(`pnl-${{i}}`);
                            elPnl.innerText = (pnl > 0 ? '+' : '') + pnl.toFixed(2) + ' U';
                            elPnl.className = pnl >= 0 ? 'val-green' : 'val-red';
                            
                            const roe = (pnl / pos['占用保证金'] * 100);
                            const elRoe = document.getElementById(`roe-${{i}}`);
                            elRoe.innerText = (roe > 0 ? '+' : '') + roe.toFixed(2) + '%';
                            elRoe.className = pnl >= 0 ? 'val-green' : 'val-red';
                            
                            if(pnl <= -pos['占用保证金']) elPnl.innerText = '🚨已爆仓';
                        }}
                        globalPnL += currentPnLs[i];
                    }});
                    
                    const totalEquity = baseBalance + totalMargin + globalPnL;
                    const elEquity = document.getElementById('total-equity');
                    elEquity.innerText = totalEquity.toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
                    elEquity.className = globalPnL >= 0 ? 'equity-num val-green' : 'equity-num val-red';
                    
                    const elTotalPnl = document.getElementById('total-pnl');
                    elTotalPnl.innerText = (globalPnL > 0 ? '+' : '') + globalPnL.toFixed(2);
                    elTotalPnl.className = globalPnL >= 0 ? 'val-green' : 'val-red';
                }};
            }} else {{
                document.getElementById('total-equity').innerText = baseBalance.toLocaleString('en-US', {{minimumFractionDigits: 2}});
            }}
        </script>
        """, height=600
    )

