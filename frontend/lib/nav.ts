import { LayoutGrid, Rows3, Layers3, PieChart, Activity } from "lucide-react";

export const NAV_GROUPS = [
  {
    label: "Markets",
    items: [
      { href: "/", label: "Overview", icon: LayoutGrid, description: "ATM Greeks, PCR/Max Pain/IV Spike interpretation, and the DOS backtest summary at a glance." },
      { href: "/chain", label: "Option Chain", icon: Rows3, description: "Live call/put chain with OI, LTP, IV, and Greeks per strike, plus market interpretation cards." },
      { href: "/surface", label: "Vol Surface", icon: Layers3, description: "Implied volatility across strikes and expiries as a 3D surface, IV smile, and a colored grid." },
    ],
  },
  {
    label: "Strategy",
    items: [
      { href: "/pnl", label: "P&L Decomposer", icon: PieChart, description: "Breaks a position's P&L down into Delta, Gamma, Theta, and Vega contributions." },
      { href: "/dos", label: "DOS Strategy", icon: Activity, description: "Direction of SuperTrend signal panel, SL monitor, and historical backtest for Bank Nifty weekly expiries." },
    ],
  },
];

export const NAV_ITEMS = NAV_GROUPS.flatMap((g) => g.items);
