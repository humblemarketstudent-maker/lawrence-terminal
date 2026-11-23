import { useState } from "react";
import { useTerminal } from "../context/TerminalContext.tsx";
import { downloadCsv } from "../lib/csv.ts";
import { formatStatement, toneClass, toneOf, yoy } from "../lib/format.ts";
import type { LineItem } from "../types.ts";
import { EmptyNote, PanelFrame, SourcePill } from "./bits.tsx";
import { Button } from "./ui/button.tsx";
import { TabContent, TabList, TabTrigger, TabsRoot } from "./ui/tabs.tsx";

type Mode = "level" | "yoy" | "both";

function Table({ lines, periods, mode }: { lines: LineItem[]; periods: string[]; mode: Mode }) {
  return (
    <div className="overflow-auto">
      <table className="w-full min-w-[640px] border-collapse text-[11px]">
        <thead>
          <tr className="text-dim">
            <th className="sticky left-0 bg-panel px-2 py-1 text-left font-normal">Line</th>
            {periods.map((period) => (
              <th key={period} className="px-2 py-1 text-right font-normal">{period}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {lines.map((line) => {
            const changes = yoy(line.values);
            return (
              <tr key={line.key} className="border-t border-border">
                <td className={`sticky left-0 bg-panel px-2 py-1 ${line.bold ? "text-foreground" : "text-muted"}`} style={{ paddingLeft: 8 + line.indent * 12 }}>
                  {line.label}
                </td>
                {line.values.map((value, index) => {
                  const change = changes[index];
                  const shown = mode === "yoy" ? change : value;
                  const unit = mode === "yoy" ? "percent" : line.unit;
                  return (
                    <td key={`${line.key}-${index}`} className={`px-2 py-1 text-right ${mode === "yoy" ? toneClass(toneOf(change)) : value != null && value < 0 ? "text-down" : ""}`}>
                      {formatStatement(shown, unit)}
                      {mode === "both" ? <div className={`text-[9px] ${toneClass(toneOf(change))}`}>{formatStatement(change, "percent")}</div> : null}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function Financials() {
  const { statements, statementsMeta, symbol, profile } = useTerminal();
  const [tab, setTab] = useState("income");
  const [mode, setMode] = useState<Mode>("both");
  if (!statements) return <PanelFrame code="FA" title={symbol}><EmptyNote>Loading statements.</EmptyNote></PanelFrame>;
  const book: Record<string, LineItem[]> = {
    income: statements.income,
    balance: statements.balance,
    cashflow: statements.cashflow,
    ratios: statements.ratios,
  };
  const lines = book[tab] ?? [];
  return (
    <PanelFrame
      code="FA"
      title={`${symbol} · ${statements.currency} millions`}
      right={
        <div className="flex items-center gap-1">
          <SourcePill meta={statementsMeta} />
          {(["level", "yoy", "both"] as Mode[]).map((item) => (
            <Button key={item} variant={mode === item ? "default" : "ghost"} onClick={() => setMode(item)}>
              {item}
            </Button>
          ))}
          <Button
            variant="outline"
            onClick={() =>
              downloadCsv(
                `${symbol}-${tab}.csv`,
                ["Line", ...statements.periods],
                lines.map((line) => [line.label, ...(mode === "yoy" ? yoy(line.values) : line.values).map((value) => (value == null ? "" : value))]),
              )
            }
          >
            CSV
          </Button>
        </div>
      }
    >
      {!statements.applicable ? <EmptyNote>{statements.notes[0]}</EmptyNote> : (
        <TabsRoot value={tab} onValueChange={setTab} className="flex h-full min-h-0 flex-col">
          <TabList>
            <TabTrigger value="income">Income</TabTrigger>
            <TabTrigger value="balance">Balance</TabTrigger>
            <TabTrigger value="cashflow">Cash flow</TabTrigger>
            <TabTrigger value="ratios">Ratios</TabTrigger>
          </TabList>
          <TabContent value={tab} className="min-h-0 flex-1 overflow-auto">
            {lines.length === 0 ? <EmptyNote>This statement was not returned for {symbol}.</EmptyNote> : <Table lines={lines} periods={statements.periods} mode={mode} />}
            <div className="space-y-1 px-3 py-3 text-[10px] leading-relaxed text-dim">
              {statements.notes.map((note) => <p key={note}>{note}</p>)}
              {profile?.sample ? <p>Multiples on the tear sheet can refresh independently of these annual lines.</p> : null}
            </div>
          </TabContent>
        </TabsRoot>
      )}
    </PanelFrame>
  );
}
