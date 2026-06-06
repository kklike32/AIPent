import type { ReactNode } from "react";
import { cn } from "../../lib/cn";

type PillTone = "base" | "muted" | "accent" | "outline";
type PillSize = "sm" | "xs";

type PillProps = {
    className?: string;
    tone?: PillTone;
    size?: PillSize;
    uppercase?: boolean;
    children: ReactNode;
};

const toneClasses: Record<PillTone, string> = {
    base: "bg-white/90 text-muted-foreground ring-1 ring-border",
    muted: "border border-border bg-muted/65 text-muted-foreground",
    accent: "bg-accent text-accent-foreground ring-1 ring-border/70",
    outline: "border border-border/75 bg-white/80 text-muted-foreground",
};

const sizeClasses: Record<PillSize, string> = {
    sm: "px-3 py-1 text-[11px]",
    xs: "px-2 py-1 text-[10px]",
};

export function Pill({ className, tone = "base", size = "sm", uppercase = true, children }: PillProps) {
    return (
        <span
            className={cn(
                "inline-flex items-center rounded-full font-semibold",
                uppercase && "uppercase tracking-[0.22em]",
                toneClasses[tone],
                sizeClasses[size],
                className,
            )}
        >
            {children}
        </span>
    );
}
