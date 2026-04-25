---
name: eco-trade
description: 模拟交易执行 — 将 eco-advise 的输出转化为模拟持仓
trigger: after eco-advise generates advice, or user says "执行交易" / "更新持仓"
---

# eco-trade — 模拟交易执行

将 eco-advise 生成的资产配置建议转化为实际的模拟交易，并追踪绩效。

## 流程

### 1. 检查当前持仓

```bash
python3 lab/trading/paper/account.py summary
```

### 2. 从 eco-advise 获取 tilt 信号

读取最新 eco-advise 的建议 tilts（如 `{"stocks":-2,"long_bonds":-1,"commodities_gold":1,"cash":2}`）。

### 3. 获取当前 ETF 价格

需要获取当前 ETF 价格（SPY/TLT/GLD/BIL）用于计算目标持仓。
可以通过 WebFetch 或 WebSearch 获取，或使用上次已知价格。

### 4. 执行再平衡

```bash
python3 lab/trading/paper/executor.py \
  --tilts '<advice tilts JSON>' \
  --prices '<prices JSON>' \
  --reason "eco-advise YYYY-MM-DD <regime>"
```

### 5. 记录快照

```bash
python3 lab/trading/paper/tracker.py --snapshot
```

### 6. 输出摘要

```json
{
  "action": "rebalance",
  "previous_tilts": {...},
  "new_tilts": {...},
  "orders_executed": 3,
  "portfolio_value": 100000.0,
  "changes_summary": "从之前配置调整到新配置"
}
```

## ETF 映射

| 资产类别 | ETF | 说明 |
|---------|-----|------|
| 股票 (stocks) | SPY | S&P 500 ETF |
| 长期国债 (long_bonds) | TLT | 20+ Year Treasury ETF |
| 商品/黄金 (commodities_gold) | GLD | Gold ETF |
| 现金 (cash) | BIL | 1-3 Month T-Bill ETF |

## 约束

- 只交易 ETF，不交易个股/个债
- 每次 rebalance 应保持仓位在 target 的 ±5% 以内
- 不频繁交易（至少 1 周间隔）
- 记录每次交易的理由以用于复盘
