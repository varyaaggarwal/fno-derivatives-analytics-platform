"use client";
import { useEffect, useMemo, useState } from "react";
import { api, ChainResponse, ChainRow, InterpretationResponse } from "@/lib/api";
import Card from "@/components/Card";
import Badge from "@/components/Badge";
import DataSourceBadge from "@/components/DataSourceBadge";
import MarketInterpretationPanel from "@/components/MarketInterpretationPanel";
import OiByStrikeChart from "@/components/OiByStrikeChart";
import InfoTooltip from "@/components/InfoTooltip";
import { Skeleton, SkeletonStatCard, SkeletonLine, SkeletonBlock, SkeletonTableRows } from "@/components/Skeleton";

type SortKey = keyof ChainRow;

function formatOi(v: number): string {
  return `${(v / 10000000).toFixed(2)} Cr`;
}

function StatCard({
  label,
  value,
  valueClassName,
  info,
}: {
  label: string;
  value: string;
  valueClassName?: string;
  info: string;
}) {
  return (
    <InfoTooltip text={info} className="block">
      <div className="hover-glow bg-card border border-border rounded-card px-4 py-3 cursor-help">
        <div className="text-[11px] text-muted-foreground uppercase tracking-wide">{label}</div>
        <div className={`font-mono mono-nums text-xl mt-1 ${valueClassName || ""}`}>{value}</div>
      </div>
    </InfoTooltip>
  );
}

export default function ChainPage() {
  const [data, setData] = useState<ChainResponse | null>(null);
  const [interp, setInterp] = useState<InterpretationResponse | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("strike");
  const [sortDir, setSortDir] = useState<1 | -1>(1);
  const [showAllGreeks, setShowAllGreeks] = useState(false);

  useEffect(() => {
    api.chain().then(setData).catch(console.error);
    api.interpretation().then(setInterp).catch(console.error);
  }, []);

  const rows = useMemo(() => {
    if (!data) return [];
    return [...data.rows].sort((a, b) => {
      const av = a[sortKey], bv = b[sortKey];
      if (typeof av === "string") return sortDir * String(av).localeCompare(String(bv));
      return sortDir * ((av as number) - (bv as number));
    });
  }, [data, sortKey, sortDir]);

  // Full Chain (Greeks) default view: nearest 8 strikes to spot (16 rows,
  // call+put) instead of every strike -- with 15 strikes each side of ATM
  // by default that's ~62 rows, meaning a lot of scrolling for a table most
  // people only need the near-the-money section of. "Show all" below
  // reveals the rest without losing any data.
  const nearAtmStrikesForGreeks = useMemo(() => {
    if (!data) return new Set<number>();
    const strikes = [...new Set(data.rows.map((r) => r.strike))];
    const nearest = strikes.sort((a, b) => Math.abs(a - data.spot) - Math.abs(b - data.spot)).slice(0, 8);
    return new Set(nearest);
  }, [data]);

  const visibleGreeksRows = useMemo(
    () => (showAllGreeks ? rows : rows.filter((r) => nearAtmStrikesForGreeks.has(r.strike))),
    [rows, showAllGreeks, nearAtmStrikesForGreeks]
  );

  // Strikes closest to spot first, so the side-by-side chain opens ATM instead of at the lowest strike.
  const strikesNearSpot = useMemo(() => {
    if (!data) return [];
    const strikes = [...new Set(data.rows.map((r) => r.strike))];
    return strikes.sort((a, b) => Math.abs(a - data.spot) - Math.abs(b - data.spot)).slice(0, 20).sort((a, b) => a - b);
  }, [data]);

  const byStrike = useMemo(() => {
    const m = new Map<number, { call?: ChainRow; put?: ChainRow }>();
    if (!data) return m;
    for (const r of data.rows) {
      const entry = m.get(r.strike) || {};
      if (r.option_type === "call") entry.call = r;
      else entry.put = r;
      m.set(r.strike, entry);
    }
    return m;
  }, [data]);

  const atmStrike = useMemo(() => {
    if (!data || data.rows.length === 0) return null;
    return data.rows.reduce((best, r) => (Math.abs(r.strike - data.spot) < Math.abs(best.strike - data.spot) ? r : best))
      .strike;
  }, [data]);

  const atmIv = useMemo(() => {
    if (atmStrike === null) return null;
    const entry = byStrike.get(atmStrike);
    const ivs = [entry?.call?.implied_volatility, entry?.put?.implied_volatility].filter(
      (v): v is number => v !== undefined
    );
    return ivs.length ? ivs.reduce((a, b) => a + b, 0) / ivs.length : null;
  }, [atmStrike, byStrike]);

  const callOiTotal = useMemo(
    () => (data ? data.rows.filter((r) => r.option_type === "call").reduce((s, r) => s + r.open_interest, 0) : 0),
    [data]
  );
  const putOiTotal = useMemo(
    () => (data ? data.rows.filter((r) => r.option_type === "put").reduce((s, r) => s + r.open_interest, 0) : 0),
    [data]
  );

  function toggleSort(key: SortKey) {
    if (key === sortKey) setSortDir((d) => (d === 1 ? -1 : 1));
    else {
      setSortKey(key);
      setSortDir(1);
    }
  }

  const columns: { key: SortKey; label: string }[] = [
    { key: "strike", label: "Strike" },
    { key: "option_type", label: "Type" },
    { key: "last_price", label: "LTP" },
    { key: "open_interest", label: "OI" },
    { key: "implied_volatility", label: "IV %" },
    { key: "delta", label: "Delta" },
    { key: "gamma", label: "Gamma" },
    { key: "theta", label: "Theta" },
    { key: "vega", label: "Vega" },
  ];

  return (
    <div className="space-y-4 max-w-[1400px]">
      <div>
        <h1 className="font-sans text-xl font-medium">Option Chain</h1>
        <p className="text-sm text-muted-foreground mt-1 flex items-center gap-2 flex-wrap">
          {data ? (
            <span>{`Spot ${data.spot.toLocaleString()} · Expiry ${data.expiry_days}d · ${data.rows.length} rows`}</span>
          ) : (
            <SkeletonLine className="w-72" />
          )}
          {data && <DataSourceBadge dataSource={data.data_source} liveFetchError={data.live_fetch_error} />}
        </p>
      </div>

      {/* Summary strip -- spot, PCR, max pain, ATM strike/IV, OI totals, chain bias */}
      <div className="grid grid-cols-2 sm:grid-cols-4 xl:grid-cols-8 gap-3">
        {!data ? (
          Array.from({ length: 8 }).map((_, i) => <SkeletonStatCard key={i} />)
        ) : (
          <>
            <StatCard label="Nifty Spot" value={data.spot.toLocaleString()} valueClassName="text-warn" info="Current NIFTY 50 index level, used as the reference price for ATM strike, ITM/OTM shading, and IV calculations." />
            <StatCard label="PCR" value={interp ? String(interp.pcr.value) : "--"} info="Put-Call Ratio: total put OI divided by total call OI. Above 1.3 is typically read as bullish, below 0.7 as bearish." />
            <StatCard label="Max Pain" value={interp ? Number(interp.max_pain.value).toFixed(0) : "--"} info="The strike where option writers as a group lose the least at expiry. Price often drifts toward this level near expiry." />
            <StatCard label="ATM Strike" value={atmStrike !== null ? String(atmStrike) : "--"} info="The strike closest to the current spot price -- the 'at the money' reference strike." />
            <StatCard label="ATM IV" value={atmIv !== null ? `${atmIv.toFixed(1)}%` : "--"} info="Average implied volatility of the call and put at the ATM strike. Higher means the market expects bigger moves." />
            <StatCard label="Call OI" value={formatOi(callOiTotal)} info="Total open interest (in crore contracts) across all call strikes -- a proxy for how much capital is positioned on the call side." />
            <StatCard label="Put OI" value={formatOi(putOiTotal)} info="Total open interest (in crore contracts) across all put strikes -- a proxy for how much capital is positioned on the put side." />
            <InfoTooltip text="Overall directional lean read from the Put-Call Ratio: more put OI skews bullish, more call OI skews bearish." className="block">
              <div className="hover-glow bg-card border border-border rounded-card px-4 py-3 cursor-help">
                <div className="text-[11px] text-muted-foreground uppercase tracking-wide">Chain Bias</div>
                <div className="mt-1">{interp ? <Badge label={interp.pcr.sentiment || "neutral"} /> : <Skeleton className="h-5 w-16" />}</div>
              </div>
            </InfoTooltip>
          </>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Side-by-side calls | strike | puts, ATM-centered -- the classic NSE chain read */}
        <Card
          title="Option Chain"
          subtitle={data ? `${data.expiry_days}d expiry · ATM-centered, ±20 strikes` : undefined}
          info="Calls on the left, puts on the right, strike in the middle -- the standard NSE chain read. The highlighted row is the ATM strike."
          className="xl:col-span-2"
        >
          <div className="overflow-x-auto -m-4 p-4">
            {!data ? (
              <SkeletonTableRows rows={14} cols={9} />
            ) : (
            <table className="w-full text-xs font-mono mono-nums">
              <thead>
                <tr className="border-b border-border text-muted-foreground">
                  <th colSpan={4} className="py-1.5 text-center font-sans font-medium text-bullish">CALLS</th>
                  <th className="py-1.5"></th>
                  <th colSpan={4} className="py-1.5 text-center font-sans font-medium text-bearish">PUTS</th>
                </tr>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="py-1.5 px-1.5">OI</th>
                  <th className="py-1.5 px-1.5">LTP</th>
                  <th className="py-1.5 px-1.5">IV%</th>
                  <th className="py-1.5 px-1.5">Delta</th>
                  <th className="py-1.5 px-2 text-center">Strike</th>
                  <th className="py-1.5 px-1.5">Delta</th>
                  <th className="py-1.5 px-1.5">IV%</th>
                  <th className="py-1.5 px-1.5">LTP</th>
                  <th className="py-1.5 px-1.5">OI</th>
                </tr>
              </thead>
              <tbody>
                {strikesNearSpot.map((strike) => {
                  const { call, put } = byStrike.get(strike) || {};
                  const isAtm = strike === atmStrike;
                  return (
                    <tr
                      key={strike}
                      className={`border-b border-border/50 hover:bg-muted/40 ${isAtm ? "bg-mainBlue/10" : ""}`}
                    >
                      <td className="py-1.5 px-1.5 text-muted-foreground">{call ? call.open_interest.toLocaleString() : "--"}</td>
                      <td className="py-1.5 px-1.5 text-bullish">{call ? call.last_price.toFixed(2) : "--"}</td>
                      <td className="py-1.5 px-1.5">{call ? call.implied_volatility.toFixed(1) : "--"}</td>
                      <td className="py-1.5 px-1.5">{call ? call.delta.toFixed(2) : "--"}</td>
                      <td className="py-1.5 px-2 text-center font-sans font-medium text-foreground">{strike}</td>
                      <td className="py-1.5 px-1.5">{put ? put.delta.toFixed(2) : "--"}</td>
                      <td className="py-1.5 px-1.5">{put ? put.implied_volatility.toFixed(1) : "--"}</td>
                      <td className="py-1.5 px-1.5 text-bearish">{put ? put.last_price.toFixed(2) : "--"}</td>
                      <td className="py-1.5 px-1.5 text-muted-foreground">{put ? put.open_interest.toLocaleString() : "--"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            )}
          </div>
        </Card>

        <div className="space-y-4">
          <Card title="Market Interpretation" subtitle="Plain-language chain read" info="Turns the raw PCR, Max Pain, and IV numbers into a plain-language read of what the chain is signaling. Click 'why?' on each row for the reasoning.">
            {interp ? (
              <MarketInterpretationPanel pcr={interp.pcr} maxPain={interp.max_pain} ivSpike={interp.iv_spike} />
            ) : (
              <div className="space-y-3 py-1">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            )}
          </Card>
          <Card title="OI by Strike" subtitle="Call OI (green) vs Put OI (red)" info="Open interest per strike near spot. Tall bars mark strikes with heavy positioning -- often acting as support (put walls) or resistance (call walls).">
            {data ? <OiByStrikeChart rows={data.rows} spot={data.spot} /> : <SkeletonBlock className="h-56 w-full" />}
          </Card>
        </div>
      </div>

      {/* Full sortable chain with Greeks -- defaults to the near-ATM subset, see nearAtmStrikesForGreeks above */}
      <Card
        title="Full Chain (Greeks)"
        subtitle={showAllGreeks ? "Every strike, sortable" : `Nearest strikes to spot, sortable · ${rows.length - visibleGreeksRows.length} more hidden`}
        info="Every strike with full Greeks -- click any column header to sort. Shaded rows are in-the-money."
      >
        <div className="flex justify-end mb-2 -mt-1">
          <button
            onClick={() => setShowAllGreeks((v) => !v)}
            className="text-xs px-2.5 py-1 rounded border border-border text-muted-foreground hover:bg-muted/40 transition-colors"
          >
            {showAllGreeks ? "Show fewer (near spot only)" : `Show all ${rows.length} rows`}
          </button>
        </div>
        <div className="overflow-x-auto -m-4 p-4 pt-0">
          {!data ? (
            <SkeletonTableRows rows={10} cols={9} />
          ) : (
          <table className="w-full text-sm font-mono mono-nums">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground text-xs">
                {columns.map((c) => (
                  <th
                    key={c.key}
                    onClick={() => toggleSort(c.key)}
                    title={`Sort by ${c.label}`}
                    className="hover-glow focus-ring cursor-pointer select-none py-2 px-2 hover:text-foreground whitespace-nowrap rounded-sm"
                  >
                    {c.label} {sortKey === c.key && (sortDir === 1 ? "↑" : "↓")}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visibleGreeksRows.map((r, i) => {
                const isITM = r.option_type === "call" ? r.strike < (data?.spot || 0) : r.strike > (data?.spot || 0);
                return (
                  <tr key={i} className={`border-b border-border/50 hover:bg-muted/40 ${isITM ? "bg-muted/20" : ""}`}>
                    <td className="py-1.5 px-2">{r.strike}</td>
                    <td className="py-1.5 px-2"><Badge label={r.option_type} /></td>
                    <td className="py-1.5 px-2">{r.last_price.toFixed(2)}</td>
                    <td className="py-1.5 px-2 text-muted-foreground">{r.open_interest.toLocaleString()}</td>
                    <td className="py-1.5 px-2">{r.implied_volatility.toFixed(2)}</td>
                    <td className="py-1.5 px-2">{r.delta.toFixed(3)}</td>
                    <td className="py-1.5 px-2">{r.gamma.toFixed(4)}</td>
                    <td className="py-1.5 px-2 text-bearish">{r.theta.toFixed(2)}</td>
                    <td className="py-1.5 px-2">{r.vega.toFixed(2)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          )}
        </div>
      </Card>
    </div>
  );
}
