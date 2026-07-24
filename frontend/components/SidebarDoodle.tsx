/**
 * SidebarDoodle -- a quiet, hand-sketched decoration for the sidebar's nav
 * area, filling the empty space below the page links on any screen taller
 * than the nav list itself.
 *
 * Drawn from this app's own vocabulary rather than a generic dot-grid or
 * abstract squiggle: a candlestick pair, an IV smile curve (the same
 * concept as the actual Vol Surface page), a call-option payoff
 * "hockey stick", and the four Greek letters this whole app is built
 * around. Single thin stroke, very low opacity, so it reads as texture
 * in the negative space rather than competing with the nav links sitting
 * in front of it.
 */
export default function SidebarDoodle() {
  return (
    <svg
      viewBox="0 0 240 520"
      preserveAspectRatio="xMidYMin slice"
      className="absolute inset-0 w-full h-full pointer-events-none select-none"
      aria-hidden="true"
    >
      <g
        fill="none"
        stroke="hsl(var(--sidebar-foreground))"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.08"
      >
        {/* two candlesticks, top-left -- a nod to the option chain's OI/LTP ticks */}
        <line x1="34" y1="46" x2="34" y2="88" />
        <rect x="27" y="58" width="14" height="20" rx="1.5" />
        <line x1="60" y1="36" x2="60" y2="80" />
        <rect x="53" y="44" width="14" height="26" rx="1.5" />

        {/* IV smile curve -- same shape the Vol Surface page plots */}
        <path d="M 30 170 Q 80 120 120 168 T 210 172" />
        <circle cx="30" cy="170" r="2.4" fill="hsl(var(--sidebar-foreground))" stroke="none" />
        <circle cx="120" cy="168" r="2.4" fill="hsl(var(--sidebar-foreground))" stroke="none" />
        <circle cx="210" cy="172" r="2.4" fill="hsl(var(--sidebar-foreground))" stroke="none" />

        {/* long call payoff -- flat premium loss, then the diagonal past breakeven */}
        <path d="M 24 260 L 108 260 L 200 210" />
        <line x1="108" y1="252" x2="108" y2="268" strokeWidth="1" opacity="0.7" />

        {/* Greek glyphs the whole engine is built around, loosely scattered like margin notes */}
        <text x="150" y="330" fontSize="26" fontFamily="Georgia, serif" fontStyle="italic" stroke="none" fill="hsl(var(--sidebar-foreground))">Δ</text>
        <text x="46" y="380" fontSize="20" fontFamily="Georgia, serif" fontStyle="italic" stroke="none" fill="hsl(var(--sidebar-foreground))">Γ</text>
        <text x="160" y="420" fontSize="22" fontFamily="Georgia, serif" fontStyle="italic" stroke="none" fill="hsl(var(--sidebar-foreground))">Θ</text>
        <text x="70" y="460" fontSize="18" fontFamily="Georgia, serif" fontStyle="italic" stroke="none" fill="hsl(var(--sidebar-foreground))">ν</text>

        {/* a faint SuperTrend-style stepped line near the bottom -- DOS strategy's own signal */}
        <path d="M 20 495 L 60 495 L 60 480 L 110 480 L 110 500 L 170 500 L 170 470 L 214 470" />
      </g>
    </svg>
  );
}
