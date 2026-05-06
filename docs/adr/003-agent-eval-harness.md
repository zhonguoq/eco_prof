# ADR-003 / Agent Eval Harness —— Layer 2 + Layer 4 的 agent 端到端测试框架

**状态**：Accepted
**日期**：2026-05-06
**相关**：ADR-002（微观引擎 v2 的 16 条决策是首个 rubric 来源）

## 背景

Issue #34 原本要求对 micro 引擎做"端到端 benchmark 测试"。在 `/triage` 流程中澄清出真实诉求：
**不是对 Python 接口做端到端测试，而是对 agent（LLM + skill + tools）的行为做端到端测试**。

输入 = skill/人格定义 + 用户 query；
输出 = agent 完整对话；
评判 = 对话是否符合 ADR-002 的决策编排。

本 ADR 钉下 agent eval 子系统的 16 个架构决策，作为实现的唯一真相源。

## 决策清单

### 1. 测试分层：Layer 2（自动化 LLM-as-Judge）+ Layer 4（人工结构化审查）
- **Layer 2**：LLM judge 依据 rubric 给对话自动打分，CI-friendly、可频繁跑
- **Layer 4**：人类在 judge 打分上加 checkbox、做最终判断，应对 judge 偏差
- 放弃 Layer 1（纯 tool trace mock）和 Layer 3 的自动化（live 模式保留但不进 CI）

### 2. 框架选择：自定义 Python harness（不引入 Promptfoo / Braintrust）
- 无新依赖、与现有 pytest 生态一致
- 可完全控制 opencode subprocess 调用、事件流解析、judge 调度
- 未来扩展性通过 `scenario + rubric` 抽象保证

### 3. 核心抽象：`Scenario = agent + input + rubric`
- scenario 是 eval 的最小单元
- 一个 scenario 绑定：要装载哪个 persona + 哪些 skill、发什么消息、用哪份 rubric 评
- 新增测试 = 新建一个 scenario 文件，不动 harness 核心

### 4. 被测对象 = 主人格 + 装载的 skill（方案 A）
- 不为每个 skill 造"瘦 agent wrapper"
- 真实产品形态是"主人格决定装载哪个 skill"，eval 就测这个完整路径
- 路由错误（该装 micro 却没装）本身就是该被 rubric 捕获的 bug

### 5. Rubric 存储：Markdown + YAML frontmatter
- 和项目现有 wiki / skill 的 frontmatter 风格一致
- 人类可读（review / PR diff 友好）+ 机器可解析（harness 抽 `{id, question}`）
- 一份 rubric 覆盖一个测试层次（Layer 2 rubric 不混 Layer 3 的数据获取检查）

### 6. 目录结构：按 skill/agent 分组
```
evals/
  README.md
  config.yaml                 # judge provider 配置（commit）
  harness/                    # Python 代码
    run.py                    # 入口
    judge.py                  # LLM judge 调用
    parser.py                 # scenario / rubric 解析
    agent_builder.py          # 动态生成 opencode agent
    seed_fixtures.py          # fixture 种子脚本
    config.py
  micro/
    scenarios/
      basic_cn.md
      basic_hk.md
      basic_us.md
    rubrics/
      adr-002.md
  macro/                      # 未来扩展
  eco-prof/                   # 未来扩展（主人格路由测试）
  fixtures/                   # gitignored，seed 脚本生成
  results/                    # gitignored，每次 run 产出
  benchmark-log.md            # 跨 run 趋势表（commit）
```

### 7. 数据前置：Offline (fixture) + Live (empty DB) 双模式
- **offline 模式**：harness 复制 `evals/fixtures/<name>.db` 到 `lab/db/`，agent 跑时数据已在
  - 适合频繁跑、CI-ready、测"分析/呈现阶段"的决策
  - 承认 distribution shift（上下文短于真实场景），用 Layer 3 兜底
- **live 模式**：清空 DB，让 agent 自己决策 fetch + 分析
  - 稀疏跑（每周/release），测"数据获取阶段"的决策（ADR-002 #7/#8/#10）
  - 需网络，非确定性高

### 8. Fixture 策略：定期重新生成 + 只 commit seed 脚本
- `evals/harness/seed_fixtures.py` 跑 `fetch_financials.py` 拉三只股票（000725.SZ / 00700.HK / AAPL），复制到 `evals/fixtures/micro_seeded.db`
- seed 脚本 **进 git**，生成的 `.db` **进 gitignore**
- 季度重跑一次，rubric 只检查结构/流程不检查具体数字

### 9. Agent 调用：subprocess + `opencode run --format json`
- `opencode run --agent <name> --format json --dangerously-skip-permissions "<input>"`
- 输出是 JSON event stream（每行一个 event，type 含 `step_start` / `text` / `tool_call` / `step_finish`）
- harness 解析事件流 → 拼出 `conversation.md` + `events.jsonl`
- 未来需并行化可切换 `opencode serve` HTTP 模式，不影响上层抽象

### 10. 人格/技能注入：动态生成 opencode agent 文件
- harness 读 scenario frontmatter 的 `persona` + `skills` 列表
- 运行时拼接生成临时 `.opencode/agent/eval-<scenario_id>.md`（gitignored）
- 跑完清理
- `src/` 下的 persona/skill 是单一真相源，不维护副本，不漂移

### 11. Scenario 文件格式
```markdown
---
scenario_id: micro_basic_cn
mode: offline                        # offline | live
persona: src/eco-prof.md
skills:
  - src/skills/micro/SKILL.md
fixture: micro_seeded                # 仅 offline 模式需要
rubric: evals/micro/rubrics/adr-002.md
tags: [micro, cn, happy-path]
---

# Scenario: A股基础估值流程

## Input
帮我估值 000725.SZ

## Notes
验证 ADR-002 的 16 个决策在 A 股场景下是否被正确编排。
```

### 12. Judge 调度：one-shot + 引用原文 + JSON schema 约束
- 一次调用把完整 rubric（N 条）+ 完整对话送给 judge
- Judge 返回 JSON：`{<rubric_id>: {"pass": bool, "reason": str, "quote": str}}`
  - `quote` 字段强制 judge 引用对话原文片段，便于人工 verify
- schema 校验：若 judge 漏答某条 rubric item，自动 fallback 到 per-item 补评
- Judge temperature=0，追求确定性

### 13. Judge Provider 配置：config.yaml + API key env var
```yaml
# evals/config.yaml（commit 进 git）
judge:
  provider: deepseek
  model: deepseek-chat
  base_url: https://api.deepseek.com/v1
  api_key_env: DEEPSEEK_API_KEY       # 从环境变量读，避免密钥进磁盘
  temperature: 0.0
  timeout_seconds: 60
```
- 切换 provider 只改 yaml，无需改代码
- 未来支持多 judge（A/B judge 对比）只需 yaml 扩展成 list

### 14. 结果产出：Layer 2 report + Layer 4 checkbox + 跨 run benchmark-log
单次 run 产出：
```
evals/results/<timestamp>/<scenario_id>/
  conversation.md      # 人类可读对话
  events.jsonl         # opencode 原始事件流（fine-tune-ready messages 格式）
  scores.json          # judge 打分
  report.md            # 融合 rubric + 对话 + 打分 + Human review checkbox
```
跨 run 追踪：`evals/benchmark-log.md`（commit）
```markdown
| 日期 | git sha | scenarios pass | judge avg | human agree rate | 备注 |
```

### 15. 产出物 gitignore 策略
**commit**：
- `evals/harness/**/*.py`（代码）
- `evals/*/scenarios/*.md`、`evals/*/rubrics/*.md`（定义）
- `evals/config.yaml`（不含密钥）
- `evals/benchmark-log.md`（跨 run 追踪）
- `evals/README.md`

**gitignore**：
- `evals/fixtures/*.db`（seed 脚本重新生成）
- `evals/results/`（全部本地保留，为未来 fine-tune 留素材，但不污染仓库）
- `.opencode/agent/eval-*.md`（harness 动态生成的临时 agent）

### 16. 实施拆分：三个 issue
- **#34**（原 issue，缩小范围）：SKILL.md 对齐 ADR-002 + `benchmark-log.md` 占位
- **#35**（新）：eval harness 骨架（决策 1–13 对应代码 + smoke test scenario）
- **#36**（新）：micro skill 首个 eval 应用（ADR-002 映射为 rubric + seed fixture + 跑出首份 report）
- 顺序：#34 → #35 → #36

## 后果

### 正向
- Agent 行为变得**可评测、可回归**，skill 改动后能立刻知道有没有偏离 ADR 决策
- 产出物天然对齐 fine-tune 数据格式，为未来模型定制打基础
- 抽象通用，未来所有 skill / persona 都能接入同一个 harness
- Judge provider 可配置，跨模型对比、切换无摩擦

### 代价
- 引入一套新的子系统（`evals/` 目录 + harness 代码）
- Fixture 需季度维护（跑 seed 脚本）
- Judge LLM 调用有 API 成本（DeepSeek 便宜，可接受）
- Offline 模式的 distribution shift 无法完全消除，依赖 Layer 4 + 偶尔 live 运行兜底

## 未决（留作未来决策）
- 并行化：当 scenario 数量超过 20 个时是否切换 `opencode serve` HTTP 模式
- Judge A/B：是否引入第二个 judge model 做交叉验证
- 数据集导出：fine-tune 时点到了再写 `export_finetune_dataset.py`
- Live 模式的调度：是否写 GitHub Action 每周自动跑
