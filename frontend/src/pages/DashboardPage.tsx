import { useState, useCallback } from "react";
import { format } from "date-fns";
import { BalanceChart } from "../components/charts/BalanceChart";
import { PerformanceCard } from "../components/performance/PerformanceCard";
import { ComparisonChart } from "../components/charts/ComparisonChart";
import { ReturnsChart } from "../components/charts/ReturnsChart";
import { HoldingsTable } from "../components/holdings/HoldingsTable";
import { AllocationBreakdown } from "../components/allocation/AllocationBreakdown";
import { AllocationChart } from "../components/charts/AllocationChart";
import { TradesList } from "../components/trades/TradesList";
import { PeriodsTable } from "../components/performance/PeriodsTable";
import { AccountsList } from "../components/accounts/AccountsList";
import { CollapsibleSection } from "../components/shared/CollapsibleSection";
import { SearchInput } from "../components/shared/SearchInput";
import { ActionFilter } from "../components/shared/ActionFilter";
import { PeriodSelector } from "../components/layout/PeriodSelector";
import type { Period } from "../types";
import type { ActionFilterValue } from "../components/shared/ActionFilter";

export function DashboardPage() {
  const [period, setPeriod] = useState<Period>("1Y");
  const [hoveredDate, setHoveredDate] = useState<string | null>(null);
  const [hoveredBalance, setHoveredBalance] = useState<number | null>(null);

  // Filter state
  const [holdingsSearch, setHoldingsSearch] = useState("");
  const [tradesSymbol, setTradesSymbol] = useState("");
  const [tradesAction, setTradesAction] = useState<ActionFilterValue>("ALL");
  const [tradesPeriod, setTradesPeriod] = useState<Period>("ALL");

  const todayStr = format(new Date(), "yyyy-MM-dd");
  const displayDate = hoveredDate ?? todayStr;

  const handleHover = useCallback(
    (date: string | null, balance: number | null) => {
      setHoveredDate(date);
      setHoveredBalance(balance);
    },
    []
  );

  return (
    <div className="space-y-8">
      {/* Hero — Balance chart + performance return */}
      <BalanceChart
        period={period}
        onPeriodChange={setPeriod}
        onHover={handleHover}
        hoveredBalance={hoveredBalance}
      />

      {/* Performance Metrics */}
      <CollapsibleSection title="Performance Metrics" delay={0.1}>
        <PerformanceCard period={period} />
      </CollapsibleSection>

      {/* Portfolio vs Benchmark */}
      <CollapsibleSection title="Portfolio vs S&P 500" delay={0.15}>
        <ComparisonChart period={period} />
      </CollapsibleSection>

      {/* Returns — daily/cumulative toggle */}
      <CollapsibleSection title="Returns" delay={0.2}>
        <ReturnsChart period={period} />
      </CollapsibleSection>

      {/* Holdings + Allocation + Accounts */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3">
          <CollapsibleSection
            title="Holdings"
            delay={0.1}
            headerRight={
              <SearchInput
                value={holdingsSearch}
                onChange={setHoldingsSearch}
                placeholder="Search holdings…"
              />
            }
          >
            <HoldingsTable
              date={displayDate}
              isHistorical={hoveredDate !== null}
              searchQuery={holdingsSearch}
            />
          </CollapsibleSection>
        </div>
        <div className="lg:col-span-2 space-y-6">
          <CollapsibleSection title="Asset Allocation" delay={0.2}>
            <AllocationBreakdown date={displayDate} />
          </CollapsibleSection>
          <CollapsibleSection title="Accounts" delay={0.3}>
            <AccountsList />
          </CollapsibleSection>
        </div>
      </div>

      {/* Allocation History */}
      <CollapsibleSection title="Allocation Over Time" delay={0.1}>
        <AllocationChart />
      </CollapsibleSection>

      {/* Trades */}
      <CollapsibleSection
        title="Trades"
        delay={0.3}
        headerRight={
          <div className="flex items-center gap-2">
            <SearchInput
              value={tradesSymbol}
              onChange={setTradesSymbol}
              placeholder="Search symbol…"
            />
            <ActionFilter value={tradesAction} onChange={setTradesAction} />
            <PeriodSelector value={tradesPeriod} onChange={setTradesPeriod} />
          </div>
        }
      >
        <TradesList
          period={tradesPeriod}
          symbolQuery={tradesSymbol}
          actionFilter={tradesAction}
        />
      </CollapsibleSection>

      {/* Multi-Period Overview */}
      <CollapsibleSection title="Multi-Period Overview" delay={0.35}>
        <PeriodsTable />
      </CollapsibleSection>
    </div>
  );
}
