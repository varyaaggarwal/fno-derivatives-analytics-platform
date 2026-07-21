"use client";
import { useEffect, useState } from "react";
import { api, PnlDecomposeResponse } from "@/lib/api";
import Card from "@/components/Card";
import Badge from "@/components/Badge";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from "recharts";

export default function PnlPage() {
  const [data, setData] = useState<PnlDecomposeResponse | null>(null);
  useEffect(() => {
    api.pnlDecompose().then(setData).catch(console.error);
  }, []);

  if (!data) return <div className="text-muted-foreground text-sm">Loading...</div>;

  const chartData = [
    { name: "Delta", value: data.delta_pnl },
    { name: "Gamma", value: data.gamma_pnl },
    { name: "Theta", value: data.theta_pnl },
    { name: "Vega", value: data.vega_pnl },
    { name: "Residual", value: data.residual_pnl },
  ];

  return (
    <div className="space-y-4 max-w-4xl">
      <div>
        <h1 className="font-sans text-xl font-medium">P&L Decomposer</h1>
        <p className="text-sm text-muted-foreground mt-1 flex items-center gap-2 flex-wrap">
          <span>Short 1 lot ATM NIFTY Call &middot; spot +0.8%, IV +1.3pts, 1 day passes</span>
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium border font-mono bg-muted/40 text-muted-foreground border-muted-foreground/30">
            FIXED SAMPLE SCENARIO
          </span>
        </p>
      </div>

      <Card title="Attribution by Greek">
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" />
              <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} />
              <ReferenceLine y={0} stroke="hsl(var(--border))" />
              <Tooltip
                contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", fontSize: 12 }}
                formatter={(v: number) => [`₹${v.toLocaleString()}`, "P&L"]}
              />
              <Bar dataKey="value" radius={[4, 4, 4, 4]}>
                {chartData.map((d, i) => (
                  <Cell key={i} fill={d.value >= 0 ? "hsl(var(--chart-2))" : "#D93036"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <Card title="Actual Total P&L">
          <div className={`font-mono mono-nums text-2xl ${data.actual_pnl >= 0 ? "text-bullish" : "text-bearish"}`}>
            ₹{data.actual_pnl.toLocaleString()}
          </div>
        </Card>
        <Card title="Primary Driver">
          <Badge label="neutral" />
          <div className="mt-2 font-sans text-lg">{data.primary_driver}</div>
        </Card>
        <Card title="Residual (higher-order)">
          <div className="font-mono mono-nums text-lg text-muted-foreground">₹{data.residual_pnl.toLocaleString()}</div>
          <p className="text-xs text-muted-foreground mt-1">Effects the linear/quadratic Greeks approximation misses.</p>
        </Card>
      </div>
    </div>
  );
}
