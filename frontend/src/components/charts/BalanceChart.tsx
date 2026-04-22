import { useMemo, useCallback } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { motion } from "framer-motion";
import { useBalanceHistory } from "../../hooks/useBalanceHistory";
import { usePerformance } from "../../hooks/usePerformance";
import { useAccounts } from "../../hooks/useAccounts";
import { PeriodSelector } from "../layout/PeriodSelector";
import { BalanceTooltip } from "./BalanceTooltip";
import { AnimatedNumber } from "../shared/AnimatedNumber";
import { ChartSkeleton } from "../shared/LoadingSkeleton";
import { formatCurrency, formatPercent } from "../../lib/format";
import {
  CHART_GREEN,
  CHART_RED,
} from "../../lib/constants";
import type { Period, BalancePoint } from "../../types";

interface Props {
  period: Period;
  onPeriodChange: (p: Period) => void;
  onHover: (date: string | null, balance: number | null) => void;
  hoveredBalance: number | null;
}

export function BalanceChart({
  period,
  onPeriodChange,
  onHover,
  hoveredBalance,
}: Props) {
  const { data: historyData, isLoading: historyLoading } =
    useBalanceHistory(period);
  const { data: perfData } = usePerformance(period);
  const { data: accountsData } = useAccounts();

  const points = historyData?.data ?? [];
  const twr = perfData?.metrics.twr ?? null;
  const isPositive = twr === null || twr >= 0;

  const accountsTotal = useMemo(
    () => (accountsData?.accounts ?? []).reduce((s, a) => s + a.balance, 0),
    [accountsData]
  );

  const currentBalance =
    points.length > 0 ? points[points.length - 1].balance : accountsTotal;
  const displayBalance = hoveredBalance ?? currentBalance;

  const lineColor = isPositive ? CHART_GREEN : CHART_RED;

  const handleMouseMove = useCallback(
    (state: { activePayload?: Array<{ payload: BalancePoint }> }) => {
      if (state.activePayload?.length) {
        const point = state.activePayload[0].payload;
        onHover(point.date, point.balance);
      }
    },
    [onHover]
  );

  const handleMouseLeave = useCallback(() => {
    onHover(null, null);
  }, [onHover]);

  const yDomain = useMemo(() => {
    if (!points.length) return [0, 100];
    const values = points.map((p) => p.balance);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const padding = (max - min) * 0.05 || 100;
    return [min - padding, max + padding];
  }, [points]);

  if (historyLoading) return <ChartSkeleton />;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="mb-1">
        <AnimatedNumber
          value={displayBalance}
          format={formatCurrency}
          className="font-mono text-4xl font-semibold text-navy-900 tracking-tight"
        />
      </div>
      {twr !== null && (
        <p
          className={`text-sm font-medium font-mono mb-6 ${
            isPositive ? "text-gain-green" : "text-loss-red"
          }`}
        >
          {formatPercent(twr)} {period}
        </p>
      )}
      {twr === null && <div className="mb-6" />}

      {points.length > 0 ? (
        <div className="h-[280px] -mx-4">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={points}
              onMouseMove={handleMouseMove}
              onMouseLeave={handleMouseLeave}
              margin={{ top: 4, right: 0, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="balanceFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={lineColor} stopOpacity={0.2} />
                  <stop offset="100%" stopColor={lineColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" hide />
              <YAxis domain={yDomain} hide />
              <Tooltip
                content={<BalanceTooltip />}
                cursor={{
                  stroke: lineColor,
                  strokeWidth: 1,
                  strokeDasharray: "4 4",
                }}
              />
              <Area
                type="monotone"
                dataKey="balance"
                stroke={lineColor}
                strokeWidth={2}
                fill="url(#balanceFill)"
                animationDuration={800}
                animationEasing="ease-out"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="h-[280px] -mx-4 flex items-center justify-center">
          <p className="text-sm text-muted">
            Balance history not yet available. Run a full sync to populate
            historical data.
          </p>
        </div>
      )}

      <div className="mt-4">
        <PeriodSelector value={period} onChange={onPeriodChange} />
      </div>
    </motion.div>
  );
}
