import { useQuery } from "@tanstack/react-query";
import { fetchAllocationHistory } from "../api/investments";
import type { Period } from "../types";

export function useAllocationHistory(
  period: Period,
  granularity: "weekly" | "monthly" = "weekly"
) {
  return useQuery({
    queryKey: ["allocation-history", period, granularity],
    queryFn: () => fetchAllocationHistory(period, granularity),
    staleTime: 60_000,
  });
}
