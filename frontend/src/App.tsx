import { useEffect } from "react";
import { BriefDialog, HelpDialog } from "./components/BriefDialog.tsx";
import { CommandBar } from "./components/CommandBar.tsx";
import { MarketDashboard } from "./components/MarketDashboard.tsx";
import { NewsDrawer } from "./components/NewsWire.tsx";
import { Workspace } from "./components/Workspace.tsx";
import { TerminalProvider, useTerminal } from "./context/TerminalContext.tsx";
import { formatPrice } from "./lib/format.ts";

function StatusBar() {
  const { layout, setLayout, linked, setLinked, quoteMeta, newsMeta, providers, banner, loading, symbol, func, activeQuote } = useTerminal();
  return (
    <footer className="flex h-6 shrink-0 items-center gap-3 border-t border-border px-2 text-[10px] text-dim">
      <span className="text-amber">{symbol}</span>
      <span>&lt;{func}&gt;</span>
      <span>{activeQuote ? formatPrice(activeQuote.price, activeQuote.assetClass) : "—"}</span>
      <span className="hidden md:inline">MKT {providers?.market ?? "yfinance"}</span>
      <span className="hidden md:inline">QUOTES {quoteMeta?.source ?? (loading ? "LOAD" : "—")}</span>
      <span className="hidden lg:inline">NEWS {newsMeta?.source ?? "—"}</span>
      <button type="button" className={linked ? "text-amber" : ""} onClick={() => setLinked(!linked)}>
        {linked ? "LINKED" : "UNLINKED"}
      </button>
      <span className="ml-auto hidden items-center gap-1 sm:flex">
        {[1, 2, 3, 4].map((item) => (
          <button key={item} type="button" onClick={() => setLayout(item as 1 | 2 | 3 | 4)} className={layout === item ? "text-amber" : ""}>
            {item}
          </button>
        ))}
      </span>
      <span className="hidden xl:inline">/ command · 1-4 layout · R refresh · ? help</span>
      {banner ? <span className="max-w-[40%] truncate text-amber">{banner}</span> : null}
    </footer>
  );
}

function Hotkeys() {
  const { setLayout, refresh, focusCommand, setHelpOpen, setBriefOpen, setActiveNews } = useTerminal();
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing = target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable);
      if (event.key === "Escape") {
        setBriefOpen(false);
        setHelpOpen(false);
        setActiveNews(null);
        if (typing && target instanceof HTMLElement) target.blur();
        return;
      }
      if (typing) return;
      if (event.key === "/") {
        event.preventDefault();
        focusCommand();
      } else if ((event.key === "r" || event.key === "R") && !event.metaKey && !event.ctrlKey) {
        event.preventDefault();
        void refresh();
      } else if (event.key >= "1" && event.key <= "4" && !event.metaKey && !event.ctrlKey && !event.altKey) {
        setLayout(Number(event.key) as 1 | 2 | 3 | 4);
      } else if (event.key === "?") {
        setHelpOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [focusCommand, refresh, setActiveNews, setBriefOpen, setHelpOpen, setLayout]);
  return null;
}

function Title() {
  const { symbol, activeQuote } = useTerminal();
  useEffect(() => {
    document.title = activeQuote?.price != null ? `${symbol} ${formatPrice(activeQuote.price, activeQuote.assetClass)} · APEX` : "APEX Terminal";
  }, [activeQuote, symbol]);
  return null;
}

function Shell() {
  return (
    <div className="flex h-full min-h-0 flex-col bg-background text-foreground">
      <Hotkeys />
      <Title />
      <CommandBar />
      <MarketDashboard />
      <div className="min-h-0 flex-1">
        <Workspace />
      </div>
      <StatusBar />
      <BriefDialog />
      <HelpDialog />
      <NewsDrawer />
    </div>
  );
}

export default function App() {
  return (
    <TerminalProvider>
      <Shell />
    </TerminalProvider>
  );
}
