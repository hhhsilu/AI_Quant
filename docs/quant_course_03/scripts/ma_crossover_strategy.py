#!/usr/bin/env python3
"""
狮头股份 600539.SH 均线交叉策略：信号生成、可视化与回测

策略逻辑：
  - 短均线（MA5）上穿长均线（MA15）→ 金叉 → 买入信号
  - 短均线（MA5）下穿长均线（MA15）→ 死叉 → 卖出信号
  - 满仓买入 / 清仓卖出，不考虑做空
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
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

# 均线参数
SHORT_WINDOW = 5    # 短均线周期
LONG_WINDOW = 15    # 长均线周期

# 回测参数
INITIAL_CAPITAL = 100000  # 初始资金（元）
COMMISSION_RATE = 0.0003  # 佣金费率（万分之三）
STAMP_TAX_RATE = 0.0005   # 印花税（卖出时，千分之零点五）
SLIPPAGE = 0.001          # 滑点 0.1%

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

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
# 3. 计算短均线和长均线
# ============================================================
print("\n" + "=" * 60)
print(f"2. 计算均线数据 (MA{SHORT_WINDOW} / MA{LONG_WINDOW})")
print("=" * 60)

df[f"ma_{SHORT_WINDOW}"] = df["close"].rolling(window=SHORT_WINDOW).mean()
df[f"ma_{LONG_WINDOW}"] = df["close"].rolling(window=LONG_WINDOW).mean()

print(f"  短均线 MA{SHORT_WINDOW}: {SHORT_WINDOW}日移动平均")
print(f"  长均线 MA{LONG_WINDOW}: {LONG_WINDOW}日移动平均")
print(f"\n  均线数据后10行:")
ma_cols = ["date", "close", f"ma_{SHORT_WINDOW}", f"ma_{LONG_WINDOW}"]
print(df[ma_cols].tail(10).to_string(index=False))

# ============================================================
# 4. 计算买入卖出交易信号
# ============================================================
print("\n" + "=" * 60)
print("3. 计算交易信号 (金叉买入 / 死叉卖出)")
print("=" * 60)

# 金叉: MA_short 由下方穿越到上方
# 死叉: MA_short 由上方穿越到下方
df["ma_diff"] = df[f"ma_{SHORT_WINDOW}"] - df[f"ma_{LONG_WINDOW}"]
df["ma_diff_prev"] = df["ma_diff"].shift(1)

# 信号: 1=买入, -1=卖出, 0=无操作
df["signal"] = 0
golden_cross = (df["ma_diff_prev"] < 0) & (df["ma_diff"] > 0)   # 金叉
death_cross = (df["ma_diff_prev"] > 0) & (df["ma_diff"] < 0)    # 死叉
df.loc[golden_cross, "signal"] = 1
df.loc[death_cross, "signal"] = -1

# 持仓状态: 1=持仓, 0=空仓
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

print(f"  买入信号（金叉）: {len(buy_signals)} 次")
for _, row in buy_signals.iterrows():
    print(f"    {row['date'].strftime('%Y-%m-%d')}  收盘价: {row['close']:.2f}  MA{SHORT_WINDOW}: {row[f'ma_{SHORT_WINDOW}']:.2f}  MA{LONG_WINDOW}: {row[f'ma_{LONG_WINDOW}']:.2f}")

print(f"\n  卖出信号（死叉）: {len(sell_signals)} 次")
for _, row in sell_signals.iterrows():
    print(f"    {row['date'].strftime('%Y-%m-%d')}  收盘价: {row['close']:.2f}  MA{SHORT_WINDOW}: {row[f'ma_{SHORT_WINDOW}']:.2f}  MA{LONG_WINDOW}: {row[f'ma_{LONG_WINDOW}']:.2f}")

# ============================================================
# 5. 可视化：股价 + 均线 + 交易信号
# ============================================================
print("\n" + "=" * 60)
print("4. 绘制可视化图形")
print("=" * 60)

# --- 图1: 股价 + 短长均线 + 买卖信号 ---
fig, ax = plt.subplots(figsize=(14, 8))

ax.plot(df["date"], df["close"], label="收盘价", color="#2563eb", linewidth=1.5, alpha=0.8)
ax.plot(df["date"], df[f"ma_{SHORT_WINDOW}"], label=f"MA{SHORT_WINDOW}（短均线）", color="#f97316", linewidth=1.2, alpha=0.9)
ax.plot(df["date"], df[f"ma_{LONG_WINDOW}"], label=f"MA{LONG_WINDOW}（长均线）", color="#7c3aed", linewidth=1.2, alpha=0.9)

# 买入信号标记（红色向上三角）
ax.scatter(buy_signals["date"], buy_signals["close"] * 0.985,
           marker="^", color="#dc2626", s=150, zorder=5, label="买入信号（金叉）")
for _, row in buy_signals.iterrows():
    ax.annotate(f"买 {row['close']:.2f}",
                xy=(row["date"], row["close"] * 0.985),
                xytext=(0, -20), textcoords="offset points",
                fontsize=9, color="#dc2626", ha="center", fontweight="bold")

# 卖出信号标记（绿色向下三角）
ax.scatter(sell_signals["date"], sell_signals["close"] * 1.015,
           marker="v", color="#16a34a", s=150, zorder=5, label="卖出信号（死叉）")
for _, row in sell_signals.iterrows():
    ax.annotate(f"卖 {row['close']:.2f}",
                xy=(row["date"], row["close"] * 1.015),
                xytext=(0, 15), textcoords="offset points",
                fontsize=9, color="#16a34a", ha="center", fontweight="bold")

ax.set_title(f"{STOCK_NAME} ({TS_CODE}) 股价、均线与交易信号", fontsize=14, fontweight="bold")
ax.set_xlabel("日期")
ax.set_ylabel("价格（元）")
ax.legend(loc="upper left", fontsize=10)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
ax.xaxis.set_major_locator(mdates.MonthLocator())
fig.autofmt_xdate(rotation=30)
fig.tight_layout()
fig.savefig(FIGURE_DIR / "01_price_ma_signals.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"  图1已保存: 01_price_ma_signals.png")

# --- 图2: 均线差值与信号区间 ---
fig, axes = plt.subplots(2, 1, sharex=True, figsize=(14, 8), height_ratios=[2, 1])

ax1 = axes[0]
ax1.plot(df["date"], df["close"], label="收盘价", color="#2563eb", linewidth=1.2, alpha=0.8)
ax1.plot(df["date"], df[f"ma_{SHORT_WINDOW}"], label=f"MA{SHORT_WINDOW}", color="#f97316", linewidth=1)
ax1.plot(df["date"], df[f"ma_{LONG_WINDOW}"], label=f"MA{LONG_WINDOW}", color="#7c3aed", linewidth=1)
# 持仓区间背景填充
holding = df[df["position"] == 1]
if len(holding) > 0:
    ax1.fill_between(holding["date"], ax1.get_ylim()[0], holding["close"],
                     alpha=0.08, color="#dc2626", label="持仓区间")
ax1.set_ylabel("价格（元）")
ax1.set_title(f"{STOCK_NAME} 均线交叉策略 - 持仓区间", fontsize=13, fontweight="bold")
ax1.legend(loc="upper left", fontsize=9)

ax2 = axes[1]
colors = np.where(df["ma_diff"] >= 0, "#dc2626", "#16a34a")
ax2.bar(df["date"], df["ma_diff"], color=colors, alpha=0.6, width=1)
ax2.axhline(0, color="#64748b", linewidth=1)
ax2.set_title(f"MA{SHORT_WINDOW} - MA{LONG_WINDOW} 差值", fontsize=12)
ax2.set_ylabel("差值")
ax2.set_xlabel("日期")
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
ax2.xaxis.set_major_locator(mdates.MonthLocator())

fig.autofmt_xdate(rotation=30)
fig.tight_layout()
fig.savefig(FIGURE_DIR / "02_ma_diff_position.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"  图2已保存: 02_ma_diff_position.png")

# ============================================================
# 6. 模拟交易回测
# ============================================================
print("\n" + "=" * 60)
print("5. 策略回测与量化指标计算")
print("=" * 60)

# 回测逻辑：信号日次日开盘价成交，考虑佣金、印花税和滑点
trades = []
capital = INITIAL_CAPITAL
shares = 0
cash = INITIAL_CAPITAL

for i in range(len(df) - 1):
    today = df.iloc[i]
    tomorrow = df.iloc[i + 1]
    trade_date = tomorrow["date"]
    trade_price = tomorrow["open"]  # 次日开盘价成交

    # 滑点调整
    buy_price = trade_price * (1 + SLIPPAGE)
    sell_price = trade_price * (1 - SLIPPAGE)

    if today["signal"] == 1 and shares == 0:
        # 买入：满仓买入
        buy_amount = cash
        buy_shares = int(buy_amount / (buy_price * 100)) * 100  # 按100股整手
        if buy_shares > 0:
            cost = buy_shares * buy_price
            commission = max(cost * COMMISSION_RATE, 5)  # 佣金最低5元
            cash -= (cost + commission)
            shares = buy_shares
            trades.append({
                "date": trade_date,
                "action": "BUY",
                "price": buy_price,
                "shares": buy_shares,
                "amount": cost,
                "commission": commission,
                "cash_after": cash,
                "shares_after": shares,
            })

    elif today["signal"] == -1 and shares > 0:
        # 卖出：清仓
        revenue = shares * sell_price
        commission = max(revenue * COMMISSION_RATE, 5)
        stamp_tax = revenue * STAMP_TAX_RATE
        cash += (revenue - commission - stamp_tax)
        trades.append({
            "date": trade_date,
                "action": "SELL",
                "price": sell_price,
                "shares": shares,
                "amount": revenue,
                "commission": commission,
                "stamp_tax": stamp_tax,
                "cash_after": cash,
                "shares_after": 0,
        })
        shares = 0

# 期末持仓按最后收盘价估值
final_close = df.iloc[-1]["close"]
final_value = cash + shares * final_close

# 计算每日策略净值
df["strategy_return"] = df["close"].pct_change()
df.loc[df.index[0], "strategy_return"] = 0
# 策略收益 = 持仓日的涨跌幅
df["strategy_return"] = df["position"].shift(1) * df["close"].pct_change()
df.loc[df.index[0], "strategy_return"] = 0
df["strategy_cum_return"] = (1 + df["strategy_return"]).cumprod() - 1

# 基准收益（买入持有）
df["benchmark_return"] = df["close"].pct_change()
df.loc[df.index[0], "benchmark_return"] = 0
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

# 胜率
completed_trades = [t for t in trades if t["action"] == "SELL"]
wins = 0
trade_pnl_list = []
for i in range(0, len(trades), 2):
    if i + 1 < len(trades):
        buy_trade = trades[i]
        sell_trade = trades[i + 1]
        pnl = sell_trade["amount"] - buy_trade["amount"] - sell_trade["commission"] - sell_trade.get("stamp_tax", 0) - buy_trade["commission"]
        trade_pnl_list.append(pnl)
        if pnl > 0:
            wins += 1

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

# 超额收益
excess_return = total_return - benchmark_total_return

print(f"\n  === 回测结果 ===")
print(f"  初始资金:       ¥{INITIAL_CAPITAL:,.0f}")
print(f"  期末总资产:     ¥{final_value:,.2f}")
print(f"  净利润:         ¥{final_value - INITIAL_CAPITAL:,.2f}")
print(f"  总交易次数:     {total_trades} 次 (买入 {buy_count}, 卖出 {sell_count})")
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
print(f"  最大回撤:       {max_drawdown:.2f}%")
print(f"  基准最大回撤:   {benchmark_max_drawdown:.2f}%")
print(f"  夏普比率:       {sharpe_ratio:.2f}")
print(f"  基准夏普比率:   {benchmark_sharpe:.2f}")

# --- 图3: 策略净值 vs 基准净值 ---
fig, ax = plt.subplots(figsize=(14, 7))
ax.plot(df["date"], df["strategy_nav"], label=f"均线策略净值 (MA{SHORT_WINDOW}/MA{LONG_WINDOW})", color="#dc2626", linewidth=1.5)
ax.plot(df["date"], df["benchmark_nav"], label="买入持有净值", color="#2563eb", linewidth=1.5, alpha=0.7)
ax.axhline(INITIAL_CAPITAL, color="#64748b", linestyle="--", linewidth=1, label=f"初始资金 ¥{INITIAL_CAPITAL:,.0f}")
ax.set_title(f"{STOCK_NAME} 策略净值 vs 买入持有基准", fontsize=14, fontweight="bold")
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

# --- 图5: 月度收益热力图 ---
df["year_month"] = df["date"].dt.to_period("M")
monthly_returns = df.groupby("year_month")["strategy_return"].apply(lambda x: (1 + x).prod() - 1) * 100
benchmark_monthly = df.groupby("year_month")["benchmark_return"].apply(lambda x: (1 + x).prod() - 1) * 100

fig, ax = plt.subplots(figsize=(14, 5))
x = range(len(monthly_returns))
width = 0.35
ax.bar([i - width/2 for i in x], monthly_returns.values, width, label="策略月度收益", color=[ "#dc2626" if v >= 0 else "#16a34a" for v in monthly_returns.values], alpha=0.8)
ax.bar([i + width/2 for i in x], benchmark_monthly.values, width, label="基准月度收益", color=["#f87171" if v >= 0 else "#4ade80" for v in benchmark_monthly.values], alpha=0.5)
ax.set_xticks(list(x))
ax.set_xticklabels([str(p) for p in monthly_returns.index], rotation=45, ha="right")
ax.axhline(0, color="#64748b", linewidth=1)
ax.set_title(f"{STOCK_NAME} 月度收益率对比", fontsize=14, fontweight="bold")
ax.set_ylabel("收益率 (%)")
ax.legend(loc="upper left", fontsize=10)
fig.tight_layout()
fig.savefig(FIGURE_DIR / "05_monthly_returns.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"  图5已保存: 05_monthly_returns.png")

# ============================================================
# 7. 导出回测结果
# ============================================================
# 交易记录
trades_df = pd.DataFrame(trades)
trades_df["date"] = trades_df["date"].dt.strftime("%Y%m%d")
trades_csv = OUTPUT_DIR / "shitou_600539_ma_trades.csv"
trades_df.to_csv(trades_csv, index=False, encoding="utf-8")

# 完整数据
result = df[["date", "close", f"ma_{SHORT_WINDOW}", f"ma_{LONG_WINDOW}", "signal", "position",
             "strategy_return", "strategy_cum_return", "strategy_nav",
             "benchmark_return", "benchmark_cum_return", "benchmark_nav",
             "drawdown"]].copy()
result["date"] = result["date"].dt.strftime("%Y%m%d")
result_csv = OUTPUT_DIR / "shitou_600539_ma_backtest.csv"
result.to_csv(result_csv, index=False, encoding="utf-8")

# 汇总指标 JSON
metrics = {
    "metadata": {
        "stock_name": STOCK_NAME,
        "ts_code": TS_CODE,
        "strategy": f"MA{SHORT_WINDOW}/MA{LONG_WINDOW} 均线交叉策略",
        "data_range": f"{df['date'].min().strftime('%Y-%m-%d')} ~ {df['date'].max().strftime('%Y-%m-%d')}",
        "trading_days": int(trading_days),
        "initial_capital": INITIAL_CAPITAL,
        "commission_rate": COMMISSION_RATE,
        "stamp_tax_rate": STAMP_TAX_RATE,
        "slippage": SLIPPAGE,
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
        "total_trades": total_trades,
        "completed_round_trips": total_round_trips,
        "win_rate_pct": round(win_rate, 1),
        "avg_pnl_per_trade": round(avg_pnl, 2),
        "max_profit": round(max_profit, 2),
        "max_loss": round(max_loss, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else None,
    },
    "buy_signals": [
        {"date": r["date"].strftime("%Y-%m-%d"), "price": round(r["close"], 2),
         f"ma_{SHORT_WINDOW}": round(r[f"ma_{SHORT_WINDOW}"], 2),
         f"ma_{LONG_WINDOW}": round(r[f"ma_{LONG_WINDOW}"], 2)}
        for _, r in buy_signals.iterrows()
    ],
    "sell_signals": [
        {"date": r["date"].strftime("%Y-%m-%d"), "price": round(r["close"], 2),
         f"ma_{SHORT_WINDOW}": round(r[f"ma_{SHORT_WINDOW}"], 2),
         f"ma_{LONG_WINDOW}": round(r[f"ma_{LONG_WINDOW}"], 2)}
        for _, r in sell_signals.iterrows()
    ],
}
metrics_json = OUTPUT_DIR / "shitou_600539_ma_metrics.json"
metrics_json.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"\n" + "=" * 60)
print(f"6. 结果导出完成")
print(f"=" * 60)
print(f"  交易记录: {trades_csv}")
print(f"  回测数据: {result_csv}")
print(f"  指标汇总: {metrics_json}")
print(f"  可视化图表: {FIGURE_DIR}/01~05")
print(f"\n  回测完成!")
