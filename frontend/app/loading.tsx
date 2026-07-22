import { Skeleton } from "@/components/Skeleton";

export default function OverviewLoading() {
  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-4 w-64 mt-2" />
      </div>

      <div className="bg-card border border-border rounded-card p-4">
        <Skeleton className="h-4 w-40 mb-3" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex flex-col items-center gap-2">
              <Skeleton className="h-16 w-full max-w-[140px] rounded-full" />
              <Skeleton className="h-3 w-12" />
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="bg-card border border-border rounded-card p-4">
            <Skeleton className="h-4 w-24 mb-3" />
            <Skeleton className="h-7 w-20 mb-2" />
            <Skeleton className="h-3 w-full" />
          </div>
        ))}
      </div>

      <div className="bg-card border border-border rounded-card p-4">
        <Skeleton className="h-4 w-56 mb-3" />
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i}>
              <Skeleton className="h-6 w-16 mb-1.5" />
              <Skeleton className="h-2.5 w-14" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
