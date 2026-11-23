import { useTerminal } from "../context/TerminalContext.tsx";
import { formatPct, formatPrice, formatSigned, toneClass, toneOf } from "../lib/format.ts";
import type { MacroPoint } from "../types.ts";
import { PanelFrame, SourcePill, Sparkline } from "./bits.tsx";

function Tile({ point, onPick }: { point: MacroPoint; onPick: (symbol: string) => void }) {
  const tone = toneOf(point.changePct ?? point.changeBp);
  const move = point.group === "rate" ? formatSigned(point.changeBp, 1) + "bp" : formatPct(point.changePct);
  const value = point.group === "rate" ? `${formatPrice(point.value, "rate")}` : formatPrice(point.value, point.group === "fx" ? "fx" : point.group === "crypto" ? "crypto" : "equity");
  return (
    <button
      type="button"
      onClick={() => point.symbol && onPick(point.symbol)}
      className="flex flex-col border border-border bg-background/40 p-2 text-left hover:border-amber/60"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] uppercase tracking-wide text-muted">{point.name}</span>
        {point.sample ? <span className="text-[9px] text-amber">SMP</span> : null}
      </div>
      <div className="mt-1 text-[16px]">{value}</div>
      <div className="mt-1 flex items-center justify-between">
        <span className={toneClass(tone)}>{move}</span>
        <Sparkline values={point.spark} up={(point.changePct ?? point.changeBp ?? 0) >= 0} />
      </div>
    </button>
  );
}

export function WeiPanel() {
  const { wei, weiMeta, selectTicker } = useTerminal();
  const points = wei?.points ?? [];
  const groups = [
    ["Equity", points.filter((point) => point.group === "equity")],
    ["Rates", points.filter((point) => point.group === "rate")],
    ["FX / commodities / crypto", points.filter((point) => point.group !== "equity" && point.group !== "rate")],
  ] as const;
  const curve = wei?.curve ?? [];
  const max = Math.max(...curve.map((point) => point.value ?? 0), 1);
  return (
    <PanelFrame code="WEI" title="World equity indices & macro" right={<SourcePill meta={weiMeta} />}>
      <div className="space-y-4 p-3">
        {groups.map(([label, rows]) => (
          <section key={label}>
            <div className="mb-2 text-[10px] uppercase tracking-[0.16em] text-dim">{label}</div>
            <div className="grid grid-cols-2 gap-2 xl:grid-cols-4">
              {rows.map((point) => (
                <Tile key={point.id} point={point} onPick={selectTicker} />
              ))}
            </div>
          </section>
        ))}
        <section className="border border-border p-3">
          <div className="flex items-baseline justify-between">
            <div className="text-[10px] uppercase tracking-[0.16em] text-dim">US Treasury curve</div>
            <div className="text-[12px]">
              2s10s {wei?.spread2s10s == null ? "—" : `${wei.spread2s10s.toFixed(2)}%`}{" "}
              <span className={toneClass(toneOf(wei?.spreadChangeBp))}>{wei?.spreadChangeBp == null ? "" : `${formatSigned(wei.spreadChangeBp, 1)}bp`}</span>
            </div>
          </div>
          <svg viewBox="0 0 320 90" className="mt-2 h-24 w-full">
            <polyline
              fill="none"
              stroke="#FF9900"
              strokeWidth="2"
              points={curve
                .map((point, index) => {
                  const x = curve.length <= 1 ? 10 : (index / (curve.length - 1)) * 300 + 10;
                  const y = 80 - ((point.value ?? 0) / max) * 70;
                  return `${x},${y}`;
                })
                .join(" ")}
            />
            {curve.map((point, index) => {
              const x = curve.length <= 1 ? 10 : (index / (curve.length - 1)) * 300 + 10;
              const y = 80 - ((point.value ?? 0) / max) * 70;
              return <text key={point.tenor} x={x} y={y - 6} textAnchor="middle" fill="#E6E8EE" fontSize="9">{point.value?.toFixed(2)}</text>;
            })}
          </svg>
          <div className="flex justify-between text-[10px] text-dim">
            {curve.map((point) => <span key={point.tenor}>{point.tenor}</span>)}
          </div>
        </section>
      </div>
    </PanelFrame>
  );
}
