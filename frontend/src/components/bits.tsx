import { useEffect, useRef, useState, type ReactNode } from "react";
import { formatPrice, rangePosition, relativeTime, stamp, toneClass, toneOf } from "../lib/format.ts";
import type { Meta } from "../types.ts";

export function PanelFrame({
  code,
  title,
  extra,
  right,
  children,
}: {
  code?: string;
  title: string;
  extra?: ReactNode;
  right?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="flex h-full min-h-0 flex-col bg-panel">
      <header className="flex h-7 shrink-0 items-center gap-2 border-b border-border px-2">
        {code ? <span className="text-[11px] text-amber">&lt;{code}&gt;</span> : null}
        <span className="truncate text-[10px] uppercase tracking-[0.14em] text-muted">{title}</span>
        {extra}
        <div className="ml-auto flex items-center gap-2">{right}</div>
      </header>
      <div className="relative min-h-0 flex-1 overflow-auto">{children}</div>
    </section>
  );
}

export function SourcePill({ meta }: { meta?: Meta | null }) {
  if (!meta) return null;
  const label = meta.stale ? "STALE" : meta.source === "live" ? "LIVE" : "FIXTURE";
  const color = label === "LIVE" ? "text-up" : "text-amber";
  return (
    <span className={`font-mono text-[10px] ${color}`} title={stamp(meta.asOf)}>
      {label} {relativeTime(meta.asOf)}
    </span>
  );
}

export function Sparkline({ values, up }: { values: number[]; up: boolean }) {
  if (values.length < 2) return <span className="inline-block h-5 w-16" />;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const width = 68;
  const height = 20;
  const points = values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * width;
      const y = height - ((value - min) / span) * (height - 2) - 1;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg width={width} height={height} className="shrink-0" aria-hidden>
      <polyline fill="none" stroke={up ? "#00C853" : "#FF3D00"} strokeWidth="1.2" points={points} />
    </svg>
  );
}

export function RangeTrack({
  low,
  high,
  price,
  label,
}: {
  low: number | null;
  high: number | null;
  price: number | null;
  label: string;
}) {
  const pos = rangePosition(price, low, high);
  return (
    <div className="flex items-center gap-1" title={`${label} ${formatPrice(low)} – ${formatPrice(high)}`}>
      <span className="w-4 text-[9px] text-dim">{label}</span>
      <div className="relative h-1 flex-1 bg-border">
        {pos != null ? <span className="absolute top-[-2px] h-2 w-1 bg-amber" style={{ left: `calc(${pos * 100}% - 2px)` }} /> : null}
      </div>
    </div>
  );
}

export function useFlash(value: number | null | undefined): "" | "flash-up" | "flash-down" {
  const previous = useRef(value);
  const [flash, setFlash] = useState<"" | "flash-up" | "flash-down">("");
  useEffect(() => {
    const prior = previous.current;
    previous.current = value;
    if (prior == null || value == null || prior === value) return;
    setFlash(value > prior ? "flash-up" : "flash-down");
    const timer = window.setTimeout(() => setFlash(""), 700);
    return () => window.clearTimeout(timer);
  }, [value]);
  return flash;
}

export function Signed({ value, text }: { value: number | null | undefined; text: string }) {
  return <span className={toneClass(toneOf(value))}>{text}</span>;
}

export function EmptyNote({ children }: { children: ReactNode }) {
  return <div className="px-3 py-6 text-[12px] leading-relaxed text-muted">{children}</div>;
}
