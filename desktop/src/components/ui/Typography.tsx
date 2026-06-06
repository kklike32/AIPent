import type { ReactNode } from "react";
import { cn } from "../../lib/cn";

type TextProps = {
    className?: string;
    children: ReactNode;
};

export function SectionEyebrow({ className, children }: TextProps) {
    return (
        <p className={cn("text-[11px] font-semibold uppercase tracking-[0.28em] text-muted-foreground", className)}>
            {children}
        </p>
    );
}

export function SectionTitle({ className, children }: TextProps) {
    return <h2 className={cn("mt-2 text-[24px] font-semibold text-foreground", className)}>{children}</h2>;
}
