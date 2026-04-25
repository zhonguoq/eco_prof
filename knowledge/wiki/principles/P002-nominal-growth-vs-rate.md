---
id: P002
title: 名义增速大于名义利率则债务负担自然减轻
statement: |
  当名义 GDP 同比增速持续高于名义利率（10Y 国债收益率）时，债务/收入比自然下降；反之则债务负担积累。
rationale: |
  这是 Dalio 债务周期框架的核心机制之一。收入增速 > 借贷成本 = "顺风"，借款人无需削减支出就能偿还债务。
  这是美丽去杠杆的必要条件（E1）。
sources:
  - 债务周期阶段判断框架.md
  - 债务周期的内在逻辑-从生产率到泡沫.md
  - 大债务周期-big-debt-cycle.md
  - 美丽去杠杆化-beautiful-deleveraging.md
confidence: medium  # Backtest shows weaker relationship than expected
testable: true
encoded_in:
  - lab/dashboard/backend/main.py:151-161
status: active
last_reviewed: 2026-04-25
review_cadence: yearly
tags: [debt-cycle, macro, monetary-policy]
related_principles: [E1, P001]
---

## 回测结果（2026-04-25）

参见 `lab/tools/backtest_principles.py` `backtest_p002()`

**数据范围**：1996-01 至 2025-10（120 个季度）

| 指标 | 结果 |
|------|------|
| Growth > Rate 的季度数 | 88/120（73%） |
| 其中债务/GDP 在次年下降 | 37（42%）|
| Rate > Growth 的季度数 | 32/120（27%） |
| 其中债务/GDP 在次年上升 | 22（69%）|
| 相关性 GDP 增速 vs 4Q后债务变化 | +0.17（弱正相关） |

**结论**：原则的单向表述"Growth > Rate → 债务自然减轻"过于简化——在 42% 的情况下确实减轻，但不是可靠的预测信号。反向表述"Rate > Growth → 债务倾向于上升"更可靠（69%）。原则需要修正为"方向正确但非因果关系"。

## 解读

- 这是判断"债务周期是否可持续"的核心检查项——但要认识到它更多是**方向性**而非**确定性**的
- 为什么 Growth > Rate 不一定减轻债务？因为在增长向好的时期，信贷往往加速扩张（动物精神）
- 不仅看当前的差值，要看趋势：差值在扩大还是缩小？
- 用 10Y 国债收益率作为"名义利率"代理——虽然是近似值，但在框架中稳定可用

## 历史含义

| 状态 | 含义 | 阶段 |
|------|------|------|
| gdp_yoy - dgs10 > +2% | 强顺风，债务快速消化 | 复苏/正常化 |
| gdp_yoy - dgs10 = 0~+2% | 温和顺风，债务稳定 | 早期扩张 |
| gdp_yoy - dgs10 = 0~-2% | 逆风开始，债务微增 | 泡沫后期 |
| gdp_yoy - dgs10 < -2% | 强逆风，债务加速积累 | 崩溃/去杠杆 |

## 已编码的引用

- `main.py:151-161`：`diff = gdp_yoy - dgs10`；`diff > 0 → ok`；`diff > -1 → warning`；`else → danger`
- 当前（2026-04-25）：名义GDP 5.4% vs 10Y 4.3%，diff = +1.0%，温和顺风
