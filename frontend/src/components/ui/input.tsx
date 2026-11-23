import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "../../lib/cn.ts";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input(
  { className, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      className={cn(
        "h-8 w-full border border-border bg-background px-2 font-mono text-xs text-foreground outline-none placeholder:text-dim focus:border-amber",
        className,
      )}
      {...props}
    />
  );
});
