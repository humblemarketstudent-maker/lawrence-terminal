"""Desk morning note assembled from whatever the cache currently trusts."""

from __future__ import annotations

from app.schemas import Brief, EcoBoard, NewsItem, Quote, WeiBoard
from app.util import iso, utcnow


def _px(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{value:,.{digits}f}"


def _pct(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def _bp(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f} bp"


def build_brief(
    quotes: list[Quote],
    news: list[NewsItem],
    wei: WeiBoard,
    eco: EcoBoard,
    *,
    sample: bool,
) -> Brief:
    moment = utcnow()
    stamp = moment.strftime("%A, %d %B %Y  %H:%M UTC")
    lines = [
        "APEX TERMINAL — MORNING BRIEF",
        stamp,
        "Internal desk note. Data may be delayed, cached, or fixture-backed. Not an order or recommendation.",
        "",
        "LAST SESSION — WORLD INDICES",
    ]
    equities = [point for point in wei.points if point.group == "equity"]
    if not equities:
        lines.append("  Index monitor unavailable.")
    for point in equities:
        lines.append(f"  {point.name:<22} {_px(point.value):>12}   {_pct(point.changePct):>8}")
    lines += ["", "RATES & DOLLAR"]
    for point in wei.points:
        if point.group == "rate":
            lines.append(f"  {point.name:<22} {_px(point.value):>8}%   {_bp(point.changeBp):>10}")
        elif point.group == "fx" and point.symbol == "DX-Y.NYB":
            lines.append(f"  {point.name:<22} {_px(point.value):>12}   {_pct(point.changePct):>8}")
    if wei.spread2s10s is not None:
        lines.append(f"  {'2s10s':<22} {_px(wei.spread2s10s):>8}%   {_bp(wei.spreadChangeBp):>10}")
    lines += ["", "COMMODITIES & CRYPTO"]
    for point in wei.points:
        if point.group in {"commodity", "crypto"}:
            lines.append(f"  {point.name:<22} {_px(point.value, 2 if point.group == 'commodity' else 0):>12}   {_pct(point.changePct):>8}")
    lines += ["", "TOP HEADLINES"]
    for index, item in enumerate(_pick_headlines(news), start=1):
        tags = ", ".join(item.keywords) if item.keywords else item.sentiment.lower()
        lines.append(f"  {index}. [{item.source}] {item.headline}")
        lines.append(f"     {item.sentiment}  impact {item.impact}  {tags}  {item.publishedAt}")
    if not news:
        lines.append("  Wire empty.")
    lines += ["", "WATCHLIST MOVERS"]
    ranked = [quote for quote in quotes if quote.changePct is not None and quote.status == "ok"]
    ranked.sort(key=lambda quote: abs(quote.changePct or 0), reverse=True)
    if not ranked:
        lines.append("  No quote changes in the cache.")
    for quote in ranked[:8]:
        lines.append(
            f"  {quote.symbol:<10} {_px(quote.price):>12}   {_pct(quote.changePct):>8}   {quote.name}"
        )
    if eco.series:
        lines += ["", "MACRO LATEST"]
        for series in eco.series:
            lines.append(f"  {series.name:<22} {_px(series.value):>8} {series.unit}")
    lines += [
        "",
        "NOTES",
        "  Headlines are RSS titles and snippets with links back to the publisher.",
        "  Sentiment is a lexicon score, not a model forecast.",
        "  Consensus on the economic calendar is a desk sample unless a keyed macro feed is configured.",
        "  — APEX Terminal",
    ]
    title = f"APEX Morning Brief — {moment.strftime('%d %b %Y')}"
    return Brief(generatedAt=iso(moment), title=title, markdown="\n".join(lines), sample=sample)


def _pick_headlines(news: list[NewsItem]) -> list[NewsItem]:
    ranked = sorted(news, key=lambda item: (item.breaking, bool(item.keywords), item.impact), reverse=True)
    picked: list[NewsItem] = []
    seen: set[str] = set()
    for item in ranked:
        if item.source in seen and len(picked) < 4:
            continue
        picked.append(item)
        seen.add(item.source)
        if len(picked) == 5:
            break
    if len(picked) < 5:
        for item in ranked:
            if item not in picked:
                picked.append(item)
            if len(picked) == 5:
                break
    return picked
