---
name: review
description: 定期复盘 — 元引擎背离检测 + 判断回溯
---

授权级别：L3（分析）/ L4（写回）

用户说"复盘"、"回顾"、"检查之前的判断"、"learn from that"时触发。

## 执行流程

### Step 1: 检测背离
调用 `python lab/scripts/check_disconfirmation.py` → 输出当前被反证的判断列表

### Step 2: 列出未决判断
调用 `python lab/scripts/list_judgments.py` → 输出所有处于 active 状态的判断

### Step 3: 聚合三路数据
- 判断信息（disconfirmed 判断 + 近期 active 判断）
- 信号偏差（当前信号值 vs 判断时的快照）
- 相关原则卡片引用（偏差涉及的 P00X）

### Step 4: 人机对话分析
与用户逐条分析偏差原因：
- 是阈值设错了？→ 触发规则更新
- 是框架遗漏了变量？→ 触发原则扩展
- 是黑天鹅事件？→ 记录为异常，不修改规则

### Step 5: 产出暂存文件
形成共识 → 写入 `lab/staging/{session_id}.md`
包含：规则修改、原则新建或更新、迭代记录

### Step 6: 提示暂存状态
"产物已暂存，可用 write-back 写回"

### Step 7 (write-back): 确认执行
当用户说"写回"、"确认"、"落地"时：
1. 扫描 `lab/staging/` → 提取所有 status: pending 的条目
2. 批量展示每个条目的 diff
3. 用户选择要执行的条目编号
4. AI 按类型执行（编辑 rules.json / 创建原则卡片 / 写入 meta.db.iterations / 更新 judgments.status）
5. 更新 staging 文件 items[].status → executed

## 输出格式

### 背离列表
- 每条背离：判断 ID + 原始预测 + 实际结果 + 偏差幅度
- 标注置信度变化

### 偏差分析报告
- 每条偏差的分析结论 + 建议的规则修改
- 区分"阈值调整"和"框架扩展"

### Staging 产物摘要
- 待写回条目清单（规则/原则/迭代）
- 每条预览 diff

### Write-back 确认清单
- 条目编号列表供用户选择
- 执行完成后报告写回结果

## 约束

- L4 写回操作必须 staging → 用户逐条确认，不可批量自动执行
- 每次 write-back 记录到 meta.db 的迭代链路：judgment → deviation → iteration → updated rule
- 分析阶段可自由对话，写回阶段严格受控
