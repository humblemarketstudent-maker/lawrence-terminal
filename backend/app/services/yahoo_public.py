"""Public Yahoo payloads that do not need a crumb.

Chart and the quote page stay readable when quoteSummary (Ticker.info) comes
back empty, which is what production saw for futures and for AAPL fundamentals.
Numbers are taken only from those payloads. A missing field stays missing.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from app.schemas import Quote
from app.symbols import bloomberg_label, classify, currency_for, exchange_for
from app.util import iso, num

_NUMBER = r"[+-]?(?:\d+\.\d+|\d+)(?:[eE][+-]?\d+)?"
_MEASURES = {
    "trailingForwardPeRatio": "forwardPE",
    "trailingPbRatio": "priceToBook",
    "trailingPeRatio": "trailingPE",
}


def _prior_session_close(price: float, closes: list[float]) -> float | None:
    """Previous session close from daily bars, when the bars actually contain one."""
    usable = [value for value in closes if value is not None and value > 0]
    if len(usable) < 2:
        return None
    tolerance = max(0.05, abs(price) * 1e-3)
    if abs(usable[-1] - price) <= tolerance:
        return usable[-2]
    # The live print is ahead of the last completed bar. That bar is the prior close
    # when it is still in the same neighbourhood as the print.
    if abs(usable[-1] - price) / price < 0.2:
        return usable[-1]
    return None


def session_change(
    price: float,
    closes: list[float] | None,
    fullday_change: float | None,
) -> tuple[float | None, float | None]:
    """Previous close and change for one print.

    The prior daily close is used when the chart has it. Yahoo's `fulldayChange`
    is the same figure when the chart meta omits `previousClose` (futures do).
    When both exist and agree, the prior bar is kept. When only `fulldayChange`
    exists, the previous close is price minus that change. No number is guessed
    beyond those two sources.
    """
    prior = _prior_session_close(price, list(closes or []))
    if prior is not None:
        return prior, price - prior
    if fullday_change is not None and price - fullday_change > 0:
        return price - fullday_change, fullday_change
    return None, None


def quote_from_chart(symbol: str, result: dict | None, *, futures_only: bool = False) -> Quote | None:
    """Build a quote from a v8 chart result. Last price does not require a previous close."""
    if not result:
        return None
    meta = result.get("meta") or {}
    instrument = str(meta.get("instrumentType") or "").upper()
    if futures_only and instrument != "FUTURE":
        return None
    price = num(meta.get("regularMarketPrice"))
    if price is None or price <= 0:
        return None
    traded = num(meta.get("regularMarketTime"))
    if traded is not None:
        age_days = (datetime.now(timezone.utc).timestamp() - traded) / 86400.0
        if age_days > 5:
            return None
    block = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    closes = [value for value in (num(item) for item in (block.get("close") or [])) if value is not None and value > 0]
    previous, change = session_change(price, closes, num(meta.get("fulldayChange")))
    change_pct = change / previous * 100.0 if change is not None and previous else None
    name = meta.get("shortName") or meta.get("longName") or symbol
    currency = meta.get("currency") if isinstance(meta.get("currency"), str) else currency_for(symbol)
    exchange = meta.get("exchangeName") if isinstance(meta.get("exchangeName"), str) else exchange_for(symbol)
    volume = num(meta.get("regularMarketVolume"))
    asset = "future" if instrument == "FUTURE" else classify(symbol)
    return Quote(
        symbol=symbol,
        name=str(name),
        label=bloomberg_label(symbol),
        assetClass=asset,
        currency=currency or "USD",
        exchange=exchange or "",
        price=price,
        change=change,
        changePct=change_pct,
        previousClose=previous,
        volume=volume if volume and volume > 0 else None,
        status="ok",
        sample=False,
        asOf=iso(),
    )


def _raw_number(html: str, key: str) -> float | None:
    match = re.search(rf'{re.escape(key)}\\":\{{\\"raw\\":({_NUMBER})', html)
    if not match:
        match = re.search(rf'"{re.escape(key)}":\{{"raw":({_NUMBER})', html)
    if not match:
        return None
    return num(match.group(1))


def _raw_string(html: str, key: str) -> str | None:
    match = re.search(rf'{re.escape(key)}\\":\\"((?:\\\\.|[^\\])*?)\\"', html)
    if not match:
        match = re.search(rf'"{re.escape(key)}":"((?:\\.|[^"\\])*)"', html)
    if not match:
        return None
    text = match.group(1).replace('\\"', '"').replace("\\n", " ").replace("\\\\", "\\")
    text = " ".join(text.split()).strip()
    return text or None


def parse_quote_page(html: str | None) -> dict:
    """Sector, description, and valuation fields embedded in the public quote page."""
    if not html:
        return {}
    fields = {
        "forwardPE": _raw_number(html, "forwardPE"),
        "priceToBook": _raw_number(html, "priceToBook"),
        "trailingPE": _raw_number(html, "trailingPE"),
        "beta": _raw_number(html, "beta"),
        "longBusinessSummary": _raw_string(html, "longBusinessSummary"),
        "sector": _raw_string(html, "sector"),
        "industry": _raw_string(html, "industry"),
        "longName": _raw_string(html, "longName"),
        "shortName": _raw_string(html, "shortName"),
        "currency": _raw_string(html, "currency"),
    }
    return {key: value for key, value in fields.items() if value not in (None, "")}


def parse_timeseries_latest(payload: dict | None) -> dict:
    """Latest trailing forward P/E, P/B, and trailing P/E from the fundamentals series."""
    found: dict[str, tuple[str, float]] = {}
    for item in ((payload or {}).get("timeseries") or {}).get("result") or []:
        if not isinstance(item, dict):
            continue
        for type_name, field in _MEASURES.items():
            points = item.get(type_name)
            if not isinstance(points, list):
                continue
            for point in points:
                if not isinstance(point, dict):
                    continue
                value = num((point.get("reportedValue") or {}).get("raw"))
                as_of = str(point.get("asOfDate") or "")
                if value is None:
                    continue
                current = found.get(field)
                if current is None or as_of >= current[0]:
                    found[field] = (as_of, value)
    return {field: pair[1] for field, pair in found.items()}


def fill_missing(base: dict | None, extra: dict | None) -> dict:
    merged = dict(base or {})
    for key, value in (extra or {}).items():
        if value in (None, "", []):
            continue
        if merged.get(key) in (None, "", []):
            merged[key] = value
    return merged


def peer_info_from_quote(quote: Quote, measures: dict | None = None) -> dict:
    """Shape a chart quote the way the live peer row reader expects."""
    measures = measures or {}
    return {
        "symbol": quote.symbol,
        "shortName": quote.name,
        "regularMarketPrice": quote.price,
        "regularMarketChange": quote.change,
        "regularMarketChangePercent": quote.changePct,
        "currency": quote.currency,
        "forwardPE": measures.get("forwardPE"),
        "priceToBook": measures.get("priceToBook"),
        "trailingPE": measures.get("trailingPE"),
    }
