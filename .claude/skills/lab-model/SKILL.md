---
name: lab-model
description: 将投资原则编码为可执行的指标、阈值、规则，建立原则↔代码双向追溯
trigger: user wants to encode a principle, or after principle extraction
---

# lab-model — 原则编码

将 Wiki Agent 提取的原则转化为 `lab/dashboard/backend/` 中可执行的代码。

## 流程

### 1. 评估可编码性

确认原则的 `testable: true` 且满足：
- 有可量化的条件（if x > y then z）
- 有可用数据源（已在 FRED 中或可新增）
- 有明确的输出（signal / status / score）

### 2. 选择挂载位置

| 场景 | 挂载位置 |
|------|---------|
| 核心诊断信号（简短） | `regime.py` → `aux_signals` |
| 独立计算逻辑（复杂） | `regime.py` → 新函数，在 `compute_regime` 中调用 |
| 新数据系列 | `fetch_us_indicators.py` → 新增 FRED 系列 + 衍生计算 |
| API 元数据 | `main.py` → `SERIES_META` |

### 3. 编码规范

```python
# <principle-id> — <principle-title>
# Source: <wiki-page-path>
# Logic: <one-line summary of what this encodes>
```

示例：
```python
# P001 — 收益率曲线倒挂是衰退的可靠领先信号
# Source: knowledge/wiki/concepts/收益率曲线-yield-curve.md
# Logic: T10Y2Y < 0 → danger
if spread < 0:
    signals.append({"id": "yield_curve", ..., "status": "danger"})
```

### 4. 更新追溯

编码后更新原则卡片：
- `encoded_in` 字段：列出编码的文件路径和行号
- `status`：确保为 `active`

### 5. 验证

- `python3 -c "compile(open('path').read(), 'path', 'exec')"` 语法检查
- 如果有历史数据，手动验证输出是否符合预期
