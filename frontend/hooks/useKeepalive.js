/**
 * useKeepalive -- pings the backend's /api/health endpoint periodically to
 * stop Render's free-tier instance from spinning down mid-demo.
 *
 * WHY THIS EXISTS: Render free-tier web services sleep after inactivity,
 * and the next request pays a cold-start penalty (tens of seconds). That's
 * fine for the background poller (it already idles outside market hours),
 * but it's a bad look mid-demo if a live-signal or feed-status view goes
 * quiet just because no one clicked anything for a while.
 *
 * Only pings while `active` is true -- e.g. only while the DOS live-signal
 * page or WS-feed status view is actually mounted -- so it doesn't run
 * unconditionally in the background and burn Render's free-tier hours
 * keeping the instance awake overnight or while the tab is idle elsewhere.
 *
 * Usage:
 *   useKeepalive(isFeedViewMounted, process.env.NEXT_PUBLIC_API_BASE);
 */
import { useEffect, useRef } from "react";

const PING_INTERVAL_MS = 3 * 60 * 1000; // 3 minutes

export default function useKeepalive(active, apiBase) {
  const intervalRef = useRef(null);

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
