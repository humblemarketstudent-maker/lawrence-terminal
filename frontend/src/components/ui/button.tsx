import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/cn.ts";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-1 whitespace-nowrap font-mono uppercase tracking-wide transition-colors disabled:pointer-events-none disabled:opacity-40",
  {
    variants: {
      variant: {
        default: "bg-amber text-background hover:bg-amber/90",
        outline: "border border-border bg-transparent text-foreground hover:border-amber hover:text-amber",
        ghost: "text-muted hover:bg-white/5 hover:text-foreground",
        amber: "border border-amber/50 text-amber hover:bg-amber/10",
      },
      size: {
        sm: "h-6 px-2 text-[10px]",
        md: "h-8 px-3 text-[11px]",
      },
    },
    defaultVariants: { variant: "outline", size: "sm" },
  },
);

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant, size, asChild = false, ...props },
  ref,
) {
  const Comp = asChild ? Slot : "button";
  return <Comp ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />;
});
