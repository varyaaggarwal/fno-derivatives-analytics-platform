/**
 * Shimmering gradient placeholders shown while data is loading, instead of
 * literal "Loading..." text. `Skeleton` is the base block; the presets below
 * cover the common shapes used across the app (stat tiles, table rows,
 * chart areas, text lines).
 */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} />;
}

export function SkeletonStatCard() {
  return (
    <div className="bg-card border border-border rounded-card px-4 py-3">
      <Skeleton className="h-2.5 w-16 mb-2" />
      <Skeleton className="h-6 w-20" />
    </div>
  );
}

export function SkeletonLine({ className = "w-full" }: { className?: string }) {
  return <Skeleton className={`h-3 ${className}`} />;
}

export function SkeletonBlock({ className = "h-56 w-full" }: { className?: string }) {
  return <Skeleton className={className} />;
}

export function SkeletonTableRows({ rows = 8, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-3">
          {Array.from({ length: cols }).map((__, c) => (
            <Skeleton key={c} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}
