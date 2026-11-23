"""Market strip, equity movers, and G10 FX for the desk header.

Symbols below were checked against live Yahoo data through yfinance on
2026-11-23. Where the public chart had no instrument, the row stays
unavailable instead of borrowing a nearby ticker.

Verified Yahoo symbols
- S&P 500: ^GSPC, longName "S&P 500"
- NASDAQ 100: ^NDX, longName "NASDAQ-100" (^IXIC is the Composite and is not used)
- Euro Stoxx 50: ^STOXX50E, longName "EURO STOXX 50" (^STOXX is the broader benchmark)
- DAX: ^GDAXI
- FTSE 100: ^FTSE (alias "FTSE")
- CSI 300: 000300.SS, quoteType INDEX. Daily history currently returns one bar,
  so the previous close is taken from Yahoo previousClose when the bar history
  cannot supply it.
- KOSPI: ^KS11, longName "KOSPI Composite Index"
- Nikkei 225: ^N225
- S&P/ASX 200: ^AXJO (alias "ASX200"), longName "S&P/ASX 200"
- USD/JPY: USDJPY=X, longName "USD/JPY" (alias "USDJPY")
- AUD/USD: AUDUSD=X, longName "AUD/USD" (alias "AUDUSD")
- US 10-year: ^TNX, longName "CBOE Interest Rate 10 Year T Note"
- G10: EURUSD=X, GBPUSD=X, USDJPY=X, USDCHF=X, USDCAD=X, AUDUSD=X, NZDUSD=X,
  USDSEK=X, USDNOK=X. Each longName matches that pair.

Not used
- TOPIX: ^TPX, ^TOPIX, ^TOPX, and the Yahoo Japan code 998405.T all 404 on
  query1.finance.yahoo.com. ETFs such as 1306.T are funds, not the index.
- US 2-year: no cash Yahoo yield. ^IRX is the 13-week bill, ^FVX is the 5-year,
  ^TNX is the 10-year, and 2YY=F is the Oct-2026 2-year yield future. The cash
  yield is the FRED constant-maturity series DGS2, which this app already reads
  without an API key. The row shows that print and its observation date.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas import DashboardBoard, DashboardRow, DashboardSection, Meta, MoverRow, Movers, Quote
from app.symbols import equity_universe
from app.util import iso

TWO_YEAR_SERIES = "DGS2"

_NON_EQUITY = {"index", "fx", "rate", "commodity", "crypto", "etf"}


@dataclass(frozen=True)
class _Spec:
    name: str
    group: str
    asset_class: str
    symbol: str | None
    aliases: tuple[str, ...] = ()
    provider: str = "yfinance"
    reason: str | None = None
    link: bool = True


STRIP: tuple[_Spec, ...] = (
    _Spec("S&P 500", "Equity Index", "index", "^GSPC", ("SPX", "S&P 500", "SP500")),
    _Spec("NASDAQ 100", "Equity Index", "index", "^NDX", ("NDX", "NASDAQ100", "NASDAQ 100")),
    _Spec("Euro Stoxx 50", "Equity Index", "index", "^STOXX50E", ("Eurostoxx", "STOXX50", "Euro Stoxx 50")),
    _Spec("DAX", "Equity Index", "index", "^GDAXI", ("DAX",)),
    _Spec("FTSE 100", "Equity Index", "index", "^FTSE", ("FTSE", "FTSE100")),
    _Spec("CSI 300", "Equity Index", "index", "000300.SS", ("CSI300", "CSI 300")),
    _Spec("KOSPI", "Equity Index", "index", "^KS11", ("KOSPI",)),
    _Spec("Nikkei 225", "Equity Index", "index", "^N225", ("Nikkei", "N225")),
    _Spec(
        "TOPIX",
        "Equity Index",
        "index",
        None,
        ("TOPIX", "TPX"),
        reason="No public Yahoo index symbol",
        link=False,
    ),
    _Spec("S&P/ASX 200", "Equity Index", "index", "^AXJO", ("ASX200", "ASX 200")),
    _Spec("USD/JPY", "FX", "fx", "USDJPY=X", ("USDJPY", "USD/JPY")),
    _Spec("AUD/USD", "FX", "fx", "AUDUSD=X", ("AUDUSD", "AUD/USD")),
    _Spec("US 2-Year Yield", "Rates", "rate", TWO_YEAR_SERIES, ("US2Y", "US 2Y"), provider="fred", link=False),
    _Spec("US 10-Year Yield", "Rates", "rate", "^TNX", ("US10Y", "US 10Y", "TNX")),
)

G10: tuple[_Spec, ...] = (
    _Spec("EUR/USD", "FX", "fx", "EURUSD=X", ("EURUSD",)),
    _Spec("GBP/USD", "FX", "fx", "GBPUSD=X", ("GBPUSD",)),
    _Spec("USD/JPY", "FX", "fx", "USDJPY=X", ("USDJPY",)),
    _Spec("USD/CHF", "FX", "fx", "USDCHF=X", ("USDCHF",)),
    _Spec("USD/CAD", "FX", "fx", "USDCAD=X", ("USDCAD",)),
    _Spec("AUD/USD", "FX", "fx", "AUDUSD=X", ("AUDUSD",)),
    _Spec("NZD/USD", "FX", "fx", "NZDUSD=X", ("NZDUSD",)),
    _Spec("USD/SEK", "FX", "fx", "USDSEK=X", ("USDSEK",)),
    _Spec("USD/NOK", "FX", "fx", "USDNOK=X", ("USDNOK",)),
)


def market_symbols() -> list[str]:
    """Yahoo symbols the strip and G10 board need. FRED and TOPIX are not included."""
    symbols: list[str] = []
    for spec in (*STRIP, *G10):
        if spec.provider != "yfinance" or not spec.symbol:
            continue
        if spec.symbol not in symbols:
            symbols.append(spec.symbol)
    return symbols


def alias_map() -> dict[str, str]:
    found: dict[str, str] = {}
    for spec in (*STRIP, *G10):
        for alias in spec.aliases:
            key = "".join(ch for ch in alias.lower() if ch.isalnum())
            found[key] = spec.name
    return found


def _yield_pair(rows: list | None) -> tuple[float | None, float | None, str | None]:
    parsed: list[tuple[str, float]] = []
    for item in rows or []:
        if not item or len(item) < 2 or item[1] is None:
            continue
        try:
            value = float(item[1])
        except (TypeError, ValueError):
            continue
        parsed.append((str(item[0]), value))
    if not parsed:
        return None, None, None
    session, last = parsed[-1]
    if not 0 < last < 25:
        return None, None, None
    previous = parsed[-2][1] if len(parsed) > 1 else None
    if previous is not None and not 0 < previous < 25:
        previous = None
    return last, previous, session


def _blank(spec: _Spec, status: str, reason: str | None) -> DashboardRow:
    return DashboardRow(
        name=spec.name,
        symbol=spec.symbol,
        group=spec.group,
        assetClass=spec.asset_class,
        status=status,  # type: ignore[arg-type]
        reason=reason,
        provider=spec.provider,
        link=spec.link and bool(spec.symbol),
    )


def _from_quote(spec: _Spec, quote: Quote) -> DashboardRow:
    return DashboardRow(
        name=spec.name,
        symbol=spec.symbol,
        group=spec.group,
        assetClass=spec.asset_class,
        price=quote.price,
        change=quote.change,
        changePct=quote.changePct,
        previousClose=quote.previousClose,
        currency=quote.currency,
        status="ok",
        provider="yfinance",
        link=spec.link and bool(spec.symbol),
    )


def _usable(quote: Quote | None) -> Quote | None:
    if quote is None or quote.sample or quote.status != "ok" or quote.price is None:
        return None
    return quote


def _market_row(spec: _Spec, quote: Quote | None, *, attempted: set[str], live: bool) -> DashboardRow:
    if spec.symbol is None:
        return _blank(spec, "unavailable", spec.reason or "No public symbol")
    usable = _usable(quote)
    if usable is not None:
        return _from_quote(spec, usable)
    if live and spec.symbol not in attempted:
        return _blank(spec, "pending", None)
    if not live:
        return _blank(spec, "unavailable", "Live feed off")
    return _blank(spec, "unavailable", "No live quote")


def _two_year(spec: _Spec, fred: dict | None, *, macro_done: bool, live: bool) -> DashboardRow:
    if not live:
        return _blank(spec, "unavailable", "Live feed off")
    last, previous, session = _yield_pair((fred or {}).get(TWO_YEAR_SERIES))
    if last is None:
        if not macro_done:
            return _blank(spec, "pending", None)
        return _blank(spec, "unavailable", "FRED DGS2 unavailable")
    change = last - previous if previous is not None else None
    change_pct = (change / previous * 100.0) if change is not None and previous else None
    return DashboardRow(
        name=spec.name,
        symbol=TWO_YEAR_SERIES,
        group=spec.group,
        assetClass="rate",
        price=last,
        change=change,
        changePct=change_pct,
        previousClose=previous,
        currency="USD",
        session=session,
        status="ok",
        provider="fred",
        link=False,
    )


def _mover(quote: Quote) -> MoverRow:
    return MoverRow(
        symbol=quote.symbol,
        name=quote.name,
        label=quote.label,
        price=quote.price,
        change=quote.change,
        changePct=quote.changePct,
        volume=quote.volume,
        currency=quote.currency,
        assetClass=quote.assetClass or "equity",
    )


def rank_movers(quotes: list[Quote], *, universe: list[str], ready: bool, attempted: int) -> Movers:
    """Top 10 by share volume, percent gain, and percent loss.

    The universe is the full equity book. Lists stay empty until every name has
    been requested, so a partial download cannot publish a top 10.
    """
    allowed = set(universe)
    usable: list[Quote] = []
    seen: set[str] = set()
    for quote in quotes:
        if quote.symbol in seen or quote.symbol not in allowed:
            continue
        if quote.symbol.startswith("^") or quote.assetClass in _NON_EQUITY:
            continue
        if _usable(quote) is None:
            continue
        seen.add(quote.symbol)
        usable.append(quote)
    with_volume = [quote for quote in usable if quote.volume is not None and quote.volume > 0]
    with_pct = [quote for quote in usable if quote.changePct is not None]
    active = sorted(with_volume, key=lambda quote: (-(quote.volume or 0), quote.symbol))[:10] if ready else []
    rise = sorted(with_pct, key=lambda quote: (-(quote.changePct or 0), quote.symbol))[:10] if ready else []
    drop = sorted(with_pct, key=lambda quote: ((quote.changePct if quote.changePct is not None else 0), quote.symbol))[:10] if ready else []
    return Movers(
        active=[_mover(quote) for quote in active],
        rise=[_mover(quote) for quote in rise],
        drop=[_mover(quote) for quote in drop],
        universe=len(universe),
        attempted=attempted,
        quoted=len(usable),
        ready=ready,
    )


def build_dashboard(
    quotes: dict[str, Quote],
    *,
    fred: dict | None,
    attempted: set[str],
    macro_done: bool,
    live: bool,
    stale: bool = False,
) -> DashboardSection:
    universe = equity_universe()
    ready = (not live) or set(universe).issubset(attempted)
    strip: list[DashboardRow] = []
    for spec in STRIP:
        if spec.provider == "fred":
            strip.append(_two_year(spec, fred if live else None, macro_done=macro_done, live=live))
        else:
            quote = quotes.get(spec.symbol) if spec.symbol else None
            strip.append(_market_row(spec, quote, attempted=attempted, live=live))
    fx = [
        _market_row(spec, quotes.get(spec.symbol) if spec.symbol else None, attempted=attempted, live=live)
        for spec in G10
    ]
    equity_quotes = [quotes[symbol] for symbol in universe if symbol in quotes]
    movers = rank_movers(equity_quotes, universe=universe, ready=ready, attempted=sum(symbol in attempted for symbol in universe))
    any_ok = any(row.status == "ok" for row in (*strip, *fx)) or bool(movers.active or movers.rise or movers.drop)
    warnings: list[str] = []
    if not live:
        warnings.append("Live market data is off.")
    elif not ready:
        warnings.append("Loading live quotes.")
        stale = True
    elif movers.quoted < movers.universe:
        missing = movers.universe - movers.quoted
        warnings.append(f"{missing} equity names had no quote and were left out of the mover lists.")
    if not any_ok:
        stale = True
    source = "live" if any_ok and not stale else "cache"
    return DashboardSection(
        data=DashboardBoard(strip=strip, movers=movers, fx=fx),
        meta=Meta(
            source=source,  # type: ignore[arg-type]
            provider="yfinance",
            asOf=iso(),
            stale=stale or not any_ok,
            warning=" ".join(warnings) or None,
        ),
    )
