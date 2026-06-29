#!/usr/bin/env python3
"""Fetch one year of Shitou stock daily data from Tushare."""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
CODEX_CONFIG = Path.home() / ".codex" / "config.toml"
API_URL = "https://api.tushare.pro"
TS_CODE = "600539.SH"
STOCK_NAME = "狮头股份"
FIELDS = [
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
        raise RuntimeError(f"Tushare request failed: {exc}") from exc

    if result.get("code") != 0:
        raise RuntimeError(f"Tushare returned error: {result.get('msg') or result}")

    data = result.get("data") or {}
    fields_out = data.get("fields") or []
    items = data.get("items") or []
    return [dict(zip(fields_out, row)) for row in items]


def normalize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out = []
    for row in rows:
        item = {
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
        }
        out.append(item)
    return sorted(out, key=lambda x: str(x["date"]))


def write_outputs(rows: list[dict[str, object]], start_date: str, end_date: str) -> None:
    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)

    metadata = {
        "stock_name": STOCK_NAME,
        "ts_code": TS_CODE,
        "source": "Tushare daily",
        "requested_start_date": start_date,
        "requested_end_date": end_date,
        "record_count": len(rows),
        "first_trade_date": rows[0]["date"] if rows else None,
        "last_trade_date": rows[-1]["date"] if rows else None,
        "units": {
            "price": "CNY",
            "volume_hands": "hands, 1 hand = 100 shares",
            "volume_shares": "shares",
            "amount_thousand_yuan": "thousand CNY",
        },
    }

    json_path = data_dir / "shitou_600539_daily.json"
    json_path.write_text(
        json.dumps({"metadata": metadata, "data": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    js_path = data_dir / "shitou_600539_daily.js"
    js_path.write_text(
        "window.SHITOU_DAILY = "
        + json.dumps({"metadata": metadata, "data": rows}, ensure_ascii=False)
        + ";\n",
        encoding="utf-8",
    )

    csv_path = data_dir / "shitou_600539_daily.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["date"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows")
    print(f"JSON: {json_path}")
    print(f"CSV:  {csv_path}")
    print(f"JS:   {js_path}")


def main() -> int:
    end = date.today()
    start = end - timedelta(days=365)
    start_date = start.strftime("%Y%m%d")
    end_date = end.strftime("%Y%m%d")

    rows = call_tushare(
        "daily",
        {"ts_code": TS_CODE, "start_date": start_date, "end_date": end_date},
        FIELDS,
    )
    normalized = normalize(rows)
    if not normalized:
        raise RuntimeError(f"No rows returned for {TS_CODE} between {start_date} and {end_date}.")

    write_outputs(normalized, start_date, end_date)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
