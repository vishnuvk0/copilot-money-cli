export interface Account {
  id: string;
  item_id: string;
  name: string;
  sub_type: string;
  institution_id: string;
  balance: number;
  is_manual: boolean;
  has_historical: boolean;
  has_live_balance: boolean;
  updated_at: string;
}

export interface Holding {
  id: number;
  account_id: string;
  item_id: string;
  symbol: string;
  name: string;
  quantity: number;
  current_price: number;
  cost_basis: number;
  total_return: number;
  average_cost: number;
  security_id: string;
  synced_at: string;
}

export interface BalancePoint {
  date: string;
  balance: number;
}

export interface BalanceHistoryResponse {
  period: string;
  account_id: string | null;
  data: BalancePoint[];
}

export interface AllocationHolding {
  symbol: string;
  name: string;
  type: string;
  quantity: number;
  price: number;
  value: number;
  weight_pct: number;
  cost_basis_per_share: number;
  unrealized_gain_pct: number | null;
}

export interface AllocationResponse {
  date: string;
  total_value: number;
  holdings: AllocationHolding[];
}

export interface FilingPosition {
  symbol: string;
  name: string;
  type: string;
  quantity: number;
  price: number;
  market_value: number;
  cost_basis: number;
  weight_pct: number;
  unrealized_gain_pct: number | null;
}

export interface SectorBreakdown {
  type: string;
  market_value: number;
  weight_pct: number;
}

export interface FilingResponse {
  filing_date: string;
  total_market_value: number;
  total_cost_basis: number;
  positions: FilingPosition[];
  sector_breakdown: SectorBreakdown[];
}

export interface PerformanceMetrics {
  twr: number | null;
  mwr_xirr: number | null;
  sharpe_ratio: number | null;
  volatility: number | null;
  beta: number | null;
  max_drawdown: number | null;
  best_day: { date: string; return: number } | null;
  worst_day: { date: string; return: number } | null;
}

export interface PerformanceResponse {
  period: string;
  account_id: string | null;
  metrics: PerformanceMetrics;
}

export interface DailyReturn {
  date: string;
  return: number;
}

export interface ComparisonResponse {
  portfolio: {
    twr: number | null;
    data: DailyReturn[];
  };
  benchmark: {
    name: string;
    twr: number | null;
    data: DailyReturn[];
  };
  alpha: number | null;
  beta: number | null;
}

export interface SyncLog {
  id: number;
  started_at: string;
  completed_at: string;
  status: string;
  accounts_synced: number;
  error: string | null;
}

export interface DataRange {
  min_date: string;
  max_date: string;
  count: number;
}

export interface SyncStatusResponse {
  last_sync: SyncLog | null;
  data_ranges: Record<string, DataRange>;
}

export interface AllocationHistorySecurity {
  symbol: string;
  values: number[];
  weights: number[];
}

export interface AllocationHistoryResponse {
  dates: string[];
  securities: AllocationHistorySecurity[];
}

export interface Trade {
  date: string;
  symbol: string;
  name: string;
  action: "BUY" | "SELL";
  quantity_change: number;
  price_on_date: number;
  estimated_value: number;
}

export type Period = "1D" | "1W" | "1M" | "3M" | "6M" | "YTD" | "1Y" | "ALL";
