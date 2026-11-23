"""Snapshot and builtin fixture book. Reads are synchronous and side-effect free."""

from __future__ import annotations

import json
import math
import random
import zlib
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from app.bars import scale_bar, slice_range, ytd_return
from app.schemas import Filing, History, NewsItem, OptionSnapshot, Quote
from app.sentiment import score_text
from app.services.normalize import option_from_dict, peer_row, profile_from_parts, statements_from_blocks
from app.symbols import (
    CATALOG,
    DEFAULT_WATCHLIST,
    NAME_TO_TICKER,
    WEI_SYMBOLS,
    bloomberg_label,
    catalog_row,
    classify,
    currency_for,
    exchange_for,
    name_for,
    peers_for,
)
from app.util import clean_text, iso, stable_id, utcnow

SNAPSHOT_PATH = Path(__file__).resolve().parent / "fixtures" / "snapshot.json"

# Last-resort anchors captured with the public feeds so a missing snapshot still paints.
ANCHORS: dict[str, float] = {
    "AAPL": 342.56,
    "MSFT": 484.52,
    "NVDA": 125.53,
    "GOOGL": 265.29,
    "AMZN": 246.82,
    "META": 560.84,
    "AMD": 424.39,
    "AVGO": 304.41,
    "TSM": 318.71,
    "ORCL": 101.19,
    "CRM": 180.62,
    "BABA": 81.08,
    "SPY": 689.81,
    "QQQ": 608.45,
    "0700.HK": 344.0,
    "9988.HK": 83.35,
    "^GSPC": 6910.39,
    "^IXIC": 22617.73,
    "^DJI": 48147.33,
    "^HSI": 22410.80,
    "^N225": 56436.65,
    "^FTSE": 10346.30,
    "^GDAXI": 24802.78,
    "^TNX": 4.912,
    "DX-Y.NYB": 103.81,
    "CL=F": 83.41,
    "GC=F": 3515.40,
    "BTC-USD": 61002.76,
    "USDHKD=X": 7.8389,
}

FORM_TITLES = {
    "10-K": "Annual report",
    "10-Q": "Quarterly report",
    "8-K": "Current report",
    "4": "Statement of changes in beneficial ownership",
}


def _load_snapshot() -> dict | None:
    if not SNAPSHOT_PATH.exists():
        return None
    try:
        return json.loads(SNAPSHOT_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return None


class FixtureBook:
    def __init__(self) -> None:
        self.raw = _load_snapshot()
        self.as_of = (self.raw or {}).get("asOf") or iso()
        self._daily: dict[str, list[dict]] = {}
        self._intra: dict[str, list[dict]] = {}

    @property
    def provider(self) -> str:
        return "snapshot" if self.raw else "builtin"

    def daily(self, symbol: str) -> list[dict]:
        if symbol not in self._daily:
            rows = ((self.raw or {}).get("daily") or {}).get(symbol)
            if rows:
                self._daily[symbol] = [scale_bar(symbol, row) for row in rows]
            else:
                anchor = ANCHORS.get(symbol)
                self._daily[symbol] = _synthetic_daily(symbol, anchor) if anchor else []
        return self._daily[symbol]

    def intraday(self, symbol: str) -> list[dict]:
        if symbol not in self._intra:
            rows = ((self.raw or {}).get("intraday") or {}).get(symbol) or []
            self._intra[symbol] = [scale_bar(symbol, row) for row in rows]
        return self._intra[symbol]

    def info(self, symbol: str) -> dict:
        payload = ((self.raw or {}).get("info") or {}).get(symbol) or {}
        return dict(payload)

    def quote(self, symbol: str) -> Quote | None:
        snap = ((self.raw or {}).get("quotes") or {}).get(symbol)
        daily = self.daily(symbol)
        if not snap and not daily:
            row = catalog_row(symbol)
            if not row:
                return None
            return _unavailable(symbol)
        price = num_or(snap, "price")
        previous = num_or(snap, "previousClose")
        open_ = num_or(snap, "open")
        high = num_or(snap, "high")
        low = num_or(snap, "low")
        volume = num_or(snap, "volume")
        if len(daily) >= 2:
            last, prior = daily[-1], daily[-2]
            price = last["close"]
            previous = prior["close"]
            open_, high, low, volume = last["open"], last["high"], last["low"], last["volume"]
        elif len(daily) == 1:
            price = daily[-1]["close"]
        if price is None:
            return _unavailable(symbol)
        change = price - previous if previous is not None else num_or(snap, "change")
        change_pct = (change / previous * 100.0) if change is not None and previous else num_or(snap, "changePct")
        window = daily[-252:] if daily else []
        week_high = max((bar["high"] for bar in window), default=num_or(snap, "week52High"))
        week_low = min((bar["low"] for bar in window), default=num_or(snap, "week52Low"))
        vol_window = [bar["volume"] for bar in daily[-30:] if bar.get("volume")]
        avg = (sum(vol_window) / len(vol_window)) if vol_window else num_or(snap, "avgVolume30d")
        spark = [bar["close"] for bar in daily[-32:]] or [float(v) for v in (snap or {}).get("sparkline") or []]
        info = self.info(symbol)
        market_cap = num_or(snap, "marketCap") or _num(info.get("marketCap"))
        ratio = (volume / avg) if volume and avg else None
        return Quote(
            symbol=symbol,
            name=name_for(symbol, info.get("shortName") if isinstance(info.get("shortName"), str) else None),
            label=bloomberg_label(symbol),
            assetClass=classify(symbol),
            currency=currency_for(symbol, info.get("currency") if isinstance(info.get("currency"), str) else num_str(snap, "currency")),
            exchange=exchange_for(symbol),
            price=price,
            change=change,
            changePct=change_pct,
            open=open_,
            high=high,
            low=low,
            previousClose=previous,
            volume=volume,
            avgVolume30d=avg,
            volumeRatio=ratio,
            week52High=week_high if isinstance(week_high, float) else _num(week_high),
            week52Low=week_low if isinstance(week_low, float) else _num(week_low),
            marketCap=market_cap,
            sparkline=spark,
            status="ok",
            sample=True,
            asOf=self.as_of,
        )

    def history(self, symbol: str, range_key: str) -> History:
        bars, interval = slice_range(self.daily(symbol), self.intraday(symbol), range_key)
        return History(symbol=symbol, range=range_key, interval=interval, bars=bars, sample=True)

    def statements(self, symbol: str):
        block = ((self.raw or {}).get("statements") or {}).get(symbol) or {}
        info = self.info(symbol)
        currency = currency_for(symbol, info.get("currency") if isinstance(info.get("currency"), str) else None)
        return statements_from_blocks(
            symbol,
            currency,
            block.get("income"),
            block.get("balance"),
            block.get("cashflow"),
            sample=True,
        )

    def options(self, symbol: str) -> OptionSnapshot | None:
        payload = ((self.raw or {}).get("options") or {}).get(symbol)
        snap = option_from_dict(payload, sample=True)
        if snap and snap.underlying is None:
            quote = self.quote(symbol)
            if quote and quote.price is not None:
                snap.underlying = quote.price
        return snap

    def peers(self, symbol: str):
        rows = []
        for peer in peers_for(symbol):
            quote = self.quote(peer)
            if quote is None or quote.status != "ok":
                continue
            rows.append(
                peer_row(
                    peer,
                    self.info(peer),
                    quote.marketCap,
                    ytd_return(self.daily(peer)),
                    self.statements(peer) if ((self.raw or {}).get("statements") or {}).get(peer) else None,
                )
            )
        return rows

    def profile(self, symbol: str):
        quote = self.quote(symbol)
        price = quote.price if quote else None
        return profile_from_parts(
            symbol,
            self.info(symbol),
            price=price,
            peers=self.peers(symbol),
            statements=self.statements(symbol),
            options=self.options(symbol),
            sample=True,
        )

    def news(self) -> list[NewsItem]:
        raw_items = (self.raw or {}).get("news") or []
        if raw_items:
            return _decorate_news(raw_items, sample=True)
        return _sample_news()

    def filings(self, symbol: str) -> list[Filing]:
        rows = ((self.raw or {}).get("filings") or {}).get(symbol) or []
        if rows:
            return [_filing(symbol, row, sample=True) for row in rows]
        if symbol == "AAPL":
            return _sample_filings()
        return []

    def macro(self) -> dict[str, list[list]]:
        series = (self.raw or {}).get("macro") or {}
        if series:
            return series
        return _sample_macro()

    def symbols_for_desk(self) -> list[str]:
        base = list(dict.fromkeys([*DEFAULT_WATCHLIST, *[symbol for symbol, _, _ in WEI_SYMBOLS]]))
        return base


def _decorate_news(raw_items: list[dict], sample: bool) -> list[NewsItem]:
    items: list[NewsItem] = []
    for row in raw_items:
        original = str(row.get("headline") or "")
        headline = _clean_headline(original)
        if not headline:
            continue
        summary = clean_text(str(row.get("summary") or ""), 500)
        source = _detect_source(original, str(row.get("url") or ""), str(row.get("source") or "WIRE").upper())
        scored = score_text(f"{headline} {summary}")
        tickers = _tickers_in(f"{headline} {summary}")
        published = str(row.get("publishedAt") or iso())
        try:
            moment = datetime.fromisoformat(published.replace("Z", "+00:00"))
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=timezone.utc)
        except ValueError:
            moment = utcnow()
            published = iso(moment)
        age = (utcnow() - moment).total_seconds()
        breaking = "breaking" in headline.lower() or (0 <= age <= 45 * 60)
        items.append(
            NewsItem(
                id=stable_id(source, headline),
                headline=headline,
                source=source,
                url=str(row.get("url") or ""),
                publishedAt=published,
                summary=summary or headline,
                tickers=tickers,
                assetClass=_asset_class(headline, tickers),
                sentiment=scored["sentiment"],
                impact=scored["impact"],
                breaking=breaking,
                keywords=scored["keywords"],
                sample=sample,
            )
        )
    items.sort(key=lambda item: item.publishedAt, reverse=True)
    return _dedup(items)[:80]


def _clean_headline(title: str) -> str:
    text = clean_text(title, 280)
    for suffix in ("Reuters", "Bloomberg", "Bloomberg.com", "WSJ", "Wall Street Journal", "Yahoo Finance", "Yahoo"):
        tail = f" - {suffix}"
        if text.lower().endswith(tail.lower()):
            text = text[: -len(tail)].strip()
    return text


def _detect_source(headline: str, url: str, fallback: str) -> str:
    blob = f"{headline} {url}".lower()
    if "reuters.com" in blob or blob.rstrip().endswith("reuters") or " - reuters" in blob:
        return "REUTERS"
    if "bloomberg.com" in blob or " - bloomberg" in blob:
        return "BLOOMBERG"
    if "wsj.com" in blob or "wall street journal" in blob or " - wsj" in blob:
        return "WSJ"
    if "finance.yahoo.com" in blob or "yahoo finance" in blob or " - yahoo" in blob:
        return "YAHOO"
    if fallback in {"REUTERS", "BLOOMBERG", "WSJ", "YAHOO"}:
        return fallback
    return "WIRE"


def _tickers_in(text: str) -> list[str]:
    found: list[str] = []
    upper = text.upper()
    lowered = text.lower()
    for name, ticker in NAME_TO_TICKER.items():
        if ticker == "MACRO":
            continue
        if name in lowered and ticker not in found:
            found.append(ticker)
    for row in CATALOG:
        symbol = row["symbol"]
        if not symbol.isalpha() or len(symbol) > 5:
            continue
        if f" {symbol} " in f" {upper} " and symbol not in found:
            found.append(symbol)
    return found[:8]


def _asset_class(headline: str, tickers: list[str]) -> str:
    blob = headline.lower()
    if any(word in blob for word in ("oil", "crude", "opec", "wti", "brent", "energy")):
        return "Energy"
    if any(word in blob for word in ("fed", "treasury", "yield", "cpi", "payroll", "fomc", "ecb", "rate", "inflation", "pmi")):
        return "Macro/Rates"
    if any(word in blob for word in ("china", "hong kong", "nikkei", "hang seng", "asia", "tencent", "alibaba", "yen")):
        return "Asia/EM"
    if any(word in blob for word in ("nvidia", "chip", "semiconductor", "apple", "microsoft", "software", "cloud", " ai")):
        return "Tech"
    if any(ticker.endswith(".HK") for ticker in tickers):
        return "Asia/EM"
    return "Equities"


def _dedup(items: list[NewsItem]) -> list[NewsItem]:
    kept: list[NewsItem] = []
    seen: list[set[str]] = []
    for item in items:
        tokens = _tokens(item.headline)
        if any(_jaccard(tokens, previous) > 0.72 for previous in seen):
            continue
        kept.append(item)
        seen.append(tokens)
    return kept


def _tokens(headline: str) -> set[str]:
    stop = {"the", "a", "an", "to", "of", "and", "in", "on", "for", "as", "after", "with", "its", "from"}
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in headline)
    return {token for token in cleaned.split() if token and token not in stop}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _filing(symbol: str, row: dict, sample: bool) -> Filing:
    form = str(row.get("form") or "")
    description = str(row.get("description") or "").strip()
    if description.upper() in {form.upper(), f"FORM {form}".upper(), ""}:
        description = FORM_TITLES.get(form, description or form)
    return Filing(
        symbol=symbol,
        form=form,
        filed=str(row.get("filed") or ""),
        description=description,
        accession=row.get("accession"),
        url=str(row.get("url") or "https://www.sec.gov/edgar/search/"),
        insider=row.get("insider"),
        sample=sample,
    )


def _unavailable(symbol: str) -> Quote:
    return Quote(
        symbol=symbol,
        name=name_for(symbol),
        label=bloomberg_label(symbol),
        assetClass=classify(symbol),
        currency=currency_for(symbol),
        exchange=exchange_for(symbol),
        status="unavailable",
        sample=True,
        asOf=iso(),
    )


def _num(value: object) -> float | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def num_or(snap: dict | None, key: str) -> float | None:
    if not snap:
        return None
    return _num(snap.get(key))


def num_str(snap: dict | None, key: str) -> str | None:
    if not snap:
        return None
    value = snap.get(key)
    return value if isinstance(value, str) else None


def _synthetic_daily(symbol: str, end_price: float, n: int = 760) -> list[dict]:
    rng = random.Random(zlib.crc32(symbol.encode()) & 0xFFFFFFFF)
    asset = classify(symbol)
    vol = {"fx": 0.0025, "rate": 0.008, "crypto": 0.028, "commodity": 0.012}.get(asset, 0.014)
    closes = [end_price]
    price = end_price
    for _ in range(n - 1):
        price = max(price / math.exp(rng.gauss(0.0002, vol)), end_price * 0.15)
        closes.append(price)
    closes.reverse()
    day = _last_weekday(utcnow().date())
    dates: list[datetime] = []
    cursor = day
    while len(dates) < n:
        if cursor.weekday() < 5:
            dates.append(cursor)
        cursor -= timedelta(days=1)
    dates.reverse()
    bars = []
    for index, close in enumerate(closes):
        prev = closes[index - 1] if index else close
        open_ = prev * (1 + rng.gauss(0, vol * 0.25))
        high = max(open_, close) * (1 + abs(rng.gauss(0, vol * 0.35)))
        low = min(open_, close) * (1 - abs(rng.gauss(0, vol * 0.35)))
        bars.append(
            {
                "time": dates[index].isoformat(),
                "open": round(open_, 4),
                "high": round(high, 4),
                "low": round(max(low, 0.0001), 4),
                "close": round(close, 4),
                "volume": round(abs(rng.gauss(4.5e7, 8e6)), 0),
            }
        )
    return bars


def _last_weekday(day):
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def _sample_news() -> list[NewsItem]:
    base = utcnow()
    samples = [
        (1, "REUTERS", "Fed officials signal patience as core inflation cools for a third month", "MACRO", "Macro/Rates"),
        (2, "BLOOMBERG", "Apple suppliers see steady holiday build rates for iPhone", "AAPL", "Tech"),
        (3, "WSJ", "Nvidia data-center orders stay firm into year-end, analysts say", "NVDA", "Tech"),
        (4, "YAHOO", "Microsoft cloud growth steadies as AI capacity comes online", "MSFT", "Tech"),
        (5, "REUTERS", "Treasury 10-year yield slips after a softer payrolls revision", "MACRO", "Macro/Rates"),
        (6, "BLOOMBERG", "Hong Kong shares rise as Tencent outlines its buyback pace", "0700.HK", "Asia/EM"),
        (8, "WSJ", "Oil dips on talk of a larger U.S. crude build", "CL=F", "Energy"),
        (9, "REUTERS", "ECB holds rates and says further easing is data dependent", "MACRO", "Macro/Rates"),
        (11, "BLOOMBERG", "Amazon advertising unit outpaces store sales again", "AMZN", "Equities"),
        (12, "YAHOO", "Gold holds near highs as real yields ease", "GC=F", "Energy"),
        (14, "WSJ", "Software midcaps lift on fresh M&A chatter after a quiet quarter", "CRM", "Equities"),
        (16, "REUTERS", "Regional banks warn on commercial real estate marks", "JPM", "Equities"),
    ]
    raw = []
    for hours, source, headline, _ticker, _asset in samples:
        moment = base - timedelta(hours=hours)
        raw.append(
            {
                "headline": headline,
                "source": source,
                "url": "https://news.google.com/search?q=" + headline.replace(" ", "+"),
                "publishedAt": iso(moment),
                "summary": headline + ". Sample desk headline used when live RSS feeds are unavailable.",
            }
        )
    return _decorate_news(raw, sample=True)


def _sample_filings() -> list[Filing]:
    today = utcnow().date()
    specs = [
        (4, "4", "Statement of changes in beneficial ownership"),
        (18, "8-K", "Current report"),
        (40, "10-Q", "Quarterly report"),
        (120, "10-K", "Annual report"),
    ]
    return [
        Filing(
            symbol="AAPL",
            form=form,
            filed=(today - timedelta(days=days)).isoformat(),
            description=description,
            accession=None,
            url="https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000320193&type=" + form,
            sample=True,
        )
        for days, form, description in specs
    ]


def _sample_macro() -> dict[str, list[list]]:
    """A short curve used only when the FRED snapshot is missing."""
    end = utcnow().date()
    series = {
        "DGS3MO": 4.34,
        "DGS2": 4.76,
        "DGS5": 4.86,
        "DGS10": 5.04,
        "DGS30": 5.40,
        "T10Y2Y": 0.29,
        "FEDFUNDS": 3.88,
        "UNRATE": 4.1,
    }
    out: dict[str, list[list]] = {}
    for name, level in series.items():
        rows = []
        for index in range(40, 0, -1):
            day = end - timedelta(days=index * 7)
            drift = math.sin(index / 4) * 0.08
            rows.append([day.isoformat(), round(level + drift, 3)])
        out[name] = rows
    cpi = []
    value = 330.0
    for index in range(24):
        month = end.replace(day=1) - timedelta(days=30 * (23 - index))
        value *= 1.0025
        cpi.append([month.isoformat(), round(value, 3)])
    out["CPIAUCSL"] = cpi
    payroll = []
    jobs = 158000.0
    for index in range(18):
        month = end.replace(day=1) - timedelta(days=30 * (17 - index))
        jobs += 180
        payroll.append([month.isoformat(), jobs])
    out["PAYEMS"] = payroll
    return out


@lru_cache
def get_book() -> FixtureBook:
    return FixtureBook()
