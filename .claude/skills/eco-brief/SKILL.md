---
name: eco-brief
description: 生成每日宏观简报 — 调用诊断+新闻+wiki 框架综合输出
trigger: user invokes /eco-brief command
---

# eco-brief — 每日宏观简报生成

按照"数据诊断 → 新闻 → 框架对照 → 资产建议 → 待观察"的标准化结构，生成完整简报。

## 前置条件

调用本 skill 前，先运行：
1. **lab-diagnose** — 获取当前诊断数据
2. **news-scan** — 获取今日新闻要点
3. **wiki-query** — 读取当前 regime 相关的框架内容（如需要）

或者直接运行三段式流程（下面包含所有这些步骤）。

## 简报流程

### Step 1：运行数据诊断

执行 lab-diagnose skill 的完整流程（读 snapshot → 计算诊断 → 计算 regime）。

关键输出：
- 债务周期阶段（Layer 1）
- 增长-通胀 regime（Layer 2）
- 资产配置倾向（股票/长债/商品黄金/现金）
- 长期结构风险（Layer 3）
- 近 7 天 regime 轨迹（从 diagnosis_history.jsonl 读取）

### Step 2：扫描今日新闻

执行 news-scan skill 的完整流程。

### Step 3：对照 wiki 框架解读

读取相关 wiki 页面，将当前数据与框架对照：

- `knowledge/wiki/analyses/宏观环境判断与投资指引框架.md` — 三层诊断 + 资产配置映射
- `knowledge/wiki/analyses/债务周期阶段判断框架.md` — 核心指标解读
- `knowledge/wiki/analyses/债务周期的内在逻辑——从生产率到泡沫.md` — 资产通胀 vs 商品通胀

对照要点：
- **三层背离检查**：Layer 1 / Layer 2 / Layer 3 的信号是否一致？矛盾意味着什么？
- **当前 regime 的经典资产应对**：框架怎么规定？当前有什么特殊情况？
- **关键阈值检查**：哪些指标接近/触达了框架定义的警戒线？
- **框架不足标注**：当前分析中有哪些框架无法覆盖的盲区？

### Step 4：运行告警引擎

调用 `lab/tools/run_alerts.py` 自动检查所有硬信号和软信号：

```bash
python3 lab/tools/run_alerts.py --date $(date +%Y-%m-%d) --news lab/news/<today>.jsonl
```

告警引擎输出包含：
- **triggered_alerts**：本次新触发的告警列表
- **p1_count / p2_count**：各级别告警数量
- **active_alerts**：当前所有活跃告警（含持续中）

将告警输出作为简报 ⚠️ 部分的直接数据源。

**P1 告警升级**：如果 `p1_count > 0`，在简报中额外生成一个"🔥 P1 紧急事项"区块，
并建议用户/系统调用 `event-brief` skill 生成专题简报。

### Step 5：写简报

写入 `lab/reports/YYYY-MM-DD_eco-brief.md`，结构如下：

```markdown
---
title: "eco_prof Daily Brief YYYY-MM-DD"
date: YYYY-MM-DD
mode: daily
regime: "..."
debt_stage: "..."
alerts: true/false
alerts_p1: <count>
alerts_p2: <count>
framework_ref: knowledge/wiki/analyses/宏观环境判断与投资指引框架.md
---

## TL;DR
（1-3 句话全局总结，如果步告警引擎返回了 P1 告警，必须在 TL;DR 中提及）

## ⚠️ 告警

（从告警引擎输出渲染，格式：）

| 级别 | 告警 | 当前值 | 关联原则 |
|------|------|--------|---------|
| 🔴 P1 | 地缘冲突 | 战争/制裁关键词匹配 | — |
| 🟡 P2 | 消费者信心 | UMCSENT 53.3 | — |
| 🟡 P2 | 债务/GDP 警戒 | 342.5% | P003 |

持续中告警标注「🔄 持续中」

### 🔥 P1 紧急事项
（如果 p1_count > 0，解释每个 P1 告警的含义和影响）

## 1. 当日数据诊断
- 债务周期阶段 + 5 信号表格
- 增长通胀 Regime
- 资产倾向
- 长期结构风险
- 近 7 天 Regime 轨迹

## 2. 新闻要点（按 category 分组）

## 3. 框架对照
- 对照 wiki 分析各信号含义
- 框架要点
- 框架不足

## 4. 资产倾向
- 框架给出的倾向 + 当前市场情况的修正说明

## 5. 待关注问题
（未来 1-2 周的关键事件和数据发布）

## 6. 数据引用
（所有用到的数据文件路径）

---
```

### Step 6：更新日志

追加一条记录到 `knowledge/wiki/log.md`：
```
## [YYYY-MM-DD HH:MM] eco-prof | daily-brief | <一句话总结>
```

## 输出

- 主产出：`lab/reports/YYYY-MM-DD_eco-brief.md`
- 日志条目：`knowledge/wiki/log.md`
