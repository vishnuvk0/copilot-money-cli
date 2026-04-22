export type ActionFilterValue = "ALL" | "BUY" | "SELL";

interface Props {
  value: ActionFilterValue;
  onChange: (value: ActionFilterValue) => void;
}

const OPTIONS: { label: string; value: ActionFilterValue }[] = [
  { label: "All", value: "ALL" },
  { label: "Buy", value: "BUY" },
  { label: "Sell", value: "SELL" },
];

export function ActionFilter({ value, onChange }: Props) {
  return (
    <div className="flex gap-1">
      {OPTIONS.map((opt) => {
        const isActive = value === opt.value;
        let activeClass = "bg-navy-900 text-cream-50";
        if (isActive && opt.value === "BUY")
          activeClass = "bg-gain-bg text-gain-green";
        if (isActive && opt.value === "SELL")
          activeClass = "bg-loss-bg text-loss-red";

        return (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              isActive ? activeClass : "text-muted hover:bg-cream-200/60"
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
