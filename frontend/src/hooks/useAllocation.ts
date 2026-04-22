import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { fetchAllocation } from "../api/investments";

export function useAllocation(date: string) {
  return useQuery({
    queryKey: ["allocation", date],
    queryFn: () => fetchAllocation(date),
    staleTime: Infinity,
    placeholderData: keepPreviousData,
    enabled: !!date,
  });
}
