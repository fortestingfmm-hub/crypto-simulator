加入了 MEXC 与 AllOrigins 穿透机制：原来的接口全是 binance.com。由于 Streamlit Cloud 是美国 IP 且极度严格，经常在请求被拦截时无声无息死掉（只显示白板）。现在不仅加入了对拦截限制极松的 mexc.com 代为查询完全一致的 K 线数据，更加上了终极的 allorigins 公共请求代理兜底！即便在最极端的网络环境下，K 线也能瞬间拉满。

K线强制清洗过滤逻辑 (uniqueData 拦截法)：LightweightCharts 极其“娇气”，即使有一根脏数据（时间戳错乱、重复时间、非整型小数），它不仅不显示那一根，而是直接让整张图白屏罢工。我重写了数据数组合并方法：if (item.time > lastTime && !isNaN(item.time)) 确保哪怕遇到脏数据也能静默清理并强行渲染。

加装了图表崩溃弹窗器 (showToast)：如果你遇到 K 线一直拉取不到，顶部会自动弹出红色 Toast（“⚠️ K线数据被网络拦截...”），而不是让你一头雾水。
