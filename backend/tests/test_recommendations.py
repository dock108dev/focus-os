from app.recommendations import recommendation_detail


class EmptySession:
    pass


def test_malformed_market_detail_returns_not_found_payload():
    detail = recommendation_detail(EmptySession(), "market:MSFT")

    assert detail["title"] == "Recommendation not found"
    assert detail["id"] == "market:MSFT"
