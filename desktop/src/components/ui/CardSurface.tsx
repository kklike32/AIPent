import type { HTMLAttributes } from "react";
import { cn } from "../../lib/cn";

type CardTone = "base" | "muted" | "accent" | "primary" | "danger";

type CardSurfaceProps = HTMLAttributes<HTMLDivElement> & {
    tone?: CardTone;
    interactive?: boolean;
};

const toneClasses: Record<CardTone, string> = {
    base: "border border-border/70 bg-white/62 text-foreground",
    muted: "border border-border/70 bg-muted/72 text-accent-foreground",
    accent: "border border-border/70 bg-accent/45 text-accent-foreground",
    primary: "border border-primary/40 bg-primary text-primary-foreground",
    danger: "border border-destructive/25 bg-[#FFF3EF] text-[#6F2F28]",
};

export function CardSurface({
    className,
    tone = "base",
    interactive = false,
    ...props
}: CardSurfaceProps) {
    return (
        <div
            className={cn(
                "rounded-[1.6rem]",
                toneClasses[tone],
                interactive && "transition-all duration-300 hover:-translate-y-1 hover:shadow-soft",
                className,
            )}
            {...props}
        />
    );
}
