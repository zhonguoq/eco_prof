# lab/ — 实践层（数据、引擎、报告）

lab/ 是"理论落地"层，严格与 `knowledge/` 分离。它读 knowledge/wiki/ 的框架、跑数据、产出诊断与简报；**从不反向写入 knowledge/**（除非用户确认归档有长期价值的 analyses）。

## 目录

```
lab/
├── CLAUDE.md               # 本文件
├── scripts/                # 入口脚本（CLI）
│   ├── init_db.py               # 数据库初始化
│   ├── fetch_macro.py           # 宏观数据采集
│   ├── diagnose.py              # 宏观诊断
│   ├── render_diagnosis.py      # 宏观报告 HTML
│   ├── fetch_financials.py      # 微观数据采集
│   ├── dcf.py                   # DCF 估值
│   ├── factor_score.py          # 因子排名
│   ├── render_micro.py          # 微观报告 HTML
│   ├── record_judgment.py       # 记录判断
│   ├── list_judgments.py        # 查询判断
│   ├── update_judgment.py       # 更新判断
│   └── check_disconfirmation.py # 背离检测
├── engine/                 # 引擎代码（三库三引擎）
│   ├── db.py               #   DB 连接管理（get_db）
│   ├── macro/              #   宏观引擎：fetcher + diagnose + 规则
│   ├── micro/              #   微观引擎：fetcher + dcf + factors
│   └── meta/               #   元引擎：judgment + disconfirmation
├── chart_lib/              # 图表组件库（pyecharts）
├── db/                     # SQLite 数据库文件（gitignored）
├── data/                   # 原始数据（CSV / JSONL）
├── news/                   # 每日新闻
└── reports/                # 分析简报
```

---

## 核心原则

### 单向引用

```
knowledge/wiki (theory)
    ↓ referenced by
lab/engine/ (implements framework indicators)
    ↓ produces data
lab/reports/ + lab/db/
    ↓ archive highlights (user confirms)
knowledge/wiki/analyses/
```

- `lab/engine/` 引用 `knowledge/wiki/` 作为框架依据；禁止写入
- `lab/db/` 存 SQLite 数据库（三库分离：macro.db / meta.db / micro.db）
- `lab/reports/` 存分析快照；长期价值结论由 eco-prof 提议归档

### 命名约定

- 引擎代码：`engine/<domain>/<module>.py` —— 如 `engine/macro/diagnose.py`
- 入口脚本：`scripts/<action>.py` —— 如 `scripts/diagnose.py`
- 图表组件：`chart_lib/<domain>_charts.py` —— 如 `chart_lib/macro_charts.py`
- 数据文件：`data/<source>_<indicator>_<date>.csv`

---

## 脚本调用规范

所有 `scripts/` 下的入口脚本遵守：

1. **stdout 输出** — 对用户有用的信息（JSON 或文本）
2. **stderr 输出错误** — 非零退出码 + 错误说明
3. **幂等** — 重复运行不产生重复数据（INSERT OR REPLACE）
4. **参数用 argparse** — 参数名与 issue 契约一致
5. **sys.path hack** — `sys.path.insert(0, ...)` 确保 `from lab.engine.*` 能 import

---

## 工作流

### Fetch
1. 跑 `scripts/fetch_macro.py` → 写入 macro.db
2. 跑 `scripts/fetch_financials.py --code <code>` → 写入 micro.db
3. 数据以 SQLite 三库为核心存储

### Diagnose
1. 跑 `scripts/diagnose.py` → 读取 macro.db → 输出阶段判定 JSON
2. 跑 `scripts/check_disconfirmation.py` → 扫描 meta.db 的背离

### Report
1. 跑 `scripts/render_diagnosis.py` → 生成宏观 HTML 报告
2. 跑 `scripts/render_micro.py --code <code>` → 生成个股 HTML 报告
3. 跑 `scripts/render_micro.py --industry <name>` → 生成行业 HTML 报告
