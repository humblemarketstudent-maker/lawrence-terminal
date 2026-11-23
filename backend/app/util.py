"""Small shared helpers."""

from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime, timezone
from html import unescape


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(moment: datetime | None = None) -> str:
    return (moment or utcnow()).isoformat()


def num(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def clean_text(value: str | None, limit: int = 700) -> str:
    if not value:
        return ""
    text = unescape(re.sub(r"<[^>]+>", " ", value))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def stable_id(*parts: str) -> str:
    digest = hashlib.sha1("||".join(parts).encode()).hexdigest()
    return digest[:16]


def clean_person(name: str | None) -> str:
    if not name:
        return ""
    text = re.sub(r"\s+", " ", name).strip()
    return re.sub(r"^(Mr\.|Ms\.|Mrs\.|Dr\.)\s+", "", text)
