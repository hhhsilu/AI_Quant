# 狮头股份技术指标 Notebook Spec

## 1. 目标

基于狮头股份 `600539.SH` 的日价格数据，设计一个 Jupyter Notebook，完整展示技术指标的计算过程、结果校验和图表解读。首批指标包括：

- RSI，相对强弱指标
- MACD，指数平滑异同移动平均线
- Bollinger Bands，布林带
- ATR，平均真实波幅

本 spec 仅规划 notebook 的结构、数据契约、计算逻辑和验收标准，不要求在当前阶段实现代码。

## 2. 数据输入

优先使用课程 02 中已补充的前复权数据：

```text
/Users/huangsilu/Documents/quant_course_02/data/shitou_600539_qfq_daily.csv
/Users/huangsilu/Documents/quant_course_02/data/shitou_600539_qfq_daily.json
```

原始日行情数据来源：

```text
/Users/huangsilu/Documents/quant_course_01/data/shitou_600539_daily.csv
/Users/huangsilu/Documents/quant_course_01/data/shitou_600539_daily.json
```

推荐在 `quant_course_02` 中建立独立数据副本，避免课程 02 的 notebook 依赖课程 01 的相对路径：

```text
quant_course_02/
  data/
    shitou_600539_qfq_daily.csv
    shitou_600539_qfq_daily.json
  notebooks/
    shitou_technical_indicators.ipynb
  docs/
    shitou_indicator_notebook_spec.md
```

当前数据字段：

| field | description | usage |
| --- | --- | --- |
| `date` | 交易日期，`YYYYMMDD` | 时间索引 |
| `open` | 开盘价 | ATR、K线展示 |
| `high` | 最高价 | ATR、K线展示 |
| `low` | 最低价 | ATR、K线展示 |
| `close` | 收盘价 | RSI、MACD、布林带 |
| `pre_close` | 前收盘价 | 涨跌校验、ATR 对照 |
| `change` | 涨跌额 | 数据校验 |
| `pct_chg` | 涨跌幅 | 辅助观察 |
| `volume_hands` | 成交量，手 | 可选副图 |
| `volume_shares` | 成交股数 | 可选副图 |
| `amount_thousand_yuan` | 成交额，千元 | 可选副图 |

注意：课程 02 数据使用 Tushare `daily + adj_factor` 生成，`metadata.adjust = "qfq"`。主价格字段 `open/high/low/close/pre_close/change/pct_chg` 为前复权口径，原始未复权字段保留为 `raw_*`。

## 3. Notebook 受众与风格

Notebook 面向量化课程学习者，应优先展示“为什么这样算”和“计算结果如何理解”。每个指标都应包含：

1. 指标含义说明。
2. 参数设定。
3. 逐步计算逻辑。
4. 结果表格预览。
5. 图表展示。
6. 简短解读。

避免把 notebook 写成只有代码和图的黑盒。每个核心计算单元前应有 Markdown 解释。

## 4. Notebook 章节规划

### 4.1 标题与任务说明

Notebook 标题：

```text
狮头股份 600539.SH 技术指标计算：RSI、MACD、布林带、ATR
```

开头说明：

- 股票名称：狮头股份
- 股票代码：`600539.SH`
- 数据频率：日线
- 数据来源：Tushare daily，或后续升级为 Tushare daily + adj_factor
- 数据区间：从数据文件 metadata 或 CSV 首末日期读取
- 指标：RSI、MACD、布林带、ATR

### 4.2 环境与依赖

建议使用：

- `pandas`：数据读取和滚动计算
- `numpy`：数值计算
- `matplotlib`：基础图表

可选：

- `plotly`：交互式图表
- `mplfinance`：K线图

Notebook 应避免在正文中安装依赖。若必须安装，应放在单独的“环境准备”小节并说明只需运行一次。

### 4.3 数据读取与整理

步骤：

1. 读取 CSV。
2. 将 `date` 转换为日期类型。
3. 按日期升序排序。
4. 设置日期为索引，或保留为显式列。
5. 检查缺失值、重复日期和 OHLC 合理性。

必要校验：

| check | rule |
| --- | --- |
| 非空 | 行数大于 0 |
| 日期唯一 | `date` 不重复 |
| 日期顺序 | 日期升序 |
| OHLC | `low <= open <= high` 且 `low <= close <= high` |
| 成交量 | `volume_hands >= 0` |

建议输出：

- 数据前 5 行
- 数据后 5 行
- 日期范围
- 总交易日数量
- 缺失值统计

## 5. 指标计算规范

### 5.1 RSI

默认参数：

| parameter | value |
| --- | --- |
| period | 14 |
| price | `close` |
| smoothing | Wilder smoothing |

计算逻辑：

1. 计算收盘价差分：`delta = close.diff()`。
2. 上涨幅度：`gain = max(delta, 0)`。
3. 下跌幅度：`loss = max(-delta, 0)`。
4. 计算平均上涨和平均下跌，默认采用 Wilder 平滑。
5. `RS = avg_gain / avg_loss`。
6. `RSI = 100 - 100 / (1 + RS)`。

结果字段：

| field | description |
| --- | --- |
| `rsi_14` | 14 日 RSI |

展示要求：

- 上图：收盘价走势。
- 下图：`rsi_14` 曲线。
- 添加 70 和 30 参考线。

解读提示：

- RSI 高于 70 通常表示短期偏热，但不等于必须下跌。
- RSI 低于 30 通常表示短期偏弱，但不等于必须上涨。
- 可观察价格创新高而 RSI 未创新高的背离现象。

### 5.2 MACD

默认参数：

| parameter | value |
| --- | --- |
| fast | 12 |
| slow | 26 |
| signal | 9 |
| price | `close` |
| moving average | EMA |

计算逻辑：

1. `ema_fast = close.ewm(span=12).mean()`。
2. `ema_slow = close.ewm(span=26).mean()`。
3. `macd_dif = ema_fast - ema_slow`。
4. `macd_dea = macd_dif.ewm(span=9).mean()`。
5. `macd_hist = macd_dif - macd_dea`。

结果字段：

| field | description |
| --- | --- |
| `macd_dif` | 快慢均线差 |
| `macd_dea` | DIF 的信号线 |
| `macd_hist` | MACD 柱，`DIF - DEA` |

展示要求：

- 上图：收盘价走势。
- 下图：DIF、DEA 两条线和 MACD 柱状图。
- 柱状图建议正值和负值用不同颜色。

解读提示：

- DIF 上穿 DEA，常称为金叉，说明短期动量转强。
- DIF 下穿 DEA，常称为死叉，说明短期动量转弱。
- MACD 柱扩大表示动量增强，收缩表示动量减弱。

### 5.3 布林带

默认参数：

| parameter | value |
| --- | --- |
| period | 20 |
| std_multiplier | 2 |
| price | `close` |

计算逻辑：

1. `bb_mid = close.rolling(20).mean()`。
2. `bb_std = close.rolling(20).std()`。
3. `bb_upper = bb_mid + 2 * bb_std`。
4. `bb_lower = bb_mid - 2 * bb_std`。
5. `bb_width = (bb_upper - bb_lower) / bb_mid`。
6. `bb_percent_b = (close - bb_lower) / (bb_upper - bb_lower)`。

结果字段：

| field | description |
| --- | --- |
| `bb_mid_20` | 20 日中轨 |
| `bb_upper_20` | 上轨 |
| `bb_lower_20` | 下轨 |
| `bb_width_20` | 布林带宽度 |
| `bb_percent_b_20` | 收盘价在上下轨之间的相对位置 |

展示要求：

- 收盘价、布林带上轨、中轨、下轨绘制在同一图中。
- 可在第二张图展示 `bb_width_20`，观察波动收缩和扩张。

解读提示：

- 价格接近上轨表示处于近期相对高位。
- 价格接近下轨表示处于近期相对低位。
- 布林带收窄说明波动降低，可能在酝酿方向选择。
- 布林带变宽说明波动增强。

### 5.4 ATR

默认参数：

| parameter | value |
| --- | --- |
| period | 14 |
| price fields | `high`, `low`, `close` |
| smoothing | rolling mean or Wilder smoothing; notebook 中需明确说明选择 |

推荐采用 Wilder smoothing，与多数技术分析软件保持一致。

计算逻辑：

1. `tr_1 = high - low`。
2. `tr_2 = abs(high - close.shift(1))`。
3. `tr_3 = abs(low - close.shift(1))`。
4. `true_range = max(tr_1, tr_2, tr_3)`。
5. `atr_14 = true_range` 的 14 日 Wilder 平滑。

结果字段：

| field | description |
| --- | --- |
| `true_range` | 真实波幅 |
| `atr_14` | 14 日平均真实波幅 |
| `atr_pct_14` | `atr_14 / close * 100`，波动幅度占收盘价比例 |

展示要求：

- 上图：收盘价走势。
- 下图：`atr_14` 或 `atr_pct_14`。
- 推荐同时展示 `atr_pct_14`，便于和不同价格区间比较。

解读提示：

- ATR 上升表示波动扩大，不代表方向一定向上。
- ATR 下降表示波动收敛。
- ATR 可用于风险控制，例如设置止损距离或观察行情是否进入高波动状态。

## 6. 汇总结果表

Notebook 最后应生成一个包含原始行情和全部指标的汇总表。

建议字段顺序：

```text
date, open, high, low, close, volume_hands,
rsi_14,
macd_dif, macd_dea, macd_hist,
bb_mid_20, bb_upper_20, bb_lower_20, bb_width_20, bb_percent_b_20,
true_range, atr_14, atr_pct_14
```

建议输出文件：

```text
quant_course_02/output/shitou_600539_indicators.csv
quant_course_02/output/shitou_600539_indicators.json
```

## 7. 图表规划

Notebook 至少包含 4 组图：

| chart | content |
| --- | --- |
| 价格与 RSI | 收盘价 + RSI 14，含 70/30 参考线 |
| 价格与 MACD | 收盘价 + DIF/DEA/MACD 柱 |
| 价格与布林带 | 收盘价 + 上轨/中轨/下轨 |
| 价格与 ATR | 收盘价 + ATR 14 或 ATR 百分比 |

图表要求：

- 所有图表应有标题、坐标轴标签和图例。
- 横轴使用真实日期，而不是行号。
- 指标图不要和价格图强行共用同一纵轴，避免误读。
- 对前 N 个因滚动窗口不足产生的空值，要在说明中解释。

## 8. Notebook 叙事结构

推荐叙事顺序：

1. 数据背景：说明狮头股份、数据区间、数据字段。
2. 数据质量检查：确认数据可用于计算。
3. RSI：从涨跌幅度理解短期强弱。
4. MACD：从均线差理解趋势动量。
5. 布林带：从均值和标准差理解价格区间。
6. ATR：从真实波幅理解风险和波动。
7. 指标汇总：合并成一个分析表。
8. 小结：说明四个指标分别回答什么问题。

小结建议：

| indicator | answers |
| --- | --- |
| RSI | 最近上涨和下跌力量谁更强 |
| MACD | 趋势动量是否增强或转弱 |
| 布林带 | 价格相对近期均值和波动区间的位置 |
| ATR | 当前波动和风险幅度有多大 |

## 9. 参数配置建议

建议在 notebook 顶部集中定义参数：

```text
STOCK_NAME = "狮头股份"
TS_CODE = "600539.SH"
DATA_PATH = "../data/shitou_600539_qfq_daily.csv"
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BB_PERIOD = 20
BB_STD_MULTIPLIER = 2
ATR_PERIOD = 14
```

这样后续可复用到其他股票，例如中芯国际、比亚迪、三峡能源。

## 10. 验收标准

Notebook 完成后应满足：

1. 能从头到尾顺序运行，无隐藏状态依赖。
2. 能成功读取狮头股份日线数据。
3. 能输出 RSI、MACD、布林带、ATR 的计算结果。
4. 每个指标至少有一个 Markdown 原理说明、一个计算过程、一个图表和一个简短解读。
5. 汇总表包含原始行情和全部指标字段。
6. 图表横轴为交易日期，标题清晰。
7. 对滚动窗口导致的初始空值有说明。
8. Notebook 必须读取 `metadata.adjust` 或在说明中明确记录复权口径，本课程默认使用前复权 `qfq`。

## 11. 后续扩展

可在完成基础 notebook 后扩展：

- 增加 K 线图和成交量副图。
- 增加交易信号示例，例如 RSI 超买超卖、MACD 金叉死叉。
- 增加参数敏感性分析，例如 RSI 6/14/24 对比。
- 增加复权价格版本，与未复权价格指标进行对比。
- 扩展为多股票批量 notebook 模板。
