import { useMemo, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useAllocationHistory } from "../../hooks/useAllocationHistory";
import { PeriodSelector } from "../layout/PeriodSelector";
import { ChartSkeleton } from "../shared/LoadingSkeleton";
import { formatCurrency, formatDateShort } from "../../lib/format";
import type { Period } from "../../types";

// Curated palette — visually distinct, works on light backgrounds
const COLORS = [
  "#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6",
  "#EC4899", "#14B8A6", "#F97316", "#6366F1", "#84CC16",
  "#06B6D4", "#D946EF", "#22D3EE", "#FB923C", "#A78BFA",
  "#34D399", "#FBBF24", "#F87171", "#818CF8", "#2DD4BF",
];

function colorFor(i: number) {
  return COLORS[i % COLORS.length];
}

interface ChartRow {
  date: string;
  [symbol: string]: number | string;
}

export function AllocationChart() {
  const [period, setPeriod] = useState<Period>("1Y");
  const [showAll, setShowAll] = useState(false);
  const granularity = period === "ALL" ? "monthly" : "weekly";
  const { data, isLoading } = useAllocationHistory(period, granularity);

  // Build recharts data: one row per date, one key per symbol (value in $)
  const { chartData, symbols, topSymbols, hasMore } = useMemo(() => {
    if (!data || !data.dates.length)
      return { chartData: [], symbols: [], topSymbols: [], hasMore: false };

    // All securities with meaningful weight (>1% on at least one date)
    const meaningful = data.securities.filter((s) =>
      s.weights.some((w) => w > 1)
    );

    // Sort by average value descending so largest is at the bottom of the stack
    const sorted = [...meaningful].sort((a, b) => {
      const avgA = a.values.reduce((s, v) => s + v, 0) / a.values.length;
      const avgB = b.values.reduce((s, v) => s + v, 0) / b.values.length;
      return avgB - avgA;
    });

    // Top securities: average weight > 1%
    const top = sorted.filter((s) => {
      const avgWeight = s.weights.reduce((sum, w) => sum + w, 0) / s.weights.length;
      return avgWeight > 1;
    });

    const allSyms = sorted.map((s) => s.symbol);
    const topSyms = top.map((s) => s.symbol);

    const rows: ChartRow[] = data.dates.map((d, i) => {
      const row: ChartRow = { date: d };
      for (const sec of sorted) {
        row[sec.symbol] = sec.values[i] ?? 0;
      }
      return row;
    });

    return {
      chartData: rows,
      symbols: allSyms,
      topSymbols: topSyms,
      hasMore: allSyms.length > topSyms.length,
    };
  }, [data]);

  const visibleSymbols = showAll ? symbols : topSymbols;

  if (isLoading) return <ChartSkeleton />;

  return (
    <div>
      {chartData.length > 0 ? (
        <div className="h-[300px] -mx-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={chartData}
              margin={{ top: 4, right: 0, left: 0, bottom: 0 }}
              stackOffset="expand"
            >
              <XAxis
                dataKey="date"
                tickFormatter={formatDateShort}
                tick={{ fontSize: 11, fill: "#94a3b8" }}
                axisLine={false}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                tick={{ fontSize: 11, fill: "#94a3b8" }}
                axisLine={false}
                tickLine={false}
                width={40}
              />
              <Tooltip content={<AllocTooltip />} />
              {symbols.map((sym, i) => (
                <Area
                  key={sym}
                  type="monotone"
                  dataKey={sym}
                  stackId="1"
                  stroke={colorFor(i)}
                  fill={colorFor(i)}
                  fillOpacity={0.85}
                  strokeWidth={0}
                  animationDuration={600}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="h-[300px] flex items-center justify-center">
          <p className="text-sm text-muted">
            No allocation history available for this period.
          </p>
        </div>
      )}

      <div className="mt-4 flex items-center justify-between">
        <PeriodSelector value={period} onChange={setPeriod} />
      </div>

      {/* Legend */}
      {visibleSymbols.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1">
          {visibleSymbols.map((sym) => {
            const idx = symbols.indexOf(sym);
            return (
              <div key={sym} className="flex items-center gap-1">
                <span
                  className="inline-block w-2 h-2 rounded-full"
                  style={{ backgroundColor: colorFor(idx) }}
                />
                <span className="text-[11px] text-muted font-medium">
                  {sym}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {hasMore && (
        <button
          onClick={() => setShowAll((v) => !v)}
          className="mt-2 text-[11px] font-medium text-navy-500 hover:text-navy-900 transition-colors"
        >
          {showAll
            ? "Show less"
            : `See all ${symbols.length} securities`}
        </button>
      )}
    </div>
  );
}

// Custom tooltip
function AllocTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;

  // Sort by value descending for the tooltip
  const sorted = [...payload]
    .filter((p: any) => p.value > 0)
    .sort((a: any, b: any) => b.value - a.value);

  const total = sorted.reduce((s: number, p: any) => s + p.value, 0);

  return (
    <div className="bg-navy-900 text-cream-50 rounded-lg px-3 py-2 text-xs shadow-lg max-h-[280px] overflow-y-auto">
      <p className="font-medium mb-1.5">{label}</p>
      {sorted.slice(0, 10).map((entry: any) => (
        <div key={entry.dataKey} className="flex justify-between gap-4 leading-relaxed">
          <span className="flex items-center gap-1.5">
            <span
              className="inline-block w-1.5 h-1.5 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            {entry.dataKey}
          </span>
          <span className="font-mono">
            {formatCurrency(entry.value)}{" "}
            <span className="text-cream-400">
              ({total > 0 ? ((entry.value / total) * 100).toFixed(1) : 0}%)
            </span>
          </span>
        </div>
      ))}
      {sorted.length > 10 && (
        <p className="text-cream-400 mt-1">+{sorted.length - 10} more</p>
      )}
    </div>
  );
}
