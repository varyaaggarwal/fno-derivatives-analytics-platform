"use client";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChainRow } from "@/lib/api";

function formatOi(v: number): string {
  if (v >= 10000000) return `${(v / 10000000).toFixed(1)}Cr`;
  if (v >= 100000) return `${(v / 100000).toFixed(1)}L`;
  if (v >= 1000) return `${(v / 1000).toFixed(0)}k`;
  return String(v);
}

export default function OiByStrikeChart({ rows, spot }: { rows: ChainRow[]; spot: number }) {
  const byStrike = new Map<number, { strike: number; callOi: number; putOi: number }>();
  for (const r of rows) {
    const entry = byStrike.get(r.strike) || { strike: r.strike, callOi: 0, putOi: 0 };
    if (r.option_type === "call") entry.callOi += r.open_interest;
    else entry.putOi += r.open_interest;
    byStrike.set(r.strike, entry);
  }
  const data = [...byStrike.values()]
    .sort((a, b) => a.strike - b.strike)
    .filter((d) => Math.abs(d.strike - spot) <= spot * 0.05); // keep the chart readable -- +/-5% around spot

  return (
    <div className="h-56">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 8, left: 8, bottom: 0 }}>
          <XAxis
            dataKey="strike"
            tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
            tickFormatter={(v) => v.toLocaleString()}
            axisLine={{ stroke: "hsl(var(--border))" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
            tickFormatter={formatOi}
            axisLine={false}
            tickLine={false}
            width={40}
          />
          <Tooltip
            contentStyle={{
              background: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(value: number, name: string) => [formatOi(value), name === "callOi" ? "Call OI" : "Put OI"]}
            labelFormatter={(strike) => `Strike ${strike}`}
          />
          <Bar dataKey="callOi" fill="hsl(var(--chart-2))" radius={[2, 2, 0, 0]} />
          <Bar dataKey="putOi" fill="var(--logout)" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
