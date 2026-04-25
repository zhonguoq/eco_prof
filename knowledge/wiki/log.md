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
