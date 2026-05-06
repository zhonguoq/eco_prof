---
scenario_id: micro_basic_cn
mode: offline
persona: src/eco-prof.md
skills:
  - src/skills/micro/SKILL.md
fixture: micro_seeded
rubric: evals/micro/rubrics/adr-002.md
tags: [micro, cn, happy-path]
---

# Scenario: A股基础估值流程

## Input
帮我估值 000725.SZ

## Notes
验证 ADR-002 的决策在 A 股（京东方 A）场景下是否被 micro skill v2 正确编排。
重点：三场景 / L3 WACC / Damodaran β / gt 公式 / 三场景对照表。
