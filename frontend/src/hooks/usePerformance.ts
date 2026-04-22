import { useQuery } from "@tanstack/react-query";
import { fetchPerformance } from "../api/returns";
import type { Period } from "../types";

export function usePerformance(period: Period, accountId?: string) {
  return useQuery({
    queryKey: ["performance", period, accountId],
    queryFn: () => fetchPerformance(period, accountId),
    staleTime: 60_000,
  });
}
