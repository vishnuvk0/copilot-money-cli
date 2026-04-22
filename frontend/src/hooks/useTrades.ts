import { useQuery } from "@tanstack/react-query";
import { fetchTrades } from "../api/investments";
import type { Period } from "../types";

export function useTrades(period: Period, securityId?: string) {
  return useQuery({
    queryKey: ["trades", period, securityId],
    queryFn: () => fetchTrades(period, securityId),
    staleTime: 60_000,
  });
}
