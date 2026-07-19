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
    return <div className="h-[420px] flex items-center justify-center text-muted-foreground text-sm">Loading surface data…</div>;
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
              [0, "#437DFB"],
              [0.5, "hsl(30, 80%, 55%)"],
              [1, "#D93036"],
            ],
            showscale: true,
            colorbar: { title: "IV %", titlefont: { color: "hsl(240, 5%, 64.9%)" }, tickfont: { color: "hsl(240, 5%, 64.9%)" }, thickness: 14 },
            contours: { z: { show: true, usecolormap: true, project: { z: true } } },
          },
        ]}
        layout={{
          autosize: true,
          paper_bgcolor: "transparent",
          plot_bgcolor: "transparent",
          margin: { l: 0, r: 0, t: 10, b: 0 },
          scene: {
            // plotly.js v2+ silently ignores a plain-string `title` on 3D scene
            // axes (it falls back to "x"/"y"/"z") -- as of v3 it must be an
            // object with a `text` key for the label to actually render.
            xaxis: { title: { text: "Strike", font: { color: "hsl(240, 5%, 64.9%)" } }, color: "hsl(240, 5%, 64.9%)", gridcolor: "hsl(240, 3.7%, 20%)", backgroundcolor: "transparent" },
            yaxis: { title: { text: "Expiry (days)", font: { color: "hsl(240, 5%, 64.9%)" } }, color: "hsl(240, 5%, 64.9%)", gridcolor: "hsl(240, 3.7%, 20%)", backgroundcolor: "transparent" },
            zaxis: { title: { text: "Implied Volatility (%)", font: { color: "hsl(240, 5%, 64.9%)" } }, color: "hsl(240, 5%, 64.9%)", gridcolor: "hsl(240, 3.7%, 20%)", backgroundcolor: "transparent" },
            camera: { eye: { x: 1.5, y: -1.5, z: 0.8 } },
          },
          font: { family: "Geist Variable, sans-serif", color: "hsl(0, 0%, 98%)" },
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%", height: "100%" }}
        useResizeHandler
      />
    </div>
  );
}
