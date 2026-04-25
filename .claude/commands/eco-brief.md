---
description: 手动触发 eco-prof 产出每日宏观简报。可带 focus 参数做专题简报。
argument-hint: "[optional focus topic]"
---

启动 `eco-prof` subagent，让它执行 Brief 模式。

$ARGUMENTS 若非空则作为本次 focus 主题，简报走专题路径（文件名带 focus-slug）；否则走 daily 模式。

请通过 Agent 工具 `subagent_type: eco-prof` 唤起，传入提示：

```
Brief 模式 / mode=daily（如 $ARGUMENTS 非空则 mode=topic focus="$ARGUMENTS"）。

按你的编排范式：
1. 查当前可用 skill 清单
2. 调 wiki-query 加载相关框架
3. 调 lab-diagnose（scope=full, days=7）
4. 调 news-scan（since_hours=24）
5. 综合判断（必要时调整步骤顺序或追加）
6. 调 eco-brief 归档

完成后返回：简报路径、一行 TL;DR、是否触发告警。
```
