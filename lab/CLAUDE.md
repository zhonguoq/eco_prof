# lab/ — 实践层（数据、工具、报告）

lab/ 是"理论落地"层，严格与 `knowledge/` 分离。它读 knowledge/wiki/ 的框架、跑数据、产出诊断与简报；**从不反向写入 knowledge/**（除非用户确认归档有长期价值的 analyses）。

## 目录

```
lab/
├── CLAUDE.md               # 本文件
├── tools/                  # 数据/诊断/归档脚本
│   ├── fetch_us_indicators.py   # FRED 宏观指标
│   ├── fetch_yield_curve.py     # 收益率曲线
│   ├── fetch_news.py            # RSS 新闻采集
│   ├── news_sources.yaml        # RSS 源配置
│   ├── query_news.py            # 新闻查询 + 过滤 + 排序（供 news-scan skill）
│   ├── run_diagnosis.py         # 跑债务周期 + regime 诊断（供 lab-diagnose skill）
│   └── write_brief.py           # 简报归档 + 日志追加（供 eco-brief skill）
├── data/                   # 拉到的原始数据
│   ├── fred_snapshot_YYYYMMDD.csv
│   └── diagnosis_history.jsonl
├── news/
│   └── YYYY-MM-DD.jsonl    # 每日新闻（UTC 日期）
├── reports/
│   └── YYYY-MM-DD_eco-brief[-<focus-slug>].md
└── dashboard/              # FastAPI + React 可视化（APScheduler 每日 06:00 UTC 刷 FRED）
```

---

## 核心原则

### 单向引用

```
knowledge/wiki (theory) ──referenced by──→ lab/tools (implements framework indicators)
                                                ↓ produces data and reports
                                         lab/reports/
                                                ↓ archive highlights (user confirms)
                                         knowledge/wiki/analyses/ (permanent knowledge)
```

- `lab/tools/*.py` **引用** `knowledge/wiki/analyses/` 作为框架依据；**禁止写入** `knowledge/`
- `lab/data/` 存原始数据——中间产物
- `lab/reports/` 存分析快照；产生长期价值结论时由 eco-prof 提议归档到 `knowledge/wiki/analyses/`

### 命名约定

- 工具脚本：`tools/<description>.py` —— 如 `fetch_us_indicators.py`
- 数据文件：`data/<source>_<indicator>_<date>.csv` —— 如 `fred_yield_curve_20260412.csv`
- 报告文件：`reports/<YYYY-MM-DD>_<topic>.md` —— 如 `2026-04-12_us-debt-cycle-diagnosis.md`

---

## 脚本调用规范（skill 与脚本的接口）

所有被 skill 调用的脚本（`query_news.py` / `run_diagnosis.py` / `write_brief.py` 等）遵守：

1. **stdout 只输出 JSON**（结构化契约），供 LLM 解析后做渲染判断
2. **stderr 输出日志**（汇总行、错误）
3. **失败以非零退出码 + stderr 说明**，不静默
4. **幂等**：同日多跑不产生重复数据（按 hash 或 date 去重）
5. **参数用 argparse**，参数名和 skill 的契约字段一一对应

---

## 工作流

### Fetch
1. 跑 `lab/tools/` 的 fetch 脚本
2. 输出落 `lab/data/` 或 `lab/news/`
3. 追加一行 `knowledge/wiki/log.md`

### Analyze
1. LLM 读最新 `lab/data/` / `lab/news/`
2. 对照 `knowledge/wiki/analyses/` 里的框架做判断
3. 写诊断到 `lab/reports/`
4. 长期价值结论 → 提议归档到 `knowledge/wiki/analyses/`

### Alert
- 关键指标触达 `knowledge/wiki/analyses/` 定义的危险线 → 在简报顶加 ⚠️ 告警
- 告警行追加到 `knowledge/wiki/log.md`

---

## dashboard 说明

`lab/dashboard/backend/` 是纯函数模块，`regime.py` / `main.py` 的 `compute_regime` / `compute_diagnosis` 等函数被 `lab/tools/run_diagnosis.py` 直接 import。改动这些函数要保持签名稳定。
