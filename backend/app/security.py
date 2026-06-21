from __future__ import annotations

import os
from collections.abc import Iterable

from fastapi import Header, HTTPException, Request, status
from starlette.responses import Response


DEFAULT_CORS_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CSV_CONTENT_TYPES = {"text/csv", "application/csv", "application/vnd.ms-excel"}


def configured_cors_origins() -> list[str]:
    configured = os.getenv("FOCUSOS_CORS_ORIGINS", "")
    if not configured.strip():
        return list(DEFAULT_CORS_ORIGINS)
    return [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]


def max_import_bytes() -> int:
    value = os.getenv("FOCUSOS_MAX_IMPORT_BYTES", str(1024 * 1024))
    try:
        return max(int(value), 1)
    except ValueError:
        return 1024 * 1024


def require_allowed_origin(request: Request, allowed_origins: Iterable[str]) -> None:
    origin = request.headers.get("origin")
    if request.method not in UNSAFE_METHODS or not origin:
        return
    if origin.rstrip("/") not in set(allowed_origins):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin is not allowed.")


def validate_csv_upload(content_type: str | None, filename: str | None, size: int, max_size: int) -> None:
    normalized_type = (content_type or "").split(";", 1)[0].strip().lower()
    normalized_name = (filename or "").lower()
    if normalized_type and normalized_type not in CSV_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload must be a CSV file.")
    if normalized_name and not normalized_name.endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload filename must end in .csv.")
    if size > max_size:
        raise HTTPException(status_code=413, detail="CSV upload is too large.")


async def require_internal_api_key(x_focusos_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("FOCUSOS_INTERNAL_API_KEY")
    if not expected:
        return
    if not x_focusos_key or x_focusos_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal API key.")


def apply_security_headers(response: Response) -> None:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cache-Control", "no-store")
    if os.getenv("FOCUSOS_ENABLE_HSTS", "").lower() in {"1", "true", "yes"}:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
