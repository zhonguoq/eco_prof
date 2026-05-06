# Agent Eval Harness

基于 ADR-003 的 agent 端到端测试框架。

**架构文档：** `docs/adr/003-agent-eval-harness.md`

---

## 快速开始

### 1. 配置 DeepSeek API Key

```bash
export DEEPSEEK_API_KEY=sk-...
```

Key 仅通过环境变量读取，不写入磁盘。
（`evals/config.yaml` 只存 `api_key_env` 字段名，不含密钥）

### 2. 运行 Smoke Test

```bash
# 验证 harness 骨架可跑通（无需数据库）
python -m evals.harness.run --scenario evals/smoke/scenarios/hello.md
```

预期产出：
```
evals/results/<timestamp>/smoke_hello/
  conversation.md   # 人类可读对话
  events.jsonl      # opencode 原始事件流
  scores.json       # judge 打分
  report.md         # rubric + 打分 + Human review checkbox
```

### 3. 运行 Micro Skill Eval（需先准备 fixture）

```bash
# Step 1：生成 fixture（需真实网络数据）
python -m evals.harness.seed_fixtures

# Step 2：运行三市场 scenario
python -m evals.harness.run --scenario evals/micro/scenarios/basic_cn.md
python -m evals.harness.run --scenario evals/micro/scenarios/basic_hk.md
python -m evals.harness.run --scenario evals/micro/scenarios/basic_us.md
```

---

## 目录结构

```
evals/
  README.md               # 本文件
  config.yaml             # judge provider 配置（无密钥）
  benchmark-log.md        # 跨 run 趋势表
  harness/
    run.py                # 入口（python -m evals.harness.run）
    judge.py              # LLM judge（DeepSeek）
    parser.py             # scenario / rubric 解析
    agent_builder.py      # 动态生成 opencode agent
    seed_fixtures.py      # fixture 种子脚本
    config.py             # 读取 config.yaml
  smoke/
    scenarios/hello.md    # Smoke scenario（自测 harness）
    rubrics/hello.md      # Smoke rubric
  micro/
    scenarios/            # A股 / 港股 / 美股 scenario
    rubrics/adr-002.md    # ADR-002 的 16 条决策 → rubric
  fixtures/               # gitignored，seed 脚本生成
  results/                # gitignored，每次 run 产出
```

---

## Gitignore 策略

**commit（进 git）：**
- `harness/**/*.py`、scenario / rubric `.md`、`config.yaml`、`benchmark-log.md`

**gitignore：**
- `fixtures/*.db`（seed 脚本重新生成）
- `results/`（本地保留，不污染仓库）
- `.opencode/agent/eval-*.md`（harness 动态生成的临时 agent）

---

## 测试分层（ADR-003 决策 1）

| Layer | 方式 | 频率 |
|-------|------|------|
| L2 | LLM judge 自动打分（本 harness）| 每次 skill/persona 变更后 |
| L4 | 人工在 report.md 上勾 checkbox | Sprint review |
