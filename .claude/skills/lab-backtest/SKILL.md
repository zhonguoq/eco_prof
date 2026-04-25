---
name: lab-backtest
description: 回测投资原则在历史数据上的表现，验证原则有效性
trigger: user wants to validate principles, or after principle extraction
---

# lab-backtest — 原则回测验证

对已编码的原则进行历史数据回测，验证其预测能力和稳定性。

## 回测框架

使用 `lab/tools/backtest_principles.py` 脚本执行回测。规则：

1. 每个回测应有一个清晰的**假设**（原则 statement 的可量化版本）
2. 一个明确的**成功指标**（准确率、精确率、召回率、领先时间）
3. 使用现有 FRED 历史数据（1995 年至今）
4. 输出结构化 JSON 结果

## 回测流程

### 1. 定义回测

```python
backtest = {
    "principle_id": "P001",
    "hypothesis": "10Y-2Y 利差持续为负 30 天以上后，24 个月内出现 NBER 衰退",
    "independent_var": "T10Y2Y < 0 for >30 days",
    "dependent_var": "NBER recession within 24 months",
    "data_needed": ["T10Y2Y", "USREC"],
    "period": "1995-01-01 to today",
}
```

### 2. 执行回测

```bash
python3 lab/tools/backtest_principles.py --principle P001
```

### 3. 评估结果

| 指标 | 含义 | 评判标准 |
|------|------|---------|
| 准确率 | (TP+TN)/(TP+TN+FP+FN) | > 70% 有预测价值 |
| 精确率 | TP/(TP+FP) | > 60% 信号可靠 |
| 召回率 | TP/(TP+FN) | > 80% 不遗漏 |
| 平均领先时间 | 信号到事件的平均月数 | 有实际决策意义即可 |
| 最差领先时间 | 信号到事件的最短月数 | > 0，否则信号出现在事后 |

### 4. 更新原则卡片

在原则卡片的 frontmatter 中添加 `backtest_findings` 字段：

```yaml
backtest_findings:
  accuracy: 0.85
  precision: 0.75
  recall: 1.0
  avg_lead_months: 14
  worst_lead_months: 5
  last_tested: 2026-04-25
  note: "所有显示该产品..."
```

如果回测结果不佳，将 `status` 改为 `deprecated` 并记录原因。
