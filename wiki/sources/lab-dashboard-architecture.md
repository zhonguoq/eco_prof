---
title: Lab Dashboard Architecture
type: source
tags: [lab, 工程架构, 仪表盘, FRED, FastAPI, React, ECharts]
created: 2026-04-12
updated: 2026-04-12
sources: [lab-dashboard-architecture.md]
---

# Lab Dashboard Architecture

**作者：** 项目内部文档  
**年份：** 2026  
**类型：** 技术架构文档

---

## 核心内容

描述 lab 层的完整技术栈：数据拉取 → REST API → 前端可视化，以及与 wiki 层的关系原则。

---

## 核心论点

- **wiki = 理论大脑，lab = 实践层**：严格分离，lab 引用 wiki 框架决定测量什么、怎么解读，但不自动回写 wiki
- **数据流**：FRED API → Python fetcher → CSV → FastAPI → React + ECharts
- **诊断逻辑**直接实现自 [债务周期阶段判断框架](../analyses/债务周期阶段判断框架.md) 的快速检查清单
- **版本约束**：echarts-for-react@3 必须搭配 ECharts 5.x，不兼容 ECharts 6

---

## 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 数据拉取 | Python + fredapi + pandas | `lab/tools/fetch_us_indicators.py` |
| 后端 API | FastAPI + uvicorn | `lab/dashboard/backend/main.py`，端口 8000 |
| 前端 | React 18 + Vite 5 + TypeScript | `lab/dashboard/frontend/`，端口 5173 |
| 图表 | ECharts 5 via echarts-for-react@3 | **必须 ECharts 5.x** |
| 样式 | Tailwind CSS v3 | 暗色主题 |

---

## API 端点

| 端点 | 说明 |
|------|------|
| `GET /api/snapshot` | 所有指标最新值 |
| `GET /api/series/{id}?years=N` | 单指标历史时序 |
| `GET /api/diagnosis` | 周期阶段诊断（五维信号 + 综合判断） |

---

## 已知局限

1. `DPSACBW027SBOG` 非真实 DSR 百分比，应换用 `TDSP`
2. 数据仅支持手动刷新，尚无定时任务
3. 仅覆盖美国指标，中国部分待建
4. 无历史诊断记录，无告警推送

---

## 关联页面

- [债务周期阶段判断框架](../analyses/债务周期阶段判断框架.md)
- [大债务周期 (Big Debt Cycle)](../concepts/大债务周期-big-debt-cycle.md)
