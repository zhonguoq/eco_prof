---
id: P004
title: 增长-通胀四象限决定资产配置倾向
statement: |
  用实际 GDP 同比（阈值 2%）和 CPI 同比（阈值 3%）将宏观环境分为四个象限：
  Goldilocks / Overheating / Stagflation / Deflation，每个象限有对应的最优资产配置倾向。
rationale: |
  这是宏观资产配置的经典框架，Dalio 的 "All Weather" 策略以此为核心。
  不同象限下各类资产的表现差异极大，识别象限是配置的第一步。
sources:
  - 宏观环境判断与投资指引框架.md
  - 债务周期阶段判断框架.md
confidence: high
testable: true
encoded_in:
  - lab/dashboard/backend/regime.py:41-61
status: active
last_reviewed: 2026-04-25
review_cadence: yearly
tags: [asset-allocation, macro-regime, quadrant-model]
related_principles: [P003, D03]
---

## 资产配置映射

| 象限 | 股票 | 长期国债 | 商品/黄金 | 现金 |
|------|------|---------|----------|------|
| Goldilocks | +2 | +1 | -1 | -1 |
| Overheating | +1 | -2 | +2 | -1 |
| Stagflation | -2 | -1 | +1 | +2 |
| Deflation | -1 | +2 | -2 | +1 |

（±2 = 强配置，±1 = 轻度，0 = 中性）

## 解读

- 对股票最有利：Goldilocks（高增长低通胀）→ 盈利扩张 + 利率温和
- 对股债双杀：Stagflation（低增长高通胀）→ 盈利承压 + 利率高企
- 对债券最有利：Deflation（低增长低通胀）→ 通缩实际回报 + 降息预期
- 商品/黄金在通胀环境下普遍受益

## 已编码的引用

- `regime.py:41-51`：四象限定义 + 中文标签
- `regime.py:56-61`：ASSET_TILTS 映射表
- 当前（2026-04-25）：Stagflation，股票 -2，长债 -1，商品/黄金 +1，现金 +2

## 局限

- 阈值（2%/3%）可调——不同经济体不同周期阶段需调整
- 四象限是需求侧框架，无法完美捕捉供给冲击（如战争驱动的通胀）
- 象限间过渡期往往比稳定期更关键——象限转换比象限本身更重要
