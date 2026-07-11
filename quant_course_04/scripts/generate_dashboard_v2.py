#!/usr/bin/env python3
"""
生成增强版海龟交易策略回测看板 HTML
功能：左侧侧边栏（股票切换/文件上传/参数调节）+ 图表简介 + 客户端策略引擎
"""

import json
import csv
from pathlib import Path

# ============================================================
# 1. 读取所有可用股票数据
# ============================================================
DATA_DIR = Path(__file__).parent.parent / "data"
STOCKS_DIR = Path(__file__).parent.parent.parent / "quant_course_02" / "data" / "stocks"

# 内置股票列表
stock_files = [
    {"code": "600539.SH", "name": "狮头股份", "path": DATA_DIR / "shitou_600539_qfq_daily.csv", "adjust": "前复权"},
    {"code": "688981.SH", "name": "中芯国际", "path": STOCKS_DIR / "688981_SH" / "daily_raw.csv", "adjust": "不复权"},
    {"code": "002594.SZ", "name": "比亚迪", "path": STOCKS_DIR / "002594_SZ" / "daily_raw.csv", "adjust": "不复权"},
    {"code": "600905.SH", "name": "三峡能源", "path": STOCKS_DIR / "600905_SH" / "daily_raw.csv", "adjust": "不复权"},
]

stocks_data = {}
for s in stock_files:
    if not s["path"].exists():
        print(f"  跳过（文件不存在）: {s['code']} {s['name']}")
        continue
    rows = []
    with open(s["path"], "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "date": row["date"],
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "vol": float(row.get("volume_hands", 0)),
            })
    stocks_data[s["code"]] = {
        "name": s["name"],
        "code": s["code"],
        "adjust": s["adjust"],
        "data": rows,
    }
    print(f"  加载: {s['code']} {s['name']} ({len(rows)} 条)")

print(f"\n共加载 {len(stocks_data)} 只股票数据")

# ============================================================
# 2. 生成 HTML
# ============================================================
OUTPUT_DIR = Path(__file__).parent.parent / "dashboard"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 将 stocks_data 序列化为紧凑 JSON
stocks_json = json.dumps(stocks_data, ensure_ascii=False)

html = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>海龟交易策略回测看板 - 多标的支持</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: "PingFang SC", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
    background: #f0f2f5; color: #1a1a2e; line-height: 1.6;
  }

  /* ===== Sidebar ===== */
  .sidebar {
    position: fixed; left: 0; top: 0; bottom: 0; width: 280px;
    background: #0f172a; color: #cbd5e1; overflow-y: auto; z-index: 100;
    display: flex; flex-direction: column;
  }
  .sidebar-header {
    padding: 20px 20px 14px; border-bottom: 1px solid rgba(255,255,255,0.08);
  }
  .sidebar-header h2 {
    font-size: 16px; color: #fff; font-weight: 700; margin-bottom: 4px;
  }
  .sidebar-header p {
    font-size: 11px; color: #64748b;
  }
  .sidebar-section {
    padding: 16px 20px; border-bottom: 1px solid rgba(255,255,255,0.06);
  }
  .sidebar-section-title {
    font-size: 11px; font-weight: 600; color: #475569; text-transform: uppercase;
    letter-spacing: 1px; margin-bottom: 10px;
  }
  .stock-list { display: flex; flex-direction: column; gap: 4px; }
  .stock-item {
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 12px; border-radius: 8px; cursor: pointer;
    transition: background 0.15s; font-size: 13px;
  }
  .stock-item:hover { background: rgba(255,255,255,0.06); }
  .stock-item.active {
    background: rgba(37,99,235,0.2); color: #60a5fa; font-weight: 600;
  }
  .stock-item .stock-code { font-size: 11px; color: #475569; }
  .stock-item.active .stock-code { color: #3b82f6; }
  .stock-item .stock-name { flex: 1; }
  .upload-btn {
    display: flex; align-items: center; justify-content: center; gap: 6px;
    width: 100%; padding: 10px; border: 1px dashed rgba(255,255,255,0.2);
    border-radius: 8px; background: transparent; color: #64748b;
    cursor: pointer; font-size: 12px; transition: all 0.15s;
  }
  .upload-btn:hover { border-color: #3b82f6; color: #60a5fa; background: rgba(59,130,246,0.05); }
  .upload-btn input { display: none; }
  .param-group { margin-bottom: 12px; }
  .param-label {
    display: flex; justify-content: space-between; align-items: center;
    font-size: 12px; color: #94a3b8; margin-bottom: 4px;
  }
  .param-label .param-value {
    color: #60a5fa; font-weight: 600; font-size: 12px;
  }
  .param-slider {
    width: 100%; height: 4px; -webkit-appearance: none; appearance: none;
    background: rgba(255,255,255,0.1); border-radius: 2px; outline: none;
  }
  .param-slider::-webkit-slider-thumb {
    -webkit-appearance: none; appearance: none;
    width: 14px; height: 14px; border-radius: 50%;
    background: #3b82f6; cursor: pointer; transition: background 0.15s;
  }
  .param-slider::-webkit-slider-thumb:hover { background: #60a5fa; }
  .param-slider::-moz-range-thumb {
    width: 14px; height: 14px; border-radius: 50%; border: none;
    background: #3b82f6; cursor: pointer;
  }
  .param-select {
    width: 100%; padding: 6px 8px; border-radius: 6px;
    background: rgba(255,255,255,0.06); color: #cbd5e1; border: 1px solid rgba(255,255,255,0.1);
    font-size: 12px; outline: none;
  }
  .param-select option { background: #1e293b; color: #cbd5e1; }
  .run-btn {
    width: 100%; padding: 10px; border: none; border-radius: 8px;
    background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
    color: #fff; font-size: 13px; font-weight: 600; cursor: pointer;
    transition: opacity 0.15s; margin-top: 4px;
  }
  .run-btn:hover { opacity: 0.9; }
  .run-btn:active { transform: scale(0.98); }
  .reset-btn {
    width: 100%; padding: 8px; border: 1px solid rgba(255,255,255,0.15);
    border-radius: 8px; background: transparent; color: #64748b;
    font-size: 12px; cursor: pointer; transition: all 0.15s; margin-top: 6px;
  }
  .reset-btn:hover { border-color: #475569; color: #94a3b8; }
  .preset-select {
    width: 100%; padding: 6px 8px; border-radius: 6px;
    background: rgba(255,255,255,0.06); color: #cbd5e1; border: 1px solid rgba(255,255,255,0.1);
    font-size: 12px; outline: none; margin-bottom: 10px;
  }
  .preset-select option { background: #1e293b; color: #cbd5e1; }

  /* ===== Main Content ===== */
  .main-content {
    margin-left: 280px; min-height: 100vh;
  }

  /* ===== Header ===== */
  .header {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #2563eb 100%);
    color: #fff; padding: 28px 32px; position: relative; overflow: hidden;
  }
  .header::after {
    content: ""; position: absolute; right: -50px; top: -50px;
    width: 300px; height: 300px; border-radius: 50%;
    background: rgba(255,255,255,0.03);
  }
  .header h1 { font-size: 22px; font-weight: 700; margin-bottom: 6px; }
  .header .subtitle { font-size: 14px; opacity: 0.85; }
  .header .meta-row {
    display: flex; gap: 24px; margin-top: 14px; flex-wrap: wrap;
  }
  .header .meta-item {
    background: rgba(255,255,255,0.1); padding: 4px 14px;
    border-radius: 20px; font-size: 12px;
  }
  .header .meta-item strong { font-weight: 600; }

  /* ===== Layout ===== */
  .container { max-width: 1400px; margin: 0 auto; padding: 20px; }

  /* ===== Metric Cards ===== */
  .metrics-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 14px; margin-bottom: 20px;
  }
  .metric-card {
    background: #fff; border-radius: 12px; padding: 18px 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-left: 4px solid #2563eb;
    transition: transform 0.2s, box-shadow 0.2s;
  }
  .metric-card:hover {
    transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.1);
  }
  .metric-card .label { font-size: 12px; color: #64748b; margin-bottom: 6px; }
  .metric-card .value { font-size: 24px; font-weight: 700; color: #1e293b; }
  .metric-card .sub { font-size: 11px; color: #94a3b8; margin-top: 4px; }
  .metric-card.positive { border-left-color: #16a34a; }
  .metric-card.positive .value { color: #16a34a; }
  .metric-card.negative { border-left-color: #dc2626; }
  .metric-card.negative .value { color: #dc2626; }
  .metric-card.warning { border-left-color: #f59e0b; }
  .metric-card.warning .value { color: #d97706; }

  /* ===== Chart Cards ===== */
  .chart-card {
    background: #fff; border-radius: 12px; padding: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 20px;
  }
  .chart-card .chart-title {
    font-size: 15px; font-weight: 600; color: #1e3a5f;
    margin-bottom: 4px; display: flex; align-items: center; gap: 8px;
  }
  .chart-card .chart-title .icon {
    width: 4px; height: 18px; background: #2563eb; border-radius: 2px;
  }
  .chart-card .chart-desc {
    font-size: 12px; color: #94a3b8; margin-bottom: 6px;
  }
  .chart-card .chart-intro {
    font-size: 12px; color: #64748b; line-height: 1.7; margin-bottom: 12px;
    padding: 10px 14px; background: #f8fafc; border-radius: 8px;
    border-left: 3px solid #e2e8f0;
  }
  .chart-card .chart-intro strong { color: #334155; font-weight: 600; }
  .chart-container { width: 100%; }

  /* ===== Two Column ===== */
  .two-col {
    display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;
  }
  @media (max-width: 1100px) { .two-col { grid-template-columns: 1fr; } }

  /* ===== Table ===== */
  .table-card {
    background: #fff; border-radius: 12px; padding: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 20px;
  }
  .table-card .table-title {
    font-size: 15px; font-weight: 600; color: #1e3a5f; margin-bottom: 14px;
    display: flex; align-items: center; gap: 8px;
  }
  .table-card .table-title .icon {
    width: 4px; height: 18px; background: #2563eb; border-radius: 2px;
  }
  table {
    width: 100%; border-collapse: collapse; font-size: 13px;
  }
  th {
    background: #f8fafc; padding: 10px 14px; text-align: left;
    font-weight: 600; color: #475569; border-bottom: 2px solid #e2e8f0;
    white-space: nowrap;
  }
  td {
    padding: 9px 14px; border-bottom: 1px solid #f1f5f9; color: #334155;
  }
  tr:hover td { background: #f8fafc; }
  .tag {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 11px; font-weight: 600;
  }
  .tag-buy { background: #fee2e2; color: #dc2626; }
  .tag-sell { background: #dcfce7; color: #16a34a; }
  .tag-stop { background: #fef3c7; color: #d97706; }
  .tag-add { background: #e0e7ff; color: #4f46e5; }

  /* ===== Strategy Info ===== */
  .info-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px;
  }
  .info-item {
    background: #fff; border-radius: 8px; padding: 12px 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  }
  .info-item .label { font-size: 11px; color: #94a3b8; margin-bottom: 2px; }
  .info-item .value { font-size: 14px; font-weight: 600; color: #334155; }

  /* ===== Footer ===== */
  .footer {
    text-align: center; padding: 20px; font-size: 12px; color: #94a3b8;
  }

  /* ===== Loading ===== */
  .loading-overlay {
    position: fixed; inset: 0; background: rgba(15,23,42,0.7);
    display: none; align-items: center; justify-content: center; z-index: 999;
  }
  .loading-overlay.show { display: flex; }
  .loading-spinner {
    width: 40px; height: 40px; border: 3px solid rgba(255,255,255,0.2);
    border-top-color: #3b82f6; border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .loading-text { color: #fff; margin-left: 12px; font-size: 14px; }

  /* ===== Toast ===== */
  .toast {
    position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%);
    background: #1e293b; color: #fff; padding: 10px 24px; border-radius: 8px;
    font-size: 13px; z-index: 998; opacity: 0; transition: opacity 0.3s;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
  }
  .toast.show { opacity: 1; }
</style>
</head>
<body>

<!-- ===== 侧边栏 ===== -->
<div class="sidebar">
  <div class="sidebar-header">
    <h2>海龟策略控制台</h2>
    <p>多标的回测 / 参数调节 / 数据导入</p>
  </div>

  <!-- 股票列表 -->
  <div class="sidebar-section">
    <div class="sidebar-section-title">股票标的</div>
    <div class="stock-list" id="stockList"></div>
  </div>

  <!-- 上传数据 -->
  <div class="sidebar-section">
    <div class="sidebar-section-title">导入数据</div>
    <label class="upload-btn">
      <span>📁 上传 CSV 数据文件</span>
      <input type="file" id="fileInput" accept=".csv">
    </label>
    <p style="font-size: 10px; color: #475569; margin-top: 6px; line-height: 1.5;">
      支持格式: date,open,high,low,close,vol
    </p>
  </div>

  <!-- 参数预设 -->
  <div class="sidebar-section">
    <div class="sidebar-section-title">策略预设</div>
    <select class="preset-select" id="presetSelect">
      <option value="classic">经典海龟 (20/10/2ATR)</option>
      <option value="aggressive">激进型 (10/5/1.5ATR)</option>
      <option value="conservative">保守型 (55/20/3ATR)</option>
      <option value="custom">自定义</option>
    </select>
  </div>

  <!-- 参数调节 -->
  <div class="sidebar-section" style="flex: 1;">
    <div class="sidebar-section-title">策略参数</div>

    <div class="param-group">
      <div class="param-label">
        <span>入场通道周期</span>
        <span class="param-value" id="val_entry">20 日</span>
      </div>
      <input type="range" class="param-slider" id="param_entry" min="5" max="60" value="20" step="1">
    </div>

    <div class="param-group">
      <div class="param-label">
        <span>出场通道周期</span>
        <span class="param-value" id="val_exit">10 日</span>
      </div>
      <input type="range" class="param-slider" id="param_exit" min="3" max="40" value="10" step="1">
    </div>

    <div class="param-group">
      <div class="param-label">
        <span>ATR 计算周期</span>
        <span class="param-value" id="val_atr">20 日</span>
      </div>
      <input type="range" class="param-slider" id="param_atr" min="5" max="60" value="20" step="1">
    </div>

    <div class="param-group">
      <div class="param-label">
        <span>止损 ATR 倍数</span>
        <span class="param-value" id="val_stop">2.0 ×</span>
      </div>
      <input type="range" class="param-slider" id="param_stop" min="0.5" max="5" value="2" step="0.5">
    </div>

    <div class="param-group">
      <div class="param-label">
        <span>每单位风险比例</span>
        <span class="param-value" id="val_risk">1.0 %</span>
      </div>
      <input type="range" class="param-slider" id="param_risk" min="0.5" max="5" value="1" step="0.5">
    </div>

    <div class="param-group">
      <div class="param-label">
        <span>最大加仓单位</span>
        <span class="param-value" id="val_units">4 个</span>
      </div>
      <input type="range" class="param-slider" id="param_units" min="1" max="8" value="4" step="1">
    </div>

    <div class="param-group">
      <div class="param-label">
        <span>加仓间隔 ATR</span>
        <span class="param-value" id="val_add">0.5 ×</span>
      </div>
      <input type="range" class="param-slider" id="param_add" min="0.25" max="2" value="0.5" step="0.25">
    </div>

    <div class="param-group">
      <div class="param-label">
        <span>初始资金 (万元)</span>
        <span class="param-value" id="val_capital">10.0 万</span>
      </div>
      <input type="range" class="param-slider" id="param_capital" min="1" max="100" value="10" step="1">
    </div>
  </div>

  <!-- 操作按钮 -->
  <div class="sidebar-section" style="border-bottom: none;">
    <button class="run-btn" id="runBtn">▶ 运行回测</button>
    <button class="reset-btn" id="resetBtn">↺ 恢复默认参数</button>
  </div>
</div>

<!-- ===== 主内容区 ===== -->
<div class="main-content">

  <div class="header">
    <h1>海龟交易策略回测看板</h1>
    <div class="subtitle" id="subtitle">加载中...</div>
    <div class="meta-row" id="metaRow"></div>
  </div>

  <div class="container">

    <!-- ===== 核心指标卡片 ===== -->
    <div class="metrics-grid" id="metricsGrid"></div>

    <!-- ===== 策略参数 ===== -->
    <div class="chart-card">
      <div class="chart-title"><span class="icon"></span>策略参数配置</div>
      <div class="chart-desc">海龟交易策略核心参数与回测设置</div>
      <div class="info-grid" id="paramGrid"></div>
    </div>

    <!-- ===== 图1: 股价 + 通道 + 交易信号 ===== -->
    <div class="chart-card">
      <div class="chart-title"><span class="icon"></span>股价、唐奇安通道与交易信号</div>
      <div class="chart-desc">收盘价走势与通道线，标记买卖信号点</div>
      <div class="chart-intro">
        <strong>图表说明：</strong>本图展示股票收盘价走势（蓝色实线），叠加 <strong>唐奇安通道</strong>——红色虚线为入场通道上轨（过去N日最高价），绿色虚线为出场通道下轨（过去M日最低价）。当收盘价<strong>突破上轨</strong>时产生买入信号（红色▲），当收盘价<strong>跌破下轨</strong>时产生卖出信号（绿色▽）。通道宽度反映了市场的波动区间，突破通道意味着趋势可能启动。
      </div>
      <div id="chart1" class="chart-container" style="height: 450px;"></div>
    </div>

    <!-- ===== 图2: ATR ===== -->
    <div class="chart-card">
      <div class="chart-title"><span class="icon"></span>ATR (Average True Range) 走势</div>
      <div class="chart-desc">20日ATR数值与ATR百分比（占收盘价比例）</div>
      <div class="chart-intro">
        <strong>图表说明：</strong>ATR（平均真实波幅）衡量市场的波动程度，数值越大表示波动越剧烈。橙色面积图为ATR绝对值（左轴），紫色点线为ATR百分比（右轴，ATR/收盘价×100%）。ATR在海龟策略中有两个核心用途：<strong>①止损定价</strong>——止损价 = 买入价 - N×ATR；<strong>②仓位管理</strong>——每单位交易股数 = (账户资金×风险比例) / (N×ATR×100)。当ATR升高时，策略会自动减小仓位以控制风险。
      </div>
      <div id="chart2" class="chart-container" style="height: 300px;"></div>
    </div>

    <!-- ===== 图3 + 图4: 净值对比 & 累计回报 ===== -->
    <div class="two-col">
      <div class="chart-card">
        <div class="chart-title"><span class="icon"></span>策略净值 vs 买入持有基准</div>
        <div class="chart-desc">海龟策略净值曲线与买入持有净值对比</div>
        <div class="chart-intro">
          <strong>图表说明：</strong>红色线为海龟策略的账户净值变化，蓝色线为同期"买入并持有"策略的净值基准。若红线在蓝线之上，说明策略优于被动持有；若在下方，说明策略表现不及基准。通过对比可直观评估海龟策略的择时效果——在上涨趋势中能否跟上、在下跌趋势中能否规避回撤。
        </div>
        <div id="chart3" class="chart-container" style="height: 320px;"></div>
      </div>
      <div class="chart-card">
        <div class="chart-title"><span class="icon"></span>累计回报对比</div>
        <div class="chart-desc">策略与基准的累计回报率(%)走势</div>
        <div class="chart-intro">
          <strong>图表说明：</strong>将策略和基准的日收益率逐日累乘，得到累计回报率（%）。红色面积线为策略累计回报，蓝色面积线为基准累计回报。0%为盈亏分界线，高于0%为盈利，低于0%为亏损。两条线之间的差距即为<strong>超额收益</strong>（Alpha），正值表示策略跑赢基准。
        </div>
        <div id="chart4" class="chart-container" style="height: 320px;"></div>
      </div>
    </div>

    <!-- ===== 图5: 回撤曲线 ===== -->
    <div class="chart-card">
      <div class="chart-title"><span class="icon"></span>最大回撤对比 (Drawdown)</div>
      <div class="chart-desc">策略与基准的回撤曲线对比，反映策略的风险控制能力</div>
      <div class="chart-intro">
        <strong>图表说明：</strong>回撤指从历史最高净值到当前净值的下跌幅度，以百分比表示。红色面积为策略回撤，蓝色面积为基准回撤。<strong>最大回撤（MDD）</strong>是衡量策略风险的核心指标——回撤越浅，说明策略在市场下跌时的抗风险能力越强。理想情况下，策略回撤应显著小于基准回撤。图中可观察策略在市场大幅回调时是否有效减仓或空仓。
      </div>
      <div id="chart5" class="chart-container" style="height: 300px;"></div>
    </div>

    <!-- ===== 图6: 持仓状态 ===== -->
    <div class="chart-card">
      <div class="chart-title"><span class="icon"></span>持仓状态与通道区间</div>
      <div class="chart-desc">持仓区间（红色背景）与唐奇安通道上下轨，展示策略的持仓时机</div>
      <div class="chart-intro">
        <strong>图表说明：</strong>蓝色实线为收盘价，红色半透明区域标记了策略<strong>持仓时段</strong>，叠加红色虚线（入场通道上轨）和绿色虚线（出场通道下轨）。通过此图可直观看到策略的持仓节奏——在哪些时段进场、持有多久、何时退出。理想的海龟策略应在趋势启动时持仓，在趋势结束时空仓，避免在震荡行情中频繁进出。
      </div>
      <div id="chart6" class="chart-container" style="height: 320px;"></div>
    </div>

    <!-- ===== 交易记录表 ===== -->
    <div class="table-card">
      <div class="table-title"><span class="icon"></span>完整交易记录</div>
      <table id="tradeTable">
        <thead>
          <tr>
            <th>序号</th>
            <th>买入日期</th>
            <th>买入价</th>
            <th>卖出日期</th>
            <th>卖出价</th>
            <th>股数</th>
            <th>盈亏(¥)</th>
            <th>收益率(%)</th>
            <th>退出方式</th>
          </tr>
        </thead>
        <tbody id="tradeTableBody"></tbody>
      </table>
    </div>

    <!-- ===== 买卖信号汇总 ===== -->
    <div class="two-col">
      <div class="table-card">
        <div class="table-title"><span class="icon"></span>买入信号明细</div>
        <table>
          <thead>
            <tr><th>日期</th><th>收盘价</th><th>通道上轨</th><th>ATR</th></tr>
          </thead>
          <tbody id="buySignalsBody"></tbody>
        </table>
      </div>
      <div class="table-card">
        <div class="table-title"><span class="icon"></span>卖出信号明细</div>
        <table>
          <thead>
            <tr><th>日期</th><th>收盘价</th><th>通道下轨</th><th>ATR</th></tr>
          </thead>
          <tbody id="sellSignalsBody"></tbody>
        </table>
      </div>
    </div>

  </div>

  <div class="footer">
    海龟交易策略回测看板 | 支持多标的切换与自定义数据导入 | 本报告仅供学习研究，不构成投资建议
  </div>
</div>

<!-- Loading -->
<div class="loading-overlay" id="loadingOverlay">
  <div class="loading-spinner"></div>
  <span class="loading-text" id="loadingText">正在计算策略...</span>
</div>

<!-- Toast -->
<div class="toast" id="toast"></div>

<script>
// ===== 内置股票数据 =====
const STOCKS_DATA = ''' + stocks_json + r''';

// ===== 默认参数 =====
const DEFAULT_PARAMS = {
  entry_channel: 20,
  exit_channel: 10,
  atr_period: 20,
  stop_loss_atr: 2.0,
  risk_per_unit: 0.01,
  max_units: 4,
  add_unit_atr: 0.5,
  initial_capital: 100000,
  commission_rate: 0.0003,
  stamp_tax_rate: 0.0005,
  slippage: 0.001,
};

// ===== 策略预设 =====
const PRESETS = {
  classic: { entry_channel: 20, exit_channel: 10, atr_period: 20, stop_loss_atr: 2.0, risk_per_unit: 0.01, max_units: 4, add_unit_atr: 0.5 },
  aggressive: { entry_channel: 10, exit_channel: 5, atr_period: 10, stop_loss_atr: 1.5, risk_per_unit: 0.02, max_units: 6, add_unit_atr: 0.5 },
  conservative: { entry_channel: 55, exit_channel: 20, atr_period: 20, stop_loss_atr: 3.0, risk_per_unit: 0.005, max_units: 2, add_unit_atr: 1.0 },
};

// ===== 当前状态 =====
let currentStock = null;
let currentData = null;
let chartInstances = {};

// ===== 工具函数 =====
function fmtDate(d) {
  if (typeof d === 'string') {
    if (d.length === 8) return d.substring(0,4) + '-' + d.substring(4,6) + '-' + d.substring(6,8);
    return d;
  }
  return d;
}

function fmtDateShort(d) {
  if (typeof d === 'string' && d.length >= 8) {
    return d.substring(0,4) + '-' + d.substring(4,6) + '-' + d.substring(6,8);
  }
  return d;
}

function showToast(msg) {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2500);
}

function showLoading(text) {
  document.getElementById('loadingText').textContent = text || '正在计算...';
  document.getElementById('loadingOverlay').classList.add('show');
}

function hideLoading() {
  document.getElementById('loadingOverlay').classList.remove('show');
}

// ===== 股票列表渲染 =====
function renderStockList() {
  const list = document.getElementById('stockList');
  list.innerHTML = '';
  for (const code in STOCKS_DATA) {
    const s = STOCKS_DATA[code];
    const item = document.createElement('div');
    item.className = 'stock-item' + (currentStock === code ? ' active' : '');
    item.innerHTML = `
      <span class="stock-name">${s.name}</span>
      <span class="stock-code">${s.code}</span>
    `;
    item.onclick = () => switchStock(code);
    list.appendChild(item);
  }
}

// ===== 切换股票 =====
function switchStock(code) {
  if (!STOCKS_DATA[code]) return;
  currentStock = code;
  currentData = STOCKS_DATA[code].data;
  renderStockList();
  runBacktest();
  showToast(`已切换至 ${STOCKS_DATA[code].name} (${code})`);
}

// ===== 文件上传 =====
document.getElementById('fileInput').addEventListener('change', function(e) {
  const file = e.target.files[0];
  if (!file) return;

  showLoading('正在解析文件...');
  const reader = new FileReader();
  reader.onload = function(evt) {
    try {
      const text = evt.target.result;
      const lines = text.split(/\r?\n/).filter(l => l.trim());
      if (lines.length < 2) { showToast('文件内容为空或格式不对'); hideLoading(); return; }

      const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
      const dateIdx = headers.indexOf('date');
      const openIdx = headers.indexOf('open');
      const highIdx = headers.indexOf('high');
      const lowIdx = headers.indexOf('low');
      const closeIdx = headers.indexOf('close');
      const volIdx = headers.indexOf('volume_hands') !== -1 ? headers.indexOf('volume_hands') :
                     headers.indexOf('vol') !== -1 ? headers.indexOf('vol') : -1;

      if (dateIdx === -1 || openIdx === -1 || highIdx === -1 || lowIdx === -1 || closeIdx === -1) {
        showToast('CSV需包含 date,open,high,low,close 列');
        hideLoading();
        return;
      }

      const data = [];
      for (let i = 1; i < lines.length; i++) {
        const parts = lines[i].split(',');
        data.push({
          date: parts[dateIdx].trim(),
          open: parseFloat(parts[openIdx]),
          high: parseFloat(parts[highIdx]),
          low: parseFloat(parts[lowIdx]),
          close: parseFloat(parts[closeIdx]),
          vol: volIdx !== -1 ? parseFloat(parts[volIdx]) || 0 : 0,
        });
      }
      data.sort((a, b) => a.date.localeCompare(b.date));

      if (data.length < 30) {
        showToast('数据行数过少（至少需要30条），当前: ' + data.length);
        hideLoading();
        return;
      }

      // 添加到 STOCKS_DATA
      const fileName = file.name.replace(/\.csv$/i, '');
      const customCode = 'UPLOAD_' + Date.now();
      STOCKS_DATA[customCode] = {
        name: fileName,
        code: customCode,
        adjust: '用户导入',
        data: data,
      };

      // 渲染列表并切换
      renderStockList();
      switchStock(customCode);
      showToast(`成功导入 ${fileName} (${data.length} 条数据)`);
    } catch (err) {
      showToast('文件解析失败: ' + err.message);
    }
    hideLoading();
  };
  reader.readAsText(file, 'UTF-8');
  e.target.value = ''; // 允许再次上传同一文件
});

// ===== 参数滑块联动 =====
function setupParamSliders() {
  const sliders = [
    { id: 'param_entry', valId: 'val_entry', key: 'entry_channel', suffix: ' 日', toVal: v => v },
    { id: 'param_exit', valId: 'val_exit', key: 'exit_channel', suffix: ' 日', toVal: v => v },
    { id: 'param_atr', valId: 'val_atr', key: 'atr_period', suffix: ' 日', toVal: v => v },
    { id: 'param_stop', valId: 'val_stop', key: 'stop_loss_atr', suffix: ' ×', toVal: v => parseFloat(v).toFixed(1) },
    { id: 'param_risk', valId: 'val_risk', key: 'risk_per_unit', suffix: ' %', toVal: v => parseFloat(v).toFixed(1), transform: v => v / 100 },
    { id: 'param_units', valId: 'val_units', key: 'max_units', suffix: ' 个', toVal: v => v },
    { id: 'param_add', valId: 'val_add', key: 'add_unit_atr', suffix: ' ×', toVal: v => parseFloat(v).toFixed(2) },
    { id: 'param_capital', valId: 'val_capital', key: 'initial_capital', suffix: ' 万', toVal: v => parseFloat(v).toFixed(1), transform: v => v * 10000 },
  ];

  sliders.forEach(s => {
    const slider = document.getElementById(s.id);
    const valDisplay = document.getElementById(s.valId);
    slider.addEventListener('input', function() {
      const rawVal = this.value;
      valDisplay.textContent = s.toVal(rawVal) + s.suffix;
      document.getElementById('presetSelect').value = 'custom';
    });
  });

  // 预设切换
  document.getElementById('presetSelect').addEventListener('change', function() {
    const preset = PRESETS[this.value];
    if (!preset) return;
    if (preset.entry_channel) { document.getElementById('param_entry').value = preset.entry_channel; document.getElementById('val_entry').textContent = preset.entry_channel + ' 日'; }
    if (preset.exit_channel) { document.getElementById('param_exit').value = preset.exit_channel; document.getElementById('val_exit').textContent = preset.exit_channel + ' 日'; }
    if (preset.atr_period) { document.getElementById('param_atr').value = preset.atr_period; document.getElementById('val_atr').textContent = preset.atr_period + ' 日'; }
    if (preset.stop_loss_atr) { document.getElementById('param_stop').value = preset.stop_loss_atr; document.getElementById('val_stop').textContent = preset.stop_loss_atr.toFixed(1) + ' ×'; }
    if (preset.risk_per_unit) { document.getElementById('param_risk').value = preset.risk_per_unit * 100; document.getElementById('val_risk').textContent = (preset.risk_per_unit * 100).toFixed(1) + ' %'; }
    if (preset.max_units) { document.getElementById('param_units').value = preset.max_units; document.getElementById('val_units').textContent = preset.max_units + ' 个'; }
    if (preset.add_unit_atr) { document.getElementById('param_add').value = preset.add_unit_atr; document.getElementById('val_add').textContent = preset.add_unit_atr.toFixed(2) + ' ×'; }
  });
}

// ===== 获取当前参数 =====
function getCurrentParams() {
  return {
    entry_channel: parseInt(document.getElementById('param_entry').value),
    exit_channel: parseInt(document.getElementById('param_exit').value),
    atr_period: parseInt(document.getElementById('param_atr').value),
    stop_loss_atr: parseFloat(document.getElementById('param_stop').value),
    risk_per_unit: parseFloat(document.getElementById('param_risk').value) / 100,
    max_units: parseInt(document.getElementById('param_units').value),
    add_unit_atr: parseFloat(document.getElementById('param_add').value),
    initial_capital: parseFloat(document.getElementById('param_capital').value) * 10000,
    commission_rate: 0.0003,
    stamp_tax_rate: 0.0005,
    slippage: 0.001,
  };
}

// ===== 恢复默认参数 =====
document.getElementById('resetBtn').addEventListener('click', function() {
  document.getElementById('param_entry').value = 20; document.getElementById('val_entry').textContent = '20 日';
  document.getElementById('param_exit').value = 10; document.getElementById('val_exit').textContent = '10 日';
  document.getElementById('param_atr').value = 20; document.getElementById('val_atr').textContent = '20 日';
  document.getElementById('param_stop').value = 2; document.getElementById('val_stop').textContent = '2.0 ×';
  document.getElementById('param_risk').value = 1; document.getElementById('val_risk').textContent = '1.0 %';
  document.getElementById('param_units').value = 4; document.getElementById('val_units').textContent = '4 个';
  document.getElementById('param_add').value = 0.5; document.getElementById('val_add').textContent = '0.50 ×';
  document.getElementById('param_capital').value = 10; document.getElementById('val_capital').textContent = '10.0 万';
  document.getElementById('presetSelect').value = 'classic';
  runBacktest();
  showToast('参数已恢复默认值');
});

// ===== 运行回测按钮 =====
document.getElementById('runBtn').addEventListener('click', function() {
  runBacktest();
});

// ============================================================
// 海龟策略核心计算引擎 (JavaScript 实现)
// ============================================================
function runTurtleStrategy(data, params) {
  const n = data.length;
  const entryCh = params.entry_channel;
  const exitCh = params.exit_channel;
  const atrPeriod = params.atr_period;
  const stopLossATR = params.stop_loss_atr;
  const riskPerUnit = params.risk_per_unit;
  const maxUnits = params.max_units;
  const addUnitATR = params.add_unit_atr;
  const initialCapital = params.initial_capital;
  const commissionRate = params.commission_rate;
  const stampTaxRate = params.stamp_tax_rate;
  const slippage = params.slippage;

  // --- 1. 唐奇安通道 ---
  const upperChannel = new Array(n).fill(null);
  const lowerChannelExit = new Array(n).fill(null);

  for (let i = 0; i < n; i++) {
    // 入场通道上轨: 过去 entryCh 日最高价 (不含当日)
    if (i >= entryCh) {
      let maxHigh = -Infinity;
      for (let j = i - entryCh; j < i; j++) {
        if (data[j].high > maxHigh) maxHigh = data[j].high;
      }
      upperChannel[i] = maxHigh;
    }
    // 出场通道下轨: 过去 exitCh 日最低价 (不含当日)
    if (i >= exitCh) {
      let minLow = Infinity;
      for (let j = i - exitCh; j < i; j++) {
        if (data[j].low < minLow) minLow = data[j].low;
      }
      lowerChannelExit[i] = minLow;
    }
  }

  // --- 2. ATR ---
  const atr = new Array(n).fill(null);
  const atrPct = new Array(n).fill(null);
  const tr = new Array(n).fill(0);

  for (let i = 0; i < n; i++) {
    if (i === 0) {
      tr[i] = data[i].high - data[i].low;
    } else {
      const tr1 = data[i].high - data[i].low;
      const tr2 = Math.abs(data[i].high - data[i-1].close);
      const tr3 = Math.abs(data[i].low - data[i-1].close);
      tr[i] = Math.max(tr1, tr2, tr3);
    }
    // ATR: 简单移动平均
    if (i >= atrPeriod - 1) {
      let sum = 0;
      for (let j = i - atrPeriod + 1; j <= i; j++) sum += tr[j];
      atr[i] = sum / atrPeriod;
      atrPct[i] = atr[i] / data[i].close * 100;
    }
  }

  // --- 3. 交易信号 ---
  const signal = new Array(n).fill(0);
  let currentState = 0; // 0=空仓, 1=持仓

  for (let i = 0; i < n; i++) {
    if (upperChannel[i] !== null && data[i].close > upperChannel[i]) {
      if (currentState === 0) {
        signal[i] = 1;
        currentState = 1;
      }
    } else if (lowerChannelExit[i] !== null && data[i].close < lowerChannelExit[i]) {
      if (currentState === 1) {
        signal[i] = -1;
        currentState = 0;
      }
    }
  }

  // 持仓状态
  const position = new Array(n).fill(0);
  let currentPos = 0;
  for (let i = 0; i < n; i++) {
    if (signal[i] === 1) currentPos = 1;
    else if (signal[i] === -1) currentPos = 0;
    position[i] = currentPos;
  }

  // --- 4. 回测 ---
  const trades = [];
  let cash = initialCapital;
  let shares = 0;
  let entryPrice = 0;
  let stopLoss = 0;
  let unitsHeld = 0;
  let lastAddPrice = 0;
  let positionOpen = false;

  for (let i = 0; i < n - 1; i++) {
    const today = data[i];
    const tomorrow = data[i + 1];
    const tradeDate = tomorrow.date;
    const tradePrice = tomorrow.open;
    const atrVal = atr[i];

    if (atrVal === null || atrVal === 0) continue;

    const buyPrice = tradePrice * (1 + slippage);
    const sellPrice = tradePrice * (1 - slippage);

    // 检查止损
    if (positionOpen && shares > 0) {
      if (tomorrow.low <= stopLoss) {
        const stopPrice = stopLoss * (1 - slippage);
        const revenue = shares * stopPrice;
        const commission = Math.max(revenue * commissionRate, 5);
        const stampTax = revenue * stampTaxRate;
        cash += (revenue - commission - stampTax);
        trades.push({
          date: tradeDate, action: 'STOP_LOSS', price: stopPrice,
          shares: shares, amount: revenue, commission: commission, stamp_tax: stampTax,
          cash_after: cash, shares_after: 0, atr: atrVal, stop_loss_price: stopLoss,
        });
        shares = 0; positionOpen = false; unitsHeld = 0;
        entryPrice = 0; stopLoss = 0;
        continue;
      }

      // 加仓
      if (unitsHeld < maxUnits && tomorrow.close >= lastAddPrice + addUnitATR * atrVal) {
        const unitRisk = cash * riskPerUnit;
        let unitShares = Math.floor(unitRisk / (stopLossATR * atrVal * 100)) * 100;
        if (unitShares > 0 && cash >= unitShares * buyPrice) {
          const cost = unitShares * buyPrice;
          const commission = Math.max(cost * commissionRate, 5);
          cash -= (cost + commission);
          shares += unitShares;
          lastAddPrice = buyPrice;
          const newStop = buyPrice - stopLossATR * atrVal;
          if (newStop > stopLoss) stopLoss = newStop;
          unitsHeld++;
          trades.push({
            date: tradeDate, action: 'ADD_UNIT', price: buyPrice,
            shares: unitShares, amount: cost, commission: commission,
            cash_after: cash, shares_after: shares, atr: atrVal, stop_loss_price: stopLoss,
          });
        }
      }
    }

    // 买入信号
    if (signal[i] === 1 && !positionOpen) {
      const unitRisk = cash * riskPerUnit;
      let unitShares = Math.floor(unitRisk / (stopLossATR * atrVal * 100)) * 100;
      if (unitShares > 0) {
        const cost = unitShares * buyPrice;
        const commission = Math.max(cost * commissionRate, 5);
        cash -= (cost + commission);
        shares = unitShares;
        entryPrice = buyPrice;
        lastAddPrice = buyPrice;
        stopLoss = buyPrice - stopLossATR * atrVal;
        unitsHeld = 1;
        positionOpen = true;
        trades.push({
          date: tradeDate, action: 'BUY', price: buyPrice,
          shares: unitShares, amount: cost, commission: commission,
          cash_after: cash, shares_after: shares, atr: atrVal, stop_loss_price: stopLoss,
        });
      }
    }

    // 卖出信号
    else if (signal[i] === -1 && positionOpen && shares > 0) {
      const revenue = shares * sellPrice;
      const commission = Math.max(revenue * commissionRate, 5);
      const stampTax = revenue * stampTaxRate;
      cash += (revenue - commission - stampTax);
      trades.push({
        date: tradeDate, action: 'SELL', price: sellPrice,
        shares: shares, amount: revenue, commission: commission, stamp_tax: stampTax,
        cash_after: cash, shares_after: 0, atr: atrVal,
      });
      shares = 0; positionOpen = false; unitsHeld = 0;
      entryPrice = 0; stopLoss = 0;
    }
  }

  // 期末估值
  const finalClose = data[n - 1].close;
  const finalValue = cash + shares * finalClose;

  // --- 5. 净值曲线 ---
  const stockReturn = new Array(n).fill(0);
  for (let i = 1; i < n; i++) {
    stockReturn[i] = (data[i].close - data[i-1].close) / data[i-1].close;
  }

  // 持仓标志
  const positionFlag = new Array(n).fill(0);
  let holding = false;
  for (let i = 0; i < n; i++) {
    if (signal[i] === 1) holding = true;
    else if (signal[i] === -1) holding = false;
    positionFlag[i] = holding ? 1.0 : 0.0;
  }

  // 策略日收益
  const strategyReturn = new Array(n).fill(0);
  for (let i = 1; i < n; i++) {
    strategyReturn[i] = positionFlag[i - 1] * stockReturn[i];
  }

  // 累计回报
  const strategyCumReturn = new Array(n).fill(0);
  const benchmarkCumReturn = new Array(n).fill(0);
  let stratCum = 0, benchCum = 0;
  for (let i = 0; i < n; i++) {
    stratCum = (stratCum + 1) * (1 + strategyReturn[i]) - 1;
    benchCum = (benchCum + 1) * (1 + stockReturn[i]) - 1;
    strategyCumReturn[i] = stratCum;
    benchmarkCumReturn[i] = benchCum;
  }

  // 净值
  const strategyNAV = strategyCumReturn.map(r => initialCapital * (1 + r));
  const benchmarkNAV = benchmarkCumReturn.map(r => initialCapital * (1 + r));

  // 回撤
  const drawdown = new Array(n).fill(0);
  const benchmarkDrawdown = new Array(n).fill(0);
  let stratPeak = initialCapital, benchPeak = initialCapital;
  for (let i = 0; i < n; i++) {
    if (strategyNAV[i] > stratPeak) stratPeak = strategyNAV[i];
    drawdown[i] = (strategyNAV[i] - stratPeak) / stratPeak;
    if (benchmarkNAV[i] > benchPeak) benchPeak = benchmarkNAV[i];
    benchmarkDrawdown[i] = (benchmarkNAV[i] - benchPeak) / benchPeak;
  }

  // --- 6. 量化指标 ---
  const totalReturn = (finalValue - initialCapital) / initialCapital * 100;
  const benchmarkTotalReturn = (data[n-1].close - data[0].close) / data[0].close * 100;
  const tradingDays = n;
  const annualizedReturn = (Math.pow(1 + totalReturn / 100, 252 / tradingDays) - 1) * 100;
  const benchmarkAnnualized = (Math.pow(1 + benchmarkTotalReturn / 100, 252 / tradingDays) - 1) * 100;
  const maxDrawdown = Math.min(...drawdown) * 100;
  const benchmarkMaxDrawdown = Math.min(...benchmarkDrawdown) * 100;

  // Sharpe
  const rfDaily = 0.02 / 252;
  let excessSum = 0, excessSqSum = 0;
  for (let i = 0; i < n; i++) {
    const excess = strategyReturn[i] - rfDaily;
    excessSum += excess;
    excessSqSum += excess * excess;
  }
  const excessMean = excessSum / n;
  const excessStd = Math.sqrt(excessSqSum / n - excessMean * excessMean);
  const sharpeRatio = excessStd > 0 ? Math.sqrt(252) * excessMean / excessStd : 0;

  // Benchmark Sharpe
  let benchExcessSum = 0, benchExcessSqSum = 0;
  for (let i = 0; i < n; i++) {
    const excess = stockReturn[i] - rfDaily;
    benchExcessSum += excess;
    benchExcessSqSum += excess * excess;
  }
  const benchExcessMean = benchExcessSum / n;
  const benchExcessStd = Math.sqrt(benchExcessSqSum / n - benchExcessMean * benchExcessMean);
  const benchmarkSharpe = benchExcessStd > 0 ? Math.sqrt(252) * benchExcessMean / benchExcessStd : 0;

  // Sortino
  let downsideSum = 0, downsideCount = 0;
  for (let i = 0; i < n; i++) {
    const excess = strategyReturn[i] - rfDaily;
    if (excess < 0) { downsideSum += excess * excess; downsideCount++; }
  }
  const downsideStd = downsideCount > 0 ? Math.sqrt(downsideSum / downsideCount) : 0;
  const sortinoRatio = downsideStd > 0 ? Math.sqrt(252) * excessMean / downsideStd : 0;

  // Calmar
  const calmarRatio = maxDrawdown !== 0 ? Math.abs(annualizedReturn / maxDrawdown) : 0;

  // 交易配对统计
  const tradeDetails = [];
  let wins = 0;
  let i = 0;
  while (i < trades.length) {
    const t = trades[i];
    if (t.action === 'BUY') {
      let allBuyCost = t.amount + t.commission;
      let allBuyShares = t.shares;
      let buyDate = t.date;
      let buyPrice = t.price;
      let j = i + 1;
      while (j < trades.length && trades[j].action === 'ADD_UNIT') {
        allBuyCost += trades[j].amount + trades[j].commission;
        allBuyShares += trades[j].shares;
        j++;
      }
      if (j < trades.length && (trades[j].action === 'SELL' || trades[j].action === 'STOP_LOSS')) {
        const sellTrade = trades[j];
        const sellRevenue = sellTrade.amount;
        const totalCost = (sellTrade.commission || 0) + (sellTrade.stamp_tax || 0);
        const pnl = sellRevenue - allBuyCost - totalCost;
        tradeDetails.push({
          buy_date: fmtDateShort(buyDate), buy_price: buyPrice,
          sell_date: fmtDateShort(sellTrade.date), sell_price: sellTrade.price,
          shares: allBuyShares, pnl: pnl,
          return_pct: pnl / allBuyCost * 100, exit_type: sellTrade.action,
        });
        if (pnl > 0) wins++;
        i = j + 1;
      } else {
        i = j;
      }
    } else {
      i++;
    }
  }

  const totalRoundTrips = tradeDetails.length;
  const winRate = totalRoundTrips > 0 ? wins / totalRoundTrips * 100 : 0;
  const pnlList = tradeDetails.map(t => t.pnl);
  const avgPnl = pnlList.length > 0 ? pnlList.reduce((a,b) => a+b, 0) / pnlList.length : 0;
  const maxProfit = pnlList.length > 0 ? Math.max(...pnlList) : 0;
  const maxLoss = pnlList.length > 0 ? Math.min(...pnlList) : 0;
  const profitSum = pnlList.filter(p => p > 0).reduce((a,b) => a+b, 0);
  const lossSum = Math.abs(pnlList.filter(p => p < 0).reduce((a,b) => a+b, 0));
  const profitFactor = lossSum > 0 ? profitSum / lossSum : (profitSum > 0 ? Infinity : 0);

  const buyCount = trades.filter(t => t.action === 'BUY').length;
  const sellCount = trades.filter(t => t.action === 'SELL').length;
  const stopLossCount = trades.filter(t => t.action === 'STOP_LOSS').length;
  const addUnitCount = trades.filter(t => t.action === 'ADD_UNIT').length;

  // 买卖信号明细
  const buySignals = [];
  const sellSignals = [];
  for (let i = 0; i < n; i++) {
    if (signal[i] === 1) {
      buySignals.push({ date: fmtDateShort(data[i].date), price: data[i].close, upper_channel: upperChannel[i] || 0, atr: atr[i] || 0 });
    } else if (signal[i] === -1) {
      sellSignals.push({ date: fmtDateShort(data[i].date), price: data[i].close, lower_channel_exit: lowerChannelExit[i] || 0, atr: atr[i] || 0 });
    }
  }

  return {
    chartData: {
      dates: data.map(d => d.date),
      close: data.map(d => d.close),
      high: data.map(d => d.high),
      low: data.map(d => d.low),
      upper_channel: upperChannel.map(v => v !== null ? Math.round(v * 100) / 100 : null),
      lower_channel_exit: lowerChannelExit.map(v => v !== null ? Math.round(v * 100) / 100 : null),
      atr: atr.map(v => v !== null ? Math.round(v * 100) / 100 : null),
      atr_pct: atrPct.map(v => v !== null ? Math.round(v * 100) / 100 : null),
      signal: signal,
      position: position,
      strategy_nav: strategyNAV.map(v => Math.round(v * 100) / 100),
      benchmark_nav: benchmarkNAV.map(v => Math.round(v * 100) / 100),
      strategy_cum_return: strategyCumReturn.map(v => Math.round(v * 10000) / 100),
      benchmark_cum_return: benchmarkCumReturn.map(v => Math.round(v * 10000) / 100),
      drawdown: drawdown.map(v => Math.round(v * 10000) / 100),
      benchmark_drawdown: benchmarkDrawdown.map(v => Math.round(v * 10000) / 100),
    },
    metrics: {
      final_value: Math.round(finalValue * 100) / 100,
      net_profit: Math.round((finalValue - initialCapital) * 100) / 100,
      total_return_pct: Math.round(totalReturn * 100) / 100,
      benchmark_total_return_pct: Math.round(benchmarkTotalReturn * 100) / 100,
      excess_return_pct: Math.round((totalReturn - benchmarkTotalReturn) * 100) / 100,
      annualized_return_pct: Math.round(annualizedReturn * 100) / 100,
      benchmark_annualized_return_pct: Math.round(benchmarkAnnualized * 100) / 100,
      max_drawdown_pct: Math.round(maxDrawdown * 100) / 100,
      benchmark_max_drawdown_pct: Math.round(benchmarkMaxDrawdown * 100) / 100,
      sharpe_ratio: Math.round(sharpeRatio * 100) / 100,
      benchmark_sharpe_ratio: Math.round(benchmarkSharpe * 100) / 100,
      sortino_ratio: Math.round(sortinoRatio * 100) / 100,
      calmar_ratio: Math.round(calmarRatio * 100) / 100,
      total_trades: trades.length,
      completed_round_trips: totalRoundTrips,
      win_rate_pct: Math.round(winRate * 10) / 10,
      avg_pnl_per_trade: Math.round(avgPnl * 100) / 100,
      max_profit: Math.round(maxProfit * 100) / 100,
      max_loss: Math.round(maxLoss * 100) / 100,
      profit_factor: profitFactor === Infinity ? null : Math.round(profitFactor * 100) / 100,
      stop_loss_count: stopLossCount,
      add_unit_count: addUnitCount,
    },
    buy_signals: buySignals.map(s => ({...s, price: Math.round(s.price * 100) / 100, upper_channel: Math.round(s.upper_channel * 100) / 100, atr: Math.round(s.atr * 1000) / 1000})),
    sell_signals: sellSignals.map(s => ({...s, price: Math.round(s.price * 100) / 100, lower_channel_exit: Math.round(s.lower_channel_exit * 100) / 100, atr: Math.round(s.atr * 1000) / 1000})),
    trade_details: tradeDetails.map(t => ({
      ...t,
      buy_price: Math.round(t.buy_price * 100) / 100,
      sell_price: Math.round(t.sell_price * 100) / 100,
      pnl: Math.round(t.pnl * 100) / 100,
      return_pct: Math.round(t.return_pct * 100) / 100,
    })),
    metadata: {
      stock_name: STOCKS_DATA[currentStock] ? STOCKS_DATA[currentStock].name : '自定义',
      ts_code: STOCKS_DATA[currentStock] ? STOCKS_DATA[currentStock].code : 'CUSTOM',
      strategy: '海龟交易策略 (Turtle Trading)',
      data_range: fmtDateShort(data[0].date) + ' ~ ' + fmtDateShort(data[n-1].date),
      trading_days: n,
      initial_capital: initialCapital,
      commission_rate: commissionRate,
      stamp_tax_rate: stampTaxRate,
      slippage: slippage,
      params: params,
    },
  };
}

// ============================================================
// 渲染看板
// ============================================================
function renderDashboard(result) {
  const cd = result.chartData;
  const m = result.metrics;
  const meta = result.metadata;
  const params = meta.params;

  // --- Header ---
  document.getElementById('subtitle').textContent = `${meta.stock_name} (${meta.ts_code}) | ${meta.data_range} | ${meta.trading_days} 个交易日`;
  const metaRow = document.getElementById('metaRow');
  metaRow.innerHTML = `
    <div class="meta-item">策略类型: <strong>海龟交易法</strong></div>
    <div class="meta-item">入场通道: <strong>${params.entry_channel}日唐奇安上轨突破</strong></div>
    <div class="meta-item">出场通道: <strong>${params.exit_channel}日唐奇安下轨突破</strong></div>
    <div class="meta-item">ATR周期: <strong>${params.atr_period}日</strong></div>
    <div class="meta-item">止损: <strong>${params.stop_loss_atr}×ATR</strong></div>
    <div class="meta-item">仓位风险: <strong>${(params.risk_per_unit * 100).toFixed(1)}%/单位</strong></div>
  `;

  // --- 指标卡片 ---
  const metricsHTML = [
    { label: '累计回报 (Cumulative Return)', value: m.total_return_pct.toFixed(2) + '%', sub: '基准: ' + m.benchmark_total_return_pct.toFixed(2) + '%', cls: m.total_return_pct >= 0 ? 'positive' : 'negative' },
    { label: '最大回撤 (MDD)', value: m.max_drawdown_pct.toFixed(2) + '%', sub: '基准: ' + m.benchmark_max_drawdown_pct.toFixed(2) + '%', cls: m.max_drawdown_pct >= -15 ? 'warning' : 'negative' },
    { label: '夏普比率 (Sharpe Ratio)', value: m.sharpe_ratio.toFixed(2), sub: '基准: ' + m.benchmark_sharpe_ratio.toFixed(2), cls: m.sharpe_ratio >= 1 ? 'positive' : 'warning' },
    { label: '期末总资产', value: '¥' + m.final_value.toLocaleString('zh-CN', {maximumFractionDigits: 0}), sub: '初始: ¥' + meta.initial_capital.toLocaleString('zh-CN'), cls: m.net_profit >= 0 ? 'positive' : 'negative' },
    { label: '净利润', value: (m.net_profit >= 0 ? '+' : '') + '¥' + m.net_profit.toLocaleString('zh-CN', {maximumFractionDigits: 0}), sub: '基准超额: ' + m.excess_return_pct.toFixed(2) + '%', cls: m.net_profit >= 0 ? 'positive' : 'negative' },
    { label: '年化收益率', value: m.annualized_return_pct.toFixed(2) + '%', sub: '基准: ' + m.benchmark_annualized_return_pct.toFixed(2) + '%', cls: m.annualized_return_pct >= 0 ? 'positive' : 'negative' },
    { label: '索提诺比率 (Sortino)', value: m.sortino_ratio.toFixed(2), sub: '只计下行风险', cls: m.sortino_ratio >= 1 ? 'positive' : 'warning' },
    { label: '卡玛比率 (Calmar)', value: m.calmar_ratio.toFixed(2), sub: '年化收益/|最大回撤|', cls: m.calmar_ratio >= 1 ? 'positive' : 'warning' },
    { label: '胜率', value: m.win_rate_pct.toFixed(0) + '%', sub: m.completed_round_trips + ' 轮完整交易', cls: m.win_rate_pct >= 50 ? 'positive' : 'negative' },
    { label: '盈亏比', value: m.profit_factor !== null ? m.profit_factor.toFixed(2) : 'N/A', sub: '总盈利/总亏损', cls: (m.profit_factor !== null && m.profit_factor >= 1) ? 'positive' : 'negative' },
    { label: '总交易次数', value: m.total_trades + ' 次', sub: '止损: ' + m.stop_loss_count + ' | 加仓: ' + m.add_unit_count, cls: '' },
    { label: '平均每笔盈亏', value: '¥' + m.avg_pnl_per_trade.toFixed(0), sub: '最大盈利: ¥' + m.max_profit.toFixed(0) + ' | 最大亏损: ¥' + m.max_loss.toFixed(0), cls: m.avg_pnl_per_trade >= 0 ? 'positive' : 'negative' },
  ];
  document.getElementById('metricsGrid').innerHTML = metricsHTML.map(item => `
    <div class="metric-card ${item.cls}">
      <div class="label">${item.label}</div>
      <div class="value">${item.value}</div>
      <div class="sub">${item.sub}</div>
    </div>
  `).join('');

  // --- 参数卡片 ---
  const paramsHTML = [
    { label: '入场通道周期', value: params.entry_channel + ' 日' },
    { label: '出场通道周期', value: params.exit_channel + ' 日' },
    { label: 'ATR计算周期', value: params.atr_period + ' 日' },
    { label: '每单位风险比例', value: (params.risk_per_unit * 100).toFixed(1) + '%' },
    { label: '止损倍数', value: params.stop_loss_atr + ' × ATR' },
    { label: '最大加仓单位', value: params.max_units + ' 个' },
    { label: '加仓间隔', value: params.add_unit_atr + ' × ATR' },
    { label: '初始资金', value: '¥' + params.initial_capital.toLocaleString('zh-CN') },
    { label: '佣金费率', value: (params.commission_rate * 10000).toFixed(1) + '‱' },
    { label: '印花税', value: (params.stamp_tax_rate * 1000).toFixed(1) + '‰' },
    { label: '滑点', value: (params.slippage * 100).toFixed(1) + '%' },
    { label: '交易日数', value: meta.trading_days + ' 天' },
  ];
  document.getElementById('paramGrid').innerHTML = paramsHTML.map(item => `
    <div class="info-item">
      <div class="label">${item.label}</div>
      <div class="value">${item.value}</div>
    </div>
  `).join('');

  // --- 日期 ---
  const dates = cd.dates.map(fmtDate);

  // --- 买卖标记 ---
  const buyMarkers = result.buy_signals.map(s => ({
    name: '买入', coord: [s.date, s.price],
    itemStyle: { color: '#dc2626' },
    label: { show: true, formatter: '买\n' + s.price, position: 'bottom', fontSize: 10, color: '#dc2626', fontWeight: 'bold' },
    symbol: 'triangle', symbolSize: 14, symbolRotate: 0,
  }));
  const sellMarkers = result.sell_signals.map(s => ({
    name: '卖出', coord: [s.date, s.price],
    itemStyle: { color: '#16a34a' },
    label: { show: true, formatter: '卖\n' + s.price, position: 'top', fontSize: 10, color: '#16a34a', fontWeight: 'bold' },
    symbol: 'triangle', symbolSize: 14, symbolRotate: 180,
  }));

  // --- 图1: 股价 + 通道 + 信号 ---
  if (chartInstances.chart1) chartInstances.chart1.dispose();
  chartInstances.chart1 = echarts.init(document.getElementById('chart1'));
  chartInstances.chart1.setOption({
    backgroundColor: '#fff',
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' }, backgroundColor: 'rgba(15,23,42,0.9)', borderColor: '#334155', textStyle: { color: '#fff', fontSize: 12 } },
    legend: { top: 5, textStyle: { fontSize: 12 } },
    grid: { left: 60, right: 30, top: 50, bottom: 60 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10 }, axisLine: { lineStyle: { color: '#cbd5e1' } } },
    yAxis: { type: 'value', scale: true, name: '价格(元)', axisLabel: { fontSize: 11 }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
    dataZoom: [ { type: 'inside', start: 0, end: 100 }, { type: 'slider', bottom: 10, height: 20, start: 0, end: 100 } ],
    series: [
      { name: '收盘价', type: 'line', data: cd.close, smooth: false, symbol: 'none', lineStyle: { width: 1.5, color: '#2563eb' }, itemStyle: { color: '#2563eb' }, z: 3 },
      { name: '入场通道上轨(' + params.entry_channel + '日)', type: 'line', data: cd.upper_channel, smooth: false, symbol: 'none', lineStyle: { width: 1, color: '#dc2626', type: 'dashed' }, itemStyle: { color: '#dc2626' }, z: 2 },
      { name: '出场通道下轨(' + params.exit_channel + '日)', type: 'line', data: cd.lower_channel_exit, smooth: false, symbol: 'none', lineStyle: { width: 1, color: '#16a34a', type: 'dashed' }, itemStyle: { color: '#16a34a' }, z: 2 },
    ],
    markPoint: { data: [...buyMarkers, ...sellMarkers] },
  });

  // --- 图2: ATR ---
  if (chartInstances.chart2) chartInstances.chart2.dispose();
  chartInstances.chart2 = echarts.init(document.getElementById('chart2'));
  chartInstances.chart2.setOption({
    backgroundColor: '#fff',
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(15,23,42,0.9)', borderColor: '#334155', textStyle: { color: '#fff' } },
    legend: { top: 5, textStyle: { fontSize: 12 } },
    grid: { left: 60, right: 60, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10 }, axisLine: { lineStyle: { color: '#cbd5e1' } } },
    yAxis: [
      { type: 'value', name: 'ATR', position: 'left', axisLabel: { fontSize: 11 }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
      { type: 'value', name: 'ATR%', position: 'right', axisLabel: { fontSize: 11, formatter: '{value}%' }, splitLine: { show: false } },
    ],
    series: [
      { name: 'ATR(' + params.atr_period + '日)', type: 'line', data: cd.atr, yAxisIndex: 0, symbol: 'none', lineStyle: { width: 1.5, color: '#f97316' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(249,115,22,0.25)' }, { offset: 1, color: 'rgba(249,115,22,0.02)' }]) } },
      { name: 'ATR百分比', type: 'line', data: cd.atr_pct, yAxisIndex: 1, symbol: 'none', lineStyle: { width: 1, color: '#8b5cf6', type: 'dotted' } },
    ],
  });

  // --- 图3: 净值对比 ---
  if (chartInstances.chart3) chartInstances.chart3.dispose();
  chartInstances.chart3 = echarts.init(document.getElementById('chart3'));
  chartInstances.chart3.setOption({
    backgroundColor: '#fff',
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(15,23,42,0.9)', borderColor: '#334155', textStyle: { color: '#fff' } },
    legend: { top: 5, textStyle: { fontSize: 12 } },
    grid: { left: 60, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10 }, axisLine: { lineStyle: { color: '#cbd5e1' } } },
    yAxis: { type: 'value', name: '净值(¥)', scale: true, axisLabel: { fontSize: 11 }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
    series: [
      { name: '海龟策略净值', type: 'line', data: cd.strategy_nav, symbol: 'none', lineStyle: { width: 2, color: '#dc2626' }, itemStyle: { color: '#dc2626' } },
      { name: '买入持有净值', type: 'line', data: cd.benchmark_nav, symbol: 'none', lineStyle: { width: 2, color: '#2563eb' }, itemStyle: { color: '#2563eb' }, z: 1 },
    ],
  });

  // --- 图4: 累计回报 ---
  if (chartInstances.chart4) chartInstances.chart4.dispose();
  chartInstances.chart4 = echarts.init(document.getElementById('chart4'));
  chartInstances.chart4.setOption({
    backgroundColor: '#fff',
    tooltip: { trigger: 'axis', valueFormatter: v => v.toFixed(2) + '%', backgroundColor: 'rgba(15,23,42,0.9)', borderColor: '#334155', textStyle: { color: '#fff' } },
    legend: { top: 5, textStyle: { fontSize: 12 } },
    grid: { left: 60, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10 }, axisLine: { lineStyle: { color: '#cbd5e1' } } },
    yAxis: { type: 'value', name: '累计回报(%)', axisLabel: { fontSize: 11, formatter: '{value}%' }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
    series: [
      { name: '策略累计回报', type: 'line', data: cd.strategy_cum_return, symbol: 'none', lineStyle: { width: 2, color: '#dc2626' }, areaStyle: { color: 'rgba(220,38,38,0.05)' } },
      { name: '基准累计回报', type: 'line', data: cd.benchmark_cum_return, symbol: 'none', lineStyle: { width: 2, color: '#2563eb' }, areaStyle: { color: 'rgba(37,99,235,0.05)' } },
    ],
  });

  // --- 图5: 回撤 ---
  if (chartInstances.chart5) chartInstances.chart5.dispose();
  chartInstances.chart5 = echarts.init(document.getElementById('chart5'));
  chartInstances.chart5.setOption({
    backgroundColor: '#fff',
    tooltip: { trigger: 'axis', valueFormatter: v => v.toFixed(2) + '%', backgroundColor: 'rgba(15,23,42,0.9)', borderColor: '#334155', textStyle: { color: '#fff' } },
    legend: { top: 5, textStyle: { fontSize: 12 } },
    grid: { left: 60, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10 }, axisLine: { lineStyle: { color: '#cbd5e1' } } },
    yAxis: { type: 'value', name: '回撤(%)', max: 0, axisLabel: { fontSize: 11, formatter: '{value}%' }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
    series: [
      { name: '策略回撤', type: 'line', data: cd.drawdown, symbol: 'none', lineStyle: { width: 1.5, color: '#dc2626' }, areaStyle: { color: 'rgba(220,38,38,0.15)' } },
      { name: '基准回撤', type: 'line', data: cd.benchmark_drawdown, symbol: 'none', lineStyle: { width: 1.5, color: '#2563eb' }, areaStyle: { color: 'rgba(37,99,235,0.1)' } },
    ],
  });

  // --- 图6: 持仓状态 ---
  const positionData = cd.position.map((p, i) => p === 1 ? cd.close[i] : null);
  if (chartInstances.chart6) chartInstances.chart6.dispose();
  chartInstances.chart6 = echarts.init(document.getElementById('chart6'));
  chartInstances.chart6.setOption({
    backgroundColor: '#fff',
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(15,23,42,0.9)', borderColor: '#334155', textStyle: { color: '#fff' } },
    legend: { top: 5, textStyle: { fontSize: 12 } },
    grid: { left: 60, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10 }, axisLine: { lineStyle: { color: '#cbd5e1' } } },
    yAxis: { type: 'value', name: '价格(元)', scale: true, axisLabel: { fontSize: 11 }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
    series: [
      { name: '收盘价', type: 'line', data: cd.close, symbol: 'none', lineStyle: { width: 1.5, color: '#2563eb' } },
      { name: '持仓区间', type: 'line', data: positionData, symbol: 'none', lineStyle: { width: 0 }, areaStyle: { color: 'rgba(220,38,38,0.15)', opacity: 0.5 }, stack: 'position' },
      { name: '入场通道(' + params.entry_channel + '日)', type: 'line', data: cd.upper_channel, symbol: 'none', lineStyle: { width: 1, color: '#dc2626', type: 'dashed' } },
      { name: '出场通道(' + params.exit_channel + '日)', type: 'line', data: cd.lower_channel_exit, symbol: 'none', lineStyle: { width: 1, color: '#16a34a', type: 'dashed' } },
    ],
  });

  // --- 交易记录表 ---
  const tagClass = { 'SELL': 'tag-sell', 'STOP_LOSS': 'tag-stop', 'BUY': 'tag-buy', 'ADD_UNIT': 'tag-add' };
  const tagLabel = { 'SELL': '卖出', 'STOP_LOSS': '止损', 'BUY': '买入', 'ADD_UNIT': '加仓' };
  document.getElementById('tradeTableBody').innerHTML = result.trade_details.map((t, i) => `
    <tr>
      <td>${i + 1}</td>
      <td>${t.buy_date}</td>
      <td>${t.buy_price.toFixed(2)}</td>
      <td>${t.sell_date}</td>
      <td>${t.sell_price.toFixed(2)}</td>
      <td>${t.shares.toLocaleString()}</td>
      <td style="color: ${t.pnl >= 0 ? '#16a34a' : '#dc2626'}; font-weight: 600;">${t.pnl >= 0 ? '+' : ''}${t.pnl.toFixed(2)}</td>
      <td style="color: ${t.return_pct >= 0 ? '#16a34a' : '#dc2626'};">${t.return_pct >= 0 ? '+' : ''}${t.return_pct.toFixed(2)}%</td>
      <td><span class="tag ${tagClass[t.exit_type]}">${tagLabel[t.exit_type] || t.exit_type}</span></td>
    </tr>
  `).join('');

  // --- 买入信号表 ---
  document.getElementById('buySignalsBody').innerHTML = result.buy_signals.map(s => `
    <tr>
      <td>${s.date}</td>
      <td style="color: #dc2626; font-weight: 600;">${s.price.toFixed(2)}</td>
      <td>${s.upper_channel.toFixed(2)}</td>
      <td>${s.atr.toFixed(3)}</td>
    </tr>
  `).join('');

  // --- 卖出信号表 ---
  document.getElementById('sellSignalsBody').innerHTML = result.sell_signals.map(s => `
    <tr>
      <td>${s.date}</td>
      <td style="color: #16a34a; font-weight: 600;">${s.price.toFixed(2)}</td>
      <td>${s.lower_channel_exit.toFixed(2)}</td>
      <td>${s.atr.toFixed(3)}</td>
    </tr>
  `).join('');
}

// ===== 运行回测 =====
function runBacktest() {
  if (!currentData) return;
  showLoading('正在运行海龟策略回测...');
  // 使用 setTimeout 让 UI 更新
  setTimeout(() => {
    try {
      const params = getCurrentParams();
      const result = runTurtleStrategy(currentData, params);
      renderDashboard(result);
      hideLoading();
    } catch (err) {
      hideLoading();
      showToast('回测出错: ' + err.message);
      console.error(err);
    }
  }, 50);
}

// ===== 响应式 =====
window.addEventListener('resize', () => {
  for (const key in chartInstances) {
    if (chartInstances[key]) chartInstances[key].resize();
  }
});

// ===== 初始化 =====
setupParamSliders();
renderStockList();

// 默认加载第一只股票
const firstCode = Object.keys(STOCKS_DATA)[0];
if (firstCode) {
  switchStock(firstCode);
}
</script>

</body>
</html>
'''

output_path = OUTPUT_DIR / "turtle_strategy_dashboard_v2.html"
output_path.write_text(html, encoding="utf-8")
print(f"\nHTML 看板已生成: {output_path}")
print(f"文件大小: {output_path.stat().st_size / 1024:.1f} KB")
