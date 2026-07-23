"use client";
import { useEffect, useState } from "react";
import { api, PnlDecomposeResponse } from "@/lib/api";
import Card from "@/components/Card";
import Badge from "@/components/Badge";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from "recharts";

import { Skeleton, SkeletonBlock } from "@/components/Skeleton";

// Bounds for the three scenario inputs -- kept generous enough to see
// interesting Greek attribution shifts, but tight enough that the position
// (default: short 1 lot ATM NIFTY Call, 6 days to expiry) stays in a
// sensible regime rather than deep ITM/OTM or past its own expiry.
const SPOT_MOVE_MIN = -5;
const SPOT_MOVE_MAX = 5;
const IV_CHANGE_MIN = -10;
const IV_CHANGE_MAX = 10;
const DAYS_ELAPSED_MIN = 0;
const DAYS_ELAPSED_MAX = 6; // matches the default 6-day expiry_days -- see main.py's clamp for what happens beyond it

function ScenarioSlider({
  label, value, min, max, step, unit, onChange,
}: {
  label: string; value: number; min: number; max: number; step: number; unit: string;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1.5">
        <label className="text-xs text-muted-foreground">{label}</label>
        <span className="font-mono mono-nums text-sm text-foreground">
          {value > 0 && unit !== " days" ? "+" : ""}{value}{unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-[hsl(var(--chart-2))] cursor-pointer"
      />
    </div>
  );
}

export default function PnlPage() {
  const [data, setData] = useState<PnlDecomposeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [spotMovePct, setSpotMovePct] = useState(0.8);
  const [ivChangePts, setIvChangePts] = useState(1.3);
  const [daysElapsed, setDaysElapsed] = useState(1);

  // Debounced fetch: re-run the decomposition ~250ms after the user stops
  // dragging a slider, rather than firing an API call on every intermediate
  // value while dragging.
  useEffect(() => {
    setLoading(true);
    const handle = setTimeout(() => {
      api.pnlDecompose({ spotMovePct, ivChangePts, daysElapsed })
        .then((d) => { setData(d); setError(null); })
        .catch((err) => setError(String(err)))
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(handle);
  }, [spotMovePct, ivChangePts, daysElapsed]);

  const resetToDefaults = () => {
    setSpotMovePct(0.8);
    setIvChangePts(1.3);
    setDaysElapsed(1);
  };

  if (!data) {
    return (
      <div className="space-y-4 max-w-4xl">
        <div>
          <h1 className="font-sans text-xl font-medium">P&L Decomposer</h1>
          <Skeleton className="h-4 w-72 mt-2" />
        </div>
        <div className="bg-card border border-border rounded-card p-4">
          <Skeleton className="h-4 w-40 mb-3" />
          <SkeletonBlock className="h-72 w-full" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-card border border-border rounded-card p-4">
              <Skeleton className="h-4 w-24 mb-3" />
              <Skeleton className="h-7 w-20" />
            </div>
          ))}
        </div>
      </div>
    );
  }

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
          <span>Short 1 lot ATM NIFTY Call &middot; adjust index move, IV change, and time below</span>
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium border font-mono bg-muted/40 text-muted-foreground border-muted-foreground/30">
            INTERACTIVE SCENARIO
          </span>
        </p>
      </div>

      <Card
        title="Scenario Inputs"
        info="Drag any of these to see how the P&L attribution below shifts. Index Move and IV Change describe how the market moved between t0 and t1; Time is how many trading days passed -- more days means more theta decay, holding everything else fixed."
      >
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          <ScenarioSlider
            label="Index Move"
            value={spotMovePct}
            min={SPOT_MOVE_MIN}
            max={SPOT_MOVE_MAX}
            step={0.1}
            unit="%"
            onChange={setSpotMovePct}
          />
          <ScenarioSlider
            label="IV Change"
            value={ivChangePts}
            min={IV_CHANGE_MIN}
            max={IV_CHANGE_MAX}
            step={0.1}
            unit="pts"
            onChange={setIvChangePts}
          />
          <ScenarioSlider
            label="Time Elapsed"
            value={daysElapsed}
            min={DAYS_ELAPSED_MIN}
            max={DAYS_ELAPSED_MAX}
            step={1}
            unit=" days"
            onChange={setDaysElapsed}
          />
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={resetToDefaults}
            className="text-xs px-2.5 py-1 rounded border border-border text-muted-foreground hover:bg-muted/40 transition-colors"
          >
            Reset to default scenario
          </button>
          {loading && <span className="text-xs text-muted-foreground animate-pulse">Recalculating&hellip;</span>}
          {error && <span className="text-xs text-bearish">{error}</span>}
        </div>
      </Card>

      <Card title="Attribution by Greek" info="Splits the position's total P&L into how much each Greek contributed -- Delta (spot move), Gamma (convexity), Theta (time decay), Vega (IV change), and a residual for higher-order effects.">
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
        <Card title="Actual Total P&L" info="The real P&L on the position for this scenario -- the sum of all Greek contributions plus the residual.">
          <div className={`font-mono mono-nums text-2xl ${data.actual_pnl >= 0 ? "text-bullish" : "text-bearish"}`}>
            ₹{data.actual_pnl.toLocaleString()}
          </div>
        </Card>
        <Card title="Primary Driver" info="Whichever Greek contributed the largest share of the P&L move in this scenario.">
          <Badge label="neutral" />
          <div className="mt-2 font-sans text-lg">{data.primary_driver}</div>
        </Card>
        <Card title="Residual (higher-order)" info="P&L left unexplained by the first-order Greek approximations -- comes from cross-effects and higher-order curvature the linear model misses.">
          <div className="font-mono mono-nums text-lg text-muted-foreground">₹{data.residual_pnl.toLocaleString()}</div>
          <p className="text-xs text-muted-foreground mt-1">Effects the linear/quadratic Greeks approximation misses.</p>
        </Card>
      </div>
    </div>
  );
}
