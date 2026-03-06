import streamlit as st
import streamlit.components.v1 as components

# ==========================================
# 1. Streamlit 页面基础配置
# ==========================================
st.set_page_config(
    page_title="市场概括 - 数字货币全景看板",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 隐藏 Streamlit 的默认留白、菜单和页脚，实现全宽沉浸式体验
hide_streamlit_style = """
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {
        padding: 0rem !important;
        max-width: 100% !important;
        overflow-x: hidden;
    }
    iframe {
        border: none !important;
        width: 100% !important;
    }
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ==========================================
# 2. 全新重写的 "市场概括" 前端应用 (HTML/JS/CSS)
# ==========================================
HTML_CONTENT = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>市场概括 - 数字货币看板</title>
    <!-- 使用 Lightweight Charts V4 最新版，原生支持 autoSize 自适应 -->
    <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        :root {
            --bg-dark: #0B0E11; 
            --bg-panel: #181A20; 
            --bg-hover: #2B3139;       
            --primary: #FCD535; 
            --text-main: #EAECEF; 
            --text-muted: #848E9C;     
            --up-green: #0ECB81; 
            --down-red: #F6465D; 
            --border: rgba(255, 255, 255, 0.08);         
        }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', -apple-system, sans-serif; -webkit-tap-highlight-color: transparent; }
        body { background-color: var(--bg-dark); color: var(--text-main); min-height: 100vh; overflow-x: hidden; }

        /* 顶部导航条 */
        header { display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; background: var(--bg-panel); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 50; }
        .logo-area { display: flex; align-items: center; gap: 10px; font-size: 22px; font-weight: 900; color: #fff; letter-spacing: 1px;}
        .logo-icon { color: var(--primary); }
        .net-status { font-size: 12px; display: flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 20px; background: rgba(14, 203, 129, 0.1); color: var(--up-green); font-weight: bold;}
        .pulse { width: 8px; height: 8px; background-color: var(--up-green); border-radius: 50%; box-shadow: 0 0 10px var(--up-green); animation: blink 1.5s infinite; }

        .container { padding: 20px; max-width: 1400px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }

        /* 控制台与数据面版 */
        .dashboard-header { display: flex; gap: 20px; flex-wrap: wrap; }
        
        .control-panel { background: var(--bg-panel); padding: 20px; border-radius: 12px; border: 1px solid var(--border); flex: 1; min-width: 300px; display: flex; flex-direction: column; gap: 12px;}
        .panel-title { font-size: 14px; color: var(--text-muted); font-weight: bold; margin-bottom: 4px; text-transform: uppercase;}
        select { width: 100%; padding: 12px; background: var(--bg-dark); color: #fff; border: 1px solid var(--border); border-radius: 8px; font-size: 18px; font-weight: bold; outline: none; cursor: pointer; }
        select:focus { border-color: var(--primary); }
        
        /* 24小时行情统计卡片 */
        .ticker-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; flex: 3; }
        .ticker-card { background: var(--bg-panel); padding: 20px; border-radius: 12px; border: 1px solid var(--border); display: flex; flex-direction: column; justify-content: center; gap: 8px; }
        .ticker-label { font-size: 13px; color: var(--text-muted); font-weight: 600; }
        .ticker-value { font-size: 22px; font-weight: 900; font-family: monospace; }
        
        /* 图表区域 */
        .chart-section { background: var(--bg-panel); border-radius: 12px; border: 1px solid var(--border); overflow: hidden; display: flex; flex-direction: column; }
        .chart-toolbar { padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); background: rgba(0,0,0,0.2);}
        .chart-title { font-size: 18px; font-weight: bold; display: flex; align-items: center; gap: 10px; }
        .live-price { font-family: monospace; font-size: 20px; }
        
        .timeframes { display: flex; gap: 8px; background: var(--bg-dark); padding: 4px; border-radius: 8px; border: 1px solid var(--border);}
        .tf-btn { color: var(--text-muted); font-size: 13px; padding: 6px 16px; border-radius: 6px; cursor: pointer; font-weight: bold; transition: 0.2s; user-select: none;}
        .tf-btn:hover { color: #fff; }
        .tf-btn.active { background: var(--bg-hover); color: var(--primary); }

        /* K线图容器 */
        #tvchart { width: 100%; height: 500px; position: relative; background: var(--bg-dark); }
        .loading-overlay { position: absolute; inset: 0; background: rgba(11,14,17,0.8); display: flex; flex-direction: column; justify-content: center; align-items: center; z-index: 10; gap: 15px;}
        .spinner { width: 40px; height: 40px; border: 4px solid rgba(252, 213, 53, 0.2); border-top-color: var(--primary); border-radius: 50%; animation: spin 1s linear infinite; }
        .error-text { color: var(--down-red); font-weight: bold; font-size: 16px; display: none; background: rgba(246,70,93,0.1); padding: 10px 20px; border-radius: 8px; border: 1px solid var(--down-red);}

        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
        @keyframes spin { to { transform: rotate(360deg); } }
        
        .up { color: var(--up-green) !important; }
        .down { color: var(--down-red) !important; }
    </style>
</head>
<body>

    <header>
        <div class="logo-area"><span class="logo-icon">📊</span> 市场概括 Market Overview</div>
        <div id="net-status" class="net-status"><div class="pulse"></div> 行情引擎已连接</div>
    </header>

    <div class="container">
        
        <!-- 顶部数据看板 -->
        <div class="dashboard-header">
            <!-- 资产选择器 -->
            <div class="control-panel">
                <div class="panel-title">选择数字资产 (Select Asset)</div>
                <select id="t-coin" onchange="onCoinChange()">
                    <!-- 由 JS 动态填充海量币种 -->
                </select>
            </div>

            <!-- 24小时统计数据 -->
            <div class="ticker-grid">
                <div class="ticker-card">
                    <span class="ticker-label">24h 涨跌幅 (Change)</span>
                    <span class="ticker-value" id="t-change">--%</span>
                </div>
                <div class="ticker-card">
                    <span class="ticker-label">24h 最高价 (High)</span>
                    <span class="ticker-value" id="t-high">--</span>
                </div>
                <div class="ticker-card">
                    <span class="ticker-label">24h 最低价 (Low)</span>
                    <span class="ticker-value" id="t-low">--</span>
                </div>
                <div class="ticker-card">
                    <span class="ticker-label">24h 成交额 (Vol USDT)</span>
                    <span class="ticker-value" id="t-vol">--</span>
                </div>
            </div>
        </div>

        <!-- 核心图表区 -->
        <div class="chart-section">
            <div class="chart-toolbar">
                <div class="chart-title">
                    <span id="chart-title-text">BTC / USDT</span>
                    <span id="chart-live-price" class="live-price">--</span>
                </div>
                <div class="timeframes">
                    <span class="tf-btn" onclick="changeTF('1m', this)">1m</span>
                    <span class="tf-btn active" onclick="changeTF('15m', this)">15m</span>
                    <span class="tf-btn" onclick="changeTF('1h', this)">1H</span>
                    <span class="tf-btn" onclick="changeTF('4h', this)">4H</span>
                    <span class="tf-btn" onclick="changeTF('1d', this)">1D</span>
                </div>
            </div>
            
            <div id="tvchart">
                <!-- 加载遮罩层 -->
                <div id="chart-loading" class="loading-overlay">
                    <div class="spinner" id="loading-spinner"></div>
                    <div id="loading-text" style="color:var(--primary); font-weight:bold; margin-top:10px;">获取 K 线数据中...</div>
                    <div id="error-box" class="error-text"></div>
                </div>
            </div>
        </div>

    </div>

    <script>
        // ==========================================
        // 核心配置与防封锁 API 节点池
        // ==========================================
        
        // 覆盖市面主流 35 种数字货币
        const COINS =[
            'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'AVAX', 'DOGE', 'DOT', 'LINK', 
            'MATIC', 'SHIB', 'LTC', 'UNI', 'BCH', 'ATOM', 'NEAR', 'APT', 'SUI', 'ARB', 
            'OP', 'INJ', 'RNDR', 'FIL', 'PEPE', 'ORDI', 'TIA', 'WLD', 'GALA', 'FTM', 
            'SAND', 'MANA', 'AXS', 'LDO', 'CRV'
        ];

        // 【极其关键】因为 Streamlit 服务器多在美国，api.binance.com 会被拒绝 (403 Forbidden)
        // 所以我们把美国专属节点 (api.binance.us) 和 无墙节点 (data-api) 放在最前面优先请求
        const API_NODES =[
            'https://api.binance.us',              // 美国节点，Streamlit Cloud 最爱
            'https://data-api.binance.vision',     // 官方提供的免墙公用节点
            'https://api.binance.com',             // 国际版节点（作为最后备用）
            'https://api1.binance.com'
        ];

        const state = {
            currentCoin: 'BTC',
            currentTF: '15m',
            chartInst: null,
            candleSeries: null,
            lastCandle: null
        };

        // ==========================================
        // 页面初始化
        // ==========================================
        window.onload = () => {
            // 填充下拉菜单
            const selectEl = document.getElementById('t-coin');
            selectEl.innerHTML = COINS.map(c => `<option value="${c}">${c} / USDT</option>`).join('');
            
            // 延迟一点初始化图表，确保容器 DOM 获取到真实宽高
            setTimeout(() => {
                initChart();
                fetchKlines();
                fetch24hTicker();
            }, 100);

            // 启动实时价格轮询引擎 (每2秒获取一次)
            setInterval(fetchLivePrice, 2000);
            // 启动24小时数据轮询引擎 (每10秒更新一次最高/最低/成交量)
            setInterval(fetch24hTicker, 10000);
        };

        // ==========================================
        // 图表引擎封装 (Lightweight Charts V4)
        // ==========================================
        function initChart() {
            const container = document.getElementById('tvchart');
            if(!container) return;

            // 原生支持 autoSize，完美适配屏幕缩放和 iframe 变化
            state.chartInst = LightweightCharts.createChart(container, {
                autoSize: true, 
                layout: { background: { type: 'solid', color: 'transparent' }, textColor: '#848E9C' },
                grid: { vertLines: { color: 'rgba(255,255,255,0.05)' }, horzLines: { color: 'rgba(255,255,255,0.05)' } },
                crosshair: { mode: 0 }, // 正常十字线模式
                rightPriceScale: { borderColor: 'rgba(255,255,255,0.1)' },
                timeScale: { borderColor: 'rgba(255,255,255,0.1)', timeVisible: true }
            });
        }

        // ==========================================
        // 核心功能：获取 K 线数据 (带智能节点轮询与纠错)
        // ==========================================
        async function fetchKlines() {
            showLoading(true);
            const symbol = state.currentCoin + 'USDT';
            const interval = state.currentTF;
            let rawData = null;
            let finalError = "";

            // 遍历节点，直到有一个成功返回数据
            for (let node of API_NODES) {
                try {
                    const url = `${node}/api/v3/klines?symbol=${symbol}&interval=${interval}&limit=500`;
                    const res = await fetch(url);
                    if (res.ok) {
                        const json = await res.json();
                        if (Array.isArray(json) && json.length > 0) {
                            rawData = json;
                            break; // 成功获取数据，跳出循环
                        }
                    } else {
                        finalError = `HTTP ${res.status}`;
                    }
                } catch (e) {
                    finalError = e.message;
                }
            }

            // 如果所有节点都失败
            if (!rawData) {
                showError(`所有行情节点拒绝访问<br>原因: ${finalError}<br>请稍后再试或检查服务器网络`);
                return;
            }

            try {
                // 如果图表中已有蜡烛线，彻底销毁旧线（防止切换周期时出现时间戳冲突导致白屏）
                if (state.candleSeries) {
                    state.chartInst.removeSeries(state.candleSeries);
                }

                // 重新创建蜡烛线
                state.candleSeries = state.chartInst.addCandlestickSeries({
                    upColor: '#0ECB81', downColor: '#F6465D', 
                    borderVisible: false, 
                    wickUpColor: '#0ECB81', wickDownColor: '#F6465D'
                });

                // 数据格式化与【严格去重防崩机制】
                let cleanData =[];
                let lastTime = 0;

                rawData.forEach(d => {
                    // Binance API 返回的是毫秒，需转为秒级整数
                    const t = Math.floor(d[0] / 1000); 
                    // Lightweight Charts 强制要求时间必须递增，否则直接崩溃
                    if (t > lastTime) {
                        cleanData.push({
                            time: t,
                            open: parseFloat(d[1]),
                            high: parseFloat(d[2]),
                            low: parseFloat(d[3]),
                            close: parseFloat(d[4])
                        });
                        lastTime = t;
                    }
                });

                // 注入数据并居中对齐
                state.candleSeries.setData(cleanData);
                state.lastCandle = cleanData[cleanData.length - 1];
                state.chartInst.timeScale().fitContent();
                
                showLoading(false);

            } catch (err) {
                console.error(err);
                showError("图表渲染引擎出错");
            }
        }

        // ==========================================
        // 全局数据实时更新 (24小时统计 & 最新秒级价格)
        // ==========================================
        async function fetch24hTicker() {
            const symbol = state.currentCoin + 'USDT';
            for (let node of API_NODES) {
                try {
                    const res = await fetch(`${node}/api/v3/ticker/24hr?symbol=${symbol}`);
                    if (res.ok) {
                        const data = await res.json();
                        
                        // 更新 UI 看板
                        const changePercent = parseFloat(data.priceChangePercent);
                        const elChange = document.getElementById('t-change');
                        elChange.innerText = (changePercent > 0 ? '+' : '') + changePercent.toFixed(2) + '%';
                        elChange.className = 'ticker-value ' + (changePercent >= 0 ? 'up' : 'down');

                        document.getElementById('t-high').innerText = parseFloat(data.highPrice).toString(); // 去除多余的0
                        document.getElementById('t-low').innerText = parseFloat(data.lowPrice).toString();
                        
                        // 格式化成交额 (转为 M 或 B)
                        let vol = parseFloat(data.quoteVolume);
                        if (vol > 1000000000) vol = (vol / 1000000000).toFixed(2) + ' B';
                        else if (vol > 1000000) vol = (vol / 1000000).toFixed(2) + ' M';
                        else vol = vol.toFixed(2);
                        document.getElementById('t-vol').innerText = vol;
                        
                        break;
                    }
                } catch (e) {}
            }
        }

        async function fetchLivePrice() {
            const symbol = state.currentCoin + 'USDT';
            for (let node of API_NODES) {
                try {
                    const res = await fetch(`${node}/api/v3/ticker/price?symbol=${symbol}`);
                    if (res.ok) {
                        const data = await res.json();
                        const price = parseFloat(data.price);
                        
                        // 1. 更新标题栏价格
                        const priceEl = document.getElementById('chart-live-price');
                        const oldPrice = parseFloat(priceEl.getAttribute('data-old')) || price;
                        priceEl.innerText = '$' + price.toString();
                        priceEl.className = 'live-price ' + (price >= oldPrice ? 'up' : 'down');
                        priceEl.setAttribute('data-old', price);

                        // 2. 动态绘制图表最后一根 K 线
                        if (state.lastCandle && state.candleSeries) {
                            const tfSeconds = { '1m': 60, '15m': 900, '1h': 3600, '4h': 14400, '1d': 86400 }[state.currentTF];
                            const now = Math.floor(Date.now() / 1000); 
                            
                            // 判断是否跨入新周期需要开新线
                            if (now >= state.lastCandle.time + tfSeconds) {
                                state.lastCandle = { 
                                    time: state.lastCandle.time + tfSeconds, 
                                    open: price, high: price, low: price, close: price 
                                };
                            } else {
                                // 刷新当前蜡烛线的高低收
                                state.lastCandle.high = Math.max(state.lastCandle.high, price); 
                                state.lastCandle.low = Math.min(state.lastCandle.low, price); 
                                state.lastCandle.close = price; 
                            }
                            state.candleSeries.update(state.lastCandle);
                        }
                        
                        // 更新顶部网络状态
                        document.getElementById('net-status').innerHTML = '<div class="pulse"></div> 行情引擎畅通';
                        document.getElementById('net-status').style.color = 'var(--up-green)';
                        break;
                    }
                } catch(e) {
                    document.getElementById('net-status').innerHTML = '🔴 正在穿透网络限制...';
                    document.getElementById('net-status').style.color = 'var(--down-red)';
                }
            }
        }

        // ==========================================
        // 交互事件响应
        // ==========================================
        function onCoinChange() {
            state.currentCoin = document.getElementById('t-coin').value;
            document.getElementById('chart-title-text').innerText = state.currentCoin + ' / USDT';
            
            // 重置价格为 --
            document.getElementById('chart-live-price').innerText = '--';
            document.getElementById('chart-live-price').className = 'live-price';
            
            // 重新拉取数据
            fetchKlines();
            fetch24hTicker();
            fetchLivePrice();
        }

        function changeTF(tf, el) { 
            // 切换按钮高亮状态
            document.querySelectorAll('.tf-btn').forEach(btn => btn.classList.remove('active')); 
            el.classList.add('active'); 
            
            state.currentTF = tf; 
            fetchKlines(); 
        }

        // ==========================================
        // UI 辅助控制
        // ==========================================
        function showLoading(isLoading) {
            const overlay = document.getElementById('chart-loading');
            const spinner = document.getElementById('loading-spinner');
            const text = document.getElementById('loading-text');
            const errorBox = document.getElementById('error-box');

            if (isLoading) {
                overlay.style.display = 'flex';
                spinner.style.display = 'block';
                text.style.display = 'block';
                errorBox.style.display = 'none';
            } else {
                overlay.style.display = 'none';
            }
        }

        function showError(msg) {
            const spinner = document.getElementById('loading-spinner');
            const text = document.getElementById('loading-text');
            const errorBox = document.getElementById('error-box');
            
            spinner.style.display = 'none';
            text.style.display = 'none';
            errorBox.style.display = 'block';
            errorBox.innerHTML = msg;
        }

    </script>
</body>
</html>"""

# ==========================================
# 3. 渲染页面
# ==========================================
# 赋予组件 1000px 的高度，确保看板能完整显示
components.html(HTML_CONTENT, height=1000, scrolling=True)
