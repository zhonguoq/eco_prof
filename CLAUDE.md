# eco_prof — 私人宏观投资顾问 Agent

本仓库根 = **eco_prof agent 的根**。三个并列子系统：

| 子系统 | 目录 | 作用 | 进入时读 |
|---|---|---|---|
| 知识库 | `knowledge/` | 经济学框架、概念、思想家、分析 | `knowledge/CLAUDE.md` |
| 实践层 | `lab/` | 数据、工具、简报 | `lab/CLAUDE.md` |
| Agent 系统 | `.claude/` | agent + skills + commands | `SCHEMA.md` §eco_prof |

## 启动自检（每次新对话）

1. 读 `SCHEMA.md` —— eco_prof agent 的契约、日志命名、演进路径
2. 读 `knowledge/wiki/index.md` —— 知识库全貌
3. 读 `knowledge/wiki/log.md` 尾部 —— 最近发生了什么

**仅在任务涉及**对应子系统时再进一步读它的 CLAUDE.md（按需，不提前加载）。

## 入口命令

- `/eco-brief [focus]` — 唤起 eco-prof 产出每日/专题宏观简报
- `/eco-chat` — 对话模式讨论宏观/投资

## 关于本项目的 pattern 背景

项目 fork 自一个通用的 "LLM Wiki Pattern"。散文说明存在 `knowledge/docs/llm-wiki-pattern.md`，非必读。
