---
name: micro
description: 微观估值 — DCF 估值 / 行业因子排名
---

# /micro — 微观估值

调用微观引擎脚本：
- **个股 DCF**：`python lab/scripts/dcf.py --code <code> [--growth <rate> --discount <rate>]`
- **行业排名**：`python lab/scripts/factor_score.py --industry <name>`
- **图表**：`python lab/scripts/render_micro.py --code <code>` (用户要求时)
