---
name: lab-diagnose
description: 跑 lab 层的宏观诊断：刷新 FRED 数据（如当日未刷）、计算债务周期 5 信号 + 增长通胀 regime + 资产倾向 + 长期结构风险 + 近 N 天历史轨迹。对外口径稳定，内部复用 lab/dashboard/backend/ 的纯函数。
---

# lab-diagnose — 宏观诊断技能

## 契约（稳定）

**输入**（自然语言描述即可）：
- `scope`: `snapshot | full | history-only`（默认 `full`）
  - `snapshot` — 只当下；最快
  - `full` — 当下 + 近 7 天轨迹
  - `history-only` — 只要轨迹
- `days`: 可选整数，默认 7（仅 `full` / `history-only` 生效）
- `refresh`: `auto | force | skip`（默认 `auto`）
  - `auto` — 当日尚无快照才刷
  - `force` — 强制重刷
  - `skip` — 不碰数据，只读现有

**输出**（Markdown 结构化块）：

```
### 当前诊断 (as of YYYY-MM-DD)
- **债务周期阶段**: <stage>  (<stage_color>)
- **增长通胀 Regime**: <quadrant> / <quadrant_cn>
- **GDP 增速**: X.XX% / **CPI 同比**: X.XX%

### 债务周期 5 信号
| 信号 | 读数 | 状态 | 说明 |
|---|---|---|---|
| 收益率曲线 | ... | ok/warning/danger | ... |
| 货币政策空间 | ... | ... | ... |
| 名义增速 vs 利率 | ... | ... | ... |
| HY 信用利差 | ... | ... | ... |
| 信用卡违约率 | ... | ... | ... |

### 辅助信号
- 失业率 / 消费者信心 / 美元指数

### 资产倾向（Dalio all-weather 式）
- 股票: +X | 长债: +X | 商品/黄金: +X | 现金: +X

### 长期结构风险
- 总债务/GDP: X.X% — status
- 联邦债务/GDP: X.X% — status
- 美元长期趋势: ...

### 近 N 天 Regime 轨迹（仅 full / history-only）
- YYYY-MM-DD: <quadrant> / <stage>
- ...

### 数据引用
- lab/data/fred_snapshot_YYYYMMDD.csv
```

## 实现步骤（v0.1）

### 1. 准备：检查当日快照

```bash
python3 -c "
import glob, datetime, os
today = datetime.date.today().strftime('%Y%m%d')
files = glob.glob('lab/data/fred_snapshot_*.csv')
print('has_today:', any(today in f for f in files))
print('latest:', sorted(files)[-1] if files else None)
"
```

### 2. 如需刷新（refresh=auto 且当日无快照，或 refresh=force）

在仓库根（`/Users/guoqiangzhong/eco_knowladge_base`）按顺序跑：

```bash
python3 lab/tools/fetch_us_indicators.py
python3 lab/tools/fetch_yield_curve.py
```

失败时：**诚实报告哪个系列拉失败**，不要静默忽略。FRED 偶尔 rate limit，可重试一次。

### 3. 计算诊断（通过 python3 -c 调用纯函数）

```bash
cd /Users/guoqiangzhong/eco_knowladge_base && python3 <<'PY'
import sys, json
sys.path.insert(0, '.')
from lab.dashboard.backend.main import read_snapshot, compute_diagnosis
from lab.dashboard.backend.regime import compute_regime, read_history, append_history

snap = read_snapshot()
if snap is None:
    print(json.dumps({"error": "no snapshot file"}))
    sys.exit(1)

diag = compute_diagnosis(snap)
reg = compute_regime(snap)

# scope=full: 也追加今日 history（幂等：read_history 按 date 去重保留最新）
append_history(diag, reg)

out = {
    "diagnosis": diag,
    "regime": reg,
    "history": read_history(limit=7),  # 若调用方要 history-only / 不同 days 参数，改这里
}
print(json.dumps(out, ensure_ascii=False, default=str))
PY
```

### 4. 解析 JSON 并按契约渲染成 Markdown

- 表格顺序：yield_curve → rate_space → growth_vs_rate → hy_spread → delinquency
- 状态颜色用 emoji：ok=✅ / warning=⚠️ / danger=🚨
- 资产倾向保持原始符号（+2 / +1 / -1 / -2），不要做口语化转换
- 轨迹按日期倒序，缺失日期用 `—` 占位

## 实现注记（允许演进，不破坏契约）

- `lab/dashboard/backend/main.py` 里的 `compute_diagnosis` 和 `regime.py` 里的 `compute_regime` 是真实逻辑源。**不要**在本 skill 里复制阈值。
- 若未来 lab 演进（加 L4、加新信号、换回归模型），**只改本 skill 的渲染逻辑**，不动上面的契约块。契约要变时 bump 版本 + 在 SCHEMA.md 记 log。

## 错误场景

- 快照缺失 + refresh=skip → 返回错误 + 建议 `refresh=auto` 重试
- FRED API 拉失败 → 报告受影响系列名 + 用上一日快照继续（若 <48h 老）
- regime.py import 失败 → 检查 `python3 --version` 和 `lab/dashboard/backend/requirements.txt` 安装

## 演进路径

- v0.2：加 L4（情绪 / 仓位 / 资金流），加参数 `include_l4: bool`
- v0.3：支持 `compare_to=YYYY-MM-DD` 做前后对照
- v1.0：多国支持（当前只 US）
