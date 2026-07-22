"use client";
import { useEffect, useState } from "react";
import { api, DosBacktestResponse, DosLiveSignal, DosSlStatus } from "@/lib/api";
import Card from "@/components/Card";
import Badge from "@/components/Badge";
import DataSourceBadge from "@/components/DataSourceBadge";
import { Button } from "@/components/ui/button";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";

import { Skeleton, SkeletonBlock } from "@/components/Skeleton";

interface OpenPosition {
  dayType: string;
  optionType: string;
  strike: number;
  entryPremium: number;
}

export default function DosPage() {
  const [signal, setSignal] = useState<DosLiveSignal | null>(null);
  const [backtest, setBacktest] = useState<DosBacktestResponse | null>(null);
  const [position, setPosition] = useState<OpenPosition | null>(null);
  const [slStatus, setSlStatus] = useState<DosSlStatus | null>(null);
  const [persistState, setPersistState] = useState<"idle" | "saving" | "done" | "error">("idle");

  useEffect(() => {
    api.dosLiveSignal().then(setSignal).catch(console.error);
    api.dosBacktest(8).then(setBacktest).catch(console.error);
  }, []);

  // SL monitor: once a position is "entered", poll /api/dos/sl-status --
  // MVP requirement: "Stop-loss monitor with visual alert for both initial
  // and trailing SL." Previously this endpoint existed on the backend but
  // nothing on the frontend ever called it.
  useEffect(() => {
    if (!position) return;
    let cancelled = false;
    function poll() {
      if (!position) return;
      api
        .dosSlStatus(position.dayType, position.optionType, position.strike, position.entryPremium)
        .then((s) => {
          if (!cancelled) setSlStatus(s);
        })
        .catch(console.error);
    }
    poll();
    const id = setInterval(poll, 10000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [position]);

  function enterTrade() {
    if (!signal || !signal.signal || !signal.recommended_strike || !signal.recommended_premium) return;
    setPosition({
      dayType: signal.day_type,
      optionType: signal.signal,
      strike: signal.recommended_strike,
      entryPremium: signal.recommended_premium,
    });
    setSlStatus(null);
  }

  async function saveToSupabase() {
    setPersistState("saving");
    try {
      const result = await api.dosBacktest(8, true);
      setBacktest(result);
      setPersistState("done");
    } catch (e) {
      console.error(e);
      setPersistState("error");
    }
  }

  const equityData = backtest?.trades.map((t, i) => ({ trade: i + 1, pnl: t.cumulative_pnl })) || [];

  return (
    <div className="space-y-4 max-w-6xl">
      <div>
        <h1 className="font-sans text-xl font-medium">DOS Strategy</h1>
        <p className="text-sm text-muted-foreground mt-1">Direction of SuperTrend &middot; Bank Nifty Futures &middot; Wed/Thu expiry, 5-min SuperTrend(10,3)</p>
        <p className="text-xs text-warn/90 mt-2 max-w-2xl leading-relaxed">
          Note: this module follows the assignment brief's Bank Nifty weekly Wed/Thu expiry spec as an
          educational exercise. In the real market, Bank Nifty weekly options were discontinued by NSE in
          November 2024 (SEBI's one-weekly-expiry-per-exchange rule) -- Bank Nifty now expires monthly, on
          the last Tuesday of the month. Nifty 50's own weekly expiry separately moved from Thursday to
          Tuesday effective September 1, 2025. The Wed/Thu, twice-a-week cadence modeled here does not
          currently exist on NSE.
        </p>
      </div>

      <Card
        title="Live Signal Panel"
        info="Direction of SuperTrend on Bank Nifty futures: sell a call when price is above SuperTrend, sell a put when it's below, only on Wed/Thu expiry days from 9:20 AM."
        subtitle={
          signal && signal.active && signal.is_mock
            ? "Mock feed — swap for a live BNF futures feed"
            : signal && !signal.active
            ? "Inactive today"
            : undefined
        }
      >
        {!signal ? (
          <div className="grid grid-cols-2 sm:grid-cols-6 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i}>
                <Skeleton className="h-2.5 w-16 mb-2" />
                <Skeleton className="h-6 w-14" />
              </div>
            ))}
          </div>
        ) : !signal.active ? (
          <div className="text-sm text-muted-foreground">
            DOS is only active on Wednesday and Thursday (Bank Nifty weekly expiry days). Today is{" "}
            <span className="text-foreground">{signal.day_type}</span> — no live signal to show.
          </div>
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-2 sm:grid-cols-6 gap-4 items-center">
              <div>
                <div className="text-[11px] text-muted-foreground">BNF Fut</div>
                <div className="font-mono mono-nums text-lg">{signal.bnf_fut?.toLocaleString()}</div>
              </div>
              <div>
                <div className="text-[11px] text-muted-foreground">SuperTrend</div>
                <div className="font-mono mono-nums text-lg">{signal.supertrend?.toLocaleString()}</div>
              </div>
              <div>
                <div className="text-[11px] text-muted-foreground">Trend</div>
                <Badge label={signal.trend === "up" ? "bullish" : "bearish"} />
              </div>
              <div>
                <div className="text-[11px] text-muted-foreground">Signal</div>
                {signal.signal ? <Badge label={signal.signal} /> : <span className="text-muted-foreground text-sm">None</span>}
              </div>
              <div>
                <div className="text-[11px] text-muted-foreground">Recommended Strike</div>
                <div className="font-mono mono-nums text-lg text-mainBlue">{signal.recommended_strike ?? "-"}</div>
              </div>
              <div>
                <div className="text-[11px] text-muted-foreground">Premium</div>
                <div className="font-mono mono-nums text-lg text-mainBlue">
                  {signal.recommended_premium !== null ? `₹${signal.recommended_premium.toFixed(2)}` : "-"}
                </div>
              </div>
            </div>
            {signal.signal && signal.recommended_strike && signal.recommended_premium && !position && (
              <Button size="sm" variant="secondary" onClick={enterTrade}>
                Enter Trade &amp; Start SL Monitor
              </Button>
            )}
          </div>
        )}
      </Card>

      {position && (
        <Card
          title="Stop-Loss Monitor"
          info="Initial SL is 50% of premium sold on Wednesday, 100% on Thursday. Trailing SL triggers once price closes beyond the SuperTrend value."
          subtitle={`Short ${position.optionType} ${position.strike} @ ₹${position.entryPremium.toFixed(2)} entry`}
        >
          {!slStatus ? (
            <div className="text-muted-foreground text-sm">Checking SL levels...</div>
          ) : (
            <div className="space-y-3">
              {slStatus.alert && (
                <div className="px-3 py-2 rounded bg-bearish/10 border border-bearish/30 text-bearish text-sm font-medium">
                  ⚠ Alert: {slStatus.exit_reason === "initial_sl" ? "Initial SL breached" : "Trailing SL breached"} — exit recommended
                </div>
              )}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div>
                  <div className="text-[11px] text-muted-foreground">Current Premium</div>
                  <div className="font-mono mono-nums text-lg">₹{slStatus.current_premium.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-[11px] text-muted-foreground">Initial SL Level</div>
                  <div className={`font-mono mono-nums text-lg ${slStatus.initial_sl_breached ? "text-bearish" : "text-foreground"}`}>
                    ₹{slStatus.initial_sl_level.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] text-muted-foreground">Trailing SL</div>
                  <Badge label={slStatus.trailing_sl_breached ? "bearish" : "neutral"} />
                </div>
                <div>
                  <div className="text-[11px] text-muted-foreground">Data</div>
                  <DataSourceBadge dataSource={slStatus.is_mock ? "mock" : "live"} liveFetchError={slStatus.live_fetch_error} />
                </div>
              </div>
              <Button size="sm" variant="outline" onClick={() => { setPosition(null); setSlStatus(null); }}>
                Exit / Stop Monitoring
              </Button>
            </div>
          )}
        </Card>
      )}

      {!backtest && (
        <div className="bg-card border border-border rounded-card p-4 space-y-4">
          <div>
            <Skeleton className="h-4 w-40 mb-3" />
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i}>
                  <Skeleton className="h-6 w-16 mb-1.5" />
                  <Skeleton className="h-2.5 w-14" />
                </div>
              ))}
            </div>
          </div>
          <SkeletonBlock className="h-64 w-full" />
        </div>
      )}

      {backtest && (
        <>
          <Card
            title="Backtest Summary"
            info="DOS run across the last several weekly expiry Wed/Thu sessions using NSE Bhav Copy data, tracking win rate, P&L, and how often stop-losses were hit."
            subtitle={`${backtest.sessions_covered ?? 8} weeks, Wed + Thu expiry sessions`}
          >
            <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
              <DataSourceBadge dataSource={backtest.data_source} liveFetchError={backtest.live_fetch_error} />
              <div className="flex items-center gap-2">
                {backtest.persisted_to_supabase != null && (
                  <span className="text-xs text-muted-foreground">
                    Saved {backtest.persisted_to_supabase} trades to Supabase
                  </span>
                )}
                <Button size="sm" variant="secondary" onClick={saveToSupabase} isLoading={persistState === "saving"}>
                  Save Trade Log to Supabase
                </Button>
                {persistState === "error" && <span className="text-xs text-bearish">Save failed</span>}
              </div>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
              <Stat label="Trades" value={backtest.summary.total_trades.toString()} />
              <Stat label="Win Rate" value={`${backtest.summary.win_rate_pct}%`} good={backtest.summary.win_rate_pct >= 50} />
              <Stat label="Total P&L" value={`₹${backtest.summary.total_pnl_rupees.toLocaleString()}`} good={backtest.summary.total_pnl_rupees >= 0} />
              <Stat label="SL Hit Rate" value={`${backtest.summary.sl_hit_rate_pct}%`} />
              <Stat label="Best / Worst" value={`₹${backtest.summary.best_trade_rupees.toLocaleString()} / ₹${backtest.summary.worst_trade_rupees.toLocaleString()}`} />
            </div>
          </Card>

          <Card title="Equity Curve" info="Cumulative P&L across the backtest, trade by trade -- a rising line means the strategy compounded gains over the period tested.">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={equityData}>
                  <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" />
                  <XAxis dataKey="trade" stroke="hsl(var(--muted-foreground))" fontSize={11} label={{ value: "Trade #", position: "insideBottom", offset: -3, fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
                  <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} />
                  <ReferenceLine y={0} stroke="hsl(var(--border))" />
                  <Tooltip contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", fontSize: 12 }} formatter={(v: number) => [`₹${v.toLocaleString()}`, "Cumulative P&L"]} />
                  <Line type="stepAfter" dataKey="pnl" stroke="#437DFB" strokeWidth={2} dot={{ r: 2 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card title="Trade Log" info="Every simulated trade in the backtest: entry strike and premium, exit reason (SL hit or market close), and the resulting P&L per trade.">
            <div className="overflow-x-auto -m-4 p-4">
              <table className="w-full text-xs font-mono mono-nums">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
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
                    <tr key={i} className="border-b border-border/50 hover:bg-muted/40">
                      <td className="py-1.5 px-2">{t.session_date}</td>
                      <td className="py-1.5 px-2 text-muted-foreground">{t.day_type}</td>
                      <td className="py-1.5 px-2"><Badge label={t.option_type} /></td>
                      <td className="py-1.5 px-2">{t.strike}</td>
                      <td className="py-1.5 px-2">{t.premium_sold.toFixed(2)}</td>
                      <td className="py-1.5 px-2">
                        {t.premium_exit.toFixed(2)}
                        {t.bhav_copy_verified && <span className="ml-1 text-bullish" title="Cross-checked against NSE Bhav Copy">✓</span>}
                      </td>
                      <td className="py-1.5 px-2 text-muted-foreground">{t.exit_reason}</td>
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
      <div className={`font-mono mono-nums text-lg ${good === undefined ? "text-foreground" : good ? "text-bullish" : "text-bearish"}`}>{value}</div>
      <div className="text-[11px] text-muted-foreground mt-0.5">{label}</div>
    </div>
  );
}
