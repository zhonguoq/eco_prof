---
id: P003
title: 总债务/GDP 超过 300%/350% 触发长期风险警戒
statement: |
  当总债务/GDP 超过 300% 时进入长期风险警戒区；超过 350% 时接近历史泡沫顶部均值，系统性风险显著上升。
rationale: |
  这是 Dalio 对过去 500 年储备货币帝国兴衰的研究结论。总债务/GDP 是衡量一国"债务承载能力"的关键指标。
  每次达到 350% 左右时都伴随储备货币地位的动摇和重大经济调整。
sources:
  - 债务周期阶段判断框架.md
  - 宏观环境判断与投资指引框架.md
  - 储备货币周期-reserve-currency-cycle.md
confidence: high
testable: true
encoded_in:
  - lab/dashboard/backend/regime.py:34-35
  - lab/dashboard/backend/regime.py:160-168
status: active
last_reviewed: 2026-04-25
review_cadence: yearly
tags: [debt, systemic-risk, reserve-currency]
related_principles: [P002, RCC01]
---

## 解读

- 这个 300%/350% 是针对**总债务**（政府 + 企业 + 家庭），不是只看政府债务
- 各国阈值因发展阶段不同而不同：美国等成熟储备货币国家容忍度更高
- 当前（2026-04-25）：美国总债务/GDP ≈ 342.5%，处于警戒区，已接近 350% 危险线

## 历史参考

- 2008 年金融危机前：美国总债务/GDP ~ 290%
- 2020 年 COVID 前：~ 350%
- 2020 年后：因 GDP 收缩短暂突破 400%，后回落
- 历史泡沫顶部均值约 300%（《大债务周期》研究）

## 已编码的引用

- `regime.py:34-35`：`DEBT_GDP_WARNING = 300`, `DEBT_GDP_DANGER = 350`
- `regime.py:160-168`：诊断逻辑，按阈值分出 ok / warning / danger
- 当前状态：⚠️ warning（342.5% ≈ 350%）

## 局限

- 总债务口径受金融衍生品、表外负债等因素影响，各国统计口径不一
- GDP 是流量而债务是存量，直接用比值在经济衰退期会"被动跳升"（GDP 降分母）
