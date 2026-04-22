import { usePeriods } from "../../hooks/usePeriods";
import { TableSkeleton } from "../shared/LoadingSkeleton";
import { formatPercent } from "../../lib/format";
import type { PerformanceMetrics } from "../../types";

const PERIOD_ORDER = ["1D", "1W", "1M", "3M", "6M", "YTD", "1Y", "ALL"];

function fmt(v: number | null, formatter: (n: number) => string): string {
  return v !== null ? formatter(v) : "--";
}

export function PeriodsTable() {
  const { data, isLoading } = usePeriods();

  if (isLoading) return <TableSkeleton />;

  const periods = data?.periods ?? {};

  const rows = PERIOD_ORDER.filter((p) => p in periods).map((p) => ({
    period: p,
    metrics: periods[p] as PerformanceMetrics,
  }));

  return (
    <div>
      {rows.length > 0 ? (
        <div className="overflow-x-auto -mx-5 px-5">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[11px] text-muted font-medium">
                <th className="text-left pb-2 pr-4">Period</th>
                <th className="text-right pb-2 pr-4">TWR</th>
                <th className="text-right pb-2 pr-4">Sharpe</th>
                <th className="text-right pb-2 pr-4">Volatility</th>
                <th className="text-right pb-2">Max Drawdown</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ period, metrics }) => (
                <tr
                  key={period}
                  className="border-t border-cream-200/50"
                >
                  <td className="py-2.5 pr-4 font-medium text-navy-900">
                    {period}
                  </td>
                  <td className="py-2.5 pr-4 text-right font-mono">
                    <span
                      className={
                        metrics.twr !== null && metrics.twr >= 0
                          ? "text-gain-green"
                          : metrics.twr !== null
                            ? "text-loss-red"
                            : "text-muted"
                      }
                    >
                      {fmt(metrics.twr, formatPercent)}
                    </span>
                  </td>
                  <td className="py-2.5 pr-4 text-right font-mono text-muted">
                    {fmt(metrics.sharpe_ratio, (v) => v.toFixed(2))}
                  </td>
                  <td className="py-2.5 pr-4 text-right font-mono text-muted">
                    {fmt(metrics.volatility, formatPercent)}
                  </td>
                  <td className="py-2.5 text-right font-mono text-muted">
                    {fmt(metrics.max_drawdown, formatPercent)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-muted py-8 text-center">
          No period data available
        </p>
      )}
    </div>
  );
}
