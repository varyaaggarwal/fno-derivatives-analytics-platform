"use client";
import { useEffect, useMemo, useState } from "react";
import { api, VolSurfaceRow } from "@/lib/api";
import Card from "@/components/Card";
import VolSurface3D from "@/components/VolSurface3D";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

function ivColor(iv: number, minIv: number, maxIv: number) {
  const pct = (iv - minIv) / (maxIv - minIv || 1);
  // interpolate mainBlue (low) -> amber chart-3 (mid) -> logout red (high), the template's own tokens
  if (pct < 0.5) {
    const t = pct / 0.5;
    return lerpColor("#437DFB", "#E88C30", t);
  }
  const t = (pct - 0.5) / 0.5;
  return lerpColor("#E88C30", "#D93036", t);
}
function lerpColor(a: string, b: string, t: number) {
  const pa = parseInt(a.slice(1), 16), pb = parseInt(b.slice(1), 16);
  const ar = (pa >> 16) & 255, ag = (pa >> 8) & 255, ab = pa & 255;
  const br = (pb >> 16) & 255, bg = (pb >> 8) & 255, bb = pb & 255;
  const r = Math.round(ar + (br - ar) * t), g = Math.round(ag + (bg - ag) * t), bl = Math.round(ab + (bb - ab) * t);
  return `rgb(${r},${g},${bl})`;
}

export default function SurfacePage() {
  const [rows, setRows] = useState<VolSurfaceRow[]>([]);
  useEffect(() => {
    api.volSurface().then((d) => setRows(d.rows.filter((r) => r.option_type === "call")));
  }, []);

  const { strikes, expiries, grid, minIv, maxIv } = useMemo(() => {
    const strikeSet = Array.from(new Set(rows.map((r) => r.strike))).sort((a, b) => a - b);
    const expirySet = Array.from(new Set(rows.map((r) => r.expiry_days))).sort((a, b) => a - b);
    const g: Record<string, number> = {};
    let mn = Infinity, mx = -Infinity;
    rows.forEach((r) => {
      g[`${r.strike}-${r.expiry_days}`] = r.implied_volatility;
      mn = Math.min(mn, r.implied_volatility);
      mx = Math.max(mx, r.implied_volatility);
    });
    return { strikes: strikeSet, expiries: expirySet, grid: g, minIv: mn, maxIv: mx };
  }, [rows]);

  const smile = useMemo(() => {
    if (expiries.length === 0) return [];
    const nearest = expiries[0];
    return rows.filter((r) => r.expiry_days === nearest).sort((a, b) => a.strike - b.strike);
  }, [rows, expiries]);

  return (
    <div className="space-y-4 max-w-6xl">
      <div>
        <h1 className="font-sans text-xl font-medium">Volatility Surface</h1>
        <p className="text-sm text-muted-foreground mt-1">Call IV across strike &amp; expiry, mock multi-expiry chain</p>
      </div>

      <Card title="Implied Volatility Surface (3D)" subtitle="Strike × expiry days × IV, rotate/zoom to inspect">
        <VolSurface3D rows={rows} />
      </Card>

      <Card title="IV Smile" subtitle={expiries.length ? `Nearest expiry: ${expiries[0]}d` : ""}>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={smile}>
              <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" />
              <XAxis dataKey="strike" stroke="hsl(var(--muted-foreground))" fontSize={11} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} unit="%" />
              <Tooltip contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", fontSize: 12 }} />
              <Line type="monotone" dataKey="implied_volatility" stroke="#437DFB" strokeWidth={2} dot={{ r: 2 }} name="IV %" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card title="Vol Surface Grid" subtitle="Strike (rows) × Expiry days (columns), color = IV">
        <div className="overflow-x-auto -m-4 p-4">
          <table className="text-xs font-mono mono-nums border-separate border-spacing-[2px]">
            <thead>
              <tr>
                <th className="p-1 text-muted-foreground text-left">Strike</th>
                {expiries.map((e) => (
                  <th key={e} className="p-1 text-muted-foreground">{e}d</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {strikes.map((s) => (
                <tr key={s}>
                  <td className="p-1 text-muted-foreground text-right pr-2">{s}</td>
                  {expiries.map((e) => {
                    const iv = grid[`${s}-${e}`];
                    return (
                      <td
                        key={e}
                        title={`${iv?.toFixed(2)}%`}
                        className="w-12 h-7 text-center rounded text-[10px] text-background font-medium"
                        style={{ background: iv !== undefined ? ivColor(iv, minIv, maxIv) : "hsl(var(--border))" }}
                      >
                        {iv !== undefined ? iv.toFixed(1) : "-"}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
