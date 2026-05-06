# Issue draft: Phase 1-3 — 微观引擎 v2 A 股可用版

**参考**：ADR-002 / 微观引擎 v2
**标签**：`feature` + `ready-for-agent`
**类型**：feature
**估计**：中等（3 个 phase 合并，约 500-800 LOC 新增/改动）

## 目标

让 A 股用户能走完"代码 → 三场景 DCF → 每股价 vs 现价判读"的完整流程。港股/美股留作 Phase 4。

## 验收标准（用户视角）

```bash
# 1. 拉数据（A 股 + yfinance securities 表）
python lab/scripts/fetch_financials.py --code 000725.SZ

# 2. 估计原始参数（CAGR / 自算 β / CAPM WACC）
python lab/scripts/estimate_params.py --code 000725.SZ
# 输出：CAGR=X%, 自算 β=Y, CAPM-L2=Z%（L3 在 Phase 5 之后）

# 3. [AI 跑 WebSearch 拿分析师共识]

# 4. 生成 3 场景
python lab/scripts/build_scenarios.py --code 000725.SZ \
    --analyst-high 0.12 --analyst-mid 0.10 --analyst-low 0.08
# 输出：base/bull/bear 三套已解析参数表，写入 scenarios 表

# 5. 用户在对话里可调
python lab/scripts/update_scenario.py --code 000725.SZ --scenario bull --N 7

# 6. 出结果
python lab/scripts/dcf.py --code 000725.SZ --scenario all
# 输出：三场景表 + 每股内在价值 + 现价对比 + Buffett 分级标签
```

## 实现清单

### Phase 1: DCF 内核升级

- [ ] `engine/micro/dcf.py`
  - [ ] `dcf_value` 签名改为 `(fcf_list, growth_rates: List[float], terminal_growth, discount_rate, base_fcf_method="mean3")`
  - [ ] 新增 `_normalize_base(fcf_list, method)`，支持 `latest/mean3/mean5/median5`
  - [ ] `base_fcf ≤ 0` 抛 `ValueError("DCF 不适用：归一化 FCF 为非正值")`
  - [ ] `growth_rates` 列表长度决定 N（不再有单独的 `growth_years` 参数）
- [ ] `tests/test_dcf_variable_growth.py`（新）
  - [ ] `[0.10]*5` 等价于原 `growth_rate=0.10, growth_years=5`
  - [ ] `[0.15, 0.12, 0.10, 0.08, 0.05]` 递减增长率分段
  - [ ] `mean3` 归一化：`fcf_list=[100, 200, 120, 80, 130]` → base=110
  - [ ] 负 FCF 抛 ValueError
- [ ] 保留 `batch_dcf`、`equity_value`、`sensitivity_matrix`，内部适配新签名

### Phase 2: scenarios 表 + resolver

- [ ] `engine/db.py` schema 加：
  ```sql
  CREATE TABLE IF NOT EXISTS scenarios (
    code TEXT, scenario_name TEXT,
    g1 REAL, N INTEGER, gt REAL, r REAL,
    base_fcf_method TEXT, updated_at TEXT,
    PRIMARY KEY (code, scenario_name)
  );
  ```
- [ ] `engine/micro/scenarios.py`（新）
  - [ ] `SCENARIO_TEMPLATES` 硬编码 base/bull/bear 三套引用
  - [ ] `resolve(code, templates, analyst=None) → dict`：把字符串引用翻成数字
    - `"CAGR"` → 调 `growth.cagr(fcf_list)`
    - `"Rf"` → 查 `macro.db` DGS10 最近值
    - `"CAPM"` → 调 `wacc.capm(rf, self_beta)`（L2，L3 待 Phase 5）
    - `"min(Rf,GDP)"` → 查 Rf + `LONG_TERM_GDP[country]`
    - `"分析师共识_高/中/低"` → 读 `analyst` 参数；未传则降级 `CAGR ± 3%`
- [ ] `scripts/build_scenarios.py`（新）
  - [ ] argparse: `--code`, `--analyst-high`, `--analyst-mid`, `--analyst-low`
  - [ ] 调 resolver，写三行到 `scenarios` 表
  - [ ] stdout 打印三场景参数表
- [ ] `scripts/update_scenario.py`（新）
  - [ ] argparse: `--code --scenario --g1 --N --gt --r`（皆可选）
  - [ ] UPDATE 指定字段
- [ ] `scripts/dcf.py` 重构
  - [ ] 移除 `--growth/--growth-years/--terminal-growth/--discount`
  - [ ] 新增 `--scenario base|bull|bear|all`
  - [ ] 从 scenarios 表读参数 → 调 dcf_value
- [ ] `tests/test_scenarios.py`（新）
  - [ ] resolver 正确翻译 `"CAGR"`、`"Rf"`、`"CAPM"`、`"min(Rf,GDP)"`
  - [ ] analyst 传入时按值，未传时 `± 3%` 降级
  - [ ] `build_scenarios.py` 写入三行
  - [ ] `update_scenario.py` 只改指定字段

### Phase 3: yfinance + securities + 每股价 + 判读

- [ ] `requirements.txt` 加 `yfinance`
- [ ] `engine/db.py` schema 加：
  ```sql
  CREATE TABLE IF NOT EXISTS securities (
    code TEXT PRIMARY KEY,
    market TEXT, name TEXT, industry TEXT,
    shares_outstanding REAL, currency TEXT,
    current_price REAL, updated_at TEXT
  );
  ```
- [ ] `engine/micro/yf_fetcher.py`（新）
  - [ ] `fetch_securities(code) → dict`：调 `yf.Ticker(code).info`，取 8 字段
  - [ ] `upsert_securities(conn, code, mock=None)`：入库
- [ ] `scripts/fetch_financials.py` 增加：采完三表后调 `upsert_securities`
- [ ] `engine/micro/dcf.py` 扩展 `equity_value`：增加返回 `per_share = equity / shares_outstanding`
- [ ] `scripts/dcf.py --scenario all` 输出升级：
  ```
  场景   每股内在价值   vs 现价   安全边际
  Bear   X.XX           −Y.Y%    −Y.Y% ✗
  Base   ...
  Bull   ...
  [标签] 现价 vs base 分级：🟢 低估 / ⚪ 合理 / 🔴 高估
  ```
- [ ] `tests/test_yf_fetcher.py`（新，mock yfinance.Ticker）
- [ ] `tests/test_per_share_valuation.py`（新）
  - [ ] equity_value 正确分母
  - [ ] Buffett 分级阈值 0.7/0.9/1.1/1.3 边界

### 测试规范

- 所有网络调用（yfinance、akshare）用 mock 注入
- 已有 30 passing tests 不能破；新增 test case 预计 +15
- 跑：`python -m pytest tests/ -q`

### 文档

- [ ] 更新 `src/skills/micro/SKILL.md`：反映 v2 命令链（fetch → estimate → build_scenarios → [人工改] → dcf --scenario all）
- [ ] 更新 `CLAUDE.md` 脚本列表（新增 build_scenarios, update_scenario）
- [ ] 在 `README` 或 `lab/CLAUDE.md` 加"Damodaran 数据占位说明"（Phase 5 才需要，此 PR 预留文件夹 `lab/data/damodaran/`）

## 非范围（显式排除）

- 港股、美股 fetcher（Phase 4）
- Damodaran 数据下载与 L3 WACC（Phase 5）
- render_micro.py HTML 报告（Phase 6）
- 行业 β re-lever（Phase 5 一起做）
- H-model 三段式 DCF（未来）

## 风险

- yfinance 国内访问不稳 → 需要 VPN；测试全 mock 规避
- A 股 industry 字段 yfinance 给英文（"Electronic Components"），与后续 Damodaran key 对齐延后到 Phase 5

## 自测流程

```bash
python -m pytest tests/ -q              # 全绿
python lab/scripts/fetch_financials.py --code 000725.SZ
python lab/scripts/estimate_params.py --code 000725.SZ
python lab/scripts/build_scenarios.py --code 000725.SZ --analyst-mid 0.10
python lab/scripts/dcf.py --code 000725.SZ --scenario all
# 肉眼核查：输出包含三场景、每股价、现价对比、分级标签
```
