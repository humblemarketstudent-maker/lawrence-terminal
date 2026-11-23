import type { Quote } from "../types.ts";

export function formatCompact(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(value)) return "—";
  const sign = value < 0 ? "-" : "";
  const abs = Math.abs(value);
  if (abs >= 1e12) return `${sign}${(abs / 1e12).toFixed(digits)}T`;
  if (abs >= 1e9) return `${sign}${(abs / 1e9).toFixed(digits)}B`;
  if (abs >= 1e6) return `${sign}${(abs / 1e6).toFixed(digits)}M`;
  if (abs >= 1e3) return `${sign}${(abs / 1e3).toFixed(digits)}K`;
  return `${sign}${abs.toFixed(digits)}`;
}

export function formatPrice(value: number | null | undefined, assetClass?: string): string {
  if (value == null || Number.isNaN(value)) return "—";
  if (assetClass === "rate") return `${value.toFixed(2)}%`;
  if (assetClass === "fx") return value.toFixed(value >= 20 ? 3 : 4);
  if (assetClass === "crypto") {
    return value.toLocaleString("en-US", { maximumFractionDigits: value >= 1000 ? 0 : 2 });
  }
  if (Math.abs(value) >= 10000) return value.toLocaleString("en-US", { maximumFractionDigits: 2 });
  return value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function formatPct(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}%`;
}

export function formatSigned(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}`;
}

export function toneOf(value: number | null | undefined): "up" | "down" | "flat" {
  if (value == null || value === 0) return "flat";
  return value > 0 ? "up" : "down";
}

export function toneClass(tone: "up" | "down" | "flat"): string {
  if (tone === "up") return "text-up";
  if (tone === "down") return "text-down";
  return "text-muted";
}

export function formatMove(quote: Pick<Quote, "change" | "changePct" | "assetClass">): { net: string; pct: string; tone: "up" | "down" | "flat" } {
  const tone = toneOf(quote.change);
  if (quote.assetClass === "rate") {
    const bp = quote.change == null ? null : quote.change * 100;
    return { net: `${formatSigned(bp, 1)}bp`, pct: formatPct(quote.changePct), tone };
  }
  const digits = quote.assetClass === "fx" ? 4 : 2;
  return { net: formatSigned(quote.change, digits), pct: formatPct(quote.changePct), tone };
}

export function formatStatement(value: number | null, unit: string): string {
  if (value == null || Number.isNaN(value)) return "—";
  if (unit === "percent") return `${value.toFixed(1)}%`;
  if (unit === "ratio") return `${value.toFixed(2)}x`;
  if (unit === "perShare") return value.toFixed(2);
  const abs = Math.abs(value);
  const text = abs >= 100 ? abs.toLocaleString("en-US", { maximumFractionDigits: 0 }) : abs.toFixed(1);
  return value < 0 ? `(${text})` : text;
}

export function yoy(values: Array<number | null>): Array<number | null> {
  return values.map((value, index) => {
    const prior = index > 0 ? values[index - 1] : null;
    if (value == null || prior == null || prior === 0) return null;
    return ((value - prior) / Math.abs(prior)) * 100;
  });
}

export function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const minutes = Math.round((Date.now() - then) / 60000);
  if (Math.abs(minutes) < 1) return "now";
  if (Math.abs(minutes) < 60) return `${minutes}m`;
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 36) return `${hours}h`;
  const days = Math.round(hours / 24);
  return `${days}d`;
}

export function stamp(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const utc = date.toISOString().replace("T", " ").slice(0, 16) + " UTC";
  const local = date.toLocaleString(undefined, { hour12: false, month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
  return `${relativeTime(iso)} · ${utc} · ${local}`;
}

export function rangePosition(price: number | null, low: number | null, high: number | null): number | null {
  if (price == null || low == null || high == null || high === low) return null;
  return Math.min(1, Math.max(0, (price - low) / (high - low)));
}

export function formatMultiple(value: number | null, unit: string): string {
  if (value == null || Number.isNaN(value)) return "—";
  if (unit === "%") return `${value.toFixed(1)}%`;
  if (unit === "x") return `${value.toFixed(2)}x`;
  return value.toFixed(2);
}
