"use client";
import { useEffect, useMemo, useState } from "react";
import { api, ChainResponse, ChainRow } from "@/lib/api";
import Card from "@/components/Card";
import Badge from "@/components/Badge";

type SortKey = keyof ChainRow;

export default function ChainPage() {
  const [data, setData] = useState<ChainResponse | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("strike");
  const [sortDir, setSortDir] = useState<1 | -1>(1);

  useEffect(() => {
    api.chain().then(setData).catch(console.error);
  }, []);

  const rows = useMemo(() => {
    if (!data) return [];
    return [...data.rows].sort((a, b) => {
      const av = a[sortKey], bv = b[sortKey];
      if (typeof av === "string") return sortDir * String(av).localeCompare(String(bv));
      return sortDir * ((av as number) - (bv as number));
    });
  }, [data, sortKey, sortDir]);

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
    <div className="space-y-4 max-w-6xl">
      <div>
        <h1 className="font-display text-xl font-medium">Option Chain</h1>
        <p className="text-sm text-muted mt-1">
          {data ? `Spot ${data.spot.toLocaleString()} · Expiry ${data.expiry_days}d · ${data.rows.length} rows` : "Loading..."}
        </p>
      </div>
      <Card>
        <div className="overflow-x-auto -m-4 p-4">
          <table className="w-full text-sm font-mono mono-nums">
            <thead>
              <tr className="border-b border-border text-left text-muted text-xs">
                {columns.map((c) => (
                  <th
                    key={c.key}
                    onClick={() => toggleSort(c.key)}
                    className="focus-ring cursor-pointer select-none py-2 px-2 hover:text-text whitespace-nowrap"
                  >
                    {c.label} {sortKey === c.key && (sortDir === 1 ? "↑" : "↓")}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => {
                const isITM = r.option_type === "call" ? r.strike < (data?.spot || 0) : r.strike > (data?.spot || 0);
                return (
                  <tr key={i} className={`border-b border-border/50 hover:bg-surface2/40 ${isITM ? "bg-surface2/20" : ""}`}>
                    <td className="py-1.5 px-2">{r.strike}</td>
                    <td className="py-1.5 px-2"><Badge label={r.option_type} /></td>
                    <td className="py-1.5 px-2">{r.last_price.toFixed(2)}</td>
                    <td className="py-1.5 px-2 text-muted">{r.open_interest.toLocaleString()}</td>
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
        </div>
      </Card>
    </div>
  );
}
