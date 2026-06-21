from datetime import date

from app.attention import (
    build_attention,
    build_morning_attention_feed,
    build_opportunities,
    build_portfolio_status_item,
    build_recommended_actions,
    summarize,
)
from app.models import Holding


def test_attention_requires_actionable_thresholds():
    holdings = [
        Holding(
            source="Fidelity",
            account="Brokerage",
            symbol="CASH",
            name="Cash",
            asset_class="Cash",
            quantity=2500,
            price=1,
            market_value=2500,
            cost_basis=2500,
            as_of=date.today(),
        ),
        Holding(
            source="Fidelity",
            account="Brokerage",
            symbol="MSFT",
            name="Microsoft",
            asset_class="Technology",
            quantity=10,
            price=700,
            market_value=7000,
            cost_basis=8000,
            as_of=date.today(),
        ),
    ]

    summary = summarize(holdings)
    attention = build_attention(holdings, summary)
    opportunities = build_opportunities(holdings, summary, attention)

    titles = [item["title"] for item in attention]
    assert "$2,500 cash is available" in titles
    assert "Technology allocation is 73.7%" in titles
    assert "MSFT is 73.7% of the portfolio" in titles
    assert "MSFT is down 12.5% from cost basis" in titles
    classes = {item["title"]: item["classification"] for item in attention}
    assert classes["$2,500 cash is available"] == "action_required"
    assert classes["Technology allocation is 73.7%"] == "action_required"
    assert classes["MSFT is 73.7% of the portfolio"] == "action_required"
    assert classes["MSFT is down 12.5% from cost basis"] == "opportunity"
    assert opportunities[0]["title"] == "High cash position"

    recommended = build_recommended_actions(attention, opportunities, [])
    assert recommended[0]["title"] == "Deployable cash is elevated."
    assert recommended[0]["detail_id"] == "finance:cash"


def test_morning_attention_feed_appends_portfolio_status_from_backend():
    financial_attention = [
        {
            "title": "MSFT is down 12.5% from cost basis",
            "why_now": "Existing finance copy.",
            "action": "",
            "priority": 7,
            "detail_id": "finance:position:MSFT:pullback",
            "classification": "opportunity",
        }
    ]
    topic_attention = [
        {
            "title": "Yankees won last night",
            "why_now": "The win changed the series.",
            "action": "",
            "priority": 8,
            "detail_id": "topic:1",
            "classification": "awareness",
        }
    ]

    feed = build_morning_attention_feed([topic_attention], financial_attention)

    assert [item["title"] for item in feed] == [
        "Yankees won last night",
        "MSFT is down 12.5% from cost basis.",
    ]
    assert feed[1]["source"] == "portfolio"
    assert feed[1]["detail_id"] == "finance:position:MSFT:pullback"


def test_portfolio_status_item_has_empty_detail_when_no_portfolio_event():
    item = build_portfolio_status_item([])

    assert item == {
        "title": "No major portfolio actions currently identified.",
        "why_now": "No portfolio event is leading the morning brief.",
        "action": "",
        "priority": 0,
        "detail_id": "",
        "classification": "awareness",
        "source": "portfolio",
    }
