---
name: lab-diagnose
description: 跑债务周期诊断 + 增长通胀 regime + 资产配置倾向
trigger: user asks for current macro diagnosis
---

# lab-diagnose — 宏观环境诊断

运行完整的宏观诊断管线，输出结构化结果。

## 流程

### 1. 读取最新数据

查找并读取 `lab/data/fred_snapshot_<latest>.csv`：

```python
import glob, pandas as pd
from pathlib import Path
data_dir = Path("lab/data")
files = sorted(data_dir.glob("fred_snapshot_*.csv"))
snapshot = pd.read_csv(files[-1])
```

### 2. 计算诊断

用 `lab/dashboard/backend/main.py` 中的 `compute_diagnosis` 函数：

```python
import sys; sys.path.insert(0, ".")
from lab.dashboard.backend.main import compute_diagnosis
result = compute_diagnosis(snapshot)
```

或者直接从文件中读取 `regime.py`/`main.py` 的诊断逻辑，手动计算每个信号。

### 3. 计算 Regime

用 `lab/dashboard/backend/regime.py` 中的 `compute_regime` 函数：

```python
from lab.dashboard.backend.regime import compute_regime
regime = compute_regime(snapshot)
```

### 4. 读取历史记录

检查 `lab/data/diagnosis_history.jsonl` 尾部，了解近期 regime 演变趋势。

### 5. 输出结构化结果

返回包含以下字段的 JSON（供 eco-brief 或其他 skill 消费）：

```json
{
  "date": "YYYY-MM-DD",
  "debt_cycle": { "stage": "...", "color": "...", "signals": [...] },
  "regime": { "quadrant": "...", "growth": ..., "inflation": ... },
  "asset_tilts": [{"asset": "stocks", "tilt": -2}, ...],
  "long_term_risk": { "debt_gdp": ..., "fed_debt_gdp": ... },
  "diagnosis_history": [...]
}
```
