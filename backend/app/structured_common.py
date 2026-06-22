from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from decimal import InvalidOperation


HTTP_TIMEOUT = 15
SOURCE_REFRESH_EXCEPTIONS = (
    urllib.error.URLError,
    TimeoutError,
    json.JSONDecodeError,
    KeyError,
    IndexError,
    ValueError,
    TypeError,
    InvalidOperation,
)


def load_json(url: str, headers: dict[str, str] | None = None) -> dict:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Source URL must use http or https")
    request = urllib.request.Request(
        url, headers=headers or {"User-Agent": "FocusOS/0.1"}
    )
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:  # nosec B310
        return json.load(response)
