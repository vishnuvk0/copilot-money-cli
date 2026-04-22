import { useMemo } from "react";
import { useTrades } from "../../hooks/useTrades";
import { TableSkeleton } from "../shared/LoadingSkeleton";
import { formatCurrencyPrecise, formatDate } from "../../lib/format";
import type { Period } from "../../types";
import type { ActionFilterValue } from "../shared/ActionFilter";

interface Props {
  period: Period;
  symbolQuery?: string;
  actionFilter?: ActionFilterValue;
}

export function TradesList({
  period,
  symbolQuery = "",
  actionFilter = "ALL",
}: Props) {
  const { data, isLoading } = useTrades(period);

  const trades = useMemo(() => {
    let list = data?.trades ?? [];
    if (symbolQuery.trim()) {
      const q = symbolQuery.toLowerCase();
      list = list.filter((t) => t.symbol.toLowerCase().includes(q));
    }
    if (actionFilter !== "ALL") {
      list = list.filter((t) => t.action === actionFilter);
    }
    return list;
  }, [data, symbolQuery, actionFilter]);

  if (isLoading) return <TableSkeleton />;

  return (
    <div>
      {trades.length > 0 ? (
        <div className="overflow-x-auto -mx-5 px-5">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[11px] text-muted font-medium">
                <th className="text-left pb-2 pr-4">Date</th>
                <th className="text-left pb-2 pr-4">Symbol</th>
                <th className="text-left pb-2 pr-4">Action</th>
                <th className="text-right pb-2 pr-4">Qty</th>
                <th className="text-right pb-2 pr-4">Price</th>
                <th className="text-right pb-2">Value</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((t, i) => (
                <tr
                  key={`${t.date}-${t.symbol}-${i}`}
                  className="border-t border-cream-200/50"
                >
                  <td className="py-2.5 pr-4 text-muted whitespace-nowrap">
                    {formatDate(t.date)}
                  </td>
                  <td className="py-2.5 pr-4 font-medium text-navy-900">
                    {t.symbol}
                  </td>
                  <td className="py-2.5 pr-4">
                    <span
                      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${
                        t.action === "BUY"
                          ? "bg-gain-bg text-gain-green"
                          : "bg-loss-bg text-loss-red"
                      }`}
                    >
                      {t.action}
                    </span>
                  </td>
                  <td className="py-2.5 pr-4 text-right font-mono text-muted">
                    {t.quantity_change.toLocaleString("en-US", {
                      maximumFractionDigits: 4,
                    })}
                  </td>
                  <td className="py-2.5 pr-4 text-right font-mono text-muted">
                    {formatCurrencyPrecise(t.price_on_date)}
                  </td>
                  <td className="py-2.5 text-right font-mono font-medium text-navy-900">
                    {formatCurrencyPrecise(t.estimated_value)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-muted py-8 text-center">
          No trades found for this period
        </p>
      )}
    </div>
  );
}
