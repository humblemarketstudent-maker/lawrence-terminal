"""Transparent lexicon sentiment for headlines. Not a forecast."""

from __future__ import annotations

import re

BULLISH = {
    "beat": 2.0,
    "beats": 2.0,
    "surge": 2.2,
    "surges": 2.2,
    "soar": 2.2,
    "soars": 2.2,
    "rally": 1.6,
    "rallies": 1.6,
    "upgrade": 2.0,
    "upgrades": 2.0,
    "record": 1.1,
    "outperform": 1.6,
    "buyback": 1.4,
    "raises guidance": 2.4,
    "raise guidance": 2.4,
    "tops estimates": 2.0,
    "above consensus": 1.8,
    "all-time high": 1.5,
    "strong demand": 1.5,
    "rate cut": 1.6,
    "cuts rates": 1.6,
    "approval": 1.2,
    "breakthrough": 1.4,
    "profit": 0.7,
    "growth": 0.8,
    "bullish": 2.0,
    "inflows": 1.2,
    "expansion": 1.0,
}
BEARISH = {
    "miss": 2.0,
    "misses": 2.0,
    "plunge": 2.4,
    "plunges": 2.4,
    "downgrade": 2.0,
    "downgrades": 2.0,
    "layoff": 2.0,
    "layoffs": 2.0,
    "lawsuit": 1.5,
    "probe": 1.6,
    "investigation": 1.6,
    "recession": 2.0,
    "default": 2.0,
    "bankruptcy": 3.0,
    "warning": 1.2,
    "cuts guidance": 2.5,
    "cut guidance": 2.5,
    "slump": 1.6,
    "selloff": 2.0,
    "sell-off": 2.0,
    "bearish": 2.0,
    "fraud": 2.6,
    "halt": 1.4,
    "recall": 1.5,
    "weak demand": 1.6,
    "below consensus": 2.0,
    "miss estimates": 2.0,
    "inflation surprise": 1.5,
    "scrutiny": 1.3,
    "fine": 1.0,
}
ALERT_PATTERNS = [
    ("guidance", r"\bguidance\b"),
    ("M&A", r"\b(m&a|merger|merges|acquire|acquires|acquisition|buyout)\b"),
    ("rate cut", r"\brate cut\b|\bcuts rates\b|\brate cuts\b"),
    ("earnings", r"\bearnings\b|\bresults\b"),
    ("downgrade", r"\bdowngrades?\b"),
    ("upgrade", r"\bupgrades?\b"),
]


def score_text(text: str) -> dict:
    blob = text.lower()
    score = 0.0
    for phrase, weight in BULLISH.items():
        if phrase in blob:
            score += weight
    for phrase, weight in BEARISH.items():
        if phrase in blob:
            score -= weight
    keywords = [label for label, pattern in ALERT_PATTERNS if re.search(pattern, blob)]
    if score > 0.7:
        label = "BULLISH"
    elif score < -0.7:
        label = "BEARISH"
    else:
        label = "NEUTRAL"
    impact = int(min(100, round(abs(score) * 18 + (8 if keywords else 0))))
    if label == "NEUTRAL":
        impact = max(impact, 12 if keywords else 8)
    return {"sentiment": label, "impact": impact, "keywords": keywords, "score": round(score, 2)}
