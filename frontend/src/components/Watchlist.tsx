import { useState } from "react";
import { useTerminal } from "../context/TerminalContext.tsx";
import { formatCompact, formatMove, formatPrice } from "../lib/format.ts";
import { PanelFrame, RangeTrack, Sparkline, useFlash } from "./bits.tsx";
import { Input } from "./ui/input.tsx";

function Row({ symbol }: { symbol: string }) {
  const { quotes, symbol: active, selectTicker, removeTicker } = useTerminal();
  const quote = quotes[symbol];
  const flash = useFlash(quote?.price);
  const move = formatMove(quote ?? { change: null, changePct: null, assetClass: "equity" });
  const up = (quote?.change ?? 0) >= 0;
  return (
    <div className={`border-b border-border px-2 py-1.5 ${active === symbol ? "bg-amber/10" : "hover:bg-white/[0.03]"}`}>
      <button type="button" onClick={() => selectTicker(symbol)} className="grid w-full grid-cols-[1fr_auto_auto] items-center gap-2 text-left">
        <div className="min-w-0">
          <div className="flex items-baseline gap-2">
            <span className="text-[12px] text-amber">{quote?.label ?? symbol}</span>
            {quote?.sample ? <span className="text-[9px] text-amber/80">SMP</span> : null}
          </div>
          <div className="truncate text-[10px] text-dim">{quote?.name ?? "Awaiting quote"}</div>
        </div>
        <div className={`text-right ${flash}`}>
          <div className="text-[12px]">{quote?.status === "unavailable" ? "NO DATA" : formatPrice(quote?.price, quote?.assetClass)}</div>
          <div className={`text-[10px] ${move.tone === "up" ? "text-up" : move.tone === "down" ? "text-down" : "text-muted"}`}>
            {move.net} {move.pct}
          </div>
        </div>
        <Sparkline values={quote?.sparkline ?? []} up={up} />
      </button>
      <div className="mt-1 grid grid-cols-[1fr_72px] items-center gap-2">
        <div className="space-y-1">
          <RangeTrack label="D" low={quote?.low ?? null} high={quote?.high ?? null} price={quote?.price ?? null} />
          <RangeTrack label="52" low={quote?.week52Low ?? null} high={quote?.week52High ?? null} price={quote?.price ?? null} />
        </div>
        <div className="text-right text-[10px] text-muted">
          <div>VOL {formatCompact(quote?.volume ?? null, 1)}</div>
          <div className={quote?.volumeRatio && quote.volumeRatio > 1.5 ? "text-amber" : ""}>
            {quote?.volumeRatio ? `${quote.volumeRatio.toFixed(2)}x 30d` : "—"}
          </div>
          <button type="button" className="text-dim hover:text-down" onClick={() => removeTicker(symbol)}>
            remove
          </button>
        </div>
      </div>
    </div>
  );
}

export function Watchlist() {
  const { watchlist, addTicker, quoteMeta } = useTerminal();
  const [draft, setDraft] = useState("");
  return (
    <PanelFrame code="MON" title="Watchlist" right={<span className="text-[10px] text-dim">{quoteMeta?.source ?? ""}</span>}>
      <div className="absolute inset-0 flex flex-col">
      <div className="min-h-0 flex-1 overflow-auto">
        {watchlist.map((symbol) => (
          <Row key={symbol} symbol={symbol} />
        ))}
      </div>
      <form
        className="shrink-0 border-t border-border bg-panel p-2"
        onSubmit={(event) => {
          event.preventDefault();
          void addTicker(draft).then(() => setDraft(""));
        }}
      >
        <Input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Add NVDA, 0700.HK, ^HSI, USDHKD=X"
          aria-label="Add ticker"
        />
      </form>
      </div>
    </PanelFrame>
  );
}
