"use client";
import { useEffect, useState } from "react";
import { api, DosBacktestResponse, DosLiveSignal } from "@/lib/api";
import Card from "@/components/Card";
import Badge from "@/components/Badge";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";

export default function DosPage() {
  const [signal, setSignal] = useState<DosLiveSignal | null>(null);
  const [backtest, setBacktest] = useState<DosBacktestResponse | null>(null);

  useEffect(() => {
    api.dosLiveSignal().then(setSignal).catch(console.error);
    api.dosBacktest(8).then(setBacktest).catch(console.error);
  }, []);

  const equityData = backtest?.trades.map((t, i) => ({ trade: i + 1, pnl: t.cumulative_pnl })) || [];

  return (
    <div className="space-y-4 max-w-6xl">
      <div>
        <h1 className="font-display text-xl font-medium">DOS Strategy</h1>
        <p className="text-sm text-muted mt-1">Direction of SuperTrend &middot; Bank Nifty Futures &middot; Wed/Thu expiry, 5-min SuperTrend(10,3)</p>
      </div>

      <Card title="Live Signal Panel" subtitle={signal?.is_mock ? "Mock feed — swap for a live BNF futures feed" : undefined}>
        {signal ? (
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 items-center">
            <div>
              <div className="text-[11px] text-muted">BNF Fut</div>
              <div className="font-mono mono-nums text-lg">{signal.bnf_fut.toLocaleString()}</div>
            </div>
            <div>
              <div className="text-[11px] text-muted">SuperTrend</div>
              <div className="font-mono mono-nums text-lg">{signal.supertrend.toLocaleString()}</div>
            </div>
            <div>
              <div className="text-[11px] text-muted">Trend</div>
              <Badge label={signal.trend === "up" ? "bullish" : "bearish"} />
            </div>
            <div>
              <div className="text-[11px] text-muted">Signal</div>
              {signal.signal ? <Badge label={signal.signal} /> : <span className="text-muted text-sm">None</span>}
            </div>
            <div>
              <div className="text-[11px] text-muted">Recommended Strike</div>
              <div className="font-mono mono-nums text-lg text-accent">{signal.recommended_strike ?? "-"}</div>
            </div>
          </div>
        ) : (
          <div className="text-muted text-sm">Loading signal...</div>
        )}
      </Card>

      {backtest && (
        <>
          <Card title="Backtest Summary" subtitle="8 weeks, Wed + Thu expiry sessions">
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
              <Stat label="Trades" value={backtest.summary.total_trades.toString()} />
              <Stat label="Win Rate" value={`${backtest.summary.win_rate_pct}%`} good={backtest.summary.win_rate_pct >= 50} />
              <Stat label="Total P&L" value={`₹${backtest.summary.total_pnl_rupees.toLocaleString()}`} good={backtest.summary.total_pnl_rupees >= 0} />
              <Stat label="SL Hit Rate" value={`${backtest.summary.sl_hit_rate_pct}%`} />
              <Stat label="Best / Worst" value={`₹${backtest.summary.best_trade_rupees.toLocaleString()} / ₹${backtest.summary.worst_trade_rupees.toLocaleString()}`} />
            </div>
          </Card>

          <Card title="Equity Curve">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={equityData}>
                  <CartesianGrid stroke="#1F2733" strokeDasharray="3 3" />
                  <XAxis dataKey="trade" stroke="#8B98A5" fontSize={11} label={{ value: "Trade #", position: "insideBottom", offset: -3, fill: "#8B98A5", fontSize: 11 }} />
                  <YAxis stroke="#8B98A5" fontSize={11} />
                  <ReferenceLine y={0} stroke="#1F2733" />
                  <Tooltip contentStyle={{ background: "#12171F", border: "1px solid #1F2733", fontSize: 12 }} formatter={(v: number) => [`₹${v.toLocaleString()}`, "Cumulative P&L"]} />
                  <Line type="stepAfter" dataKey="pnl" stroke="#6366F1" strokeWidth={2} dot={{ r: 2 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card title="Trade Log">
            <div className="overflow-x-auto -m-4 p-4">
              <table className="w-full text-xs font-mono mono-nums">
                <thead>
                  <tr className="border-b border-border text-left text-muted">
                    <th className="py-1.5 px-2">Date</th>
                    <th className="py-1.5 px-2">Day</th>
                    <th className="py-1.5 px-2">Type</th>
                    <th className="py-1.5 px-2">Strike</th>
                    <th className="py-1.5 px-2">Premium Sold</th>
                    <th className="py-1.5 px-2">Premium Exit</th>
                    <th className="py-1.5 px-2">Exit Reason</th>
                    <th className="py-1.5 px-2">P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {backtest.trades.map((t, i) => (
                    <tr key={i} className="border-b border-border/50 hover:bg-surface2/40">
                      <td className="py-1.5 px-2">{t.session_date}</td>
                      <td className="py-1.5 px-2 text-muted">{t.day_type}</td>
                      <td className="py-1.5 px-2"><Badge label={t.option_type} /></td>
                      <td className="py-1.5 px-2">{t.strike}</td>
                      <td className="py-1.5 px-2">{t.premium_sold.toFixed(2)}</td>
                      <td className="py-1.5 px-2">{t.premium_exit.toFixed(2)}</td>
                      <td className="py-1.5 px-2 text-muted">{t.exit_reason}</td>
                      <td className={`py-1.5 px-2 ${t.pnl_rupees >= 0 ? "text-bullish" : "text-bearish"}`}>
                        ₹{t.pnl_rupees.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

function Stat({ label, value, good }: { label: string; value: string; good?: boolean }) {
  return (
    <div>
      <div className={`font-mono mono-nums text-lg ${good === undefined ? "text-text" : good ? "text-bullish" : "text-bearish"}`}>{value}</div>
      <div className="text-[11px] text-muted mt-0.5">{label}</div>
    </div>
  );
}
