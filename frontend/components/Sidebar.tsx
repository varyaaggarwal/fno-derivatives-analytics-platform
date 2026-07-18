"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { RefreshCw } from "lucide-react";
import { NAV_GROUPS } from "@/lib/nav";
import CommandTrigger from "@/components/CommandPalette";

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-border bg-surface">
      <div className="h-14 flex items-center gap-2.5 px-4 border-b border-border">
        <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center font-display font-bold text-sm shrink-0">Δ</div>
        <div className="min-w-0">
          <div className="font-display font-medium text-sm tracking-tight leading-tight truncate">F&O Analytics</div>
          <div className="text-[11px] text-muted leading-tight">AlgoLabs · Assignment 2</div>
        </div>
      </div>

      <div className="p-3">
        <CommandTrigger />
      </div>

      <nav className="flex-1 px-2 space-y-4 overflow-y-auto">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            <div className="px-3 pb-1.5 text-[11px] font-medium tracking-wide uppercase text-muted/70">
              {group.label}
            </div>
            <div className="space-y-0.5">
              {group.items.map(({ href, label, icon: Icon }) => {
                const active = pathname === href;
                return (
                  <Link
                    key={href}
                    href={href}
                    className={`focus-ring flex items-center gap-2.5 px-3 py-2 rounded-pill text-sm transition-colors ${
                      active ? "bg-surface3 text-text" : "text-muted hover:text-text hover:bg-surface2"
                    }`}
                  >
                    <Icon size={16} strokeWidth={2} className={active ? "text-accent" : ""} />
                    {label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="px-4 py-3 border-t border-border flex items-center gap-2 text-xs text-muted">
        <RefreshCw size={12} />
        Mock data mode
      </div>
    </aside>
  );
}
