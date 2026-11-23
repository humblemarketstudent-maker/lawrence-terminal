"""Market strip, equity movers, and G10 FX for the desk header.

The strip is cash indexes, FX, and the US 2-year yield. Futures are not shown.
Symbols below were checked against the Yahoo chart on 2026-11-23. TOPIX still
has no working public cash symbol (^TPX, ^TOPIX, and 998405.T do not quote),
so that row stays unavailable.

Change is versus the previous session. Thin histories such as CSI 300 use
Yahoo's full-day change when the daily bars do not include a prior close.

Verified cash symbols
- S&P 500 ^GSPC, NASDAQ 100 ^NDX, Euro Stoxx 50 ^STOXX50E, DAX ^GDAXI,
  FTSE 100 ^FTSE, Nikkei 225 ^N225, S&P/ASX 200 ^AXJO, KOSPI ^KS11
- CSI 300 000300.SS, CSI 500 000905.SS, CSI 1000 000852.SS
- TWSE ^TWII (TSEC capitalization-weighted index), Singapore STI ^STI,
  Nifty 50 ^NSEI, KLCI ^KLSE, SET50 ^SET50.BK
- USD/JPY USDJPY=X, AUD/USD AUDUSD=X, US 10-year ^TNX
- US 2-year is FRED DGS2, not a Yahoo yield future
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
    basis: str | None = None


STRIP: tuple[_Spec, ...] = (
    _Spec("S&P 500", "Equity Index", "index", "^GSPC", ("SPX", "S&P 500", "SP500")),
    _Spec("NASDAQ 100", "Equity Index", "index", "^NDX", ("NDX", "NASDAQ100", "NASDAQ 100")),
    _Spec("Euro Stoxx 50", "Equity Index", "index", "^STOXX50E", ("Eurostoxx", "STOXX50", "Euro Stoxx 50")),
    _Spec("DAX", "Equity Index", "index", "^GDAXI", ("DAX",)),
    _Spec("FTSE 100", "Equity Index", "index", "^FTSE", ("FTSE", "FTSE100", "FTSE 100")),
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
    _Spec("CSI 500", "Equity Index", "index", "000905.SS", ("CSI500", "CSI 500")),
    _Spec("CSI 1000", "Equity Index", "index", "000852.SS", ("CSI1000", "CSI 1000")),
    _Spec("TWSE", "Equity Index", "index", "^TWII", ("TWSE", "TAIEX")),
    _Spec("Singapore STI", "Equity Index", "index", "^STI", ("STI", "Singapore")),
    _Spec("Nifty 50", "Equity Index", "index", "^NSEI", ("Nifty", "Nifty 50")),
    _Spec("KLCI", "Equity Index", "index", "^KLSE", ("KLCI", "FKLI")),
    _Spec("SET50", "Equity Index", "index", "^SET50.BK", ("SET50",)),
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
    """Yahoo symbols the strip and G10 board need. FRED and blank rows are omitted."""
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


def _from_quote(spec: _Spec, quote: Quote, *, symbol: str | None = None) -> DashboardRow:
    chosen = symbol or spec.symbol
    return DashboardRow(
        name=spec.name,
        symbol=chosen,
        group=spec.group,
        assetClass=spec.asset_class,
        price=quote.price,
        change=quote.change,
        changePct=quote.changePct,
        previousClose=quote.previousClose,
        currency=quote.currency,
        status="ok",
        provider="yfinance",
        link=spec.link and bool(chosen),
        basis=spec.basis if quote.previousClose else None,
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
    if not live:
        return _blank(spec, "unavailable", "Live feed off")
    if spec.symbol not in attempted:
        return _blank(spec, "pending", None)
    return _blank(spec, "unavailable", spec.reason or "No live quote")


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
