import { useAccounts } from "../../hooks/useAccounts";
import { AccountCard } from "./AccountCard";
import { CardSkeleton } from "../shared/LoadingSkeleton";
import { formatCurrency } from "../../lib/format";

export function AccountsList() {
  const { data, isLoading } = useAccounts();

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <CardSkeleton key={i} />
        ))}
      </div>
    );
  }

  const accounts = (data?.accounts ?? []).filter((a) => a.balance > 0);
  const total = accounts.reduce((sum, a) => sum + a.balance, 0);

  return (
    <div>
      {total > 0 && (
        <p className="text-xs text-muted mb-3">
          Total {formatCurrency(total)} &middot; {accounts.length} accounts
        </p>
      )}
      <div className="space-y-2">
        {accounts.map((account) => (
          <AccountCard key={account.id} account={account} />
        ))}
      </div>
    </div>
  );
}
