"use client";
import { useEffect, useState } from "react";

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
  useEffect(() => {
    setCountdown(nextExpiryCountdown());
    const id = setInterval(() => setCountdown(nextExpiryCountdown()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="h-14 border-b border-border bg-surface/60 backdrop-blur flex items-center justify-between px-4 md:px-6">
      <div className="flex items-center gap-3">
        <span className="text-sm text-muted">NIFTY</span>
        <span className="font-mono mono-nums text-sm text-text">24,350.00</span>
        <span className="font-mono mono-nums text-xs text-bullish">+0.34%</span>
      </div>
      <div className="flex items-center gap-2 text-xs text-muted">
        <span className="hidden sm:inline">Next expiry close in</span>
        <span className="font-mono mono-nums text-warn tabular-nums w-[90px] text-right">{countdown}</span>
      </div>
    </header>
  );
}
