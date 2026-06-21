from __future__ import annotations

import re


CARE_PATTERNS = [
    re.compile(r"\bwhy Mike should care[:,]?\s*", re.IGNORECASE),
    re.compile(r"\bMike should care because\s*", re.IGNORECASE),
    re.compile(r"\bMike should care[:,]?\s*", re.IGNORECASE),
    re.compile(r"\bwhy this matters[:,]?\s*", re.IGNORECASE),
]


def clean_editorial_text(value: str | None) -> str:
    if not value:
        return ""

    text = value.strip()
    for pattern in CARE_PATTERNS:
        text = pattern.sub("", text)

    text = text.replace(
        "The 24-hour move is large enough to monitor but does not create a trading instruction.",
        "The 24-hour move remains within normal volatility.",
    )
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""

    return text[0].upper() + text[1:]


def clean_action_text(value: str | None) -> str:
    text = clean_editorial_text(value)
    if re.match(r"^(review|consider|decide)\s+whether\b", text, re.IGNORECASE):
        return ""
    return text
