"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Command } from "lucide-react";
import { NAV_ITEMS } from "@/lib/nav";

export default function CommandTrigger() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIdx, setActiveIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const results = NAV_ITEMS.filter((item) =>
    item.label.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      const typing = target.tagName === "INPUT" || target.tagName === "TEXTAREA";
      if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || (e.key === "/" && !typing)) {
        e.preventDefault();
        setOpen(true);
      }
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    if (open) {
      setQuery("");
      setActiveIdx(0);
      setTimeout(() => inputRef.current?.focus(), 10);
    }
  }, [open]);

  function go(idx: number) {
    const item = results[idx];
    if (item) {
      router.push(item.href);
      setOpen(false);
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="focus-ring w-full flex items-center justify-between gap-2 px-3 py-2 rounded-pill bg-surface3 border border-border text-xs text-muted hover:text-text hover:border-accent/50 transition-colors"
      >
        <span className="flex items-center gap-2">
          <Command size={13} strokeWidth={2} />
          Jump to page
        </span>
        <kbd className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-surface2 border border-border text-muted">/</kbd>
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] bg-black/60 backdrop-blur-sm"
          onClick={() => setOpen(false)}
        >
          <div
            className="w-full max-w-md mx-4 rounded-card border border-border bg-surface2 shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
              <Command size={15} className="text-muted" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => { setQuery(e.target.value); setActiveIdx(0); }}
                onKeyDown={(e) => {
                  if (e.key === "ArrowDown") { e.preventDefault(); setActiveIdx((i) => Math.min(i + 1, results.length - 1)); }
                  if (e.key === "ArrowUp") { e.preventDefault(); setActiveIdx((i) => Math.max(i - 1, 0)); }
                  if (e.key === "Enter") go(activeIdx);
                }}
                placeholder="Search pages…"
                className="flex-1 bg-transparent outline-none text-sm text-text placeholder:text-muted"
              />
            </div>
            <div className="max-h-72 overflow-y-auto p-1.5">
              {results.length === 0 && (
                <div className="px-3 py-6 text-center text-xs text-muted">No pages match "{query}"</div>
              )}
              {results.map(({ href, label, icon: Icon }, idx) => (
                <button
                  key={href}
                  onClick={() => go(idx)}
                  onMouseEnter={() => setActiveIdx(idx)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-pill text-sm text-left transition-colors ${
                    idx === activeIdx ? "bg-surface3 text-text" : "text-muted"
                  }`}
                >
                  <Icon size={15} strokeWidth={2} className={idx === activeIdx ? "text-accent" : ""} />
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
