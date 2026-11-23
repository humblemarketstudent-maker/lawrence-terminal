import { useTerminal } from "../context/TerminalContext.tsx";
import { EmptyNote, PanelFrame, SourcePill } from "./bits.tsx";

export function FilingsPanel() {
  const { filings, filingsMeta, symbol, profile } = useTerminal();
  return (
    <PanelFrame code="FIL" title={`${profile?.label ?? symbol} SEC filings`} right={<SourcePill meta={filingsMeta} />}>
      {filingsMeta?.warning ? <div className="px-3 py-2 text-[11px] text-amber">{filingsMeta.warning}</div> : null}
      {filings.length === 0 ? <EmptyNote>No recent 10-K, 10-Q, 8-K, or Form 4 rows for {symbol}.</EmptyNote> : null}
      <table className="w-full text-[11px]">
        <tbody>
          {filings.map((filing) => (
            <tr key={`${filing.accession ?? filing.url}-${filing.form}`} className="border-b border-border">
              <td className="px-2 py-2 text-amber">{filing.form}</td>
              <td className="px-2 py-2 text-dim">{filing.filed}</td>
              <td className="px-2 py-2">
                <a href={filing.url} target="_blank" rel="noreferrer" className="hover:text-amber">
                  {filing.description}
                </a>
                {filing.insider ? <div className="text-[10px] text-muted">{filing.insider}</div> : null}
              </td>
              <td className="px-2 py-2 text-[10px] text-dim">{filing.sample ? "SMP" : "EDGAR"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </PanelFrame>
  );
}
