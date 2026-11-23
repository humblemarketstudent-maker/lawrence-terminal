"""Public RSS aggregation. Snippets and outbound links only — no article scraping."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import feedparser
import httpx

from app.book import _decorate_news
from app.util import iso

log = logging.getLogger(__name__)

UA = "APEX Terminal research@apex-terminal.local"

GLOBAL_FEEDS = [
    ("REUTERS", "https://news.google.com/rss/search?q=site:reuters.com+when:3d+(markets+OR+stocks+OR+Fed)&hl=en-US&gl=US&ceid=US:en"),
    ("BLOOMBERG", "https://news.google.com/rss/search?q=site:bloomberg.com+when:3d+(markets+OR+stocks)&hl=en-US&gl=US&ceid=US:en"),
    ("WSJ", "https://news.google.com/rss/search?q=site:wsj.com+when:3d+(markets+OR+stocks+OR+Fed)&hl=en-US&gl=US&ceid=US:en"),
    ("YAHOO", "https://news.google.com/rss/search?q=site:finance.yahoo.com+when:3d+(stocks+OR+markets)&hl=en-US&gl=US&ceid=US:en"),
]


def _google_url(query: str) -> str:
    return "https://news.google.com/rss/search?" + str(httpx.QueryParams({"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}))


def feeds_for_ticker(symbol: str) -> list[tuple[str, str]]:
    root = symbol.split(".")[0].replace("^", "")
    return [
        ("WIRE", _google_url(f"{root} stock when:7d")),
        ("YAHOO", f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={root}&region=US&lang=en-US"),
    ]


async def _read_feed(client: httpx.AsyncClient, source: str, url: str) -> list[dict]:
    response = await client.get(url)
    response.raise_for_status()
    parsed = feedparser.parse(response.content)
    items = []
    for entry in parsed.entries[:14]:
        title = getattr(entry, "title", "") or ""
        if not title:
            continue
        published = None
        stamp = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
        if stamp:
            published = datetime(*stamp[:6], tzinfo=timezone.utc).isoformat()
        link = getattr(entry, "link", "") or ""
        resolved = source
        blob = f"{title} {link}".lower()
        if "fool.com" in blob or "motley" in blob:
            continue
        if source == "YAHOO" and "yahoo" not in blob and "finance.yahoo.com" not in blob:
            # Yahoo's headline RSS syndicates third parties. Keep only Yahoo-hosted items.
            if "yahoo" not in title.lower():
                continue
        items.append(
            {
                "headline": title,
                "source": resolved,
                "url": link,
                "publishedAt": published or iso(),
                "summary": getattr(entry, "summary", "") or "",
            }
        )
    return items


async def fetch_news(symbol: str | None = None) -> list:
    feeds = list(GLOBAL_FEEDS)
    if symbol:
        feeds.extend(feeds_for_ticker(symbol))
    raw: list[dict] = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=4.0), follow_redirects=True, headers={"User-Agent": UA}) as client:
        for source, url in feeds:
            try:
                raw.extend(await _read_feed(client, source, url))
            except Exception as exc:
                log.warning("news feed %s failed: %s", source, exc)
    items = _decorate_news(raw, sample=False)
    if symbol:
        root = symbol.split(".")[0].lstrip("^").upper()
        matched = [item for item in items if symbol in item.tickers or root in item.headline.upper() or symbol in item.headline.upper()]
        if len(matched) >= 3:
            return matched
    return items
