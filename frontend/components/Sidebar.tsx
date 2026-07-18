"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutGrid, Rows3, Layers3, PieChart, Activity } from "lucide-react";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutGrid },
  { href: "/chain", label: "Option Chain", icon: Rows3 },
  { href: "/surface", label: "Vol Surface", icon: Layers3 },
  { href: "/pnl", label: "P&L Decomposer", icon: PieChart },
  { href: "/dos", label: "DOS Strategy", icon: Activity },
];

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden md:flex w-56 shrink-0 flex-col border-r border-border bg-surface">
      <div className="h-14 flex items-center gap-2 px-4 border-b border-border">
        <div className="w-6 h-6 rounded bg-accent flex items-center justify-center font-display font-bold text-xs">Δ</div>
        <span className="font-display font-medium text-sm tracking-tight">F&O Analytics</span>
      </div>
      <nav className="flex-1 py-3 px-2 space-y-0.5">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`focus-ring flex items-center gap-2.5 px-3 py-2 rounded-card text-sm transition-colors ${
                active ? "bg-surface2 text-text" : "text-muted hover:text-text hover:bg-surface2/60"
              }`}
            >
              <Icon size={16} strokeWidth={2} className={active ? "text-accent" : ""} />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="px-4 py-3 border-t border-border text-xs text-muted">
        AlgoLabs Assignment 2<br />Mock data mode
      </div>
    </aside>
  );
}
