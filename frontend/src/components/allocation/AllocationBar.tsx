import { motion } from "framer-motion";

interface Props {
  label: string;
  percentage: number;
  value: number;
}

export function AllocationBar({ label, percentage, value }: Props) {
  return (
    <div className="flex items-center gap-3 py-1.5">
      <span className="text-xs text-muted w-20 shrink-0 truncate">{label}</span>
      <div className="flex-1 h-2 rounded-full bg-alloc-track overflow-hidden">
        <motion.div
          className="h-full rounded-full bg-alloc-blue"
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </div>
      <span className="font-mono text-xs text-navy-900 w-12 text-right">
        {percentage.toFixed(1)}%
      </span>
    </div>
  );
}
