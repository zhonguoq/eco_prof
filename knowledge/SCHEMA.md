# knowledge/ Schema — 知识库契约

本文定义 `knowledge/` 下所有 wiki 页的格式、内链规范、语言约定、ingest/query/lint 工作流。`.claude/skills/knowledge-query` 与 eco-prof 在引用 wiki 时以本文为准。

---

## 目录结构

```
knowledge/
├── CLAUDE.md
├── SCHEMA.md               # 本文件
├── docs/                   # 背景散文（非规范）
├── raw/                    # 源文档（immutable）
│   ├── assets/             # 图片、PDF、附件
│   └── *.md / *.pdf / ...
└── wiki/                   # LLM 维护的知识体
    ├── index.md            # 全局索引
    ├── log.md              # 操作日志（append-only）
    ├── concepts/           # 经济学概念、理论、模型
    ├── thinkers/           # 思想家条目
    ├── schools/            # 学派概览
    ├── sources/            # 每个 raw 源的摘要页
    └── analyses/           # 跨源综合分析
```

---

## 页格式（YAML frontmatter）

```yaml
---
title: Page title
type: concept | thinker | school | source | analysis
tags: [macroeconomics, monetary-policy, ...]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [source-filename, ...]   # 支撑该页的 raw 源
---
```

### 按页类型的内容骨架

**concept**
- Definition (Chinese + English)
- Core mechanism
- Related concepts (internal links)
- Representative thinkers (internal links)
- School affiliation (internal links)
- Source citations

**thinker**
- Bio (birth/death years, nationality, school)
- Core contributions
- Major works
- Key concepts (internal links)
- Controversies and criticisms
- Source citations

**school**
- Origins and background
- Core claims
- Representative figures (internal links)
- Key concepts (internal links)
- Disagreements with other schools
- Source citations

**source**
- Metadata (author, year, type)
- Core arguments (3–7 bullets)
- Key concepts (internal links)
- Relation to existing wiki content: what it supports or challenges
- Questions worth exploring further

**analysis**
- Problem / goal
- Method
- Key findings
- Conclusions
- Wiki pages cited

---

## 内链规范

使用标准 Markdown 链接：`[Page Title](../concepts/page.md)`。
用相对路径，兼容 Obsidian 与普通 Markdown 渲染器。

---

## 工作流

### Ingest（处理一个新 source）

1. 读 `knowledge/raw/` 下的源文件
2. （可选）和用户讨论要点
3. 在 `knowledge/wiki/sources/` 建 source 摘要页
4. 更新或新建 `concepts/` / `thinkers/` / `schools/` 相关页
5. 更新 `knowledge/wiki/index.md` 条目与计数
6. 追加 `knowledge/wiki/log.md` 日志

### Query

1. 读 `knowledge/wiki/index.md` 定位候选页
2. 读候选页，综合成答案
3. 若答案有独立价值，建议归档到 `analyses/`

### Lint（健康检查）

- 内链引用但无页面的概念（dangling links）
- 孤儿页（无入边）
- 跨页矛盾
- 被 ≥2 个 source 引用但还没独立页的概念
- 可以通过 web 查补的数据缺口

---

## 语言约定

- **指令文件**（CLAUDE.md / SCHEMA.md）：英文或中英混杂均可
- **wiki 页标题**：双语 `中文名 (English Name)`，如 `边际效用 (Marginal Utility)`
- **思想家/学派标题**：英文主，中文在括号
- **wiki 正文**：中文主，首次出现的英文术语保留
- **source 摘要页**：沿用原文语言

---

## 经济学分类法（打 tag 用）

- Microeconomics / Macroeconomics
- Monetary Economics / Fiscal Policy
- Behavioral Economics
- Development Economics
- International Economics / Trade Theory
- Political Economy
- Game Theory
- Information Economics
- Institutional Economics
- History of Economic Thought
