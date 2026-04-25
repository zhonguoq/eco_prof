---
name: eco-brief
description: 生成今日宏观简报
---

# /eco-brief — 每日宏观简报

执行 eco-brief skill 生成今日宏观简报。

## 流程

1. 运行 **lab-diagnose**（拉最新数据 + 诊断）
2. 运行 **news-scan**（扫描今日新闻）
3. 读取相关 **wiki 框架** 对照解读
4. 合成简报写入 `lab/reports/YYYY-MM-DD_eco-brief.md`
5. 追加日志到 `knowledge/wiki/log.md`

## 可选参数

- `today`（默认）：生成今日简报
- `date:YYYY-MM-DD`：指定日期（如果该日已有简报，直接显示）
- `--rerun`：重新生成（覆盖已有简报）
