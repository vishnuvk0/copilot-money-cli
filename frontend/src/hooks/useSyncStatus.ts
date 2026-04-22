import { useQuery } from "@tanstack/react-query";
import { fetchSyncStatus } from "../api/investments";

export function useSyncStatus() {
  return useQuery({
    queryKey: ["sync-status"],
    queryFn: fetchSyncStatus,
    staleTime: 30_000,
  });
}
