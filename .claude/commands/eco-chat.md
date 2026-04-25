---
description: 进入与 eco-prof 的对话模式——就当前宏观、投资、wiki 内容、最近诊断展开讨论。
argument-hint: "[your question]"
---

启动 `eco-prof` subagent，让它执行 Chat 模式。

通过 Agent 工具 `subagent_type: eco-prof` 唤起，传入提示：

```
Chat 模式。用户问题：
$ARGUMENTS

按你的讨论范式：
1. 先听懂问题的形状（解释 / 判断 / 建议 / 回顾）
2. 按需最小调用 skill（拒绝无脑全跑 brief 流程）
3. 先答核心 → 再给支撑 → 最后标不确定性
4. 若对话中出现有长期价值的结论，主动提议归档到 wiki/analyses/
```

若 $ARGUMENTS 为空，请 eco-prof 先问用户想讨论什么方向（不要自作主张做日报）。
