import { Component, useEffect, useState, type ReactNode } from "react";
import { Group, Panel, Separator } from "react-resizable-panels";
import { useTerminal } from "../context/TerminalContext.tsx";
import { ChartPanel } from "./ChartPanel.tsx";
import { EcoPanel } from "./EcoPanel.tsx";
import { FilingsPanel } from "./FilingsPanel.tsx";
import { Financials } from "./Financials.tsx";
import { NewsWire } from "./NewsWire.tsx";
import { TearSheet } from "./TearSheet.tsx";
import { Watchlist } from "./Watchlist.tsx";
import { WeiPanel } from "./WeiPanel.tsx";

class PanelError extends Component<{ name: string; children: ReactNode }, { message: string | null }> {
  state = { message: null as string | null };

  static getDerivedStateFromError(error: Error) {
    return { message: error.message };
  }

  render() {
    if (this.state.message) {
      return <div className="p-3 text-[12px] text-down">{this.props.name} failed: {this.state.message}</div>;
    }
    return this.props.children;
  }
}

function Main() {
  const { func } = useTerminal();
  const panel = (() => {
    if (func === "GP") return <ChartPanel />;
    if (func === "FA") return <Financials />;
    if (func === "N") return <NewsWire mode="full" />;
    if (func === "WEI") return <WeiPanel />;
    if (func === "ECO") return <EcoPanel />;
    if (func === "FIL") return <FilingsPanel />;
    return <TearSheet />;
  })();
  return <PanelError name={func}>{panel}</PanelError>;
}

function Secondary() {
  const { func } = useTerminal();
  if (func === "WEI") return <EcoPanel />;
  if (func === "ECO") return <WeiPanel />;
  if (func === "N") return <FilingsPanel />;
  if (func === "GP") return <TearSheet />;
  return <FilingsPanel />;
}

function useMobile() {
  const [mobile, setMobile] = useState(() => window.matchMedia("(max-width: 900px)").matches);
  useEffect(() => {
    const query = window.matchMedia("(max-width: 900px)");
    const onChange = () => setMobile(query.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);
  return mobile;
}

export function Workspace() {
  const { layout, func } = useTerminal();
  const mobile = useMobile();
  const [pane, setPane] = useState<"desk" | "watch" | "news">("desk");
  if (mobile) {
    return (
      <div className="flex h-full min-h-0 flex-col">
        <div className="min-h-0 flex-1">
          {pane === "watch" ? <Watchlist /> : null}
          {pane === "desk" ? <Main /> : null}
          {pane === "news" ? <NewsWire mode="full" /> : null}
        </div>
        <nav className="grid h-10 shrink-0 grid-cols-3 border-t border-border text-[10px] uppercase tracking-wide">
          {(["watch", "desk", "news"] as const).map((item) => (
            <button key={item} type="button" onClick={() => setPane(item)} className={pane === item ? "text-amber" : "text-muted"}>
              {item}
            </button>
          ))}
        </nav>
      </div>
    );
  }
  if (layout === 1) {
    return (
      <div className="h-full">
        <Main />
      </div>
    );
  }
  if (layout === 2) {
    return (
      <Group orientation="horizontal" className="h-full" style={{ height: "100%" }} id="layout-2">
        <Panel id="watch" defaultSize="24%" minSize="16%" className="h-full min-h-0">
          <Watchlist />
        </Panel>
        <Separator className="w-1" />
        <Panel id="main" defaultSize="76%" minSize="40%" className="h-full min-h-0">
          <Main />
        </Panel>
      </Group>
    );
  }
  if (layout === 4) {
    return (
      <Group orientation="vertical" className="h-full" style={{ height: "100%" }} id="layout-4">
        <Panel id="top" defaultSize="58%" minSize="30%" className="h-full min-h-0">
          <Group orientation="horizontal" className="h-full" style={{ height: "100%" }} id="layout-4-top">
            <Panel id="watch" defaultSize="28%" minSize="16%" className="h-full min-h-0"><Watchlist /></Panel>
            <Separator className="w-1" />
            <Panel id="main" defaultSize="72%" minSize="36%" className="h-full min-h-0"><Main /></Panel>
          </Group>
        </Panel>
        <Separator className="h-1" />
        <Panel id="bottom" defaultSize="42%" minSize="22%" className="h-full min-h-0">
          <Group orientation="horizontal" className="h-full" style={{ height: "100%" }} id="layout-4-bottom">
            <Panel id="news" defaultSize="50%" minSize="24%" className="h-full min-h-0"><NewsWire mode="rail" /></Panel>
            <Separator className="w-1" />
            <Panel id="secondary" defaultSize="50%" minSize="24%" className="h-full min-h-0"><Secondary /></Panel>
          </Group>
        </Panel>
      </Group>
    );
  }
  return (
    <Group orientation="horizontal" className="h-full" style={{ height: "100%" }} id="layout-3">
      <Panel id="watch" defaultSize="22%" minSize="15%" className="h-full min-h-0"><Watchlist /></Panel>
      <Separator className="w-1" />
      <Panel id="main" defaultSize="54%" minSize="34%" className="h-full min-h-0"><Main /></Panel>
      <Separator className="w-1" />
      <Panel id="rail" defaultSize="24%" minSize="16%" className="h-full min-h-0">
        {func === "N" ? <FilingsPanel /> : <NewsWire mode="rail" />}
      </Panel>
    </Group>
  );
}
