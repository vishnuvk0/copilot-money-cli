import { useMemo } from "react";
import { AnimatePresence } from "framer-motion";
import { useAllocation } from "../../hooks/useAllocation";
import { useHoldings } from "../../hooks/useHoldings";
import { HoldingRow } from "./HoldingRow";
import { TableSkeleton } from "../shared/LoadingSkeleton";
import { formatCurrency, formatDate } from "../../lib/format";
import type { AllocationHolding } from "../../types";

interface Props {
  date: string;
  isHistorical: boolean;
  searchQuery?: string;
}

export function HoldingsTable({ date, isHistorical, searchQuery = "" }: Props) {
  const { data: allocData, isLoading: allocLoading, isFetching } = useAllocation(date);
  const { data: holdingsData, isLoading: holdingsLoading } = useHoldings();

  // Fallback: convert raw holdings to AllocationHolding shape when allocation is empty
  const { holdings, totalValue } = useMemo(() => {
    const allocHoldings = allocData?.holdings ?? [];
    if (allocHoldings.length > 0) {
      return { holdings: allocHoldings, totalValue: allocData?.total_value ?? 0 };
    }

    // Fallback to current holdings
    if (!holdingsData?.holdings?.length) {
      return { holdings: [] as AllocationHolding[], totalValue: 0 };
    }

    // Aggregate holdings by symbol (multiple accounts may hold same security)
    const bySymbol = new Map<string, AllocationHolding>();
    let total = 0;
    for (const h of holdingsData.holdings) {
      const value = h.quantity * h.current_price;
      total += value;
      const existing = bySymbol.get(h.symbol);
      if (existing) {
        existing.quantity += h.quantity;
        existing.value += value;
      } else {
        bySymbol.set(h.symbol, {
          symbol: h.symbol,
          name: h.name,
          type: "",
          quantity: h.quantity,
          price: h.current_price,
          value,
          weight_pct: 0,
          cost_basis_per_share: h.average_cost,
          unrealized_gain_pct:
            h.average_cost > 0
              ? (h.current_price - h.average_cost) / h.average_cost
              : null,
        });
      }
    }

    // Compute weight percentages
    const result = [...bySymbol.values()]
      .map((h) => ({ ...h, weight_pct: total > 0 ? (h.value / total) * 100 : 0 }))
      .sort((a, b) => b.value - a.value);

    return { holdings: result, totalValue: total };
  }, [allocData, holdingsData]);

  const filteredHoldings = useMemo(() => {
    if (!searchQuery.trim()) return holdings;
    const q = searchQuery.toLowerCase();
    return holdings.filter(
      (h) =>
        h.symbol.toLowerCase().includes(q) ||
        (h.name && h.name.toLowerCase().includes(q))
    );
  }, [holdings, searchQuery]);

  if (allocLoading && holdingsLoading) return <TableSkeleton />;

  return (
    <div>
      {(isFetching || isHistorical) && (
        <div className="flex items-center gap-2 mb-3">
          {isFetching && !allocLoading && (
            <div className="h-1.5 w-1.5 rounded-full bg-navy-500 animate-pulse" />
          )}
          {isHistorical && (
            <span className="text-xs text-muted bg-cream-100 rounded-md px-2 py-0.5">
              {formatDate(date)}
            </span>
          )}
        </div>
      )}

      {totalValue > 0 && (
        <p className="text-xs text-muted mb-3">
          Total {formatCurrency(totalValue)} &middot; {holdings.length} positions
          {searchQuery && filteredHoldings.length !== holdings.length && (
            <span> &middot; {filteredHoldings.length} matched</span>
          )}
        </p>
      )}

      <AnimatePresence mode="popLayout">
        {filteredHoldings.map((h) => (
          <HoldingRow key={h.symbol} holding={h} />
        ))}
      </AnimatePresence>

      {filteredHoldings.length === 0 && (
        <p className="text-sm text-muted py-8 text-center">
          {searchQuery ? "No holdings match your search" : "No holdings data for this date"}
        </p>
      )}
    </div>
  );
}
