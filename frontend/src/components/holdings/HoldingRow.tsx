import { motion } from "framer-motion";
import { GainBadge } from "./GainBadge";
import { formatCurrency } from "../../lib/format";
import type { AllocationHolding } from "../../types";

interface Props {
  holding: AllocationHolding;
}

export function HoldingRow({ holding }: Props) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex items-center justify-between py-3 border-b border-cream-200/60 last:border-0"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-medium text-navy-900">
            {holding.symbol}
          </span>
          <span className="text-xs text-muted truncate">{holding.name}</span>
        </div>
        <div className="mt-0.5 text-xs text-muted">
          {holding.quantity.toFixed(holding.quantity % 1 === 0 ? 0 : 2)} shares
        </div>
      </div>
      <div className="flex items-center gap-3">
        <GainBadge value={holding.unrealized_gain_pct} />
        <span className="font-mono text-sm font-medium text-navy-900 w-24 text-right">
          {formatCurrency(holding.value)}
        </span>
      </div>
    </motion.div>
  );
}
