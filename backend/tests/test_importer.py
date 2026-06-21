import pytest

from app.importer import CSVImportError, parse_holdings_csv


def test_parse_holdings_csv_rejects_malformed_numeric_values():
    raw = b"symbol,name,quantity,price,market value,cost basis\nMSFT,Microsoft,ten,430,4300,4000\n"

    with pytest.raises(CSVImportError, match="Row 2: invalid quantity value 'ten'"):
        parse_holdings_csv(raw, source="Manual")


def test_parse_holdings_csv_allows_common_blank_placeholders():
    raw = b"symbol,name,quantity,price,market value,cost basis\nCASH,Cash,--,n/a,1000,\n"

    holdings = parse_holdings_csv(raw, source="Manual")

    assert len(holdings) == 1
    assert holdings[0].quantity == 0
    assert holdings[0].price == 0
    assert holdings[0].market_value == 1000
