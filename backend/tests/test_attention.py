from datetime import date

from app.attention import (
    build_assistant_briefing,
    build_attention,
    build_morning_attention_feed,
    build_opportunities,
    build_portfolio_review_item,
    build_portfolio_status_item,
    build_recommended_actions,
    homepage_scan_violations,
    summarize,
)
from app.models import Holding
from app.watch_provenance import source_watch_id


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
    categories = {item["title"]: item["category"] for item in attention}
    assert categories["$2,500 cash is available"] == "action"
    assert categories["Technology allocation is 73.7%"] == "action"
    assert categories["MSFT is 73.7% of the portfolio"] == "action"
    assert categories["MSFT is down 12.5% from cost basis"] == "opportunity"
    assert all("importance_score" in item for item in attention)
    assert all("why_user_cares" in item for item in attention)
    assert opportunities[0]["title"] == "High cash position"

    recommended = build_recommended_actions(attention, opportunities, [])
    assert recommended[0]["title"] == "Deployable cash is elevated."
    assert recommended[0]["detail_id"] == "finance:cash"


def test_morning_attention_feed_collapses_portfolio_thresholds_before_awareness():
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
            "title": "MSFT is down 5.1% from its five-day high",
            "why_now": "Market pullback crossed the review range.",
            "action": "",
            "priority": 7,
            "source": "market",
            "detail_id": "market:MSFT:pullback",
            "category": "opportunity",
        },
        {
            "title": "Yankees won last night",
            "why_now": "The win changed the series.",
            "action": "",
            "priority": 8,
            "detail_id": "topic:1",
            "classification": "awareness",
        },
        {
            "title": "Bitcoin is up 1.5% over 24 hours",
            "why_now": "The move remains within normal volatility.",
            "action": "",
            "priority": 9,
            "source": "topic",
            "topic": "Bitcoin",
            "detail_id": "topic:2",
            "category": "awareness",
        },
    ]

    feed = build_morning_attention_feed([topic_attention], financial_attention)

    assert [item["title"] for item in feed] == [
        "Portfolio opportunity window is open",
        "Yankees won last night",
    ]
    assert feed[0]["category"] == "opportunity"
    assert feed[0]["vertical"] == "Portfolio"
    assert feed[0]["detail_id"] == "portfolio:review"
    assert feed[0]["signal_count"] == 2
    assert feed[0]["story_type"] == "focusos"
    assert feed[0]["source_watch_ids"] == [
        source_watch_id("Portfolio & market positioning")
    ]
    assert feed[0]["triggered_surface_rule"] == (
        "portfolio review threshold crossed"
    )
    assert feed[1]["story_type"] == "external"
    assert feed[1]["source_watch_ids"] == [source_watch_id("Yankees")]
    assert "Bitcoin is up 1.5% over 24 hours" not in [item["title"] for item in feed]


def test_portfolio_review_item_groups_financial_signals():
    item = build_portfolio_review_item(
        [
            {
                "title": "Technology allocation is 73.7%",
                "why_now": "Technology is above threshold.",
                "action": "",
                "priority": 9,
                "detail_id": "finance:technology",
                "category": "action",
                "importance_score": 91,
                "actionability_score": 86,
                "expiration_hours": 72,
            },
            {
                "title": "MSFT is down 12.5% from cost basis",
                "why_now": "Pullback threshold crossed.",
                "action": "",
                "priority": 7,
                "detail_id": "finance:position:MSFT:pullback",
                "category": "opportunity",
                "importance_score": 82,
                "actionability_score": 58,
                "expiration_hours": 72,
            },
        ]
    )

    assert item["title"] == "Review portfolio positioning"
    assert item["detail_id"] == "portfolio:review"
    assert item["signal_count"] == 2
    assert item["vertical"] == "Portfolio"
    assert "Technology concentration is above target" in item["why_now"]
    assert item["source_watch_ids"] == [
        source_watch_id("Portfolio & market positioning")
    ]


def test_homepage_scan_rules_reject_too_many_or_duplicate_domain_stories():
    valid_feed = [
        {
            "title": "Portfolio",
            "why_now": "Portfolio thresholds changed today.",
            "domain": "Portfolio",
        },
        {
            "title": "Golf",
            "why_now": "Wednesday is the best weather window.",
            "domain": "Life",
        },
        {
            "title": "Yankees",
            "why_now": "The result changed the division picture.",
            "domain": "Sports",
        },
    ]
    assert homepage_scan_violations(valid_feed) == []

    duplicate_domain = valid_feed + [
        {
            "title": "More sports",
            "why_now": "Another sports item with enough context.",
            "domain": "Sports",
        }
    ]
    assert "Sports" in homepage_scan_violations(duplicate_domain)[0]

    too_many = [
        {
            "title": f"Story {idx}",
            "why_now": "This story has enough context to stand alone.",
            "domain": f"D{idx}",
        }
        for idx in range(8)
    ]
    assert "3-7" in homepage_scan_violations(too_many)[0]


def test_portfolio_status_item_has_empty_detail_when_no_portfolio_event():
    item = build_portfolio_status_item([])

    assert item == {
        "title": "No major portfolio actions currently identified.",
        "why_now": "No portfolio event is leading the morning brief.",
        "action": "",
        "priority": 0,
        "detail_id": "",
        "category": "awareness",
        "importance_score": 35,
        "actionability_score": 0,
        "expiration_hours": 168,
        "why_user_cares": "Portfolio thresholds were checked and none require attention.",
        "classification": "awareness",
        "source": "portfolio",
    }


def test_assistant_briefing_does_not_manufacture_primary_focus_on_quiet_day():
    briefing = build_assistant_briefing(
        [
            {
                "title": "AI policy discussion stayed mostly procedural",
                "why_now": "Useful context, but not a shift that should dominate the morning.",
                "detail_id": "topic:1",
                "domain": "Technology",
                "category": "awareness",
                "importance_score": 48,
                "story_type": "external",
            },
            {
                "title": "No major portfolio actions currently identified.",
                "why_now": "No portfolio event is leading the morning brief.",
                "detail_id": "",
                "domain": "Portfolio",
                "category": "awareness",
                "importance_score": 35,
                "story_type": "focusos",
            },
        ]
    )

    assert briefing["mode"] == "quiet"
    assert briefing["primary_focus"]["title"] == "No single focus today"
    assert briefing["secondary_notes"][0]["title"] == (
        "AI policy discussion stayed mostly procedural"
    )


def test_assistant_briefing_promotes_one_primary_focus_and_three_notes():
    items = [
        {
            "title": "Review portfolio positioning",
            "why_now": "Technology exposure remains elevated and cash is available.",
            "detail_id": "portfolio:review",
            "domain": "Portfolio",
            "category": "action",
            "importance_score": 92,
            "story_type": "focusos",
        },
        *[
            {
                "title": f"Note {idx}",
                "why_now": "This is useful secondary context.",
                "detail_id": f"topic:{idx}",
                "domain": "Awareness",
                "category": "awareness",
                "importance_score": 60,
                "story_type": "external",
            }
            for idx in range(5)
        ],
    ]

    briefing = build_assistant_briefing(items, watch_status=[{"title": "WWDC"}])

    assert briefing["mode"] == "focused"
    assert briefing["primary_focus"]["title"] == "Review portfolio positioning"
    assert len(briefing["secondary_notes"]) == 3
    assert briefing["watch_status"] == [{"title": "WWDC"}]
