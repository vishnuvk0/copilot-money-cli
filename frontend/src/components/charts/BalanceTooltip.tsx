import { formatCurrency, formatDateShort } from "../../lib/format";

interface Props {
  active?: boolean;
  payload?: Array<{ payload: { date: string; balance: number } }>;
}

export function BalanceTooltip({ active, payload }: Props) {
  if (!active || !payload?.length) return null;
  const { date, balance } = payload[0].payload;

  return (
    <div className="rounded-lg bg-navy-900 px-3 py-2 text-xs shadow-lg">
      <p className="font-mono text-cream-50 font-medium">
        {formatCurrency(balance)}
      </p>
      <p className="text-cream-300 mt-0.5">{formatDateShort(date)}</p>
    </div>
  );
}
