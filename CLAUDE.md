# eco_prof — 量化投资 Agent 实验

## 项目结构

```
eco_prof/
├── CLAUDE.md                  # 本文件：项目说明书（非 Agent 人格）
│
├── .claude/                   # Agent 团队定义
│   ├── agents/eco-prof.md     # 主编排 Agent
│   ├── skills/                # 专业能力（工作流）
│   │   ├── wiki-query/        #   知识库查询
│   │   ├── lab-diagnose/      #   宏观诊断
│   │   ├── news-scan/         #   新闻扫描
│   │   └── eco-brief/         #   每日简报生成
│   └── commands/              # 用户命令入口
│
├── knowledge/                 # 知识库层 —— 理论、框架、原则
│   ├── SCHEMA.md              # 知识库契约
│   ├── CLAUDE.md              # 知识层规则
│   ├── raw/                   # 原始材料（immutable）
│   └── wiki/                  # 结构化知识体
│       ├── index.md           # 全局索引
│       ├── log.md             # 操作日志
│       ├── concepts/          # 经济概念（9 页）
│       ├── thinkers/          # 思想家（1 页）
│       ├── sources/           # 来源摘要（3 页）
│       └── analyses/          # 综合分析（3 页）
│
└── lab/                       # 实践层 —— 数据、工具、报告
    ├── CLAUDE.md              # lab 层规则
    ├── tools/                 # 数据采集脚本
    ├── data/                  # 原始数据（CSV / JSONL）
    ├── news/                  # 每日新闻
    ├── reports/               # 分析简报
    └── dashboard/             # FastAPI + React 可视化
```

## 核心原则

1. **单向引用**：knowledge/（真理源）→ lab/（实践）→ .claude/（协调），禁止反向写入
2. **原则驱动**：所有可重复的判断都抽象为原则，原则编码为工具，工具产出信号
3. **可追溯**：每条分析结论都要关联来源（数据、wiki 概念、原则卡片）
4. **渐进放权**：读 → 分析 → 建议 → 推荐 → 执行，逐级释放信任（L0–L5）
5. **人机协作**：关键决策（原则提取、交易执行）需用户人工确认

## Agent 团队一览

| Agent | 职责 | Skill |
|-------|------|-------|
| **eco-prof**（主编排） | 理解意图、路由专家、综合输出 | 所有 skill |
| Wiki Agent（知识管理） | 知识库查询、录入、原则提取 | wiki-query |
| Lab Agent（工具建模） | 跑诊断、回测、指标编码 | lab-diagnose |
| News Agent（新闻采集） | 新闻扫描、过滤、关联框架 | news-scan |
| Analysis Agent（分析） | 综合判断、投资建议、简报 | eco-brief |

## 常用命令

- `/eco-brief` — 生成今日宏观简报
- `/eco-chat` — 进入交互式分析模式

## 参考文档

- `knowledge/SCHEMA.md` — wiki 页格式、内链规范、工作流
- `knowledge/CLAUDE.md` — 知识层操作规则
- `lab/CLAUDE.md` — 实践层操作规则、脚本接口约定
