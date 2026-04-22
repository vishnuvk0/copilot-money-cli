import { useQuery } from "@tanstack/react-query";
import { fetchDailyReturns } from "../api/returns";
import type { Period } from "../types";

export function useDailyReturns(
  period: Period,
  accountId?: string,
  cumulative = false
) {
  return useQuery({
    queryKey: ["daily-returns", period, accountId, cumulative],
    queryFn: () => fetchDailyReturns(period, accountId, cumulative),
    staleTime: 60_000,
  });
}
