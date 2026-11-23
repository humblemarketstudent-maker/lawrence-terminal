import { useState } from "react";
import { useTerminal } from "../context/TerminalContext.tsx";
import { formatSigned, toneClass, toneOf } from "../lib/format.ts";
import type { EcoEvent } from "../types.ts";
import { PanelFrame, SourcePill, Sparkline } from "./bits.tsx";

function print(value: number | null, unit: string) {
  if (value == null) return "—";
  if (unit === "k") return `${value.toFixed(0)}k`;
  if (unit === "idx") return value.toFixed(1);
  return `${value.toFixed(unit === "%" ? 2 : 1)}${unit === "%" ? "%" : ""}`;
}

function surprise(event: EcoEvent) {
  if (event.actual == null || event.consensus == null) return null;
  return event.actual - event.consensus;
}

export function EcoPanel() {
  const { eco, ecoMeta } = useTerminal();
  const [category, setCategory] = useState("ALL");
  const events = (eco?.events ?? []).filter((event) => category === "ALL" || event.category === category);
  return (
    <PanelFrame code="ECO" title="Economic calendar" right={<SourcePill meta={ecoMeta} />}>
      <div className="space-y-3 p-2">
        <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
          {(eco?.series ?? []).map((series) => (
            <div key={series.id} className="border border-border p-2">
              <div className="text-[10px] uppercase text-dim">{series.name}</div>
              <div className="text-[16px]">{print(series.value, series.unit)}</div>
              <div className="flex items-center justify-between">
                <span className={toneClass(toneOf(series.change))}>{formatSigned(series.change, 2)}</span>
                <Sparkline values={series.spark} up={(series.change ?? 0) >= 0} />
              </div>
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-1">
          {["ALL", "CPI", "LABOR", "RATES", "PMI"].map((item) => (
            <button key={item} type="button" onClick={() => setCategory(item)} className={`px-2 py-1 text-[10px] ${category === item ? "bg-amber text-background" : "text-muted"}`}>
              {item}
            </button>
          ))}
        </div>
        <div className="overflow-auto">
          <table className="w-full min-w-[720px] text-[11px]">
            <thead className="text-dim">
              <tr>
                {["Date", "Time", "Region", "Event", "Consensus", "Actual", "Prior", "Surprise"].map((label) => (
                  <th key={label} className="px-2 py-1 text-left font-normal">{label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {events.map((event) => {
                const delta = surprise(event);
                return (
                  <tr key={event.id} className="border-t border-border">
                    <td className="px-2 py-1">{event.date}</td>
                    <td className="px-2 py-1 text-muted">{event.time}</td>
                    <td className="px-2 py-1">{event.region}</td>
                    <td className="px-2 py-1">
                      {event.event} {event.importance === "high" ? <span className="text-amber">●</span> : null}
                    </td>
                    <td className="px-2 py-1" title={event.consensusSample ? "Sample desk consensus, not a licensed survey." : ""}>
                      {print(event.consensus, event.unit)}
                      {event.consensusSample ? <span className="ml-1 text-[9px] text-amber">SMP</span> : null}
                    </td>
                    <td className="px-2 py-1">
                      {print(event.actual, event.unit)}
                      {event.actualSample ? <span className="ml-1 text-[9px] text-amber">SMP</span> : null}
                    </td>
                    <td className="px-2 py-1 text-muted">{print(event.prior, event.unit)}</td>
                    <td className={`px-2 py-1 ${toneClass(toneOf(delta))}`}>{delta == null ? "—" : formatSigned(delta, event.unit === "k" ? 0 : 2)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="px-1 text-[10px] leading-relaxed text-dim">{eco?.note}</p>
      </div>
    </PanelFrame>
  );
}
