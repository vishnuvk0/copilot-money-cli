import { apiFetch } from "./client";
import type {
  Account,
  Holding,
  BalanceHistoryResponse,
  AllocationResponse,
  AllocationHistoryResponse,
  FilingResponse,
  SyncStatusResponse,
  Trade,
  Period,
} from "../types";

export function fetchAccounts() {
  return apiFetch<{ accounts: Account[] }>("/investments/accounts");
}

export function fetchHoldings(accountId?: string) {
  const params = accountId ? `?account_id=${accountId}` : "";
  return apiFetch<{ holdings: Holding[] }>(`/investments/holdings${params}`);
}

export function fetchBalanceHistory(period: Period, accountId?: string) {
  const params = new URLSearchParams({ period });
  if (accountId) params.set("account_id", accountId);
  return apiFetch<BalanceHistoryResponse>(
    `/investments/balance-history?${params}`
  );
}

export function fetchAllocation(date: string) {
  return apiFetch<AllocationResponse>(`/investments/allocation/${date}`);
}

export function fetchFiling(date: string) {
  return apiFetch<FilingResponse>(`/investments/filing/${date}`);
}

export function fetchSyncStatus() {
  return apiFetch<SyncStatusResponse>("/investments/sync-status");
}

export function fetchAllocationHistory(
  period: Period,
  granularity: "weekly" | "monthly" = "weekly"
) {
  const params = new URLSearchParams({ period, granularity });
  return apiFetch<AllocationHistoryResponse>(
    `/investments/allocation-history?${params}`
  );
}

export function fetchTrades(period: Period, securityId?: string) {
  const params = new URLSearchParams({ period });
  if (securityId) params.set("security_id", securityId);
  return apiFetch<{ trades: Trade[] }>(`/investments/trades?${params}`);
}

export function triggerSync() {
  return apiFetch<{ status: string }>("/investments/sync", { method: "POST" });
}
