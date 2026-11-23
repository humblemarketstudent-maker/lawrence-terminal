"""Short company descriptions for the DES page.

Google's HTML search from this server is a JavaScript wall, so a readable
snippet is used when one is actually present and otherwise the Wikipedia
summary is used. The source string says which one it was. The text is clipped
to a couple of sentences.
"""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import quote

_UA = "APEX Terminal research@apex-terminal.local"
_DROP = {
    "inc", "incorporated", "corp", "corporation", "ltd", "limited", "plc", "holdings",
    "holding", "group", "company", "co", "sa", "ag", "nv", "se", "the", "and", "of",
}
_GOOGLE_SOURCE = "Google search result"
_WIKI_SOURCE = "Wikipedia summary. Google search did not return a readable description from this server."


def clip_sentences(text: str, sentences: int = 2, limit: int = 420) -> str:
    cleaned = " ".join(unescape(text).split()).strip()
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]
    chosen = " ".join(parts[:sentences]) if parts else cleaned
    if len(chosen) <= limit:
        return chosen
    cut = chosen[:limit]
    space = cut.rfind(" ")
    body = cut[:space] if space > 40 else cut
    return body.rstrip(" ,;:") + "…"


def google_snippet(html: str | None) -> str | None:
    """A knowledge-panel or result snippet, only when the page actually contains one."""
    if not html:
        return None
    if "enablejs" in html and "kno-rdesc" not in html and 'data-attrid="description"' not in html:
        return None
    patterns = (
        r'class="kno-rdesc"[^>]*>.*?<span[^>]*>(.*?)</span>',
        r'data-attrid="description"[^>]*>.*?<span[^>]*>(.*?)</span>',
        r'<div class="BNeawe s3v9rd AP7Wnd">(.*?)</div>',
    )
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.S)
        if not match:
            continue
        text = clip_sentences(re.sub(r"<[^>]+>", " ", match.group(1)))
        if len(text) >= 40:
            return text
    return None


def _tokens(value: str) -> set[str]:
    words = re.findall(r"[A-Za-z0-9]+", value.lower())
    return {word for word in words if word not in _DROP and len(word) >= 3}


def titles_match(company: str, title: str) -> bool:
    left, right = _tokens(company), _tokens(title)
    if not left or not right:
        return False
    return bool(left & right)


def _get(url: str, params: dict | None = None) -> object | None:
    try:
        from curl_cffi import requests

        response = requests.get(url, params=params, headers={"User-Agent": _UA, "Accept-Language": "en"}, timeout=12, impersonate="chrome")
        if response.status_code != 200:
            return None
        content = response.headers.get("content-type") or ""
        if "json" in content or url.endswith(".json") or "api.php" in url or "/page/summary/" in url:
            return response.json()
        return response.text
    except Exception:
        return None


def _wikipedia_extract(name: str) -> str | None:
    found = _get(
        "https://en.wikipedia.org/w/api.php",
        {"action": "opensearch", "search": name, "limit": 3, "namespace": 0, "format": "json"},
    )
    titles = found[1] if isinstance(found, list) and len(found) > 1 and isinstance(found[1], list) else []
    for title in titles:
        if not isinstance(title, str) or not titles_match(name, title):
            continue
        payload = _get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title.replace(' ', '_'))}")
        extract = payload.get("extract") if isinstance(payload, dict) else None
        if isinstance(extract, str) and len(extract.strip()) >= 40:
            return clip_sentences(extract)
    return None


def company_description(name: str) -> tuple[str | None, str | None]:
    """Short description and an honest source label. Neither field is invented."""
    query = " ".join(name.split())
    if not query:
        return None, None
    page = _get("https://www.google.com/search", {"q": query, "hl": "en", "gbv": "1"})
    snippet = google_snippet(page if isinstance(page, str) else None)
    if snippet:
        return snippet, _GOOGLE_SOURCE
    extract = _wikipedia_extract(query)
    if extract:
        return extract, _WIKI_SOURCE
    return None, None
