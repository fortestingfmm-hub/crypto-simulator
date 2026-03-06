import streamlit as st
import streamlit.components.v1 as components

# 1. 设置 Streamlit 页面配置
st.set_page_config(
    page_title="廿九实战终端",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 隐藏默认元素，实现全屏沉浸式体验
hide_streamlit_style = """
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {
        padding: 0rem !important;
        max-width: 100% !important;
    }
    iframe {
        border: none !important;
    }
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# 2. 核心 HTML/JS 代码
HTML_CONTENT = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>廿九 - 极速实战终端 V11</title>
    <!-- 引入 TradingView Lightweight Charts -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/lightweight-charts/3.8.0/lightweight-charts.standalone.production.js"></script>
    <style>
        :root {
            --bg-dark: #0B0E11; --bg-card: rgba(24, 26, 32, 0.7); --bg-hover: rgba(43, 49, 57, 0.8);       
            --primary: #FCD535; --primary-dark: #E6C32B;   
            --ai-color: #8E44AD; --ai-glow: #B28DFF;
            --text-main: #EAECEF; --text-muted: #848E9C;     
            --up-green: #0ECB81; --down-red: #F6465D; --border: rgba(43, 49, 57, 0.5);         
        }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, sans-serif; -webkit-tap-highlight-color: transparent; }
        body { background-color: var(--bg-dark); color: var(--text-main); padding-bottom: 90px; overflow-x: hidden; 
               background-image: radial-gradient(circle at 50% 0%, #1a1e24 0%, #0B0E11 60%); }

        .glass-card { background: var(--bg-card); backdrop-filter: blur(12px); border-radius: 16px; padding: 16px; margin-bottom: 16px; border: 1px solid var(--border); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2); }

        header { display: flex; flex-direction: column; padding: 16px 20px; background: rgba(11, 14, 17, 0.85); backdrop-filter: blur(10px); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 50; }
        .header-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .logo-area { display: flex; align-items: center; gap: 8px; font-size: 22px; font-weight: 900; background: linear-gradient(45deg, #FCD535, #fff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 2px;}
        .status-badge { font-size: 11px; padding: 4px 10px; border-radius: 12px; font-weight: 600; background: rgba(14, 203, 129, 0.1); color: var(--up-green); display: flex; align-items: center; gap: 6px; border: 1px solid rgba(14,203,129,0.2);}
        .pulse { width: 6px; height: 6px; background-color: var(--up-green); border-radius: 50%; box-shadow: 0 0 10px var(--up-green); animation: blink 1s infinite; }
        
        .equity-board { background: linear-gradient(135deg, rgba(43,49,57,0.8), rgba(24,26,32,0.9)); padding: 16px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; border: 1px solid rgba(255,255,255,0.05);}
        .equity-info { display: flex; flex-direction: column; gap: 4px; }
        .equity-label { font-size: 12px; color: var(--text-muted); }
        .equity-value { font-size: 24px; font-weight: 900; font-family: monospace; color: var(--primary); text-shadow: 0 0 15px rgba(252,213,53,0.3); transition: 0.3s;}
        
        .header-btns { display: flex; gap: 10px; }
        .action-btn-sm { background: rgba(246, 70, 93, 0.15); color: var(--down-red); border: 1px solid rgba(246,70,93,0.3); padding: 8px 12px; border-radius: 8px; font-size: 12px; font-weight: bold; cursor: pointer; transition: 0.2s;}
        .action-btn-sm.green { background: rgba(14, 203, 129, 0.15); color: var(--up-green); border-color: rgba(14,203,129,0.3); }
        .action-btn-sm:active { transform: scale(0.9); }
        
        .container { padding: 16px; max-width: 600px; margin: 0 auto; height: 100%;}
        .card-title { font-size: 14px; font-weight: 700; color: #fff; margin-bottom: 16px; display: flex; align-items: center; gap: 6px; border-bottom: 1px solid var(--border); padding-bottom: 10px;}

        .market-header { display: grid; grid-template-columns: 2fr 1fr 1fr; font-size: 12px; color: var(--text-muted); margin-bottom: 10px; padding: 0 5px;}
        .market-header div:nth-child(2), .market-header div:nth-child(3) { text-align: right; }
        .coin-row { display: grid; grid-template-columns: 2fr 1fr 1fr; align-items: center; padding: 12px 5px; border-bottom: 1px solid var(--border); font-family: monospace; font-size: 15px;}
        .coin-name { font-weight: bold; font-family: -apple-system, sans-serif;}
        .price-spot, .price-future { text-align: right; font-weight: 600; transition: color 0.1s;}

        .chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .chart-coin-title { font-size: 18px; font-weight: 900; color: var(--primary); font-family: monospace; display: flex; align-items: center; gap: 8px;}
        .chart-price { font-size: 18px; font-weight: bold; color: #fff; font-family: monospace;}
        .timeframes { display: flex; gap: 6px; background: rgba(0,0,0,0.3); padding: 4px; border-radius: 8px; border: 1px solid var(--border);}
        .tf-btn { color: var(--text-muted); font-size: 12px; padding: 4px 8px; border-radius: 6px; cursor: pointer; font-weight: bold; transition: 0.2s;}
        .tf-btn.active { background: var(--bg-hover); color: #fff; }
        #tvchart { width: 100%; height: 320px; position: relative; border-radius: 8px; overflow: hidden; background: transparent; }

        .input-group { display: flex; gap: 12px; margin-bottom: 12px; }
        .input-box { flex: 1; background: rgba(0,0,0,0.2); border-radius: 10px; padding: 10px 14px; display: flex; flex-direction: column; gap: 6px; border: 1px solid var(--border); transition: 0.3s; }
        .input-box:focus-within { border-color: var(--primary); box-shadow: 0 0 10px rgba(252,213,53,0.1); background: rgba(0,0,0,0.4);}
        .input-label { font-size: 11px; color: var(--text-muted); font-weight: 600; display: flex; justify-content: space-between; align-items: center;}
        select, input { background: transparent; border: none; color: #fff; font-size: 16px; font-weight: bold; outline: none; width: 100%; font-family: monospace;}
        select option { background: #181A20; color: #fff; }
        
        .preview-board { background: rgba(252,213,53,0.05); border: 1px dashed rgba(252,213,53,0.3); border-radius: 10px; padding: 12px; margin: 16px 0; font-size: 12px; color: #bbb; display: grid; grid-template-columns: 1fr 1fr; gap: 10px;}
        .prev-item { display: flex; flex-direction: column; gap: 4px; }
        .prev-val { font-family: monospace; font-size: 14px; font-weight: bold; color: #fff;}
        .prev-val.warn { color: var(--down-red); }

        .btn-submit { width: 100%; background: linear-gradient(90deg, var(--primary), #f39c12); color: #000; border: none; padding: 16px; border-radius: 12px; font-size: 16px; font-weight: 900; cursor: pointer; text-transform: uppercase; box-shadow: 0 4px 15px rgba(252,213,53,0.3); transition: 0.2s;}
        .btn-submit:active { transform: scale(0.98); }

        .pos-tabs { display: flex; gap: 15px; margin-bottom: 15px; border-bottom: 1px solid var(--border); padding-bottom: 10px; }
        .pos-tab { font-size: 14px; font-weight: 800; color: var(--text-muted); cursor: pointer; transition: 0.3s; position: relative; }
        .pos-tab.active { color: #fff; }
        .pos-tab.active::after { content: ''; position: absolute; bottom: -11px; left: 0; width: 100%; height: 3px; background: var(--primary); border-radius: 3px; box-shadow: 0 0 8px var(--primary); }

        .pos-card { position: relative; overflow: hidden; background: linear-gradient(180deg, rgba(43,49,57,0.6) 0%, rgba(24,26,32,0.8) 100%); border-radius: 16px; padding: 16px; margin-bottom: 16px; border: 1px solid var(--border); box-shadow: 0 4px 20px rgba(0,0,0,0.3);}
        .pos-line { position: absolute; left: 0; top: 0; bottom: 0; width: 4px; }
        .pos-line.long { background: var(--up-green); box-shadow: 0 0 15px var(--up-green);}
        .pos-line.short { background: var(--down-red); box-shadow: 0 0 15px var(--down-red);}
        .pos-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.05);}
        .pos-tag { font-size: 14px; font-weight: 900; display: flex; align-items: center; gap: 6px;}
        .close-btn { background: rgba(255,255,255,0.1); color: #fff; font-size: 12px; padding: 6px 14px; border-radius: 8px; border: none; cursor: pointer; font-weight: bold; transition: 0.2s;}
        
        .pos-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 12px; font-size: 12px; font-family: monospace;}
        .grid-item { display: flex; flex-direction: column; gap: 4px; }
        .grid-item span:first-child { color: var(--text-muted); font-size: 11px;}
        .grid-val { color: #fff; font-weight: bold; font-size: 13px;}
        
        .pnl-row { display: flex; justify-content: space-between; align-items: flex-end; background: rgba(0,0,0,0.2); padding: 12px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.02);}
        .pnl-value { font-family: monospace; font-size: 24px; font-weight: 900; }
        .roe-value { font-family: monospace; font-size: 16px; font-weight: bold; }

        .history-reason { font-size: 11px; padding: 3px 8px; border-radius: 6px; background: rgba(255,255,255,0.1); color: #fff; font-weight: bold;}
        .reason-liq { background: rgba(246,70,93,0.2); color: var(--down-red); border: 1px solid var(--down-red);}
        .reason-tp { background: rgba(14,203,129,0.2); color: var(--up-green); border: 1px solid var(--up-green);}
        .clear-hist-btn { text-align: center; color: var(--text-muted); font-size: 12px; margin-top: 10px; cursor: pointer; text-decoration: underline; padding-bottom: 20px;}

        .up { color: var(--up-green) !important; }
        .down { color: var(--down-red) !important; }

        .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); backdrop-filter: blur(8px); z-index: 9999; display: none; justify-content: center; align-items: center; }
        .modal-content { width: 90%; max-width: 380px; background: linear-gradient(180deg, #1f2329 0%, #121418 100%); border: 1px solid var(--primary); border-radius: 20px; padding: 24px; box-shadow: 0 10px 40px rgba(0,0,0,0.8); animation: scaleUp 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
        .modal-title { font-size: 18px; font-weight: 900; color: #fff; margin-bottom: 10px; text-align: center; }
        .modal-btn-row { display: flex; gap: 15px; margin-top: 24px; }
        .modal-btn-cancel { flex: 1; background: rgba(255,255,255,0.1); color: #fff; border: none; padding: 14px; border-radius: 12px; font-weight: bold; cursor: pointer; }
        .modal-btn-save { flex: 1; background: var(--primary); color: #000; border: none; padding: 14px; border-radius: 12px; font-weight: bold; cursor: pointer; }

        #toast-container { position: fixed; top: 20px; left: 50%; transform: translateX(-50%); z-index: 9999; display: flex; flex-direction: column; gap: 10px; width: 90%; max-width: 400px; pointer-events: none;}
        .toast { background: rgba(24, 26, 32, 0.95); backdrop-filter: blur(10px); color: #fff; padding: 16px 20px; border-radius: 12px; font-weight: bold; font-size: 14px; border-left: 4px solid var(--primary); box-shadow: 0 10px 30px rgba(0,0,0,0.5); animation: slideDown 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); line-height: 1.5;}
        .toast.error { border-left-color: var(--down-red); background: rgba(40, 15, 15, 0.95);}
        .toast.success { border-left-color: var(--up-green); }

        .chat-container { display: flex; flex-direction: column; height: calc(100vh - 180px); }
        .chat-box { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; padding-bottom: 10px;}
        .chat-box::-webkit-scrollbar { display: none; }
        .msg-row { display: flex; width: 100%; }
        .msg-row.user { justify-content: flex-end; }
        .msg-row.ai { justify-content: flex-start; }
        .msg-bubble { max-width: 90%; padding: 14px 18px; border-radius: 16px; font-size: 14px; line-height: 1.6; word-wrap: break-word;}
        .msg-row.user .msg-bubble { background: linear-gradient(135deg, var(--primary), var(--primary-dark)); color: #000; border-bottom-right-radius: 4px; font-weight: 600;}
        .msg-row.ai .msg-bubble { background: rgba(30, 26, 41, 0.9); color: #E0D4F5; border: 1px solid #3B2D59; border-bottom-left-radius: 4px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);}
        .chat-input-area { display: flex; gap: 10px; background: var(--bg-card); padding: 12px; border-radius: 16px; border: 1px solid var(--border); margin-top: 10px; backdrop-filter: blur(10px);}
        .chat-input-area input { flex: 1; padding: 8px; font-size: 15px; color: #fff; background: transparent; border: none; outline: none;}
        .send-btn { background: linear-gradient(135deg, var(--ai-color), var(--ai-glow)); color: white; border: none; width: 44px; height: 44px; border-radius: 12px; display: flex; justify-content: center; align-items: center; cursor: pointer; font-size: 18px; box-shadow: 0 4px 10px rgba(142,68,173,0.3);}

        .tab-bar { position: fixed; bottom: 0; left: 0; right: 0; height: 80px; background: rgba(11, 14, 17, 0.9); backdrop-filter: blur(15px); display: flex; justify-content: space-around; align-items: center; border-top: 1px solid rgba(255,255,255,0.05); z-index: 100;}
        .tab-item { display: flex; flex-direction: column; align-items: center; gap: 6px; color: var(--text-muted); font-size: 11px; font-weight: 700; cursor: pointer; transition: 0.3s;}
        .tab-icon { font-size: 22px; filter: grayscale(100%) opacity(0.5); transition: 0.3s;}
        .tab-item.active { color: var(--primary); }
        .tab-item.active .tab-icon { filter: grayscale(0) opacity(1); transform: translateY(-2px);}
        .tab-item[data-tab="ai"].active { color: var(--ai-glow); } 
        
        .tab-content { display: none; }
        .tab-content.active { display: block; animation: fadeIn 0.4s ease; }

        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px);} to { opacity: 1; transform: translateY(0);} }
        @keyframes slideDown { from { opacity: 0; transform: translateY(-30px);} to { opacity: 1; transform: translateY(0);} }
        @keyframes scaleUp { from { opacity: 0; transform: scale(0.85); } to { opacity: 1; transform: scale(1); } }
    </style>
</head>
<body>

    <div id="toast-container"></div>

    <div id="tpsl-modal" class="modal-overlay">
        <div class="modal-content">
            <div class="modal-title" id="modal-title">⚙️ 随时调整止盈止损</div>
            <input type="hidden" id="modal-pos-id">
            <div class="input-group">
                <div class="input-box" style="border:1px dashed var(--up-green); background:rgba(14,203,129,0.05);">
                    <span class="input-label">目标止盈价 (TP)</span>
                    <input type="number" id="modal-tp" placeholder="选填，达标平仓">
                </div>
            </div>
            <div class="input-group">
                <div class="input-box" style="border:1px dashed var(--down-red); background:rgba(246,70,93,0.05);">
                    <span class="input-label">硬性止损价 (SL) <span style="color:var(--down-red)">*防爆仓必备</span></span>
                    <input type="number" id="modal-sl" placeholder="选填，击穿强平将爆仓">
                </div>
            </div>
            <div class="modal-btn-row">
                <button class="modal-btn-cancel" onclick="closeTPSLModal()">取消修改</button>
                <button class="modal-btn-save" onclick="saveTPSL()">确认更新点位</button>
            </div>
        </div>
    </div>

    <div id="withdraw-modal" class="modal-overlay">
        <div class="modal-content">
            <div class="modal-title" style="color: var(--up-green);">💰 模拟利润落袋为安</div>
            <div style="color:var(--text-muted); font-size:12px; margin-bottom:15px; text-align:center; line-height: 1.5;">
                养成定期出金的好习惯！<br>提现将从你的可用模拟余额中扣除相应金额。
            </div>
            <div class="input-group">
                <div class="input-box" style="border-color: var(--up-green);">
                    <span class="input-label">提现金额 (USDT)</span>
                    <input type="number" id="withdraw-amount" placeholder="输入要提取的利润">
                </div>
            </div>
            <div class="modal-btn-row">
                <button class="modal-btn-cancel" onclick="closeWithdrawModal()">取消</button>
                <button class="modal-btn-save" style="background: var(--up-green); color: #fff;" onclick="confirmWithdraw()">确认提现</button>
            </div>
        </div>
    </div>

    <header>
        <div class="header-top">
            <div class="logo-area"><span class="logo-icon">⚡</span> 廿九</div>
            <div id="net-status" class="status-badge"><div class="pulse"></div> 引擎启动中...</div>
        </div>
        <div class="equity-board">
            <div class="equity-info">
                <span class="equity-label">模拟账户总净值 (USDT)</span>
                <span class="equity-value" id="total-equity">5,000,000.00</span>
            </div>
            <div class="header-btns">
                <button class="action-btn-sm green" onclick="openWithdrawModal()">💰 虚拟提现</button>
                <button class="action-btn-sm" onclick="resetAccount()">↻ 重置</button>
            </div>
        </div>
    </header>

    <div class="container">
        <div id="market" class="tab-content">
            <div class="glass-card" style="padding: 16px 10px;">
                <div class="card-title" style="margin-left: 5px;">🔥 现货/合约全市场扫描</div>
                <div class="market-header">
                    <div>资产名称</div><div>现货 (Spot)</div><div>合约 (Futures)</div>
                </div>
                <div id="market-list"></div>
            </div>
        </div>

        <div id="portfolio" class="tab-content active">
            
            <div class="glass-card" style="padding: 12px;">
                <div class="chart-header">
                    <div class="chart-coin-title">
                        <span id="chart-title-text">BTC/USDT</span>
                        <span id="chart-current-price" class="chart-price">--</span>
                    </div>
                    <div class="timeframes">
                        <span class="tf-btn" onclick="changeTF('1m', this)">1m</span>
                        <span class="tf-btn active" onclick="changeTF('15m', this)">15m</span>
                        <span class="tf-btn" onclick="changeTF('1h', this)">1H</span>
                        <span class="tf-btn" onclick="changeTF('4h', this)">4H</span>
                        <span class="tf-btn" onclick="changeTF('1d', this)">1D</span>
                    </div>
                </div>
                <!-- 图表容器 -->
                <div id="tvchart"></div>
            </div>

            <div class="glass-card">
                <div class="card-title">⚔️ 廿九实战量化 (强平机制启动)</div>
                <div class="input-group">
                    <div class="input-box">
                        <span class="input-label">交易对</span>
                        <select id="t-coin" onchange="syncCoinChart(); updatePreview();"></select>
                    </div>
                    <div class="input-box">
                        <span class="input-label">方向</span>
                        <select id="t-side" onchange="updatePreview()">
                            <option value="long">🟢 做多 (Long)</option>
                            <option value="short">🔴 做空 (Short)</option>
                        </select>
                    </div>
                </div>

                <div class="input-group">
                    <div class="input-box">
                        <span class="input-label">投入保证金 (USDT) <span style="color:var(--primary); font-weight:normal;" id="avail-bal">可用: 500万</span></span>
                        <input type="number" id="t-margin" value="10000" oninput="updatePreview()">
                    </div>
                    <div class="input-box">
                        <span class="input-label">杠杆 <span id="lev-show" style="color:var(--primary)">100X</span></span>
                        <input type="number" id="t-lev" value="100" max="1000" min="1" oninput="document.getElementById('lev-show').innerText=this.value+'X'; updatePreview();">
                    </div>
                </div>

                <div class="input-group">
                    <div class="input-box">
                        <span class="input-label">止盈价 (TP)</span>
                        <input type="number" id="t-tp" placeholder="选填" oninput="updatePreview()">
                    </div>
                    <div class="input-box">
                        <span class="input-label">止损价 (SL)</span>
                        <input type="number" id="t-sl" placeholder="选填" oninput="updatePreview()">
                    </div>
                </div>

                <div class="preview-board">
                    <div class="prev-item">
                        <span>💀 预估强制平仓价 (Liquidation)</span>
                        <span class="prev-val warn" id="prev-liq">--</span>
                    </div>
                    <div class="prev-item">
                        <span>🎯 触及止盈预计收益</span>
                        <span class="prev-val up" id="prev-tp">--</span>
                    </div>
                    <div class="prev-item" style="grid-column: span 2;">
                        <span>🛡️ 触及止损预计亏损 (未设止损将面临清零)</span>
                        <span class="prev-val down" id="prev-sl">--</span>
                    </div>
                </div>

                <button class="btn-submit" onclick="executeTrade()">🚀 确认下单建仓</button>
            </div>

            <div class="pos-tabs">
                <div class="pos-tab active" id="tab-active" onclick="switchPosTab('active')">实时持仓 (<span id="pos-count">0</span>)</div>
                <div class="pos-tab" id="tab-history" onclick="switchPosTab('history')">历史交割单</div>
            </div>

            <div id="positions-container"></div>
            <div id="history-container" style="display: none;"></div>

        </div>

        <div id="ai" class="tab-content">
            <div class="chat-container">
                <div style="text-align:center; margin-bottom: 15px; padding: 12px; background: rgba(142,68,173,0.1); border: 1px dashed var(--ai-color); border-radius: 12px;">
                    <span style="color:var(--ai-glow); font-weight:900; font-size:14px;">⚡ OpenClaw 交易灵魂已注入 ⚡</span><br>
                    <span style="color:var(--text-muted); font-size:12px; margin-top:4px; display:block;">支持自然对话记忆 / 无需配置 / 自动调用盘面数据</span>
                </div>
                <div class="chat-box" id="chat-box"></div>
                
                <div class="chat-input-area">
                    <input type="text" id="chat-input" placeholder="可随意聊天，或问: 以太坊能做空吗？" onkeypress="if(event.key==='Enter') sendAI()">
                    <button class="send-btn" onclick="sendAI()">➤</button>
                </div>
            </div>
        </div>
    </div>

    <div class="tab-bar">
        <div class="tab-item" onclick="switchTab('market', this)"><span class="tab-icon">📊</span><span>行情列表</span></div>
        <div class="tab-item active" onclick="switchTab('portfolio', this)"><span class="tab-icon">⚔️</span><span>廿九终端</span></div>
        <div class="tab-item" onclick="switchTab('ai', this)" data-tab="ai"><span class="tab-icon">🔮</span><span>AI助手</span></div>
    </div>

    <script>
        const TOP_COINS =['BTC', 'ETH', 'SOL', 'BNB', 'DOGE', 'XRP', 'PEPE', 'ORDI', 'WLD', 'AVAX', 'LINK', 'SUI', 'ADA'];
        
        const state = {
            balance: 5000000, prices: {},
            positions:[], history:[], chatHistory:[], 
            chartCoin: 'BTC', chartTF: '15m', chartInst: null, candleSeries: null, lastCandle: null
        };

        function showToast(msg, type = 'info') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.innerHTML = msg;
            container.appendChild(toast);
            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(-20px)';
                setTimeout(() => toast.remove(), 400);
            }, 3500);
        }

        window.onload = () => {
            try {
                initDOM();
                const savedBal = localStorage.getItem('mock_balance'); if(savedBal) state.balance = parseFloat(savedBal);
                const savedPos = localStorage.getItem('mock_pos'); if(savedPos) state.positions = JSON.parse(savedPos);
                const savedHist = localStorage.getItem('mock_history'); if(savedHist) state.history = JSON.parse(savedHist);
                const savedChat = localStorage.getItem('mock_chat'); if(savedChat) state.chatHistory = JSON.parse(savedChat);

                setTimeout(initTVChartSafe, 300); 
                renderPositions();
                renderHistory();
                renderChatHistory();
                updateEquityUI();
                startBulletproofPolling();
                setTimeout(updatePreview, 1000); 

                if(state.chatHistory.length === 0) {
                    appendChat('ai', '你好！我是 **OpenClaw** 智能代理。欢迎来到实战终端。', false);
                }
            } catch (error) { console.error("初始化出错", error); }
        };

        function initDOM() {
            const html = TOP_COINS.map(c => `<div class="coin-row"><div class="coin-name">${c}</div><div id="spot-${c}" class="price-spot">--</div><div id="future-${c}" class="price-future">--</div></div>`).join('');
            document.getElementById('market-list').innerHTML = html;
            document.getElementById('t-coin').innerHTML = TOP_COINS.map(c => `<option value="${c}">${c} / USDT</option>`).join('');
        }

        async function startBulletproofPolling() {
            const badge = document.getElementById('net-status');
            setInterval(async () => {
                let success = false;
                
                // 【核心优化 1】价格数据防阻断代理序列
                const PRICE_URLS =[
                    'https://data-api.binance.vision/api/v3/ticker/price',
                    'https://api.binance.com/api/v3/ticker/price',
                    'https://api.mexc.com/api/v3/ticker/price', // MEXC API 对国内/国外都更友好
                    `https://api.allorigins.win/raw?url=${encodeURIComponent('https://api.binance.com/api/v3/ticker/price')}` // 终极防墙免费代理
                ];

                for (let url of PRICE_URLS) {
                    try {
                        const res = await fetch(url);
                        if (res.ok) {
                            const data = await res.json();
                            handlePriceData(data);
                            success = true; break; 
                        }
                    } catch(e) {}
                }
                if(success) {
                    badge.innerHTML = '<div class="pulse"></div> 🟢 行情直连畅通'; badge.style.color = 'var(--up-green)';
                } else {
                    badge.innerHTML = '🔴 数据穿透受阻...'; badge.style.color = 'var(--down-red)';
                }
            }, 1500); 
        }

        function handlePriceData(dataArray) {
            let needCalc = false;
            dataArray.forEach(item => {
                const coin = item.symbol.replace('USDT', '');
                if (TOP_COINS.includes(coin)) {
                    const price = parseFloat(item.price);
                    state.prices[coin] = price;
                    updatePriceNode(`spot-${coin}`, price, coin);
                    updatePriceNode(`future-${coin}`, price, coin);
                    if(coin === state.chartCoin) updateRealtimeCandle(price);
                    needCalc = true;
                }
            });
            if(needCalc) {
                updatePreview(); 
                if(state.positions.length > 0) fastCalculatePNL();
            }
        }

        function updatePriceNode(id, price, coin) {
            const el = document.getElementById(id); if(!el) return;
            const oldPrice = parseFloat(el.getAttribute('data-old')) || 0;
            if(price !== oldPrice && oldPrice !== 0) el.style.color = price > oldPrice ? 'var(--up-green)' : 'var(--down-red)';
            el.innerText = price < 1 ? price.toFixed(4) : price.toFixed(2);
            el.setAttribute('data-old', price);
            setTimeout(() => { if(el) el.style.color = ''; }, 200);
        }

        function initTVChartSafe() {
            try {
                const container = document.getElementById('tvchart');
                if (!container) return;
                
                // 【核心优化 2】强制获取准确的容器宽度，解决白屏问题
                let initWidth = container.offsetWidth || window.innerWidth - 32;
                if (initWidth < 100) initWidth = window.innerWidth > 600 ? 560 : window.innerWidth - 32;

                state.chartInst = LightweightCharts.createChart(container, {
                    width: initWidth,
                    height: 320,
                    layout: { background: { type: 'solid', color: 'transparent' }, textColor: '#848E9C' },
                    grid: { vertLines: { color: 'rgba(43,49,57,0.2)', style: 1 }, horzLines: { color: 'rgba(43,49,57,0.2)', style: 1 } },
                    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
                    rightPriceScale: { borderColor: 'rgba(43,49,57,0.5)' },
                    timeScale: { borderColor: 'rgba(43,49,57,0.5)', timeVisible: true, secondsVisible: false },
                });
                
                state.candleSeries = state.chartInst.addCandlestickSeries({ upColor: '#0ECB81', downColor: '#F6465D', borderVisible: false, wickUpColor: '#0ECB81', wickDownColor: '#F6465D' });
                
                fetchChartHistory(); 

                new ResizeObserver(entries => {
                    if (entries.length === 0 || entries[0].target.clientWidth === 0) return;
                    state.chartInst.resize(entries[0].target.clientWidth, 320);
                }).observe(container);

            } catch (error) { console.error("图表初始化失败:", error); }
        }

        function syncCoinChart() {
            state.chartCoin = document.getElementById('t-coin').value;
            document.getElementById('chart-title-text').innerText = state.chartCoin + '/USDT';
            document.getElementById('chart-current-price').innerText = '--'; 
            fetchChartHistory();
        }

        function changeTF(tf, el) { 
            document.querySelectorAll('.tf-btn').forEach(btn => btn.classList.remove('active')); 
            el.classList.add('active'); 
            state.chartTF = tf; 
            fetchChartHistory(); 
        }

        async function fetchChartHistory() {
            if(!state.candleSeries) return;
            const symbol = state.chartCoin + 'USDT'; 
            const interval = state.chartTF;
            let data = null;
            
            // 【核心优化 3】K线数据最强防屏蔽节点序列（包含备用交易所及跨域代理）
            const KLINE_URLS =[
                `https://data-api.binance.vision/api/v3/klines?symbol=${symbol}&interval=${interval}&limit=150`,
                `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=${interval}&limit=150`,
                `https://api.mexc.com/api/v3/klines?symbol=${symbol}&interval=${interval}&limit=150`,
                `https://api.allorigins.win/raw?url=${encodeURIComponent('https://api.binance.com/api/v3/klines?symbol='+symbol+'&interval='+interval+'&limit=150')}`
            ];

            for (let url of KLINE_URLS) {
                try {
                    const res = await fetch(url);
                    if (res.ok) { 
                        const temp = await res.json(); 
                        if (Array.isArray(temp) && temp.length > 0) { data = temp; break; } 
                    }
                } catch(e) { console.warn("节点拉取失败，自动切换:", url); }
            }

            if (!data) {
                showToast(`⚠️ ${interval} K线数据被网络拦截，请刷新或切换网络重试`, 'error');
                return;
            }

            // 【核心优化 4】强制清洗数据，防止相同时间戳导致图表完全崩溃罢工
            const formatted = data.map(d => ({ 
                time: Math.floor(d[0] / 1000), 
                open: parseFloat(d[1]), 
                high: parseFloat(d[2]), 
                low: parseFloat(d[3]), 
                close: parseFloat(d[4]) 
            }));
            
            const uniqueData =[];
            let lastTime = -1;
            
            formatted.forEach(item => {
                if (item.time > lastTime && !isNaN(item.time)) {
                    uniqueData.push(item);
                    lastTime = item.time;
                }
            });

            if (uniqueData.length > 0) {
                try {
                    state.candleSeries.setData(uniqueData);
                    state.lastCandle = uniqueData[uniqueData.length - 1]; 
                    state.chartInst.timeScale().fitContent();
                } catch(e) { console.error("K线渲染引擎报错:", e); }
            }
        }

        function updateRealtimeCandle(price) {
            if(!state.lastCandle || !state.candleSeries) return;
            const now = Math.floor(Date.now() / 1000); 
            const tfSeconds = { '1m': 60, '15m': 900, '1h': 3600, '4h': 14400, '1d': 86400 }[state.chartTF];
            
            if(now >= state.lastCandle.time + tfSeconds) {
                state.lastCandle = { time: state.lastCandle.time + tfSeconds, open: price, high: price, low: price, close: price };
            } else { 
                state.lastCandle.high = Math.max(state.lastCandle.high, price); 
                state.lastCandle.low = Math.min(state.lastCandle.low, price); 
                state.lastCandle.close = price; 
            }
            
            try { state.candleSeries.update(state.lastCandle); } catch(e) {}
            
            const titlePrice = document.getElementById('chart-current-price');
            titlePrice.innerText = '$' + (price < 1 ? price.toFixed(4) : price.toFixed(2));
            titlePrice.style.color = state.lastCandle.close >= state.lastCandle.open ? 'var(--up-green)' : 'var(--down-red)';
        }

        function updateEquityUI() {
            let totalMarginUsed = 0, totalUnrealizedPNL = 0;
            state.positions.forEach(p => {
                totalMarginUsed += p.margin;
                const curPrice = state.prices[p.coin] || p.entry;
                totalUnrealizedPNL += p.side === 'long' ? (curPrice - p.entry)*p.amount : (p.entry - curPrice)*p.amount;
            });
            const equity = state.balance + totalUnrealizedPNL;
            const available = state.balance - totalMarginUsed;
            document.getElementById('total-equity').innerText = equity.toFixed(2);
            document.getElementById('avail-bal').innerText = `可用: ${available.toFixed(2)}`;
            
            if(equity <= 0) document.getElementById('total-equity').style.color = 'var(--down-red)';
            else document.getElementById('total-equity').style.color = 'var(--primary)';
            return available;
        }

        function resetAccount() {
            if(confirm('重置会清空所有持仓和交割单历史，确认操作？')) {
                state.balance = 5000000; state.positions =[]; state.history =[];
                localStorage.setItem('mock_balance', state.balance); 
                localStorage.setItem('mock_pos', '[]');
                localStorage.setItem('mock_history', '[]');
                renderPositions(); renderHistory(); updateEquityUI();
                showToast('🔄 账户与交割单已重置！', 'success');
            }
        }

        function openWithdrawModal() { document.getElementById('withdraw-modal').style.display = 'flex'; }
        function closeWithdrawModal() { document.getElementById('withdraw-modal').style.display = 'none'; document.getElementById('withdraw-amount').value = ''; }
        
        function confirmWithdraw() {
            const amount = parseFloat(document.getElementById('withdraw-amount').value);
            if (isNaN(amount) || amount <= 0) return showToast('请输入有效的提现金额', 'error');
            const avail = updateEquityUI();
            if (amount > avail) return showToast(`提现不能超过可用余额 (${avail.toFixed(2)})！`, 'error');

            state.balance -= amount;
            localStorage.setItem('mock_balance', state.balance);
            updateEquityUI();
            closeWithdrawModal();
            showToast(`🎉 成功出金 ${amount} USDT！`, 'success');
        }

        function updatePreview() {
            const coin = document.getElementById('t-coin').value, side = document.getElementById('t-side').value;
            const lev = parseInt(document.getElementById('t-lev').value) || 100, margin = parseFloat(document.getElementById('t-margin').value) || 0;
            const tp = parseFloat(document.getElementById('t-tp').value) || 0, sl = parseFloat(document.getElementById('t-sl').value) || 0;
            const curPrice = state.prices[coin];
            
            if (!curPrice || margin <= 0) { document.getElementById('prev-liq').innerText = '--'; document.getElementById('prev-tp').innerText = '--'; document.getElementById('prev-sl').innerText = '--'; return; }

            const amount = (margin * lev) / curPrice;
            let liqPrice = side === 'long' ? curPrice * (1 - 1/lev) : curPrice * (1 + 1/lev);
            
            let tpPnl = 0, slPnl = 0;
            if (side === 'long') {
                if (tp > 0) tpPnl = (tp - curPrice) * amount;
                if (sl > 0) slPnl = (curPrice - sl) * amount;
            } else {
                if (tp > 0) tpPnl = (curPrice - tp) * amount;
                if (sl > 0) slPnl = (sl - curPrice) * amount;
            }

            document.getElementById('prev-liq').innerText = '$' + liqPrice.toFixed(4);
            document.getElementById('prev-tp').innerText = tp > 0 ? `+${tpPnl.toFixed(2)} U` : '未设置';
            document.getElementById('prev-sl').innerText = sl > 0 ? `-${slPnl.toFixed(2)} U` : '裸奔将清空余额';
        }

        function executeTrade() {
            const coin = document.getElementById('t-coin').value, side = document.getElementById('t-side').value;
            const lev = Math.min(Math.max(parseInt(document.getElementById('t-lev').value)||1, 1), 1000); 
            const margin = parseFloat(document.getElementById('t-margin').value);
            const tp = parseFloat(document.getElementById('t-tp').value) || null, sl = parseFloat(document.getElementById('t-sl').value) || null;
            
            const curPrice = state.prices[coin];
            if(!curPrice) return showToast(`正在连通节点，请稍候`, 'error');
            if(!margin || margin <= 0) return showToast('请输入有效保证金！', 'error');
            
            const available = updateEquityUI();
            if(margin > available) return showToast(`可用余额不足！`, 'error');

            const liqPrice = side === 'long' ? curPrice * (1 - 1/lev) : curPrice * (1 + 1/lev);
            
            if (side === 'long' && sl && sl <= liqPrice) return showToast(`多单止损不能等于/低于强平价`, 'error');
            if (side === 'short' && sl && sl >= liqPrice) return showToast(`空单止损不能等于/高于强平价`, 'error');

            const amount = (margin * lev) / curPrice;
            state.positions.unshift({ id: Date.now().toString(), coin, side, lev, margin, entry: curPrice, amount, tp, sl, liq: liqPrice, openTime: Date.now() });
            
            localStorage.setItem('mock_pos', JSON.stringify(state.positions));
            document.getElementById('t-tp').value = ''; document.getElementById('t-sl').value = '';
            
            showToast(`✅ 建仓成功`, 'success');
            renderPositions(); updateEquityUI();
        }

        function openTPSLModal(id) {
            const p = state.positions.find(x => x.id === id);
            if(!p) return;
            document.getElementById('modal-pos-id').value = id;
            document.getElementById('modal-title').innerText = `⚙️ 修改 ${p.coin} 止盈止损`;
            document.getElementById('modal-tp').value = p.tp || '';
            document.getElementById('modal-sl').value = p.sl || '';
            document.getElementById('tpsl-modal').style.display = 'flex';
        }

        function closeTPSLModal() { document.getElementById('tpsl-modal').style.display = 'none'; }

        function saveTPSL() {
            const id = document.getElementById('modal-pos-id').value;
            const p = state.positions.find(x => x.id === id);
            if(!p) return closeTPSLModal();

            const tpVal = parseFloat(document.getElementById('modal-tp').value) || null;
            const slVal = parseFloat(document.getElementById('modal-sl').value) || null;

            p.tp = tpVal; p.sl = slVal;
            localStorage.setItem('mock_pos', JSON.stringify(state.positions));
            closeTPSLModal(); renderPositions();
            showToast(`✅ 更新成功！`, 'success');
        }

        function fastCalculatePNL() {
            if(state.positions.length === 0) return;
            let totalUnrealizedPNL = 0, totalMarginUsed = 0;
            
            for (let i = state.positions.length - 1; i >= 0; i--) {
                const p = state.positions[i];
                const curPrice = state.prices[p.coin]; if(!curPrice) continue;
                
                let isClosed = false;
                if (p.side === 'long') {
                    if (p.tp && curPrice >= p.tp) isClosed = triggerClose(i, '止盈 (TP)', p.tp);
                    else if (p.sl && curPrice <= p.sl) isClosed = triggerClose(i, '止损 (SL)', p.sl);
                    else if (curPrice <= p.liq) isClosed = triggerLiquidation(i);
                } else {
                    if (p.tp && curPrice <= p.tp) isClosed = triggerClose(i, '止盈 (TP)', p.tp);
                    else if (p.sl && curPrice >= p.sl) isClosed = triggerClose(i, '止损 (SL)', p.sl);
                    else if (curPrice >= p.liq) isClosed = triggerLiquidation(i);
                }
                if(isClosed) continue; 

                totalMarginUsed += p.margin;
                let pnl = p.side === 'long' ? (curPrice - p.entry)*p.amount : (p.entry - curPrice)*p.amount;
                totalUnrealizedPNL += pnl;
                let roe = (pnl / p.margin) * 100;

                const color = pnl >= 0 ? 'var(--up-green)' : 'var(--down-red)', sign = pnl >= 0 ? '+' : '';
                const elPrice = document.getElementById(`pos-price-${p.id}`), elPnl = document.getElementById(`pos-pnl-${p.id}`), elRoe = document.getElementById(`pos-roe-${p.id}`);
                
                if(elPrice) elPrice.innerText = curPrice < 1 ? curPrice.toFixed(4) : curPrice.toFixed(2);
                if(elPnl) { elPnl.innerText = sign + pnl.toFixed(2); elPnl.style.color = color; }
                if(elRoe) { elRoe.innerText = sign + roe.toFixed(2) + '%'; elRoe.style.color = color; }
            }

            document.getElementById('total-equity').innerText = (state.balance + totalUnrealizedPNL).toFixed(2);
            document.getElementById('avail-bal').innerText = `可用: ${(state.balance - totalMarginUsed).toFixed(2)}`;
        }

        function saveHistory(position, finalPrice, pnl, reason) {
            const histObj = { ...position, closePrice: finalPrice, closeTime: Date.now(), realizedPnl: pnl, roe: (pnl / position.margin) * 100, reason: reason };
            state.history.unshift(histObj);
            if(state.history.length > 50) state.history.pop(); 
            localStorage.setItem('mock_history', JSON.stringify(state.history));
            renderHistory();
        }

        function triggerClose(index, reason, exitPrice = null) {
            const p = state.positions[index];
            const finalPrice = exitPrice || state.prices[p.coin];
            let pnl = p.side === 'long' ? (finalPrice - p.entry)*p.amount : (p.entry - finalPrice)*p.amount;
            
            state.balance += pnl; 
            saveHistory(p, finalPrice, pnl, reason);
            state.positions.splice(index, 1);
            showToast(`🔔 ${reason}平仓，盈亏: ${pnl>=0?'+':''}${pnl.toFixed(2)} U`, pnl>=0?'success':'error');
            localStorage.setItem('mock_balance', state.balance); localStorage.setItem('mock_pos', JSON.stringify(state.positions));
            renderPositions(); updateEquityUI(); return true;
        }

        function triggerLiquidation(index) {
            const p = state.positions[index];
            let finalPrice = p.liq; let pnl = 0; let reasonStr = '';

            if (!p.sl) { pnl = -p.margin; state.balance = 0; reasonStr = '💀 爆仓归零'; showToast(`💀 爆仓！余额被清零！`, 'error'); } 
            else { finalPrice = p.sl; pnl = p.side === 'long' ? (p.sl - p.entry)*p.amount : (p.entry - p.sl)*p.amount; state.balance += pnl; reasonStr = '⚠️ 强平截断'; showToast(`⚠️ 触发底线！已按截断处理！`, 'error'); }
            
            saveHistory(p, finalPrice, pnl, reasonStr);
            state.positions.splice(index, 1);
            localStorage.setItem('mock_balance', state.balance); localStorage.setItem('mock_pos', JSON.stringify(state.positions));
            renderPositions(); updateEquityUI(); return true;
        }

        function manualClose(id) {
            const index = state.positions.findIndex(p => p.id === id);
            if(index > -1) triggerClose(index, '市价平仓');
        }

        function formatTime(ts) {
            const d = new Date(ts);
            return `${(d.getMonth()+1).toString().padStart(2,'0')}-${d.getDate().toString().padStart(2,'0')} ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;
        }

        function switchPosTab(tab) {
            document.querySelectorAll('.pos-tab').forEach(el => el.classList.remove('active'));
            if(tab === 'active') {
                document.getElementById('tab-active').classList.add('active');
                document.getElementById('positions-container').style.display = 'block';
                document.getElementById('history-container').style.display = 'none';
            } else {
                document.getElementById('tab-history').classList.add('active');
                document.getElementById('positions-container').style.display = 'none';
                document.getElementById('history-container').style.display = 'block';
            }
        }

        function renderPositions() {
            const container = document.getElementById('positions-container');
            document.getElementById('pos-count').innerText = state.positions.length;
            if(state.positions.length === 0) { container.innerHTML = '<div style="text-align:center;color:var(--border);padding:30px;font-weight:bold;">您当前没有任何持仓</div>'; return; }

            container.innerHTML = state.positions.map(p => `
                <div class="pos-card">
                    <div class="pos-line ${p.side}"></div>
                    <div class="pos-header">
                        <div class="pos-tag ${p.side === 'long' ? 'up' : 'down'}">${p.coin} ${p.side==='long'?'多单':'空单'} · ${p.lev}X</div>
                        <button class="close-btn" onclick="manualClose('${p.id}')">⚡ 闪电平仓</button>
                    </div>
                    <div class="pos-grid">
                        <div class="grid-item"><span>开仓均价</span><span class="grid-val">$${p.entry.toFixed(4)}</span></div>
                        <div class="grid-item"><span>标记现价</span><span class="grid-val">$<span id="pos-price-${p.id}">--</span></span></div>
                        <div class="grid-item"><span>预估强平</span><span class="grid-val" style="color:var(--down-red)">$${p.liq.toFixed(4)}</span></div>
                        <div class="grid-item"><span>保证金</span><span class="grid-val">$${p.margin.toFixed(2)}</span></div>
                        <div class="grid-item" style="cursor:pointer; background:rgba(14,203,129,0.05); padding:6px; border-radius:6px;" onclick="openTPSLModal('${p.id}')">
                            <span style="color:var(--text-muted); font-size:11px;">止盈(TP)</span><span class="grid-val up">${p.tp ? '$'+p.tp : '点击设置'}</span>
                        </div>
                        <div class="grid-item" style="cursor:pointer; background:rgba(246,70,93,0.05); padding:6px; border-radius:6px;" onclick="openTPSLModal('${p.id}')">
                            <span style="color:var(--text-muted); font-size:11px;">止损(SL)</span><span class="grid-val down">${p.sl ? '$'+p.sl : '点击设置'}</span>
                        </div>
                    </div>
                    <div class="pnl-row">
                        <div style="display:flex; flex-direction:column;"><span style="font-size:11px; color:var(--text-muted); margin-bottom:4px;">未实现盈亏</span><span class="pnl-value" id="pos-pnl-${p.id}">0.00</span></div>
                        <div style="display:flex; flex-direction:column; align-items:flex-end;"><span style="font-size:11px; color:var(--text-muted); margin-bottom:4px;">收益率(ROE)</span><span class="roe-value" id="pos-roe-${p.id}">0.00%</span></div>
                    </div>
                </div>`).join('');
            fastCalculatePNL(); 
        }

        function renderHistory() {
            const container = document.getElementById('history-container');
            if(state.history.length === 0) { container.innerHTML = '<div style="text-align:center;color:var(--border);padding:30px;font-weight:bold;">暂无交割单记录</div>'; return; }
            let html = state.history.map(h => {
                const isProfit = h.realizedPnl >= 0; const color = isProfit ? 'var(--up-green)' : 'var(--down-red)';
                return `
                <div class="pos-card" style="opacity: 0.9;">
                    <div class="pos-line ${h.side}" style="background:${color}; box-shadow:none;"></div>
                    <div class="pos-header" style="border-bottom:none; margin-bottom:4px;">
                        <div class="pos-tag" style="color:${color};">${h.coin} ${h.side==='long'?'多单':'空单'} · ${h.lev}X</div>
                        <div class="history-reason" style="background:rgba(255,255,255,0.1)">${h.reason}</div>
                    </div>
                    <div class="pos-grid" style="margin-bottom: 8px;">
                        <div class="grid-item"><span>建仓价</span><span class="grid-val">$${h.entry.toFixed(4)}</span></div>
                        <div class="grid-item"><span>平仓价</span><span class="grid-val">$${h.closePrice.toFixed(4)}</span></div>
                        <div class="grid-item"><span>时间</span><span class="grid-val" style="font-weight:normal; font-size:11px;">${formatTime(h.closeTime)}</span></div>
                    </div>
                    <div class="pnl-row" style="background:transparent; padding:0; border:none; margin-top:8px; border-top: 1px dashed rgba(255,255,255,0.05); padding-top: 8px;">
                        <div style="display:flex; flex-direction:column;"><span style="font-size:11px; color:var(--text-muted);">已实现盈亏</span><span class="pnl-value" style="color:${color}; font-size:20px;">${isProfit?'+':''}${h.realizedPnl.toFixed(2)}</span></div>
                        <div style="display:flex; flex-direction:column; align-items:flex-end;"><span style="font-size:11px; color:var(--text-muted);">净收益率</span><span class="roe-value" style="color:${color}">${isProfit?'+':''}${h.roe.toFixed(2)}%</span></div>
                    </div>
                </div>`}).join('');
            html += `<div class="clear-hist-btn" onclick="clearHistory()">🗑️ 清空所有历史</div>`;
            container.innerHTML = html;
        }

        function clearHistory() {
            if(confirm('清空这台设备上的所有历史记录？')) { state.history =[]; localStorage.setItem('mock_history', '[]'); renderHistory(); }
        }

        function appendChat(role, content, save=true) {
            const box = document.getElementById('chat-box');
            let htmlContent = content.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            box.innerHTML += `<div class="msg-row ${role}"><div class="msg-bubble">${htmlContent}</div></div>`;
            box.scrollTop = box.scrollHeight;
            if(save) { state.chatHistory.push({role, content}); localStorage.setItem('mock_chat', JSON.stringify(state.chatHistory)); }
        }

        function renderChatHistory() {
            state.chatHistory.forEach(m => {
                const box = document.getElementById('chat-box');
                let htmlContent = m.content.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                box.innerHTML += `<div class="msg-row ${m.role}"><div class="msg-bubble">${htmlContent}</div></div>`;
            });
            setTimeout(()=> document.getElementById('chat-box').scrollTop = 9999, 100);
        }

        async function sendAI() {
            const input = document.getElementById('chat-input'), text = input.value.trim();
            if(!text) return;
            appendChat('user', text); input.value = '';
            
            const box = document.getElementById('chat-box'), typingId = 'typing-' + Date.now();
            box.innerHTML += `<div class="msg-row ai" id="${typingId}"><div class="msg-bubble" style="color:var(--ai-glow); font-family:monospace;">思考中<span class="pulse" style="display:inline-block; margin-left:8px;"></span></div></div>`;
            box.scrollTop = box.scrollHeight;

            try {
                let messages =[{ role: 'system', content: `你是基于 OpenClaw 的智能代理，请提供极高同理心和准确盘面分析。` }];
                state.chatHistory.slice(-8).forEach(m => messages.push({ role: (m.role === 'ai' ? 'assistant' : 'user'), content: m.content }));
                
                let coinRef = TOP_COINS.find(c => text.toUpperCase().includes(c));
                let envData = coinRef ? `当前 ${coinRef} 实时价: $${state.prices[coinRef]||'未知'}` : `BTC市价: $${state.prices['BTC']||'未知'}`;
                
                messages.pop(); 
                messages.push({ role: 'user', content: `[隐藏数据注入: ${envData}]\n\n用户说: ${text}` });

                const res = await fetch('https://text.pollinations.ai/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ messages, model: "openai" }) });
                document.getElementById(typingId).remove();
                if(!res.ok) throw new Error();
                appendChat('ai', await res.text());
            } catch(e) { 
                document.getElementById(typingId).remove(); appendChat('ai', "⚠️ 连接超时，稍后重试。"); 
            }
        }

        function switchTab(tabId, el) {
            document.querySelectorAll('.tab-content, .tab-item').forEach(e => e.classList.remove('active'));
            document.getElementById(tabId).classList.add('active'); el.classList.add('active');
            
            if(tabId === 'portfolio' && state.chartInst) {
                setTimeout(() => { 
                    const container = document.getElementById('tvchart'); 
                    if(container.clientWidth > 0) state.chartInst.resize(container.clientWidth, 320); 
                }, 100);
            }
            if(tabId === 'ai') setTimeout(()=> document.getElementById('chat-box').scrollTop = 9999, 50);
        }

        window.addEventListener('resize', () => {
            if (document.getElementById('portfolio').classList.contains('active') && state.chartInst) {
                const container = document.getElementById('tvchart');
                if(container.clientWidth > 0) state.chartInst.resize(container.clientWidth, 320);
            }
        });
    </script>
</body>
</html>"""

# 3. 将高度设为 1000 以确保不用双滚动条即可完全展示
components.html(HTML_CONTENT, height=1000, scrolling=True)
