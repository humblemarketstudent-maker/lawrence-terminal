import { useTerminal } from "../context/TerminalContext.tsx";
import { formatCompact, formatMultiple, formatPct, formatPrice, toneClass, toneOf } from "../lib/format.ts";
import type { CompanyProfile, PeerRow } from "../types.ts";
import { EmptyNote, PanelFrame, SourcePill } from "./bits.tsx";

function Field({ label, value, title, tone }: { label: string; value: string; title?: string; tone?: "up" | "down" | "flat" }) {
  return (
    <div className="border border-border px-2 py-1.5" title={title}>
      <div className="text-[9px] uppercase tracking-wide text-dim">{label}</div>
      <div className={`truncate ${tone ? toneClass(tone) : ""}`}>{value}</div>
    </div>
  );
}

function statusText(status: string, reason?: string | null): string {
  if (status === "pending") return "LOAD";
  if (status === "unavailable") return "UNAVAILABLE";
  return reason || "—";
}

function turnoverValue(profile: CompanyProfile): { text: string; title: string } {
  if (profile.turnoverStatus === "pending") return { text: "LOAD", title: "Loading dollar turnover" };
  if (profile.turnoverStatus !== "ok" || profile.turnoverUsd == null) {
    const local = profile.turnoverLocal != null ? `Local ${formatCompact(profile.turnoverLocal)} ${profile.turnoverCurrency ?? ""}`.trim() : "";
    return { text: "UNAVAILABLE", title: [profile.turnoverReason, local].filter(Boolean).join(" · ") };
  }
  const fx = profile.fxPair && profile.fxPair !== "USD" && profile.fxRate != null
    ? `${profile.fxPair} ${profile.fxRate.toFixed(profile.fxRate < 0.1 ? 6 : 4)}`
    : "USD";
  const local = profile.turnoverCurrency && profile.turnoverCurrency !== "USD"
    ? `${formatCompact(profile.turnoverLocal)} ${profile.turnoverCurrency}`
    : "";
  return { text: `$${formatCompact(profile.turnoverUsd)}`, title: [local, fx].filter(Boolean).join(" · ") || "Dollar turnover" };
}

function PeerTable({
  peers,
  status,
  reason,
  source,
  onPick,
}: {
  peers: PeerRow[];
  status: CompanyProfile["peersStatus"];
  reason?: string | null;
  source?: string | null;
  onPick: (symbol: string) => void;
}) {
  return (
    <div data-testid="peer-comparison">
      <div className="mb-1 flex items-baseline gap-2">
        <span className="text-[10px] uppercase tracking-[0.14em] text-amber">Peer comparison</span>
        {source ? <span className="truncate text-[10px] text-dim">{source}</span> : null}
      </div>
      {status !== "ok" ? <div className="text-[12px] text-amber" title={reason ?? ""}>{statusText(status, reason)}{reason && status === "unavailable" ? ` · ${reason}` : ""}</div> : null}
      {status === "ok" && peers.length === 0 ? <div className="text-[12px] text-amber">UNAVAILABLE</div> : null}
      {status === "ok" && peers.length > 0 ? (
        <div className="overflow-auto border border-border">
          <table className="w-full text-[11px]">
            <thead className="text-dim">
              <tr>
                {["Ticker", "Price", "Chg %", "Fwd P/E", "P/B", "Mkt cap", "P/E", "EV/EBITDA"].map((label) => (
                  <th key={label} className="px-2 py-1 text-right font-normal first:text-left">{label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {peers.map((peer) => (
                <tr key={peer.symbol} className="border-t border-border">
                  <td className="px-2 py-1">
                    <button type="button" className="text-amber" onClick={() => onPick(peer.symbol)}>{peer.symbol}</button>
                    <span className="ml-2 text-dim">{peer.name}</span>
                  </td>
                  <td className="px-2 text-right">{formatPrice(peer.price, "equity")}</td>
                  <td className={`px-2 text-right ${toneClass(toneOf(peer.changePct))}`}>{formatPct(peer.changePct, 2)}</td>
                  <td className="px-2 text-right">{peer.forwardPE?.toFixed(1) ?? "—"}</td>
                  <td className="px-2 text-right">{peer.priceBook?.toFixed(1) ?? "—"}</td>
                  <td className="px-2 text-right">{formatCompact(peer.marketCap, 1)}</td>
                  <td className="px-2 text-right">{peer.trailingPE?.toFixed(1) ?? "—"}</td>
                  <td className="px-2 text-right">{peer.evEbitda?.toFixed(1) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

export function TearSheet() {
  const { profile, profileMeta, activeQuote, selectTicker, filings, symbol } = useTerminal();
  if (!profile) return <PanelFrame code="DES" title={symbol}><EmptyNote>Loading the tear sheet.</EmptyNote></PanelFrame>;
  const liveQuote = activeQuote && !activeQuote.sample && activeQuote.status === "ok" ? activeQuote : null;
  const price = profile.sample ? (liveQuote?.price ?? profile.price) : (profile.price ?? liveQuote?.price ?? null);
  const changePct = profile.sample ? (liveQuote?.changePct ?? profile.changePct) : (profile.changePct ?? liveQuote?.changePct ?? null);
  const analyst = profile.analyst;
  const low = analyst?.targetLow;
  const high = analyst?.targetHigh;
  const span = low != null && high != null && high !== low ? high - low : null;
  const turnover = turnoverValue(profile);
  const events = profile.eventsStatus === "ok"
    ? profile.events.map((event) => [event.label, event.date, event.detail].filter(Boolean).join(" ")).join(" · ")
    : profile.eventsStatus === "unavailable"
      ? `UNAVAILABLE${profile.eventsReason ? ` · ${profile.eventsReason}` : ""}`
      : "LOAD";
  return (
    <PanelFrame
      code="DES"
      title={`${profile.label} · ${profile.name}`}
      extra={<span className="text-[10px] text-dim">{profile.currency}</span>}
      right={<SourcePill meta={profileMeta} />}
    >
      <div className="grid gap-3 p-3 lg:grid-cols-[1.4fr_1fr]" data-testid="company-view">
        <div className="space-y-3 lg:col-span-2">
          <div className="grid grid-cols-2 gap-2 text-[11px] sm:grid-cols-4 xl:grid-cols-7" data-testid="company-stats">
            <Field label="Last" value={formatPrice(price, profile.assetClass)} />
            <Field label="Change" value={formatPct(changePct, 2)} tone={toneOf(changePct)} />
            <Field label="Turnover USD" value={turnover.text} title={turnover.title} />
            <Field label="52w high" value={formatPrice(profile.week52High, profile.assetClass)} />
            <Field label="52w low" value={formatPrice(profile.week52Low, profile.assetClass)} />
            <Field label="Fwd P/E" value={profile.forwardPE == null ? "—" : `${profile.forwardPE.toFixed(2)}x`} />
            <Field label="P/B" value={profile.priceToBook == null ? "—" : `${profile.priceToBook.toFixed(2)}x`} />
          </div>
          <div className="border border-border px-2 py-1.5 text-[12px]" title={profile.eventsReason ?? ""}>
            <div className="text-[9px] uppercase tracking-wide text-dim">Upcoming events</div>
            <div className={profile.eventsStatus === "ok" ? "" : "text-amber"}>{events}</div>
          </div>
          <div>
            <p className="copy text-[13px] leading-relaxed text-foreground/90">{profile.summary}</p>
            {profile.descriptionSource ? <div className="mt-1 text-[10px] text-dim">Source: {profile.descriptionSource}</div> : null}
          </div>
          <PeerTable
            peers={profile.peers}
            status={profile.peersStatus}
            reason={profile.peersReason}
            source={profile.peersSource}
            onPick={selectTicker}
          />
        </div>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2 text-[11px] sm:grid-cols-4">
            {[
              ["Mkt cap", formatCompact(profile.marketCap ?? activeQuote?.marketCap)],
              ["EV", formatCompact(profile.enterpriseValue)],
              ["Price", formatPrice(price, profile.assetClass)],
              ["EPS", profile.eps == null ? "—" : profile.eps.toFixed(2)],
              ["Div yield", profile.dividendYield == null ? "—" : `${profile.dividendYield.toFixed(2)}%`],
              ["Beta", profile.beta == null ? "—" : profile.beta.toFixed(2)],
              ["Employees", profile.employees ? profile.employees.toLocaleString("en-US") : "—"],
              ["HQ", profile.headquarters ?? "—"],
            ].map(([label, value]) => (
              <div key={label} className="border border-border px-2 py-1.5">
                <div className="text-[9px] uppercase tracking-wide text-dim">{label}</div>
                <div className="truncate">{value}</div>
              </div>
            ))}
          </div>
          <div>
            <div className="mb-1 text-[10px] uppercase tracking-wide text-dim">Key executives</div>
            {profile.executives.length === 0 ? <div className="text-[12px] text-muted">No officer list on this instrument.</div> : null}
            <table className="w-full text-[11px]">
              <tbody>
                {profile.executives.map((person) => (
                  <tr key={`${person.name}-${person.title}`} className="border-t border-border">
                    <td className="py-1 pr-3">{person.name}</td>
                    <td className="py-1 text-muted">{person.title}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div>
            <div className="mb-1 text-[10px] uppercase tracking-wide text-dim">Recent filings</div>
            {filings.slice(0, 5).map((filing) => (
              <a key={`${filing.form}-${filing.filed}-${filing.accession}`} href={filing.url} target="_blank" rel="noreferrer" className="flex gap-2 border-t border-border py-1 text-[11px] hover:text-amber">
                <span className="w-12 text-amber">{filing.form}</span>
                <span className="w-24 text-dim">{filing.filed}</span>
                <span className="truncate">{filing.description}</span>
              </a>
            ))}
            {filings.length === 0 ? <div className="text-[12px] text-muted">No SEC filings for this symbol.</div> : null}
          </div>
        </div>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            {profile.multiples.map((item) => (
              <div key={item.key} className="border border-border px-2 py-2">
                <div className="text-[9px] uppercase tracking-wide text-amber">{item.label}</div>
                <div className="text-[16px]">{formatMultiple(item.value, item.unit)}</div>
              </div>
            ))}
          </div>
          {analyst ? (
            <div className="border border-border p-2">
              <div className="text-[10px] uppercase tracking-wide text-dim">
                Street {analyst.recommendation ?? "—"} · {analyst.numAnalysts ?? "—"} analysts
              </div>
              <div className="mt-2 text-[12px]">
                Low {formatPrice(analyst.targetLow)} · Mean {formatPrice(analyst.targetMean)} · High {formatPrice(analyst.targetHigh)}
              </div>
              {span != null && low != null && price != null ? (
                <div className="relative mt-3 h-2 bg-border">
                  <span className="absolute top-[-3px] h-3 w-px bg-foreground" style={{ left: `${Math.min(100, Math.max(0, ((analyst.targetMean ?? low) - low) / span * 100))}%` }} />
                  <span className="absolute top-[-4px] h-4 w-1 bg-amber" style={{ left: `${Math.min(100, Math.max(0, (price - low) / span * 100))}%` }} />
                </div>
              ) : null}
              <div className="mt-1 text-[10px] text-dim">Amber mark is last price. White tick is the mean target.</div>
            </div>
          ) : null}
          {profile.options ? (
            <div className="border border-border p-2 text-[11px]">
              <div className="text-[10px] uppercase tracking-wide text-dim">ATM options · {profile.options.expiry}</div>
              <div className="mt-1 grid grid-cols-2 gap-2">
                <div>Strike {formatPrice(profile.options.atmStrike)}</div>
                <div>Spot {formatPrice(profile.options.underlying)}</div>
                <div className="text-up">Call {formatPrice(profile.options.callLast)} · IV {profile.options.callIV?.toFixed(1) ?? "—"}%</div>
                <div className="text-down">Put {formatPrice(profile.options.putLast)} · IV {profile.options.putIV?.toFixed(1) ?? "—"}%</div>
                <div>Call OI {formatCompact(profile.options.callOI, 0)}</div>
                <div>Put OI {formatCompact(profile.options.putOI, 0)}</div>
              </div>
            </div>
          ) : null}
          {profile.website ? (
            <a className="text-[11px] text-amber" href={profile.website} target="_blank" rel="noreferrer">{profile.website}</a>
          ) : null}
        </div>
      </div>
    </PanelFrame>
  );
}
