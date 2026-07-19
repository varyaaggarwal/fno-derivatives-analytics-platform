"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { RefreshCw } from "lucide-react";
import { NAV_GROUPS } from "@/lib/nav";
import CommandTrigger from "@/components/CommandPalette";

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
      <div className="h-14 flex items-center gap-2.5 px-4 border-b border-sidebar-border">
        <div className="w-7 h-7 rounded-lg bg-mainBlue flex items-center justify-center font-sans font-bold text-sm shrink-0 text-white">Δ</div>
        <div className="min-w-0">
          <div className="font-sans font-medium text-sm tracking-tight leading-tight truncate text-sidebar-foreground">F&O Analytics</div>
          <div className="text-[11px] text-muted-foreground leading-tight">AlgoLabs · Assignment 2</div>
        </div>
      </div>

      <div className="p-3">
        <CommandTrigger />
      </div>

      <nav className="flex-1 px-2 space-y-4 overflow-y-auto">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            <div className="px-3 pb-1.5 text-[11px] font-medium tracking-wide uppercase text-muted-foreground/70">
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
                      active
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-muted-foreground hover:text-sidebar-accent-foreground hover:bg-sidebar-accent/60"
                    }`}
                  >
                    <Icon size={16} strokeWidth={2} className={active ? "text-sidebar-primary" : ""} />
                    {label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="px-4 py-3 border-t border-sidebar-border flex items-center gap-2 text-xs text-muted-foreground">
        <RefreshCw size={12} />
        Mock data mode
      </div>
    </aside>
  );
}
