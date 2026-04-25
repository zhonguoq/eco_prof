---
id: P006
title: 收益率曲线六形态对应不同债务周期阶段
statement: |
  收益率曲线呈现六种不同形态，每种对应特定的债务周期阶段：
  正常正斜率（早期健康）→ 趋平（泡沫中后期）→ 倒挂（顶部）
  → 牛陡（萧条开始）→ 超平近零（去杠杆/QE）→ 恢复正斜率（正常化）
rationale: |
  收益率曲线不仅监控倒挂，其完整形态演变序列对应债务周期的每个阶段。
  监控形态转换比监控单一利差点位更有预测价值——比如从"趋平→倒挂"是顶部的确信号，
  而从"倒挂→牛陡"确认衰退已经开始。
  这是 P001 的扩展——P001 关注单一检查点（是否倒挂），P006 关注完整形态序列。
sources:
  - 收益率曲线-yield-curve.md
  - 债务周期阶段判断框架.md
  - 大债务周期-big-debt-cycle.md
confidence: medium
testable: true
encoded_in:
  - lab/dashboard/backend/regime.py:classify_yield_curve_shape
status: active
last_reviewed: 2026-04-25
review_cadence: yearly
tags: [yield-curve, debt-cycle, phase-detection, pattern-recognition]
related_principles: [P001, B04]
---

## 六形态详解

| 形态 | 利差 | 短端 | 特征 | 阶段 |
|------|------|------|------|------|
| 正常正斜率 | >+0.50% | 正常（>2%） | 利差充裕，银行有放贷动力 | 早期健康 |
| 趋平 | 0 ~ +0.50% | 上升中 | 短端上行快于长端，利差压缩 | 泡沫中后期 |
| 倒挂 | <0% | 高位 | 利差为负，信贷收缩 | 顶部 |
| 牛陡 | <0% 但快速回升 | 暴跌 | 短端崩溃，央行紧急降息 | 萧条开始 |
| 超平近零 | ~0% | <0.5% | 短端近零，曲线被 QE 压制 | 去杠杆 |
| 恢复正斜率 | >+0.50% | 低位回升 | 曲线重新正常化 | 正常化 |

## 已编码的引用

- `regime.py:classify_yield_curve_shape()` — 完整的六形态分类器
- `regime.py:YC_SHAPES` — 形态定义字典
- `regime.py:YC_SHAPE_THRESHOLDS` — 阈值配置

## 局限

- 趋势计算依赖 ~3 个月时间窗口，数据稀疏时降级为利差水平分类
- QE 期间形态可能失真（央行人为压低长端）
- 形态判定在过渡期（如从倒挂到牛陡的边缘）可能不稳定
