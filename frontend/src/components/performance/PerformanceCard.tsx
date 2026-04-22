import { usePerformance } from "../../hooks/usePerformance";
import { Skeleton } from "../shared/LoadingSkeleton";
import { formatPercent, formatDate } from "../../lib/format";
import type { Period, PerformanceMetrics } from "../../types";

interface Props {
  period: Period;
}

interface MetricTile {
  label: string;
  key: keyof PerformanceMetrics;
  format: (v: number) => string;
}

const METRICS: MetricTile[] = [
  { label: "Time-Weighted Return", key: "twr", format: formatPercent },
  { label: "Money-Weighted (XIRR)", key: "mwr_xirr", format: formatPercent },
  {
    label: "Sharpe Ratio",
    key: "sharpe_ratio",
    format: (v) => v.toFixed(2),
  },
  {
    label: "Volatility",
    key: "volatility",
    format: formatPercent,
  },
  {
    label: "Beta",
    key: "beta",
    format: (v) => v.toFixed(2),
  },
  {
    label: "Max Drawdown",
    key: "max_drawdown",
    format: formatPercent,
  },
];

function colorClass(key: string, value: number): string {
  if (key === "max_drawdown") return "text-loss-red";
  if (key === "beta" || key === "sharpe_ratio" || key === "volatility") return "text-navy-900";
  return value >= 0 ? "text-gain-green" : "text-loss-red";
}

export function PerformanceCard({ period }: Props) {
  const { data, isLoading } = usePerformance(period);

  if (isLoading) {
    return (
      <div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      </div>
    );
  }

  const metrics = data?.metrics;
  if (!metrics) return null;

  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {METRICS.map(({ label, key, format }) => {
          const raw = metrics[key];
          const value = typeof raw === "number" ? raw : null;
          return (
            <div
              key={key}
              className="rounded-xl bg-cream-50/80 border border-cream-200/50 px-4 py-3"
            >
              <p className="text-[11px] text-muted font-medium mb-1">
                {label}
              </p>
              {value !== null ? (
                <p
                  className={`text-lg font-semibold font-mono ${colorClass(key, value)}`}
                >
                  {format(value)}
                </p>
              ) : (
                <p className="text-lg font-mono text-muted">--</p>
              )}
            </div>
          );
        })}
      </div>

      {(metrics.best_day || metrics.worst_day) && (
        <div className="mt-3 flex gap-4 text-[11px] text-muted">
          {metrics.best_day && (
            <span>
              Best day: {formatPercent(metrics.best_day.return)} on{" "}
              {formatDate(metrics.best_day.date)}
            </span>
          )}
          {metrics.worst_day && (
            <span>
              Worst day: {formatPercent(metrics.worst_day.return)} on{" "}
              {formatDate(metrics.worst_day.date)}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
