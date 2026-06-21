from app.attention_corpus import (
    DOMAIN_TARGETS,
    SIMULATION_DAYS,
    SIMULATION_START,
    build_may_june_simulation,
    classification_rules,
    corpus_summary,
    generate_event_corpus,
    watch_model,
)


def test_attention_corpus_meets_domain_targets():
    events = generate_event_corpus()
    summary = corpus_summary(events)

    assert summary["total_events"] == 1500
    assert summary["domain_counts"] == DOMAIN_TARGETS
    assert set(classification_rules()) == {
        "Deadline",
        "Opportunity",
        "Context Change",
        "Monitoring",
        "Maintenance",
        "Noise",
    }
    assert summary["evaluation_counts"]["Ignore"] > 0
    assert summary["evaluation_counts"]["Lead Story"] > 0
    assert 20 <= summary["evaluation_counts"]["Lead Story"] <= 30
    assert summary["unique_title_count"] >= 400


def test_watch_items_are_object_conditions_expiration_models():
    events = generate_event_corpus()
    watch_events = [event for event in events if event["domain"] == "Watch Items"]

    assert len(watch_events) == DOMAIN_TARGETS["Watch Items"]
    assert all("watch" in event for event in watch_events)
    assert all(event["watch"]["object"] for event in watch_events)
    assert all(event["watch"]["conditions"] for event in watch_events)
    assert all(event["watch"]["expiration"] for event in watch_events)
    assert watch_model()["definition"].startswith("A watch is object plus conditions")


def test_events_include_promotion_and_suppression_rules():
    events = generate_event_corpus()

    assert all("promotion_rules" in event for event in events)
    assert all("lead_story" in event["promotion_rules"] for event in events)
    assert all(event["suppression_rules"] for event in events)
    noise = [event for event in events if event["event_class"] == "Noise"]
    assert noise
    assert all(event["evaluation"] == "Ignore" for event in noise)


def test_corpus_models_mike_specific_attention_objects():
    events = generate_event_corpus()
    titles = "\n".join(event["title"] for event in events)
    domains = {event["domain"] for event in events}

    assert {"Dog", "Golf Equipment", "Books & Entertainment", "Health", "Life Logistics"} <= domains
    assert "repos still not migrated" in titles
    assert "Critical KEV now maps" in titles
    assert "Mortgage rates moved back below" in titles
    assert "UNH is down another" in titles
    assert "Bogey" in titles
    assert "TSA PreCheck renewal window opened" in titles


def test_may_june_simulation_covers_required_day_shapes():
    simulation = build_may_june_simulation(generate_event_corpus())

    assert len(simulation) == SIMULATION_DAYS
    assert simulation[0]["date"] == SIMULATION_START.isoformat()
    assert simulation[-1]["date"] == "2026-06-21"
    assert any(day["allows_no_spotlight"] for day in simulation)
    assert any(day["multiple_competing_focuses"] for day in simulation)
    assert any(day["dominant_domain"] == "Work" for day in simulation)
    assert any(day["dominant_domain"] == "Travel" for day in simulation)
    assert any(day["dominant_domain"] == "Finance & Markets" for day in simulation)
    assert sum(1 for day in simulation if day["allows_no_spotlight"]) >= 10
    assert len({day["scenario"] for day in simulation}) >= 45
