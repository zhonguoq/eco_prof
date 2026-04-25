---
name: eco-brief
description: 每日/专题宏观简报的归档技能。接收 eco-prof 已合成好的内容，按模板写 lab/reports/YYYY-MM-DD_eco-brief.md，并在 wiki/log.md 追加一行。不做分析——分析是 eco-prof 做的，这里只做格式化和归档。
---

# eco-brief — 简报归档技能

## 契约（稳定）

**输入**（由 eco-prof 传入已综合好的内容）：
- `mode`: `daily | topic`（必需）
- `date`: YYYY-MM-DD（默认今日）
- `focus`: 可选，专题时用作标题副标题
- `tldr`: 3 句内核心判断（必需）
- `alerts`: 可选，告警板块原文
- `diagnosis_block`: lab-diagnose 输出的 Markdown（必需）
- `news_block`: news-scan 输出的 Markdown（必需，若当日无新闻也要写"无新增"）
- `framework_block`: wiki-query 输出的 Markdown（必需）
- `asset_tilts_note`: 对 regime.py 默认资产倾向的补充说明（可选；不要推翻，除非数据有力）
- `watch_list`: 下一步值得关注的问题/信号
- `data_refs`: 数据与新闻文件路径列表

**输出**：
- 写文件 `lab/reports/YYYY-MM-DD_eco-brief.md`（专题模式则为 `YYYY-MM-DD_eco-brief-<focus-slug>.md`）
- 追加 `wiki/log.md` 一行（见下）
- 返回写入路径

## 模板

```markdown
---
title: "eco_prof Daily Brief <date>"
date: <date>
mode: <mode>
focus: <focus or null>
regime: <quadrant>
debt_stage: <stage>
alerts: <bool>
framework_ref: wiki/analyses/宏观环境判断与投资指引框架.md
---

# eco_prof Daily Brief — <date>

## TL;DR
<tldr>

<if alerts: ## ⚠️ 告警\n<alerts>>

## 1. 当日数据诊断
<diagnosis_block>

## 2. 新闻要点（过去 24h）
<news_block>

## 3. 框架对照
<framework_block>

## 4. 资产倾向
<默认由 regime.py 给出，此处只呈现表格；若 asset_tilts_note 非空，附加于表格下方>

| 资产 | 倾向 | 说明 |
|---|---|---|
| 股票 | +X | ... |
| 长期国债 | +X | ... |
| 商品/黄金 | +X | ... |
| 现金 | +X | ... |

<asset_tilts_note if any>

## 5. 待关注问题
<watch_list>

## 6. 数据引用
<data_refs bulleted>

---
*由 eco-prof 在 <local timestamp> 生成 · mode=<mode>*
```

## 实现步骤

1. 计算 `date`（默认 `datetime.date.today()`）
2. 计算文件路径 `lab/reports/YYYY-MM-DD_eco-brief[-<focus-slug>].md`
   - focus-slug：中文保留，空格转 `-`，截断 30 字
3. 用 Write 工具写入（若文件已存在且同日同 focus → 加后缀 `-v2`，不覆盖）
4. 用 Bash 追加一行到 `wiki/log.md`：
   ```
   ## [YYYY-MM-DD HH:MM] eco-prof | <mode> | <tldr 第一句>
   - 归档: lab/reports/<filename>
   - regime: <quadrant> · debt_stage: <stage>
   <- alerts: yes if alerts else omit>
   ```
5. 返回绝对路径字符串

## 约束

- **不做分析**：不重新判断 regime，不改 tilts，不挑战诊断——那是 eco-prof 的事。这里只做**搬运工 + 格式化**。
- **不读 wiki 原文**：framework_block 由 eco-prof/wiki-query 提供；这里只贴。
- 如果任何必需输入缺失：报错 + 列出缺项，不要用空字符串糊弄。

## 演进路径

- v0.2：支持 `format: markdown | html | pdf`（pdf 用 pandoc）
- v0.3：同时发送到 webhook（Slack / Telegram）
- v0.4：简报之间加"和上次比"的 diff 板块
