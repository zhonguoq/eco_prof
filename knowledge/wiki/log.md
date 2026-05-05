# Wiki Log

操作日志，按时间倒序追加。每条记录格式：`## [YYYY-MM-DD] 操作类型 | 标题`

---

## [2026-04-19] lab-upgrade | 宏观环境监测系统（从债务周期仪表盘扩展）

将现有的「美国债务周期仪表盘」升级为**持久运行的宏观监测系统**，把 wiki 中的多层周期理论自动化。

**数据层扩展** — `lab/tools/fetch_us_indicators.py`
- 新增 5 个 FRED 系列：GDPC1（实际GDP）、UNRATE（失业率）、UMCSENT（消费者信心）、DTWEXBGS（美元指数）
- 新增 2 个衍生序列：RGDP_YOY（实际GDP同比）、CPI_YOY（CPI同比）
- 总计 18 个指标系列覆盖三层诊断

**引擎层** — `lab/dashboard/backend/regime.py`（新建）
- 增长-通胀四象限模型（Goldilocks / Overheating / Stagflation / Deflation）
- 可配置阈值（增长 2%，通胀 3%）
- 资产配置倾向映射（股/长债/商品黄金/现金，±2 刻度）
- 长期结构性风险评级（总债务/GDP、联邦债务/GDP、美元指数）

**调度层** — `lab/dashboard/backend/scheduler.py`（新建）
- APScheduler 集成到 FastAPI lifespan
- 每日 06:00 UTC 自动拉取 FRED 数据
- 启动时自动补齐今日诊断日志
- 诊断结果追加到 `lab/data/diagnosis_history.jsonl`（LLM 可直接读取）

**API 层** — `lab/dashboard/backend/main.py`
- 新增 `GET /api/regime`、`GET /api/diagnosis/history`、`POST /api/refresh`
- 扩展 SERIES_META（新增 Group 5：增长-通胀 regime 指标）
- 修复既有 bug：货币政策空间提示的 bps 计算（fedfunds → fedfunds × 100）

**前端层** — `lab/dashboard/frontend/src/`
- 新组件：RegimePanel（四象限可视化 + 资产倾向条形图 + 长期风险列表）
- 新组件：RegimeTimeline（历史 regime 变迁时间线）
- App.tsx 新增 4 个 KPI 卡片和 5 个图表（CPI/实际GDP/失业率/美元指数/消费者信心）
- Header 新增「刷新数据」按钮

**Wiki 层**
- 新建分析页：`wiki/analyses/宏观环境判断与投资指引框架.md`——记录三层诊断 + 四象限 + 资产映射的设计思路
- 更新 `wiki/index.md` 统计

**当前诊断（2026-04-19 首次记录）：**
- Layer 1（债务周期）：早期健康 / 正常化（5 信号全 ok）
- Layer 2（Regime）：**Stagflation** — 实际GDP 1.99%（略低于 2% 阈值）+ CPI 3.32%（高于 3% 阈值）
- Layer 3（长期）：总债务/GDP 342.5%（警戒），联邦债务/GDP 122.6%（警戒）
- 资产倾向：现金 ++，商品/黄金 +，股票 --，长期国债 -

**启动方式：**
```
python3 -m uvicorn lab.dashboard.backend.main:app --port 8000
cd lab/dashboard/frontend && npm run dev
```

---

## [2026-04-12] ingest | Principles for Dealing with the Changing World Order (Ray Dalio, 2020)

- 新增 source 摘要：`wiki/sources/dalio-changing-world-order-2020.md`
  - 7 条核心论点：三力驱动、帝国模板、储备货币机制、货币三阶段、内部秩序崩溃顺序、美中博弈、个人应对策略
  - 历史跨度：500 年，覆盖荷兰/英国/美国/中国帝国周期
- 新增概念页面（4 个）：
  - `wiki/concepts/世界秩序大周期-big-cycle-of-world-order.md`：三大子周期叠加框架、典型阶段、帝国对比表
  - `wiki/concepts/帝国兴衰决定因素-determinants-of-empire-power.md`：八大指标及滞后顺序、美中对比（2020）
  - `wiki/concepts/储备货币周期-reserve-currency-cycle.md`：货币体系三阶段、英镑→美元交接案例、当前美元处境
  - `wiki/concepts/内部秩序周期-internal-order-cycle.md`：财富差距→民粹→货币化→革命的完整机制、历史案例
- 更新 `wiki/thinkers/ray-dalio.md`：补充第5大贡献（世界秩序研究），新增4个概念链接，sources 扩展
- 更新 `wiki/index.md`：来源数 2→3，页面数 10→15，新增4个概念条目和1个来源条目

---

## [2026-04-12] ingest | Lab Dashboard Architecture

- 新增 raw 文档：`raw/lab-dashboard-architecture.md`
- 新增 source 摘要：`wiki/sources/lab-dashboard-architecture.md`
  - 记录 lab 层完整技术栈（fetcher / FastAPI / React + ECharts）
  - 关键约束：echarts-for-react@3 必须搭配 ECharts 5.x
  - 已知局限：DSR 系列有误、无定时任务、无中国数据、无告警
- 更新 `wiki/index.md`：来源数 1→2，页面数 8→9

## [2026-04-12] lab-setup | 创建债务周期仪表盘（React + FastAPI）

- 新增 `lab/dashboard/backend/main.py`：FastAPI 后端，提供 `/api/snapshot`、`/api/series/{id}`、`/api/diagnosis` 三个接口
- 新增 `lab/dashboard/frontend/`：React + Vite 5 + ECharts + Tailwind 前端
  - 顶部：周期阶段诊断面板（五维信号 + 综合判断）
  - KPI 卡片行：7 个关键指标实时值 + 颜色状态
  - 三组图表：收益率曲线/利率走廊/GDP 增速 vs 利率、债务健康度、领先预警信号
- 启动方式：`python3 -m uvicorn lab.dashboard.backend.main:app --port 8000` + `npm run dev`（端口 5173）

## [2026-04-12] lab-setup | 创建 lab/ 层 + 美国指标数据拉取

- 创建 `lab/tools/`、`lab/data/`、`lab/reports/` 目录
- 新增工具脚本：`lab/tools/fetch_us_indicators.py`
  - 使用 FRED API 拉取 11 个美国宏观指标系列（1995 年至今）
  - 衍生序列：名义 GDP 同比增速、10Y-2Y 利差（备用计算）
  - 输出：13 个 CSV 文件 + `fred_snapshot_20260412.csv` 快照汇总
- 新增分析报告：`lab/reports/2026-04-12_us-debt-cycle-diagnosis.md`
  - 对照《债务周期阶段判断框架》三组核心指标进行诊断
  - 初步判断：美国处于"顶部后早期调整阶段"，曲线从倒挂恢复，利率从高位下行，信用市场尚无恐慌信号
  - 主要风险：总债务/GDP ~343%（越过 300% 警戒线），滞胀风险待观察

---

## [2026-04-12] analysis | 债务周期推导与阶段判断框架

基于对话中的深度讨论，新建两个分析页面：

- `analyses/债务周期的内在逻辑-从生产率到泡沫.md`
  从第一性原理推导：货币初衷→工具异化→泡沫自我强化→崩溃→去杠杆。
  补充两个关键修正：①资产抵押品的结构性放大机制；②泡沫期 CPI 往往不高（钱流入资产市场而非商品市场）。

- `analyses/债务周期阶段判断框架.md`
  实用诊断工具：三组核心指标（债务健康度、货币政策空间、名义增速 vs 利率）、收益率曲线形态解读、综合诊断表、三条快速检查清单。

**更新：** `wiki/index.md`（统计：1来源，8页面）

---

## [2026-04-11] ingest | Principles For Navigating Big Debt Crises — Ray Dalio (2018)

处理书籍 Part 1（原型大债务周期）。

**新建页面（5个）：**
- `sources/dalio-big-debt-crises-2018.md` — 来源摘要
- `concepts/大债务周期-big-debt-cycle.md` — 七阶段模板、四根杠杆、两种类型
- `concepts/美丽去杠杆化-beautiful-deleveraging.md` — 核心概念，成功条件与历史案例
- `concepts/通缩型萧条-deflationary-depression.md` — 机制、政策工具、历史案例
- `concepts/通胀型萧条-inflationary-depression.md` — 外币债务、货币危机、超级通胀
- `thinkers/ray-dalio.md` — 人物页：贡献、著作、方法论、争议

**更新：** `wiki/index.md`（统计：1来源，6页面）

---

## [2026-04-11] init | Wiki 初始化

初始化个人经济学知识库。

- 创建目录结构：`raw/`、`wiki/concepts/`、`wiki/thinkers/`、`wiki/schools/`、`wiki/sources/`、`wiki/analyses/`
- 创建 `wiki/index.md`、`wiki/log.md`
- 创建 schema 文档 `SCHEMA.md`

---

## [2026-04-12] query | 补充收益率曲线概念页

**新建页面（1个）：**
- `concepts/收益率曲线-yield-curve.md` — 完整概念页：定义、五种曲线形态、两大关键利差（10Y-2Y / 10Y-3M）、三大理论机制（预期理论、流动性溢价、银行信贷传导）、美国历史衰退记录、与大债务周期各阶段的对应关系、局限性与注意事项

**更新：** `wiki/index.md`（统计：2来源，10页面）

## [2026-04-19 19:35] eco-prof | daily-brief | 美国宏观出现典型三层背离：债务周期 5 信号全绿但增长-通胀 regime 已进入 Stagflation
- 归档: lab/reports/2026-04-19_eco-brief.md
- regime: Stagflation · debt_stage: 早期健康 / 正常化
- alerts: yes (soft) — 三层背离 + UMCSENT 56.6 danger + 总债务/GDP 342.5% 逼近 350%

## [2026-04-25 13:03] eco-prof | daily-brief | 美国宏观三层背离持续：债务周期 5 信号全绿但增长-通胀 regime 处 Stagflation
- 归档: lab/reports/2026-04-25_eco-brief.md
- regime: Stagflation · debt_stage: 早期健康 / 正常化
- alerts: yes — UMCSENT 53.3 danger + 伊朗战争能源冲击 + 总债务/GDP 342.5%

## [2026-04-25 14:19] eco-prof | phase-1 | 重建 Agent 团队基础设施完成
- 新建: `CLAUDE.md`（root）— 项目说明书
- 新建: `.claude/agents/eco-prof.md` — 主编排 Agent 定义
- 新建: `.claude/skills/wiki-query/SKILL.md` — 知识库查询
- 新建: `.claude/skills/lab-diagnose/SKILL.md` — 宏观诊断
- 新建: `.claude/skills/news-scan/SKILL.md` — 新闻扫描
- 新建: `.claude/skills/eco-brief/SKILL.md` — 每日简报生成
- 新建: `.claude/commands/eco-brief.md` — `/eco-brief` 命令
- 新建: `.claude/commands/eco-chat.md` — `/eco-chat` 命令
- 背景: 8 个文件覆盖 4 个 Agent 角色；CLAUDE.md 采用"项目说明书"策略避免编码污染
- 下一步: Phase 2 — 原则提取与编码

## [2026-04-25 14:30] eco-prof | phase-2 | 完成首批 5 条原则提取 + P005 指标编码
- 新建: `.claude/skills/wiki-extract/SKILL.md` — 原则提取工作流
- 新建: `knowledge/wiki/principles/` + P001-P005 原则卡片（全部确认 active）
- 新建: `knowledge/wiki/principles/index.md` — 原则索引
- 编码: P005 资产通胀背离指标 — SP500 拉取 + 衍生计算 + regime 诊断信号
  - `fetch_us_indicators.py`: 新增 SP500 系列、SP500_YOY、ASSET_INFLATION_DIVERGENCE 衍生计算
  - `regime.py`: 新增资产通胀背离 aux_signal（>10% warning, >20% danger）
  - `main.py`: 新增 SERIES_META 元数据
- P005 阈值: divergence > 10% → warning, > 20% → danger

## [2026-04-25 15:00] eco-prof | phase-2.2 | 编码 B4 + A6 原则，新增 P006/P007 卡片
- 新建: `.claude/skills/lab-model/SKILL.md` — 原则编码工作流
- 编码 B4: `regime.py:classify_yield_curve_shape()` — 六形态分类器（正常/趋平/倒挂/牛陡/超平/恢复）
- 编码 A6: `regime.py:classify_rate_phase()` — 利率水平+方向 9 状态分类器
- 新增 P006: 收益率曲线六形态映射债务周期阶段（medium confidence）
- 新增 P007: 利率水平+方向决定货币政策阶段（medium confidence）
- 建立双向追溯: 每条原则 card 标记 encoded_in，代码中标注原则 ID
- 原则总计: 7 条（全部 active + 全部已编码）

## [2026-04-25 15:20] eco-prof | phase-2.3 | 完成原则回测验证闭环

## [2026-04-25 21:00] eco-prof | phase-3.1 | 完成新闻深度分析系统

新闻告警引擎上线：
- 新建 `lab/tools/run_alerts.py` — 原则驱动告警引擎（12 条硬信号规则 + 7 条软信号规则）
- 新建 `lab/data/alerts.jsonl` — 告警历史存储
- 新建 `.claude/skills/event-brief/SKILL.md` — P1 告警触发时自动生成专题简报
- 更新 `.claude/skills/news-scan/SKILL.md` — 加入原则关联 + 告警引擎调用 + 结构化输出格式
- 更新 `.claude/skills/eco-brief/SKILL.md` — Step 4 替换为告警引擎调用，简报模板加入结构化告警区块
- 更新 `.claude/agents/eco-prof.md` — 新增 news-alert/event-brief 技能路由 + 自主唤醒序列

当前告警（2026-04-25）：
- 🔴 P1: ALERT-WAR（地缘冲突—伊朗战争）+ ALERT-FED（央行相关新闻关键词）
- 🟡 P2: ALERT-DEBT2（债务/GDP 342.5%警戒）+ ALERT-STAG（Stagflation持续）+ ALERT-SENTIMENT（UMCSENT 53.3）+ ALERT-CPI/ALERT-RESERVE/ALERT-SHADOW（新闻关键词）

首次 event-brief 输出：`lab/reports/2026-04-25_brief-iran-war-geopolitical-risk.md`

## [2026-04-25 21:30] eco-prof | phase-3.2 | 创建投资建议引擎

- 新建 `.claude/skills/eco-advise/SKILL.md` — 结构化资产配置建议引擎
  - 基准配置：基于 regime.py 四象限 ASSET_TILTS
  - 告警调整因子：P1 ±1, P2 ±0.5，支持叠加
  - 三时间框架：短期(1-3m) / 中期(3-12m) / 长期(1-3y)
  - 置信度评分：基于信号一致性/数据时效/框架覆盖/历史对标四因素
  - 输出：人类可读报告 + 结构化 JSON
- 首次建议输出：`lab/reports/2026-04-25_eco-advise.md`（四层背离下的防御配置）
- 核心判断：基准 Stagflation 防御配置，但 4/30 GDP 可能推翻此判断

## [2026-04-25 21:45] eco-prof | phase-3.3 | 中国市场扩展 — 数据管道 + Wiki 知识

**数据层**：
- 新建 `lab/tools/fetch_cn_indicators.py` — 中国宏观指标拉取
  - 7 个 World Bank API 免费系列：GDP 增速、CPI、政府债务/GDP、经常账户/GDP、税收/GDP、失业率、人口
  - 1 个 FRED 系列：DEXCHUS（USDCNY 汇率 6.82）
  - 输出：8 个 CSV + cn_snapshot_YYYYMMDD.csv 快照
  - 当前数据：中国 GDP 4.98%（2024）、CPI 0.22%（近通缩）、USDCNY 6.82

**Wiki 知识**：
- 新建 `概念/中国债务周期-china-debt-cycle.md` — 国有银行+房地产+LGFV 驱动，与美国模板的三点根本差异
- 新建 `概念/A股市场特征-ashare-market-characteristics.md` — 散户主导/政策敏感/高波动，P001-P005 修正说明
- 新建 `概念/中美周期联动-china-us-cycle-linkage.md` — 四大传导通道 + 当前最异步相位
- 当前 wiki 页面总数：19（含 7 原则卡片）

**下一步**：Phase 3.4 — eco-review 定期复盘技能

## [2026-04-25 22:00] eco-prof | phase-3.4 | 创建定期复盘技能

- 新建 `.claude/skills/eco-review/SKILL.md` — 定期复盘工作流
  - 按周/月/事件驱动三种频率触发
  - 回溯判断 vs 实际走势 → 修正原则
  - 输出结构化复盘报告到 `lab/reports/`

## [2026-04-25 22:00] eco-prof | phase-3 | 全部完成

Phase 3 所有子阶段完成：

| 子阶段 | 完成内容 |
|-------|---------|
| 3.1 新闻深度分析 | run_alerts.py 告警引擎 + event-brief 专题简报 + news-scan 增强 |
| 3.2 投资建议引擎 | eco-advise 结构化配置建议（含置信度/时间框架/告警调整） |
| 3.3 多市场扩展 | 中国数据管道（8 个系列）+ 3 个 wiki 概念页 |
| 3.4 定期复盘 | eco-review 复盘工作流 |

**进入 Phase 4：模拟交易系统**

## [2026-04-25 22:30] eco-prof | phase-4.1 | 模拟交易系统上线

- 新建 `lab/trading/paper/account.py` — 模拟账户（现金/持仓/P&L/交易记录，持久化到 JSON）
- 新建 `lab/trading/paper/executor.py` — tilt→权重→ETF 持仓转换和执行
- 新建 `lab/trading/paper/tracker.py` — NAV 快照记录、绩效追踪
- 新建 `.claude/skills/eco-trade/SKILL.md` — 模拟交易执行工作流
- 首次交易：Stagflation 配置已执行

当前持仓（2026-04-25）：
| ETF | 份额 | 权重 | 对应资产 |
|-----|------|------|---------|
| SPY | 0 | 0% | 股票（Stagflation → 0%）|
| TLT | 101 | 9% | 长期国债（tilt -1）|
| GLD | 151 | 36% | 商品/黄金（tilt +1，告警调整 +1 → +2）|
| BIL | 556 | 55% | 现金（tilt +2，告警调整 +0.5 → +2.5 归一化后 55%）|
| **总计** | | **100%** | 现金剩余 $182 |

## [2026-04-25 23:00] eco-prof | 全系统集成验证

所有 8 个技能已到位：
1. wiki-query（知识查询）
2. wiki-extract（原则提取）
3. lab-diagnose（宏观诊断）
4. lab-model（原则编码）
5. lab-backtest（原则回测）
6. news-scan（新闻扫描 + 原则关联 + 告警集成）
7. news-alert → event-brief（框架告警 + 专题简报）
8. eco-advise（投资建议）
9. eco-trade（模拟交易执行）
10. eco-review（定期复盘）
11. eco-brief（每日简报，整合上面所有流程）

项目状态：Phase 1-4.1 完成，等待用户确认评估后继续
- 新建: `.claude/skills/lab-backtest/SKILL.md` — 回测工作流
- 新建: `lab/tools/backtest_principles.py` — 回测引擎（支持 P001/P002/P005）
- P001 回测: 精确率 75%，平均领先 17.3 个月 → SUPPORTED
  - 2022-2024 深度倒挂 783 天尚未验证（当前 open case）
- P002 回测: Growth>Rate 时债务下降仅 42% → WEAK，confidence 降为 medium
  - 修正理解：方向正确但非因果，Rate>Growth 侧更可靠（69%）
- P005 回测: 数据不足（SP500 从 2016 起，最大 divergence 仅 7.64%）→ INCONCLUSIVE
- 已更新 P001/P002/P005 卡片添加 backtest_findings 字段
- Phase 2 闭环完成（提取→编码→回测）

## [2026-04-25 21:40] eco-prof | daily-brief | 滞胀+2P1告警，三层背离持续，伊朗战争主导地缘风险，消费者信心53.3极度低迷

## [2026-05-02 21:30] eco-prof | daily-brief | REGIME 切换：Stagflation → Overheating，Q1 GDP 上修至 2.66% 翻转了象限判断
- 归档: lab/reports/2026-05-02_eco-brief.md
- regime: Overheating · debt_stage: 早期健康 / 正常化
- 关键事件: 4/29 FOMC（维持利率不变）, 4/30 ECB 决议, SP500 收于 7230
- alerts: yes — 8 条（2 P1 / 6 P2）
