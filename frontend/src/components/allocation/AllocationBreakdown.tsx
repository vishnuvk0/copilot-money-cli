import { useFiling } from "../../hooks/useFiling";
import { AllocationBar } from "./AllocationBar";
import { TableSkeleton } from "../shared/LoadingSkeleton";

interface Props {
  date: string;
}

export function AllocationBreakdown({ date }: Props) {
  const { data, isLoading } = useFiling(date);

  if (isLoading) return <TableSkeleton />;

  const sectors = data?.sector_breakdown ?? [];

  return (
    <div>
      <div className="space-y-0.5">
        {sectors.map((s) => (
          <AllocationBar
            key={s.type}
            label={s.type}
            percentage={s.weight_pct}
            value={s.market_value}
          />
        ))}
      </div>

      {sectors.length === 0 && (
        <p className="text-sm text-muted py-6 text-center">
          No allocation data
        </p>
      )}
    </div>
  );
}
