/**
 * Small inline badge showing whether the data on screen is live or mock.
 * Previously several pages either hardcoded a "mock" label regardless of
 * actual data_source, or showed no indicator at all (see audit items #7).
 * This is the one place that logic lives now.
 */
export default function DataSourceBadge({
  dataSource,
  liveFetchError,
}: {
  dataSource?: string | null;
  liveFetchError?: string | null;
}) {
  if (!dataSource) return null;
  const isLive = dataSource.startsWith("live");
  return (
    <span
      title={!isLive && liveFetchError ? liveFetchError : undefined}
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium border font-mono ${
        isLive
          ? "bg-bullish/10 text-bullish border-bullish/30"
          : "bg-warn/10 text-warn border-warn/30"
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${isLive ? "bg-bullish" : "bg-warn"}`} />
      {isLive ? "LIVE DATA" : "MOCK DATA"}
    </span>
  );
}
