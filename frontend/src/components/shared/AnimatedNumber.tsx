import { useEffect, useRef } from "react";
import { useSpring } from "framer-motion";

interface Props {
  value: number;
  format: (n: number) => string;
  className?: string;
}

export function AnimatedNumber({ value, format, className }: Props) {
  const ref = useRef<HTMLSpanElement>(null);
  const spring = useSpring(value, { stiffness: 80, damping: 20 });

  useEffect(() => {
    spring.set(value);
  }, [value, spring]);

  useEffect(() => {
    return spring.on("change", (latest) => {
      if (ref.current) {
        ref.current.textContent = format(latest);
      }
    });
  }, [spring, format]);

  return <span ref={ref} className={className}>{format(value)}</span>;
}
