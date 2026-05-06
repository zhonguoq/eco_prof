---
name: micro
description: 微观引擎 v2 — DCF 三场景估值 + 行业因子排名
---

授权级别：L1

用户需要 DCF 估值、行业因子排名、估值 vs 价格对比时触发。

## 执行流程

### 0. 前置条件

**务必确认用户提供了股票代码。** 如果是中文名（如"京东方A"），先转换为 A 股代码（如 `000725.SZ`）。

根据代码后缀推断市场（ADR-002 决策 #7）：
- `.SZ` / `.SH` → `CN`
- `.HK` → `HK`
- 无后缀（如 `AAPL`）→ `US`

**首次运行时先 fetch 数据：**

```bash
python lab/scripts/fetch_financials.py --code <股票代码> --country <CN/HK/US>
```

这会从 akshare/yfinance 拉取历史三表 + securities（股价/行业/股本），存入 `micro.db`。

---

### 1. 自动参数估计（L3 WACC）

运行参数估计脚本（ADR-002 决策 #3、#4、#5、#6）：

```bash
python lab/scripts/estimate_params.py --code <股票代码> --country <CN/HK/US>
```

输出展示 **L3 WACC 完整分解**：

| 参数 | 说明 |
|------|------|
| Re（资本成本） | Rf + β_industry_relevered × ERP |
| Rd（债务成本） | interest_expense / total_liabilities（缺失则降级 Rf+2%）|
| D/V、E/V | 资产负债表 + 市值 |
| β 来源 | Damodaran 行业 β re-lever（优先）；自算 β 作对照值（ADR #5）|
| ERP | Damodaran ctryprem.csv（按国家）（ADR #4）|
| gt = min(Rf, GDP) | Rf 来自 macro.db；GDP 硬编码 CN=4.5%、US/HK=4.0%（ADR #6）|

⚠️ 若 `interest_expense` / `pretax_income` 缺失，自动降级为 L2（CAPM），
输出中说明降级原因（ADR-002 决策 #3）。

**记录以下估计值用于步骤 3：**
- WACC L3（= 折现率 r）及 L2 sanity check 值
- gt（终端增长率）及计算依据
- CAGR（历史 FCF 复合增长率）

---

### 2. WebSearch：分析师共识增长率

用 WebSearch **仅获取分析师增长率共识**（不搜行业 WACC，WACC 已由 L3 自动计算）：

```
<股票名称> <股票代码> 分析师 预测 增长率 2026 2027
```

整理为三个数值，对应 ADR-002 决策 #11 的三场景参数：
- **high**（乐观预测 → bull 场景）
- **mid**（中性预测 → base 场景）
- **low**（保守预测 → bear 场景）

若搜不到分析师数据，使用降级公式（ADR-002 决策 #12）：
- `high = CAGR + 3%`、`mid = CAGR`、`low = CAGR − 3%`

---

### 3. 向用户确认三个参数（精简版）

展示以下参数，请用户确认（ADR-002 决策 #2 否决"参数超市"）：

| 参数 | 自动估计值 | 来源 |
|------|-----------|------|
| 分析师增长率区间 | high=X%, mid=Y%, low=Z% | WebSearch / CAGR±3% 降级 |
| 估算年限 N | 5（bull=7, bear=5） | ADR 硬编码默认 |
| WACC | L3=X.XX%（L2 sanity=Y.YY%）| Damodaran + 财报自动计算 |

用户可 override 任何参数；若对 WACC 不满意可手动输入覆盖。

---

### 4. 生成三场景参数

用户确认后执行（ADR-002 决策 #2/#11/#13）：

```bash
python lab/scripts/build_scenarios.py \
  --code <股票代码> --country <CN/HK/US> \
  --analyst-high <H> --analyst-mid <M> --analyst-low <L>
```

脚本自动：
- 构建 base / bull / bear 三套场景（ADR #2）
- 以 L3 WACC 作为折现率 `r`（ADR #3），同时存储 `wacc_l2_sanity`
- 写入 `micro.db` 的 `scenarios` 表（ADR #13）

---

### 5. 生成 HTML 报告

```bash
python lab/scripts/render_micro.py --code <股票代码> --dcf --out-dir lab/reports/
```

生成包含以下区块的 HTML 报告（ADR-002 决策 #15）：
1. 股票头部卡片（估值徽章 + 当前价格）
2. 三场景对照表（scenario / 每股内在价值 / vs 现价 / 安全边际）
3. FCF 历史柱状图
4. 估值敏感性热力图
5. 行业排名表（可选）

---

### 6. 呈现与解读（ADR-002 决策 #15）

从 HTML 报告中提取三场景对照表，以 Markdown 呈现：

| 场景 | 每股内在价值 | vs 现价 | 安全边际 |
|------|------------|--------|---------|
| bear | ¥XX.X | XX% | XX% |
| base | ¥XX.X | XX% | XX% |
| bull | ¥XX.X | XX% | XX% |

**Buffett 30% 安全边际单标签解读（基于 base 场景的 price/IV 比率）：**
- < 0.7：🟢 深度低估
- 0.7–0.9：🟢 低估
- 0.9–1.1：⚪ 合理
- 1.1–1.3：🔴 高估
- > 1.3：🔴 深度高估

---

### 行业因子排名路径（独立于 DCF）

1. 确认行业范围
2. 调用 `python lab/scripts/factor_score.py --industry <行业名称>`
3. 呈现 PE/PB/ROE/PS 排名

---

## 输出格式

### DCF 估值（三场景，ADR #2/#15）
- 三场景对照表（base/bull/bear × 内在价值/vs 现价/安全边际）
- Buffett 30% 安全边际单标签解读
- L3 WACC 分解说明（Re/Rd/tax/D-V 各项数值）+ L2 sanity check

### 行业排名
- PE/PB/ROE/PS 各因子排名表
- 综合排名
- 行业均值对照

### 图表选项（按需）
- 三场景估值对照图
- FCF 历史柱状图
- 估值敏感性热力图

## 约束

- DCF 计算由固定 Python 函数执行，AI 不生成算法代码
- WebSearch 结果**仅用于获取分析师增长率**，不用于 WACC 估算（ADR #11）
- **用户必须在 `build_scenarios.py` 执行前确认参数**，不能自动代入默认值
- L3 WACC 自动计算；Damodaran CSV 每年 1 月手动更新（见 `lab/data/damodaran/README.md`）（ADR #4）
- 若 `interest_expense`/`pretax_income` 缺失，自动降级并在输出中说明原因（ADR #3）
- 首次使用必须运行 `fetch_financials.py` 拉取数据
- 不做股票名称→代码查询（强制代码输入，ADR #7）
