2026.3.06 11.32.17
强行锁定时间排序验证 (if t > lastTimestamp)：之前的 Bug 是因为币安 API 的 1天/4小时级别的部分历史数据偶尔不按照顺序返回，或者包含重复时间，V3 的 Lightweight-charts 对时间强迫症极强，一旦乱序会使得整个图表组件崩溃。现在加了“清洗墙”，保证送给图表的数据绝对纯净。

抛弃 ResizeObserver，引入 autoSize: true (V4)：我在 <head> 里引入了 lightweight-charts.standalone.production.js (V4 官方版)。V4 原生支持了 autoSize 参数，它完全接管了屏幕尺寸自动调整，无论 Streamlit 的 iframe 怎么抽风或者在手机上横竖屏怎么转，图表都不会再变成 width=0 导致崩溃了。

加载指示器 (#chart-loading)：现在 K 线图面板在获取数据时中间会显示 📡 正在连接行情节点...。如果因为网络问题拉取失败，它会直观地显示出错误而不是干巴巴一片黑屏，让你一眼就能知道当前状态。
2026.3.6
加入了 MEXC 与 AllOrigins 穿透机制：原来的接口全是 binance.com。由于 Streamlit Cloud 是美国 IP 且极度严格，经常在请求被拦截时无声无息死掉（只显示白板）。现在不仅加入了对拦截限制极松的 mexc.com 代为查询完全一致的 K 线数据，更加上了终极的 allorigins 公共请求代理兜底！即便在最极端的网络环境下，K 线也能瞬间拉满。

K线强制清洗过滤逻辑 (uniqueData 拦截法)：LightweightCharts 极其“娇气”，即使有一根脏数据（时间戳错乱、重复时间、非整型小数），它不仅不显示那一根，而是直接让整张图白屏罢工。我重写了数据数组合并方法：if (item.time > lastTime && !isNaN(item.time)) 确保哪怕遇到脏数据也能静默清理并强行渲染。

加装了图表崩溃弹窗器 (showToast)：如果你遇到 K 线一直拉取不到，顶部会自动弹出红色 Toast（“⚠️ K线数据被网络拦截...”），而不是让你一头雾水。
