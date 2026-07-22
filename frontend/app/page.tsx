import Card from "@/components/Card";
import Badge from "@/components/Badge";
import GreekGauge from "@/components/GreekGauge";
import DataSourceBadge from "@/components/DataSourceBadge";
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
        <h1 className="font-sans text-xl font-medium">Overview</h1>
        <p className="text-sm text-muted-foreground mt-1 flex items-center gap-2 flex-wrap">
          <span>
            NIFTY spot {chain.spot.toLocaleString()} &middot; nearest expiry {chain.expiry_days}d
          </span>
          <DataSourceBadge dataSource={chain.data_source} liveFetchError={chain.live_fetch_error} />
        </p>
      </div>

      {/* Signature element: ATM Greeks as gauges, echoing the deck's risk-dashboard icons */}
      <Card
        title="ATM Risk Dashboard"
        subtitle={`Strike ${atmRow.strike} Call`}
        info="Delta, Gamma, Theta, and Vega for the at-the-money call, computed from Black-Scholes. These show how the option's price reacts to spot, spot's rate of change, time decay, and volatility."
      >
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <GreekGauge symbol="Δ" label="Delta" value={atmRow.delta} min={0} max={1} color="hsl(160, 60%, 45%)" decimals={3} info="Rate of change of option price per ₹1 move in the underlying. ~0.5 at-the-money." />
          <GreekGauge symbol="Γ" label="Gamma" value={atmRow.gamma} min={0} max={0.005} color="#437DFB" decimals={4} info="Rate of change of Delta itself. Highest for at-the-money options near expiry." />
          <GreekGauge symbol="Θ" label="Theta/day" value={atmRow.theta} min={-20} max={0} color="#D93036" decimals={2} info="Value the option loses per day from time decay alone, holding everything else constant." />
          <GreekGauge symbol="ν" label="Vega" value={atmRow.vega} min={0} max={30} color="hsl(30, 80%, 55%)" decimals={2} info="Change in option price per 1 percentage-point move in implied volatility." />
        </div>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card title="PCR Signal" info="Put-Call Ratio = total put open interest / total call open interest. Above 1.3 skews bullish (heavy put writing), below 0.7 skews bearish (heavy call writing).">
          <div className="flex items-center justify-between mb-2">
            <span className="font-mono mono-nums text-2xl">{interp.pcr.value}</span>
            <Badge label={interp.pcr.sentiment || "neutral"} />
          </div>
          <p className="text-xs text-muted-foreground">{interp.pcr.note}</p>
        </Card>
        <Card title="Max Pain" info="The strike where option writers collectively lose the least money at expiry. Prices often gravitate here as expiry approaches.">
          <div className="font-mono mono-nums text-2xl mb-2">{Number(interp.max_pain.value).toFixed(0)}</div>
          <p className="text-xs text-muted-foreground">{interp.max_pain.note}</p>
        </Card>
        <Card title="IV Spike" info="How far current ATM implied volatility sits from its recent average. A large positive spike usually means the market is pricing in an event.">
          <div className="flex items-center justify-between mb-2">
            <span className="font-mono mono-nums text-2xl">{interp.iv_spike.value}%</span>
            <Badge label={Math.abs(Number(interp.iv_spike.value)) < 15 ? "neutral" : Number(interp.iv_spike.value) > 0 ? "elevated" : "depressed"} />
          </div>
          <p className="text-xs text-muted-foreground">{interp.iv_spike.note}</p>
        </Card>
      </div>

      <Card
        title="DOS Strategy — 8 Week Backtest"
        subtitle="Bank Nifty Futures, SuperTrend(10,3), Wed/Thu expiry sessions"
        info="Direction of SuperTrend: sells the option on the side SuperTrend favors on Bank Nifty's weekly expiry days, with initial and trailing stop-losses. This is the backtest run over the last 8 weekly expiry sessions."
      >
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
      <div className={`font-mono mono-nums text-lg ${highlight === undefined ? "text-foreground" : highlight ? "text-bullish" : "text-bearish"}`}>
        {value}
      </div>
      <div className="text-[11px] text-muted-foreground mt-0.5">{label}</div>
    </div>
  );
}
