#!/usr/bin/env python3
"""
Generate raw OHLCV data for all stocks as a compact JS file.
The frontend JavaScript will compute MA, signals, and backtest dynamically.
"""

import csv
import json
from pathlib import Path

STOCKS = [
    {
        "name": "狮头股份",
        "ts_code": "600539.SH",
        "exchange": "上交所",
        "market": "A股主板",
        "csv_path": "../quant_course_02/data/stocks/600539_SH/daily_qfq.csv",
        "adjust": "qfq",
    },
    {
        "name": "中芯国际",
        "ts_code": "688981.SH",
        "exchange": "上交所",
        "market": "科创板",
        "csv_path": "../quant_course_02/data/stocks/688981_SH/daily_raw.csv",
        "adjust": "none",
    },
    {
        "name": "比亚迪",
        "ts_code": "002594.SZ",
        "exchange": "深交所",
        "market": "A股主板",
        "csv_path": "../quant_course_02/data/stocks/002594_SZ/daily_raw.csv",
        "adjust": "none",
    },
    {
        "name": "三峡能源",
        "ts_code": "600905.SH",
        "exchange": "上交所",
        "market": "A股主板",
        "csv_path": "../quant_course_02/data/stocks/600905_SH/daily_raw.csv",
        "adjust": "none",
    },
]

BASE_DIR = Path(__file__).resolve().parent
STOCKS_DIR = BASE_DIR.parent.parent / "quant_course_02" / "data" / "stocks"
OUTPUT_DIR = BASE_DIR.parent / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_stock_data(stock):
    """Load CSV and return compact list of [date_str, open, high, low, close, volume]."""
    csv_path = STOCKS_DIR / stock["symbol_dir"] / (
        "daily_qfq.csv" if stock["adjust"] == "qfq" else "daily_raw.csv"
    )
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            date_str = r["date"][:4] + "-" + r["date"][4:6] + "-" + r["date"][6:8]
            rows.append([
                date_str,
                round(float(r["open"]), 3),
                round(float(r["high"]), 3),
                round(float(r["low"]), 3),
                round(float(r["close"]), 3),
                round(float(r["volume_hands"]), 1),
            ])
    return rows


stocks_data = []
for s in STOCKS:
    symbol_dir = s["csv_path"].split("/")[-2]
    csv_path = STOCKS_DIR / symbol_dir / ("daily_qfq.csv" if s["adjust"] == "qfq" else "daily_raw.csv")
    rows = load_stock_data({"symbol_dir": symbol_dir, "adjust": s["adjust"]})
    stocks_data.append({
        "name": s["name"],
        "ts_code": s["ts_code"],
        "exchange": s["exchange"],
        "market": s["market"],
        "adjust": s["adjust"],
        "first_date": rows[0][0] if rows else "",
        "last_date": rows[-1][0] if rows else "",
        "record_count": len(rows),
        "data": rows,
    })
    print(f"  {s['name']} ({s['ts_code']}): {len(rows)} records, {rows[0][0]} ~ {rows[-1][0]}")

js_content = "var STOCK_DATA = " + json.dumps(stocks_data, ensure_ascii=False, separators=(",", ":")) + ";"
output_path = OUTPUT_DIR / "stock_raw_data.js"
output_path.write_text(js_content, encoding="utf-8")
file_size = output_path.stat().st_size
print(f"\nGenerated: {output_path} ({file_size / 1024:.1f} KB)")
