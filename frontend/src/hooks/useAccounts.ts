import { useQuery } from "@tanstack/react-query";
import { fetchAccounts } from "../api/investments";

export function useAccounts() {
  return useQuery({
    queryKey: ["accounts"],
    queryFn: fetchAccounts,
    staleTime: 60_000,
  });
}
