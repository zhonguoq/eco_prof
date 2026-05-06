# ADR-002 / 微观引擎 v2 —— DCF 三场景 + 多市场 + 严肃参数

**状态**：Accepted
**日期**：2026-05-06
**取代**：`src/skills/micro/SKILL.md` v1 的参数超市流程

## 背景

micro 技能 v1 只支持 A 股、单一增长率、极简 WACC 查表，距离"严肃行业估值"有 5 大缺口（参见对话记录）。本 ADR 钉下 16 个设计决策，作为 v2 实现的唯一真相源。

## 决策清单

### 1. DCF 结构：两段式 A + 逐年列表 C 同时支持
- 内核统一为 `growth_rates: List[float]` + `terminal_growth` + `discount_rate`
- 两段式 `(g1, N)` 等价于 `[g1]*N`；内核无分支

### 2. 参数呈现：scenario bundles（硬编码 base/bull/bear）
- 三套场景预设，用户整套选或在对话里临时覆盖（不持久化到文件）
- 否决"零件超市"多参数独立组合（组合爆炸、制造虚假精度）

### 3. WACC 严肃度：总是算 L3（完整 WACC）
- 公式：`WACC = E/V·Re + D/V·Rd·(1-t)`
- L2（纯 CAPM）作为 sanity check 对照展示
- 数据缺失时**自动降级 L2，并在输出中明确说明降级原因**

### 4. Damodaran 作为行业基础数据
- **手动下载** CSV 到 `lab/data/damodaran/`（需指南）
- 覆盖：ERP（按国家，月更）、行业 β（年更）、D/E、有效税率、现成 WACC sanity check
- yfinance 的英文 industry 字段直接作为 Damodaran 查表 key；维护少量别名映射

### 5. β 来源：行业 β re-lever 优先，自算 β 作 fallback
- `β_levered = β_unlevered × (1 + (1-t)·D/E)`
- 行业在 Damodaran 表里**未命中**时，降级为 `beta.py` 自算 β
- 自算 β 永远作为"对照值"展示，供人工审视异常

### 6. 永续增长率：`gt = min(Rf, 长期GDP)`
- `LONG_TERM_GDP` 在 `wacc.py` 硬编码国家 dict：CN=4.5%、US=4.0%、HK=4.0%
- Rf 从 `macro.db` 读（DGS10 美 / 中国 10Y 国债）
- 三场景里 gt 基本一致，bear 额外 −0.5%

### 7. 股票识别：强制代码输入
- 形如 `000725.SZ` / `0700.HK` / `AAPL`
- market 从后缀正则推断
- **不做**名称→代码查询

### 8. 多市场 fetcher：router + 三个 sub-fetcher
- `fetcher.py` 只做 dispatch
- `fetcher_a.py` / `fetcher_hk.py` / `fetcher_us.py` 各自负责形状转换
- A 股宽表、港股美股长表（pivot by STD_ITEM_NAME）
- FIELD_MAP 为**代码内 dict**（不走外置 json），支持 `list` 候选值做别名兜底

### 9. 数据分工：yfinance + akshare
| 数据 | 源 |
|---|---|
| 历史三表（CF/BS/IS） | akshare（覆盖 15+ 年） |
| `securities` 表（shares/industry/currency/mcap） | yfinance（三市场统一） |
| 当前股价（估值对比） | yfinance currentPrice |
| 历史价格（自算 β） | akshare |

### 10. `shares_outstanding` 策略：每次 fetch 刷新
- 存 `securities` 表单一字段，每次 `fetch_financials.py` 调用时覆写
- 不做历史切片（DCF 只看当前）

### 11. Scenario 参数解析：AI 编排，脚本只收数字
- AI 跑 WebSearch 拿分析师共识 → 调 `build_scenarios.py --analyst-high 0.12 --analyst-mid 0.10 --analyst-low 0.08`
- 脚本 resolve 字符串引用（`"CAGR"`、`"Rf"`、`"CAPM"`）为实际数字
- 输出落盘到 `micro.db` 的 `scenarios` 表

### 12. 分析师数据缺失时的降级
- `high = CAGR + 3%`，`low = CAGR − 3%`（绝对值加减）
- 只填 mid：`high = mid + 3%, low = mid − 3%`

### 13. scenarios 存储：SQL 表
- `scenarios` 表列：`code, scenario_name(base/bull/bear), g1, N, gt, r, base_fcf_method, updated_at`
- `dcf.py` CLI 简化为 `--code X --scenario base|bull|bear|all`，不再接受原始参数 flag

### 14. 基础 FCF 归一化：三年均值
- `base_fcf = mean(fcf_list[-3:])`
- 可选 flag `--base-fcf latest|mean3|mean5|median5`
- **负值则报错**拒绝估值（拒绝 DCF 不适用的场景）

### 15. 最终判读：三场景对照表 + Buffett 30% 带单标签
- 表格列：scenario / 每股内在价值 / vs 现价 / 安全边际
- 单标签基于 `price / base`：
  - < 0.7 🟢 深度低估
  - 0.7–0.9 🟢 低估
  - 0.9–1.1 ⚪ 合理
  - 1.1–1.3 🔴 高估
  - > 1.3 🔴 深度高估
- 安全边际 30% 硬编码

### 16. 落地顺序 & 测试策略
- **Phase 1-3 合并为一次 PR**（A 股可用版，含 dcf 内核 + scenarios + yfinance 每股价）
- **Phase 4-6 独立 issues**（HK/US fetcher、Damodaran+L3、3 场景渲染）
- **TDD 节奏**：每 phase 先红后绿
- 所有 fetcher 测试 mock DataFrame，不调真实网络

## 后果

### 正向
- 估值严肃性大幅提升（接近 Damodaran / 券商标准）
- 三市场通用，一套代码
- 场景可重放、可 diff、可版本化

### 代价
- 新依赖：yfinance
- 手动维护 Damodaran CSV（季度下载）
- A 股 industry 对接 Damodaran 的别名字典需首次人工对齐

## 未决（留作未来 ADR）
- 归一化 FCF margin（方案 E）在周期股场景的引入
- H-model（三段式）是否补回
- 场景文件版本化（若 SQL 不够用，导出成 git-tracked json）
