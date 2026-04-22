import { useState, useMemo } from "react";
import {
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";
import { useDailyReturns } from "../../hooks/useDailyReturns";
import { ChartSkeleton } from "../shared/LoadingSkeleton";
import { formatDateShort, formatPercent } from "../../lib/format";
import { CHART_GREEN, CHART_GREEN_LIGHT, CHART_RED } from "../../lib/constants";
import type { Period } from "../../types";

interface Props {
  period: Period;
}

type Mode = "daily" | "cumulative";

export function ReturnsChart({ period }: Props) {
  const [mode, setMode] = useState<Mode>("daily");
  const { data: dailyData, isLoading: dailyLoading } = useDailyReturns(
    period,
    undefined,
    false
  );
  const { data: cumData, isLoading: cumLoading } = useDailyReturns(
    period,
    undefined,
    true
  );

  const isLoading = mode === "daily" ? dailyLoading : cumLoading;
  const points = mode === "daily" ? dailyData?.data ?? [] : cumData?.data ?? [];

  const chartRows = useMemo(
    () => points.map((p) => ({ date: p.date, value: p.return * 100 })),
    [points]
  );

  const stats = useMemo(() => {
    const daily = dailyData?.data ?? [];
    const up = daily.filter((d) => d.return > 0).length;
    const down = daily.filter((d) => d.return < 0).length;
    const totalReturn = cumData?.data?.length
      ? cumData.data[cumData.data.length - 1].return
      : null;
    return { up, down, totalReturn };
  }, [dailyData, cumData]);

  if (isLoading) return <ChartSkeleton />;

  return (
    <div>
      <div className="flex gap-1 mb-4">
        {(["daily", "cumulative"] as Mode[]).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              mode === m
                ? "bg-navy-900 text-cream-50"
                : "text-muted hover:bg-cream-200/60"
            }`}
          >
            {m === "daily" ? "Daily" : "Cumulative"}
          </button>
        ))}
      </div>

      {chartRows.length > 0 ? (
        <div className="h-[280px] -mx-2">
          <ResponsiveContainer width="100%" height="100%">
            {mode === "daily" ? (
              <BarChart
                data={chartRows}
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
                  tickFormatter={(v: number) => `${v.toFixed(1)}%`}
                  tick={{ fontSize: 11, fill: "#94a3b8" }}
                  axisLine={false}
                  tickLine={false}
                  width={45}
                />
                <ReferenceLine y={0} stroke="#e2e8f0" />
                <Tooltip content={<ReturnTooltip />} />
                <Bar dataKey="value" animationDuration={600} radius={[2, 2, 0, 0]}>
                  {chartRows.map((entry, i) => (
                    <Cell
                      key={i}
                      fill={entry.value >= 0 ? CHART_GREEN : CHART_RED}
                      fillOpacity={0.85}
                    />
                  ))}
                </Bar>
              </BarChart>
            ) : (
              <AreaChart
                data={chartRows}
                margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="cumFill" x1="0" y1="0" x2="0" y2="1">
                    <stop
                      offset="0%"
                      stopColor={CHART_GREEN}
                      stopOpacity={0.2}
                    />
                    <stop
                      offset="100%"
                      stopColor={CHART_GREEN}
                      stopOpacity={0}
                    />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="date"
                  tickFormatter={formatDateShort}
                  tick={{ fontSize: 11, fill: "#94a3b8" }}
                  axisLine={false}
                  tickLine={false}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tickFormatter={(v: number) => `${v.toFixed(1)}%`}
                  tick={{ fontSize: 11, fill: "#94a3b8" }}
                  axisLine={false}
                  tickLine={false}
                  width={45}
                />
                <ReferenceLine y={0} stroke="#e2e8f0" />
                <Tooltip content={<ReturnTooltip />} />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke={CHART_GREEN}
                  strokeWidth={2}
                  fill="url(#cumFill)"
                  animationDuration={800}
                />
              </AreaChart>
            )}
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="h-[280px] flex items-center justify-center">
          <p className="text-sm text-muted">
            No returns data available for this period.
          </p>
        </div>
      )}

      <div className="mt-3 flex gap-4 text-[11px] text-muted">
        {stats.totalReturn !== null && (
          <span>
            Total return:{" "}
            <span
              className={`font-mono font-medium ${
                stats.totalReturn >= 0 ? "text-gain-green" : "text-loss-red"
              }`}
            >
              {formatPercent(stats.totalReturn)}
            </span>
          </span>
        )}
        <span>{stats.up} up days</span>
        <span>{stats.down} down days</span>
      </div>
    </div>
  );
}

function ReturnTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const value = payload[0].value;
  return (
    <div className="bg-navy-900 text-cream-50 rounded-lg px-3 py-2 text-xs shadow-lg">
      <p className="font-medium mb-1">{label}</p>
      <p className={`font-mono ${value >= 0 ? "text-green-400" : "text-red-400"}`}>
        {value >= 0 ? "+" : ""}
        {value.toFixed(2)}%
      </p>
    </div>
  );
}
