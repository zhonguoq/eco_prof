---
name: news-scan
description: 扫描今日新闻，按框架相关性排序，提取关键主题
trigger: user asks about recent news or invoked by eco-brief
---

# news-scan — 新闻扫描

读取当日新闻，过滤排序，按类别归纳。

## 流程

### 1. 定位今日新闻文件

`lab/news/<today-or-yesterday-UTC>.jsonl`

### 2. 读取和筛选

逐行解析 JSONL，关注新闻类别：

- `central_bank` — 央行政策信号：利率、QE/QT、监管
- `macro` — 宏观经济数据、评论
- `geopolitics` — 地缘政治事件：战争、制裁、贸易
- `markets` — 市场走势、资金流动

### 3. 相关性排序

按以下优先级排序：
- 跟 wiki 框架定义的"关键信号"相关的新闻（收益率曲线、通胀、信用利差…）
- 与当前 regime 矛盾的新闻（如 stagflation + 股市创新高）
- 重大突发事件（战争、央行意外行动）

### 4. 按类别摘要

每个 category 输出：
- 3-5 条最重要的新闻（标题 + 来源 + 一句话影响说明）
- 如果某个 category 当天无相关新闻，标注"无重大事件"

### 5. 原则关联（必做）

**每一条新闻**在摘要时，尝试关联知识库中的原则卡片：

| 新闻类别 | 可能关联的原则 | 检查条件 |
|---------|--------------|---------|
| 收益率曲线、利率 | P001（曲线倒挂→衰退）、P006（曲线形态→周期阶段）、P007（利率水平→政策阶段） | 查看 T10Y2Y、DGS2、DGS10 读数 |
| GDP / 增长数据 | P002（名义增速 vs 利率）、P004（Regime 判断） | 比较 GDP_YOY vs DGS10 |
| 债务 / 信用数据 | P003（债务/GDP 阈值）、P005（资产-商品通胀背离） | 查看总债务/GDP 比率 |
| 资产价格 / 股市 | P005（泡沫期资产通胀背离） | 检查 SP500_YOY vs CPI_YOY |
| 央行政策 | P007（利率→货币政策阶段） | 查看 Fed Funds 水平和趋势 |
| 通胀数据 | P004（Regime 判断）、P005（资产通胀背离） | 检查 CPI_YOY 阈值 |

输出格式：每条新闻或每组新闻后标注 `[principle: P00X]` 引用。

### 6. 告警引擎调用

新闻扫描完成后，自动调用告警引擎检查当前数据是否触发任何告警规则：

```bash
python3 lab/tools/run_alerts.py --date <YYYY-MM-DD> --news lab/news/<YYYY-MM-DD>.jsonl
```

解读告警输出：
- 将 `triggered_alerts` 按 severity（P1 → P2 → P3）排序嵌入结果
- P1 告警用 🔴 标注，P2 用 🟡，P3 用 🔵
- 对每条触发的告警，解释其与今日新闻的关联（如有）
- 标注哪些告警是"持续中"（之前已触发，今日仍在）、哪些是"新触发"

### 7. 框架关联

如果某条新闻触发了 wiki 框架中定义的"危险信号"（如收益率倒挂、利差飙升），用 ⚠️ 标注并引用相关的 wiki 页面。

## 输出格式

输出包含以下字段的结构化结果（JSON 格式，供 eco-brief 消费）：

```json
{
  "date": "YYYY-MM-DD",
  "news_summary": {
    "central_bank": [{"title": "...", "source": "...", "principle": ["P00X"], "impact": "..."}],
    "macro": [...],
    "geopolitics": [...],
    "markets": [...]
  },
  "principle_references": ["P001", "P003", ...],
  "alerts": {
    "triggered": [{"alert_id": "ALERT-XX", "severity": "P1", "title": "...", "principle_ids": [...]}],
    "p1_count": 0,
    "p2_count": 0,
    "total": 0
  }
}
```

## 约束

- 不要完整输出每条新闻的 summary——提取关键点即可
- 如果新闻文件为空或不存在，注明"今日暂无新闻数据"
- 如果新闻扫描被 eco-brief 调用，直接输出结构化文本即可（由 eco-brief 负责最终渲染）
