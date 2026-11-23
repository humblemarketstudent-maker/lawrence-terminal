"""Live company-view fields that are not on the saved snapshot.

Turnover, the calendar, and peer rows are built from public Yahoo payloads.
Nothing here invents a GICS code, a peer, or an FX rate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.schemas import CompanyEvent, PeerRow
from app.symbols import bloomberg_label, name_for
from app.util import num

# Quoted minor units. The price is divided by `divisor` before FX conversion.
_MINOR = {"GBp": ("GBP", 100.0), "GBX": ("GBP", 100.0), "ZAc": ("ZAR", 100.0)}

TAXONOMY_SOURCE = "Yahoo Finance sector and industry. An official GICS code is not in the public feed."
DESCRIPTION_SOURCE = "Yahoo Finance business summary"


@dataclass(frozen=True)
class Turnover:
    local: float | None
    local_currency: str | None
    usd: float | None
    pair: str | None
    fx_rate: float | None
    status: str
    reason: str | None


def price_currency(currency: str | None) -> tuple[str, float]:
    """Major currency and the divisor that turns the quoted price into major units."""
    code = currency or "USD"
    if code in _MINOR:
        major, divisor = _MINOR[code]
        return major, divisor
    return code, 1.0


def dollar_volume(
    price: float | None,
    volume: float | None,
    currency: str | None,
    *,
    usd_per_major: float | None,
    pair: str | None,
) -> Turnover:
    """Share turnover in USD. `usd_per_major` is dollars per one major currency unit."""
    if price is None or price <= 0 or volume is None or volume <= 0:
        return Turnover(None, None, None, None, None, "unavailable", "No price and volume for dollar turnover.")
    major, divisor = price_currency(currency)
    local = price / divisor * volume
    if major == "USD":
        return Turnover(local, "USD", local, "USD", 1.0, "ok", None)
    if usd_per_major is None or usd_per_major <= 0:
        return Turnover(local, major, None, None, None, "unavailable", f"No FX rate to convert {major} turnover into USD.")
    return Turnover(local, major, local * usd_per_major, pair, usd_per_major, "ok", None)


def _as_dates(value: object) -> list[date]:
    if value is None:
        return []
    if isinstance(value, list):
        found: list[date] = []
        for item in value:
            found.extend(_as_dates(item))
        return found
    if isinstance(value, datetime):
        return [value.date()]
    if isinstance(value, date):
        return [value]
    text = str(value).strip()
    if not text or text in {"None", "NaT"}:
        return []
    try:
        return [date.fromisoformat(text[:10])]
    except ValueError:
        return []


def upcoming_events(calendar: dict | None, earnings: list[dict] | None, today: date) -> list[CompanyEvent]:
    """Future earnings and dividend dates only. Past prints are not shown as upcoming."""
    events: list[CompanyEvent] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, label: str, day: date, detail: str | None) -> None:
        if day < today:
            return
        key = (kind, day.isoformat())
        if key in seen:
            return
        seen.add(key)
        events.append(CompanyEvent(kind=kind, label=label, date=day.isoformat(), detail=detail))  # type: ignore[arg-type]

    for row in earnings or []:
        for day in _as_dates(row.get("date")):
            estimate = num(row.get("epsEstimate"))
            detail = f"EPS est {estimate:.2f}" if estimate is not None else None
            add("earnings", "Earnings", day, detail)
    cal = calendar or {}
    for day in _as_dates(cal.get("Earnings Date")):
        add("earnings", "Earnings", day, None)
    for day in _as_dates(cal.get("Ex-Dividend Date")):
        add("ex-dividend", "Ex-dividend", day, None)
    for day in _as_dates(cal.get("Dividend Date")):
        add("dividend", "Dividend", day, None)
    events.sort(key=lambda item: (item.date, item.kind))
    return events[:4]


def _growth_percent(value: object) -> float | None:
    number = num(value)
    if number is None:
        return None
    if abs(number) <= 2:
        return number * 100.0
    return number


def live_peer(info: dict | None) -> PeerRow | None:
    """One peer from a live Yahoo quote payload. Rows without a price are dropped."""
    info = info or {}
    symbol = str(info.get("symbol") or "").upper()
    price = num(info.get("regularMarketPrice"))
    if not symbol or price is None:
        return None
    currency = info.get("currency") if isinstance(info.get("currency"), str) else None
    return PeerRow(
        symbol=symbol,
        name=name_for(symbol, info.get("shortName") or info.get("longName")),
        label=bloomberg_label(symbol),
        marketCap=num(info.get("marketCap")),
        trailingPE=num(info.get("trailingPE")),
        forwardPE=num(info.get("forwardPE")),
        evEbitda=num(info.get("enterpriseToEbitda")),
        priceBook=num(info.get("priceToBook")),
        revenueGrowth=_growth_percent(info.get("revenueGrowth")),
        price=price,
        change=num(info.get("regularMarketChange")),
        changePct=num(info.get("regularMarketChangePercent")),
        currency=currency,
        status="ok",
    )


def peer_rows(infos: list[dict] | None) -> list[PeerRow]:
    rows: list[PeerRow] = []
    seen: set[str] = set()
    for info in infos or []:
        row = live_peer(info)
        if row is None or row.symbol in seen:
            continue
        seen.add(row.symbol)
        rows.append(row)
    return rows
