/**
 * useKeepalive -- pings the backend's /api/health endpoint periodically to
 * stop Render's free-tier instance from spinning down mid-demo.
 *
 * WHY THIS EXISTS: Render free-tier web services sleep after inactivity,
 * and the next request pays a cold-start penalty (tens of seconds). TopBar
 * already polls /api/chain every 30s on every page, which incidentally
 * helps -- but the DOS Strategy page (app/dos/page.tsx) is the one place
 * where staying "live" actually matters for a demo (live-signal panel, SL
 * monitor), so this hook is mounted there specifically rather than
 * globally, and hits the lighter /api/health endpoint rather than
 * duplicating the chain poll.
 *
 * Only pings while `active` is true -- so it doesn't run unconditionally
 * in the background and burn Render's free-tier hours keeping the
 * instance awake while no one's looking at a live view.
 *
 * Usage (inside a "use client" component):
 *   useKeepalive(true, process.env.NEXT_PUBLIC_API_BASE);
 */
import { useEffect, useRef } from "react";

const PING_INTERVAL_MS = 3 * 60 * 1000; // 3 minutes

export default function useKeepalive(active: boolean, apiBase?: string): void {
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!active || !apiBase) return undefined;

    const ping = () => {
      fetch(`${apiBase}/api/health`).catch((err) => {
        // Never let a failed ping surface as an app error -- if Render is
        // asleep/waking up, this request is part of *causing* it to wake
        // up, not evidence that anything is broken.
        console.warn("keepalive ping failed (backend may be waking up):", err);
      });
    };

    ping(); // immediate ping on mount, then on the interval below
    intervalRef.current = setInterval(ping, PING_INTERVAL_MS);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [active, apiBase]);
}
