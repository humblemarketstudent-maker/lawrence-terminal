import { useMemo, useState } from "react";
import { useTerminal } from "../context/TerminalContext.tsx";
import { relativeTime, stamp } from "../lib/format.ts";
import type { NewsAsset, NewsItem, NewsSource } from "../types.ts";
import { EmptyNote, PanelFrame, SourcePill } from "./bits.tsx";
import { Modal } from "./ui/dialog.tsx";
import { Input } from "./ui/input.tsx";

const SOURCES: NewsSource[] = ["ALL", "REUTERS", "BLOOMBERG", "WSJ", "YAHOO"];
const ASSETS: NewsAsset[] = ["ALL", "Equities", "Macro/Rates", "Asia/EM", "Tech", "Energy"];

function Badge({ source }: { source: string }) {
  return <span className="border border-amber/40 px-1 text-[9px] tracking-wide text-amber">{source}</span>;
}

function Sentiment({ item }: { item: NewsItem }) {
  const color = item.sentiment === "BULLISH" ? "text-up" : item.sentiment === "BEARISH" ? "text-down" : "text-muted";
  return (
    <span className={`text-[9px] ${color}`}>
      {item.sentiment} {item.impact}
    </span>
  );
}

export function NewsWire({ mode }: { mode: "rail" | "full" }) {
  const { news, symbolNews, newsMeta, symbolNewsMeta, setActiveNews, selectTicker, watchlist, symbol } = useTerminal();
  const sourceItems = mode === "full" ? (symbolNews.length ? symbolNews : news) : news;
  const meta = mode === "full" ? symbolNewsMeta ?? newsMeta : newsMeta;
  const [source, setSource] = useState<NewsSource>("ALL");
  const [asset, setAsset] = useState<NewsAsset>("ALL");
  const [query, setQuery] = useState("");
  const [onlyBook, setOnlyBook] = useState(false);

  const rows = useMemo(() => {
    return sourceItems.filter((item) => {
      if (source !== "ALL" && item.source !== source) return false;
      if (asset !== "ALL" && item.assetClass !== asset) return false;
      if (onlyBook && !item.tickers.some((ticker) => watchlist.includes(ticker))) return false;
      if (query && !`${item.headline} ${item.summary}`.toLowerCase().includes(query.toLowerCase())) return false;
      return true;
    });
  }, [sourceItems, source, asset, onlyBook, query, watchlist]);

  return (
    <PanelFrame
      code={mode === "full" ? "N" : undefined}
      title={mode === "full" ? `${symbol} news wire` : "News wire"}
      right={<SourcePill meta={meta} />}
    >
      <div className="sticky top-0 z-10 space-y-1 border-b border-border bg-panel px-2 py-1">
        <div className="flex flex-wrap gap-1">
          {SOURCES.map((item) => (
            <button key={item} type="button" onClick={() => setSource(item)} className={`px-1.5 py-0.5 text-[10px] ${source === item ? "bg-amber text-background" : "text-muted"}`}>
              {item === "ALL" ? "ALL" : item.slice(0, 3)}
            </button>
          ))}
          <button type="button" onClick={() => setOnlyBook((value) => !value)} className={`ml-auto px-1.5 py-0.5 text-[10px] ${onlyBook ? "text-amber" : "text-dim"}`}>
            BOOK
          </button>
        </div>
        {mode === "full" ? (
          <div className="flex flex-wrap items-center gap-1">
            {ASSETS.map((item) => (
              <button key={item} type="button" onClick={() => setAsset(item)} className={`px-1.5 py-0.5 text-[10px] ${asset === item ? "text-amber" : "text-dim"}`}>
                {item}
              </button>
            ))}
            <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter headlines" className="ml-auto h-6 max-w-40 text-[11px]" aria-label="Filter headlines" />
          </div>
        ) : null}
        {meta?.warning ? <div className="text-[10px] text-amber">{meta.warning}</div> : null}
      </div>
      {rows.length === 0 ? <EmptyNote>No headlines match this filter. Clear it or press R to refresh the wire.</EmptyNote> : null}
      {rows.map((item) => (
        <article key={item.id} className={`border-b border-border px-2 py-1.5 ${item.breaking ? "breaking-row" : ""}`}>
          <button type="button" onClick={() => setActiveNews(item)} className="w-full text-left">
            <div className="flex items-center gap-2">
              <Badge source={item.source} />
              <span className="text-[10px] text-dim" title={stamp(item.publishedAt)}>
                {relativeTime(item.publishedAt)}
              </span>
              {item.breaking ? <span className="text-[9px] text-down">BREAK</span> : null}
              {item.sample ? <span className="text-[9px] text-amber">SMP</span> : null}
              <Sentiment item={item} />
            </div>
            <h3 className="mt-1 text-[12px] leading-snug text-foreground">{item.headline}</h3>
          </button>
          <div className="mt-1 flex flex-wrap gap-1">
            {item.keywords.map((keyword) => (
              <span key={keyword} className="bg-amber/15 px-1 text-[9px] uppercase text-amber">
                {keyword}
              </span>
            ))}
            {item.tickers.map((ticker) => (
              <button key={ticker} type="button" onClick={() => selectTicker(ticker)} className="text-[10px] text-amber hover:underline">
                {ticker}
              </button>
            ))}
          </div>
        </article>
      ))}
    </PanelFrame>
  );
}

export function NewsDrawer() {
  const { activeNews, setActiveNews, selectTicker } = useTerminal();
  const item = activeNews;
  return (
    <Modal open={item != null} onOpenChange={(open) => !open && setActiveNews(null)} title="READER" side>
      {item ? (
        <div className="space-y-3 p-3">
          <div className="flex flex-wrap items-center gap-2 text-[10px]">
            <Badge source={item.source} />
            <span className="text-dim">{stamp(item.publishedAt)}</span>
            <Sentiment item={item} />
          </div>
          <h2 className="text-[16px] leading-snug text-foreground">{item.headline}</h2>
          <p className="copy text-[14px] leading-relaxed text-muted">{item.summary}</p>
          <div>
            <div className="text-[10px] uppercase tracking-wide text-dim">Extracted tickers</div>
            <div className="mt-1 flex flex-wrap gap-2">
              {item.tickers.length === 0 ? <span className="text-[12px] text-muted">None detected in the snippet.</span> : null}
              {item.tickers.map((ticker) => (
                <button key={ticker} type="button" className="border border-border px-2 py-1 text-[11px] text-amber" onClick={() => selectTicker(ticker)}>
                  {ticker}
                </button>
              ))}
            </div>
          </div>
          <p className="text-[10px] leading-relaxed text-dim">
            Sentiment is a lexicon score on the headline and RSS snippet, not a model forecast. The body stays at the publisher.
          </p>
          {item.url ? (
            <a className="inline-block border border-amber px-3 py-2 text-[11px] text-amber" href={item.url} target="_blank" rel="noreferrer">
              Open original
            </a>
          ) : null}
        </div>
      ) : null}
    </Modal>
  );
}
