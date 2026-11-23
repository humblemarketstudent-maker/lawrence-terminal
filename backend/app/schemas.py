"""API models. Field names are camelCase to match the TypeScript client."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Meta(BaseModel):
    source: Literal["live", "cache", "fixture"]
    provider: str
    asOf: str
    stale: bool = False
    warning: str | None = None


class Quote(BaseModel):
    symbol: str
    name: str
    label: str
    assetClass: str
    currency: str
    exchange: str
    price: float | None = None
    change: float | None = None
    changePct: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    previousClose: float | None = None
    volume: float | None = None
    avgVolume30d: float | None = None
    volumeRatio: float | None = None
    week52High: float | None = None
    week52Low: float | None = None
    marketCap: float | None = None
    sparkline: list[float] = Field(default_factory=list)
    status: Literal["ok", "unavailable"] = "ok"
    sample: bool = False
    asOf: str


class Bar(BaseModel):
    time: int | str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0


class History(BaseModel):
    symbol: str
    range: str
    interval: str
    bars: list[Bar]
    sample: bool = False


class Executive(BaseModel):
    name: str
    title: str


class Multiple(BaseModel):
    key: str
    label: str
    value: float | None
    unit: str


class PeerRow(BaseModel):
    symbol: str
    name: str
    label: str
    marketCap: float | None = None
    trailingPE: float | None = None
    forwardPE: float | None = None
    evEbitda: float | None = None
    priceBook: float | None = None
    revenueGrowth: float | None = None
    ytd: float | None = None


class AnalystView(BaseModel):
    recommendation: str | None = None
    targetLow: float | None = None
    targetMean: float | None = None
    targetHigh: float | None = None
    numAnalysts: int | None = None


class OptionSnapshot(BaseModel):
    expiry: str
    underlying: float | None = None
    atmStrike: float | None = None
    callLast: float | None = None
    putLast: float | None = None
    callIV: float | None = None
    putIV: float | None = None
    callOI: float | None = None
    putOI: float | None = None
    sample: bool = False


class CompanyProfile(BaseModel):
    symbol: str
    name: str
    label: str
    assetClass: str
    sector: str | None = None
    industry: str | None = None
    summary: str
    website: str | None = None
    employees: int | None = None
    headquarters: str | None = None
    currency: str
    executives: list[Executive] = Field(default_factory=list)
    multiples: list[Multiple] = Field(default_factory=list)
    analyst: AnalystView | None = None
    peers: list[PeerRow] = Field(default_factory=list)
    options: OptionSnapshot | None = None
    price: float | None = None
    marketCap: float | None = None
    enterpriseValue: float | None = None
    beta: float | None = None
    dividendYield: float | None = None
    eps: float | None = None
    revenue: float | None = None
    netIncome: float | None = None
    sample: bool = False


class LineItem(BaseModel):
    key: str
    label: str
    values: list[float | None]
    unit: str
    bold: bool = False
    indent: int = 0


class Statements(BaseModel):
    symbol: str
    currency: str
    periods: list[str]
    periodEnds: list[str]
    income: list[LineItem]
    balance: list[LineItem]
    cashflow: list[LineItem]
    ratios: list[LineItem]
    notes: list[str] = Field(default_factory=list)
    sample: bool = False
    applicable: bool = True


class NewsItem(BaseModel):
    id: str
    headline: str
    source: str
    url: str
    publishedAt: str
    summary: str
    tickers: list[str] = Field(default_factory=list)
    assetClass: str
    sentiment: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    impact: int
    breaking: bool = False
    keywords: list[str] = Field(default_factory=list)
    sample: bool = False


class Filing(BaseModel):
    symbol: str
    form: str
    filed: str
    description: str
    accession: str | None = None
    url: str
    insider: str | None = None
    sample: bool = False


class MacroPoint(BaseModel):
    id: str
    symbol: str | None = None
    name: str
    group: Literal["equity", "rate", "fx", "commodity", "crypto"]
    value: float | None = None
    change: float | None = None
    changePct: float | None = None
    changeBp: float | None = None
    unit: str
    spark: list[float] = Field(default_factory=list)
    sample: bool = False


class YieldPoint(BaseModel):
    tenor: str
    years: float
    value: float | None = None


class WeiBoard(BaseModel):
    points: list[MacroPoint]
    curve: list[YieldPoint]
    spread2s10s: float | None = None
    spreadChangeBp: float | None = None


class EcoEvent(BaseModel):
    id: str
    date: str
    time: str
    region: str
    event: str
    category: Literal["CPI", "LABOR", "RATES", "PMI", "OTHER"]
    importance: Literal["high", "medium"]
    consensus: float | None = None
    actual: float | None = None
    prior: float | None = None
    unit: str
    consensusSample: bool = False
    actualSample: bool = False


class EcoSeries(BaseModel):
    id: str
    name: str
    value: float | None = None
    unit: str
    change: float | None = None
    spark: list[float] = Field(default_factory=list)


class EcoBoard(BaseModel):
    events: list[EcoEvent]
    series: list[EcoSeries]
    note: str


class Brief(BaseModel):
    generatedAt: str
    title: str
    markdown: str
    sample: bool = False


class SearchHit(BaseModel):
    symbol: str
    name: str
    assetClass: str
    exchange: str
    label: str


class QuoteSection(BaseModel):
    data: list[Quote]
    meta: Meta


class HistorySection(BaseModel):
    data: History
    meta: Meta


class ProfileSection(BaseModel):
    data: CompanyProfile
    meta: Meta


class StatementsSection(BaseModel):
    data: Statements
    meta: Meta


class NewsSection(BaseModel):
    data: list[NewsItem]
    meta: Meta


class FilingsSection(BaseModel):
    data: list[Filing]
    meta: Meta


class WeiSection(BaseModel):
    data: WeiBoard
    meta: Meta


class EcoSection(BaseModel):
    data: EcoBoard
    meta: Meta


class SymbolBundle(BaseModel):
    symbol: str
    profile: ProfileSection
    statements: StatementsSection
    history: HistorySection
    filings: FilingsSection
    news: NewsSection


class DashboardRow(BaseModel):
    name: str
    symbol: str | None = None
    group: str
    assetClass: str
    price: float | None = None
    change: float | None = None
    changePct: float | None = None
    previousClose: float | None = None
    currency: str | None = None
    session: str | None = None
    status: Literal["ok", "unavailable", "pending"] = "pending"
    reason: str | None = None
    provider: str | None = None
    link: bool = False


class MoverRow(BaseModel):
    symbol: str
    name: str
    label: str
    price: float | None = None
    change: float | None = None
    changePct: float | None = None
    volume: float | None = None
    currency: str
    assetClass: str = "equity"


class Movers(BaseModel):
    active: list[MoverRow] = Field(default_factory=list)
    rise: list[MoverRow] = Field(default_factory=list)
    drop: list[MoverRow] = Field(default_factory=list)
    activity: Literal["volume"] = "volume"
    activityNote: str = "Last session share volume. Names with no volume print are omitted."
    changeNote: str = "Percent change versus the previous close."
    universe: int = 0
    attempted: int = 0
    quoted: int = 0
    ready: bool = False


class DashboardBoard(BaseModel):
    strip: list[DashboardRow]
    movers: Movers
    fx: list[DashboardRow]


class DashboardSection(BaseModel):
    data: DashboardBoard
    meta: Meta


class BootstrapResponse(BaseModel):
    quotes: QuoteSection
    news: NewsSection
    wei: WeiSection
    eco: EcoSection
    bundle: SymbolBundle
    serverTime: str
    providers: dict
