# Issue draft: Phase 5 — Damodaran 数据 + L3 WACC + β re-lever

**依赖**：#30 合并（Phase 4 可并行）
**参考**：ADR-002 第 3、4、5、6 项
**标签**：`feature` + `ready-for-agent`

## 目标

把 WACC 从单一查表升级为完整公式，把 β 从自算改为行业 re-lever，把 gt 从固定 3% 改为 `min(Rf, GDP)`。效果：三场景估值接近 Damodaran / 券商标准。

## 验收标准

```bash
python lab/scripts/estimate_params.py --code 000725.SZ
# 输出包含：
#   Re (CAPM): X%
#   Rd (cost of debt): Y%
#   effective tax rate: Z%
#   D/V: A%, E/V: B%
#   WACC (L3): C%   ←  新
#   WACC (L2 sanity): D%   ← 原
#   Industry β (Damodaran, re-levered): E   vs   Self β: F
#   gt = min(Rf, GDP): G%  (country=CN, Rf=2.5%, GDP=4.5%)
```

## 实现清单

### Damodaran 数据

- [ ] 写 `lab/data/damodaran/README.md` —— **手动下载指南**
  - [ ] 列出所需 4 张表的 URL + 保存文件名：
    - ERP by country: `ctryprem.csv`
    - Betas by sector (US / Emerging Markets / China / Japan): `betas_us.csv` / `betas_em.csv` / `betas_china.csv` / `betas_japan.csv`
    - Tax rates by country: `taxrate.csv`
  - [ ] 每年 1 月更新一次的提示
- [ ] 首次 commit 样例 CSV（你先手动下载放进去）
- [ ] `engine/micro/damodaran.py`（新）
  - [ ] `load_erp(country="CN") → float`
  - [ ] `load_industry_beta(industry, market) → dict{"unlevered_beta", "levered_beta", "de_ratio", "tax_rate"}`
  - [ ] `load_country_tax(country) → float`
  - [ ] CSV 解析 + in-memory cache
  - [ ] 行业 key 别名映射 `INDUSTRY_ALIASES = {"Beverages—Wineries & Distilleries": "Beverage (Alcoholic)", ...}`

### WACC L3

- [ ] `engine/micro/wacc.py` 重写
  - [ ] `wacc_l3(code, conn) → dict{wacc, re, rd, tax, de_ratio, method, degradation_reason}`
    - Re = CAPM(Rf, β_relevered, ERP_by_country)
    - β_relevered = β_unlevered × (1 + (1-t) × D/E_company)；β_unlevered 从 Damodaran 取
    - Rd = `interest_expense / total_debt`；若缺 → 降级 `Rf + 2%`，记 reason
    - t = `income_tax / pretax_income`；pretax_income ≤ 0 → 降级 Damodaran 国家税率，记 reason
    - D/V = `total_liab / (total_liab + market_cap)`；market_cap 来自 securities 表
  - [ ] `wacc_l2(rf, beta, erp) → float`（旧 capm，保留作 sanity）
  - [ ] 保留 `default_industry` 作兜底

### β re-lever

- [ ] `engine/micro/beta.py`
  - [ ] 新增 `industry_relevered_beta(code, conn) → (beta, source)`
    - source = "damodaran" 或 "self-computed"
    - 先查 Damodaran 表，未命中 fallback `calc_beta`（自算）
  - [ ] 自算 `calc_beta` 不变，作为对照值保留

### gt 计算

- [ ] `engine/micro/wacc.py` 或 `scenarios.py` 增加：
  - [ ] `LONG_TERM_GDP = {"CN": 0.045, "US": 0.040, "HK": 0.040}`
  - [ ] `terminal_growth(country, macro_conn) → float`：`min(Rf_from_macro_db, GDP)`
  - [ ] `scenarios.py::resolve` 里 `"min(Rf,GDP)"` 引用改调此函数

### scenarios 集成

- [ ] `build_scenarios.py` 里 `"CAPM"` 引用改为调 `wacc_l3`
- [ ] scenario 的 `r` 字段存 L3 结果；同时写一列 `wacc_l2_sanity` 到 scenarios 表以便展示
- [ ] 若 L3 全部降级，`update_scenario.py` 允许手动覆写

### 测试

- [ ] `tests/test_damodaran.py`（新，mock CSV）
- [ ] `tests/test_wacc_l3.py`（新）
  - [ ] 正常场景计算正确
  - [ ] interest_expense 缺 → 降级 Rd=Rf+2%，degradation_reason 非空
  - [ ] pretax_income ≤ 0 → 降级到国家税率
  - [ ] 零负债 → D/V≈0，WACC 退化为 Re（等价 L2）
- [ ] `tests/test_beta_relevered.py`（新）
- [ ] `tests/test_terminal_growth.py`（新：CN gt=2.5% 因 Rf<GDP；US gt≈4%）

## 非范围

- render 层（Phase 6）
- Damodaran 数据下载自动化（永远手动）

## 风险

- Damodaran 行业英文 key 对不上 yfinance industry → 别名字典首次需人工对齐，预估 20-30 条
- Rf 来源是 `macro.db.DGS10` (美) 但中国 10Y 国债未必已入 macro.db → issue 里要先确认是否需要补宏观采集
