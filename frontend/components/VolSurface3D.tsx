"use client";
import { useMemo } from "react";
import dynamic from "next/dynamic";
import type { VolSurfaceRow } from "@/lib/api";

// react-plotly.js (and the plotly.js it wraps) touches `window`/`self` at
// import time, which crashes Next's server-side prerender. Deferring the
// import() itself (not just the component) to a client-only dynamic import
// keeps it out of the server bundle entirely.
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

export default function VolSurface3D({ rows }: { rows: VolSurfaceRow[] }) {
  const { x, y, z, empty } = useMemo(() => {
    const strikes = Array.from(new Set(rows.map((r) => r.strike))).sort((a, b) => a - b);
    const expiries = Array.from(new Set(rows.map((r) => r.expiry_days))).sort((a, b) => a - b);
    const lookup: Record<string, number> = {};
    rows.forEach((r) => { lookup[`${r.strike}-${r.expiry_days}`] = r.implied_volatility; });

    // z[row][col] where rows = expiries, cols = strikes -- Plotly surface convention
    const zGrid = expiries.map((e) => strikes.map((s) => lookup[`${s}-${e}`] ?? null));
    return { x: strikes, y: expiries, z: zGrid, empty: strikes.length === 0 || expiries.length === 0 };
  }, [rows]);

  if (empty) {
    return <div className="h-[420px] flex items-center justify-center text-muted text-sm">Loading surface data…</div>;
  }

  return (
    <div className="h-[420px]">
      <Plot
        data={[
          {
            type: "surface",
            x,
            y,
            z,
            colorscale: [
              [0, "#6366F1"],
              [0.5, "#FBBF24"],
              [1, "#F87171"],
            ],
            showscale: true,
            colorbar: { title: "IV %", titlefont: { color: "#8B98A5" }, tickfont: { color: "#8B98A5" }, thickness: 14 },
            contours: { z: { show: true, usecolormap: true, project: { z: true } } },
          },
        ]}
        layout={{
          autosize: true,
          paper_bgcolor: "transparent",
          plot_bgcolor: "transparent",
          margin: { l: 0, r: 0, t: 10, b: 0 },
          scene: {
            xaxis: { title: "Strike", color: "#8B98A5", gridcolor: "#1F2733", backgroundcolor: "transparent" },
            yaxis: { title: "Expiry (days)", color: "#8B98A5", gridcolor: "#1F2733", backgroundcolor: "transparent" },
            zaxis: { title: "IV %", color: "#8B98A5", gridcolor: "#1F2733", backgroundcolor: "transparent" },
            camera: { eye: { x: 1.5, y: -1.5, z: 0.8 } },
          },
          font: { family: "Inter, sans-serif", color: "#E6EDF3" },
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%", height: "100%" }}
        useResizeHandler
      />
    </div>
  );
}
