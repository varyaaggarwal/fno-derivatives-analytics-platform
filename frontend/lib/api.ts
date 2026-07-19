const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error ${res.status} on ${path}`);
  return res.json();
}

export interface ChainRow {
  strike: number;
  option_type: "call" | "put";
  last_price: number;
  open_interest: number;
  implied_volatility: number;
  theoretical_price: number;
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
}

export interface ChainResponse {
  spot: number;
  expiry_days: number;
  timestamp: string;
  rows: ChainRow[];
}

export interface InterpretationCard {
  metric: string;
  value: number | string | null;
  sentiment?: string;
  note: string;
}

export interface InterpretationResponse {
  pcr: InterpretationCard;
  max_pain: InterpretationCard;
  iv_spike: InterpretationCard;
}

export interface PnlDecomposeResponse {
  delta_pnl: number;
  gamma_pnl: number;
  theta_pnl: number;
  vega_pnl: number;
  residual_pnl: number;
  actual_pnl: number;
  primary_driver: string;
}

export interface DosSummary {
  total_trades: number;
  win_rate_pct: number;
  avg_pnl_rupees: number;
  total_pnl_rupees: number;
  sl_hit_rate_pct: number;
  initial_sl_hits: number;
  trailing_sl_hits: number;
  market_close_exits: number;
  best_trade_rupees: number;
  worst_trade_rupees: number;
}

export interface DosTrade {
  session_date: string;
  day_type: string;
  entry_time: string;
  exit_time: string;
  option_type: string;
  strike: number;
  premium_sold: number;
  premium_exit: number;
  exit_reason: string;
  pnl_rupees: number;
  cumulative_pnl: number;
}

export interface DosBacktestResponse {
  summary: DosSummary;
  trades: DosTrade[];
}

export interface DosLiveSignal {
  day_type: string;
  bnf_fut: number;
  supertrend: number;
  trend: "up" | "down";
  signal: "CE" | "PE" | null;
  recommended_strike: number | null;
  is_mock: boolean;
}

export interface VolSurfaceRow {
  strike: number;
  option_type: "call" | "put";
  implied_volatility: number;
  expiry_days: number;
}

export interface HealthResponse {
  status: string;
  live_nse: boolean;
  supabase_configured: boolean;
}

export const api = {
  health: () => getJSON<HealthResponse>(`/api/health`),
  chain: (expiryDays = 6, spot = 24350) => getJSON<ChainResponse>(`/api/chain?expiry_days=${expiryDays}&spot=${spot}`),
  interpretation: (expiryDays = 6, spot = 24350) => getJSON<InterpretationResponse>(`/api/interpretation?expiry_days=${expiryDays}&spot=${spot}`),
  pnlDecompose: (strike = 24350) => getJSON<PnlDecomposeResponse>(`/api/pnl-decompose?strike=${strike}`),
  dosBacktest: (weeks = 8) => getJSON<DosBacktestResponse>(`/api/dos/backtest?n_weeks=${weeks}`),
  dosLiveSignal: () => getJSON<DosLiveSignal>(`/api/dos/live-signal`),
  volSurface: (spot = 24350) => getJSON<{ spot: number; rows: VolSurfaceRow[]; data_source?: string }>(`/api/vol-surface?spot=${spot}`),
};
