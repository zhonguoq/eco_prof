# Lab Dashboard Architecture
# 数据仪表盘架构文档

**Type:** Internal technical documentation  
**Created:** 2026-04-12  
**Status:** Active (v1.0)

---

## Overview

This project extends the personal economics knowledge base with a **lab layer** — a live data practice environment that sits alongside the wiki. The lab fetches real macroeconomic data, runs diagnostic analysis, and surfaces results through an interactive dashboard.

The guiding principle: **wiki = theory brain, lab = practice layer**. They are strictly separated. The lab references the wiki's frameworks to decide what to measure and how to interpret it, but never writes back to the wiki automatically. Only conclusions with long-term value are manually archived to `wiki/analyses/`.

---

## Directory Layout

```
eco_knowladge_base/
├── raw/                        # Source documents (read-only)
├── wiki/                       # LLM-maintained knowledge base
└── lab/
    ├── tools/
    │   ├── fetch_us_indicators.py   # FRED data fetcher
    │   └── dashboard/
    │       ├── backend/             # FastAPI REST API
    │       │   ├── main.py
    │       │   └── requirements.txt
    │       └── frontend/            # React + ECharts UI
    │           ├── src/
    │           │   ├── api/client.ts
    │           │   ├── components/
    │           │   └── App.tsx
    │           └── package.json
    ├── data/                    # Fetched CSV files (FRED output)
    └── reports/                 # Analysis snapshots (markdown)
```

---

## Component 1: Data Fetcher — `fetch_us_indicators.py`

**Language:** Python 3  
**Dependencies:** `fredapi`, `pandas`  
**Data source:** FRED (Federal Reserve Economic Data), free API, registration required

### What it fetches

Twelve series mapped to the three indicator groups from `wiki/analyses/债务周期阶段判断框架.md`:

| Group | Series ID | Indicator |
|-------|-----------|-----------|
| 1 — Debt Health | TCMDO | Total Credit Market Debt ($B) |
| 1 | GDP | Nominal GDP ($B, quarterly SAAR) |
| 1 | GFDEGDQ188S | Federal Debt / GDP (%) |
| 1 | DPSACBW027SBOG | Household Debt (proxy) |
| 2 — Monetary Policy | FEDFUNDS | Federal Funds Rate (%) |
| 2 | DGS2 | 2-Year Treasury Yield (%) |
| 2 | DGS10 | 10-Year Treasury Yield (%) |
| 2 | T10Y2Y | 10Y-2Y Spread (%, FRED computed) |
| 3 — Nominal Growth vs Rates | CPIAUCSL | CPI All Urban (index) |
| 3 | GDP_YOY | Nominal GDP YoY growth (derived) |
| Early Warning | BAMLH0A0HYM2 | ICE BofA HY OAS Credit Spread (%) |
| Early Warning | DRCCLACBS | Credit Card Delinquency Rate (%) |

### Output files

- **Individual series:** `lab/data/fred_<series_id_lower>_<YYYYMMDD>.csv`
- **Snapshot summary:** `lab/data/fred_snapshot_<YYYYMMDD>.csv` — one row per series with latest value and date

### How to run

```bash
# From project root
python3 lab/tools/fetch_us_indicators.py
```

### API key

Store as environment variable `FRED_API_KEY`, or it falls back to the hardcoded key in the script. For production use, prefer the environment variable.

---

## Component 2: Backend API — `lab/dashboard/backend/main.py`

**Language:** Python 3  
**Framework:** FastAPI  
**Dependencies:** `fastapi`, `uvicorn[standard]`, `pandas`

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/snapshot` | Latest value for every indicator, with metadata |
| GET | `/api/series/{id}?years=N` | Full historical time series for one indicator (default 20 years) |
| GET | `/api/diagnosis` | Computed cycle-stage signals and overall stage judgment |
| GET | `/api/series` | List all available series with metadata |

### Diagnosis logic (`/api/diagnosis`)

Implements the 快速检查清单 from `wiki/analyses/债务周期阶段判断框架.md`. Evaluates five dimensions:

1. **Yield curve** (T10Y2Y): negative → danger, < 0.5% → warning, else ok
2. **Policy rate space** (FEDFUNDS): < 0.5% → danger, < 2% → warning, else ok
3. **Nominal growth vs nominal rate** (GDP_YOY vs DGS10): rate > growth → warning/danger
4. **HY credit spread** (BAMLH0A0HYM2): > 8% → danger, > 5% → warning
5. **Credit card delinquency** (DRCCLACBS): > 4% → danger, > 3% → warning

Overall stage is derived from the count of danger/warning signals:
- ≥ 2 danger → 萧条 / 去杠杆期
- 1 danger or ≥ 3 warning → 顶部 / 调整期
- ≥ 1 warning → 泡沫中后期 / 过渡
- all ok → 早期健康 / 正常化

### File resolution

The backend always reads the **latest** CSV file matching the pattern `fred_snapshot_*.csv` (sorted alphabetically, last entry). This means running the fetcher and refreshing the browser is all that's needed to update data — no server restart required.

### How to run

```bash
# From project root
python3 -m uvicorn lab.dashboard.backend.main:app --port 8000 --reload
```

---

## Component 3: Frontend — `lab/dashboard/frontend/`

**Language:** TypeScript  
**Framework:** React 18 + Vite 5  
**Chart library:** Apache ECharts 5 via `echarts-for-react@3`  
**Styling:** Tailwind CSS v3

> **Version constraint:** `echarts-for-react@3` requires **ECharts 5.x**. Do NOT upgrade to ECharts 6 — it breaks compatibility.

### Component tree

```
App.tsx
├── DiagnosisPanel        — calls /api/diagnosis, shows 5 signals + stage badge
├── KpiCard (×7)          — calls /api/snapshot, one card per key indicator
├── LineChart (×6)        — calls /api/series/{id}, single time-series with optional threshold line + markArea
└── MultiLineChart (×1)   — calls /api/series for multiple ids, overlaid on one chart
```

### Key design decisions

**ErrorBoundary wrapping:** Every chart section is wrapped in an `ErrorBoundary`. If one chart fails, the rest of the page continues to render. The black-screen-of-death problem is prevented at the component level.

**Threshold visualization:** Uses ECharts `markLine` (dashed reference line) + `markArea` (shaded danger zone) instead of `visualMap piecewise`. The `visualMap` approach conflicts with `areaStyle` on line charts — it was removed.

**No `opts={{ renderer: "svg" }}`:** The SVG renderer flag was removed. Some ECharts 5 builds have issues with this prop via `echarts-for-react`. Default canvas renderer is used.

**Dark theme:** Hardcoded dark palette (`bg-gray-950` base). No light mode.

### Dashboard layout (top to bottom)

1. **Header** — title + latest data date badge
2. **Diagnosis Panel** — cycle stage verdict + 5-signal breakdown (green/amber/red)
3. **KPI Cards** (7 cards) — snapshot values with color-coded status borders
4. **Rates & Yield Curve** (3 charts) — 10Y-2Y spread, rates corridor, GDP growth vs 10Y
5. **Debt Health** (2 charts) — federal debt/GDP, total credit
6. **Early Warning** (2 charts) — HY credit spread, credit card delinquency

### Color coding

| Status | Color | Trigger |
|--------|-------|---------|
| 健康 (ok) | Emerald | All thresholds normal |
| 注意 (warning) | Amber | Approaching danger zone |
| 危险 (danger) | Red | Threshold breached |

---

## Daily Workflow

### Update data

```bash
python3 lab/tools/fetch_us_indicators.py
```

New CSVs are written to `lab/data/`. The backend picks them up automatically on the next request.

### Start the dashboard

**Terminal 1 — backend:**
```bash
python3 -m uvicorn lab.dashboard.backend.main:app --port 8000 --reload
```

**Terminal 2 — frontend:**
```bash
cd lab/dashboard/frontend
npm run dev
```

Open: http://localhost:5173

---

## Known Limitations & Future Work

1. **DPSACBW027SBOG is not a true DSR %** — it's total household debt in $B. The correct DSR series is `TDSP` (Total Debt Service Payments as % of Disposable Personal Income). Should be swapped in the fetcher.

2. **No auto-refresh** — data only updates when the fetcher is run manually. A cron job or scheduled task would enable daily automatic updates.

3. **US only** — China indicators (M2, credit impulse, property sector data) are not yet implemented. Planned as a second fetch script.

4. **No historical diagnosis log** — the diagnosis is always computed from the latest snapshot. Tracking how the stage judgment changes over time would be valuable.

5. **No alerts** — the wiki framework defines alert thresholds, but no push notification or email alert is wired up.

---

## Dependencies Summary

### Python

```
fredapi>=0.4.3
pandas>=2.0.0
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
```

### Node.js

```
echarts: 5.x  (must be 5.x, not 6.x)
echarts-for-react: ^3.0.6
react: ^18
axios: latest
tailwindcss: ^3
vite: ^5
```
