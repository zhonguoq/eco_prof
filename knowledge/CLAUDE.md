# knowledge/ — 经济学知识库（eco_prof 的"大脑"）

本目录是 eco_prof 的知识库层，**完全自治**：所有关于知识库的规则、页模板、工作流都在这里。lab/ 和 eco_prof agent 只读取本层内容，不反向改写 schema。

## 进入 knowledge/ 时的启动自检

1. 读 `knowledge/SCHEMA.md` —— 页模板、内链规范、语言约定、分类法、ingest/query/lint 工作流
2. 读 `knowledge/wiki/index.md` —— 当前知识库全貌
3. 读 `knowledge/wiki/log.md` 尾部 —— 最近发生了什么

## 目录

```
knowledge/
├── CLAUDE.md               # 本文件（入口）
├── SCHEMA.md               # 知识库 schema（契约）
├── docs/
│   └── llm-wiki-pattern.md # 通用 LLM Wiki 模式的背景散文
├── raw/                    # 原始来源（immutable，LLM 只读）
└── wiki/
    ├── index.md            # 全局索引
    ├── log.md              # 操作日志（append-only）
    ├── concepts/           # 经济学概念
    ├── thinkers/           # 思想家
    ├── schools/            # 学派
    ├── sources/            # 源文档摘要页
    └── analyses/           # 跨源综合分析 + eco_prof 长期价值结论归档
```

## 与 lab / eco_prof 的关系

- **lab** 是实践层。其脚本可**读取** `knowledge/wiki/analyses/` 作为框架依据（单向引用），但**从不写入** `knowledge/`。
- **eco_prof agent** 的简报（`lab/reports/`）若产生长期价值的结论，**由用户确认后**由人/eco-prof 归档到 `knowledge/wiki/analyses/`。
- 所有 eco-prof 的操作日志追加到 `knowledge/wiki/log.md`。

## pattern 背景

`docs/llm-wiki-pattern.md` 描述了本项目 fork 的通用 pattern。非必读——SCHEMA.md 已经把规则落地。想了解"为什么这么分层"时看。
