/**
 * Wraps any element with a hover-revealed description box. CSS-only (group /
 * group-hover), so it works the same in server or client components with no
 * extra JS state. Used to give every card/stat/nav item a one-line
 * explanation of what it means -- useful for a viva where you need to
 * explain each feature on the dashboard.
 */
export default function InfoTooltip({
  text,
  children,
  className = "",
}: {
  text: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span className={`relative inline-block group/tooltip ${className}`}>
      {children}
      <span
        role="tooltip"
        className="pointer-events-none absolute left-1/2 bottom-full z-20 mb-2 w-56 -translate-x-1/2 rounded-md border border-border bg-popover px-2.5 py-1.5 text-[11px] leading-snug text-popover-foreground opacity-0 shadow-lg transition-opacity duration-150 group-hover/tooltip:opacity-100"
      >
        {text}
      </span>
    </span>
  );
}
