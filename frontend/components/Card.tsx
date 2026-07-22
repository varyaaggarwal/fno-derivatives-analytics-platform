import { Info } from "lucide-react";
import InfoTooltip from "@/components/InfoTooltip";

export default function Card({
  title,
  subtitle,
  info,
  children,
  className = "",
}: {
  title?: string;
  subtitle?: string;
  info?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`hover-glow bg-card border border-border rounded-card p-4 ${className}`}>
      {title && (
        <div className="mb-3 flex items-start gap-1.5">
          <div>
            <h3 className="font-sans font-medium text-sm text-foreground flex items-center gap-1.5">
              {title}
              {info && (
                <InfoTooltip text={info}>
                  <Info size={12} className="text-muted-foreground/70 cursor-help" />
                </InfoTooltip>
              )}
            </h3>
            {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
          </div>
        </div>
      )}
      {children}
    </div>
  );
}
