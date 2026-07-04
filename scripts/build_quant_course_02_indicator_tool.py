#!/usr/bin/env python3
"""Build the quant_course_02 interactive stock indicator HTML tool."""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


COURSE_DIR = Path("/Users/huangsilu/Documents/quant_course_02")
API_URL = "https://api.tushare.pro"
CODEX_CONFIG = Path.home() / ".codex" / "config.toml"
DEFAULT_ADJUST = "qfq"

STOCKS = [
    {
        "stock_name": "狮头股份",
        "ts_code": "600539.SH",
        "exchange": "上交所",
        "market": "A股主板",
        "role": "既有样例，基础材料代表",
    },
    {
        "stock_name": "中芯国际",
        "ts_code": "688981.SH",
        "exchange": "上交所",
        "market": "科创板",
        "role": "半导体制造代表",
    },
    {
        "stock_name": "比亚迪",
        "ts_code": "002594.SZ",
        "exchange": "深交所",
        "market": "A股主板",
        "role": "新能源汽车代表",
    },
    {
        "stock_name": "三峡能源",
        "ts_code": "600905.SH",
        "exchange": "上交所",
        "market": "A股主板",
        "role": "绿色电力代表",
    },
]

DAILY_FIELDS = [
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "pre_close",
    "change",
    "pct_chg",
    "vol",
    "amount",
]
ADJ_FIELDS = ["trade_date", "adj_factor"]
CSV_FIELDS = [
    "date",
    "open",
    "high",
    "low",
    "close",
    "pre_close",
    "change",
    "pct_chg",
    "volume_hands",
    "volume_shares",
    "amount_thousand_yuan",
    "raw_open",
    "raw_high",
    "raw_low",
    "raw_close",
    "raw_pre_close",
    "raw_change",
    "raw_pct_chg",
    "adj_factor",
]


def symbol_dir(ts_code: str) -> str:
    return ts_code.replace(".", "_")


def get_token() -> str:
    token = os.environ.get("TUSHARE_TOKEN")
    if token:
        return token.strip()

    if CODEX_CONFIG.exists():
        text = CODEX_CONFIG.read_text(encoding="utf-8")
        match = re.search(r"https://api\.tushare\.pro/mcp/\?token=([^\"'\s]+)", text)
        if match:
            parsed = urlparse("https://api.tushare.pro/mcp/?token=" + match.group(1))
            values = parse_qs(parsed.query).get("token")
            if values:
                return values[0]

    raise RuntimeError("No Tushare token found. Set TUSHARE_TOKEN or configure tushareMcp in Codex.")


def call_tushare(api_name: str, params: dict[str, str], fields: list[str]) -> list[dict[str, object]]:
    payload = {
        "api_name": api_name,
        "token": get_token(),
        "params": params,
        "fields": ",".join(fields),
    }
    req = Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Tushare request failed for {api_name}: {exc}") from exc

    if result.get("code") != 0:
        raise RuntimeError(f"Tushare returned error for {api_name}: {result.get('msg') or result}")

    data = result.get("data") or {}
    fields_out = data.get("fields") or []
    items = data.get("items") or []
    return [dict(zip(fields_out, row)) for row in items]


def qfq_price(value: object, adj_factor: float, latest_adj_factor: float) -> float:
    return round(float(value) * adj_factor / latest_adj_factor, 4)


def normalize_qfq(
    daily_rows: list[dict[str, object]],
    adj_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    adj_by_date = {str(row["trade_date"]): float(row["adj_factor"]) for row in adj_rows}
    daily_sorted = sorted(daily_rows, key=lambda row: str(row["trade_date"]))
    if not daily_sorted:
        return []

    missing = [str(row["trade_date"]) for row in daily_sorted if str(row["trade_date"]) not in adj_by_date]
    if missing:
        raise RuntimeError(f"Missing adj_factor for {len(missing)} dates, first: {missing[0]}")

    latest_date = str(daily_sorted[-1]["trade_date"])
    latest_adj_factor = adj_by_date[latest_date]
    if latest_adj_factor <= 0:
        raise RuntimeError(f"Invalid latest adj_factor for {latest_date}: {latest_adj_factor}")

    rows: list[dict[str, object]] = []
    previous_close: float | None = None
    for row in daily_sorted:
        trade_date = str(row["trade_date"])
        factor = adj_by_date[trade_date]
        if factor <= 0:
            raise RuntimeError(f"Invalid adj_factor on {trade_date}: {factor}")

        close = qfq_price(row["close"], factor, latest_adj_factor)
        pre_close = previous_close if previous_close is not None else qfq_price(row["pre_close"], factor, latest_adj_factor)
        change = round(close - pre_close, 4)
        pct_chg = round(change / pre_close * 100, 4) if pre_close else 0.0
        item = {
            "date": trade_date,
            "open": qfq_price(row["open"], factor, latest_adj_factor),
            "high": qfq_price(row["high"], factor, latest_adj_factor),
            "low": qfq_price(row["low"], factor, latest_adj_factor),
            "close": close,
            "pre_close": pre_close,
            "change": change,
            "pct_chg": pct_chg,
            "volume_hands": float(row["vol"]),
            "volume_shares": float(row["vol"]) * 100,
            "amount_thousand_yuan": float(row["amount"]),
            "raw_open": float(row["open"]),
            "raw_high": float(row["high"]),
            "raw_low": float(row["low"]),
            "raw_close": float(row["close"]),
            "raw_pre_close": float(row["pre_close"]),
            "raw_change": float(row["change"]),
            "raw_pct_chg": float(row["pct_chg"]),
            "adj_factor": factor,
        }
        rows.append(item)
        previous_close = close

    return rows


def validate_rows(rows: list[dict[str, object]], ts_code: str) -> None:
    if not rows:
        raise RuntimeError(f"No rows for {ts_code}")
    seen: set[str] = set()
    previous = ""
    for row in rows:
        row_date = str(row["date"])
        if row_date in seen:
            raise RuntimeError(f"{ts_code} duplicate date {row_date}")
        if previous and row_date <= previous:
            raise RuntimeError(f"{ts_code} dates not ascending near {row_date}")
        seen.add(row_date)
        previous = row_date
        if not float(row["low"]) <= float(row["open"]) <= float(row["high"]):
            raise RuntimeError(f"{ts_code} adjusted open invalid on {row_date}")
        if not float(row["low"]) <= float(row["close"]) <= float(row["high"]):
            raise RuntimeError(f"{ts_code} adjusted close invalid on {row_date}")
        if float(row["adj_factor"]) <= 0:
            raise RuntimeError(f"{ts_code} invalid adj_factor on {row_date}")


def normalize_raw(daily_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in sorted(daily_rows, key=lambda item: str(item["trade_date"])):
        rows.append(
            {
                "date": str(row["trade_date"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "pre_close": float(row["pre_close"]),
                "change": float(row["change"]),
                "pct_chg": float(row["pct_chg"]),
                "volume_hands": float(row["vol"]),
                "volume_shares": float(row["vol"]) * 100,
                "amount_thousand_yuan": float(row["amount"]),
                "raw_open": float(row["open"]),
                "raw_high": float(row["high"]),
                "raw_low": float(row["low"]),
                "raw_close": float(row["close"]),
                "raw_pre_close": float(row["pre_close"]),
                "raw_change": float(row["change"]),
                "raw_pct_chg": float(row["pct_chg"]),
                "adj_factor": 1.0,
            }
        )
    return rows


def load_existing_qfq(stock: dict[str, str]) -> list[dict[str, object]] | None:
    candidates = [
        COURSE_DIR / "data" / "stocks" / symbol_dir(stock["ts_code"]) / "daily_qfq.json",
    ]
    if stock["ts_code"] == "600539.SH":
        candidates.append(COURSE_DIR / "data" / "shitou_600539_qfq_daily.json")
    for path in candidates:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("metadata", {}).get("adjust") == "qfq":
                return payload.get("data") or []
    return None


def write_stock_outputs(
    stock: dict[str, str],
    rows: list[dict[str, object]],
    start_date: str,
    end_date: str,
    adjust: str,
    source: str,
) -> dict[str, object]:
    stock_dir_name = symbol_dir(stock["ts_code"])
    out_dir = COURSE_DIR / "data" / "stocks" / stock_dir_name
    out_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        **stock,
        "source": source,
        "adjust": adjust,
        "requested_start_date": start_date,
        "requested_end_date": end_date,
        "record_count": len(rows),
        "first_trade_date": rows[0]["date"],
        "last_trade_date": rows[-1]["date"],
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "units": {
            "price": "CNY, qfq adjusted unless prefixed with raw_",
            "volume_hands": "hands, 1 hand = 100 shares",
            "volume_shares": "shares",
            "amount_thousand_yuan": "thousand CNY",
        },
    }
    suffix = "qfq" if adjust == "qfq" else "raw"
    csv_path = out_dir / f"daily_{suffix}.csv"
    json_path = out_dir / f"daily_{suffix}.json"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps({"metadata": metadata, "data": rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        **stock,
        "symbol_dir": stock_dir_name,
        "adjust": adjust,
        "record_count": len(rows),
        "first_trade_date": rows[0]["date"],
        "last_trade_date": rows[-1]["date"],
        "daily_csv": f"data/stocks/{stock_dir_name}/daily_{suffix}.csv",
        "daily_json": f"data/stocks/{stock_dir_name}/daily_{suffix}.json",
    }


def build_app_data(manifest: dict[str, object], datasets: dict[str, dict[str, object]]) -> None:
    payload = {"manifest": manifest, "datasets": datasets}
    out_path = COURSE_DIR / "data" / "indicator_tool_data.js"
    out_path.write_text(
        "window.STOCK_INDICATOR_DATA = " + json.dumps(payload, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )


def build_design_doc() -> None:
    doc = """# 股票技术指标 HTML 工具设计文档

## 1. 产品定位

本工具是一个本地单页 HTML 技术指标工作台，用于在量化课程中演示不同股票价格数据如何生成 RSI、MACD、布林带和 ATR。

第一版采用纯前端实现，不依赖后端服务；数据通过 `data/indicator_tool_data.js` 以内嵌 JavaScript 对象方式加载，因此可直接打开 HTML 文件查看。

## 2. 当前股票数据

| 股票 | 代码 | 口径 | 说明 |
| --- | --- | --- | --- |
| 狮头股份 | 600539.SH | qfq 前复权 | 基础材料样例 |
| 中芯国际 | 688981.SH | 按数据文件 metadata 显示 | 半导体制造代表 |
| 比亚迪 | 002594.SZ | 按数据文件 metadata 显示 | 新能源汽车代表 |
| 三峡能源 | 600905.SH | 按数据文件 metadata 显示 | 绿色电力代表 |

## 3. 页面信息架构

- 顶部栏：产品标题、股票选择、数据口径、区间、最新收盘价。
- 左侧参数面板：指标开关、RSI、MACD、布林带、ATR 参数。
- 右侧主区域：价格主图、指标图、最新指标摘要、最近 20 日数据表。

## 4. 指标参数

| 指标 | 默认参数 | 可调参数 |
| --- | --- | --- |
| RSI | 14 | 周期 |
| MACD | 12, 26, 9 | 快线、慢线、信号线 |
| 布林带 | 20, 2.0 | 周期、标准差倍数 |
| ATR | 14 | 周期 |

## 5. 交互规则

1. 切换股票后，读取对应数据并重算全部指标。
2. 调整参数后，图表和表格即时重绘。
3. 勾选或取消指标开关后，相关图层或指标面板即时显示/隐藏。
4. 点击“重置参数”恢复默认参数。

## 6. 界面参考

```text
┌──────────────────────────────────────────────────────────────────────┐
│ 股票技术指标工作台  [股票选择 ▼]  数据口径  区间/最新价/行数          │
├───────────────────────┬──────────────────────────────────────────────┤
│ 参数面板              │ 价格主图：收盘价 + 可选布林带                 │
│ - 指标开关            │                                              │
│ - RSI 周期            ├──────────────────────────────────────────────┤
│ - MACD 快慢信号线     │ 指标图：RSI / MACD / ATR                     │
│ - 布林带周期和倍数    ├──────────────────────────────────────────────┤
│ - ATR 周期            │ 最近指标摘要 + 最近 20 日结果表              │
└───────────────────────┴──────────────────────────────────────────────┘
```

## 7. 验收标准

- 可选择四只股票。
- 明确显示每只股票的数据口径；优先使用 `qfq` 前复权，接口限流时标记为原始未复权。
- 四个指标都能计算并绘制。
- 每个指标参数都能调节并即时重绘。
- 最近 20 个交易日结果表可读。
- 页面不依赖外部 CDN，直接打开 HTML 即可使用。
"""
    docs_dir = COURSE_DIR / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "indicator_html_tool_design.md").write_text(doc, encoding="utf-8")


def build_html() -> None:
    dashboard_dir = COURSE_DIR / "dashboard"
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    html = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>股票技术指标工作台</title>
  <style>
    :root {
      --bg: #f5f7fb;
      --panel: #ffffff;
      --line: #d8dee9;
      --text: #172033;
      --muted: #667085;
      --blue: #2563eb;
      --red: #dc2626;
      --green: #16a34a;
      --purple: #7c3aed;
      --orange: #f97316;
      --teal: #0f766e;
      --shadow: 0 1px 2px rgba(16, 24, 40, .06), 0 1px 3px rgba(16, 24, 40, .08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      font-size: 14px;
    }
    header {
      display: grid;
      grid-template-columns: minmax(220px, 1fr) minmax(260px, 420px);
      gap: 16px;
      align-items: center;
      padding: 16px 20px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
      position: sticky;
      top: 0;
      z-index: 5;
    }
    h1 { margin: 0; font-size: 20px; font-weight: 750; letter-spacing: 0; }
    .subtitle { margin-top: 4px; color: var(--muted); font-size: 13px; }
    .stock-picker { display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: center; }
    select, input {
      width: 100%;
      height: 34px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--text);
      padding: 0 10px;
      font: inherit;
    }
    button {
      height: 34px;
      border: 1px solid #b8c2d6;
      border-radius: 6px;
      background: #fff;
      color: var(--text);
      padding: 0 12px;
      font: inherit;
      cursor: pointer;
    }
    button.primary { background: var(--blue); border-color: var(--blue); color: #fff; }
    main {
      display: grid;
      grid-template-columns: 320px minmax(0, 1fr);
      gap: 16px;
      padding: 16px;
      max-width: 1600px;
      margin: 0 auto;
    }
    aside, section, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }
    aside { padding: 14px; align-self: start; position: sticky; top: 82px; }
    .group { padding: 12px 0; border-bottom: 1px solid #edf1f7; }
    .group:last-child { border-bottom: 0; }
    .group h2 { margin: 0 0 10px; font-size: 14px; }
    .kv { display: grid; grid-template-columns: 88px 1fr; gap: 6px; margin: 6px 0; color: var(--muted); }
    .kv strong { color: var(--text); font-weight: 650; }
    .toggle { display: flex; align-items: center; gap: 8px; margin: 8px 0; }
    .toggle input { width: 16px; height: 16px; }
    .control { display: grid; grid-template-columns: 96px 1fr 58px; gap: 8px; align-items: center; margin: 9px 0; }
    .control input[type="range"] { padding: 0; }
    .workspace { display: grid; gap: 16px; min-width: 0; }
    .summary {
      display: grid;
      grid-template-columns: repeat(5, minmax(120px, 1fr));
      gap: 10px;
    }
    .metric {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      box-shadow: var(--shadow);
      min-width: 0;
    }
    .metric span { display: block; color: var(--muted); font-size: 12px; }
    .metric strong { display: block; margin-top: 4px; font-size: 18px; overflow-wrap: anywhere; }
    .chart-panel { padding: 12px; min-width: 0; }
    .chart-title { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; gap: 12px; }
    .chart-title h2 { margin: 0; font-size: 15px; }
    .chart-title span { color: var(--muted); font-size: 12px; }
    svg { width: 100%; height: auto; display: block; overflow: visible; }
    .axis { stroke: #98a2b3; stroke-width: 1; }
    .grid { stroke: #e4e9f2; stroke-width: 1; }
    .label { fill: #667085; font-size: 11px; }
    .legend { display: flex; flex-wrap: wrap; gap: 12px; margin: 6px 0 0; color: var(--muted); font-size: 12px; }
    .swatch { width: 10px; height: 10px; border-radius: 2px; display: inline-block; margin-right: 5px; }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 940px; }
    th, td { padding: 8px 9px; border-bottom: 1px solid #edf1f7; text-align: right; white-space: nowrap; }
    th:first-child, td:first-child { text-align: left; }
    th { color: var(--muted); font-weight: 650; background: #fafbfe; position: sticky; top: 0; }
    .empty { padding: 20px; color: var(--muted); }
    @media (max-width: 980px) {
      header, main { grid-template-columns: 1fr; }
      aside { position: static; }
      .summary { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>股票技术指标工作台</h1>
      <div class="subtitle">选择股票，调节 RSI、MACD、布林带、ATR 参数，即时重算和重绘。</div>
    </div>
    <div class="stock-picker">
      <select id="stockSelect" aria-label="选择股票"></select>
      <button id="resetBtn">重置参数</button>
    </div>
  </header>

  <main>
    <aside>
      <div class="group">
        <h2>股票数据</h2>
        <div class="kv"><span>股票</span><strong id="stockName">--</strong></div>
        <div class="kv"><span>代码</span><strong id="stockCode">--</strong></div>
        <div class="kv"><span>口径</span><strong id="adjust">--</strong></div>
        <div class="kv"><span>区间</span><strong id="dateRange">--</strong></div>
        <div class="kv"><span>交易日</span><strong id="rowCount">--</strong></div>
      </div>

      <div class="group">
        <h2>指标开关</h2>
        <label class="toggle"><input type="checkbox" id="showRsi" checked> RSI</label>
        <label class="toggle"><input type="checkbox" id="showMacd" checked> MACD</label>
        <label class="toggle"><input type="checkbox" id="showBb" checked> 布林带</label>
        <label class="toggle"><input type="checkbox" id="showAtr" checked> ATR</label>
      </div>

      <div class="group">
        <h2>RSI 参数</h2>
        <div class="control"><label>周期</label><input id="rsiPeriodRange" type="range" min="2" max="60" value="14"><input id="rsiPeriod" type="number" min="2" max="60" value="14"></div>
      </div>

      <div class="group">
        <h2>MACD 参数</h2>
        <div class="control"><label>快线</label><input id="macdFastRange" type="range" min="2" max="40" value="12"><input id="macdFast" type="number" min="2" max="40" value="12"></div>
        <div class="control"><label>慢线</label><input id="macdSlowRange" type="range" min="5" max="80" value="26"><input id="macdSlow" type="number" min="5" max="80" value="26"></div>
        <div class="control"><label>信号</label><input id="macdSignalRange" type="range" min="2" max="40" value="9"><input id="macdSignal" type="number" min="2" max="40" value="9"></div>
      </div>

      <div class="group">
        <h2>布林带参数</h2>
        <div class="control"><label>周期</label><input id="bbPeriodRange" type="range" min="5" max="80" value="20"><input id="bbPeriod" type="number" min="5" max="80" value="20"></div>
        <div class="control"><label>倍数</label><input id="bbMultRange" type="range" min="1" max="4" step="0.1" value="2"><input id="bbMult" type="number" min="1" max="4" step="0.1" value="2"></div>
      </div>

      <div class="group">
        <h2>ATR 参数</h2>
        <div class="control"><label>周期</label><input id="atrPeriodRange" type="range" min="2" max="60" value="14"><input id="atrPeriod" type="number" min="2" max="60" value="14"></div>
      </div>
    </aside>

    <div class="workspace">
      <div class="summary" id="summary"></div>

      <section class="chart-panel">
        <div class="chart-title"><h2>价格主图</h2><span id="priceChartHint">收盘价；勾选布林带后叠加上下轨</span></div>
        <div id="priceChart"></div>
        <div class="legend" id="priceLegend"></div>
      </section>

      <section class="chart-panel">
        <div class="chart-title"><h2>指标图</h2><span>按左侧开关显示 RSI / MACD / ATR</span></div>
        <div id="indicatorCharts"></div>
      </section>

      <section class="chart-panel">
        <div class="chart-title"><h2>最近 20 个交易日</h2><span>所有数值基于当前参数重新计算</span></div>
        <div class="table-wrap" id="tableWrap"></div>
      </section>
    </div>
  </main>

  <script src="../data/indicator_tool_data.js"></script>
  <script>
    const appData = window.STOCK_INDICATOR_DATA;
    const defaults = { rsiPeriod: 14, macdFast: 12, macdSlow: 26, macdSignal: 9, bbPeriod: 20, bbMult: 2, atrPeriod: 14 };
    const controls = ["rsiPeriod", "macdFast", "macdSlow", "macdSignal", "bbPeriod", "bbMult", "atrPeriod"];
    const toggles = ["showRsi", "showMacd", "showBb", "showAtr"];

    function fmtDate(s) { return `${s.slice(0,4)}-${s.slice(4,6)}-${s.slice(6,8)}`; }
    function fmt(v, digits = 2) { return Number.isFinite(v) ? v.toFixed(digits) : "--"; }
    function syncPair(id) {
      const n = document.getElementById(id);
      const r = document.getElementById(id + "Range");
      const sync = source => {
        const value = source.value;
        n.value = value;
        r.value = value;
        render();
      };
      n.addEventListener("input", () => sync(n));
      r.addEventListener("input", () => sync(r));
    }
    function params() {
      return {
        rsiPeriod: Math.max(2, Number(document.getElementById("rsiPeriod").value)),
        macdFast: Math.max(2, Number(document.getElementById("macdFast").value)),
        macdSlow: Math.max(5, Number(document.getElementById("macdSlow").value)),
        macdSignal: Math.max(2, Number(document.getElementById("macdSignal").value)),
        bbPeriod: Math.max(5, Number(document.getElementById("bbPeriod").value)),
        bbMult: Math.max(1, Number(document.getElementById("bbMult").value)),
        atrPeriod: Math.max(2, Number(document.getElementById("atrPeriod").value)),
      };
    }
    function selectedDataset() {
      return appData.datasets[document.getElementById("stockSelect").value];
    }
    function ema(values, period, minPeriods = 1) {
      const alpha = 2 / (period + 1);
      const out = [];
      let prev = null;
      let valid = 0;
      for (const value of values) {
        if (!Number.isFinite(value)) { out.push(null); continue; }
        valid += 1;
        prev = prev === null ? value : alpha * value + (1 - alpha) * prev;
        out.push(valid >= minPeriods ? prev : null);
      }
      return out;
    }
    function wilder(values, period) {
      const alpha = 1 / period;
      const out = [];
      let prev = null;
      let valid = 0;
      for (const value of values) {
        if (!Number.isFinite(value)) { out.push(null); continue; }
        valid += 1;
        prev = prev === null ? value : alpha * value + (1 - alpha) * prev;
        out.push(valid >= period ? prev : null);
      }
      return out;
    }
    function rolling(values, period, fn) {
      return values.map((_, i) => {
        if (i + 1 < period) return null;
        const window = values.slice(i + 1 - period, i + 1);
        return fn(window);
      });
    }
    function mean(arr) { return arr.reduce((a, b) => a + b, 0) / arr.length; }
    function std(arr) {
      const m = mean(arr);
      return Math.sqrt(arr.reduce((s, v) => s + (v - m) ** 2, 0) / (arr.length - 1));
    }
    function compute(rows, p) {
      const close = rows.map(d => d.close);
      const high = rows.map(d => d.high);
      const low = rows.map(d => d.low);
      const delta = close.map((v, i) => i === 0 ? null : v - close[i - 1]);
      const gain = delta.map(v => v === null ? null : Math.max(v, 0));
      const loss = delta.map(v => v === null ? null : Math.max(-v, 0));
      const avgGain = wilder(gain, p.rsiPeriod);
      const avgLoss = wilder(loss, p.rsiPeriod);
      const rsi = avgGain.map((g, i) => {
        const l = avgLoss[i];
        if (g === null || l === null) return null;
        if (l === 0 && g > 0) return 100;
        if (l === 0) return null;
        return 100 - 100 / (1 + g / l);
      });

      const fast = ema(close, p.macdFast);
      const slow = ema(close, p.macdSlow);
      const dif = fast.map((v, i) => v === null || slow[i] === null ? null : v - slow[i]);
      const dea = ema(dif, p.macdSignal);
      const hist = dif.map((v, i) => v === null || dea[i] === null ? null : v - dea[i]);

      const mid = rolling(close, p.bbPeriod, mean);
      const stdev = rolling(close, p.bbPeriod, std);
      const upper = mid.map((v, i) => v === null ? null : v + p.bbMult * stdev[i]);
      const lower = mid.map((v, i) => v === null ? null : v - p.bbMult * stdev[i]);
      const width = upper.map((v, i) => v === null ? null : (v - lower[i]) / mid[i]);
      const percentB = upper.map((v, i) => v === null ? null : (close[i] - lower[i]) / (v - lower[i]));

      const tr = rows.map((d, i) => {
        if (i === 0) return d.high - d.low;
        return Math.max(d.high - d.low, Math.abs(d.high - rows[i - 1].close), Math.abs(d.low - rows[i - 1].close));
      });
      const atr = wilder(tr, p.atrPeriod);
      const atrPct = atr.map((v, i) => v === null ? null : v / close[i] * 100);

      return rows.map((d, i) => ({ ...d, rsi: rsi[i], macdDif: dif[i], macdDea: dea[i], macdHist: hist[i], bbMid: mid[i], bbUpper: upper[i], bbLower: lower[i], bbWidth: width[i], bbPercentB: percentB[i], trueRange: tr[i], atr: atr[i], atrPct: atrPct[i] }));
    }
    function chartScales(series, width, height, pad) {
      const values = series.flatMap(s => s.values).filter(Number.isFinite);
      const min = Math.min(...values);
      const max = Math.max(...values);
      const span = max - min || 1;
      return {
        x: i => pad.left + (i / Math.max(series[0].values.length - 1, 1)) * (width - pad.left - pad.right),
        y: v => height - pad.bottom - ((v - (min - span * 0.08)) / (span * 1.16)) * (height - pad.top - pad.bottom),
        min: min - span * 0.08,
        max: max + span * 0.08,
      };
    }
    function pathFor(values, x, y) {
      let d = "";
      let open = false;
      values.forEach((v, i) => {
        if (!Number.isFinite(v)) { open = false; return; }
        d += `${open ? "L" : "M"}${x(i).toFixed(2)},${y(v).toFixed(2)}`;
        open = true;
      });
      return d;
    }
    function drawLineChart(el, rows, series, options = {}) {
      const width = 980;
      const height = options.height || 320;
      const pad = { left: 58, right: 24, top: 18, bottom: 36 };
      if (!rows.length || !series.some(s => s.values.some(Number.isFinite))) {
        el.innerHTML = '<div class="empty">没有可绘制的数据</div>';
        return;
      }
      const scales = chartScales(series, width, height, pad);
      const ticks = 4;
      const grid = Array.from({ length: ticks + 1 }, (_, i) => {
        const y = pad.top + i * (height - pad.top - pad.bottom) / ticks;
        const value = scales.max - i * (scales.max - scales.min) / ticks;
        return `<line class="grid" x1="${pad.left}" x2="${width - pad.right}" y1="${y}" y2="${y}"></line><text class="label" x="8" y="${y + 4}">${fmt(value, options.digits ?? 2)}</text>`;
      }).join("");
      const dateTicks = [0, Math.floor(rows.length / 3), Math.floor(rows.length * 2 / 3), rows.length - 1]
        .map(i => `<text class="label" x="${scales.x(i)}" y="${height - 10}" text-anchor="middle">${fmtDate(rows[i].date).slice(2)}</text>`).join("");
      const paths = series.map(s => `<path d="${pathFor(s.values, scales.x, scales.y)}" fill="none" stroke="${s.color}" stroke-width="${s.width || 2}" stroke-dasharray="${s.dash || ""}"></path>`).join("");
      el.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${options.title || "chart"}">${grid}<line class="axis" x1="${pad.left}" x2="${width - pad.right}" y1="${height - pad.bottom}" y2="${height - pad.bottom}"></line><line class="axis" x1="${pad.left}" x2="${pad.left}" y1="${pad.top}" y2="${height - pad.bottom}"></line>${paths}${dateTicks}</svg>`;
    }
    function drawMacdChart(el, rows) {
      const width = 980, height = 260, pad = { left: 58, right: 24, top: 18, bottom: 36 };
      const series = [{ values: rows.map(d => d.macdDif), color: "#f97316" }, { values: rows.map(d => d.macdDea), color: "#0f766e" }, { values: rows.map(d => d.macdHist), color: "#64748b" }];
      const scales = chartScales(series, width, height, pad);
      const barW = Math.max(1, (width - pad.left - pad.right) / rows.length * 0.75);
      const zeroY = scales.y(0);
      const bars = rows.map((d, i) => {
        if (!Number.isFinite(d.macdHist)) return "";
        const x = scales.x(i) - barW / 2;
        const y = scales.y(Math.max(d.macdHist, 0));
        const h = Math.abs(scales.y(d.macdHist) - zeroY);
        return `<rect x="${x}" y="${y}" width="${barW}" height="${h}" fill="${d.macdHist >= 0 ? "#dc2626" : "#16a34a"}" opacity=".65"></rect>`;
      }).join("");
      el.innerHTML = `<div class="chart-title"><h2>MACD</h2><span>DIF / DEA / 柱</span></div><svg viewBox="0 0 ${width} ${height}">${bars}<line class="grid" x1="${pad.left}" x2="${width - pad.right}" y1="${zeroY}" y2="${zeroY}"></line><path d="${pathFor(rows.map(d => d.macdDif), scales.x, scales.y)}" fill="none" stroke="#f97316" stroke-width="2"></path><path d="${pathFor(rows.map(d => d.macdDea), scales.x, scales.y)}" fill="none" stroke="#0f766e" stroke-width="2"></path></svg><div class="legend"><span><i class="swatch" style="background:#f97316"></i>DIF</span><span><i class="swatch" style="background:#0f766e"></i>DEA</span><span><i class="swatch" style="background:#dc2626"></i>正柱</span><span><i class="swatch" style="background:#16a34a"></i>负柱</span></div>`;
    }
    function renderSummary(rows, ds) {
      const latest = rows[rows.length - 1];
      const prev = rows[rows.length - 2] || latest;
      const cards = [
        ["最新收盘", fmt(latest.close, 2)],
        ["涨跌幅", `${fmt(latest.pct_chg, 2)}%`],
        ["RSI", fmt(latest.rsi, 2)],
        ["MACD柱", fmt(latest.macdHist, 3)],
        ["ATR%", `${fmt(latest.atrPct, 2)}%`],
      ];
      document.getElementById("summary").innerHTML = cards.map(([k, v]) => `<div class="metric"><span>${k}</span><strong>${v}</strong></div>`).join("");
      document.getElementById("stockName").textContent = ds.metadata.stock_name;
      document.getElementById("stockCode").textContent = ds.metadata.ts_code;
      const adjustLabel = ds.metadata.adjust === "qfq" ? "qfq 前复权" : "none 原始未复权";
      document.getElementById("adjust").textContent = adjustLabel;
      document.getElementById("priceChartHint").textContent = `${adjustLabel}收盘价；勾选布林带后叠加上下轨`;
      document.getElementById("dateRange").textContent = `${fmtDate(ds.metadata.first_trade_date)} 至 ${fmtDate(ds.metadata.last_trade_date)}`;
      document.getElementById("rowCount").textContent = ds.metadata.record_count;
    }
    function renderTable(rows) {
      const latest = rows.slice(-20).reverse();
      const head = ["date", "close", "rsi", "macdDif", "macdDea", "macdHist", "bbMid", "bbUpper", "bbLower", "atr", "atrPct"];
      const labels = ["日期", "收盘", "RSI", "DIF", "DEA", "MACD柱", "布林中轨", "布林上轨", "布林下轨", "ATR", "ATR%"];
      document.getElementById("tableWrap").innerHTML = `<table><thead><tr>${labels.map(v => `<th>${v}</th>`).join("")}</tr></thead><tbody>${latest.map(row => `<tr>${head.map(key => `<td>${key === "date" ? fmtDate(row[key]) : fmt(row[key], key === "atrPct" ? 2 : 3)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
    }
    function render() {
      const ds = selectedDataset();
      const p = params();
      if (p.macdFast >= p.macdSlow) {
        p.macdSlow = p.macdFast + 1;
        document.getElementById("macdSlow").value = p.macdSlow;
        document.getElementById("macdSlowRange").value = p.macdSlow;
      }
      const rows = compute(ds.data, p);
      renderSummary(rows, ds);
      const priceSeries = [{ name: "收盘价", values: rows.map(d => d.close), color: "#2563eb", width: 2.4 }];
      if (document.getElementById("showBb").checked) {
        priceSeries.push({ name: "布林上轨", values: rows.map(d => d.bbUpper), color: "#dc2626", dash: "6 4" });
        priceSeries.push({ name: "布林中轨", values: rows.map(d => d.bbMid), color: "#334155" });
        priceSeries.push({ name: "布林下轨", values: rows.map(d => d.bbLower), color: "#16a34a", dash: "6 4" });
      }
      drawLineChart(document.getElementById("priceChart"), rows, priceSeries, { title: "价格主图" });
      document.getElementById("priceLegend").innerHTML = priceSeries.map(s => `<span><i class="swatch" style="background:${s.color}"></i>${s.name}</span>`).join("");

      const container = document.getElementById("indicatorCharts");
      container.innerHTML = "";
      if (document.getElementById("showRsi").checked) {
        const box = document.createElement("div");
        box.className = "panel chart-panel";
        box.innerHTML = '<div class="chart-title"><h2>RSI</h2><span>70 / 30 为常用参考线</span></div><div class="chart"></div>';
        container.appendChild(box);
        drawLineChart(box.querySelector(".chart"), rows, [{ values: rows.map(d => d.rsi), color: "#7c3aed", width: 2 }], { height: 220, digits: 0, title: "RSI" });
      }
      if (document.getElementById("showMacd").checked) {
        const box = document.createElement("div");
        box.className = "panel chart-panel";
        container.appendChild(box);
        drawMacdChart(box, rows);
      }
      if (document.getElementById("showAtr").checked) {
        const box = document.createElement("div");
        box.className = "panel chart-panel";
        box.innerHTML = '<div class="chart-title"><h2>ATR</h2><span>ATR% 更适合跨价格区间比较</span></div><div class="chart"></div><div class="legend"><span><i class="swatch" style="background:#ea580c"></i>ATR</span><span><i class="swatch" style="background:#0f766e"></i>ATR%</span></div>';
        container.appendChild(box);
        drawLineChart(box.querySelector(".chart"), rows, [{ values: rows.map(d => d.atr), color: "#ea580c" }, { values: rows.map(d => d.atrPct), color: "#0f766e" }], { height: 240, title: "ATR" });
      }
      renderTable(rows);
    }
    function init() {
      const select = document.getElementById("stockSelect");
      select.innerHTML = appData.manifest.stocks.map(s => `<option value="${s.ts_code}">${s.stock_name} ${s.ts_code}</option>`).join("");
      select.addEventListener("change", render);
      controls.forEach(syncPair);
      toggles.forEach(id => document.getElementById(id).addEventListener("change", render));
      document.getElementById("resetBtn").addEventListener("click", () => {
        Object.entries(defaults).forEach(([key, value]) => {
          document.getElementById(key).value = value;
          document.getElementById(key + "Range").value = value;
        });
        toggles.forEach(id => document.getElementById(id).checked = true);
        render();
      });
      render();
    }
    init();
  </script>
</body>
</html>
"""
    (dashboard_dir / "indicator_tool.html").write_text(html, encoding="utf-8")
    (COURSE_DIR / "index.html").write_text(
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=dashboard/indicator_tool.html"><title>股票技术指标工作台</title></head><body><a href="dashboard/indicator_tool.html">打开股票技术指标工作台</a></body></html>\n',
        encoding="utf-8",
    )


def main() -> int:
    end = date.today()
    start = end - timedelta(days=365)
    start_date = start.strftime("%Y%m%d")
    end_date = end.strftime("%Y%m%d")
    manifest_stocks: list[dict[str, object]] = []
    datasets: dict[str, dict[str, object]] = {}
    adj_factor_available = True

    for stock in STOCKS:
        params = {"ts_code": stock["ts_code"], "start_date": start_date, "end_date": end_date}
        print(f"Fetching {stock['stock_name']} {stock['ts_code']}...")
        existing_qfq = load_existing_qfq(stock)
        daily_rows = call_tushare("daily", params, DAILY_FIELDS)

        adjust = "none"
        source = "Tushare daily"
        if existing_qfq:
            rows = existing_qfq
            adjust = "qfq"
            source = "Tushare daily + adj_factor (cached)"
        elif adj_factor_available:
            try:
                adj_rows = call_tushare("adj_factor", params, ADJ_FIELDS)
                rows = normalize_qfq(daily_rows, adj_rows)
                adjust = "qfq"
                source = "Tushare daily + adj_factor"
            except RuntimeError as exc:
                if "频率超限" not in str(exc) and "rate" not in str(exc).lower():
                    raise
                print(f"  adj_factor limited; using raw daily data for {stock['ts_code']}.")
                adj_factor_available = False
                rows = normalize_raw(daily_rows)
        else:
            rows = normalize_raw(daily_rows)

        validate_rows(rows, stock["ts_code"])
        stock_manifest = write_stock_outputs(stock, rows, start_date, end_date, adjust, source)
        manifest_stocks.append(stock_manifest)
        datasets[stock["ts_code"]] = {
            "metadata": {
                **stock,
                "adjust": adjust,
                "record_count": len(rows),
                "first_trade_date": rows[0]["date"],
                "last_trade_date": rows[-1]["date"],
                "source": source,
            },
            "data": rows,
        }

    manifest = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "Tushare daily; qfq where adj_factor is available",
        "adjust": "per_stock",
        "stocks": manifest_stocks,
    }
    (COURSE_DIR / "data").mkdir(parents=True, exist_ok=True)
    (COURSE_DIR / "data" / "stock_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    build_app_data(manifest, datasets)
    build_design_doc()
    build_html()
    print(f"Built indicator tool at {COURSE_DIR / 'dashboard' / 'indicator_tool.html'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
