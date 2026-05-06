# Issue draft: Phase 4 — 多市场 fetcher（HK + US）

**依赖**：#30 合并
**参考**：ADR-002 第 7、8、9 项
**标签**：`feature` + `ready-for-agent`

## 目标

让 Phase 1-3 已跑通的 A 股流程对 `0700.HK` / `AAPL` 一样可用。所有下游脚本（estimate / build_scenarios / dcf）无需改动——fetcher 层吐出同构 dict。

## 验收标准

```bash
python lab/scripts/fetch_financials.py --code 0700.HK   # 港股
python lab/scripts/fetch_financials.py --code AAPL      # 美股
# 之后 estimate/build_scenarios/dcf 全走通
python lab/scripts/dcf.py --code 0700.HK --scenario all
```

## 实现清单

### Router

- [ ] `engine/micro/fetcher.py` 瘦身为 dispatcher
  - [ ] `_detect_market(code) → "A"|"HK"|"US"`（正则：`\.SH$|\.SZ$`→A, `\.HK$`→HK, 其余→US）
  - [ ] `fetch_financial_statements(code, conn, mock=None)` 按 market 调 sub-fetcher

### A 股 sub-fetcher（抽取既有逻辑）

- [ ] `engine/micro/fetcher_a.py`
  - [ ] 移入现有 `_aksymbol` + wide 表抽取逻辑
  - [ ] `FIELD_MAP_A` 字段字典（列名映射）
  - [ ] 扩展抽 10 字段：`operating_cf, capex, cash, total_liab, revenue, net_income, equity, pretax_income, income_tax, interest_expense`
  - [ ] 利润表接口：`ak.stock_profit_sheet_by_report_em`

### HK sub-fetcher（新）

- [ ] `engine/micro/fetcher_hk.py`
  - [ ] `FIELD_MAP_HK` dict，value 支持 `str | list[str]`（别名兜底）
  - [ ] 调 `ak.stock_financial_hk_report_em(stock, symbol, indicator="年度")` 三次（资产负债表/利润表/现金流量表）
  - [ ] **长表 pivot**：`df[df.STD_ITEM_NAME==name].AMOUNT.iloc[0]`；别名逐个尝试
  - [ ] 按 `REPORT_DATE` 分组成年度行

### US sub-fetcher（新）

- [ ] `engine/micro/fetcher_us.py`
  - [ ] `FIELD_MAP_US` dict（也是中文 STD_ITEM_NAME 值，因为东财表头是中文）
  - [ ] 调 `ak.stock_financial_us_report_em(stock, symbol, indicator="年报")` 三次
  - [ ] pivot 同 HK

### 测试

- [ ] `tests/test_fetcher_hk.py`（新，mock DataFrame）
  - [ ] 长表 pivot 正确抽值
  - [ ] 别名兜底：map 给 `["购建固定资产...", "购买固定资产..."]`，后者命中时也返回
  - [ ] 缺字段时返回 NULL 不报错
- [ ] `tests/test_fetcher_us.py`（新，同上）
- [ ] `tests/test_fetcher_router.py`（新）
  - [ ] `000725.SZ` → fetcher_a
  - [ ] `0700.HK` → fetcher_hk
  - [ ] `AAPL` → fetcher_us

## 非范围

- Damodaran 行业映射在 Phase 5
- `securities` 表已在 Phase 3 建立；此阶段只确认 yfinance 能正确识别 HK/US ticker

## 风险

- 东财长表 STD_ITEM_NAME 对港股/美股可能因公司不同而用词有差异 → FIELD_MAP 的别名 list 会逐步补
- 小概率单个字段找不到 → 记录到日志，不 abort
