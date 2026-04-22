import { PERIODS } from "../../lib/constants";
import type { Period } from "../../types";

interface Props {
  value: Period;
  onChange: (p: Period) => void;
}

export function PeriodSelector({ value, onChange }: Props) {
  return (
    <div className="flex gap-1">
      {PERIODS.map((p) => (
        <button
          key={p.value}
          onClick={() => onChange(p.value)}
          className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
            value === p.value
              ? "bg-navy-900 text-cream-50"
              : "text-muted hover:bg-cream-200/60"
          }`}
        >
          {p.label}
        </button>
      ))}
    </div>
  );
}
