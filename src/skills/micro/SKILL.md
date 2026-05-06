---
name: micro
description: 微观引擎 — DCF 估值 + 行业因子排名
---

授权级别：L1

用户需要 DCF 估值、行业因子排名、估值 vs 价格对比时触发。

## 执行流程

### 0. 前置条件

**务必确认用户提供了股票代码。** 如果是中文名（如"京东方A"），先转换为 A 股代码（如 `000725.SZ`）。

**首次运行时先 fetch 数据：**

```bash
python lab/scripts/fetch_financials.py --code <股票代码>
```

这会从 akshare 拉取股价历史、现金流量表和资产负债表，存入 `micro.db`。

---

### 1. 自动参数估计

运行参数估计脚本：

```bash
python lab/scripts/estimate_params.py --code <股票代码> --industry <行业>
```

输出包括：
- **CAGR**（年复合增长率）—— 基于 FCF 历史
- **线性趋势增长率** —— 基于 FCF 线性回归
- **Beta**（vs 沪深 300）—— 基于股价历史
- **CAPM WACC**（Rf + Beta × ERP）
- **行业默认 WACC**

**记录这些估计值用于后续呈现给用户。**

---

### 2. WebSearch：分析师共识 & 行业参考

用 WebSearch 获取以下外部参考信息，**务必按以下搜索词执行**：

**搜索 A（分析师共识增长率）：**
```
<股票名称> <股票代码> 分析师 预测 增长率 2026 2027
```

**搜索 B（行业参考 WACC）：**
```
<行业> 行业 WACC 加权平均资本成本 参考
```

将搜索结果整理为结构化摘要呈现给用户。

---

### 3. 向用户呈现参数选项

向用户展示 **4 个增长率来源** 和 **3 个 WACC 来源**，请求用户确认最终参数。

**增长率选项（4 个）：**
| # | 来源 | 说明 |
|---|------|------|
| A | **CAGR**（引擎计算） | 基于历史 FCF 的年复合增长率 |
| B | **线性趋势**（引擎计算） | 基于历史 FCF 的线性回归增长率 |
| C | **分析师共识**（WebSearch） | 搜索到的分析师预测增长率 |
| D | **行业参考**（WebSearch） | 搜索到的行业平均增长率 |

**WACC 选项（3 个）：**
| # | 来源 | 说明 |
|---|------|------|
| A | **CAPM**（引擎计算） | Rf + Beta × ERP，基于宏观引擎 10Y 国债收益率 |
| B | **行业默认**（引擎） | 根据行业查表 |
| C | **行业参考**（WebSearch） | 搜索到的行业 WACC 参考值 |

**询问用户的决策：**
- 用户可以选择使用任一增长率 + 任一 WACC 的组合（共 12 种）
- 用户也可以输入自己的自定义参数
- 如果用户不确定，建议使用 **CAGR + CAPM WACC** 作为默认组合

---

### 4. 批量计算

```bash
# 默认组合（单一参数）
python lab/scripts/dcf.py --code <代码> --growth <增长率> --discount <折现率> --equity

# 敏感性矩阵
python lab/scripts/dcf.py --code <代码> --growth <增长率> --discount <折现率> --sensitivity
```

如果有多个组合，可以逐一运行：

```bash
# 12 组合全部计算（用户确认后）
python lab/scripts/dcf.py --code <代码> --growth <CAGR> --discount <CAPM> --equity
python lab/scripts/dcf.py --code <代码> --growth <分析师> --discount <行业默认> --equity
# ... 等
```

---

### 5. 呈现结果

- 呈现每个组合的 DCF 估值（企业价值 + 股权价值）
- 呈现敏感性矩阵（增长率 × 折现率）
- 标注当前价格 vs 估值对比（低估 / 合理 / 高估）
- 如需图表：`python lab/scripts/render_micro.py --code <代码> --dcf`

---

### 行业因子排名路径（独立于 DCF）

1. 确认行业范围
2. 调用 `python lab/scripts/factor_score.py --industry <行业名称>`
3. 呈现 PE/PB/ROE/PS 排名

---

## 输出格式

### DCF 估值
- 估值区间（合理估值 + 上下限）
- 敏感性表（增长率 × 折现率矩阵）
- 当前价格 vs 估值对比（低估/合理/高估）

### 行业排名
- PE/PB/ROE/PS 各因子排名表
- 综合排名
- 行业均值对照

### 图表选项（按需）
- 估值 vs 价格趋势图
- 敏感性热力图
- 历史价格走势

## 约束

- DCF 计算由固定 Python 函数执行，AI 不生成算法代码
- WebSearch 结果仅作为参考呈现给用户，不做自动决策
- **用户必须在每个 DCF 计算前确认参数**，不能自动代入默认值
- 首次使用必须运行 `fetch_financials.py` 拉取数据
