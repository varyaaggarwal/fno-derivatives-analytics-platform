"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const IST_OFFSET_MIN = 5 * 60 + 30; // fixed UTC+5:30, no DST

function istNow(): Date {
  const utcMs = Date.now();
  return new Date(utcMs + IST_OFFSET_MIN * 60000);
}

function isMarketOpen(now: Date): boolean {
  const day = now.getUTCDay(); // istNow() already shifted, so getUTC* reads as IST wall-clock
  if (day === 0 || day === 6) return false;
  const minutes = now.getUTCHours() * 60 + now.getUTCMinutes();
  return minutes >= 9 * 60 + 15 && minutes <= 15 * 60 + 30;
}

function formatIST(now: Date): string {
  const h = String(now.getUTCHours()).padStart(2, "0");
  const m = String(now.getUTCMinutes()).padStart(2, "0");
  const s = String(now.getUTCSeconds()).padStart(2, "0");
  return `${h}:${m}:${s} IST`;
}

export default function StatusBar() {
  const [connected, setConnected] = useState<boolean | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [isLive, setIsLive] = useState<boolean | null>(null);
  const [lastCheck, setLastCheck] = useState<string>("--");
  const [marketOpen, setMarketOpen] = useState(false);

  useEffect(() => {
    setMarketOpen(isMarketOpen(istNow()));
    const clockId = setInterval(() => setMarketOpen(isMarketOpen(istNow())), 30000);

    let cancelled = false;
    async function check() {
      const started = performance.now();
      try {
        const h = await api.health();
        if (cancelled) return;
        setConnected(true);
        setIsLive(h.live_nse);
        setLatencyMs(Math.round(performance.now() - started));
      } catch {
        if (cancelled) return;
        setConnected(false);
        setLatencyMs(null);
      }
      setLastCheck(formatIST(istNow()));
    }
    check();
    const pollId = setInterval(check, 30000);
    return () => {
      cancelled = true;
      clearInterval(clockId);
      clearInterval(pollId);
    };
  }, []);

  return (
    <footer className="h-9 border-t border-border bg-card/60 backdrop-blur flex items-center justify-between px-4 md:px-6 text-[11px] text-muted-foreground font-mono mono-nums">
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1.5">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              connected === null ? "bg-muted-foreground/50" : connected ? "bg-bullish" : "bg-bearish"
            }`}
          />
          {connected === null ? "CONNECTING" : connected ? "API CONNECTED" : "API UNREACHABLE"}
        </span>
        {latencyMs !== null && <span>LATENCY {latencyMs}ms</span>}
        {isLive !== null && <span>SOURCE {isLive ? "LIVE" : "MOCK"}</span>}
        <span className={marketOpen ? "text-bullish" : "text-muted-foreground"}>
          MARKET {marketOpen ? "OPEN" : "CLOSED"}
        </span>
        <span className="hidden sm:inline">LAST CHECK {lastCheck}</span>
      </div>
    </footer>
  );
}
