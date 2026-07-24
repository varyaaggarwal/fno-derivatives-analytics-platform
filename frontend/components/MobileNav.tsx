"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { NAV_GROUPS } from "@/lib/nav";

/**
 * MobileNav -- Sidebar.tsx (the page navigation) is `hidden md:flex`, so on
 * any phone-width screen there was previously no way to switch pages at
 * all: no hamburger, no bottom nav, nothing. This adds a hamburger button
 * (visible only below the md breakpoint, next to TopBar's content) that
 * opens a full-height drawer with the same NAV_GROUPS Sidebar.tsx uses, so
 * the two stay in sync automatically if pages are ever added/renamed.
 */
export default function MobileNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  // Close automatically whenever the route actually changes (i.e. after a
  // link was tapped), rather than requiring a second tap on the backdrop.
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <div className="md:hidden">
      <button
        onClick={() => setOpen(true)}
        aria-label="Open navigation menu"
        className="hover-glow focus-ring flex items-center justify-center w-8 h-8 rounded-md text-muted-foreground hover:text-foreground"
      >
        <Menu size={20} />
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex">
          {/* Backdrop -- tapping it closes the drawer, same as tapping a link does */}
          <div className="fixed inset-0 bg-black/60" onClick={() => setOpen(false)} />

          <aside className="relative w-64 max-w-[80vw] h-full bg-sidebar border-r border-sidebar-border flex flex-col">
            <div className="h-14 flex items-center justify-between gap-2.5 px-4 border-b border-sidebar-border">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-7 h-7 rounded-lg bg-mainBlue flex items-center justify-center font-sans font-bold text-sm shrink-0 text-white">Δ</div>
                <div className="font-sans font-medium text-sm tracking-tight leading-tight truncate text-sidebar-foreground">F&O Analytics</div>
              </div>
              <button
                onClick={() => setOpen(false)}
                aria-label="Close navigation menu"
                className="hover-glow focus-ring flex items-center justify-center w-8 h-8 rounded-md text-muted-foreground hover:text-foreground shrink-0"
              >
                <X size={18} />
              </button>
            </div>

            <nav className="flex-1 px-2 py-3 space-y-4 overflow-y-auto">
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
                          className={`hover-glow focus-ring flex items-center gap-2.5 px-3 py-2.5 rounded-pill text-sm transition-colors border border-transparent w-full ${
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
          </aside>
        </div>
      )}
    </div>
  );
}
