import { useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";

interface Props {
  title: string;
  defaultOpen?: boolean;
  headerRight?: ReactNode;
  children: ReactNode;
  delay?: number;
}

export function CollapsibleSection({
  title,
  defaultOpen = true,
  headerRight,
  children,
  delay = 0,
}: Props) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className="rounded-2xl bg-white/60 border border-cream-200/80 p-5"
    >
      <button
        type="button"
        onClick={() => setIsOpen((o) => !o)}
        aria-expanded={isOpen}
        className="flex w-full items-center justify-between gap-3"
      >
        <h2 className="text-sm font-semibold text-navy-900">{title}</h2>

        <div className="flex items-center gap-2">
          {headerRight && (
            <div
              onClick={(e) => e.stopPropagation()}
              onKeyDown={(e) => e.stopPropagation()}
              role="presentation"
            >
              {headerRight}
            </div>
          )}

          <motion.span
            animate={{ rotate: isOpen ? 180 : 0 }}
            transition={{ duration: 0.2 }}
            className="text-muted"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              className="stroke-current"
            >
              <path
                d="M4 6l4 4 4-4"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </motion.span>
        </div>
      </button>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="pt-4">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
