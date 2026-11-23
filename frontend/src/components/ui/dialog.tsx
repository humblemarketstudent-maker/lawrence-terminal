import * as Dialog from "@radix-ui/react-dialog";
import type { ReactNode } from "react";
import { cn } from "../../lib/cn.ts";

export function Modal({
  open,
  onOpenChange,
  title,
  children,
  className,
  side = false,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  children: ReactNode;
  className?: string;
  side?: boolean;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/70" />
        <Dialog.Content
          className={cn(
            "fixed z-50 flex flex-col border border-border bg-panel outline-none",
            side
              ? "inset-y-0 right-0 w-[min(440px,100%)]"
              : "left-1/2 top-1/2 max-h-[min(860px,calc(100%-32px))] w-[min(880px,calc(100%-24px))] -translate-x-1/2 -translate-y-1/2",
            className,
          )}
        >
          <div className="flex h-9 shrink-0 items-center border-b border-border px-3">
            <Dialog.Title className="font-mono text-[11px] tracking-[0.14em] text-amber">{title}</Dialog.Title>
            <Dialog.Close className="ml-auto font-mono text-[10px] text-muted hover:text-amber">ESC</Dialog.Close>
          </div>
          <div className="min-h-0 flex-1 overflow-auto">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
