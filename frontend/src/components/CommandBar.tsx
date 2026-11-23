import { useEffect, useMemo, useState } from "react";
import { useTerminal } from "../context/TerminalContext.tsx";
import { EXAMPLES, FUNC_HINT, parseCommand } from "../lib/command.ts";
import { Button } from "./ui/button.tsx";

function sessionOpen(timeZone: string, start: number, end: number, now: Date) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    weekday: "short",
  }).formatToParts(now);
  const weekday = parts.find((part) => part.type === "weekday")?.value;
  if (weekday === "Sat" || weekday === "Sun") return false;
  const hour = Number(parts.find((part) => part.type === "hour")?.value ?? "0");
  const minute = Number(parts.find((part) => part.type === "minute")?.value ?? "0");
  const value = hour + minute / 60;
  return value >= start && value < end;
}

export function CommandBar() {
  const { commandRef, runCommand, openBrief, symbol, func, refreshing, watchlist } = useTerminal();
  const [value, setValue] = useState(`${symbol} <${func}>`);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cursor, setCursor] = useState(0);
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    setValue((current) => (document.activeElement === commandRef.current ? current : `${symbol} <${func}>`));
  }, [symbol, func, commandRef]);

  const suggestions = useMemo(() => {
    const query = value.trim().toUpperCase();
    if (!query) return EXAMPLES.slice(0, 8);
    const tickerHits = watchlist
      .filter((item) => item.toUpperCase().includes(query))
      .slice(0, 6)
      .map((item) => `${item} <DES>`);
    const examples = EXAMPLES.filter((example) => example.toUpperCase().includes(query));
    const pool = [...tickerHits, ...examples.filter((example) => !tickerHits.includes(example))];
    return (pool.length ? pool : EXAMPLES).slice(0, 8);
  }, [value, watchlist]);

  const sessions = [
    ["US", sessionOpen("America/New_York", 9.5, 16, now)],
    ["EU", sessionOpen("Europe/London", 8, 16.5, now)],
    ["HK", sessionOpen("Asia/Hong_Kong", 9.5, 16, now)],
  ] as const;

  function commit(text: string) {
    const result = runCommand(text);
    if (result) {
      setError(result);
      return;
    }
    setError(null);
    setHistory((current) => [text, ...current.filter((item) => item !== text)].slice(0, 20));
    setHistoryIndex(-1);
    const parsed = parseCommand(text);
    if (!("error" in parsed) && parsed.func !== "BRIEF") {
      setValue(text.toUpperCase());
    }
    setOpen(false);
  }

  const utc = now.toISOString().slice(11, 19);
  const local = now.toLocaleTimeString(undefined, { hour12: false });

  return (
    <header className="relative z-30 shrink-0 border-b border-border bg-background">
      <div className="flex h-12 items-center gap-3 px-2">
        <div className="flex items-center gap-2 pr-1">
          <span className="grid h-7 w-7 place-items-center bg-amber font-mono text-sm font-semibold text-background">A</span>
          <div className="leading-none">
            <div className="text-[13px] font-semibold tracking-[0.18em] text-amber">APEX</div>
            <div className="text-[9px] tracking-[0.22em] text-muted">TERMINAL</div>
          </div>
        </div>
        <div className="relative min-w-0 flex-1">
          <span className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-amber">&gt;</span>
          <input
            ref={commandRef}
            value={value}
            aria-label="Command bar"
            spellCheck={false}
            placeholder="Type a ticker, e.g. AAPL"
            onFocus={() => setOpen(true)}
            onBlur={() => window.setTimeout(() => setOpen(false), 120)}
            onChange={(event) => {
              setValue(event.target.value);
              setError(null);
              setCursor(0);
              setOpen(true);
            }}
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setCursor((index) => Math.min(suggestions.length - 1, index + 1));
              } else if (event.key === "ArrowUp") {
                event.preventDefault();
                if (open && cursor > 0) setCursor((index) => index - 1);
                else if (history.length) {
                  const next = Math.min(history.length - 1, historyIndex + 1);
                  setHistoryIndex(next);
                  setValue(history[next] ?? value);
                }
              } else if (event.key === "Enter") {
                event.preventDefault();
                commit(open && suggestions[cursor] && value.trim().length < 2 ? suggestions[cursor] : value);
              } else if (event.key === "Escape") {
                setOpen(false);
                event.currentTarget.blur();
              } else if (event.key === "Tab" && suggestions[cursor]) {
                event.preventDefault();
                setValue(suggestions[cursor]);
              }
            }}
            className="h-8 w-full border border-border bg-panel pl-6 pr-2 font-mono text-[13px] text-foreground outline-none placeholder:text-dim focus:border-amber"
          />
          {open ? (
            <ul className="absolute left-0 right-0 top-9 z-40 border border-border bg-panel">
              {suggestions.map((example, index) => {
                const code = example.match(/<([A-Z]+)>/)?.[1] ?? "";
                return (
                  <li key={example}>
                    <button
                      type="button"
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => commit(example)}
                      className={`flex w-full items-center gap-3 px-2 py-1 text-left text-[12px] ${index === cursor ? "bg-amber/10 text-amber" : "text-foreground"}`}
                    >
                      <span className="w-40">{example}</span>
                      <span className="text-[10px] text-muted">{FUNC_HINT[code]}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : null}
        </div>
        <div className="hidden items-center gap-3 lg:flex">
          {sessions.map(([label, openSession]) => (
            <span key={label} className="flex items-center gap-1 text-[10px] text-muted">
              <span className={`h-1.5 w-1.5 ${openSession ? "bg-up" : "bg-down"}`} />
              {label}
            </span>
          ))}
          <div className="text-right leading-tight">
            <div className="text-[11px] text-foreground">{utc} UTC</div>
            <div className="text-[10px] text-dim">{local}</div>
          </div>
        </div>
        <Button variant="amber" onClick={() => void openBrief()}>
          Brief
        </Button>
      </div>
      <div className="flex h-5 items-center px-3 text-[10px] text-dim">
        {error ? <span className="text-down">{error}</span> : <span>Type a ticker and Enter for the tear sheet · DES · GP chart · FA financials · N news · FIL filings · / to focus</span>}
        {refreshing ? <span className="ml-auto text-amber">REFRESH</span> : null}
      </div>
      {refreshing ? (
        <div className="relative h-px overflow-hidden bg-border">
          <div className="loadbar absolute inset-y-0 w-1/3 bg-amber" />
        </div>
      ) : null}
    </header>
  );
}
