const STYLES: Record<string, string> = {
  call: "bg-bullish/10 text-bullish border-bullish/30",
  ce: "bg-bullish/10 text-bullish border-bullish/30",
  bullish: "bg-bullish/10 text-bullish border-bullish/30",
  put: "bg-bearish/10 text-bearish border-bearish/30",
  pe: "bg-bearish/10 text-bearish border-bearish/30",
  bearish: "bg-bearish/10 text-bearish border-bearish/30",
  neutral: "bg-muted/40 text-muted-foreground border-muted-foreground/30",
  elevated: "bg-warn/10 text-warn border-warn/30",
  depressed: "bg-mainBlue/10 text-mainBlue border-mainBlue/30",
};

export default function Badge({ label }: { label: string }) {
  const key = label.toLowerCase();
  const style = STYLES[key] || "bg-muted/40 text-muted-foreground border-muted-foreground/30";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border font-mono ${style}`}>
      {label.toUpperCase()}
    </span>
  );
}
