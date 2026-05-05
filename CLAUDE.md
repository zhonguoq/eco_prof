# eco_prof — 量化投资 Agent 实验

三引擎架构（宏观引擎 + 元引擎 + 微观引擎），SQLite 数据存储，pyecharts HTML 报告，opencode CLI 交互。

## 项目结构

```
eco_prof/
├── CLAUDE.md                  # 本文件：开发环境说明书
│
├── .claude/                   # Agent 团队定义
│   ├── agents/eco-prof.md     # 产品应用 eco-prof 的人格定义
│   ├── skills/                # 7 个技能（wiki / macro / micro / news / brief / advise / review）
│   └── commands/              # 用户命令入口
│
├── knowledge/                 # 知识库层 —— 理论、框架、原则
│   ├── SCHEMA.md              # 知识库契约
│   ├── CLAUDE.md              # 知识层规则
│   ├── raw/                   # 原始材料（immutable）
│   └── wiki/                  # 结构化知识体
│       ├── index.md           # 全局索引
│       ├── log.md             # 操作日志
│       ├── concepts/          # 经济概念
│       ├── thinkers/          # 思想家
│       ├── sources/           # 来源摘要
│       └── analyses/          # 综合分析
│
├── lab/                       # 实践层 —— 数据、引擎、报告
│   ├── CLAUDE.md              # lab 层规则
│   ├── scripts/               # 入口脚本（CLI）
│   │   ├── init_db.py         #   数据库初始化
│   │   ├── fetch_macro.py     #   宏观数据采集
│   │   ├── diagnose.py        #   宏观诊断
│   │   ├── render_diagnosis.py #   宏观报告 HTML
│   │   ├── fetch_financials.py #   微观数据采集
│   │   ├── dcf.py             #   DCF 估值
│   │   ├── factor_score.py    #   因子排名
│   │   ├── render_micro.py    #   微观报告 HTML
│   │   ├── record_judgment.py #   记录判断
│   │   ├── list_judgments.py  #   查询判断
│   │   ├── update_judgment.py #   更新判断
│   │   └── check_disconfirmation.py # 背离检测
│   ├── engine/                # 引擎代码
│   │   ├── db.py              #   DB 连接管理
│   │   ├── macro/             #   宏观引擎（fetcher, diagnose, rules.json）
│   │   ├── micro/             #   微观引擎（fetcher, dcf, factors）
│   │   └── meta/              #   元引擎（judgment, disconfirmation）
│   ├── chart_lib/             # 图表组件库（pyecharts）
│   ├── db/                    # SQLite 数据库（gitignored）
│   ├── data/                  # 原始数据缓存
│   ├── news/                  # 每日新闻
│   └── reports/               # 分析简报
│
├── tests/                     # 测试（30 passing）
├── docs/agents/               # 工程管理模板（issue-tracker, triage-labels, domain）
└── PRD-001-system-architecture-v2.md
```

## 核心原则

1. **单向引用**：knowledge/ → lab/ → .claude/，禁止反向写入
2. **三引擎驱动**：宏观引擎（数据→诊断）→ 元引擎（判断→迭代）→ 微观引擎（估值→排名）
3. **原则驱动**：所有可重复判断抽象为原则，原则编码为指标，指标产出信号
4. **可追溯**：每条分析结论关联来源（数据、wiki 概念、原则卡片）
5. **渐进放权**：L0 读 → L1 分析 → L2 建议 → L3 推荐 → L4 执行
6. **人机协作**：关键决策（原则提取、交易执行）需用户确认

## 开发工作流

### 运行测试

```bash
python -m pytest tests/ -q
```

### 测试规范

- 只测外部行为，不测内部实现细节
- 每个 issue 一个测试文件，30 tests 全绿
- 新功能走 TDD：RED → GREEN → REFACTOR

### 新功能开发

1. 提 Issue（类型：bug / feature / iteration）
2. 标 Label（needs-triage → triage → ready-for-agent → ready-for-human）
3. TDD 实现：先写测试 → 实现 → lint → 提交 PR
4. AI 是调度器，不生成计算代码 — 所有算法在 `lab/engine/` 中固化

### 工程管理参考

- `docs/agents/issue-tracker.md` — GitHub issue 操作
- `docs/agents/triage-labels.md` — 5 个标准标签
- `docs/agents/domain.md` — 多上下文文档导航
