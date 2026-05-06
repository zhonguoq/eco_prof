---
scenario_id: micro_basic_hk
mode: offline
persona: src/eco-prof.md
skills:
  - src/skills/micro/SKILL.md
fixture: micro_seeded
rubric: evals/micro/rubrics/adr-002.md
tags: [micro, hk, happy-path]
---

# Scenario: 港股基础估值流程

## Input
帮我估值 00700.HK

## Notes
验证 ADR-002 的决策在港股（腾讯控股）场景下是否被 micro skill v2 正确编排。
重点：HK 市场 Damodaran 数据 / gt 使用 HK=4.0% / 三场景对照表。
