import { useQuery } from "@tanstack/react-query";
import { fetchBalanceHistory } from "../api/investments";
import type { Period } from "../types";

export function useBalanceHistory(period: Period, accountId?: string) {
  return useQuery({
    queryKey: ["balance-history", period, accountId],
    queryFn: () => fetchBalanceHistory(period, accountId),
    staleTime: 60_000,
  });
}
