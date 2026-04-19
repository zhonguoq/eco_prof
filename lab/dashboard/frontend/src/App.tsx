import { useEffect, useState } from "react";
import { fetchSnapshot, SnapshotRow, triggerRefresh } from "./api/client";
import DiagnosisPanel from "./components/DiagnosisPanel";
import ErrorBoundary from "./components/ErrorBoundary";
import KpiCard from "./components/KpiCard";
import LineChart from "./components/LineChart";
import MultiLineChart from "./components/MultiLineChart";
import RegimePanel from "./components/RegimePanel";
import RegimeTimeline from "./components/RegimeTimeline";
import YieldCurveChart from "./components/YieldCurveChart";
import "./index.css";

function getRow(snapshot: SnapshotRow[], id: string) {
  return snapshot.find(r => r.series_id === id);
}

type Status = "ok" | "warning" | "danger" | "neutral";

function spreadStatus(v: number): Status {
  return v < 0 ? "danger" : v < 0.5 ? "warning" : "ok";
}
function rateStatus(v: number): Status {
  return v < 0.5 ? "danger" : v < 2.0 ? "warning" : "ok";
}
function growthVsRateStatus(g: number, r: number): Status {
  const d = g - r;
  return d < -1 ? "danger" : d < 0 ? "warning" : "ok";
}
function hyStatus(v: number): Status {
  return v > 8 ? "danger" : v > 5 ? "warning" : "ok";
}
function delinqStatus(v: number): Status {
  return v > 4 ? "danger" : v > 3 ? "warning" : "ok";
}
function cpiStatus(v: number): Status {
  return v > 5 ? "danger" : v > 3 ? "warning" : "ok";
}
function unrateStatus(v: number): Status {
  return v > 6 ? "danger" : v > 4 ? "warning" : "ok";
}

export default function App() {
  const [snapshot, setSnapshot] = useState<SnapshotRow[]>([]);
  const [updated, setUpdated] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const loadData = () => {
    fetchSnapshot().then(data => {
      setSnapshot(data);
      const dates = data.map(r => r.latest_date).filter(Boolean).sort();
      setUpdated(dates[dates.length - 1] ?? "");
    }).catch(console.error);
  };

  useEffect(() => { loadData(); }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    triggerRefresh()
      .then(() => {
        setTimeout(() => {
          loadData();
          setRefreshing(false);
        }, 5000);
      })
      .catch(() => setRefreshing(false));
  };

  const val  = (id: string) => getRow(snapshot, id)?.latest_value;
  const date = (id: string) => getRow(snapshot, id)?.latest_date;

  const spread   = val("T10Y2Y");
  const fedfunds = val("FEDFUNDS");
  const dgs10    = val("DGS10");
  const gdpYoy   = val("GDP_YOY");
  const hyOas    = val("BAMLH0A0HYM2");
  const delinq   = val("DRCCLACBS");
  const cpiYoy   = val("CPI_YOY");
  const rgdpYoy  = val("RGDP_YOY");
  const unrate   = val("UNRATE");
  const umcsent  = val("UMCSENT");
  const dtwexbgs = val("DTWEXBGS");

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold text-white tracking-tight">宏观环境监测仪表盘</h1>
          <p className="text-xs text-gray-500 mt-0.5">Macro Regime Dashboard · FRED Data · Auto-updated</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="text-xs px-3 py-1.5 rounded-lg border border-gray-700 bg-gray-800 hover:bg-gray-700 disabled:opacity-50 transition-colors"
          >
            {refreshing ? "刷新中..." : "刷新数据"}
          </button>
          {updated && (
            <span className="text-xs text-gray-500 bg-gray-800 px-3 py-1 rounded-full">
              最新数据 {updated}
            </span>
          )}
        </div>
      </header>

      <main className="px-6 py-6 space-y-8 max-w-7xl mx-auto">
        {/* Debt Cycle Diagnosis */}
        <ErrorBoundary>
          <DiagnosisPanel />
        </ErrorBoundary>

        {/* Growth-Inflation Regime */}
        <ErrorBoundary>
          <RegimePanel />
        </ErrorBoundary>

        {/* KPI cards */}
        <section>
          <h2 className="text-xs text-gray-500 uppercase tracking-widest mb-3">关键指标快照</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
            {spread   !== undefined && <KpiCard label="10Y-2Y 利差"  value={spread >= 0 ? `+${spread.toFixed(2)}` : spread.toFixed(2)} unit="%" status={spreadStatus(spread)}            date={date("T10Y2Y")} />}
            {fedfunds !== undefined && <KpiCard label="联邦基金利率"  value={fedfunds.toFixed(2)} unit="%" status={rateStatus(fedfunds)}                                                   date={date("FEDFUNDS")} />}
            {dgs10    !== undefined && <KpiCard label="10Y 国债"     value={dgs10.toFixed(2)}    unit="%"                                                                                   date={date("DGS10")} />}
            {gdpYoy !== undefined && dgs10 !== undefined && <KpiCard label="名义GDP增速" value={gdpYoy.toFixed(1)} unit="%" status={growthVsRateStatus(gdpYoy, dgs10)}                    date={date("GDP_YOY")} />}
            {rgdpYoy !== undefined && <KpiCard label="实际GDP增速" value={rgdpYoy.toFixed(1)} unit="%"                                                                                     date={date("RGDP_YOY")} />}
            {cpiYoy  !== undefined && <KpiCard label="CPI 同比"    value={cpiYoy.toFixed(1)}  unit="%" status={cpiStatus(cpiYoy)}                                                          date={date("CPI_YOY")} />}
            {unrate  !== undefined && <KpiCard label="失业率"      value={unrate.toFixed(1)}  unit="%" status={unrateStatus(unrate)}                                                       date={date("UNRATE")} />}
            {umcsent !== undefined && <KpiCard label="消费者信心"   value={umcsent.toFixed(0)} unit=""                                                                                      date={date("UMCSENT")} />}
            {dtwexbgs !== undefined && <KpiCard label="美元指数"    value={dtwexbgs.toFixed(1)} unit=""                                                                                     date={date("DTWEXBGS")} />}
            {hyOas  !== undefined && <KpiCard label="HY 信用利差"  value={hyOas.toFixed(2)}    unit="%" status={hyStatus(hyOas)}                                                           date={date("BAMLH0A0HYM2")} />}
            {delinq !== undefined && <KpiCard label="信用卡违约率" value={delinq.toFixed(2)}   unit="%" status={delinqStatus(delinq)}                                                      date={date("DRCCLACBS")} />}
          </div>
        </section>

        {/* Group: Growth-Inflation Regime Charts */}
        <section>
          <h2 className="text-xs text-gray-500 uppercase tracking-widest mb-3">增长-通胀趋势</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <ErrorBoundary>
              <LineChart seriesId="RGDP_YOY" title="实际GDP同比增速" unit="%" threshold={2} thresholdLabel="增长阈值 2%" color="#34d399" />
            </ErrorBoundary>
            <ErrorBoundary>
              <LineChart seriesId="CPI_YOY" title="CPI同比通胀率" unit="%" threshold={3} thresholdLabel="通胀阈值 3%" color="#f59e0b" />
            </ErrorBoundary>
            <ErrorBoundary>
              <LineChart seriesId="UNRATE" title="失业率" unit="%" threshold={5} thresholdLabel="警戒线 5%" color="#a78bfa" />
            </ErrorBoundary>
          </div>
        </section>

        {/* Group: Rates & Yield Curve */}
        <section>
          <h2 className="text-xs text-gray-500 uppercase tracking-widest mb-3">货币政策 &amp; 收益率曲线</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <ErrorBoundary>
              <LineChart seriesId="T10Y2Y"  title="10Y-2Y 利差" unit="%" threshold={0} thresholdLabel="倒挂警戒" color="#60a5fa" />
            </ErrorBoundary>
            <ErrorBoundary>
              <MultiLineChart title="利率走廊 Fed Funds / 2Y / 10Y" unit="%" series={[
                { id: "FEDFUNDS", label: "Fed Funds", color: "#f59e0b" },
                { id: "DGS2",     label: "2Y",        color: "#a78bfa" },
                { id: "DGS10",    label: "10Y",       color: "#34d399" },
              ]} />
            </ErrorBoundary>
            <ErrorBoundary>
              <LineChart
                seriesId="GDP_YOY"
                title="名义GDP同比增速 vs 10Y"
                unit="%"
                threshold={dgs10}
                thresholdLabel={dgs10 !== undefined ? `10Y=${dgs10.toFixed(2)}%` : undefined}
                color="#34d399"
              />
            </ErrorBoundary>
            <ErrorBoundary>
              <YieldCurveChart />
            </ErrorBoundary>
          </div>
        </section>

        {/* Group: Debt Health */}
        <section>
          <h2 className="text-xs text-gray-500 uppercase tracking-widest mb-3">债务健康度</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ErrorBoundary>
              <LineChart seriesId="GFDEGDQ188S" title="联邦债务 / GDP" unit="%" color="#f87171" />
            </ErrorBoundary>
            <ErrorBoundary>
              <LineChart seriesId="TCMDO" title="总信贷市场债务" unit=" $B" color="#fb923c" />
            </ErrorBoundary>
          </div>
        </section>

        {/* Group: Long-term / Reserve Currency */}
        <section>
          <h2 className="text-xs text-gray-500 uppercase tracking-widest mb-3">长期结构 &amp; 储备货币</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ErrorBoundary>
              <LineChart seriesId="DTWEXBGS" title="美元贸易加权指数" unit="" color="#38bdf8" />
            </ErrorBoundary>
            <ErrorBoundary>
              <LineChart seriesId="UMCSENT" title="消费者信心指数 (Michigan)" unit="" color="#c084fc" />
            </ErrorBoundary>
          </div>
        </section>

        {/* Early warning */}
        <section>
          <h2 className="text-xs text-gray-500 uppercase tracking-widest mb-3">领先预警信号</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ErrorBoundary>
              <LineChart seriesId="BAMLH0A0HYM2" title="HY 信用利差 (OAS)" unit="%" threshold={5}   thresholdLabel="预警 5%"   color="#c084fc" />
            </ErrorBoundary>
            <ErrorBoundary>
              <LineChart seriesId="DRCCLACBS"    title="信用卡违约率"       unit="%" threshold={3.5} thresholdLabel="预警 3.5%" color="#f472b6" />
            </ErrorBoundary>
          </div>
        </section>

        {/* Regime Timeline */}
        <ErrorBoundary>
          <RegimeTimeline />
        </ErrorBoundary>
      </main>
    </div>
  );
}
