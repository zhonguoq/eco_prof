---
id: P007
title: 利率水平与方向共同决定货币政策阶段
statement: |
  判断货币政策阶段需要同时看利率水平（高位/中等/近零）和方向（上升/下降/平稳）：
  高位+上升→收紧末端 → 高位+急降→顶部反转确认衰退
  中等+上升→收紧中 → 中等+下降→放松中
  近零+上升→正常化初期 → 近零+平稳→去杠杆
rationale: |
  单独的利率水平会误导——"利率中等"可以是收紧中也可以是放松中。
  加入方向（3个月趋势）后，可以得到 3×3 = 9 个状态，覆盖债务周期完整序列。
  这是 A6 的编码实现。
sources:
  - 债务周期阶段判断框架.md
  - 债务周期的内在逻辑-从生产率到泡沫.md
confidence: medium
testable: true
encoded_in:
  - lab/dashboard/backend/regime.py:classify_rate_phase
status: active
last_reviewed: 2026-04-25
review_cadence: yearly
tags: [monetary-policy, interest-rate, phase-detection]
related_principles: [P001, P006]
---

## 解读

- 利率阶段是债务周期阶段检测的核心辅助信号
- 高位+上升≈泡沫中后期；高位急降≈衰退确认
- 近零≈去杠杆；近零微升≈正常化曙光
- 需要约 3 个月数据来确定趋势方向，短期波动会被平滑

## 已编码的引用

- `regime.py:classify_rate_phase()` — 完整的利率阶段分类器
- `regime.py:RATE_PHASE_THRESHOLDS` — 阈值配置（高/低/趋势窗口/趋势敏感度）

## 局限

- 趋势窗口固定为 63 个交易日（~3 个月），不适合检测快速政策转向
- 零利率下限（ZLB）时期方向信号丢失，降级为水平分类
- "高位"阈值 3% 和"低位"阈值 0.5% 是经验值，需根据经济体调整
