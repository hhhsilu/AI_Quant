#!/usr/bin/env python3
"""
狮头股份 600539.SH 海龟交易策略：信号生成、可视化与回测

海龟策略核心逻辑：
  - 唐奇安通道（Donchian Channel）：
    - 入场通道：20日最高价 → 突破买入
    - 出场通道：10日最低价 → 突破卖出
  - ATR（Average True Range）：用于仓位管理和止损
  - 仓位管理：每单位风险 = 账户资金的 1%
  - 止损：入场价 - 2 × ATR
  - 加仓：每盈利 0.5 × ATR 加一个单位（最多4个单位）
  - 评估指标：最大回撤(MDD)、夏普比率(Sharpe)、累计回报(Cumulative Return)等
"""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ============================================================
# 1. 参数配置
# ============================================================
STOCK_NAME = "狮头股份"
TS_CODE = "600539.SH"
DATA_PATH = Path("../data/shitou_600539_qfq_daily.csv")
META_PATH = Path("../data/shitou_600539_qfq_daily.json")
OUTPUT_DIR = Path("../output")
FIGURE_DIR = OUTPUT_DIR / "figures"
DASHBOARD_DIR = Path("../dashboard")

# 海龟策略参数
ENTRY_CHANNEL = 20     # 入场通道周期（20日唐奇安通道上轨）
EXIT_CHANNEL = 10      # 出场通道周期（10日唐奇安通道下轨）
ATR_PERIOD = 20         # ATR 计算周期
RISK_PER_UNIT = 0.01    # 每单位风险比例（1%）
STOP_LOSS_ATR = 2.0     # 止损倍数（2倍ATR）
MAX_UNITS = 4           # 最大加仓单位数
ADD_UNIT_ATR = 0.5      # 加仓间隔（0.5倍ATR）

# 回测参数
INITIAL_CAPITAL = 100000  # 初始资金（元）
COMMISSION_RATE = 0.0003  # 佣金费率（万分之三）
STAMP_TAX_RATE = 0.0005   # 印花税（卖出时，千分之零点五）
SLIPPAGE = 0.001          # 滑点 0.1%

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)
DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

# matplotlib 中文配置
plt.rcParams["figure.figsize"] = (14, 7)
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.3
plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# ============================================================
# 2. 加载已存储的股价数据
# ============================================================
print("=" * 60)
print("1. 加载股价数据")
print("=" * 60)

df = pd.read_csv(DATA_PATH, dtype={"date": str})
with META_PATH.open("r", encoding="utf-8") as f:
    metadata = json.load(f)["metadata"]

df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
df = df.sort_values("date").reset_index(drop=True)

print(f"  股票: {STOCK_NAME} ({TS_CODE})")
print(f"  数据范围: {df['date'].min().strftime('%Y-%m-%d')} ~ {df['date'].max().strftime('%Y-%m-%d')}")
print(f"  交易日数: {len(df)} 天")
print(f"  复权方式: {metadata.get('adjust')}")
print(f"\n  数据前5行:")
print(df[["date", "open", "high", "low", "close", "volume_hands"]].head().to_string(index=False))
print(f"\n  数据后5行:")
print(df[["date", "open", "high", "low", "close", "volume_hands"]].tail().to_string(index=False))

# ============================================================
# 3. 计算唐奇安高低价格通道
# ============================================================
print("\n" + "=" * 60)
print(f"2. 计算唐奇安通道 (入场:{ENTRY_CHANNEL}日 / 出场:{EXIT_CHANNEL}日)")
print("=" * 60)

# 入场通道上轨：过去N日最高价（不含当日）
df["upper_channel"] = df["high"].rolling(window=ENTRY_CHANNEL).max().shift(1)
# 入场通道下轨：过去N日最低价（不含当日）
df["lower_channel_entry"] = df["low"].rolling(window=ENTRY_CHANNEL).min().shift(1)
# 出场通道下轨：过去M日最低价（不含当日）
df["lower_channel_exit"] = df["low"].rolling(window=EXIT_CHANNEL).min().shift(1)
# 出场通道上轨：过去M日最高价（不含当日，用于参考）
df["upper_channel_exit"] = df["high"].rolling(window=EXIT_CHANNEL).max().shift(1)

print(f"  入场通道上轨: 过去{ENTRY_CHANNEL}日最高价")
print(f"  出场通道下轨: 过去{EXIT_CHANNEL}日最低价")
print(f"\n  通道数据后10行:")
ch_cols = ["date", "close", "high", "low", "upper_channel", "lower_channel_exit"]
print(df[ch_cols].tail(10).to_string(index=False))

# ============================================================
# 4. 计算 ATR（Average True Range）
# ============================================================
print("\n" + "=" * 60)
print(f"3. 计算 ATR (周期: {ATR_PERIOD}日)")
print("=" * 60)

# True Range
df["prev_close"] = df["close"].shift(1)
df["tr1"] = df["high"] - df["low"]
df["tr2"] = (df["high"] - df["prev_close"]).abs()
df["tr3"] = (df["low"] - df["prev_close"]).abs()
df["tr"] = df[["tr1", "tr2", "tr3"]].max(axis=1)

# ATR: 简单移动平均
df["atr"] = df["tr"].rolling(window=ATR_PERIOD).mean()

# ATR 百分比（用于参考）
df["atr_pct"] = df["atr"] / df["close"] * 100

print(f"  TR = max(当日最高-最低, |最高-昨收|, |最低-昨收|)")
print(f"  ATR = {ATR_PERIOD}日TR的简单移动平均")
print(f"\n  ATR 数据后10行:")
atr_cols = ["date", "close", "tr", "atr", "atr_pct"]
print(df[atr_cols].tail(10).to_string(index=False))

# ============================================================
# 5. 计算买入卖出交易信号
# ============================================================
print("\n" + "=" * 60)
print("4. 计算交易信号 (突破买入 / 突破卖出)")
print("=" * 60)

# 买入信号: 收盘价突破入场通道上轨
# 卖出信号: 收盘价跌破出场通道下轨
df["signal"] = 0
df.loc[df["close"] > df["upper_channel"], "signal"] = 1
df.loc[df["close"] < df["lower_channel_exit"], "signal"] = -1

# 去除重复信号：只在状态变化时产生交易
df["position_signal"] = 0
current_state = 0  # 0=空仓, 1=持仓
for i in range(len(df)):
    sig = df.loc[i, "signal"]
    if sig == 1 and current_state == 0:
        df.loc[i, "position_signal"] = 1
        current_state = 1
    elif sig == -1 and current_state == 1:
        df.loc[i, "position_signal"] = -1
        current_state = 0

# 使用 position_signal 作为最终交易信号
df["signal"] = df["position_signal"]

# 持仓状态
df["position"] = 0
current_pos = 0
for i in range(len(df)):
    if df.loc[i, "signal"] == 1:
        current_pos = 1
    elif df.loc[i, "signal"] == -1:
        current_pos = 0
    df.loc[i, "position"] = current_pos

buy_signals = df[df["signal"] == 1]
sell_signals = df[df["signal"] == -1]

print(f"  买入信号（突破{ENTRY_CHANNEL}日高点）: {len(buy_signals)} 次")
for _, row in buy_signals.iterrows():
    print(f"    {row['date'].strftime('%Y-%m-%d')}  收盘价: {row['close']:.2f}  "
          f"通道上轨: {row['upper_channel']:.2f}  ATR: {row['atr']:.2f}")

print(f"\n  卖出信号（跌破{EXIT_CHANNEL}日低点）: {len(sell_signals)} 次")
for _, row in sell_signals.iterrows():
    print(f"    {row['date'].strftime('%Y-%m-%d')}  收盘价: {row['close']:.2f}  "
          f"通道下轨: {row['lower_channel_exit']:.2f}  ATR: {row['atr']:.2f}")

# ============================================================
# 6. 可视化：股价 + 通道 + 交易信号
# ============================================================
print("\n" + "=" * 60)
print("5. 绘制可视化图形")
print("=" * 60)

# --- 图1: 股价 + 唐奇安通道 + 买卖信号 ---
fig, ax = plt.subplots(figsize=(14, 8))

ax.plot(df["date"], df["close"], label="收盘价", color="#2563eb", linewidth=1.5, alpha=0.8)
ax.plot(df["date"], df["upper_channel"], label=f"入场通道上轨 ({ENTRY_CHANNEL}日最高)", color="#dc2626", linewidth=1, alpha=0.7, linestyle="--")
ax.plot(df["date"], df["lower_channel_exit"], label=f"出场通道下轨 ({EXIT_CHANNEL}日最低)", color="#16a34a", linewidth=1, alpha=0.7, linestyle="--")
ax.fill_between(df["date"], df["upper_channel"], df["lower_channel_exit"], alpha=0.05, color="#6366f1")

# 买入信号标记（红色向上三角）
ax.scatter(buy_signals["date"], buy_signals["close"] * 0.985,
           marker="^", color="#dc2626", s=150, zorder=5, label="买入信号（突破上轨）")
for _, row in buy_signals.iterrows():
    ax.annotate(f"买 {row['close']:.2f}",
                xy=(row["date"], row["close"] * 0.985),
                xytext=(0, -20), textcoords="offset points",
                fontsize=9, color="#dc2626", ha="center", fontweight="bold")

# 卖出信号标记（绿色向下三角）
ax.scatter(sell_signals["date"], sell_signals["close"] * 1.015,
           marker="v", color="#16a34a", s=150, zorder=5, label="卖出信号（跌破下轨）")
for _, row in sell_signals.iterrows():
    ax.annotate(f"卖 {row['close']:.2f}",
                xy=(row["date"], row["close"] * 1.015),
                xytext=(0, 15), textcoords="offset points",
                fontsize=9, color="#16a34a", ha="center", fontweight="bold")

ax.set_title(f"{STOCK_NAME} ({TS_CODE}) 股价、唐奇安通道与交易信号", fontsize=14, fontweight="bold")
ax.set_xlabel("日期")
ax.set_ylabel("价格（元）")
ax.legend(loc="upper left", fontsize=10)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
ax.xaxis.set_major_locator(mdates.MonthLocator())
fig.autofmt_xdate(rotation=30)
fig.tight_layout()
fig.savefig(FIGURE_DIR / "01_price_channel_signals.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"  图1已保存: 01_price_channel_signals.png")

# --- 图2: ATR 曲线 ---
fig, axes = plt.subplots(2, 1, sharex=True, figsize=(14, 7), height_ratios=[2, 1])

ax1 = axes[0]
ax1.plot(df["date"], df["close"], label="收盘价", color="#2563eb", linewidth=1.2, alpha=0.8)
ax1.plot(df["date"], df["upper_channel"], label=f"入场通道 ({ENTRY_CHANNEL}日)", color="#dc2626", linewidth=1, alpha=0.5, linestyle="--")
ax1.plot(df["date"], df["lower_channel_exit"], label=f"出场通道 ({EXIT_CHANNEL}日)", color="#16a34a", linewidth=1, alpha=0.5, linestyle="--")
holding = df[df["position"] == 1]
if len(holding) > 0:
    ax1.fill_between(holding["date"], ax1.get_ylim()[0], holding["close"],
                     alpha=0.08, color="#dc2626", label="持仓区间")
ax1.set_ylabel("价格（元）")
ax1.set_title(f"{STOCK_NAME} 海龟策略 - 持仓区间与通道", fontsize=13, fontweight="bold")
ax1.legend(loc="upper left", fontsize=9)

ax2 = axes[1]
ax2.fill_between(df["date"], df["atr"], 0, color="#f97316", alpha=0.3, label="ATR")
ax2.plot(df["date"], df["atr"], color="#f97316", linewidth=1.2, label=f"ATR({ATR_PERIOD})")
ax2.set_title(f"ATR (Average True Range, {ATR_PERIOD}日)", fontsize=12)
ax2.set_ylabel("ATR")
ax2.set_xlabel("日期")
ax2.legend(loc="upper left", fontsize=9)
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
ax2.xaxis.set_major_locator(mdates.MonthLocator())

fig.autofmt_xdate(rotation=30)
fig.tight_layout()
fig.savefig(FIGURE_DIR / "02_atr_position.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"  图2已保存: 02_atr_position.png")

# ============================================================
# 7. 模拟交易回测（海龟策略仓位管理）
# ============================================================
print("\n" + "=" * 60)
print("6. 海龟策略回测与量化指标计算")
print("=" * 60)

trades = []
capital = INITIAL_CAPITAL
cash = INITIAL_CAPITAL
shares = 0
entry_price = 0
stop_loss = 0
units_held = 0
last_add_price = 0
position_open = False

for i in range(len(df) - 1):
    today = df.iloc[i]
    tomorrow = df.iloc[i + 1]
    trade_date = tomorrow["date"]
    trade_price = tomorrow["open"]

    atr_val = today["atr"]
    if pd.isna(atr_val) or atr_val == 0:
        continue

    # 滑点调整
    buy_price = trade_price * (1 + SLIPPAGE)
    sell_price = trade_price * (1 - SLIPPAGE)

    # 检查止损
    if position_open and shares > 0:
        if tomorrow["low"] <= stop_loss:
            # 止损触发
            stop_price = stop_loss * (1 - SLIPPAGE)
            revenue = shares * stop_price
            commission = max(revenue * COMMISSION_RATE, 5)
            stamp_tax = revenue * STAMP_TAX_RATE
            cash += (revenue - commission - stamp_tax)
            trades.append({
                "date": trade_date,
                "action": "STOP_LOSS",
                "price": round(stop_price, 3),
                "shares": shares,
                "amount": round(revenue, 2),
                "commission": round(commission, 2),
                "stamp_tax": round(stamp_tax, 2),
                "cash_after": round(cash, 2),
                "shares_after": 0,
                "atr": round(atr_val, 3),
                "stop_loss_price": round(stop_loss, 3),
                "reason": f"止损触发 (止损价 {stop_loss:.2f})",
            })
            shares = 0
            position_open = False
            units_held = 0
            entry_price = 0
            stop_loss = 0
            continue

        # 检查加仓条件：价格比上次买入/加仓价高 0.5 * ATR
        if units_held < MAX_UNITS and tomorrow["close"] >= last_add_price + ADD_UNIT_ATR * atr_val:
            # 计算新单位仓位
            unit_risk = cash * RISK_PER_UNIT
            unit_shares = int(unit_risk / (STOP_LOSS_ATR * atr_val * 100)) * 100
            if unit_shares > 0 and cash >= unit_shares * buy_price:
                cost = unit_shares * buy_price
                commission = max(cost * COMMISSION_RATE, 5)
                cash -= (cost + commission)
                shares += unit_shares
                last_add_price = buy_price
                # 更新止损价（以最低入场价为基础）
                new_stop = buy_price - STOP_LOSS_ATR * atr_val
                if new_stop > stop_loss:
                    stop_loss = new_stop
                units_held += 1
                trades.append({
                    "date": trade_date,
                    "action": "ADD_UNIT",
                    "price": round(buy_price, 3),
                    "shares": unit_shares,
                    "amount": round(cost, 2),
                    "commission": round(commission, 2),
                    "cash_after": round(cash, 2),
                    "shares_after": shares,
                    "atr": round(atr_val, 3),
                    "stop_loss_price": round(stop_loss, 3),
                    "reason": f"加仓第{units_held}单位 (+{ADD_UNIT_ATR}ATR)",
                })

    # 买入信号
    if today["signal"] == 1 and not position_open:
        unit_risk = cash * RISK_PER_UNIT
        unit_shares = int(unit_risk / (STOP_LOSS_ATR * atr_val * 100)) * 100
        if unit_shares > 0:
            cost = unit_shares * buy_price
            commission = max(cost * COMMISSION_RATE, 5)
            cash -= (cost + commission)
            shares = unit_shares
            entry_price = buy_price
            last_add_price = buy_price
            stop_loss = buy_price - STOP_LOSS_ATR * atr_val
            units_held = 1
            position_open = True
            trades.append({
                "date": trade_date,
                "action": "BUY",
                "price": round(buy_price, 3),
                "shares": unit_shares,
                "amount": round(cost, 2),
                "commission": round(commission, 2),
                "cash_after": round(cash, 2),
                "shares_after": shares,
                "atr": round(atr_val, 3),
                "stop_loss_price": round(stop_loss, 3),
                "reason": f"突破{ENTRY_CHANNEL}日高点买入",
            })

    # 卖出信号
    elif today["signal"] == -1 and position_open and shares > 0:
        revenue = shares * sell_price
        commission = max(revenue * COMMISSION_RATE, 5)
        stamp_tax = revenue * STAMP_TAX_RATE
        cash += (revenue - commission - stamp_tax)
        trades.append({
            "date": trade_date,
            "action": "SELL",
            "price": round(sell_price, 3),
            "shares": shares,
            "amount": round(revenue, 2),
            "commission": round(commission, 2),
            "stamp_tax": round(stamp_tax, 2),
            "cash_after": round(cash, 2),
            "shares_after": 0,
            "atr": round(atr_val, 3),
            "reason": f"跌破{EXIT_CHANNEL}日低点卖出",
        })
        shares = 0
        position_open = False
        units_held = 0
        entry_price = 0
        stop_loss = 0

# 期末持仓按最后收盘价估值
final_close = df.iloc[-1]["close"]
final_value = cash + shares * final_close

# --- 每日策略净值计算 ---
# 策略日收益 = 持仓 * 个股日收益
df["stock_return"] = df["close"].pct_change()
df.loc[df.index[0], "stock_return"] = 0

# 构建持仓时序
position_series = np.zeros(len(df))
holding = False
for i in range(len(df)):
    if df.loc[i, "signal"] == 1:
        holding = True
    elif df.loc[i, "signal"] == -1:
        holding = False
    position_series[i] = 1.0 if holding else 0.0

df["position_flag"] = position_series
df["strategy_return"] = df["position_flag"].shift(1) * df["stock_return"]
df.loc[df.index[0], "strategy_return"] = 0
df["strategy_cum_return"] = (1 + df["strategy_return"]).cumprod() - 1

# 基准收益（买入持有）
df["benchmark_return"] = df["stock_return"]
df["benchmark_cum_return"] = (1 + df["benchmark_return"]).cumprod() - 1

# 策略净值曲线
df["strategy_nav"] = INITIAL_CAPITAL * (1 + df["strategy_cum_return"])
df["benchmark_nav"] = INITIAL_CAPITAL * (1 + df["benchmark_cum_return"])

# --- 量化指标计算 ---
total_return = (final_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
benchmark_total_return = (df.iloc[-1]["close"] - df.iloc[0]["close"]) / df.iloc[0]["close"] * 100
trading_days = len(df)
annualized_return = ((1 + total_return / 100) ** (252 / trading_days) - 1) * 100
benchmark_annualized = ((1 + benchmark_total_return / 100) ** (252 / trading_days) - 1) * 100

# 最大回撤
df["peak"] = df["strategy_nav"].cummax()
df["drawdown"] = (df["strategy_nav"] - df["peak"]) / df["peak"]
max_drawdown = df["drawdown"].min() * 100

# 基准最大回撤
df["benchmark_peak"] = df["benchmark_nav"].cummax()
df["benchmark_drawdown"] = (df["benchmark_nav"] - df["benchmark_peak"]) / df["benchmark_peak"]
benchmark_max_drawdown = df["benchmark_drawdown"].min() * 100

# 夏普比率（年化，无风险利率2%）
risk_free_daily = 0.02 / 252
excess_returns = df["strategy_return"] - risk_free_daily
if excess_returns.std() > 0:
    sharpe_ratio = np.sqrt(252) * excess_returns.mean() / excess_returns.std()
else:
    sharpe_ratio = 0

# 基准夏普比率
bench_excess = df["benchmark_return"] - risk_free_daily
if bench_excess.std() > 0:
    benchmark_sharpe = np.sqrt(252) * bench_excess.mean() / bench_excess.std()
else:
    benchmark_sharpe = 0

# 索提诺比率（Sortino Ratio，只计算下行波动）
downside_returns = excess_returns[excess_returns < 0]
if len(downside_returns) > 0 and downside_returns.std() > 0:
    sortino_ratio = np.sqrt(252) * excess_returns.mean() / downside_returns.std()
else:
    sortino_ratio = 0

# 胜率与交易统计
completed_trades = [t for t in trades if t["action"] in ("SELL", "STOP_LOSS")]
wins = 0
trade_pnl_list = []
trade_details = []

# 配对交易：BUY → SELL/STOP_LOSS
i = 0
while i < len(trades):
    t = trades[i]
    if t["action"] in ("BUY",):
        # 找到对应的卖出
        buy_total_cost = t["amount"] + t["commission"]
        buy_shares = t["shares"]
        buy_date = t["date"]
        buy_price = t["price"]

        # 查找后续加仓
        all_buy_cost = buy_total_cost
        all_buy_shares = buy_shares
        j = i + 1
        while j < len(trades) and trades[j]["action"] == "ADD_UNIT":
            all_buy_cost += trades[j]["amount"] + trades[j]["commission"]
            all_buy_shares += trades[j]["shares"]
            j += 1

        # 找到卖出
        if j < len(trades) and trades[j]["action"] in ("SELL", "STOP_LOSS"):
            sell_trade = trades[j]
            sell_revenue = sell_trade["amount"]
            total_cost = sell_trade.get("commission", 0) + sell_trade.get("stamp_tax", 0)
            pnl = sell_revenue - all_buy_cost - total_cost
            trade_pnl_list.append(pnl)
            trade_details.append({
                "buy_date": buy_date,
                "buy_price": buy_price,
                "sell_date": sell_trade["date"],
                "sell_price": sell_trade["price"],
                "shares": all_buy_shares,
                "pnl": pnl,
                "return_pct": pnl / all_buy_cost * 100,
                "exit_type": sell_trade["action"],
            })
            if pnl > 0:
                wins += 1
            i = j + 1
        else:
            i = j
    else:
        i += 1

total_round_trips = len(trade_pnl_list)
win_rate = wins / total_round_trips * 100 if total_round_trips > 0 else 0
avg_pnl = np.mean(trade_pnl_list) if trade_pnl_list else 0
max_profit = max(trade_pnl_list) if trade_pnl_list else 0
max_loss = min(trade_pnl_list) if trade_pnl_list else 0
profit_factor = (sum(p for p in trade_pnl_list if p > 0) / abs(sum(p for p in trade_pnl_list if p < 0))) if trade_pnl_list and any(p < 0 for p in trade_pnl_list) else float('inf')

# 交易次数
total_trades = len(trades)
buy_count = len([t for t in trades if t["action"] == "BUY"])
sell_count = len([t for t in trades if t["action"] == "SELL"])
stop_loss_count = len([t for t in trades if t["action"] == "STOP_LOSS"])
add_unit_count = len([t for t in trades if t["action"] == "ADD_UNIT"])

# 超额收益
excess_return = total_return - benchmark_total_return

# 卡玛比率 (Calmar Ratio) = 年化收益 / |最大回撤|
calmar_ratio = abs(annualized_return / max_drawdown) if max_drawdown != 0 else 0

print(f"\n  === 回测结果 ===")
print(f"  初始资金:       ¥{INITIAL_CAPITAL:,.0f}")
print(f"  期末总资产:     ¥{final_value:,.2f}")
print(f"  净利润:         ¥{final_value - INITIAL_CAPITAL:,.2f}")
print(f"  总交易次数:     {total_trades} 次 (买入 {buy_count}, 卖出 {sell_count}, 止损 {stop_loss_count}, 加仓 {add_unit_count})")
print(f"  完整交易轮次:   {total_round_trips} 次")
print(f"  胜率:           {win_rate:.1f}% ({wins}/{total_round_trips})")
print(f"  平均每笔盈亏:   ¥{avg_pnl:,.2f}")
print(f"  最大单笔盈利:   ¥{max_profit:,.2f}")
print(f"  最大单笔亏损:   ¥{max_loss:,.2f}")
print(f"  盈亏比:         {profit_factor:.2f}")
print(f"\n  --- 收益指标 ---")
print(f"  策略总收益率:   {total_return:.2f}%")
print(f"  基准总收益率:   {benchmark_total_return:.2f}% (买入持有)")
print(f"  超额收益:       {excess_return:.2f}%")
print(f"  策略年化收益:   {annualized_return:.2f}%")
print(f"  基准年化收益:   {benchmark_annualized:.2f}%")
print(f"\n  --- 风险指标 ---")
print(f"  最大回撤(MDD):  {max_drawdown:.2f}%")
print(f"  基准最大回撤:   {benchmark_max_drawdown:.2f}%")
print(f"  夏普比率:       {sharpe_ratio:.2f}")
print(f"  基准夏普比率:   {benchmark_sharpe:.2f}")
print(f"  索提诺比率:     {sortino_ratio:.2f}")
print(f"  卡玛比率:       {calmar_ratio:.2f}")

# --- 图3: 策略净值 vs 基准净值 ---
fig, ax = plt.subplots(figsize=(14, 7))
ax.plot(df["date"], df["strategy_nav"], label="海龟策略净值", color="#dc2626", linewidth=1.5)
ax.plot(df["date"], df["benchmark_nav"], label="买入持有净值", color="#2563eb", linewidth=1.5, alpha=0.7)
ax.axhline(INITIAL_CAPITAL, color="#64748b", linestyle="--", linewidth=1, label=f"初始资金 ¥{INITIAL_CAPITAL:,.0f}")
ax.set_title(f"{STOCK_NAME} 海龟策略净值 vs 买入持有基准", fontsize=14, fontweight="bold")
ax.set_xlabel("日期")
ax.set_ylabel("净值（元）")
ax.legend(loc="upper left", fontsize=10)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
ax.xaxis.set_major_locator(mdates.MonthLocator())
fig.autofmt_xdate(rotation=30)
fig.tight_layout()
fig.savefig(FIGURE_DIR / "03_nav_comparison.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"\n  图3已保存: 03_nav_comparison.png")

# --- 图4: 回撤曲线 ---
fig, ax = plt.subplots(figsize=(14, 5))
ax.fill_between(df["date"], df["drawdown"] * 100, 0, color="#dc2626", alpha=0.3, label="策略回撤")
ax.fill_between(df["date"], df["benchmark_drawdown"] * 100, 0, color="#2563eb", alpha=0.2, label="基准回撤")
ax.set_title(f"{STOCK_NAME} 最大回撤对比", fontsize=14, fontweight="bold")
ax.set_xlabel("日期")
ax.set_ylabel("回撤 (%)")
ax.legend(loc="lower left", fontsize=10)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
ax.xaxis.set_major_locator(mdates.MonthLocator())
fig.autofmt_xdate(rotation=30)
fig.tight_layout()
fig.savefig(FIGURE_DIR / "04_drawdown.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"  图4已保存: 04_drawdown.png")

# --- 图5: 累计回报对比 ---
fig, ax = plt.subplots(figsize=(14, 6))
ax.plot(df["date"], df["strategy_cum_return"] * 100, label="海龟策略累计回报", color="#dc2626", linewidth=1.5)
ax.plot(df["date"], df["benchmark_cum_return"] * 100, label="买入持有累计回报", color="#2563eb", linewidth=1.5, alpha=0.7)
ax.axhline(0, color="#64748b", linewidth=1)
ax.set_title(f"{STOCK_NAME} 累计回报对比", fontsize=14, fontweight="bold")
ax.set_xlabel("日期")
ax.set_ylabel("累计回报 (%)")
ax.legend(loc="upper left", fontsize=10)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
ax.xaxis.set_major_locator(mdates.MonthLocator())
fig.autofmt_xdate(rotation=30)
fig.tight_layout()
fig.savefig(FIGURE_DIR / "05_cumulative_return.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"  图5已保存: 05_cumulative_return.png")

# ============================================================
# 8. 导出回测结果
# ============================================================
# 交易记录
trades_df = pd.DataFrame(trades)
if len(trades_df) > 0:
    trades_df["date"] = trades_df["date"].dt.strftime("%Y%m%d")
trades_csv = OUTPUT_DIR / "shitou_600539_turtle_trades.csv"
trades_df.to_csv(trades_csv, index=False, encoding="utf-8")

# 完整数据
result = df[["date", "close", "high", "low", "upper_channel", "lower_channel_exit",
             "atr", "atr_pct", "signal", "position",
             "strategy_return", "strategy_cum_return", "strategy_nav",
             "benchmark_return", "benchmark_cum_return", "benchmark_nav",
             "drawdown", "benchmark_drawdown"]].copy()
result["date"] = result["date"].dt.strftime("%Y%m%d")
result_csv = OUTPUT_DIR / "shitou_600539_turtle_backtest.csv"
result.to_csv(result_csv, index=False, encoding="utf-8")

# 汇总指标 JSON
metrics = {
    "metadata": {
        "stock_name": STOCK_NAME,
        "ts_code": TS_CODE,
        "strategy": "海龟交易策略 (Turtle Trading)",
        "data_range": f"{df['date'].min().strftime('%Y-%m-%d')} ~ {df['date'].max().strftime('%Y-%m-%d')}",
        "trading_days": int(trading_days),
        "initial_capital": INITIAL_CAPITAL,
        "commission_rate": COMMISSION_RATE,
        "stamp_tax_rate": STAMP_TAX_RATE,
        "slippage": SLIPPAGE,
        "params": {
            "entry_channel": ENTRY_CHANNEL,
            "exit_channel": EXIT_CHANNEL,
            "atr_period": ATR_PERIOD,
            "risk_per_unit": RISK_PER_UNIT,
            "stop_loss_atr": STOP_LOSS_ATR,
            "max_units": MAX_UNITS,
            "add_unit_atr": ADD_UNIT_ATR,
        },
    },
    "metrics": {
        "final_value": round(final_value, 2),
        "net_profit": round(final_value - INITIAL_CAPITAL, 2),
        "total_return_pct": round(total_return, 2),
        "benchmark_total_return_pct": round(benchmark_total_return, 2),
        "excess_return_pct": round(excess_return, 2),
        "annualized_return_pct": round(annualized_return, 2),
        "benchmark_annualized_return_pct": round(benchmark_annualized, 2),
        "max_drawdown_pct": round(max_drawdown, 2),
        "benchmark_max_drawdown_pct": round(benchmark_max_drawdown, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "benchmark_sharpe_ratio": round(benchmark_sharpe, 2),
        "sortino_ratio": round(sortino_ratio, 2),
        "calmar_ratio": round(calmar_ratio, 2),
        "total_trades": total_trades,
        "completed_round_trips": total_round_trips,
        "win_rate_pct": round(win_rate, 1),
        "avg_pnl_per_trade": round(avg_pnl, 2),
        "max_profit": round(max_profit, 2),
        "max_loss": round(max_loss, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else None,
        "stop_loss_count": stop_loss_count,
        "add_unit_count": add_unit_count,
    },
    "buy_signals": [
        {"date": r["date"].strftime("%Y-%m-%d"), "price": round(r["close"], 2),
         "upper_channel": round(r["upper_channel"], 2), "atr": round(r["atr"], 2)}
        for _, r in buy_signals.iterrows()
    ],
    "sell_signals": [
        {"date": r["date"].strftime("%Y-%m-%d"), "price": round(r["close"], 2),
         "lower_channel_exit": round(r["lower_channel_exit"], 2), "atr": round(r["atr"], 2)}
        for _, r in sell_signals.iterrows()
    ],
    "trade_details": [
        {
            "buy_date": t["buy_date"].strftime("%Y-%m-%d") if hasattr(t["buy_date"], "strftime") else str(t["buy_date"]),
            "buy_price": round(t["buy_price"], 2),
            "sell_date": t["sell_date"].strftime("%Y-%m-%d") if hasattr(t["sell_date"], "strftime") else str(t["sell_date"]),
            "sell_price": round(t["sell_price"], 2),
            "shares": t["shares"],
            "pnl": round(t["pnl"], 2),
            "return_pct": round(t["return_pct"], 2),
            "exit_type": t["exit_type"],
        }
        for t in trade_details
    ],
}
metrics_json = OUTPUT_DIR / "shitou_600539_turtle_metrics.json"
metrics_json.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

# --- 导出图表数据供 HTML 看板使用 ---
chart_data = {
    "dates": result["date"].tolist(),
    "close": result["close"].tolist(),
    "high": result["high"].tolist(),
    "low": result["low"].tolist(),
    "upper_channel": [round(x, 2) if not pd.isna(x) else None for x in result["upper_channel"]],
    "lower_channel_exit": [round(x, 2) if not pd.isna(x) else None for x in result["lower_channel_exit"]],
    "atr": [round(x, 2) if not pd.isna(x) else None for x in result["atr"]],
    "atr_pct": [round(x, 2) if not pd.isna(x) else None for x in result["atr_pct"]],
    "signal": result["signal"].tolist(),
    "position": result["position"].tolist(),
    "strategy_nav": [round(x, 2) for x in result["strategy_nav"]],
    "benchmark_nav": [round(x, 2) for x in result["benchmark_nav"]],
    "strategy_cum_return": [round(x * 100, 2) for x in result["strategy_cum_return"]],
    "benchmark_cum_return": [round(x * 100, 2) for x in result["benchmark_cum_return"]],
    "drawdown": [round(x * 100, 2) for x in result["drawdown"]],
    "benchmark_drawdown": [round(x * 100, 2) for x in result["benchmark_drawdown"]],
}
chart_data_json = OUTPUT_DIR / "turtle_chart_data.json"
chart_data_json.write_text(json.dumps(chart_data, ensure_ascii=False), encoding="utf-8")

print(f"\n" + "=" * 60)
print(f"7. 结果导出完成")
print(f"=" * 60)
print(f"  交易记录: {trades_csv}")
print(f"  回测数据: {result_csv}")
print(f"  指标汇总: {metrics_json}")
print(f"  图表数据: {chart_data_json}")
print(f"  可视化图表: {FIGURE_DIR}/01~05")
print(f"\n  回测完成!")
