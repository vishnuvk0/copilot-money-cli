import { useSyncStatus } from "../../hooks/useSyncStatus";
import { formatRelativeTime } from "../../lib/format";

export function Header() {
  const { data } = useSyncStatus();
  const lastSync = data?.last_sync;
  const isRunning = lastSync?.status === "running";
  const completedAt = lastSync?.completed_at;

  return (
    <header className="flex items-center justify-between pb-8">
      <h1 className="font-serif text-2xl font-bold text-navy-900 tracking-tight">
        Portfolio
      </h1>
      {lastSync && (
        <div className="flex items-center gap-2 text-sm text-muted">
          {isRunning ? (
            <>
              <span className="inline-block h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
              <span>Syncing...</span>
            </>
          ) : completedAt ? (
            <>
              <span className="inline-block h-2 w-2 rounded-full bg-gain-green" />
              <span>Synced {formatRelativeTime(completedAt)}</span>
            </>
          ) : null}
        </div>
      )}
    </header>
  );
}
