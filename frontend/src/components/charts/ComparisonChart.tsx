import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { useComparison } from "../../hooks/useComparison";
import { ChartSkeleton } from "../shared/LoadingSkeleton";
import { formatDateShort, formatPercent } from "../../lib/format";
import { CHART_GREEN, CHART_BLUE } from "../../lib/constants";
import type { Period } from "../../types";

interface Props {
  period: Period;
}

interface ChartRow {
  date: string;
  portfolio: number;
  benchmark: number;
}

export function ComparisonChart({ period }: Props) {
  const { data, isLoading } = useComparison(period);

  const chartData = useMemo<ChartRow[]>(() => {
    if (!data) return [];
    const pMap = new Map(data.portfolio.data.map((d) => [d.date, d.return]));
    const bMap = new Map(data.benchmark.data.map((d) => [d.date, d.return]));
    const allDates = [
      ...new Set([
        ...data.portfolio.data.map((d) => d.date),
        ...data.benchmark.data.map((d) => d.date),
      ]),
    ].sort();

    return allDates.map((date) => ({
      date,
      portfolio: (pMap.get(date) ?? 0) * 100,
      benchmark: (bMap.get(date) ?? 0) * 100,
    }));
  }, [data]);

  if (isLoading) return <ChartSkeleton />;

  return (
    <div>
      {chartData.length > 0 ? (
        <div className="h-[300px] -mx-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
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
                tickFormatter={(v: number) => `${v.toFixed(0)}%`}
                tick={{ fontSize: 11, fill: "#94a3b8" }}
                axisLine={false}
                tickLine={false}
                width={45}
              />
              <Tooltip content={<ComparisonTooltip />} />
              <Legend
                verticalAlign="top"
                height={28}
                formatter={(value: string) =>
                  value === "portfolio" ? "Portfolio" : "S&P 500"
                }
              />
              <Line
                type="monotone"
                dataKey="portfolio"
                stroke={CHART_GREEN}
                strokeWidth={2}
                dot={false}
                animationDuration={800}
              />
              <Line
                type="monotone"
                dataKey="benchmark"
                stroke={CHART_BLUE}
                strokeWidth={2}
                dot={false}
                strokeDasharray="4 4"
                animationDuration={800}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="h-[300px] flex items-center justify-center">
          <p className="text-sm text-muted">
            No comparison data available for this period.
          </p>
        </div>
      )}

      {data && (
        <div className="mt-3 flex gap-3">
          {data.alpha !== null && (
            <span className="inline-flex items-center rounded-md bg-cream-100 px-2.5 py-1 text-xs font-medium font-mono text-navy-900">
              Alpha {formatPercent(data.alpha)}
            </span>
          )}
          {data.beta !== null && (
            <span className="inline-flex items-center rounded-md bg-cream-100 px-2.5 py-1 text-xs font-medium font-mono text-navy-900">
              Beta {data.beta.toFixed(2)}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function ComparisonTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-navy-900 text-cream-50 rounded-lg px-3 py-2 text-xs shadow-lg">
      <p className="font-medium mb-1">{label}</p>
      {payload.map((entry: any) => (
        <div key={entry.dataKey} className="flex justify-between gap-4">
          <span style={{ color: entry.color }}>
            {entry.dataKey === "portfolio" ? "Portfolio" : "S&P 500"}
          </span>
          <span className="font-mono">{entry.value.toFixed(2)}%</span>
        </div>
      ))}
    </div>
  );
}
