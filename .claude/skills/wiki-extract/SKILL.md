---
name: wiki-extract
description: 从 wiki 知识中提取可操作原则卡片，形成可编码、可验证的投资原则库
trigger: user wants to extract principles from wiki, or after ingest of new source
---

# wiki-extract — 原则提取

从 wiki 知识中提取**可操作的原则卡片**。每条原则应是一个可被编码、回测、迭代的判断规则。

## 原则卡片格式

每条原则存为一个独立的 `.md` 文件在 `knowledge/wiki/principles/` 下，文件名用 `P-编号-英文简述.md`：

```yaml
---
id: P001
title: 收益率曲线倒挂是衰退的可靠领先信号
statement: |
  当 10Y-2Y 国债收益率利差持续为负时，未来 12-18 个月内出现经济衰退的概率显著升高。
rationale: |
  收益率曲线倒挂反映了市场对未来增长的悲观预期，同时压缩银行净息差，导致信贷收缩。
  历史回测支持（过去 8 次美国衰退中 7 次之前出现倒挂）。
sources:
  - 收益率曲线-yield-curve.md
  - 债务周期阶段判断框架.md
confidence: high           # high / medium / low / speculative
testable: true             # 能否用历史数据回测验证？
encoded_in:                # 已编码位置（空白的表示待编码）
  - lab/dashboard/backend/main.py:128-136
status: active             # active / deprecated / disproven / proposed
last_reviewed: 2026-04-25
review_cadence: yearly
tags: [yield-curve, recession, leading-indicator]
related_principles: [P003, P005]
---

## 解读

（可选）对原则的深入解释、适用条件、注意事项。

## 历史案例

- 2006-2007 年倒挂 → 2008 年金融危机
- 2019 年倒挂 → 2020 年疫情衰退
- 2023 年倒挂 → 待验证

## 已编码的引用

- `lab/dashboard/backend/main.py:128-136` — 收益率曲线信号诊断，将 `spread < 0` 标记为 `danger`
```

## 提取流程

### 1. 定位可原则化的知识

从 wiki 中找**可转化为判断规则**的内容：

| 适合提取为原则 | 不适合 |
|-------|--------|
| ✅ 可量化的阈值（"当 X > Y 时意味着 Z"） | ❌ 纯定义性内容（"什么是债务周期"） |
| ✅ 可回测的判断（"历史表明 P 导致 Q"） | ❌ 描述性历史（"2008 年雷曼倒闭"） |
| ✅ 可编码的规则（"如果 A 且 B，则配置 C"） | ❌ 个人观点无普适性 |
| ✅ 跨案例的规律（"所有储备货币都经历三阶段"） | ❌ 一次性事件 |

### 2. 起草原则卡片

对每个候选原则：
1. 写 `id`（按顺序 P001, P002... 新发现放最后）
2. 写 `title`（中文，15 字以内，可理解）
3. 写 `statement`（一句话，精确、无歧义）
4. 写 `rationale`（为什么这个原则成立？来自什么逻辑/证据？）
5. 标 `confidence`（基于 wiki 中证据的充分程度）
6. 标 `testable`（是否可量化回测？）
7. 标注 `sources`（引用 wiki 页面路径）
8. 检查是否已编码（搜索 `lab/dashboard/backend/` 中是否有对应逻辑）
9. 标注 `status: proposed`

### 3. 用户确认

将起草完成的原则卡片**逐条呈现给用户**，让用户确认：
- 原则是否正确？
- 措辞是否准确？
- confidence 是否合理？

用户确认后，将 `status` 改为 `active`。

### 4. 更新索引

将已确认的原则加入 `knowledge/wiki/principles/index.md`。

### 5. 更新日志

追加到 `knowledge/wiki/log.md`。
