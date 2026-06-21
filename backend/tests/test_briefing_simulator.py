from app.briefing_simulator import layout_recommendation, run_simulation


def test_simulation_generates_required_scenarios():
    results = run_simulation(40)
    scenarios = {row["scenario"] for row in results}

    assert len(results) == 40
    assert "boring market day" in scenarios
    assert "market crash day" in scenarios
    assert "yankees playoff clinch" in scenarios
    assert "rutgers game week" in scenarios
    assert "vacation week" in scenarios
    assert "busy work week" in scenarios
    assert "no news day" in scenarios
    assert "ai breakthrough day" in scenarios
    assert "golf weather week" in scenarios
    assert "crypto crash day" in scenarios


def test_simulation_reveals_non_hero_days():
    results = run_simulation(40)
    layouts = {row["recommended_layout"] for row in results}

    assert "flat" in layouts or "quiet" in layouts
    assert "single_hero" in layouts or "major_event" in layouts
    assert any(row["static_hero_risk"] for row in results)


def test_layout_recommendation_does_not_force_hero_for_low_signal_day():
    layout = layout_recommendation(
        [
            {
                "importance_score": 42,
                "attention_section": "Around You",
                "story_type": "external",
            },
            {
                "importance_score": 38,
                "attention_section": "Background",
                "story_type": "external",
            },
            {
                "importance_score": 36,
                "attention_section": "Today",
                "story_type": "focusos",
            },
        ]
    )

    assert layout["mode"] == "flat"
