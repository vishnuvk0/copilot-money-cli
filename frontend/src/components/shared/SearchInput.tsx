interface Props {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export function SearchInput({
  value,
  onChange,
  placeholder = "Search…",
}: Props) {
  return (
    <div className="relative">
      <svg
        width="14"
        height="14"
        viewBox="0 0 14 14"
        fill="none"
        className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted stroke-current"
      >
        <circle cx="6" cy="6" r="4.5" strokeWidth="1.3" />
        <path d="M9.5 9.5l3 3" strokeWidth="1.3" strokeLinecap="round" />
      </svg>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="rounded-lg bg-cream-50/80 border border-cream-200/50 pl-8 pr-3 py-1.5 text-xs text-navy-900 placeholder:text-muted/60 outline-none focus:border-navy-500/40 transition-colors w-36"
      />
    </div>
  );
}
