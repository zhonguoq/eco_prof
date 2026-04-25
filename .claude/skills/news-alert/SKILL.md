---
name: news-alert
description: 框架驱动的主动告警 — 当新闻或数据触发原则定义的"危险信号"时即时告警
trigger: after news-scan completes, or when user requests alert check
---

# news-alert — 框架驱动告警

基于 wiki 框架和原则卡片中定义的触发条件，对今日数据进行扫描，
当信号触及告警线时生成 ⚠️ 告警。

## 告警清单

每条告警关联一条或多条原则卡片，按严重程度分三级：

| 级别 | 标签 | 含义 | 行动 |
|------|------|------|------|
| 🔴 严重 | P1 | 框架定义的"危险"/"danger"条件已触发 | 立即生成专题简报 |
| 🟡 警告 | P2 | 框架定义的"警告"/"warning"条件已触发 | 在每日简报中高亮 |
| 🔵 关注 | P3 | 接近警戒线或趋势逆转 | 在简报中标注"待观察" |

## 告警规则定义

每条告警规则关联一条原则卡片和一个可检查的数据条件：

### 硬信号（从 `lab/data/` 当前数据自动检测）

| ID | 关联原则 | 条件 | 级别 | 说明 |
|----|---------|------|------|------|
| ALERT-YC | P001/P006 | T10Y2Y < 0 且持续 > 5 个交易日 | 🔴 P1 | 收益率曲线正式倒挂 |
| ALERT-YC2 | P001 | T10Y2Y 从倒挂恢复正斜率 | 🟡 P2 | 最后绿灯——衰退倒计时 |
| ALERT-DEBT | P003 | 总债务/GDP > 350% | 🔴 P1 | 债务超过泡沫顶部均值 |
| ALERT-DEBT2 | P003 | 总债务/GDP > 300% | 🟡 P2 | 债务进入警戒区 |
| ALERT-STAG | P004 | Regime 进入 Stagflation | 🟡 P2 | 最差资产环境 |
| ALERT-REGIME-SHIFT | P004 | Regime 象限切换 | 🟡 P2 | 资产配置需要调整 |
| ALERT-DIVERGE | P005 | 资产通胀背离 > +15% | 🔴 P1 | 典型泡沫特征 |
| ALERT-DIVERGE2 | P005 | 资产通胀背离 > +10% | 🟡 P2 | 关注泡沫风险 |
| ALERT-SENTIMENT | — | UMCSENT < 60 | 🟡 P2 | 消费者信心极低 |
| ALERT-SPREAD | C2 | HY 利差 > 5% | 🔴 P1 | 信用市场恐慌 |
| ALERT-SPREAD2 | C2 | HY 利差 > 8% | 🔴 P1 | 危机级别利差 |
| ALERT-RATE0 | A6/P007 | Fed Funds < 0.5% | 🟡 P2 | 利率近零 |

### 软信号（从新闻文本检测）

下面是与原则关联的新闻关键词——当新闻扫描匹配到时触发关注：

| ID | 关联原则 | 新闻关键词 | 级别 | 说明 |
|----|---------|-----------|------|------|
| ALERT-WAR | — | 战争、军事冲突、制裁、核 | 🔴 P1 | 地缘冲突推升不确定性 |
| ALERT-FED | P007/P001 | 美联储意外(加息/降息)、紧急 | 🔴 P1 | 央行非常规行动 |
| ALERT-BANK | B5 | 银行危机、信贷紧缩、挤兑 | 🔴 P1 | 金融系统风险 |
| ALERT-CPI | P004/P005 | CPI超预期、通胀飙升、通缩 | 🟡 P2 | 通胀/通缩信号 |
| ALERT-DEFAULT | C1/C2 | 违约、降级、破产、债务危机 | 🟡 P2 | 信用事件 |
| ALERT-RESERVE | P003 | 去美元化、储备货币、BRICS | 🟡 P2 | 储备货币地位 |
| ALERT-SHADOW | C4 | 影子银行、加密货币、杠杆 | 🟡 P2 | 金融创新/监管套利 |

## 告警输出格式

每次告警输出为一条 JSON：

```json
{
  "alert_id": "ALERT-YC",
  "severity": "P1",
  "principle_ids": ["P001", "P006"],
  "title": "收益率曲线正式倒挂",
  "current_value": "T10Y2Y = -0.23%",
  "triggered_at": "2026-04-25",
  "note": "参考知识库 knowledge/wiki/concepts/收益率曲线-yield-curve.md 的详细解读",
  "suggested_action": "生成专题简报：收益率曲线倒挂分析"
}
```

## 告警生命周期

- **首次触发**：生成告警并记录到 `lab/reports/alerts.jsonl`
- **持续中**：每日在 eco-brief 中展示，标"持续中"
- **已解除**：条件不再满足 → 标记 resolved，记录持续时间
- **告警历史**：用于复盘——"这个告警对了还是虚警？"
