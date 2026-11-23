export type SourceKind = "live" | "cache" | "fixture";

export interface Meta {
  source: SourceKind;
  provider: string;
  asOf: string;
  stale: boolean;
  warning?: string | null;
}

export interface Section<T> {
  data: T;
  meta: Meta;
}

export interface Quote {
  symbol: string;
  name: string;
  label: string;
  assetClass: string;
  currency: string;
  exchange: string;
  price: number | null;
  change: number | null;
  changePct: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  previousClose: number | null;
  volume: number | null;
  avgVolume30d: number | null;
  volumeRatio: number | null;
  week52High: number | null;
  week52Low: number | null;
  marketCap: number | null;
  sparkline: number[];
  status: "ok" | "unavailable";
  sample: boolean;
  asOf: string;
}

export interface Bar {
  time: number | string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface History {
  symbol: string;
  range: string;
  interval: string;
  bars: Bar[];
  sample: boolean;
}

export interface Executive {
  name: string;
  title: string;
}

export interface Multiple {
  key: string;
  label: string;
  value: number | null;
  unit: string;
}

export interface PeerRow {
  symbol: string;
  name: string;
  label: string;
  marketCap: number | null;
  trailingPE: number | null;
  forwardPE: number | null;
  evEbitda: number | null;
  priceBook: number | null;
  revenueGrowth: number | null;
  ytd: number | null;
}

export interface AnalystView {
  recommendation: string | null;
  targetLow: number | null;
  targetMean: number | null;
  targetHigh: number | null;
  numAnalysts: number | null;
}

export interface OptionSnapshot {
  expiry: string;
  underlying: number | null;
  atmStrike: number | null;
  callLast: number | null;
  putLast: number | null;
  callIV: number | null;
  putIV: number | null;
  callOI: number | null;
  putOI: number | null;
  sample: boolean;
}

export interface CompanyProfile {
  symbol: string;
  name: string;
  label: string;
  assetClass: string;
  sector: string | null;
  industry: string | null;
  summary: string;
  website: string | null;
  employees: number | null;
  headquarters: string | null;
  currency: string;
  executives: Executive[];
  multiples: Multiple[];
  analyst: AnalystView | null;
  peers: PeerRow[];
  options: OptionSnapshot | null;
  price: number | null;
  marketCap: number | null;
  enterpriseValue: number | null;
  beta: number | null;
  dividendYield: number | null;
  eps: number | null;
  revenue: number | null;
  netIncome: number | null;
  sample: boolean;
}

export interface LineItem {
  key: string;
  label: string;
  values: Array<number | null>;
  unit: string;
  bold: boolean;
  indent: number;
}

export interface Statements {
  symbol: string;
  currency: string;
  periods: string[];
  periodEnds: string[];
  income: LineItem[];
  balance: LineItem[];
  cashflow: LineItem[];
  ratios: LineItem[];
  notes: string[];
  sample: boolean;
  applicable: boolean;
}

export interface NewsItem {
  id: string;
  headline: string;
  source: string;
  url: string;
  publishedAt: string;
  summary: string;
  tickers: string[];
  assetClass: string;
  sentiment: "BULLISH" | "BEARISH" | "NEUTRAL";
  impact: number;
  breaking: boolean;
  keywords: string[];
  sample: boolean;
}

export interface Filing {
  symbol: string;
  form: string;
  filed: string;
  description: string;
  accession: string | null;
  url: string;
  insider: string | null;
  sample: boolean;
}

export interface MacroPoint {
  id: string;
  symbol: string | null;
  name: string;
  group: "equity" | "rate" | "fx" | "commodity" | "crypto";
  value: number | null;
  change: number | null;
  changePct: number | null;
  changeBp: number | null;
  unit: string;
  spark: number[];
  sample: boolean;
}

export interface YieldPoint {
  tenor: string;
  years: number;
  value: number | null;
}

export interface WeiBoard {
  points: MacroPoint[];
  curve: YieldPoint[];
  spread2s10s: number | null;
  spreadChangeBp: number | null;
}

export interface EcoEvent {
  id: string;
  date: string;
  time: string;
  region: string;
  event: string;
  category: "CPI" | "LABOR" | "RATES" | "PMI" | "OTHER";
  importance: "high" | "medium";
  consensus: number | null;
  actual: number | null;
  prior: number | null;
  unit: string;
  consensusSample: boolean;
  actualSample: boolean;
}

export interface EcoSeries {
  id: string;
  name: string;
  value: number | null;
  unit: string;
  change: number | null;
  spark: number[];
}

export interface EcoBoard {
  events: EcoEvent[];
  series: EcoSeries[];
  note: string;
}

export interface Brief {
  generatedAt: string;
  title: string;
  markdown: string;
  sample: boolean;
}

export interface SearchHit {
  symbol: string;
  name: string;
  assetClass: string;
  exchange: string;
  label: string;
}

export interface SymbolBundle {
  symbol: string;
  profile: Section<CompanyProfile>;
  statements: Section<Statements>;
  history: Section<History>;
  filings: Section<Filing[]>;
  news: Section<NewsItem[]>;
}

export interface Providers {
  market: string;
  macro: string;
  news: string;
  filings: string;
  live: boolean;
  snapshotAsOf: string | null;
  keys: Record<string, boolean>;
  cache: { entries: number; fresh: number };
}

export interface DashboardRow {
  name: string;
  symbol: string | null;
  group: string;
  assetClass: string;
  price: number | null;
  change: number | null;
  changePct: number | null;
  previousClose: number | null;
  currency: string | null;
  session: string | null;
  status: "ok" | "unavailable" | "pending";
  reason: string | null;
  provider: string | null;
  link: boolean;
}

export interface MoverRow {
  symbol: string;
  name: string;
  label: string;
  price: number | null;
  change: number | null;
  changePct: number | null;
  volume: number | null;
  currency: string;
  assetClass: string;
}

export interface Movers {
  active: MoverRow[];
  rise: MoverRow[];
  drop: MoverRow[];
  activity: "volume";
  activityNote: string;
  changeNote: string;
  universe: number;
  attempted: number;
  quoted: number;
  ready: boolean;
}

export interface DashboardBoard {
  strip: DashboardRow[];
  movers: Movers;
  fx: DashboardRow[];
}

export interface Bootstrap {
  quotes: Section<Quote[]>;
  news: Section<NewsItem[]>;
  wei: Section<WeiBoard>;
  eco: Section<EcoBoard>;
  bundle: SymbolBundle;
  serverTime: string;
  providers: Providers;
}

export type FuncCode = "DES" | "GP" | "FA" | "N" | "FIL" | "WEI" | "ECO";
export type LayoutMode = 1 | 2 | 3 | 4;
export type NewsSource = "ALL" | "REUTERS" | "BLOOMBERG" | "WSJ" | "YAHOO";
export type NewsAsset = "ALL" | "Equities" | "Macro/Rates" | "Asia/EM" | "Tech" | "Energy";
