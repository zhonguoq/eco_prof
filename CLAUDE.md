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
│   │   ├── lab-model/         #   原则编码
│   │   ├── lab-backtest/      #   原则回测
│   │   ├── news-scan/         #   新闻扫描
│   │   ├── news-alert/        #   主动告警
│   │   ├── event-brief/       #   专题简报
│   │   ├── eco-brief/         #   每日简报
│   │   ├── eco-advise/        #   配置建议
│   │   ├── eco-trade/         #   模拟交易
│   │   ├── eco-review/        #   定期复盘
│   │   └── wiki-extract/      #   原则提取
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
    ├── scripts/               # 入口脚本（CLI）
    │   ├── init_db.py         #   数据库初始化
    │   ├── fetch_macro.py     #   宏观数据采集
    │   ├── diagnose.py        #   宏观诊断
    │   ├── render_diagnosis.py #   宏观报告 HTML
    │   ├── fetch_financials.py #   微观数据采集
    │   ├── dcf.py             #   DCF 估值
    │   ├── factor_score.py    #   因子排名
    │   ├── render_micro.py    #   微观报告 HTML
    │   ├── record_judgment.py #   记录判断
    │   ├── list_judgments.py  #   查询判断
    │   ├── update_judgment.py #   更新判断
    │   └── check_disconfirmation.py # 背离检测
    ├── engine/                # 引擎代码
    │   ├── db.py              #   DB 连接管理
    │   ├── macro/             #   宏观引擎
    │   │   ├── fetcher.py, diagnose.py, rules.json
    │   ├── micro/             #   微观引擎
    │   │   ├── fetcher.py, dcf.py, factors.py
    │   └── meta/              #   元引擎
    │       ├── judgment.py, disconfirmation.py
    ├── chart_lib/             # 图表组件库（pyecharts）
    │   ├── base.py, macro_charts.py, micro_charts.py, composite.py
    ├── db/                    # SQLite 数据库（gitignored）
    ├── data/                  # 原始数据（CSV / JSONL）
    ├── news/                  # 每日新闻
    └── reports/               # 分析简报
```

## 核心原则

1. **单向引用**：knowledge/（真理源）→ lab/（实践）→ .claude/（协调），禁止反向写入
2. **三引擎驱动**：宏观引擎（数据→诊断）→ 元引擎（判断→迭代）→ 微观引擎（估值→排名），串行依赖
3. **原则驱动**：所有可重复的判断都抽象为原则，原则编码为指标，指标产出信号
4. **可追溯**：每条分析结论都要关联来源（数据、wiki 概念、原则卡片）
5. **渐进放权**：读 → 分析 → 建议 → 推荐 → 执行，逐级释放信任（L0–L5）
6. **人机协作**：关键决策（原则提取、交易执行）需用户人工确认

## 三引擎架构

| 引擎 | 职责 | 数据源 | 输出 | 关联 Skills |
|------|------|--------|------|-------------|
| **宏观引擎** | FRED 数据采集 → 7 阶段诊断 → 宏观图表 | macro.db | 阶段判定、信号面板、HTML 报告 | lab-diagnose, lab-model, lab-backtest, eco-brief |
| **微观引擎** | 行情/财报采集 → DCF 估值 → 因子排名 → 微观图表 | micro.db | 估值、排名、HTML 报告 | —（scripts 直调） |
| **元引擎** | 判断记录 → 背离检测 → 规则迭代 | meta.db | 背离报告、判断历史 | —（scripts 直调） |
| **知识引擎** | wiki 查询 → 原则提取 → 框架引用 | knowledge/wiki/ | 概念解释、原则卡片 | wiki-query, wiki-extract |
| **新闻引擎** | RSS 采集 → 信号过滤 → 事件告警 | news/*.jsonl | 新闻简报、事件告警 | news-scan, news-alert, event-brief |
| **配置引擎** | 宏观建议 → 模拟交易 → 定期复盘 | — | 配置方案、交易记录、复盘报告 | eco-advise, eco-trade, eco-review |

## AI 自然语言调度规则（Slice 11）

当用户询问宏观/微观问题时，按以下流程调度：

1. **判断意图**
   - 宏观诊断 → 调用 `python lab/scripts/diagnose.py`
   - 个股估值 → 调用 `python lab/scripts/dcf.py --code <code>`
   - 行业排名 → 调用 `python lab/scripts/factor_score.py --industry <name>`
   - 查看背离 → 调用 `python lab/scripts/check_disconfirmation.py`
   - 生成报告 → 调用 `lab/scripts/render_diagnosis.py` 或 `render_micro.py`

2. **解析输出** — 标准输出为 JSON（结构化）或纯文本，用 Markdown 渲染给用户

3. **生成 HTML 报告** — 只在用户明确说"看图表 / 生成报告 / 可视化"时调用 chart_lib

4. **AI 是调度器，不生成计算代码** — 所有算法在 lab/engine/ 中固化，AI 只负责调用和展示结果

## 参考文档

- `knowledge/SCHEMA.md` — wiki 页格式、内链规范、工作流
- `knowledge/CLAUDE.md` — 知识层操作规则
- `lab/CLAUDE.md` — 实践层操作规则、脚本接口约定

## Agent skills

### Issue tracker

Issues and PRDs live as GitHub issues. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Multi-context — `CONTEXT-MAP.md` at the root points to per-context `CONTEXT.md` files. See `docs/agents/domain.md`.
