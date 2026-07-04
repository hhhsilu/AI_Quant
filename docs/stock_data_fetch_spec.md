# 典型股票规范化取数 Spec

## 1. 目标

建立一套可重复、可校验、可扩展的股票复权日行情取数规范，用于未来批量获取典型股票数据，并稳定输出给分析脚本、可视化面板或课程材料使用。

首批覆盖股票：

| stock_name | ts_code | exchange | market | role |
| --- | --- | --- | --- | --- |
| 狮头股份 | 600539.SH | 上交所 | A股主板 | 既有样例，延续当前项目基准 |
| 中芯国际 | 688981.SH | 上交所 | 科创板 | 半导体制造代表 |
| 比亚迪 | 002594.SZ | 深交所 | A股主板 | 新能源汽车代表 |
| 三峡能源 | 600905.SH | 上交所 | A股主板 | 绿色电力代表 |

说明：中芯国际同时有港股代码 `00981.HK`。本规范首批按 A 股 `688981.SH` 取数；如未来需要做 AH 股对照，应新增独立配置项，而不是复用同一 `ts_code`。

## 2. 数据源

默认数据源为 Tushare Pro。

- 日行情接口：`daily`
- 股票基础信息接口：`stock_basic`
- 交易日历接口：`trade_cal`
- 复权因子接口：`adj_factor`

复权口径：

- 默认使用前复权：`qfq`
- 主分析字段 `open/high/low/close/pre_close/change/pct_chg` 采用复权后价格口径。
- 原始未复权行情保留在 `raw_*` 字段，便于审计和与行情源对账。
- 如未来需要后复权，应通过参数显式指定 `--adjust hfq`，并在元数据中记录。

认证顺序：

1. 优先读取环境变量 `TUSHARE_TOKEN`。
2. 若环境变量不存在，可读取 Codex 本地配置中的 Tushare MCP token。
3. 两者都不存在时，脚本必须失败并输出明确错误，不生成半成品数据。

## 3. 取数范围

默认取数窗口：

- `end_date`：运行当天，格式 `YYYYMMDD`
- `start_date`：`end_date` 向前 365 个自然日

可配置参数：

| parameter | type | default | description |
| --- | --- | --- | --- |
| `start_date` | string | today - 365 days | 起始日期，`YYYYMMDD` |
| `end_date` | string | today | 结束日期，`YYYYMMDD` |
| `stocks` | list | 首批四只股票 | 待取数股票清单 |
| `adjust` | enum | `qfq` | 可选：`qfq`, `hfq`, `none`；课程分析默认前复权 |
| `output_formats` | list | `json,csv,js` | 输出格式 |

## 4. 标准字段

每只股票的日行情必须统一输出以下字段。除 `raw_*` 字段外，价格和涨跌字段默认均为复权后口径。

| field | type | unit | source field | description |
| --- | --- | --- | --- | --- |
| `date` | string | `YYYYMMDD` | `trade_date` | 交易日期 |
| `open` | number | CNY | adjusted `open` | 复权开盘价 |
| `high` | number | CNY | adjusted `high` | 复权最高价 |
| `low` | number | CNY | adjusted `low` | 复权最低价 |
| `close` | number | CNY | adjusted `close` | 复权收盘价 |
| `pre_close` | number | CNY | derived | 复权前收盘价 |
| `change` | number | CNY | derived | 复权涨跌额，`close - pre_close` |
| `pct_chg` | number | percent | derived | 复权涨跌幅，`change / pre_close * 100` |
| `volume_hands` | number | hand | `vol` | 成交量，1 手 = 100 股 |
| `volume_shares` | number | share | `vol * 100` | 成交股数 |
| `amount_thousand_yuan` | number | thousand CNY | `amount` | 成交额，千元 |
| `raw_open` | number | CNY | `open` | 原始未复权开盘价 |
| `raw_high` | number | CNY | `high` | 原始未复权最高价 |
| `raw_low` | number | CNY | `low` | 原始未复权最低价 |
| `raw_close` | number | CNY | `close` | 原始未复权收盘价 |
| `raw_pre_close` | number | CNY | `pre_close` | 原始未复权前收盘价 |
| `adj_factor` | number | ratio | `adj_factor` | 复权因子 |

字段约束：

- 所有日期升序排列。
- 数值字段必须转换为数字，不保留字符串数字。
- `volume_shares` 必须由 `volume_hands * 100` 派生。
- `raw_*` 字段必须保留原始未复权行情。
- 当 `adjust = qfq` 时，最近一个交易日的复权价格应与原始价格一致或接近一致。
- 当 `adjust = hfq` 时，最早一个交易日的复权价格应与原始价格一致或接近一致。

复权计算约定：

| adjust | formula |
| --- | --- |
| `qfq` | `adjusted_price = raw_price * adj_factor / latest_adj_factor` |
| `hfq` | `adjusted_price = raw_price * adj_factor / first_adj_factor` |
| `none` | `adjusted_price = raw_price`，仅用于调试或对账 |

## 5. 输出结构

推荐目录：

```text
data/
  stocks/
    600539_SH/
      daily.csv
      daily.json
      daily.js
    688981_SH/
      daily.csv
      daily.json
      daily.js
    002594_SZ/
      daily.csv
      daily.json
      daily.js
    600905_SH/
      daily.csv
      daily.json
      daily.js
  stock_manifest.json
```

为兼容当前项目中的狮头股份面板，可在迁移期继续生成：

```text
data/shitou_600539_daily.csv
data/shitou_600539_daily.json
data/shitou_600539_daily.js
```

迁移期结束后，新功能应优先读取 `data/stocks/<symbol>/daily.*`。

## 6. JSON 格式

每个 `daily.json` 必须包含 `metadata` 和 `data` 两个顶层字段。

```json
{
  "metadata": {
    "stock_name": "狮头股份",
    "ts_code": "600539.SH",
    "exchange": "上交所",
    "market": "A股主板",
    "source": "Tushare daily + adj_factor",
    "requested_start_date": "20250704",
    "requested_end_date": "20260704",
    "record_count": 242,
    "first_trade_date": "20250704",
    "last_trade_date": "20260703",
    "adjust": "qfq",
    "fetched_at": "2026-07-04T10:30:00+08:00",
    "units": {
      "price": "CNY",
      "volume_hands": "hands, 1 hand = 100 shares",
      "volume_shares": "shares",
      "amount_thousand_yuan": "thousand CNY"
    }
  },
  "data": []
}
```

`daily.js` 格式：

```js
window.STOCK_DAILY_600539_SH = { "metadata": {}, "data": [] };
```

变量命名规则：

- 固定前缀：`STOCK_DAILY_`
- `ts_code` 中的 `.` 替换为 `_`
- 全部大写

## 7. Manifest 格式

`data/stock_manifest.json` 记录本批次可用股票，供前端或分析脚本发现数据集。

```json
{
  "generated_at": "2026-07-04T10:30:00+08:00",
  "source": "Tushare",
  "adjust": "qfq",
  "stocks": [
    {
      "stock_name": "狮头股份",
      "ts_code": "600539.SH",
      "symbol_dir": "600539_SH",
      "daily_json": "data/stocks/600539_SH/daily.json",
      "daily_csv": "data/stocks/600539_SH/daily.csv",
      "daily_js": "data/stocks/600539_SH/daily.js"
    }
  ]
}
```

## 8. 工作步骤

### 8.1 准备阶段

1. 确认股票清单：名称、`ts_code`、交易所、板块、样本角色。
2. 确认 Tushare token 可用。
3. 确认日期窗口、复权口径、输出格式；默认复权口径为 `qfq`。
4. 创建或读取统一配置文件，例如 `config/stocks.json`。

### 8.2 取数阶段

1. 对每只股票调用 `daily` 接口获取原始未复权行情。
2. 对同一股票和日期窗口调用 `adj_factor` 接口获取复权因子。
3. 按 `trade_date` 合并日行情和复权因子。
4. 根据 `adjust` 参数计算复权 OHLC、`pre_close`、`change`、`pct_chg`。
5. 保留原始未复权 OHLC 到 `raw_*` 字段。
6. 按标准字段做字段映射和单位转换。
7. 按 `date` 升序排序。
8. 生成单股票 `daily.csv`、`daily.json`、`daily.js`。
9. 汇总生成 `stock_manifest.json`。

### 8.3 校验阶段

每只股票必须执行以下校验：

| check | rule | failure action |
| --- | --- | --- |
| 非空 | `record_count > 0` | 失败并保留错误日志 |
| 日期顺序 | `date` 严格升序 | 失败 |
| 日期唯一 | 不允许重复 `date` | 失败 |
| OHLC 合理性 | `low <= open/close <= high` | 失败 |
| 原始 OHLC 合理性 | `raw_low <= raw_open/raw_close <= raw_high` | 失败 |
| 复权因子 | `adj_factor > 0` | 失败 |
| 复权口径 | `metadata.adjust` 必须为 `qfq`、`hfq` 或 `none` | 失败 |
| 涨跌额 | `change` 应接近 `close - pre_close` | 失败 |
| 成交量 | `volume_hands >= 0` 且 `volume_shares = volume_hands * 100` | 失败 |
| 成交额 | `amount_thousand_yuan >= 0` | 失败 |
| 元数据一致 | `record_count == len(data)` | 失败 |

建议但不强制的校验：

- 将返回日期与 `trade_cal` 中的开市日期做交叉核对。
- 对比 `stock_basic`，确认 `ts_code` 和股票名称匹配。
- 若当日未收盘，允许最后一个交易日不是运行日。

### 8.4 归档阶段

1. 在 `metadata.fetched_at` 记录取数时间。
2. 如需保留历史批次，可同步复制到 `data/archive/YYYYMMDD_HHMMSS/`。
3. 当前版本的数据永远保存在 `data/stocks/<symbol>/daily.*`。

## 9. 推荐脚本接口

未来脚本建议命名为：

```text
scripts/fetch_stock_daily.py
```

建议命令行：

```bash
python3 scripts/fetch_stock_daily.py
python3 scripts/fetch_stock_daily.py --start-date 20250101 --end-date 20260704
python3 scripts/fetch_stock_daily.py --stocks 600539.SH,688981.SH
python3 scripts/fetch_stock_daily.py --adjust hfq --formats json,csv
```

建议配置文件：

```text
config/stocks.json
```

```json
{
  "adjust": "qfq",
  "stocks": [
    {
      "stock_name": "狮头股份",
      "ts_code": "600539.SH",
      "exchange": "上交所",
      "market": "A股主板",
      "role": "既有样例，延续当前项目基准"
    },
    {
      "stock_name": "中芯国际",
      "ts_code": "688981.SH",
      "exchange": "上交所",
      "market": "科创板",
      "role": "半导体制造代表"
    },
    {
      "stock_name": "比亚迪",
      "ts_code": "002594.SZ",
      "exchange": "深交所",
      "market": "A股主板",
      "role": "新能源汽车代表"
    },
    {
      "stock_name": "三峡能源",
      "ts_code": "600905.SH",
      "exchange": "上交所",
      "market": "A股主板",
      "role": "绿色电力代表"
    }
  ]
}
```

## 10. 验收标准

本规范对应的未来取数任务完成后，应满足：

1. 四只股票均生成 `daily.csv`、`daily.json`、`daily.js`。
2. 每个 JSON 文件包含完整 `metadata` 和 `data`。
3. `stock_manifest.json` 能枚举全部股票数据路径。
4. 校验失败时，脚本以非零状态退出，不静默生成错误数据。
5. 当前狮头股份面板在迁移期仍可打开。
6. README 或课程说明中记录运行命令和 token 配置方式。

## 11. 后续扩展

可在此规范基础上逐步扩展：

- 增加指数数据，例如沪深300、中证全指、创业板指。
- 增加估值指标，例如市盈率、市净率、总市值。
- 增加财务报表数据，用于基本面分析。
- 增加行业分类，用于横向对比。
- 增加自动化调度，例如每日收盘后更新。
- 增加前端多股票切换和对比图表。
