---
name: review
description: 定期复盘 — 元引擎背离检测 + 判断回溯
---

# /review — 复盘

调用元引擎背离检测和判断回溯，检查过去判断的正确性：

1. 跑 `python lab/scripts/check_disconfirmation.py` 检测背离
2. 跑 `python lab/scripts/list_judgments.py` 列出未决判断
3. 输出偏差分析报告
