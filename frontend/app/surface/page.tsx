"use client";
import { useEffect, useMemo, useState } from "react";
import { api, VolSurfaceRow } from "@/lib/api";
import Card from "@/components/Card";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

function ivColor(iv: number, minIv: number, maxIv: number) {
  const pct = (iv - minIv) / (maxIv - minIv || 1);
  // interpolate indigo (low) -> amber (mid) -> red (high), matching the accent/warn/bearish tokens
  if (pct < 0.5) {
    const t = pct / 0.5;
    return lerpColor("#6366F1", "#FBBF24", t);
  }
  const t = (pct - 0.5) / 0.5;
  return lerpColor("#FBBF24", "#F87171", t);
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
        <h1 className="font-display text-xl font-medium">Volatility Surface</h1>
        <p className="text-sm text-muted mt-1">Call IV across strike &amp; expiry, mock multi-expiry chain</p>
      </div>

      <Card title="IV Smile" subtitle={expiries.length ? `Nearest expiry: ${expiries[0]}d` : ""}>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={smile}>
              <CartesianGrid stroke="#1F2733" strokeDasharray="3 3" />
              <XAxis dataKey="strike" stroke="#8B98A5" fontSize={11} />
              <YAxis stroke="#8B98A5" fontSize={11} unit="%" />
              <Tooltip contentStyle={{ background: "#12171F", border: "1px solid #1F2733", fontSize: 12 }} />
              <Line type="monotone" dataKey="implied_volatility" stroke="#6366F1" strokeWidth={2} dot={{ r: 2 }} name="IV %" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card title="Vol Surface Grid" subtitle="Strike (rows) × Expiry days (columns), color = IV">
        <div className="overflow-x-auto -m-4 p-4">
          <table className="text-xs font-mono mono-nums border-separate border-spacing-[2px]">
            <thead>
              <tr>
                <th className="p-1 text-muted text-left">Strike</th>
                {expiries.map((e) => (
                  <th key={e} className="p-1 text-muted">{e}d</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {strikes.map((s) => (
                <tr key={s}>
                  <td className="p-1 text-muted text-right pr-2">{s}</td>
                  {expiries.map((e) => {
                    const iv = grid[`${s}-${e}`];
                    return (
                      <td
                        key={e}
                        title={`${iv?.toFixed(2)}%`}
                        className="w-12 h-7 text-center rounded text-[10px] text-bg font-medium"
                        style={{ background: iv !== undefined ? ivColor(iv, minIv, maxIv) : "#1F2733" }}
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
