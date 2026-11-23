"""Market strip, equity movers, and G10 FX for the desk header.

Equity benchmarks on the strip are futures, not cash indexes. Symbols were
checked against live Yahoo data on 2026-11-23. A row with no working contract
stays unavailable. Cash index tickers are not borrowed as a substitute, and a
stale or inconsistent futures print is not shown.

The change on a futures row is last price minus Yahoo's previous close. On the
contracts that quote, that previous close is the figure Yahoo itself uses for
regularMarketChange (the conventional prior settlement/close for that listing).

Verified futures
- E-mini S&P: ES=F, CME, quoteType FUTURE, "E-Mini S&P 500 Dec 26".
  Example print: 7085.5 vs previous close 6935.0, change +150.5.
- E-mini NASDAQ 100: NQ=F, CME, "Nasdaq 100 Dec 26" (CME NQ is the E-mini).
  Example print: 25859.25 vs 25126.5, change +732.75.
- Nikkei 225: NIY=F, CME Nikkei/Yen continuous. Osaka's contract has no Yahoo
  symbol. Example print: 56090 vs 54555, change +1535. SGX NK-Z26.SI quoted
  the same level with a different previous close, so the strip uses the
  continuous CME contract and its own previous close.
- SGX MSCI Singapore: front month among SGP-{month}.SI by share volume.
  On 2026-11-23 that was SGP-X26.SI (Nov, volume about 19k) over SGP-Z26.SI
  (Dec). Example print: 441.4 vs 444.6.

Checked and not used
- Euro Stoxx, DAX, FTSE 100: no Yahoo futures symbol (FESX, FDAX, FFI/Z).
- CSI 300 / 500 / 1000: no CFFEX futures symbol. Cash indexes are not used.
- KOSPI 200, TWSE/TAIEX, KLCI, SET50, GIFT Nifty: no live Yahoo futures symbol.
  SGX TWN-Z26.SI is FTSE Taiwan, not TWSE. SGX IN (old Nifty code) does not print.
- TOPIX: CME TPY=F still has a symbol, but on 2026-11-23 the last trade was
  2026-11-19, previous close equalled the price, and Yahoo's change did not.
  That quote is rejected. No Osaka TOPIX futures symbol was found.
- ASX 200: APZ6.AX is the December 2016 contract. No 2026 SPI symbol quoted.
- US 2-year: no cash Yahoo yield. 2YY=F is not the cash yield. The row stays
  on FRED DGS2. US 10-year stays on ^TNX. USD/JPY and AUD/USD stay cash FX.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from app.schemas import DashboardBoard, DashboardRow, DashboardSection, Meta, MoverRow, Movers, Quote
from app.symbols import equity_universe
from app.util import iso

_MONTH_CODES = "FGHJKMNQUVXZ"
_FUTURE_BASIS = "vs prior close"

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
    front_root: str | None = None
    front_suffix: str = ".SI"


def contract_candidates(root: str, suffix: str, today: date | None = None, count: int = 5) -> list[str]:
    """Nearest listed months for an exchange that has no continuous Yahoo symbol."""
    today = today or datetime.now(timezone.utc).date()
    year, month = today.year, today.month
    symbols: list[str] = []
    for _ in range(count):
        symbols.append(f"{root}-{_MONTH_CODES[month - 1]}{year % 100:02d}{suffix}")
        month += 1
        if month == 13:
            month = 1
            year += 1
    return symbols


STRIP: tuple[_Spec, ...] = (
    _Spec("E-mini S&P futures", "CME", "future", "ES=F", ("SPX", "S&P 500", "SP500", "ES"), basis=_FUTURE_BASIS),
    _Spec("E-mini NASDAQ 100 futures", "CME", "future", "NQ=F", ("NDX", "NASDAQ100", "NASDAQ 100", "NQ"), basis=_FUTURE_BASIS),
    _Spec(
        "Euro Stoxx futures",
        "Futures",
        "future",
        None,
        ("Eurostoxx", "STOXX50", "Euro Stoxx 50", "Euro Stoxx"),
        reason="No Yahoo futures symbol",
        link=False,
    ),
    _Spec("DAX futures", "Futures", "future", None, ("DAX",), reason="No Yahoo futures symbol", link=False),
    _Spec("FTSE 100 futures", "Futures", "future", None, ("FTSE", "FTSE100", "FTSE 100"), reason="No Yahoo futures symbol", link=False),
    _Spec("CSI 300 futures", "Futures", "future", None, ("CSI300", "CSI 300"), reason="No Yahoo futures symbol", link=False),
    _Spec("CSI 500 futures", "Futures", "future", None, ("CSI500", "CSI 500"), reason="No Yahoo futures symbol", link=False),
    _Spec("CSI 1000 futures", "Futures", "future", None, ("CSI1000", "CSI 1000"), reason="No Yahoo futures symbol", link=False),
    _Spec("KOSPI 200 futures", "Futures", "future", None, ("KOSPI", "KOSPI200", "KOSPI 200"), reason="No Yahoo futures symbol", link=False),
    _Spec("Nikkei 225 futures", "CME", "future", "NIY=F", ("Nikkei", "N225", "NIY"), basis=_FUTURE_BASIS),
    _Spec(
        "TOPIX futures",
        "Futures",
        "future",
        None,
        ("TOPIX", "TPX"),
        reason="No consistent Yahoo futures quote (CME TPY=F rejected)",
        link=False,
    ),
    _Spec("TWSE futures", "Futures", "future", None, ("TWSE", "TAIEX"), reason="No Yahoo futures symbol", link=False),
    _Spec(
        "ASX 200 futures",
        "Futures",
        "future",
        None,
        ("ASX200", "ASX 200", "SPI"),
        reason="No current Yahoo futures symbol",
        link=False,
    ),
    _Spec(
        "SGX MSCI Singapore futures",
        "SGX",
        "future",
        None,
        ("SGP", "MSCI Singapore", "SIMSCI"),
        reason="No live SGX front-month quote",
        link=True,
        basis=_FUTURE_BASIS,
        front_root="SGP",
    ),
    _Spec(
        "SGX GIFT Nifty 50 futures",
        "Futures",
        "future",
        None,
        ("GIFT", "GIFT Nifty", "Nifty"),
        reason="No Yahoo futures symbol",
        link=False,
    ),
    _Spec("Malaysia KLCI futures", "Futures", "future", None, ("KLCI", "FKLI"), reason="No Yahoo futures symbol", link=False),
    _Spec("Thailand SET50 futures", "Futures", "future", None, ("SET50",), reason="No Yahoo futures symbol", link=False),
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


def market_symbols(today: date | None = None) -> list[str]:
    """Yahoo symbols the strip and G10 board need. FRED rows and blank futures are omitted."""
    symbols: list[str] = []
    for spec in (*STRIP, *G10):
        if spec.provider != "yfinance":
            continue
        if spec.front_root:
            for symbol in contract_candidates(spec.front_root, spec.front_suffix, today):
                if symbol not in symbols:
                    symbols.append(symbol)
            continue
        if not spec.symbol:
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
        basis=spec.basis,
    )


def _usable(quote: Quote | None) -> Quote | None:
    if quote is None or quote.sample or quote.status != "ok" or quote.price is None:
        return None
    return quote


def _market_row(spec: _Spec, quote: Quote | None, *, attempted: set[str], live: bool) -> DashboardRow:
    if spec.symbol is None:
        return _blank(spec, "unavailable", spec.reason or "No public symbol")
    usable = _usable(quote)
    if usable is not None and (spec.asset_class != "future" or usable.previousClose not in (None, 0)):
        return _from_quote(spec, usable)
    if not live:
        return _blank(spec, "unavailable", "Live feed off")
    if spec.symbol not in attempted:
        return _blank(spec, "pending", None)
    return _blank(spec, "unavailable", spec.reason or "No live quote")


def _front_row(spec: _Spec, quotes: dict[str, Quote], *, attempted: set[str], live: bool) -> DashboardRow:
    """Highest-volume live month among the nearby contracts. Continuous symbols use `_market_row`."""
    candidates = contract_candidates(spec.front_root or "", spec.front_suffix)
    if not live:
        return _blank(spec, "unavailable", "Live feed off")
    usable: list[Quote] = []
    for symbol in candidates:
        quote = _usable(quotes.get(symbol))
        if quote is None or quote.previousClose in (None, 0):
            continue
        usable.append(quote)
    if usable:
        best = max(usable, key=lambda quote: (quote.volume or 0, quote.symbol))
        return _from_quote(spec, best, symbol=best.symbol)
    if not set(candidates).issubset(attempted):
        return _blank(spec, "pending", None)
    return _blank(spec, "unavailable", spec.reason or "No live front-month quote")


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
        elif spec.front_root:
            strip.append(_front_row(spec, quotes, attempted=attempted, live=live))
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
