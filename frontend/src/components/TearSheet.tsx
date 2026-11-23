import { useTerminal } from "../context/TerminalContext.tsx";
import { formatCompact, formatMultiple, formatPct, formatPrice } from "../lib/format.ts";
import type { PeerRow } from "../types.ts";
import { EmptyNote, PanelFrame, SourcePill } from "./bits.tsx";

function PeerTable({ peers, onPick }: { peers: PeerRow[]; onPick: (symbol: string) => void }) {
  return (
    <div>
      <div className="mb-1 text-[10px] uppercase tracking-[0.14em] text-amber">Peer comparison</div>
      {peers.length === 0 ? <div className="text-[12px] text-muted">No mapped comps for this symbol.</div> : null}
      {peers.length > 0 ? (
        <div className="overflow-auto border border-border">
          <table className="w-full text-[11px]">
            <thead className="text-dim">
              <tr>
                {["Ticker", "Mkt cap", "P/E", "Fwd", "EV/EBITDA", "P/B", "Rev g", "YTD"].map((label) => (
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
                  <td className="px-2 text-right">{formatCompact(peer.marketCap, 1)}</td>
                  <td className="px-2 text-right">{peer.trailingPE?.toFixed(1) ?? "—"}</td>
                  <td className="px-2 text-right">{peer.forwardPE?.toFixed(1) ?? "—"}</td>
                  <td className="px-2 text-right">{peer.evEbitda?.toFixed(1) ?? "—"}</td>
                  <td className="px-2 text-right">{peer.priceBook?.toFixed(1) ?? "—"}</td>
                  <td className="px-2 text-right">{formatPct(peer.revenueGrowth, 1)}</td>
                  <td className={`px-2 text-right ${(peer.ytd ?? 0) >= 0 ? "text-up" : "text-down"}`}>{formatPct(peer.ytd, 1)}</td>
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
  const price = activeQuote?.price ?? profile.price;
  const analyst = profile.analyst;
  const low = analyst?.targetLow;
  const high = analyst?.targetHigh;
  const span = low != null && high != null && high !== low ? high - low : null;
  return (
    <PanelFrame
      code="DES"
      title={`${profile.label} · ${profile.name}`}
      extra={<span className="text-[10px] text-dim">{[profile.sector, profile.industry].filter(Boolean).join(" · ")}</span>}
      right={<SourcePill meta={profileMeta} />}
    >
      <div className="grid gap-3 p-3 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-3 lg:col-span-2">
          <p className="copy line-clamp-3 text-[13px] leading-relaxed text-foreground/90">{profile.summary}</p>
          <PeerTable peers={profile.peers} onPick={selectTicker} />
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
