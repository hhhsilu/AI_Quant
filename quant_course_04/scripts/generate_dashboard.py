#!/usr/bin/env python3
"""
生成海龟策略可视化看板 HTML
读取回测数据和指标，生成自包含的 HTML 看板（使用 ECharts）
"""

import json
from pathlib import Path

OUTPUT_DIR = Path("../output")
DASHBOARD_DIR = Path("../dashboard")

# 读取数据
with (OUTPUT_DIR / "turtle_chart_data.json").open("r", encoding="utf-8") as f:
    chart_data = json.load(f)
with (OUTPUT_DIR / "shitou_600539_turtle_metrics.json").open("r", encoding="utf-8") as f:
    metrics_data = json.load(f)

# 将数据嵌入 HTML
chart_data_json = json.dumps(chart_data, ensure_ascii=False)
metrics_json = json.dumps(metrics_data, ensure_ascii=False)

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>海龟交易策略回测看板 - 狮头股份 600539.SH</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: "PingFang SC", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
    background: #f0f2f5; color: #1a1a2e; line-height: 1.6;
  }}

  /* ===== Header ===== */
  .header {{
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #2563eb 100%);
    color: #fff; padding: 28px 32px; position: relative; overflow: hidden;
  }}
  .header::after {{
    content: ""; position: absolute; right: -50px; top: -50px;
    width: 300px; height: 300px; border-radius: 50%;
    background: rgba(255,255,255,0.03);
  }}
  .header h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 6px; }}
  .header .subtitle {{ font-size: 14px; opacity: 0.85; }}
  .header .meta-row {{
    display: flex; gap: 24px; margin-top: 14px; flex-wrap: wrap;
  }}
  .header .meta-item {{
    background: rgba(255,255,255,0.1); padding: 4px 14px;
    border-radius: 20px; font-size: 12px;
  }}
  .header .meta-item strong {{ font-weight: 600; }}

  /* ===== Layout ===== */
  .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}

  /* ===== Metric Cards ===== */
  .metrics-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 14px; margin-bottom: 20px;
  }}
  .metric-card {{
    background: #fff; border-radius: 12px; padding: 18px 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-left: 4px solid #2563eb;
    transition: transform 0.2s, box-shadow 0.2s;
  }}
  .metric-card:hover {{
    transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.1);
  }}
  .metric-card .label {{ font-size: 12px; color: #64748b; margin-bottom: 6px; }}
  .metric-card .value {{ font-size: 24px; font-weight: 700; color: #1e293b; }}
  .metric-card .sub {{ font-size: 11px; color: #94a3b8; margin-top: 4px; }}
  .metric-card.positive {{ border-left-color: #16a34a; }}
  .metric-card.positive .value {{ color: #16a34a; }}
  .metric-card.negative {{ border-left-color: #dc2626; }}
  .metric-card.negative .value {{ color: #dc2626; }}
  .metric-card.warning {{ border-left-color: #f59e0b; }}
  .metric-card.warning .value {{ color: #d97706; }}

  /* ===== Chart Cards ===== */
  .chart-card {{
    background: #fff; border-radius: 12px; padding: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 20px;
  }}
  .chart-card .chart-title {{
    font-size: 15px; font-weight: 600; color: #1e3a5f;
    margin-bottom: 4px; display: flex; align-items: center; gap: 8px;
  }}
  .chart-card .chart-title .icon {{
    width: 4px; height: 18px; background: #2563eb; border-radius: 2px;
  }}
  .chart-card .chart-desc {{
    font-size: 12px; color: #94a3b8; margin-bottom: 12px;
  }}
  .chart-container {{ width: 100%; }}

  /* ===== Two Column ===== */
  .two-col {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;
  }}
  @media (max-width: 900px) {{ .two-col {{ grid-template-columns: 1fr; }} }}

  /* ===== Table ===== */
  .table-card {{
    background: #fff; border-radius: 12px; padding: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 20px;
  }}
  .table-card .table-title {{
    font-size: 15px; font-weight: 600; color: #1e3a5f; margin-bottom: 14px;
    display: flex; align-items: center; gap: 8px;
  }}
  .table-card .table-title .icon {{
    width: 4px; height: 18px; background: #2563eb; border-radius: 2px;
  }}
  table {{
    width: 100%; border-collapse: collapse; font-size: 13px;
  }}
  th {{
    background: #f8fafc; padding: 10px 14px; text-align: left;
    font-weight: 600; color: #475569; border-bottom: 2px solid #e2e8f0;
    white-space: nowrap;
  }}
  td {{
    padding: 9px 14px; border-bottom: 1px solid #f1f5f9; color: #334155;
  }}
  tr:hover td {{ background: #f8fafc; }}
  .tag {{
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 11px; font-weight: 600;
  }}
  .tag-buy {{ background: #fee2e2; color: #dc2626; }}
  .tag-sell {{ background: #dcfce7; color: #16a34a; }}
  .tag-stop {{ background: #fef3c7; color: #d97706; }}
  .tag-add {{ background: #e0e7ff; color: #4f46e5; }}

  /* ===== Strategy Info ===== */
  .info-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px; margin-bottom: 20px;
  }}
  .info-item {{
    background: #fff; border-radius: 8px; padding: 12px 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  }}
  .info-item .label {{ font-size: 11px; color: #94a3b8; margin-bottom: 2px; }}
  .info-item .value {{ font-size: 14px; font-weight: 600; color: #334155; }}

  /* ===== Footer ===== */
  .footer {{
    text-align: center; padding: 20px; font-size: 12px; color: #94a3b8;
  }}
</style>
</head>
<body>

<div class="header">
  <h1>海龟交易策略回测看板</h1>
  <div class="subtitle">狮头股份 (600539.SH) | 前复权日线 | 2025-07-04 ~ 2026-07-03</div>
  <div class="meta-row">
    <div class="meta-item">策略类型: <strong>海龟交易法 (Turtle Trading)</strong></div>
    <div class="meta-item">入场通道: <strong>20日唐奇安上轨突破</strong></div>
    <div class="meta-item">出场通道: <strong>10日唐奇安下轨突破</strong></div>
    <div class="meta-item">ATR周期: <strong>20日</strong></div>
    <div class="meta-item">止损: <strong>2×ATR</strong></div>
    <div class="meta-item">仓位风险: <strong>1%/单位</strong></div>
  </div>
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
    <div class="chart-desc">收盘价走势与20日入场通道上轨、10日出场通道下轨，红色三角为买入信号，绿色三角为卖出信号</div>
    <div id="chart1" class="chart-container" style="height: 450px;"></div>
  </div>

  <!-- ===== 图2: ATR ===== -->
  <div class="chart-card">
    <div class="chart-title"><span class="icon"></span>ATR (Average True Range) 走势</div>
    <div class="chart-desc">20日ATR数值与ATR百分比（占收盘价比例），反映市场波动率</div>
    <div id="chart2" class="chart-container" style="height: 300px;"></div>
  </div>

  <!-- ===== 图3 + 图4: 净值对比 & 累计回报 ===== -->
  <div class="two-col">
    <div class="chart-card">
      <div class="chart-title"><span class="icon"></span>策略净值 vs 买入持有基准</div>
      <div class="chart-desc">海龟策略净值曲线与买入持有净值对比</div>
      <div id="chart3" class="chart-container" style="height: 320px;"></div>
    </div>
    <div class="chart-card">
      <div class="chart-title"><span class="icon"></span>累计回报对比</div>
      <div class="chart-desc">策略与基准的累计回报率(%)走势</div>
      <div id="chart4" class="chart-container" style="height: 320px;"></div>
    </div>
  </div>

  <!-- ===== 图5: 回撤曲线 ===== -->
  <div class="chart-card">
    <div class="chart-title"><span class="icon"></span>最大回撤对比 (Drawdown)</div>
    <div class="chart-desc">策略与基准的回撤曲线对比，反映策略的风险控制能力</div>
    <div id="chart5" class="chart-container" style="height: 300px;"></div>
  </div>

  <!-- ===== 图6: 持仓状态 ===== -->
  <div class="chart-card">
    <div class="chart-title"><span class="icon"></span>持仓状态与通道区间</div>
    <div class="chart-desc">持仓区间（红色背景）与唐奇安通道上下轨，展示策略的持仓时机</div>
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
  海龟交易策略回测看板 | 数据来源: Tushare (前复权日线) | 本报告仅供学习研究，不构成投资建议
</div>

<script>
// ===== 数据 =====
const chartData = {chart_data_json};
const metricsData = {metrics_json};
const m = metricsData.metrics;
const meta = metricsData.metadata;
const params = meta.params;

// ===== 格式化日期 =====
function fmtDate(d) {{
  if (d.length === 8) return d.substring(0,4) + '-' + d.substring(4,6) + '-' + d.substring(6,8);
  return d;
}}

// ===== 生成指标卡片 =====
const metricsHTML = [
  {{ label: '累计回报 (Cumulative Return)', value: m.total_return_pct.toFixed(2) + '%', sub: '基准: ' + m.benchmark_total_return_pct.toFixed(2) + '%', cls: m.total_return_pct >= 0 ? 'positive' : 'negative' }},
  {{ label: '最大回撤 (MDD)', value: m.max_drawdown_pct.toFixed(2) + '%', sub: '基准: ' + m.benchmark_max_drawdown_pct.toFixed(2) + '%', cls: m.max_drawdown_pct >= -15 ? 'warning' : 'negative' }},
  {{ label: '夏普比率 (Sharpe Ratio)', value: m.sharpe_ratio.toFixed(2), sub: '基准: ' + m.benchmark_sharpe_ratio.toFixed(2), cls: m.sharpe_ratio >= 1 ? 'positive' : 'warning' }},
  {{ label: '期末总资产', value: '¥' + m.final_value.toLocaleString('zh-CN', {{maximumFractionDigits: 0}}), sub: '初始: ¥' + meta.initial_capital.toLocaleString('zh-CN'), cls: m.net_profit >= 0 ? 'positive' : 'negative' }},
  {{ label: '净利润', value: (m.net_profit >= 0 ? '+' : '') + '¥' + m.net_profit.toLocaleString('zh-CN', {{maximumFractionDigits: 0}}), sub: '基准超额: ' + m.excess_return_pct.toFixed(2) + '%', cls: m.net_profit >= 0 ? 'positive' : 'negative' }},
  {{ label: '年化收益率', value: m.annualized_return_pct.toFixed(2) + '%', sub: '基准: ' + m.benchmark_annualized_return_pct.toFixed(2) + '%', cls: m.annualized_return_pct >= 0 ? 'positive' : 'negative' }},
  {{ label: '索提诺比率 (Sortino)', value: m.sortino_ratio.toFixed(2), sub: '只计下行风险', cls: m.sortino_ratio >= 1 ? 'positive' : 'warning' }},
  {{ label: '卡玛比率 (Calmar)', value: m.calmar_ratio.toFixed(2), sub: '年化收益/|最大回撤|', cls: m.calmar_ratio >= 1 ? 'positive' : 'warning' }},
  {{ label: '胜率', value: m.win_rate_pct.toFixed(0) + '%', sub: m.completed_round_trips + ' 轮完整交易', cls: m.win_rate_pct >= 50 ? 'positive' : 'negative' }},
  {{ label: '盈亏比', value: m.profit_factor !== null ? m.profit_factor.toFixed(2) : 'N/A', sub: '总盈利/总亏损', cls: m.profit_factor >= 1 ? 'positive' : 'negative' }},
  {{ label: '总交易次数', value: m.total_trades + ' 次', sub: '止损: ' + m.stop_loss_count + ' | 加仓: ' + m.add_unit_count, cls: '' }},
  {{ label: '平均每笔盈亏', value: '¥' + m.avg_pnl_per_trade.toFixed(0), sub: '最大盈利: ¥' + m.max_profit.toFixed(0) + ' | 最大亏损: ¥' + m.max_loss.toFixed(0), cls: m.avg_pnl_per_trade >= 0 ? 'positive' : 'negative' }},
];

document.getElementById('metricsGrid').innerHTML = metricsHTML.map(item => `
  <div class="metric-card ${{item.cls}}">
    <div class="label">${{item.label}}</div>
    <div class="value">${{item.value}}</div>
    <div class="sub">${{item.sub}}</div>
  </div>
`).join('');

// ===== 生成参数卡片 =====
const paramsHTML = [
  {{ label: '入场通道周期', value: params.entry_channel + ' 日' }},
  {{ label: '出场通道周期', value: params.exit_channel + ' 日' }},
  {{ label: 'ATR计算周期', value: params.atr_period + ' 日' }},
  {{ label: '每单位风险比例', value: (params.risk_per_unit * 100) + '%' }},
  {{ label: '止损倍数', value: params.stop_loss_atr + ' × ATR' }},
  {{ label: '最大加仓单位', value: params.max_units + ' 个' }},
  {{ label: '加仓间隔', value: params.add_unit_atr + ' × ATR' }},
  {{ label: '初始资金', value: '¥' + meta.initial_capital.toLocaleString('zh-CN') }},
  {{ label: '佣金费率', value: (meta.commission_rate * 10000).toFixed(1) + '‱' }},
  {{ label: '印花税', value: (meta.stamp_tax_rate * 1000).toFixed(1) + '‰' }},
  {{ label: '滑点', value: (meta.slippage * 100).toFixed(1) + '%' }},
  {{ label: '交易日数', value: meta.trading_days + ' 天' }},
];
document.getElementById('paramGrid').innerHTML = paramsHTML.map(item => `
  <div class="info-item">
    <div class="label">${{item.label}}</div>
    <div class="value">${{item.value}}</div>
  </div>
`).join('');

// ===== 日期格式转换 =====
const dates = chartData.dates.map(fmtDate);

// ===== 买卖信号标记 =====
const buyMarkers = metricsData.buy_signals.map(s => ({{
  name: '买入',
  coord: [s.date, s.price],
  itemStyle: {{ color: '#dc2626' }},
  label: {{ show: true, formatter: '买\\n' + s.price, position: 'bottom', fontSize: 10, color: '#dc2626', fontWeight: 'bold' }},
  symbol: 'triangle', symbolSize: 14, symbolRotate: 0,
}}));
const sellMarkers = metricsData.sell_signals.map(s => ({{
  name: '卖出',
  coord: [s.date, s.price],
  itemStyle: {{ color: '#16a34a' }},
  label: {{ show: true, formatter: '卖\\n' + s.price, position: 'top', fontSize: 10, color: '#16a34a', fontWeight: 'bold' }},
  symbol: 'triangle', symbolSize: 14, symbolRotate: 180,
}}));

// ===== 图1: 股价 + 通道 + 信号 =====
const chart1 = echarts.init(document.getElementById('chart1'));
chart1.setOption({{
  backgroundColor: '#fff',
  tooltip: {{
    trigger: 'axis', axisPointer: {{ type: 'cross' }},
    backgroundColor: 'rgba(15,23,42,0.9)', borderColor: '#334155',
    textStyle: {{ color: '#fff', fontSize: 12 }},
  }},
  legend: {{ top: 5, textStyle: {{ fontSize: 12 }} }},
  grid: {{ left: 60, right: 30, top: 50, bottom: 60 }},
  xAxis: {{ type: 'category', data: dates, axisLabel: {{ fontSize: 10, rotate: 0 }},
    axisLine: {{ lineStyle: {{ color: '#cbd5e1' }} }} }},
  yAxis: {{ type: 'value', scale: true, name: '价格(元)',
    axisLabel: {{ fontSize: 11 }}, splitLine: {{ lineStyle: {{ color: '#f1f5f9' }} }} }},
  dataZoom: [
    {{ type: 'inside', start: 0, end: 100 }},
    {{ type: 'slider', bottom: 10, height: 20, start: 0, end: 100 }},
  ],
  series: [
    {{
      name: '收盘价', type: 'line', data: chartData.close,
      smooth: false, symbol: 'none', lineStyle: {{ width: 1.5, color: '#2563eb' }},
      itemStyle: {{ color: '#2563eb' }}, z: 3,
    }},
    {{
      name: '入场通道上轨(20日)', type: 'line', data: chartData.upper_channel,
      smooth: false, symbol: 'none', lineStyle: {{ width: 1, color: '#dc2626', type: 'dashed' }},
      itemStyle: {{ color: '#dc2626' }}, z: 2,
    }},
    {{
      name: '出场通道下轨(10日)', type: 'line', data: chartData.lower_channel_exit,
      smooth: false, symbol: 'none', lineStyle: {{ width: 1, color: '#16a34a', type: 'dashed' }},
      itemStyle: {{ color: '#16a34a' }}, z: 2,
    }},
  ],
  markPoint: {{ data: [...buyMarkers, ...sellMarkers] }},
}});

// ===== 图2: ATR =====
const chart2 = echarts.init(document.getElementById('chart2'));
chart2.setOption({{
  backgroundColor: '#fff',
  tooltip: {{ trigger: 'axis', backgroundColor: 'rgba(15,23,42,0.9)', borderColor: '#334155', textStyle: {{ color: '#fff' }} }},
  legend: {{ top: 5, textStyle: {{ fontSize: 12 }} }},
  grid: {{ left: 60, right: 60, top: 40, bottom: 30 }},
  xAxis: {{ type: 'category', data: dates, axisLabel: {{ fontSize: 10 }},
    axisLine: {{ lineStyle: {{ color: '#cbd5e1' }} }} }},
  yAxis: [
    {{ type: 'value', name: 'ATR', position: 'left', axisLabel: {{ fontSize: 11 }},
      splitLine: {{ lineStyle: {{ color: '#f1f5f9' }} }} }},
    {{ type: 'value', name: 'ATR%', position: 'right', axisLabel: {{ fontSize: 11, formatter: '{{value}}%' }},
      splitLine: {{ show: false }} }},
  ],
  series: [
    {{
      name: 'ATR(20日)', type: 'line', data: chartData.atr, yAxisIndex: 0,
      symbol: 'none', lineStyle: {{ width: 1.5, color: '#f97316' }},
      areaStyle: {{ color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        {{ offset: 0, color: 'rgba(249,115,22,0.25)' }},
        {{ offset: 1, color: 'rgba(249,115,22,0.02)' }},
      ]) }},
    }},
    {{
      name: 'ATR百分比', type: 'line', data: chartData.atr_pct, yAxisIndex: 1,
      symbol: 'none', lineStyle: {{ width: 1, color: '#8b5cf6', type: 'dotted' }},
    }},
  ],
}});

// ===== 图3: 净值对比 =====
const chart3 = echarts.init(document.getElementById('chart3'));
chart3.setOption({{
  backgroundColor: '#fff',
  tooltip: {{ trigger: 'axis', backgroundColor: 'rgba(15,23,42,0.9)', borderColor: '#334155', textStyle: {{ color: '#fff' }} }},
  legend: {{ top: 5, textStyle: {{ fontSize: 12 }} }},
  grid: {{ left: 60, right: 20, top: 40, bottom: 30 }},
  xAxis: {{ type: 'category', data: dates, axisLabel: {{ fontSize: 10 }},
    axisLine: {{ lineStyle: {{ color: '#cbd5e1' }} }} }},
  yAxis: {{ type: 'value', name: '净值(¥)', scale: true, axisLabel: {{ fontSize: 11 }},
    splitLine: {{ lineStyle: {{ color: '#f1f5f9' }} }} }},
  series: [
    {{
      name: '海龟策略净值', type: 'line', data: chartData.strategy_nav,
      symbol: 'none', lineStyle: {{ width: 2, color: '#dc2626' }},
      itemStyle: {{ color: '#dc2626' }},
    }},
    {{
      name: '买入持有净值', type: 'line', data: chartData.benchmark_nav,
      symbol: 'none', lineStyle: {{ width: 2, color: '#2563eb' }},
      itemStyle: {{ color: '#2563eb' }}, z: 1,
    }},
  ],
}});

// ===== 图4: 累计回报 =====
const chart4 = echarts.init(document.getElementById('chart4'));
chart4.setOption({{
  backgroundColor: '#fff',
  tooltip: {{ trigger: 'axis', valueFormatter: v => v.toFixed(2) + '%',
    backgroundColor: 'rgba(15,23,42,0.9)', borderColor: '#334155', textStyle: {{ color: '#fff' }} }},
  legend: {{ top: 5, textStyle: {{ fontSize: 12 }} }},
  grid: {{ left: 60, right: 20, top: 40, bottom: 30 }},
  xAxis: {{ type: 'category', data: dates, axisLabel: {{ fontSize: 10 }},
    axisLine: {{ lineStyle: {{ color: '#cbd5e1' }} }} }},
  yAxis: {{ type: 'value', name: '累计回报(%)', axisLabel: {{ fontSize: 11, formatter: '{{value}}%' }},
    splitLine: {{ lineStyle: {{ color: '#f1f5f9' }} }} }},
  series: [
    {{
      name: '策略累计回报', type: 'line', data: chartData.strategy_cum_return,
      symbol: 'none', lineStyle: {{ width: 2, color: '#dc2626' }},
      areaStyle: {{ color: 'rgba(220,38,38,0.05)' }},
    }},
    {{
      name: '基准累计回报', type: 'line', data: chartData.benchmark_cum_return,
      symbol: 'none', lineStyle: {{ width: 2, color: '#2563eb' }},
      areaStyle: {{ color: 'rgba(37,99,235,0.05)' }},
    }},
  ],
}});

// ===== 图5: 回撤 =====
const chart5 = echarts.init(document.getElementById('chart5'));
chart5.setOption({{
  backgroundColor: '#fff',
  tooltip: {{ trigger: 'axis', valueFormatter: v => v.toFixed(2) + '%',
    backgroundColor: 'rgba(15,23,42,0.9)', borderColor: '#334155', textStyle: {{ color: '#fff' }} }},
  legend: {{ top: 5, textStyle: {{ fontSize: 12 }} }},
  grid: {{ left: 60, right: 20, top: 40, bottom: 30 }},
  xAxis: {{ type: 'category', data: dates, axisLabel: {{ fontSize: 10 }},
    axisLine: {{ lineStyle: {{ color: '#cbd5e1' }} }} }},
  yAxis: {{ type: 'value', name: '回撤(%)', max: 0, axisLabel: {{ fontSize: 11, formatter: '{{value}}%' }},
    splitLine: {{ lineStyle: {{ color: '#f1f5f9' }} }} }},
  series: [
    {{
      name: '策略回撤', type: 'line', data: chartData.drawdown,
      symbol: 'none', lineStyle: {{ width: 1.5, color: '#dc2626' }},
      areaStyle: {{ color: 'rgba(220,38,38,0.15)' }},
    }},
    {{
      name: '基准回撤', type: 'line', data: chartData.benchmark_drawdown,
      symbol: 'none', lineStyle: {{ width: 1.5, color: '#2563eb' }},
      areaStyle: {{ color: 'rgba(37,99,235,0.1)' }},
    }},
  ],
}});

// ===== 图6: 持仓状态 =====
// 构建持仓区间数据
const positionData = chartData.position.map((p, i) => p === 1 ? chartData.close[i] : null);
const chart6 = echarts.init(document.getElementById('chart6'));
chart6.setOption({{
  backgroundColor: '#fff',
  tooltip: {{ trigger: 'axis', backgroundColor: 'rgba(15,23,42,0.9)', borderColor: '#334155', textStyle: {{ color: '#fff' }} }},
  legend: {{ top: 5, textStyle: {{ fontSize: 12 }} }},
  grid: {{ left: 60, right: 20, top: 40, bottom: 30 }},
  xAxis: {{ type: 'category', data: dates, axisLabel: {{ fontSize: 10 }},
    axisLine: {{ lineStyle: {{ color: '#cbd5e1' }} }} }},
  yAxis: {{ type: 'value', name: '价格(元)', scale: true, axisLabel: {{ fontSize: 11 }},
    splitLine: {{ lineStyle: {{ color: '#f1f5f9' }} }} }},
  series: [
    {{
      name: '收盘价', type: 'line', data: chartData.close,
      symbol: 'none', lineStyle: {{ width: 1.5, color: '#2563eb' }},
    }},
    {{
      name: '持仓区间', type: 'line', data: positionData,
      symbol: 'none', lineStyle: {{ width: 0 }},
      areaStyle: {{ color: 'rgba(220,38,38,0.15)', opacity: 0.5 }},
      stack: 'position',
    }},
    {{
      name: '入场通道(20日)', type: 'line', data: chartData.upper_channel,
      symbol: 'none', lineStyle: {{ width: 1, color: '#dc2626', type: 'dashed' }},
    }},
    {{
      name: '出场通道(10日)', type: 'line', data: chartData.lower_channel_exit,
      symbol: 'none', lineStyle: {{ width: 1, color: '#16a34a', type: 'dashed' }},
    }},
  ],
}});

// ===== 交易记录表 =====
const tradeDetails = metricsData.trade_details;
const tagClass = {{ 'SELL': 'tag-sell', 'STOP_LOSS': 'tag-stop', 'BUY': 'tag-buy', 'ADD_UNIT': 'tag-add' }};
const tagLabel = {{ 'SELL': '卖出', 'STOP_LOSS': '止损', 'BUY': '买入', 'ADD_UNIT': '加仓' }};
document.getElementById('tradeTableBody').innerHTML = tradeDetails.map((t, i) => `
  <tr>
    <td>${{i + 1}}</td>
    <td>${{t.buy_date}}</td>
    <td>${{t.buy_price.toFixed(2)}}</td>
    <td>${{t.sell_date}}</td>
    <td>${{t.sell_price.toFixed(2)}}</td>
    <td>${{t.shares.toLocaleString()}}</td>
    <td style="color: ${{t.pnl >= 0 ? '#16a34a' : '#dc2626'}}; font-weight: 600;">${{t.pnl >= 0 ? '+' : ''}}${{t.pnl.toFixed(2)}}</td>
    <td style="color: ${{t.return_pct >= 0 ? '#16a34a' : '#dc2626'}};">${{t.return_pct >= 0 ? '+' : ''}}${{t.return_pct.toFixed(2)}}%</td>
    <td><span class="tag ${{tagClass[t.exit_type]}}">${{tagLabel[t.exit_type] || t.exit_type}}</span></td>
  </tr>
`).join('');

// ===== 买入信号表 =====
document.getElementById('buySignalsBody').innerHTML = metricsData.buy_signals.map((s, i) => `
  <tr>
    <td>${{s.date}}</td>
    <td style="color: #dc2626; font-weight: 600;">${{s.price.toFixed(2)}}</td>
    <td>${{s.upper_channel.toFixed(2)}}</td>
    <td>${{s.atr.toFixed(3)}}</td>
  </tr>
`).join('');

// ===== 卖出信号表 =====
document.getElementById('sellSignalsBody').innerHTML = metricsData.sell_signals.map((s, i) => `
  <tr>
    <td>${{s.date}}</td>
    <td style="color: #16a34a; font-weight: 600;">${{s.price.toFixed(2)}}</td>
    <td>${{s.lower_channel_exit.toFixed(2)}}</td>
    <td>${{s.atr.toFixed(3)}}</td>
  </tr>
`).join('');

// ===== 响应式调整 =====
window.addEventListener('resize', () => {{
  [chart1, chart2, chart3, chart4, chart5, chart6].forEach(c => c.resize());
}});
</script>

</body>
</html>
"""

output_path = DASHBOARD_DIR / "turtle_strategy_dashboard.html"
output_path.write_text(html, encoding="utf-8")
print(f"HTML 看板已生成: {output_path}")
print(f"文件大小: {output_path.stat().st_size / 1024:.1f} KB")
