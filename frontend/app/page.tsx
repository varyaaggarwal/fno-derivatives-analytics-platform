import Card from "@/components/Card";
import Badge from "@/components/Badge";
import GreekGauge from "@/components/GreekGauge";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function OverviewPage() {
  const [chain, interp, dos] = await Promise.all([
    api.chain(),
    api.interpretation(),
    api.dosBacktest(8),
  ]);

  const atmRow = chain.rows
    .filter((r) => r.option_type === "call")
    .reduce((best, r) => (Math.abs(r.strike - chain.spot) < Math.abs(best.strike - chain.spot) ? r : best));

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="font-display text-xl font-medium">Overview</h1>
        <p className="text-sm text-muted mt-1">
          NIFTY spot {chain.spot.toLocaleString()} &middot; nearest expiry {chain.expiry_days}d &middot; snapshot mock data
        </p>
      </div>

      {/* Signature element: ATM Greeks as gauges, echoing the deck's risk-dashboard icons */}
      <Card title="ATM Risk Dashboard" subtitle={`Strike ${atmRow.strike} Call`}>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <GreekGauge symbol="Δ" label="Delta" value={atmRow.delta} min={0} max={1} color="#34D399" decimals={3} />
          <GreekGauge symbol="Γ" label="Gamma" value={atmRow.gamma} min={0} max={0.005} color="#6366F1" decimals={4} />
          <GreekGauge symbol="Θ" label="Theta/day" value={atmRow.theta} min={-20} max={0} color="#F87171" decimals={2} />
          <GreekGauge symbol="ν" label="Vega" value={atmRow.vega} min={0} max={30} color="#FBBF24" decimals={2} />
        </div>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card title="PCR Signal">
          <div className="flex items-center justify-between mb-2">
            <span className="font-mono mono-nums text-2xl">{interp.pcr.value}</span>
            <Badge label={interp.pcr.sentiment || "neutral"} />
          </div>
          <p className="text-xs text-muted">{interp.pcr.note}</p>
        </Card>
        <Card title="Max Pain">
          <div className="font-mono mono-nums text-2xl mb-2">{Number(interp.max_pain.value).toFixed(0)}</div>
          <p className="text-xs text-muted">{interp.max_pain.note}</p>
        </Card>
        <Card title="IV Spike">
          <div className="flex items-center justify-between mb-2">
            <span className="font-mono mono-nums text-2xl">{interp.iv_spike.value}%</span>
            <Badge label={Math.abs(Number(interp.iv_spike.value)) < 15 ? "neutral" : Number(interp.iv_spike.value) > 0 ? "elevated" : "depressed"} />
          </div>
          <p className="text-xs text-muted">{interp.iv_spike.note}</p>
        </Card>
      </div>

      <Card title="DOS Strategy — 8 Week Backtest" subtitle="Bank Nifty Futures, SuperTrend(10,3), Wed/Thu expiry sessions">
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
          <Stat label="Trades" value={dos.summary.total_trades.toString()} />
          <Stat label="Win Rate" value={`${dos.summary.win_rate_pct}%`} highlight={dos.summary.win_rate_pct >= 50} />
          <Stat label="Total P&L" value={`₹${dos.summary.total_pnl_rupees.toLocaleString()}`} highlight={dos.summary.total_pnl_rupees >= 0} />
          <Stat label="SL Hit Rate" value={`${dos.summary.sl_hit_rate_pct}%`} />
          <Stat label="Avg P&L / Trade" value={`₹${dos.summary.avg_pnl_rupees.toLocaleString()}`} highlight={dos.summary.avg_pnl_rupees >= 0} />
        </div>
      </Card>
    </div>
  );
}

function Stat({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div>
      <div className={`font-mono mono-nums text-lg ${highlight === undefined ? "text-text" : highlight ? "text-bullish" : "text-bearish"}`}>
        {value}
      </div>
      <div className="text-[11px] text-muted mt-0.5">{label}</div>
    </div>
  );
}
