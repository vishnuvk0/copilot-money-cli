import { useQuery } from "@tanstack/react-query";
import { fetchHoldings } from "../api/investments";

export function useHoldings(accountId?: string) {
  return useQuery({
    queryKey: ["holdings", accountId],
    queryFn: () => fetchHoldings(accountId),
    staleTime: 60_000,
  });
}
