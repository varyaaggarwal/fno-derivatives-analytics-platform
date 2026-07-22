"use client";
import { useState } from "react";
import Badge from "@/components/Badge";
import { InterpretationCard } from "@/lib/api";

function Row({ label, card }: { label: string; card: InterpretationCard }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="py-3 border-b border-border/60 last:border-b-0">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-muted-foreground">{label}</span>
          {card.sentiment && <Badge label={card.sentiment} />}
        </div>
        <span className="font-mono mono-nums text-sm">
          {card.value === null ? "--" : card.value}
          {label === "IV Spike" && card.value !== null ? "%" : ""}
        </span>
      </div>
      <button
        onClick={() => setOpen((o) => !o)}
        className="focus-ring text-[11px] text-mainBlue/80 hover:text-mainBlue mt-1"
      >
        {open ? "hide" : "why?"}
      </button>
      {open && <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">{card.note}</p>}
    </div>
  );
}

export default function MarketInterpretationPanel({
  pcr,
  maxPain,
  ivSpike,
}: {
  pcr: InterpretationCard;
  maxPain: InterpretationCard;
  ivSpike: InterpretationCard;
}) {
  return (
    <div>
      <Row label="Put-Call Ratio" card={pcr} />
      <Row label="Max Pain" card={maxPain} />
      <Row label="IV Spike" card={ivSpike} />
    </div>
  );
}
