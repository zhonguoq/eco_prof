# Issue draft: Phase 6 — render_micro.py 三场景 HTML 报告

**依赖**：#30 + Phase 4 + Phase 5（全部合并后）
**参考**：ADR-002 第 15 项
**标签**：`feature` + `ready-for-agent`

## 目标

把现有 `render_micro.py` 升级为"三场景估值报告"HTML，用 pyecharts 组件呈现。决策者不需要看 stdout，直接看 HTML 即可形成判断。

## 验收标准

```bash
python lab/scripts/render_micro.py --code 000725.SZ --dcf
# 生成 lab/reports/micro_000725.SZ_YYYYMMDD.html
# 浏览器打开后包含 5 个区块（见下）
```

## 报告布局（5 区块）

1. **头部卡片**
   - 公司名 + 代码 + 市场
   - 当前价 + 货币
   - 分级标签（🟢低估 / ⚪合理 / 🔴高估，Buffett 30% 带）
   - 基于 `base` 场景的相对差

2. **三场景对照表**

   | scenario | g₁ | N | gt | r | base FCF | 每股内在价值 | vs 现价 | 安全边际 |
   |---|---|---|---|---|---|---|---|---|
   | Bear | ... | 3 | ... | ... | ... | HK$380 | −18% | ✗ −18% |
   | Base | ... | 5 | ... | ... | ... | HK$521 | +13% | ✓ |
   | Bull | ... | 7 | ... | ... | ... | HK$680 | +47% | ✓ |

   表格下方：**行内注释**列降级信息（如 "Rd 降级：利息费用缺失"）。

3. **参数来源透明**（卡片行）
   - CAGR, 自算 β, Damodaran 行业 β (re-levered), Rf, ERP, WACC-L3, WACC-L2 sanity
   - 分析师共识（若有，标 source = "WebSearch"）

4. **历史 FCF + 基础 FCF 归一化** — pyecharts bar chart
   - 过去 5-10 年 FCF 柱状图
   - 红色横线标 `base_fcf`（三年均值）

5. **敏感性热力图** — pyecharts heatmap
   - `base` 场景附近 `g₁ ± 3%` × `r ± 2%` 9-25 格热力图
   - 每格数字 = 每股内在价值；颜色按 vs 现价百分比

## 实现清单

- [ ] `chart_lib/micro_charts.py` 新增
  - [ ] `scenario_table(scenarios, current_price, shares) → pyecharts Table`
  - [ ] `valuation_badge(ratio) → HTML snippet`（颜色分级）
  - [ ] `fcf_history_chart(fcf_list, base_fcf) → Bar`
  - [ ] `sensitivity_heatmap(base_scenario, fcf_list, shares) → HeatMap`
- [ ] `scripts/render_micro.py` 重构
  - [ ] argparse: `--code`, `--dcf`（默认 on），`--industry`（行业报告分支）
  - [ ] 读 `scenarios` 表 + `securities` 表 + `financial_statements` 表
  - [ ] 用 pyecharts `Page` 组装 5 区块
  - [ ] 输出 `lab/reports/micro_<code>_<date>.html`
- [ ] `tests/test_render_micro.py`
  - [ ] 给定 mock 三场景 + securities 数据 → 生成 HTML 不报错
  - [ ] 分级标签阈值边界正确（0.7/0.9/1.1/1.3）
  - [ ] 降级原因（如果 scenarios 表有）出现在表格注释

## 非范围

- 行业对比（factor_score）的渲染保持原样
- 报告国际化（只输出中文）
- 交互式参数调节（静态 HTML）

## 风险

- pyecharts Table 组件排版控制能力弱 → 可能需降级到 HTML 原生 `<table>` + inline CSS
- 敏感性热力图 25 格 × 每格 DCF 计算，单只股票 ~50ms 可接受
