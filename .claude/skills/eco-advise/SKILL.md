---
name: eco-advise
description: 基于三层诊断 + 告警 + 原则，给出结构化资产配置建议
trigger: user asks for investment advice, or as final step in eco-brief
---

# eco-advise — 结构化投资建议引擎

基于当前宏观诊断、活跃告警、新闻语境和原则框架，合成资产配置建议。
输出人类可读报告 + 结构化 JSON（供未来 Trading Agent 消费）。

## 流程

### 1. 收集输入

调用 eco-advise 前需准备好以下数据：

| 输入 | 来源 | 说明 |
|------|------|------|
| 当前 Regime | lab-diagnose / diagnosis_history.jsonl | 四象限 + 资产倾向 |
| 债务周期阶段 | lab-diagnose / diagnosis_history.jsonl | 5 信号 + 综合判断 |
| 活跃告警 | `python3 lab/tools/run_alerts.py --date <date> --news <news.jsonl>` | P1/P2/P3 告警列表 |
| 新闻要点 | news-scan 输出 | 按 category 的新闻摘要 |
| 框架原则 | wiki-query | 当前 regime 相关原则卡片 |

### 2. 合成逻辑

#### 2.1 基准配置

从 regime.py 的 `ASSET_TILTS` 四象限映射中获取基准资产倾向：

| Regime | 股票 | 长债 | 商品/黄金 | 现金 |
|--------|------|------|----------|------|
| Goldilocks | +2 | +1 | -1 | -1 |
| Overheating | +1 | -2 | +2 | -1 |
| Stagflation | -2 | -1 | +1 | +2 |
| Deflation | -1 | +2 | -2 | +1 |

#### 2.2 告警调整因子

活跃告警对基准配置进行修正：

| 告警 | 调整 | 说明 |
|------|------|------|
| ALERT-WAR (P1) | 黄金/商品 +1, 股票 -1 | 地缘风险溢价 |
| ALERT-FED (P1) | 现金 +1, 长债 -1 | 央行意外 → 波动率上升 |
| ALERT-BANK (P1) | 现金 +2, 所有风险资产 -1 | 系统性风险 → 全面防御 |
| ALERT-YC (P1) | 股票 -1, 现金 +1 | 衰退信号 → 减仓风险资产 |
| ALERT-DEBT (P1) | 长债 -1, 黄金 +1 | 债务可持续性担忧 |
| ALERT-DIVERGE (P1) | 股票 -1, 现金 +1 | 泡沫风险 → 减仓 |
| ALERT-SPREAD (P1) | 全面 -1 风险资产 | 信用市场恐慌 |
| ALERT-SENTIMENT (P2) | 消费/零售相关 -0.5 | 消费者悲观 → 消费类承压 |
| ALERT-STAG (P2) | 维持基准 stagflation 配置 | 确认当前 regime 判断 |

调整规则：P1 告警调整幅度 ±1，P2 告警 ±0.5。多个同方向告警叠加，上限 ±2。

#### 2.3 时间框架映射

将单一配置映射到三个时间框架：

| 时间框架 | 范围 | 侧重 |
|---------|------|------|
| 短期 (Short) | 1-3 月 | 告警/新闻驱动的高频调整，侧重防御 |
| 中期 (Medium) | 3-12 月 | Regime 判断 + 周期定位 |
| 长期 (Long) | 1-3 年 | 结构趋势 + 原则不变部分（如债务/GDP 趋势） |

短期配置更保守（对 P1 告警敏感），长期配置更接近基准 regime 映射。

#### 2.4 置信度评分

每条建议附带置信度，基于以下因素综合：

| 因素 | 高置信度 | 低置信度 |
|------|---------|---------|
| 信号一致性 | Layer 1/2/3 方向一致 | 三层背离（当前正是） |
| 数据时效性 | 数据在 1 周内 | 关键数据超过 1 季度 |
| 框架覆盖度 | wiki 有明确框架依据 | 框架盲区/无法建模 |
| 历史对标 | 有清晰历史对标 | 无先例的新现象 |

输出格式：`confidence: high / medium-high / medium / medium-low / low`

### 3. 输出格式

#### 3.1 人类可读报告

```markdown
---
title: "eco_prof 投资建议"
date: YYYY-MM-DD
mode: advice
based_on: daily-brief YYYY-MM-DD
---

# eco_prof 投资建议

## TL;DR
（3-5 句话总结核心建议）

## 基准配置（Regime: XXXX）

| 资产 | 基准倾向 | 短期 (1-3m) | 中期 (3-12m) | 长期 (1-3y) | 置信度 |
|------|---------|------------|-------------|------------|--------|
| 股票 | ±N | ±N | ±N | ±N | high/low |
| 长期国债 | ±N | ±N | ±N | ±N | high/low |
| 商品/黄金 | ±N | ±N | ±N | ±N | high/low |
| 现金 | ±N | ±N | ±N | ±N | high/low |

## 关键调整因子
- 告警调整：ALERT-XXX → ±N（说明）
- 新闻语境：（简要说明）
- 框架修正：（如有偏离框架的判断）

## 情景分析

| 情景 | 概率 | 配置方向 |
|------|------|---------|
| 基准情景 | XX% | ... |
| 乐观情景 | XX% | ... |
| 悲观情景 | XX% | ... |

## 风险提示
- （列举 2-3 个值得关注的尾部风险）

## 待观察
- （触发配置调整的关键观察指标）
```

#### 3.2 结构化 JSON（Trading Agent 消费）

```json
{
  "advice_id": "advice-2026-04-25",
  "generated_at": "2026-04-25T15:00:00",
  "based_on": {"regime": "Stagflation", "debt_stage": "早期健康/正常化"},
  "base_tilts": {"stocks": -2, "long_bonds": -1, "commodities_gold": 1, "cash": 2},
  "active_alerts": ["ALERT-WAR", "ALERT-STAG", "ALERT-SENTIMENT"],
  "allocations": {
    "short_term_1_3m": {
      "stocks": {"tilt": -2, "confidence": "medium"},
      "long_bonds": {"tilt": -1, "confidence": "medium"},
      "commodities_gold": {"tilt": 2, "confidence": "high"},
      "cash": {"tilt": 2, "confidence": "high"}
    },
    "medium_term_3_12m": {
      "stocks": {"tilt": -2, "confidence": "medium-low"},
      "long_bonds": {"tilt": -1, "confidence": "medium-low"},
      "commodities_gold": {"tilt": 1, "confidence": "medium"},
      "cash": {"tilt": 2, "confidence": "medium-high"}
    },
    "long_term_1_3y": {
      "stocks": {"tilt": -1, "confidence": "medium-low"},
      "long_bonds": {"tilt": 0, "confidence": "low"},
      "commodities_gold": {"tilt": 1, "confidence": "medium"},
      "cash": {"tilt": 1, "confidence": "medium"}
    }
  },
  "scenarios": {
    "baseline": {"probability": 0.5, "description": "..."},
    "bull": {"probability": 0.25, "description": "..."},
    "bear": {"probability": 0.25, "description": "..."}
  },
  "risk_warnings": ["..."],
  "key_watchpoints": ["..."]
}
```

## 约束

- 不给出具体价格目标（超越框架能力）
- 不推荐个股/个债（只到资产类别级别）
- 每个建议必须标注置信度
- 如果框架无法覆盖当前情况，明确标注"框架盲区"
- 所有建议基于 Dalio 原则框架，对框架本身的偏离需加注说明
- **不构成投资建议**——仅供研究参考
