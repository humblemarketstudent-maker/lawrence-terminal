import * as Tabs from "@radix-ui/react-tabs";
import type { ReactNode } from "react";
import { cn } from "../../lib/cn.ts";

export function TabList({ children }: { children: ReactNode }) {
  return <Tabs.List className="flex h-7 shrink-0 items-end gap-1 border-b border-border px-2">{children}</Tabs.List>;
}

export function TabTrigger({ value, children }: { value: string; children: ReactNode }) {
  return (
    <Tabs.Trigger
      value={value}
      className={cn(
        "border-b-2 border-transparent px-2 py-1 font-mono text-[10px] uppercase tracking-wide text-muted",
        "data-[state=active]:border-amber data-[state=active]:text-amber",
      )}
    >
      {children}
    </Tabs.Trigger>
  );
}

export const TabsRoot = Tabs.Root;
export const TabContent = Tabs.Content;
