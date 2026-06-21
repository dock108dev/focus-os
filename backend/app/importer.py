from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation

from .models import Holding


class CSVImportError(ValueError):
    """Raised when an uploaded holdings CSV cannot be imported safely."""


ALIASES = {
    "symbol": {"symbol", "ticker"},
    "name": {"name", "description", "security", "security name"},
    "quantity": {"quantity", "qty", "shares"},
    "price": {"price", "last price", "current price"},
    "market_value": {"market value", "current value", "value", "total value"},
    "cost_basis": {"cost basis", "total cost", "cost", "cost basis total"},
    "account": {"account", "account name"},
    "asset_class": {"asset class", "type", "category"},
}


def normalize_header(value: str) -> str:
    return value.strip().lower().replace("_", " ")


def parse_decimal(value: str | None, field_name: str = "numeric field", row_number: int | None = None) -> Decimal:
    if value is None:
        return Decimal("0")
    cleaned = value.replace("$", "").replace(",", "").replace("%", "").strip()
    if cleaned in {"", "--", "n/a", "N/A"}:
        return Decimal("0")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = f"-{cleaned[1:-1]}"
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        row_prefix = f"Row {row_number}: " if row_number is not None else ""
        raise CSVImportError(f"{row_prefix}invalid {field_name} value {value!r}.") from None


def get_value(row: dict[str, str], canonical: str) -> str:
    aliases = ALIASES[canonical]
    for key, value in row.items():
        if normalize_header(key) in aliases:
            return value.strip()
    return ""


def parse_holdings_csv(raw: bytes, source: str) -> list[Holding]:
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    holdings: list[Holding] = []

    for row_number, row in enumerate(reader, start=2):
        symbol = get_value(row, "symbol").upper()
        name = get_value(row, "name")
        asset_class = get_value(row, "asset_class") or "Unknown"
        account = get_value(row, "account") or source
        quantity = parse_decimal(get_value(row, "quantity"), "quantity", row_number)
        price = parse_decimal(get_value(row, "price"), "price", row_number)
        market_value = parse_decimal(get_value(row, "market_value"), "market value", row_number)
        cost_basis = parse_decimal(get_value(row, "cost_basis"), "cost basis", row_number)

        if not symbol and ("cash" in name.lower() or asset_class.lower() == "cash"):
            symbol = "CASH"
        if not symbol and not name and market_value == 0:
            continue
        if market_value == 0 and quantity and price:
            market_value = quantity * price

        holdings.append(
            Holding(
                source=source,
                account=account,
                symbol=symbol or "UNKNOWN",
                name=name or symbol or "Unknown holding",
                asset_class=asset_class,
                quantity=quantity,
                price=price,
                market_value=market_value,
                cost_basis=cost_basis,
                as_of=date.today(),
            )
        )

    return holdings
