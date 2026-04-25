---
name: event-brief
description: P1 告警触发时自动生成专题简报
trigger: when run_alerts.py returns P1 alerts, or user says "专题简报"
---

# event-brief — 事件驱动专题简报

当系统检测到 P1（严重）告警时，自动生成聚焦该风险的专题简报，
不经过标准 eco-brief 流程——直接深入分析单一主题。

## 触发条件

1. **自动检测**：`python3 lab/tools/run_alerts.py --date <YYYY-MM-DD> --news lab/news/<YYYY-MM-DD>.jsonl`
   输出中 `p1_count > 0`
2. **手动**：用户说"写一个关于 XX 的专题简报"

## 流程

### 1. 定位触发事件

如果自动触发，从告警输出中找到所有 P1 告警：

```json
{
  "alert_id": "ALERT-WAR",
  "severity": "P1",
  "title": "地缘冲突推升不确定性（新闻关键词匹配）",
  "current_value": "匹配关键词: war, IRGC, sanctions",
  "triggered_at": "2026-04-25",
  "suggested_action": "生成专题简报：地缘风险分析"
}
```

如果手动触发，直接使用用户指定主题。

### 2. 收集相关数据

根据告警类型收集数据：

| 告警类型 | 需读取的数据 |
|---------|------------|
| ALERT-YC / YC2 | `fred_t10y2y_*.csv`（日度序列）、`诊断历史.jsonl` |
| ALERT-DEBT / DEBT2 | `fred_tcmdo_*.csv`、`fred_gdp_*.csv`、`fred_gfddegdq188s_*.csv` |
| ALERT-DIVERGE | `fred_sp500_*.csv`、`fred_cpiaucsl_*.csv` |
| ALERT-SPREAD | `fred_bamlh0a0hym2_*.csv` |
| ALERT-WAR | 今日新闻中地缘政治相关条目 |
| ALERT-FED | 今日新闻中央行相关条目 + `fred_fedfunds_*.csv` |
| ALERT-BANK | 今日新闻 + 信用利差数据 |

### 3. 分析框架

遵循三层分析结构：

**Layer 1 — 发生了什么**
- 事件描述：什么、何时、谁
- 数据佐证：用图表或数据锚定

**Layer 2 — 框架定位**
- 关联哪些原则卡片（原理层面解读）
- 对当前 regime / 债务周期阶段的影响
- 历史对标（类似事件过去如何演变）

**Layer 3 — 投资含义**
- 资产配置调整建议（如果有）
- 关键观察指标（什么信号会证实/证伪当前判断）
- 情景分析（乐观 / 基准 / 悲观）

### 4. 生成简报

文件命名：`lab/reports/YYYY-MM-DD_brief-<topic-slug>.md`

格式示例：

```markdown
---
title: "专题简报：<主题>"
date: YYYY-MM-DD
type: event-driven
trigger: <告警ID 或 用户请求>
p1_alerts: [告警列表]
---

# 专题简报：<主题>

## TL;DR
<三句话总结>

## 1. 事件概述
...

## 2. 框架分析
- **关联原则**: P00X — ...
- **Regime 影响**: ...
- **历史对标**: ...

## 3. 投资含义
- **资产影响**: ...
- **关键观察**: ...
- **情景**:
  - 乐观: ...
  - 基准: ...
  - 悲观: ...

## 4. 数据引用
- ...
```

### 5. 归档

- 简报存入 `lab/reports/`
- 在 `knowledge/wiki/log.md` 追加一条记录
- 如果是重大事件，提议将分析结论归档到 `knowledge/wiki/analyses/`

## 约束

- 专题简报聚焦**单一主题**，不要面面俱到
- 不重复 eco-brief 中的常规内容
- 如果同一日有多个 P1 告警，优先处理最高优先级的（WAR > FED > BANK > YC > DEBT > SPREAD）
- 简报应在 1000-2000 字范围内，保持可读性
