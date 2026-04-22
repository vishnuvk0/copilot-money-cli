import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { fetchFiling } from "../api/investments";

export function useFiling(date: string) {
  return useQuery({
    queryKey: ["filing", date],
    queryFn: () => fetchFiling(date),
    staleTime: Infinity,
    placeholderData: keepPreviousData,
    enabled: !!date,
  });
}
