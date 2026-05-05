# PRD-001: eco_prof 系统架构 v2 — 宏观/微观/元三引擎设计

## Problem Statement

当前 eco_prof 仓库是一个 AI 直觉构建的原型系统，存在根本性问题：

1. **AI 替代了设计决策** — 宏观引擎的增长率阈值 2.0%、通胀阈值 3.0%、regime 四象限分类（Goldilocks/Stagflation 等）都是 AI 猜测的默认值，用户没有参与任何一个设计决策点。结果：系统用不起来，因为不是用户的。
2. **知识层单一** — 整个知识库 100% 是 Ray Dalio，schools/ 目录为空，缺乏其他学派交叉验证。
3. **微观估值完全空白** — 无 DCF、无因子打分、无财报数据 pipeline，无法支撑个股决策。
4. **缺乏迭代闭环** — 没有记录"判断→结果→修正"的机制。原则卡片 P001-P007 是从书里抄来的，不是从用户自己交易经验提炼的。
5. **数据管理混乱** — 宏观时序数据散落在几十个 CSV 文件中，难以高效查询和关联。
6. **前端维护成本高** — 现有 FastAPI + React 仪表盘需要维护前端代码，用户明确表示不愿意。

## Solution

构建一个**三引擎架构**的系统，核心原则：**人做设计决策，AI 做最后一公里加速**。

三引擎分工：

| 引擎 | 职责 | 输出 |
|------|------|------|
| **宏观引擎** | 基于 Dalio 七阶段模型诊断当前债务周期位置 | 阶段结论 + 原始信号 |
| **微观引擎** | DCF 估值 + 行业因子打分 | 估值区间 + 行业排名 |
| **元引擎** | 记录判断→检测背离→触发迭代→修正原则 | 偏差分析 + 原则更新 |

所有有明确公式的计算（DCF、PE、因子等）由预构建的传统代码执行，AI 负责调度和呈现。交互方式为 CLI 对话 + Python 生成的 HTML 报告（pyecharts），零前端代码维护。

## User Stories

### 宏观引擎

1. As a 投资者, I want to run a daily macro diagnosis from the CLI, so that I know the current debt cycle stage without opening a dashboard.
2. As a 投资者, I want to see the 6 signal dimensions (yield curve shape, CPI, employment, consumer sentiment, manufacturing index, growth-vs-rate) individually, so that I can form my own judgment rather than relying on a black-box stage label.
3. As a 投资者, I want the macro engine to output both a stage reference (Dalio phases 1-7) and raw signal data, so that I can cross-validate the AI's suggestion against my own reading.
4. As a 投资者, I want the yield curve shape classifier to include trajectory (previous shape), so that phases 1/6/7 (all "normal curve" but different contexts) can be distinguished.
5. As a 投资者, I want the stage 3 (Top) detection rule to be: yield curve inverted + employment rising from trough + CPI > 3%, so that the first automated rule matches my own mental model.
6. As a 投资者, I want all macro thresholds to be configurable in a single rules file (not hardcoded in Python), so that I can tune them without editing code.
7. As a 投资者, I want the macro engine to generate an HTML report via pyecharts when I ask "what's the macro picture", so that I can visualize yield curve history and stage timeline without maintaining a frontend framework.
8. As a 投资者, I want the FRED data fetch to be a single unified script writing to SQLite, so that I don't have scattered CSV files for every indicator.
9. As a 投资者, I want the fetch script to be idempotent (re-running doesn't duplicate data), so that I can safely run it on a cron schedule.
10. As a 投资者, I want the macro engine to record each diagnosis as a "macro judgment" in the meta database, so that the meta engine can track whether my predictions were correct.

### 微观引擎

11. As a 投资者, I want to run DCF valuation for any A-share stock from the CLI, so that I can compare intrinsic value vs current price.
12. As a 投资者, I want to provide growth rate and discount rate assumptions when running DCF, so that the assumptions reflect my judgment rather than AI defaults.
13. As a 投资者, I want the DCF calculator to be a fixed Python function (not AI-generated each time), so that computation is consistent and token-efficient.
14. As a 投资者, I want to see the DCF sensitivity table (varying growth rate × discount rate), so that I understand how sensitive the valuation is to my assumptions.
15. As a 投资者, I want to run a factor score for stocks in the same industry (PE/PB/ROE/PS ranking), so that I can compare relative valuation within a peer group.
16. As a 投资者, I want to view a "valuation vs price" comparison chart for a stock over time, so that I can see when the stock entered undervalued/overvalued territory.
17. As a 投资者, I want financial data for A-shares (via AKShare) and US/HK stocks (via yfinance), so that all three markets are covered.
18. As a 投资者, I want to compose arbitrary charts via natural language — e.g. "show me the PE band for 600519 alongside the industry average PE" — so that I can flexibly explore data without predefined dashboards.

### 元引擎

19. As a 投资者, I want every macro judgment and micro valuation to be automatically recorded in a judgments table, so that I build a track record of my investment decisions.
20. As a 投资者, I want each judgment to include a concrete, time-bound prediction (e.g. "CPI will fall below 3% within 6 months"), so that the system can objectively verify correctness later.
21. As a 投资者, I want the system to automatically detect when new data disconfirms a past judgment, so that I'm alerted to revisit my assumptions.
22. As a 投资者, I want a weekly review command that lists "judgments closed this week with deviation analysis", so that I can systematically learn from mistakes.
23. As a 投资者, I want each iteration cycle to result in a concrete rule update (e.g. "stage 3 threshold changed from CPI 3% to 2.5%"), so that the system becomes more aligned with my experience over time.
24. As a 投资者, I want to manually mark a judgment as "wrong" even without automated detection, so that I can trigger iteration based on qualitative insight that numeric data may not capture.
25. As a 投资者, I want the meta database to track the full lineage: judgment → deviation → iteration → updated rule, so that I can audit my own decision evolution.

### 系统与基础设施

26. As a 投资者, I want all data stored in SQLite databases (macro.db, meta.db, micro.db), so that queries are fast and the system has zero operational overhead.
27. As a 投资者, I want to interact with the system via natural language in the opencode CLI, so that I don't need to learn a custom query language.
28. As a 投资者, I want the chart library to be a maintained set of reusable components (not one-off generated HTML), so that charts get richer over time without rewriting.
29. As a 投资者, I want fetched data to persist even after a repo teardown, so that historical macro data isn't lost during refactoring.
30. As a 投资者, I want the system architecture to support phased rollout: macro first, then meta, then micro, so that I start getting value from day one.

## Implementation Decisions

### Architecture

- **Three engines, one controller**: Macro and Micro engines produce signals (not decisions). The user (via Meta engine) integrates signals into investment decisions. This is the "Engine C" architecture confirmed in design sessions.
- **AI role**: Scheduler and translator — calls pre-built formula code (DCF, factor calculation, signal classification), never generates algorithmic code at runtime.
- **Interaction model**: opencode CLI for natural language queries. Python generates HTML reports (via pyecharts) for visualization. Zero frontend framework code.

### Database Schema

Three SQLite databases under `lab/data/db/`:

**macro.db** — Unified time-series storage (replacing scattered CSVs):
- `series(series_id TEXT, date TEXT, value REAL, PRIMARY KEY(series_id, date))` — all FRED indicator data
- `series_meta(series_id TEXT PRIMARY KEY, name, unit, freq, source, last_updated)` — indicator metadata

**meta.db** — Meta engine records:
- `judgments(id TEXT PRIMARY KEY, type TEXT, timestamp, stage, signals JSON, confidence, prediction, verification_window, actual_outcome, context, user_id)` — atomic unit of iteration
- `iterations(id TEXT PRIMARY KEY, judgment_id, trigger_type, deviation_analysis, old_rule, new_rule, timestamp)` — principle evolution log

**micro.db** — Financial data (phase 2):
- `financials(stock_code, report_date, revenue, net_income, operating_cf, total_assets, total_liabilities, equity)`
- `prices(stock_code, date, open, high, low, close, volume)`
- `factors(stock_code, date, pe, pb, roe, ps, market_cap, industry)`

### Macro Engine Design

- **Framework**: Dalio's 7-phase debt cycle model (removing the AI-invented 2×2 growth-inflation regime quadrant)
- **Output**: Stage reference (phases 1-7) + raw signals (6 dimensions)
- **6 signal dimensions**: yield curve shape (with trajectory), CPI YoY, unemployment rate, consumer sentiment, manufacturing index, nominal growth vs nominal rate
- **Stage classification strategy**: Progressive rule-building. Start with user-defined rules for phase 3 (Top) and phase 5 (Beautiful Deleveraging), use simplified fallback for others. User adds rules as disconfirmations accumulate.
- **Configurable thresholds**: All thresholds live in a TOML rules file (`lab/rules/macro.toml`), not hardcoded. The file contains per-signal thresholds, signal-to-stage mapping rules, and phase metadata. User edits this file when the meta engine triggers an iteration. AI reads from this file at runtime — never writes to it without explicit user confirmation.
- **News scanning**: Kept as optional enrichment, not part of core diagnosis. RSS fetcher writes to local JSONL.
- **Layer 3 — Long-term structural risk** (retained from current codebase, thresholds to be iterated by user):
  - Total debt/GDP (warning ≥ 300%, danger ≥ 350%)
  - Federal debt/GDP (warning ≥ 100%, danger ≥ 130%)
  - USD trade-weighted index trend
  - These are calculated alongside the 7-stage diagnosis but reported as a separate risk overlay, not integrated into stage classification

### 7 Phase Definitions

Each phase is defined in the user's own words from design sessions, paired with observable signal characteristics:

**Phase 1 — Early (早期)**
> User's definition: "发生在整个社会货币和信贷稀缺的时候, 人们基于借助货币和信贷工具, 来盘活整个社会"
- Signals:利率低位（fedfunds < 2.5%）, 曲线正常正斜率, 信贷总量从低位扩张, CPI < 3%, 就业率从高位回落（改善）, 全要素生产率回升

**Phase 2 — Bubble (泡沫期)**
> User's definition: "发生在整个社会的货币和信贷过剩, 但是生产率已经开始停滞或者难以上升了, 整个社会的风气也开始脱实向虚，人们开始推崇炒某类资产，货币和信贷从一个加速社会资源流通的工具, 逐渐成为目的本身"
- Signals: 利率上升中（央行踩刹车）, 曲线趋平或接近倒挂, CPI > 3%, 消费者信心高位, 全要素生产率增速放缓, 资产通胀>商品通胀（P005信号）, 债务/GDP持续上升

**Phase 3 — Top (顶部)**
> Rule confirmed by user: 收益率曲线倒挂（10Y-2Y < 0）+ 就业率从底部开始回升 + 消费者信心从高位回落 + CPI仍 > 3%
- Yield curve inverted as the primary classifier; auxiliary signals confirm the transition

**Phase 4 — Depression (萧条)**
> User's definition: "人们的信心和产业被某个因素摧毁, 所有一切都在下跌，人们陷入恐慌，对未来失去信心。做什么都是亏，陷入恶性循环"
- Signals: 曲线牛陡（央行紧急降息）, 利率急速下降, HY信用利差飙升（> 8%）, 消费者信心断崖（< 60）, 违约率上升, CPI从高位回落（通缩压力）, 制造业指数 < 45, 资产价格全面下跌

**Phase 5 — Beautiful Deleveraging (美丽去杠杆)**
> User's definition: "虽然信贷在消失, 但是央行通过债务货币化的手段, 使得债务货币化的速度基本上等于信贷消失的速度"
- Signals: 利率近零（fedfunds < 0.5%）, 曲线极平趴在低位, 名义增速≈名义利率（债务/GDP稳定）, QE / 非常规货币政策, 信贷收缩速度≈债务货币化速度

**Phase 6 — Pushing on a String (推绳子)**
> From Dalio's framework, confirmed by user: 货币政策进一步宽松但效果有限（"推绳子"——向前推绳子不能使绳子直）, 经济反应迟钝, 需要更直接的财政刺激配合
- Signals: 利率近零, 曲线极平, 常规降息无效, 信贷传导机制失灵

**Phase 7 — Normalization (正常化)**
> From Dalio's framework, confirmed by user: 债务/收入比逐步下降至可持续水平, 信贷活动恢复正常, 经济重回增长轨道
- Signals: 曲线恢复正斜率, 利率从近零缓慢抬升, 信用利差正常水平, 资产价格稳定上涨, 消费者信心逐步修复

### Micro Engine Design (Phase 2)

- **DCF Calculator**: Fixed Python function `dcf_value(cash_flows, growth_rate, discount_rate, terminal_growth)`. Input assumptions from user, output valuation range + sensitivity table.
- **Factor Scorer**: Fixed Python function `factor_rank(stock_list, factor_weights)`. Industry-relative scoring for PE, PB, ROE, PS.
- **Data sources**: AKShare (A-shares financials), yfinance (US/HK price + basic financials)
- **AI role**: Parse user intent → call the right fixed function → format results → generate visualization

### Chart Library

- **Stack**: pyecharts (wraps ECharts 5)
- **Structure**: `lab/chart_lib/` with modular components:
  - `base.py` — global theme, branding, layout defaults
  - `macro_charts.py` — yield curve history, stage timeline, signal dashboard
  - `composite.py` — chart combiner that takes a list of chart specs → renders single HTML page
- **Design principle**: Components are reused and composable. No one-off chart code. Over time the library grows richer (annotations, zoom, crosshair) without rewriting.

### Implementation Order

Phase 0 ("cleanup & foundation"):
1. Move FRED API key from `settings.local.json` to environment variable (`FRED_API_KEY`)
2. Create `lab/data/db/` directory structure
3. Define the TOML rules file schema (thresholds, signal-to-stage mappings, phase names)

Phase 1 ("macro first") — **Milestone: first automated debt cycle diagnosis from CLI**:
1. Create macro.db + meta.db schemas, migrate existing FRED data from CSVs into SQLite
2. Rewrite FRED fetch as single `fetch_macro.py` → writes to macro.db (idempotent)
3. Build `run_diagnosis.py` with progressive 7-stage classification, records judgment to meta.db
4. Build chart_lib (macro_charts.py + composite.py) — yield curve, CPI vs GDP, stage timeline, signal summary
5. CLI query flow: "what stage are we in" → run_diagnosis → chart → HTML report

Phase 2 ("meta loop"):
1. Build deviation detection: periodic SQL query checking `judgments.prediction vs actual_outcome`
2. Alert user when discrepancy exceeds configurable threshold
3. Build weekly review command
4. Connect iteration output back to rule configuration file

Phase 3 ("micro engine"):
1. Create micro.db schema
2. Integrate AKShare + yfinance data fetch
3. Build DCF calculator module
4. Build factor scorer module
5. Natural language query → chart composition flow

### Code Cleanup

- **Current repo (Phase 0)**: Keep `knowledge/` (wiki content) and `lab/data/` (existing CSV data for migration). Teardown everything else.
- **`regime.py`**: Remove entirely (the regime quadrant was AI hallucination confirmed by user).
- **`main.py` / dashboard/**: Remove. Chart generation moves to chart_lib + HTML reports.
- **`trading/`**: Remove. Paper trading will be redesigned when micro engine is ready.
- **`.claude/`**: Review and restructure to match the new three-engine architecture.
- **Existing fetch scripts**: Rewrite as single unified fetch_macro.py.

## Testing Decisions

- **Test philosophy**: Only test external behavior, not implementation details. A test should verify that given input X, the output Y matches expected behavior, not that internal variables have certain values.
- **Macro signal classification tests**: Given known historical data (e.g. 2008 yield curve, CPI, employment), verify the classifier produces the expected phase. These tests serve as regression guards when thresholds change.
- **DCF calculator tests**: Fixed known inputs → known outputs. Test edge cases (zero growth, negative cash flows, extreme discount rates).
- **Factor scorer tests**: Given a mock universe of stocks with known factor values, verify ranking is correct.
- **Chart generation tests**: Not tested (visual output). The underlying data functions that feed the charts ARE tested.
- **SQLite CRUD tests**: Verify write/read/update operations against an in-memory SQLite database (separate from production dbs).
- **Prior art**: No existing tests in this codebase — this will be the first test infrastructure.

## Out of Scope

- **Real-time data / WebSocket feeds** — All data is batch-fetched on a schedule or on demand.
- **Automated trading execution** — The system produces signals for human decision. No API integration with brokerages.
- **Machine learning models** — No ML. All signals are deterministic rule-based.
- **Multi-currency / FX focus** — USD-centric macro. China indicators added but limited to annual data from World Bank.
- **Portfolio optimization** — No mean-variance or risk-parity optimization in scope. Asset allocation is rule-based tilt.
- **Mobile app / web frontend** — Zero frontend code. HTML reports are generated Python-side, viewed in browser.
- **Real-time alerting (push notifications)** — Alerts are surfaced in CLI or generated HTML, not pushed to phone/email.
- **Crowd-sourced data / alternative data** — No scraping of social media, satellite data, etc.

## Further Notes

- **The repo name stays `eco_prof`** — it's a personal investment "professor" / "professional" system.
- **Secrets management**: FRED API key (currently in plaintext in `settings.local.json`) must be moved to environment variables. This is a Phase 0 cleanup task.
- **Knowledge layer**: The `knowledge/wiki/schools/` directory is intentionally left empty for now — first get the system running with Dalio, then ingest other schools as second-order iteration.
- **OpenCode integration**: The system is designed to be operated through opencode's CLI interface. All scripts output JSON to stdout (following the lab CLAUDE.md conventions) so opencode can parse and render results naturally.
- **"最后一公里" principle**: AI does format conversion, data plumbing, and chart rendering. The user sets assumptions, defines rules, and makes decisions. This line must be defended in every feature addition.
- **全要素生产率 data sourcing**: For Phase 2 detection (bubble phase, productivity stagnation), 全要素生产率 is referenced conceptually. FRED series for US (e.g. MFP, TFP) will be added as an optional signal. For China TFP data, sourcing TBD — this signal may initially be omitted for China diagnosis until a reliable source is identified.
- **Manufacturing index sourcing**: ISM Manufacturing PMI (US) via FRED series NAPM. China Caixin Manufacturing PMI TBD — AKShare may have this. This is a Phase 1 implementation detail to resolve during fetch script development.
