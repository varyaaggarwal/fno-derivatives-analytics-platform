"use client";
import { useMemo, useRef } from "react";
import dynamic from "next/dynamic";
import type { VolSurfaceRow } from "@/lib/api";
import { Skeleton } from "@/components/Skeleton";

// react-plotly.js (and the plotly.js it wraps) touches `window`/`self` at
// import time, which crashes Next's server-side prerender. Deferring the
// import() itself (not just the component) to a client-only dynamic import
// keeps it out of the server bundle entirely.
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

// The plotly.js UMD bundle react-plotly.js already loads sets
// `window.Plotly` as a side effect, so once <Plot> has rendered once,
// window.Plotly is the exact same instance driving it -- no need for a
// second import of our own.
declare global {
  interface Window { Plotly?: any }
}

const DEFAULT_EYE = { x: 1.5, y: -1.5, z: 0.8 };
const DEFAULT_EYE_DISTANCE = Math.sqrt(DEFAULT_EYE.x ** 2 + DEFAULT_EYE.y ** 2 + DEFAULT_EYE.z ** 2);
// How far the camera is allowed to pull back. Plotly's 3D scroll-zoom has no
// built-in floor -- scrolling out indefinitely just shrinks the surface to a
// tiny, cluttered speck surrounded by empty space, which looks broken rather
// than useful. This caps the camera at ~1.6x the default distance (chosen so
// the whole surface is still clearly, comfortably visible right up to the
// limit) while leaving zooming IN completely unrestricted.
const MAX_EYE_DISTANCE = DEFAULT_EYE_DISTANCE * 1.6;

export default function VolSurface3D({ rows }: { rows: VolSurfaceRow[] }) {
  const graphDivRef = useRef<any>(null);

  const { x, y, z, empty } = useMemo(() => {
    const strikes = Array.from(new Set(rows.map((r) => r.strike))).sort((a, b) => a - b);
    const expiries = Array.from(new Set(rows.map((r) => r.expiry_days))).sort((a, b) => a - b);
    const lookup: Record<string, number> = {};
    rows.forEach((r) => { lookup[`${r.strike}-${r.expiry_days}`] = r.implied_volatility; });

    // z[row][col] where rows = expiries, cols = strikes -- Plotly surface convention
    const zGrid = expiries.map((e) => strikes.map((s) => lookup[`${s}-${e}`] ?? null));
    return { x: strikes, y: expiries, z: zGrid, empty: strikes.length === 0 || expiries.length === 0 };
  }, [rows]);

  // Fires on every drag/scroll interaction. If the camera has been pulled
  // back past MAX_EYE_DISTANCE, snap it back in along the same direction
  // (only distance is clamped -- rotation/pan direction is left alone, so
  // this doesn't fight the user's actual gesture, just its zoom-out extent).
  const clampZoomOut = (figure: any) => {
    const eye = figure?.layout?.scene?.camera?.eye;
    if (!eye) return;
    const dist = Math.sqrt(eye.x ** 2 + eye.y ** 2 + eye.z ** 2);
    if (dist > MAX_EYE_DISTANCE * 1.01 && graphDivRef.current && window.Plotly) {
      const scale = MAX_EYE_DISTANCE / dist;
      window.Plotly.relayout(graphDivRef.current, {
        "scene.camera.eye": { x: eye.x * scale, y: eye.y * scale, z: eye.z * scale },
      } as any);
    }
  };

  if (empty) {
    return <Skeleton className="h-[420px] w-full" />;
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
            camera: { eye: DEFAULT_EYE },
          },
          font: { family: "Geist Variable, sans-serif", color: "hsl(0, 0%, 98%)" },
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%", height: "100%" }}
        useResizeHandler
        onInitialized={(_figure: any, graphDiv: any) => { graphDivRef.current = graphDiv; }}
        onUpdate={(figure: any, graphDiv: any) => { graphDivRef.current = graphDiv; clampZoomOut(figure); }}
      />
    </div>
  );
}
