# Debt Cycle Dashboard

React + FastAPI 仪表盘，可视化美国债务周期关键指标。

## 启动

**1. 启动后端**（在项目根目录）

```bash
python3 -m uvicorn lab.dashboard.backend.main:app --port 8000 --reload
```

**2. 启动前端**

```bash
cd lab/dashboard/frontend
npm run dev
```

打开 http://localhost:5173

## 更新数据

```bash
python3 lab/tools/fetch_us_indicators.py
```

刷新浏览器即可看到最新数据（后端每次请求时读最新 CSV）。

## 目录结构

```
dashboard/
├── backend/
│   ├── main.py          # FastAPI — /api/snapshot, /api/series/{id}, /api/diagnosis
│   └── requirements.txt
└── frontend/
    └── src/
        ├── api/client.ts          # axios 封装 + 类型定义
        ├── components/
        │   ├── KpiCard.tsx        # 单指标卡片
        │   ├── StatusBadge.tsx    # 健康/注意/危险标签
        │   ├── DiagnosisPanel.tsx # 周期阶段诊断面板
        │   ├── LineChart.tsx      # 单序列折线图（支持阈值线）
        │   └── MultiLineChart.tsx # 多序列折线图
        └── App.tsx                # 主页面布局
```
