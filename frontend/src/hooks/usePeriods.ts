import { useQuery } from "@tanstack/react-query";
import { fetchPeriods } from "../api/returns";

export function usePeriods(accountId?: string) {
  return useQuery({
    queryKey: ["periods", accountId],
    queryFn: () => fetchPeriods(accountId),
    staleTime: 60_000,
  });
}
