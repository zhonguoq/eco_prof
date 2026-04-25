# eco_prof Agent Schema

本仓库根层契约：描述 eco_prof agent、其 skill 层、与 lab/knowledge 子系统的交互规则。知识库内部的页模板等在 `knowledge/SCHEMA.md`；lab 的命名与脚本规范在 `lab/CLAUDE.md`。

---

## eco_prof Agent — 设计原则与演进路径

自 2026-04 起本项目引入常驻私人宏观投资顾问 agent：`eco_prof`。定义在 `.claude/agents/eco-prof.md`，由 `/eco-brief`（定时简报）与 `/eco-chat`（对话讨论）两个入口唤起，也可被 `/schedule` 远程触发器定时调用。

### 分层与稳定性

| 层 | 位置 | 稳定性 | 说明 |
|---|---|---|---|
| 主 agent（壳） | `.claude/agents/eco-prof.md` | **稳定**——未来 multi-agent 化时是根 | 只写人设、原则、编排范式；**不**出现具体指标/数据源/文件路径 |
| 技能（可演进） | `.claude/skills/*/SKILL.md` | 契约稳定，内部实现可变 | `knowledge-query` / `lab-diagnose` / `news-scan` / `eco-brief` |
| 实现细节（变动频繁） | `lab/tools/*.py`、`lab/dashboard/backend/*.py`、`knowledge/wiki/**` | 自由演进 | lab 加信号、knowledge 加框架，都不影响上两层 |

**三条不变量**：
1. 主 agent prompt 不硬编码具体指标名（T10Y2Y）、数据源（FRED、Reuters）、文件路径（regime.py）。
2. Skill frontmatter 中的输入输出契约视为对主 agent 的公共 API；改契约要 bump 版本 + 在 `knowledge/wiki/log.md` 记录（前缀 `skill-contract-change | <skill-name>`）。
3. 思考框架由 `knowledge-query` skill 动态读入 `knowledge/wiki/`，wiki 改动主 agent 自动吃到最新，不把框架复制粘贴到 prompt。

### 产出与日志命名

- **每日简报**：`lab/reports/YYYY-MM-DD_eco-brief.md`
- **专题简报**：`lab/reports/YYYY-MM-DD_eco-brief-<focus-slug>.md`
- **（未来）小时扫描**：`lab/reports/YYYY-MM-DD-HHMM_eco-scan.md`
- **新闻存储**：`lab/news/YYYY-MM-DD.jsonl`（UTC 日期，`fetch_news.py` 幂等写入）
- **log 前缀**（追加到 `knowledge/wiki/log.md`）：
  - `eco-prof | daily-brief | <tl;dr 首句>`
  - `eco-prof | topic | <focus>`
  - `eco-prof | alert | <触发项>`
  - `eco-prof | scan | <关键变化>`（v0.3+）
  - `skill-contract-change | <skill> | v0.X → v0.Y`

### 与 lab/dashboard 的关系

lab/dashboard 的 APScheduler（每日 06:00 UTC 刷 FRED）**保持不动**，与 eco_prof **并行运行**：前者负责"数据新鲜"，后者负责"基于数据做综合分析"。eco_prof 的 `lab-diagnose` skill 只在需要时补刷数据，不代替 scheduler。

### 历史路径兼容

`lab/reports/2026-04-*.md` 等早期产出里引用的 `wiki/analyses/...` / `wiki/concepts/...` 等价于现路径 `knowledge/wiki/analyses/...` / `knowledge/wiki/concepts/...`。新产出必须用 `knowledge/wiki/...`。

### 演进路径

- **v0.1**（2026-04）：单主 agent + 4 个 skill。MVP 目标：跑通"定时 → 拉数+拉新闻 → 框架诊断 → 简报归档"闭环。
- **v0.1.1**（当前）：目录重构（根=eco_prof，knowledge/ 与 lab/ 并列）；skill heredoc 实化为 `lab/tools/` 脚本；`wiki-query` → `knowledge-query`；news_sources 清洗 + 中文源；`fetch_news` 加 `max_age_hours`。
- **v0.2**：multi-agent 化。`knowledge-query` skill 升级为 `knowledge-expert` subagent；新增 `macro-analyst`、`geopolitics-analyst`、`portfolio-strategist` subagent。主 eco-prof 收敛为纯 orchestrator。
- **v0.3**：告警与小时扫描。加 `/eco-scan` + 小时级 `/schedule`；新 skill `alert-check`。
- **v0.4**：Portfolio 只读接入。新 skill `portfolio-read`（券商 API）+ subagent `portfolio-strategist`。
- **v0.5**：`wiki-lint` 周任务。
- **v1.0**：白名单 + 人工 confirm 下的半自动 ETF 调仓。

**演进原则**：先加 skill，后拆 subagent；skill 契约改动优先 bump 版本，不悄悄破坏。
