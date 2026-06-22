from app.attention_corpus import (
    DOMAIN_TARGETS,
    SIMULATION_DAYS,
    SIMULATION_START,
    build_may_june_simulation,
    classification_rules,
    configured_watches,
    corpus_summary,
    generate_event_corpus,
    planning_layers,
    preset_quality_reviews,
    watch_quality_reviews,
    watch_model,
    watch_presets,
)


def test_attention_corpus_meets_domain_targets():
    events = generate_event_corpus()
    summary = corpus_summary(events)

    assert summary["total_events"] == 1500
    assert summary["configured_watch_count"] == len(configured_watches())
    assert summary["valid_watch_count"] == len(configured_watches())
    assert summary["valid_preset_count"] == len(watch_presets())
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
    assert summary["unique_title_count"] >= 350


def test_configured_watches_are_source_of_truth_attention_config():
    layers = planning_layers()
    watches = configured_watches()
    model = watch_model()

    assert set(layers) == {"Configured Watches", "Generated Events", "Briefing Outputs"}
    assert model["definition"].startswith("A watch is user-authored attention infrastructure")
    assert set(model["required_fields"]) == {
        "object",
        "conditions",
        "sources",
        "cadence",
        "surface_rules",
        "suppression_rules",
        "expiration",
        "preferred_output",
    }
    assert len(watches) >= 10
    for watch in watches:
        assert watch["object"]
        assert watch["conditions"]
        assert watch["sources"]
        assert watch["cadence"]
        assert watch["surface_rules"]
        assert watch["suppression_rules"]
        assert watch["expiration"]
        assert watch["preferred_output"]

    watch_names = {watch["name"] for watch in watches}
    assert {
        "Bitcoin range",
        "UNH watch",
        "Mortgage rates",
        "Bogey care",
        "Yankees and Rutgers",
        "Golf weather and equipment",
        "Work migrations",
        "Side projects",
        "Home maintenance",
        "Family dates",
    } <= watch_names

    preset_names = {preset["name"] for preset in watch_presets()}
    assert {
        "Markets",
        "Sports teams",
        "Travel",
        "Family dates",
        "Home maintenance",
        "Pets",
        "Medical appointments",
        "Work projects",
        "Side projects",
        "Tech interests",
    } <= preset_names
    assert all(preset["created_watch_id"].startswith("watch:") for preset in watch_presets())


def test_watch_quality_review_validates_silent_surface_and_suppression():
    reviews = watch_quality_reviews()

    assert len(reviews) == len(configured_watches())
    assert all(review["valid"] for review in reviews)
    for review in reviews:
        assert all(review["criteria"].values())
        assert review["outcomes"]["silent_monitoring"]
        assert review["outcomes"]["useful_surface"]
        assert review["outcomes"]["explicit_suppression"]

    reviews_by_name = {review["name"]: review for review in reviews}
    for name in {
        "Bitcoin range",
        "Work migrations",
        "Family dates",
        "Bogey care",
        "Health admin",
        "Side projects",
        "WWDC and coding tools",
    }:
        outcomes = reviews_by_name[name]["outcomes"]
        assert outcomes["silent_monitoring"]
        assert outcomes["useful_surface"]
        assert outcomes["explicit_suppression"]


def test_watch_presets_create_editable_valid_watches():
    reviews = preset_quality_reviews()

    assert len(reviews) == len(watch_presets())
    assert all(review["valid"] for review in reviews)
    assert all(review["criteria"]["creates_editable_watch"] for review in reviews)
    assert all(review["criteria"]["does_not_create_fixed_category"] for review in reviews)


def test_generated_events_do_not_blur_configured_watches_into_event_domain():
    events = generate_event_corpus()

    assert "Watch Items" not in {event["domain"] for event in events}
    assert all(event["domain"] in DOMAIN_TARGETS for event in events)


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


def test_simulation_primary_focus_is_lead_story_only_and_unique():
    events = generate_event_corpus()
    events_by_id = {event["id"]: event for event in events}
    simulation = build_may_june_simulation(events)

    for day in simulation:
        assert len(day["selected_event_ids"]) == len(set(day["selected_event_ids"]))
        if day["primary_focus_id"] is not None:
            primary_event = events_by_id[day["primary_focus_id"]]
            assert primary_event["evaluation"] == "Lead Story"

    days_by_date = {day["date"]: day for day in simulation}
    assert days_by_date["2026-05-23"]["primary_focus_id"] is None
    assert days_by_date["2026-06-04"]["primary_focus_id"] is None
    assert days_by_date["2026-06-16"]["primary_focus_id"] is None


def test_briefing_outputs_are_traceable_to_configured_watches():
    events = generate_event_corpus()
    event_ids = {event["id"] for event in events}
    watch_ids = {watch["id"] for watch in configured_watches()}
    outputs = [
        output
        for day in build_may_june_simulation(events)
        for output in day["briefing_outputs"]
    ]

    assert len(outputs) >= 10
    for output in outputs[:10]:
        assert output["event_id"] in event_ids
        assert output["source_watch_ids"]
        assert set(output["source_watch_ids"]) <= watch_ids
        assert output["triggered_surface_rule"]
        assert output["suppressed_by"] is None
        assert output["why_today"]
