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

  if (!data) return <div className="text-muted text-sm">Loading...</div>;

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
        <h1 className="font-display text-xl font-medium">P&L Decomposer</h1>
        <p className="text-sm text-muted mt-1">Short 1 lot ATM NIFTY Call &middot; spot +0.8%, IV +1.3pts, 1 day passes</p>
      </div>

      <Card title="Attribution by Greek">
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid stroke="#242428" strokeDasharray="3 3" />
              <XAxis dataKey="name" stroke="#8B8B92" fontSize={12} />
              <YAxis stroke="#8B8B92" fontSize={11} />
              <ReferenceLine y={0} stroke="#242428" />
              <Tooltip
                contentStyle={{ background: "#0A0A0B", border: "1px solid #242428", fontSize: 12 }}
                formatter={(v: number) => [`₹${v.toLocaleString()}`, "P&L"]}
              />
              <Bar dataKey="value" radius={[4, 4, 4, 4]}>
                {chartData.map((d, i) => (
                  <Cell key={i} fill={d.value >= 0 ? "#34D399" : "#F87171"} />
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
          <div className="mt-2 font-display text-lg">{data.primary_driver}</div>
        </Card>
        <Card title="Residual (higher-order)">
          <div className="font-mono mono-nums text-lg text-muted">₹{data.residual_pnl.toLocaleString()}</div>
          <p className="text-xs text-muted mt-1">Effects the linear/quadratic Greeks approximation misses.</p>
        </Card>
      </div>
    </div>
  );
}
