import type { Bootstrap, Brief, DashboardBoard, History, NewsItem, Quote, SearchHit, Section, SymbolBundle, WeiBoard, EcoBoard, Filing } from "../types.ts";

const BASE = import.meta.env.VITE_API_BASE ?? "";

async function getJSON<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE}${path}`);
  if (!response.ok) {
    throw new Error(`${response.status} ${path}`);
  }
  return (await response.json()) as T;
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`${response.status} ${path}`);
  return (await response.json()) as T;
}

export const api = {
  bootstrap: (symbol: string, range: string) =>
    getJSON<Bootstrap>(`/api/bootstrap?symbol=${encodeURIComponent(symbol)}&range=${encodeURIComponent(range)}`),
  symbol: (symbol: string, range: string, force = false) =>
    getJSON<SymbolBundle>(`/api/symbol/${encodeURIComponent(symbol)}?range=${encodeURIComponent(range)}&force=${force ? "true" : "false"}`),
  quotes: async (symbols: string[]) => {
    const size = 80;
    const sections: Section<Quote[]>[] = [];
    for (let i = 0; i < symbols.length; i += size) {
      const part = symbols.slice(i, i + size);
      sections.push(await getJSON<Section<Quote[]>>(`/api/quotes?symbols=${encodeURIComponent(part.join(","))}`));
    }
    return {
      data: sections.flatMap((section) => section.data ?? []),
      meta: sections[0]?.meta,
    } as Section<Quote[]>;
  },
  history: (symbol: string, range: string) =>
    getJSON<Section<History>>(`/api/history/${encodeURIComponent(symbol)}?range=${encodeURIComponent(range)}`),
  news: (symbol?: string) => getJSON<Section<NewsItem[]>>(`/api/news${symbol ? `?symbol=${encodeURIComponent(symbol)}` : ""}`),
  dashboard: () => getJSON<Section<DashboardBoard>>("/api/dashboard"),
  wei: () => getJSON<Section<WeiBoard>>("/api/wei"),
  eco: () => getJSON<Section<EcoBoard>>("/api/eco"),
  filings: (symbol: string) => getJSON<Section<Filing[]>>(`/api/filings/${encodeURIComponent(symbol)}`),
  search: async (q: string) => (await getJSON<{ results: SearchHit[] }>(`/api/search?q=${encodeURIComponent(q)}`)).results,
  refresh: (symbols: string[], scope = "all", range = "1Y") => postJSON<{ ok: boolean }>("/api/refresh", { symbols, scope, range }),
  brief: (symbols: string[]) => postJSON<Brief>("/api/brief", { symbols }),
};
