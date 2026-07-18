"use client";

/**
 * Signature visual for the platform: a semicircular gauge per Greek, deliberately
 * echoing the "Option Greeks: Your Risk Dashboard" gauge-icon language from the
 * FnO induction deck (Δ Γ Θ ν ρ), rather than a generic KPI tile.
 */
export default function GreekGauge({
  symbol,
  label,
  value,
  min,
  max,
  color,
  decimals = 2,
}: {
  symbol: string;
  label: string;
  value: number;
  min: number;
  max: number;
  color: string;
  decimals?: number;
}) {
  const format = (v: number) => v.toFixed(decimals);
  const clamped = Math.max(min, Math.min(max, value));
  const pct = (clamped - min) / (max - min);
  const angle = -90 + pct * 180; // semicircle: -90deg (min) to +90deg (max)
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
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 100 62" className="w-full max-w-[140px]">
        <path
          d={`M ${arcStart.x} ${arcStart.y} A ${radius} ${radius} 0 0 1 ${arcEnd.x} ${arcEnd.y}`}
          fill="none"
          stroke="#1F2733"
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
        <line x1={cx} y1={cy} x2={needleX} y2={needleY} stroke="#E6EDF3" strokeWidth="2" strokeLinecap="round" />
        <circle cx={cx} cy={cy} r="3" fill="#E6EDF3" />
        <text x={cx} y={cy - 12} textAnchor="middle" className="font-display" fontSize="14" fill={color}>
          {symbol}
        </text>
      </svg>
      <div className="font-mono mono-nums text-sm text-text -mt-1">{format(value)}</div>
      <div className="text-[11px] text-muted">{label}</div>
    </div>
  );
}
