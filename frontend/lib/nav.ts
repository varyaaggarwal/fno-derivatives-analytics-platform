import { LayoutGrid, Rows3, Layers3, PieChart, Activity } from "lucide-react";

export const NAV_GROUPS = [
  {
    label: "Markets",
    items: [
      { href: "/", label: "Overview", icon: LayoutGrid },
      { href: "/chain", label: "Option Chain", icon: Rows3 },
      { href: "/surface", label: "Vol Surface", icon: Layers3 },
    ],
  },
  {
    label: "Strategy",
    items: [
      { href: "/pnl", label: "P&L Decomposer", icon: PieChart },
      { href: "/dos", label: "DOS Strategy", icon: Activity },
    ],
  },
];

export const NAV_ITEMS = NAV_GROUPS.flatMap((g) => g.items);
