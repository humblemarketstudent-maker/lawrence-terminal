import { useState } from "react";
import { useTerminal } from "../context/TerminalContext.tsx";
import { Button } from "./ui/button.tsx";
import { Modal } from "./ui/dialog.tsx";

export function BriefDialog() {
  const { briefOpen, setBriefOpen, brief, briefLoading, openBrief } = useTerminal();
  const [copied, setCopied] = useState(false);
  return (
    <Modal open={briefOpen} onOpenChange={setBriefOpen} title="MORNING BRIEF">
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <Button variant="amber" onClick={() => void openBrief()} disabled={briefLoading}>
          {briefLoading ? "Generating" : "Regenerate"}
        </Button>
        <Button
          variant="outline"
          onClick={() => {
            if (!brief) return;
            void navigator.clipboard.writeText(brief.markdown).then(() => {
              setCopied(true);
              window.setTimeout(() => setCopied(false), 1200);
            });
          }}
        >
          {copied ? "Copied" : "Copy"}
        </Button>
        {brief?.sample ? <span className="text-[10px] text-amber">Includes fixture data</span> : <span className="text-[10px] text-up">Desk cache</span>}
      </div>
      <pre className="whitespace-pre-wrap px-4 py-3 text-[12px] leading-relaxed text-foreground">{brief?.markdown ?? "Generating the note…"}</pre>
    </Modal>
  );
}

export function HelpDialog() {
  const { helpOpen, setHelpOpen } = useTerminal();
  const rows = [
    ["/", "Focus the command bar"],
    ["Enter", "Run AAPL US <DES>, <WEI>, <ECO>, <BRIEF>"],
    ["1 2 3 4", "Switch workspace layout"],
    ["R", "Force-refresh feeds"],
    ["Esc", "Close the reader, brief, or help"],
    ["?", "Show this card"],
    ["MKT", "Benchmarks, equity movers, and G10 FX sit under the command bar"],
  ];
  return (
    <Modal open={helpOpen} onOpenChange={setHelpOpen} title="KEYS">
      <table className="w-full text-[12px]">
        <tbody>
          {rows.map(([key, help]) => (
            <tr key={key} className="border-b border-border">
              <td className="px-3 py-2 text-amber">{key}</td>
              <td className="px-3 py-2 text-muted">{help}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Modal>
  );
}
