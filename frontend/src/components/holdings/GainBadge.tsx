interface Props {
  value: number | null;
  showPercent?: boolean;
}

export function GainBadge({ value, showPercent = true }: Props) {
  if (value === null) return <span className="text-xs text-muted">--</span>;

  const isPositive = value >= 0;
  return (
    <span
      className={`inline-flex items-center gap-0.5 rounded-md px-2 py-0.5 text-xs font-medium font-mono ${
        isPositive
          ? "bg-gain-bg text-gain-green"
          : "bg-loss-bg text-loss-red"
      }`}
    >
      <span>{isPositive ? "\u25B2" : "\u25BC"}</span>
      {showPercent
        ? `${Math.abs(value * 100).toFixed(1)}%`
        : `$${Math.abs(value).toLocaleString("en-US", { maximumFractionDigits: 0 })}`}
    </span>
  );
}
