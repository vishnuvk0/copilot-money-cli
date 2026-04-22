import { formatDistanceToNow } from "date-fns";
import { formatCurrency } from "../../lib/format";
import type { Account } from "../../types";

interface Props {
  account: Account;
}

const COLORS = [
  "bg-navy-500",
  "bg-gain-green",
  "bg-alloc-blue",
  "bg-amber-500",
  "bg-violet-500",
];

export function AccountCard({ account }: Props) {
  const initial = account.name.charAt(0).toUpperCase();
  const colorIdx =
    account.name.split("").reduce((a, c) => a + c.charCodeAt(0), 0) %
    COLORS.length;

  return (
    <div className="flex items-center gap-3 rounded-xl bg-white/60 border border-cream-200/80 px-4 py-3 transition-shadow hover:shadow-[0_2px_8px_rgba(0,0,0,0.04)]">
      <div
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-white text-sm font-semibold ${COLORS[colorIdx]}`}
      >
        {initial}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-navy-900 truncate">
          {account.name}
        </p>
        <p className="text-xs text-muted">
          {account.sub_type} &middot; Updated{" "}
          {formatDistanceToNow(new Date(Number(account.updated_at)), {
            addSuffix: true,
          })}
        </p>
      </div>
      <span className="font-mono text-sm font-medium text-navy-900">
        {formatCurrency(account.balance)}
      </span>
    </div>
  );
}
