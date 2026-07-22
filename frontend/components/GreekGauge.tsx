"use client";
import InfoTooltip from "@/components/InfoTooltip";

/**
 * Signature visual for the platform: a semicircular gauge per Greek, deliberately
 * echoing the "Option Greeks: Your Risk Dashboard" gauge-icon language from the
 * FnO induction deck (Δ Γ Θ ν ρ), rather than a generic KPI tile.
 *
 * Palette wired to the Zero (Mail-0) template's CSS variables.
 */
export default function GreekGauge({
  symbol,
  label,
  value,
  min,
  max,
  color,
  decimals = 2,
  info,
}: {
  symbol: string;
  label: string;
  value: number;
  min: number;
  max: number;
  color: string;
  decimals?: number;
  info?: string;
}) {
  const format = (v: number) => v.toFixed(decimals);
  const clamped = Math.max(min, Math.min(max, value));
  const pct = (clamped - min) / (max - min);
  const radius = 40;
  const cx = 50, cy = 50;
  const startAngle = -180, endAngle = 0; // degrees, semicircle path along the top
  const polarToCartesian = (angleDeg: number) => {
    const rad = (angleDeg * Math.PI) / 180;
    return { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) };
  };
  const arcStart = polarToCartesian(startAngle);
  const arcEnd = polarToCartesian(endAngle);
  const needleAngleRad = ((-180 + pct * 180) * Math.PI) / 180;
  const needleLen = radius - 6;
  const needleX = cx + needleLen * Math.cos(needleAngleRad);
  const needleY = cy + needleLen * Math.sin(needleAngleRad);

  return (
    <div className="hover-glow flex flex-col items-center rounded-card border border-transparent p-1.5">
      <svg viewBox="0 0 100 62" className="w-full max-w-[140px]">
        <path
          d={`M ${arcStart.x} ${arcStart.y} A ${radius} ${radius} 0 0 1 ${arcEnd.x} ${arcEnd.y}`}
          fill="none"
          stroke="hsl(var(--border))"
          strokeWidth="8"
          strokeLinecap="round"
        />
        <path
          d={`M ${arcStart.x} ${arcStart.y} A ${radius} ${radius} 0 0 1 ${cx + radius * Math.cos((startAngle + pct * 180) * Math.PI / 180)} ${cy + radius * Math.sin((startAngle + pct * 180) * Math.PI / 180)}`}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
        />
        <line x1={cx} y1={cy} x2={needleX} y2={needleY} stroke="hsl(var(--foreground))" strokeWidth="2" strokeLinecap="round" />
        <circle cx={cx} cy={cy} r="3" fill="hsl(var(--foreground))" />
        <text x={cx} y={cy - 12} textAnchor="middle" className="font-sans" fontSize="14" fill={color}>
          {symbol}
        </text>
      </svg>
      <div className="font-mono mono-nums text-sm text-foreground -mt-1">{format(value)}</div>
      {info ? (
        <InfoTooltip text={info}>
          <div className="text-[11px] text-muted-foreground cursor-help underline decoration-dotted underline-offset-2">{label}</div>
        </InfoTooltip>
      ) : (
        <div className="text-[11px] text-muted-foreground">{label}</div>
      )}
    </div>
  );
}
