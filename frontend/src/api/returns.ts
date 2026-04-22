import { apiFetch } from "./client";
import type {
  PerformanceResponse,
  DailyReturn,
  ComparisonResponse,
  PerformanceMetrics,
  Period,
} from "../types";

export function fetchPerformance(period: Period, accountId?: string) {
  const params = new URLSearchParams({ period });
  if (accountId) params.set("account_id", accountId);
  return apiFetch<PerformanceResponse>(`/returns/performance?${params}`);
}

export function fetchDailyReturns(
  period: Period,
  accountId?: string,
  cumulative = false
) {
  const params = new URLSearchParams({ period });
  if (accountId) params.set("account_id", accountId);
  if (cumulative) params.set("cumulative", "true");
  return apiFetch<{ period: string; cumulative: boolean; data: DailyReturn[] }>(
    `/returns/daily-returns?${params}`
  );
}

export function fetchComparison(period: Period, accountId?: string) {
  const params = new URLSearchParams({ period });
  if (accountId) params.set("account_id", accountId);
  return apiFetch<ComparisonResponse>(`/returns/comparison?${params}`);
}

export function fetchPeriods(accountId?: string) {
  const params = accountId ? `?account_id=${accountId}` : "";
  return apiFetch<{
    account_id: string | null;
    periods: Record<string, PerformanceMetrics>;
  }>(`/returns/periods${params}`);
}
