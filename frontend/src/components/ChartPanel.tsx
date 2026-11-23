import { useEffect, useMemo, useRef, useState } from "react";
import {
  AreaSeries,
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type SeriesType,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import { useTerminal } from "../context/TerminalContext.tsx";
import { api } from "../lib/api.ts";
import { formatCompact, formatPrice } from "../lib/format.ts";
import { ema, macd, rsi, sma } from "../lib/indicators.ts";
import type { Bar } from "../types.ts";
import { EmptyNote, PanelFrame, SourcePill } from "./bits.tsx";
import { Button } from "./ui/button.tsx";
import { Input } from "./ui/input.tsx";

const FRAMES = ["1D", "5D", "1M", "6M", "YTD", "1Y", "5Y"];

function asTime(value: number | string): Time {
  return (typeof value === "number" ? (value as UTCTimestamp) : value) as Time;
}

function lineData(bars: Bar[], series: Array<number | null>) {
  return bars.flatMap((bar, index) => {
    const value = series[index];
    return value == null ? [] : [{ time: asTime(bar.time), value }];
  });
}

function vwap(bars: Bar[]) {
  let pv = 0;
  let volume = 0;
  let day = "";
  const out: Array<{ time: Time; value: number }> = [];
  for (const bar of bars) {
    const key = typeof bar.time === "number" ? new Date(bar.time * 1000).toISOString().slice(0, 10) : String(bar.time).slice(0, 10);
    if (typeof bar.time === "number" && key !== day) {
      pv = 0;
      volume = 0;
      day = key;
    }
    if (!bar.volume) continue;
    const typical = (bar.high + bar.low + bar.close) / 3;
    pv += typical * bar.volume;
    volume += bar.volume;
    out.push({ time: asTime(bar.time), value: pv / volume });
  }
  return out;
}

function percent(bars: Bar[]) {
  const base = bars[0]?.close;
  if (!base) return [];
  return bars.map((bar) => ({ time: asTime(bar.time), value: (bar.close / base - 1) * 100 }));
}

export function ChartPanel() {
  const { symbol, activeQuote, history, historyMeta, timeframe, setTimeframe, profile } = useTerminal();
  const host = useRef<HTMLDivElement>(null);
  const [style, setStyle] = useState<"candle" | "line">("candle");
  const [sma20, setSma20] = useState(true);
  const [sma50, setSma50] = useState(true);
  const [sma200, setSma200] = useState(false);
  const [showVwap, setShowVwap] = useState(false);
  const [showRsi, setShowRsi] = useState(false);
  const [showMacd, setShowMacd] = useState(false);
  const [showVolume, setShowVolume] = useState(true);
  const [compare, setCompare] = useState("");
  const [compareBars, setCompareBars] = useState<Bar[] | null>(null);
  const [legend, setLegend] = useState<Bar | null>(null);
  const bars = useMemo(() => (history?.symbol === symbol ? history.bars : []), [history, symbol]);
  const activeCompare = compare.trim() ? compareBars : null;

  useEffect(() => {
    const next = compare.trim().toUpperCase();
    if (!next) return;
    let cancelled = false;
    api
      .history(next, timeframe)
      .then((section) => {
        if (!cancelled) setCompareBars(section.data.bars);
      })
      .catch(() => {
        if (!cancelled) setCompareBars([]);
      });
    return () => {
      cancelled = true;
    };
  }, [compare, timeframe]);

  const last = bars[bars.length - 1] ?? null;
  const readout = legend ?? last;

  useEffect(() => {
    const node = host.current;
    if (!node || bars.length === 0) return;
    const chart: IChartApi = createChart(node, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "#131722" },
        textColor: "#8B909C",
        fontFamily: "JetBrains Mono, ui-monospace, monospace",
        fontSize: 11,
      },
      grid: { vertLines: { color: "#1E222D" }, horzLines: { color: "#1E222D" } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "#1E222D" },
      timeScale: {
        borderColor: "#1E222D",
        timeVisible: history?.interval.endsWith("m") || history?.interval.endsWith("h") || false,
        secondsVisible: false,
      },
    });

    const comparing = Boolean(compare.trim() && activeCompare && activeCompare.length > 1);
    let primary: ISeriesApi<SeriesType> | null = null;
    if (comparing && compareBars) {
      const base = chart.addSeries(LineSeries, { color: "#FF9900", lineWidth: 2, priceFormat: { type: "custom", formatter: (price: number) => `${price.toFixed(2)}%` } });
      const other = chart.addSeries(LineSeries, { color: "#E6E8EE", lineWidth: 2, priceFormat: { type: "custom", formatter: (price: number) => `${price.toFixed(2)}%` } });
      base.setData(percent(bars));
      other.setData(percent(activeCompare ?? []));
      primary = base;
    } else if (style === "line") {
      const series = chart.addSeries(AreaSeries, {
        lineColor: "#FF9900",
        topColor: "rgba(255,153,0,0.28)",
        bottomColor: "rgba(255,153,0,0.02)",
        lineWidth: 2,
      });
      series.setData(bars.map((bar) => ({ time: asTime(bar.time), value: bar.close })));
      primary = series;
    } else {
      const series = chart.addSeries(CandlestickSeries, {
        upColor: "#00C853",
        downColor: "#FF3D00",
        borderVisible: false,
        wickUpColor: "#00C853",
        wickDownColor: "#FF3D00",
      });
      series.setData(bars.map((bar) => ({ time: asTime(bar.time), open: bar.open, high: bar.high, low: bar.low, close: bar.close })));
      primary = series;
    }

    if (showVolume && !comparing) {
      const volume = chart.addSeries(HistogramSeries, {
        priceFormat: { type: "volume" },
        priceScaleId: "volume",
        priceLineVisible: false,
        lastValueVisible: false,
      });
      volume.setData(
        bars.map((bar) => ({
          time: asTime(bar.time),
          value: bar.volume,
          color: bar.close >= bar.open ? "rgba(0,200,83,0.45)" : "rgba(255,61,0,0.45)",
        })),
      );
      chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.78, bottom: 0 } });
      primary?.priceScale().applyOptions({ scaleMargins: { top: 0.08, bottom: 0.28 } });
    }

    const closes = bars.map((bar) => bar.close);
    const addLine = (values: Array<number | null>, color: string) => {
      const series = chart.addSeries(LineSeries, { color, lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
      series.setData(lineData(bars, values));
    };
    if (!comparing && sma20) addLine(sma(closes, 20), "#FF9900");
    if (!comparing && sma50) addLine(sma(closes, 50), "#E6E8EE");
    if (!comparing && sma200) addLine(sma(closes, 200), "#8B909C");
    if (!comparing && showVwap) {
      const series = chart.addSeries(LineSeries, { color: "#C6A15B", lineWidth: 1, lineStyle: 2, priceLineVisible: false, lastValueVisible: false });
      series.setData(vwap(bars));
    }

    let pane = 1;
    if (!comparing && showRsi) {
      const series = chart.addSeries(LineSeries, { color: "#FF9900", lineWidth: 1, priceLineVisible: false }, pane);
      series.setData(lineData(bars, rsi(closes)));
      series.createPriceLine({ price: 70, color: "#FF3D00", lineStyle: 2, title: "70" });
      series.createPriceLine({ price: 30, color: "#00C853", lineStyle: 2, title: "30" });
      chart.panes()[pane]?.setHeight(72);
      pane += 1;
    }
    if (!comparing && showMacd) {
      const osc = macd(closes);
      const signal = ema(osc.macd, 9);
      chart.addSeries(HistogramSeries, { priceLineVisible: false, lastValueVisible: false }, pane).setData(
        bars.map((bar, index) => ({
          time: asTime(bar.time),
          value: osc.hist[index] ?? 0,
          color: (osc.hist[index] ?? 0) >= 0 ? "rgba(0,200,83,0.7)" : "rgba(255,61,0,0.7)",
        })),
      );
      chart.addSeries(LineSeries, { color: "#E6E8EE", lineWidth: 1, priceLineVisible: false, lastValueVisible: false }, pane).setData(lineData(bars, osc.macd));
      chart.addSeries(LineSeries, { color: "#FF9900", lineWidth: 1, priceLineVisible: false, lastValueVisible: false }, pane).setData(lineData(bars, signal));
      chart.panes()[pane]?.setHeight(80);
    }

    chart.timeScale().fitContent();
    const onMove = (param: { time?: Time; seriesData: Map<ISeriesApi<SeriesType>, unknown> }) => {
      if (!primary || !param.time) {
        setLegend(null);
        return;
      }
      const point = param.seriesData.get(primary) as { open?: number; high?: number; low?: number; close?: number; value?: number } | undefined;
      if (!point) return;
      const match = bars.find((bar) => String(bar.time) === String(param.time));
      if (point.open != null && point.close != null) {
        setLegend({
          time: param.time as number | string,
          open: point.open,
          high: point.high ?? point.open,
          low: point.low ?? point.open,
          close: point.close,
          volume: match?.volume ?? 0,
        });
      }
    };
    chart.subscribeCrosshairMove(onMove);
    return () => {
      chart.unsubscribeCrosshairMove(onMove);
      chart.remove();
    };
  }, [bars, style, sma20, sma50, sma200, showVwap, showRsi, showMacd, showVolume, compare, activeCompare, history?.interval]);

  const toggles = useMemo(
    () => [
      ["RSI", showRsi, setShowRsi],
      ["MACD", showMacd, setShowMacd],
      ["SMA20", sma20, setSma20],
      ["SMA50", sma50, setSma50],
      ["SMA200", sma200, setSma200],
      ["VWAP", showVwap, setShowVwap],
      ["VOL", showVolume, setShowVolume],
    ] as const,
    [sma20, sma50, sma200, showVwap, showRsi, showMacd, showVolume],
  );

  return (
    <PanelFrame
      code="GP"
      title={`${activeQuote?.label ?? symbol} · ${profile?.name ?? activeQuote?.name ?? symbol}`}
      right={
        <div className="flex items-center gap-2 text-[11px]">
          {readout ? (
            <span className="hidden text-muted xl:inline">
              O {formatPrice(readout.open)} H {formatPrice(readout.high)} L {formatPrice(readout.low)} C {formatPrice(readout.close)} V {formatCompact(readout.volume, 1)}
            </span>
          ) : null}
          <SourcePill meta={historyMeta} />
        </div>
      }
    >
      <div className="flex h-full min-h-0 flex-col">
        <div className="shrink-0 border-b border-border">
          <div className="flex flex-wrap items-center gap-1 px-2 py-1">
            {FRAMES.map((frame) => (
              <Button key={frame} variant={timeframe === frame ? "default" : "ghost"} onClick={() => setTimeframe(frame)}>
                {frame}
              </Button>
            ))}
            <Button variant={style === "candle" ? "amber" : "ghost"} onClick={() => setStyle("candle")}>
              Candle
            </Button>
            <Button variant={style === "line" ? "amber" : "ghost"} onClick={() => setStyle("line")}>
              Line
            </Button>
            <form
              className="ml-auto flex items-center gap-1"
              onSubmit={(event) => {
                event.preventDefault();
                const form = new FormData(event.currentTarget);
                setCompare(String(form.get("compare") ?? ""));
              }}
            >
              <Input name="compare" defaultValue={compare} placeholder="Compare NVDA" aria-label="Compare symbol" className="h-6 w-28 text-[11px]" />
              <Button type="submit" variant="outline">
                %
              </Button>
            </form>
          </div>
          <div className="flex flex-wrap items-center gap-1 border-t border-border px-2 py-1">
            <span className="pr-1 text-[10px] uppercase tracking-wide text-dim">Studies</span>
            {toggles.map(([label, on, setOn]) => (
              <Button key={label} variant={on ? "amber" : "ghost"} aria-pressed={on} onClick={() => setOn(!on)}>
                {label}
              </Button>
            ))}
          </div>
        </div>
        {compare.trim() ? <div className="px-2 py-1 text-[10px] text-dim">Normalized to percent return from the first bar. {symbol} amber, {compare.toUpperCase()} white.</div> : null}
        {bars.length === 0 ? (
          <EmptyNote>No bars returned for {symbol}. Check the ticker or press R to refresh.</EmptyNote>
        ) : (
          <div className="relative min-h-[280px] flex-1">
            <div ref={host} className="absolute inset-0" />
          </div>
        )}
      </div>
    </PanelFrame>
  );
}
