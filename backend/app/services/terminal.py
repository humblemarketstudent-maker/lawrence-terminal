"""Cache-aware facade. Reads return immediately; live work happens behind them."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import datetime, timezone

from app.adapters.router import MarketRouter
from app.adapters.yfinance_adapter import silence_yfinance
from app.book import get_book
from app.dashboard import build_dashboard, market_symbols
from app.cache import TTLCache
from app.config import Settings, get_settings
from app.schemas import (
    BootstrapResponse,
    Brief,
    CompanyProfile,
    FilingsSection,
    History,
    HistorySection,
    Meta,
    NewsItem,
    NewsSection,
    ProfileSection,
    Quote,
    QuoteSection,
    SearchHit,
    Statements,
    StatementsSection,
    SymbolBundle,
)
from app.services.brief import build_brief
from app.services.filings import fetch_filings
from app.services.macro import build_eco, build_wei, fetch_fred
from app.services.news import fetch_news
from app.services.company import peer_rows, upcoming_events
from app.services.normalize import option_from_dict, profile_from_parts, statements_from_blocks
from app.symbols import WEI_SYMBOLS, bloomberg_label, equity_universe, normalize_symbol, search_catalog
from app.util import iso

log = logging.getLogger(__name__)


class Terminal:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.cache = TTLCache()
        self.book = get_book()
        self.router = MarketRouter(self.settings)
        self.hot: set[str] = set(self.book.symbols_for_desk())
        self.hot.update(market_symbols())
        self._attempted: set[str] = set()
        self._macro_done = False
        self.focus = "AAPL"
        self._tasks: dict[str, asyncio.Task] = {}
        self._quote_lock = asyncio.Lock()
        self._stop = asyncio.Event()
        silence_yfinance()

    def _meta(self, source: str, provider: str, as_of: str, stale: bool = False, warning: str | None = None) -> Meta:
        return Meta(source=source, provider=provider, asOf=as_of, stale=stale, warning=warning)  # type: ignore[arg-type]

    def _section(self, key: str, factory):
        hit = self.cache.get(key, allow_stale=True)
        if not hit:
            return factory()
        section = hit.value
        if hit.fresh:
            return section
        stale = section.model_copy(deep=True)
        stale.meta.source = "cache"
        stale.meta.stale = True
        return stale

    def _kick(self, key: str, factory) -> None:
        if self.settings.disable_live:
            return
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            log.warning("skipped background %s; no running event loop", key)
            return
        current = self._tasks.get(key)
        if current and not current.done():
            return
        task = asyncio.create_task(factory())
        self._tasks[key] = task

        def _done(finished: asyncio.Task) -> None:
            self._tasks.pop(key, None)
            with suppress(asyncio.CancelledError):
                exc = finished.exception()
                if exc:
                    log.warning("background %s failed: %s", key, exc)

        task.add_done_callback(_done)

    def best_quote(self, symbol: str) -> Quote:
        hit = self.cache.get(f"q:{symbol}", allow_stale=True)
        if hit:
            return hit.value
        fixture = self.book.quote(symbol)
        if fixture:
            return fixture
        return _missing(symbol)

    def quote_section(self, symbols: list[str]) -> QuoteSection:
        clean = _unique(symbols)
        data = [self.best_quote(symbol) for symbol in clean]
        sources = []
        for symbol in clean:
            hit = self.cache.get(f"q:{symbol}", allow_stale=True)
            if hit and hit.fresh:
                sources.append("live")
            elif hit:
                sources.append("cache")
            else:
                sources.append("fixture")
        if sources and all(item == "live" for item in sources):
            source, stale = "live", False
        elif "live" in sources or "cache" in sources:
            source, stale = "cache", "fixture" in sources or "cache" in sources
        else:
            source, stale = "fixture", False
        as_of = data[0].asOf if data else iso()
        warning = None
        if any(quote.status != "ok" for quote in data):
            warning = "One or more symbols did not return a quote."
        return QuoteSection(data=data, meta=self._meta(source, self.router.active_name, as_of, stale, warning))

    def _live_quote(self, symbol: str) -> Quote | None:
        hit = self.cache.get(f"q:{symbol}", allow_stale=True)
        if not hit:
            return None
        quote = hit.value
        if quote.sample or quote.status != "ok" or quote.price is None:
            return None
        return quote

    async def refresh_quotes(self, symbols: list[str]) -> None:
        if self.settings.disable_live:
            return
        symbols = _unique(symbols)
        if not symbols:
            return
        # Dashboard symbols first so the strip paints before the 462-name book finishes.
        priority = set(market_symbols())
        symbols = [symbol for symbol in symbols if symbol in priority] + [symbol for symbol in symbols if symbol not in priority]
        chunk_size = 40
        async with self._quote_lock:
            for i in range(0, len(symbols), chunk_size):
                chunk = symbols[i : i + chunk_size]
                try:
                    quotes = await self.router.get_quotes(chunk)
                except Exception as exc:
                    log.warning("quote refresh failed: %s", exc)
                    continue
                for quote in quotes:
                    merged = self._merge_quote(quote)
                    self.cache.set(f"q:{merged.symbol}", merged, self.settings.cache_ttl_quotes)
                self._attempted = self._attempted.union(chunk)

    def _merge_quote(self, quote: Quote) -> Quote:
        fixture = self.book.quote(quote.symbol)
        if not fixture:
            return quote
        payload = quote.model_dump()
        fallback = fixture.model_dump()
        for key in ("marketCap", "sparkline", "week52High", "week52Low", "avgVolume30d", "name"):
            if payload.get(key) in (None, [], "") and fallback.get(key) not in (None, [], ""):
                payload[key] = fallback[key]
        if payload.get("volume") and payload.get("avgVolume30d") and not payload.get("volumeRatio"):
            payload["volumeRatio"] = payload["volume"] / payload["avgVolume30d"]
        payload["sample"] = False
        return Quote(**payload)

    async def refresh_history(self, symbol: str, range_key: str) -> None:
        if self.settings.disable_live:
            return
        try:
            bars, interval = await self.router.get_history(symbol, range_key)
        except Exception as exc:
            log.warning("history %s %s failed: %s", symbol, range_key, exc)
            return
        if len(bars) < 2:
            return
        history = History(symbol=symbol, range=range_key, interval=interval, bars=bars, sample=False)
        section = HistorySection(data=history, meta=self._meta("live", "yfinance", iso()))
        self.cache.set(f"h:{symbol}:{range_key}", section, self.settings.cache_ttl_history)

    def history_section(self, symbol: str, range_key: str) -> HistorySection:
        def factory():
            history = self.book.history(symbol, range_key)
            warning = None if history.bars else f"No bars are available for {symbol}."
            return HistorySection(data=history, meta=self._meta("fixture", self.book.provider, self.book.as_of, warning=warning))

        return self._section(f"h:{symbol}:{range_key}", factory)

    async def refresh_fundamentals(self, symbol: str) -> None:
        if self.settings.disable_live:
            return
        try:
            payload = await self.router.get_fundamentals(symbol)
        except Exception as exc:
            log.warning("fundamentals %s failed: %s", symbol, exc)
            return
        info = payload.get("info") or {}
        currency = info.get("currency") if isinstance(info.get("currency"), str) else "USD"
        statements = statements_from_blocks(symbol, currency, payload.get("income"), payload.get("balance"), payload.get("cashflow"), sample=False)
        self.cache.set(f"s:{symbol}", StatementsSection(data=statements, meta=self._meta("live", "yfinance", iso())), self.settings.cache_ttl_fundamentals)
        quote = self.best_quote(symbol)
        live_quote = quote if quote.status == "ok" and not quote.sample else None
        options_payload = None
        if classify_equity(symbol):
            options_payload = await self.router.get_options(symbol, (live_quote or quote).price)
        options = option_from_dict(options_payload, sample=False)
        peers = peer_rows(payload.get("peers"))
        if peers:
            peers_status, peers_reason, peers_source = "ok", None, "Yahoo Finance recommendations"
        elif payload.get("peersError"):
            peers_status, peers_reason, peers_source = "unavailable", str(payload.get("peersError")), None
        elif payload.get("peerSymbols"):
            peers_status, peers_reason, peers_source = "unavailable", "Yahoo listed peers but none returned a live price.", None
        else:
            peers_status, peers_reason, peers_source = "unavailable", "Yahoo did not list peers for this symbol.", None
        event_payload = payload.get("events") or {}
        events = upcoming_events(event_payload.get("calendar"), event_payload.get("earnings"), datetime.now(timezone.utc).date())
        if events:
            events_status, events_reason = "ok", None
        else:
            events_status, events_reason = "unavailable", "No upcoming date in the Yahoo calendar."
        profile = profile_from_parts(
            symbol,
            info,
            price=live_quote.price if live_quote else None,
            quote=live_quote,
            peers=peers,
            statements=statements,
            options=options,
            sample=False,
            fx=payload.get("fx") if isinstance(payload.get("fx"), dict) else None,
            events=events,
            events_status=events_status,
            events_reason=events_reason,
            peers_status=peers_status,
            peers_reason=peers_reason,
            peers_source=peers_source,
        )
        if profile.marketCap and quote.marketCap is None:
            self.cache.set(f"q:{symbol}", quote.model_copy(update={"marketCap": profile.marketCap}), self.settings.cache_ttl_quotes)
        self.cache.set(f"p:{symbol}", ProfileSection(data=profile, meta=self._meta("live", "yfinance", iso())), self.settings.cache_ttl_fundamentals)

    def profile_section(self, symbol: str) -> ProfileSection:
        def factory():
            profile = self.book.profile(symbol)
            if self.settings.disable_live:
                profile = profile.model_copy(update={
                    "peers": [],
                    "peersStatus": "unavailable",
                    "peersReason": "Live peer feed is off.",
                    "peersSource": None,
                    "events": [],
                    "eventsStatus": "unavailable",
                    "eventsReason": "Live calendar is off.",
                    "turnoverLocal": None,
                    "turnoverUsd": None,
                    "turnoverStatus": "unavailable",
                    "turnoverReason": "Live turnover is off.",
                    "fxPair": None,
                    "fxRate": None,
                })
            return ProfileSection(data=profile, meta=self._meta("fixture", self.book.provider, self.book.as_of))

        return self._section(f"p:{symbol}", factory)

    def statements_section(self, symbol: str) -> StatementsSection:
        def factory():
            statements = self.book.statements(symbol)
            return StatementsSection(data=statements, meta=self._meta("fixture", self.book.provider, self.book.as_of))

        return self._section(f"s:{symbol}", factory)

    async def refresh_news(self, symbol: str | None = None) -> None:
        if self.settings.disable_live:
            return
        try:
            items = await fetch_news(symbol)
        except Exception as exc:
            log.warning("news refresh failed: %s", exc)
            return
        if len(items) < 4:
            return
        section = NewsSection(data=items, meta=self._meta("live", "rss", iso()))
        self.cache.set("news" if not symbol else f"news:{symbol}", section, self.settings.cache_ttl_news)

    def news_section(self, symbol: str | None = None) -> NewsSection:
        key = f"news:{symbol}" if symbol else "news"

        def factory():
            if symbol:
                items = _filter_news(self.book.news(), symbol)
                warning = None
                if len(items) < 3:
                    items = self.book.news()
                    warning = f"No {symbol} headlines in the saved wire. Showing the desk stream."
                return NewsSection(data=items, meta=self._meta("fixture", self.book.provider, self.book.as_of, warning=warning))
            return NewsSection(data=self.book.news(), meta=self._meta("fixture", self.book.provider, self.book.as_of))

        global_section = self._section("news", lambda: NewsSection(data=self.book.news(), meta=self._meta("fixture", self.book.provider, self.book.as_of)))
        if not symbol:
            return global_section
        hit = self.cache.get(key, allow_stale=True)
        if hit:
            return self._section(key, factory)
        filtered = _filter_news(global_section.data, symbol)
        if len(filtered) >= 3:
            return NewsSection(data=filtered, meta=global_section.meta)
        return factory() if not global_section.data else NewsSection(
            data=filtered or global_section.data[:20],
            meta=global_section.meta.model_copy(update={"warning": None if filtered else f"No {symbol} headlines yet. Showing the desk stream."}),
        )

    async def refresh_filings(self, symbol: str) -> None:
        if self.settings.disable_live:
            return
        try:
            filings = await fetch_filings(symbol, self.settings.sec_user_agent)
        except Exception as exc:
            log.warning("filings %s failed: %s", symbol, exc)
            return
        if not filings:
            return
        section = FilingsSection(data=filings, meta=self._meta("live", "sec", iso()))
        self.cache.set(f"f:{symbol}", section, self.settings.cache_ttl_filings)

    def filings_section(self, symbol: str) -> FilingsSection:
        def factory():
            filings = self.book.filings(symbol)
            warning = None
            if not filings:
                warning = "No SEC submissions for this symbol. EDGAR covers US registrants."
            return FilingsSection(data=filings, meta=self._meta("fixture", "sec" if filings else self.book.provider, self.book.as_of, warning=warning))

        return self._section(f"f:{symbol}", factory)

    async def refresh_macro(self) -> None:
        if self.settings.disable_live:
            return
        series = None
        try:
            series = await fetch_fred(self.settings.fred_api_key)
        except Exception as exc:
            log.warning("macro refresh failed: %s", exc)
        self._macro_done = True
        if not series or len(series) < 3:
            return
        self.cache.set("fred", series, self.settings.cache_ttl_macro)
        self.cache.set("fred-meta", self._meta("live", "fred" if not self.settings.fred_api_key else "fred-api", iso()), self.settings.cache_ttl_macro)

    def _fred(self) -> tuple[dict, Meta]:
        hit = self.cache.get("fred", allow_stale=True)
        meta_hit = self.cache.get("fred-meta", allow_stale=True)
        if hit:
            meta = meta_hit.value if meta_hit else self._meta("cache", "fred", iso(), stale=not hit.fresh)
            if not hit.fresh:
                meta = meta.model_copy(update={"source": "cache", "stale": True})
            return hit.value, meta
        return self.book.macro(), self._meta("fixture", self.book.provider, self.book.as_of)

    def wei_section(self):
        from app.schemas import WeiSection

        fred, meta = self._fred()
        quotes = {}
        for symbol, _name, _group in WEI_SYMBOLS:
            quotes[symbol] = self.best_quote(symbol)
        board = build_wei(quotes, fred, sample_macro=meta.source != "live")
        if any(not quote.sample for quote in quotes.values()) and meta.source == "fixture":
            meta = meta.model_copy(update={"source": "cache", "stale": True})
        return WeiSection(data=board, meta=meta)

    def eco_section(self):
        from app.schemas import EcoSection

        fred, meta = self._fred()
        return EcoSection(data=build_eco(fred, sample_macro=meta.source != "live"), meta=meta)

    def dashboard_section(self):
        quotes: dict[str, Quote] = {}
        symbols = list(dict.fromkeys([*market_symbols(), *equity_universe()]))
        for symbol in symbols:
            quote = self._live_quote(symbol)
            if quote is not None:
                quotes[symbol] = quote
        fred_hit = self.cache.get("fred", allow_stale=True)
        # Quote TTL is 20s, shorter than one pass over the 462-name book, so a
        # fresh live print is still the last close after the TTL flips. The
        # pill stays LIVE for those prints instead of flashing STALE.
        return build_dashboard(
            quotes,
            fred=fred_hit.value if fred_hit else None,
            attempted=set(self._attempted),
            macro_done=self._macro_done,
            live=not self.settings.disable_live,
            stale=False,
        )

    async def refresh_symbol(self, symbol: str, range_key: str) -> None:
        await asyncio.gather(
            self.refresh_fundamentals(symbol),
            self.refresh_history(symbol, range_key),
            self.refresh_filings(symbol),
            self.refresh_news(symbol),
            return_exceptions=True,
        )

    def bundle(self, symbol: str, range_key: str, *, force: bool = False) -> SymbolBundle:
        symbol = normalize_symbol(symbol) or "AAPL"
        self.focus = symbol
        self.hot.add(symbol)
        if force:
            self._kick(f"force:{symbol}:{range_key}", lambda: self.refresh_symbol(symbol, range_key))
        else:
            self._kick(f"sym:{symbol}:{range_key}", lambda: self.refresh_symbol(symbol, range_key))
        return SymbolBundle(
            symbol=symbol,
            profile=self.profile_section(symbol),
            statements=self.statements_section(symbol),
            history=self.history_section(symbol, range_key),
            filings=self.filings_section(symbol),
            news=self.news_section(symbol),
        )

    def bootstrap(self, symbol: str, range_key: str = "1Y") -> BootstrapResponse:
        symbol = normalize_symbol(symbol) or "AAPL"
        self.hot.update(self.book.symbols_for_desk())
        self.hot.add(symbol)
        self._kick("quotes", lambda: self.refresh_quotes(list(self.hot)))
        self._kick("news", self.refresh_news)
        self._kick("macro", self.refresh_macro)
        return BootstrapResponse(
            quotes=self.quote_section(list(dict.fromkeys([*self.book.symbols_for_desk(), symbol]))),
            news=self.news_section(None),
            wei=self.wei_section(),
            eco=self.eco_section(),
            bundle=self.bundle(symbol, range_key),
            serverTime=iso(),
            providers=self.provider_status(),
        )

    async def force_refresh(self, symbols: list[str], scope: str, range_key: str) -> dict:
        symbols = _unique(symbols or list(self.hot))
        self.hot.update(symbols)
        tasks = []
        if scope in {"all", "quotes"}:
            tasks.append(self.refresh_quotes(list(self.hot)))
        if scope in {"all", "news"}:
            tasks.append(self.refresh_news(self.focus))
        if scope in {"all", "macro"}:
            tasks.append(self.refresh_macro())
        if scope in {"all", "fundamentals"}:
            tasks.append(self.refresh_symbol(self.focus, range_key))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        return {"ok": True, "refreshed": scope, "asOf": iso()}

    def brief(self, symbols: list[str]) -> Brief:
        symbols = _unique(symbols or list(self.book.symbols_for_desk())[:10])
        quotes = [self.best_quote(symbol) for symbol in symbols]
        news = self.news_section(None)
        wei = self.wei_section()
        eco = self.eco_section()
        sample = all(quote.sample for quote in quotes) or all(item.sample for item in news.data[:5])
        return build_brief(quotes, news.data, wei.data, eco.data, sample=sample)

    def search(self, query: str) -> list[SearchHit]:
        return [
            SearchHit(
                symbol=row["symbol"],
                name=row["name"],
                assetClass=row["assetClass"],
                exchange=row["exchange"],
                label=bloomberg_label(row["symbol"]),
            )
            for row in search_catalog(query)
        ]

    def provider_status(self) -> dict:
        settings = self.settings
        return {
            "market": self.router.active_name,
            "macro": "fred" if not settings.fred_api_key else "fred-api",
            "news": "rss",
            "filings": "sec",
            "live": not settings.disable_live,
            "snapshotAsOf": self.book.as_of if self.book.raw else None,
            "keys": {
                "finnhub": bool(settings.finnhub_api_key),
                "fmp": bool(settings.fmp_api_key),
                "alphavantage": bool(settings.alphavantage_api_key),
                "twelvedata": bool(settings.twelvedata_api_key),
                "fred": bool(settings.fred_api_key),
            },
            "cache": self.cache.stats(),
        }

    async def warm_loop(self) -> None:
        if self.settings.disable_live:
            return
        await asyncio.sleep(0.4)
        macro_task = asyncio.create_task(self.refresh_macro())
        await self.refresh_quotes(list(self.hot))
        with suppress(Exception):
            await macro_task
        await self.refresh_news()
        await self.refresh_symbol("AAPL", "1Y")
        tick = 0
        while not self._stop.is_set():
            try:
                await asyncio.wait_for(self._stop.wait(), 25)
                return
            except asyncio.TimeoutError:
                pass
            tick += 1
            await self.refresh_quotes(list(self.hot))
            if tick % 6 == 0:
                await self.refresh_news()
            if tick % 40 == 0:
                await self.refresh_macro()


def _unique(symbols: list[str]) -> list[str]:
    out: list[str] = []
    for raw in symbols:
        symbol = normalize_symbol(raw)
        if symbol and symbol not in out and len(symbol) <= 24:
            out.append(symbol)
    return out


def _missing(symbol: str) -> Quote:
    from app.symbols import classify, currency_for, exchange_for, name_for

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


def _filter_news(items: list[NewsItem], symbol: str) -> list[NewsItem]:
    root = symbol.split(".")[0].lstrip("^").upper()
    matched = []
    for item in items:
        blob = item.headline.upper()
        if symbol in item.tickers or symbol in blob or (len(root) >= 2 and root in blob) or root in {ticker.split(".")[0] for ticker in item.tickers}:
            matched.append(item)
    return matched


def classify_equity(symbol: str) -> bool:
    from app.symbols import classify

    return classify(symbol) == "equity"


_TERMINAL: Terminal | None = None


def get_terminal() -> Terminal:
    global _TERMINAL
    if _TERMINAL is None:
        _TERMINAL = Terminal()
    return _TERMINAL
