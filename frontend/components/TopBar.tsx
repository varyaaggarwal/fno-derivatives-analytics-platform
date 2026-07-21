"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import DataSourceBadge from "@/components/DataSourceBadge";

function nextExpiryCountdown(): string {
  const now = new Date();
  const target = new Date(now);
  target.setHours(15, 30, 0, 0);
  // walk forward to the next Wed(3) or Thu(4) close (JS getDay: 0=Sun..6=Sat, so Wed=3, Thu=4)
  while (![3, 4].includes(target.getDay()) || target.getTime() <= now.getTime()) {
    target.setDate(target.getDate() + 1);
    target.setHours(15, 30, 0, 0);
  }
  const diffMs = target.getTime() - now.getTime();
  const h = Math.floor(diffMs / 3600000);
  const m = Math.floor((diffMs % 3600000) / 60000);
  const s = Math.floor((diffMs % 60000) / 1000);
  return `${h}h ${m}m ${s}s`;
}

export default function TopBar() {
  const [countdown, setCountdown] = useState("--");
  const [spot, setSpot] = useState<number | null>(null);
  const [dataSource, setDataSource] = useState<string | undefined>();
  const [liveFetchError, setLiveFetchError] = useState<string | null | undefined>();
  const sessionOpenRef = useRef<number | null>(null); // reference point for %-change, set on first fetch

  useEffect(() => {
    setCountdown(nextExpiryCountdown());
    const id = setInterval(() => setCountdown(nextExpiryCountdown()), 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    // Previously this whole block was 100% static hardcoded JSX ("24,350.00
    // +0.34%") -- it never changed regardless of live vs mock data. Now it
    // pulls the real spot from /api/chain, polling so it stays current.
    let cancelled = false;
    function poll() {
      api
        .chain()
        .then((d) => {
          if (cancelled) return;
          if (sessionOpenRef.current === null) sessionOpenRef.current = d.spot;
          setSpot(d.spot);
          setDataSource(d.data_source);
          setLiveFetchError(d.live_fetch_error);
        })
        .catch(() => {});
    }
    poll();
    const id = setInterval(poll, 30000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const changePct =
    spot !== null && sessionOpenRef.current ? ((spot - sessionOpenRef.current) / sessionOpenRef.current) * 100 : null;

  return (
    <header className="h-14 border-b border-border bg-card/60 backdrop-blur flex items-center justify-between px-4 md:px-6">
      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground">NIFTY</span>
        <span className="font-mono mono-nums text-sm text-foreground">
          {spot !== null ? spot.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "--"}
        </span>
        {changePct !== null && (
          <span className={`font-mono mono-nums text-xs ${changePct >= 0 ? "text-bullish" : "text-bearish"}`}>
            {changePct >= 0 ? "+" : ""}
            {changePct.toFixed(2)}%
          </span>
        )}
        <DataSourceBadge dataSource={dataSource} liveFetchError={liveFetchError} />
      </div>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="hidden sm:inline">Next expiry close in</span>
        <span className="font-mono mono-nums text-warn tabular-nums w-[90px] text-right">{countdown}</span>
      </div>
    </header>
  );
}
