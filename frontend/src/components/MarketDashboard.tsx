import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useTerminal } from "../context/TerminalContext.tsx";
import { formatCompact, formatMove, formatPrice, toneClass } from "../lib/format.ts";
import type { DashboardBoard, DashboardRow, Meta, MoverRow } from "../types.ts";
import { api } from "../lib/api.ts";
import { SourcePill } from "./bits.tsx";

function formatLevel(row: DashboardRow): string {
  if (row.price == null) return "—";
  if (row.assetClass === "rate") return `${row.price.toFixed(3)}%`;
  return formatPrice(row.price, row.assetClass);
}

function MoveText({ row }: { row: DashboardRow }) {
  if (row.status === "pending") return <span className="text-[10px] text-dim">LOAD</span>;
  if (row.status === "unavailable") return <span className="text-[10px] text-amber">UNAVAILABLE</span>;
  const move = formatMove({ change: row.change, changePct: row.changePct, assetClass: row.assetClass });
  const text = row.assetClass === "rate" ? move.net : `${move.net} ${move.pct}`;
  return <span className={`text-[10px] ${toneClass(move.tone)}`}>{text}</span>;
}

function StripCell({ row, onOpen }: { row: DashboardRow; onOpen: (symbol: string) => void }) {
  const detail = row.provider === "fred" ? `FRED ${row.symbol ?? ""}` : row.group;
  const session = row.session ? ` · ${row.session}` : "";
  const title = [row.name, row.reason, row.previousClose != null ? `prev ${row.previousClose}` : ""].filter(Boolean).join(" · ");
  const body = (
    <>
      <div className="truncate text-[10px] uppercase tracking-wide text-muted">{row.name}</div>
      <div className="mt-0.5 flex items-baseline justify-between gap-2">
        <span className="text-[13px]">{row.status === "ok" ? formatLevel(row) : "—"}</span>
        <MoveText row={row} />
      </div>
      <div className="truncate text-[9px] text-dim">{detail}{session}</div>
    </>
  );
  const className = "min-w-0 border-b border-r border-border px-2 py-1 text-left hover:bg-white/[0.03]";
  if (row.link && row.symbol) {
    return (
      <button type="button" title={title} className={className} onClick={() => onOpen(row.symbol as string)}>
        {body}
      </button>
    );
  }
  return (
    <div title={title} className={className}>
      {body}
    </div>
  );
}

function MoverLine({ row, volume, onOpen }: { row: MoverRow; volume?: boolean; onOpen: (symbol: string) => void }) {
  const move = formatMove({ change: row.change, changePct: row.changePct, assetClass: "equity" });
  return (
    <button
      type="button"
      title={row.name}
      onClick={() => onOpen(row.symbol)}
      className={`grid w-full items-baseline gap-2 px-2 py-[3px] text-left hover:bg-white/[0.04] ${volume ? "grid-cols-[minmax(0,1fr)_auto_auto_auto]" : "grid-cols-[minmax(0,1fr)_auto_auto]"}`}
    >
      <span className="truncate text-[11px] text-amber">{row.symbol}</span>
      <span className="text-[11px]">{formatPrice(row.price, "equity")}</span>
      <span className={`text-[11px] ${toneClass(move.tone)}`}>{move.pct}</span>
      {volume ? <span className="text-[10px] text-dim">{formatCompact(row.volume, 1)}</span> : null}
    </button>
  );
}

function Column({
  code,
  title,
  note,
  children,
}: {
  code: string;
  title: string;
  note?: string;
  children: ReactNode;
}) {
  return (
    <section className="flex min-h-0 flex-col border-b border-r border-border xl:h-full xl:border-b-0">
      <header className="flex h-6 shrink-0 items-center gap-2 border-b border-border px-2">
        <span className="text-[10px] text-amber">{code}</span>
        <span className="truncate text-[10px] uppercase tracking-[0.14em] text-muted">{title}</span>
        {note ? <span className="ml-auto truncate text-[9px] text-dim">{note}</span> : null}
      </header>
      <div className="min-h-0 flex-1 overflow-auto">{children}</div>
    </section>
  );
}

function EmptyLine({ children }: { children: string }) {
  return <div className="px-2 py-3 text-[11px] text-dim">{children}</div>;
}

export function MarketDashboard() {
  const { selectTicker, refreshing } = useTerminal();
  const [board, setBoard] = useState<DashboardBoard | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);

  const load = useCallback(() => {
    api
      .dashboard()
      .then((section) => {
        setBoard(section.data);
        setMeta(section.meta);
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 15000);
    return () => window.clearInterval(timer);
  }, [load]);

  useEffect(() => {
    if (!refreshing) load();
  }, [load, refreshing]);

  const movers = board?.movers;
  const progress = !movers ? "LOAD" : movers.ready ? `${movers.quoted}/${movers.universe} quoted` : `${movers.attempted}/${movers.universe}`;
  const waiting = movers && !movers.ready ? `Quoting the equity book ${movers.attempted}/${movers.universe}` : null;

  return (
    <section
      className="max-h-[46vh] min-h-0 shrink-0 overflow-auto border-b border-border bg-panel min-[901px]:max-h-none min-[901px]:overflow-visible"
      data-testid="market-dashboard"
    >
      <header className="flex h-6 items-center gap-2 border-b border-border px-2">
        <span className="text-[11px] text-amber">MKT</span>
        <span className="text-[10px] uppercase tracking-[0.14em] text-muted">Market</span>
        <span className="hidden text-[10px] text-dim sm:inline">{progress} · last session volume</span>
        {meta?.warning ? <span className="truncate text-[10px] text-amber">{meta.warning}</span> : null}
        <span className="ml-auto">{meta?.warning?.startsWith("Loading") ? <span className="text-[10px] text-amber">LOAD</span> : <SourcePill meta={meta} />}</span>
      </header>
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7" data-testid="dash-strip">
        {(board?.strip ?? []).map((row) => (
          <StripCell key={row.name} row={row} onOpen={selectTicker} />
        ))}
        {!board ? <div className="col-span-full px-2 py-2 text-[11px] text-dim">LOAD</div> : null}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:h-44 xl:grid-cols-4 xl:overflow-hidden">
        <Column code="ACT" title="Most active" note="volume">
          {waiting ? <EmptyLine>{waiting}</EmptyLine> : null}
          {!waiting && movers && movers.active.length === 0 ? <EmptyLine>No live volume prints yet.</EmptyLine> : null}
          {movers?.ready ? movers.active.map((row) => <MoverLine key={row.symbol} row={row} volume onOpen={selectTicker} />) : null}
        </Column>
        <Column code="UP" title="Most rise" note="% vs prior close">
          {waiting ? <EmptyLine>{waiting}</EmptyLine> : null}
          {!waiting && movers && movers.rise.length === 0 ? <EmptyLine>No percent changes yet.</EmptyLine> : null}
          {movers?.ready ? movers.rise.map((row) => <MoverLine key={row.symbol} row={row} onOpen={selectTicker} />) : null}
        </Column>
        <Column code="DN" title="Most drop" note="% vs prior close">
          {waiting ? <EmptyLine>{waiting}</EmptyLine> : null}
          {!waiting && movers && movers.drop.length === 0 ? <EmptyLine>No percent changes yet.</EmptyLine> : null}
          {movers?.ready ? movers.drop.map((row) => <MoverLine key={row.symbol} row={row} onOpen={selectTicker} />) : null}
        </Column>
        <Column code="G10" title="G10 FX" note="vs prior close">
          {(board?.fx ?? []).map((row) => (
            <button
              key={row.name}
              type="button"
              title={row.reason ?? row.name}
              onClick={() => row.link && row.symbol && selectTicker(row.symbol)}
              className="grid w-full grid-cols-[72px_minmax(0,1fr)_auto] items-baseline gap-2 px-2 py-[3px] text-left hover:bg-white/[0.04]"
            >
              <span className="truncate text-[11px] text-amber">{row.name}</span>
              <span className="text-right text-[11px]">{row.status === "ok" ? formatLevel(row) : "—"}</span>
              <MoveText row={row} />
            </button>
          ))}
          {!board ? <EmptyLine>LOAD</EmptyLine> : null}
        </Column>
      </div>
    </section>
  );
}
