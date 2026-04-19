import axios from "axios";

const BASE = "http://localhost:8000";
export const api = axios.create({ baseURL: BASE });

export interface SnapshotRow {
  series_id: string;
  name: string;
  latest_date: string;
  latest_value: number;
  group?: number;
  unit?: string;
}

export interface SeriesPoint { date: string; value: number; }

export interface SeriesResponse {
  series_id: string;
  meta: { name: string; group: number; unit: string };
  data: SeriesPoint[];
}

export interface Signal {
  id: string;
  label: string;
  value: string;
  status: "ok" | "warning" | "danger";
  note: string;
}

export interface DiagnosisResponse {
  stage: string;
  stage_color: "ok" | "warning" | "danger";
  signals: Signal[];
}

export const fetchSnapshot  = (): Promise<SnapshotRow[]>       => api.get("/api/snapshot").then(r => r.data);
export const fetchSeries    = (id: string, years = 20): Promise<SeriesResponse> => api.get(`/api/series/${id}`, { params: { years } }).then(r => r.data);
export const fetchDiagnosis = (): Promise<DiagnosisResponse>   => api.get("/api/diagnosis").then(r => r.data);

export interface YieldCurvePoint { maturity: string; months: number; value: number; }
export interface YieldCurveSnapshot { requested_date: string; actual_date: string; points: YieldCurvePoint[]; }
export interface YieldCurveInfo { min_date: string; max_date: string; maturities: string[]; }

export const fetchYieldCurveInfo = (): Promise<YieldCurveInfo> =>
  api.get("/api/yield-curve/info").then(r => r.data);

export const fetchYieldCurve = (dates: string[]): Promise<YieldCurveSnapshot[]> =>
  api.get("/api/yield-curve", { params: { dates: dates.join(",") } }).then(r => r.data);

// --- Regime API ---

export interface AssetTilt {
  asset: string;
  asset_cn: string;
  tilt: number; // -2 to +2
}

export interface AuxSignal {
  id: string;
  label: string;
  value: string;
  status: "ok" | "warning" | "danger" | "neutral";
}

export interface RegimeResponse {
  quadrant: string | null;
  quadrant_cn: string;
  growth: { value: number | null; level: string | null; threshold: number; label: string };
  inflation: { value: number | null; level: string | null; threshold: number; label: string };
  aux_signals: AuxSignal[];
  asset_tilts: AssetTilt[] | null;
  long_term: Record<string, { value: number; status?: string; note: string }>;
}

export interface HistoryRecord {
  date: string;
  debt_cycle_stage: string;
  regime_quadrant: string;
  regime_quadrant_cn: string;
  growth_value: number | null;
  inflation_value: number | null;
  asset_tilts: AssetTilt[] | null;
}

export const fetchRegime = (): Promise<RegimeResponse> =>
  api.get("/api/regime").then(r => r.data);

export const fetchDiagnosisHistory = (limit = 365): Promise<HistoryRecord[]> =>
  api.get("/api/diagnosis/history", { params: { limit } }).then(r => r.data);

export const triggerRefresh = (): Promise<{ status: string; message: string }> =>
  api.post("/api/refresh").then(r => r.data);
