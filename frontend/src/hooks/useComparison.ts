import { useQuery } from "@tanstack/react-query";
import { fetchComparison } from "../api/returns";
import type { Period } from "../types";

export function useComparison(period: Period, accountId?: string) {
  return useQuery({
    queryKey: ["comparison", period, accountId],
    queryFn: () => fetchComparison(period, accountId),
    staleTime: 60_000,
  });
}
