from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Iterable

from .attention import (
    build_morning_attention_feed,
    homepage_scan_violations,
)
from .briefing_simulator_helpers import SimulatedScenario
from .briefing_simulator_scenarios import scenario_catalog

def build_simulated_days(total_days: int = 50) -> list[SimulatedScenario]:
    catalog = scenario_catalog()
    return [catalog[index % len(catalog)] for index in range(total_days)]


def layout_recommendation(feed: list[dict]) -> dict:
    if not feed:
        return {"mode": "empty", "reason": "No stories passed the attention filter."}

    scores = [int(item.get("importance_score") or 0) for item in feed]
    top_score = max(scores)
    top_item = max(feed, key=lambda item: int(item.get("importance_score") or 0))
    today_count = sum(1 for item in feed if item.get("attention_section") == "Today")
    focusos_count = sum(1 for item in feed if item.get("story_type") == "focusos")

    if top_score >= 95:
        return {
            "mode": "major_event",
            "reason": "One signal is strong enough to dominate the whole page.",
        }
    if (
        top_score >= 86
        and today_count <= 1
        and top_item.get("suggested_posture") != "Ignore"
    ):
        return {
            "mode": "single_hero",
            "reason": "A single high-signal item deserves a hero treatment.",
        }
    if top_score >= 72 and today_count >= 2:
        return {
            "mode": "two_lead",
            "reason": "Two meaningful items should share the top of the page.",
        }
    if top_score < 72 and focusos_count >= 1:
        return {
            "mode": "flat",
            "reason": "No item is strong enough to force a hero; use a flat briefing.",
        }
    return {"mode": "quiet", "reason": "The day is mostly background context."}


def evaluate_day(day_number: int, scenario: SimulatedScenario) -> dict:
    feed = build_morning_attention_feed([scenario.topical], scenario.financial)
    layout = layout_recommendation(feed)
    scan_violations = homepage_scan_violations(feed)
    scores = [int(item.get("importance_score") or 0) for item in feed]
    average_score = round(mean(scores), 1) if scores else 0
    return {
        "day": day_number,
        "scenario": scenario.name,
        "notes": scenario.notes,
        "recommended_layout": layout["mode"],
        "layout_reason": layout["reason"],
        "average_importance": average_score,
        "max_importance": max(scores) if scores else 0,
        "story_count": len(feed),
        "focusos_story_count": sum(
            1 for item in feed if item.get("story_type") == "focusos"
        ),
        "external_story_count": sum(
            1 for item in feed if item.get("story_type") == "external"
        ),
        "static_hero_risk": layout["mode"] in {"flat", "quiet", "two_lead"},
        "scan_violations": scan_violations,
        "stories": [
            {
                "section": item.get("attention_section"),
                "domain": item.get("domain"),
                "title": item.get("title"),
                "summary": item.get("why_now"),
                "posture": item.get("suggested_posture"),
                "story_type": item.get("story_type"),
                "importance_score": item.get("importance_score"),
            }
            for item in feed
        ],
    }


def run_simulation(total_days: int = 50) -> list[dict]:
    return [
        evaluate_day(index + 1, scenario)
        for index, scenario in enumerate(build_simulated_days(total_days))
    ]


def render_markdown(results: Iterable[dict]) -> str:
    rows = list(results)
    layout_counts: dict[str, int] = {}
    for row in rows:
        layout_counts[row["recommended_layout"]] = (
            layout_counts.get(row["recommended_layout"], 0) + 1
        )

    lines = [
        f"# FocusOS {len(rows)}-Day Briefing Simulation",
        "",
        "Purpose: validate whether ranking and layout assumptions hold across many mornings before changing UI again.",
        "",
        "## Summary",
        "",
        f"- Simulated days: {len(rows)}",
        f"- Layout recommendations: {', '.join(f'{key}={value}' for key, value in sorted(layout_counts.items()))}",
        f"- Days where a static hero may overstate importance: {sum(1 for row in rows if row['static_hero_risk'])}",
        f"- Days with scan-rule violations: {sum(1 for row in rows if row['scan_violations'])}",
        "",
        "## Manual Review Questions",
        "",
        "For each day, ask:",
        "",
        "1. Does the top story deserve top placement?",
        "2. Should the layout have a hero, two leads, or a flat briefing?",
        "3. Are Type B FocusOS stories carrying the value, or is this drifting back into news?",
        "4. Does anything feel overstated or understated?",
        "",
        "## Simulated Days",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"### Day {row['day']}: {row['scenario'].title()}",
                "",
                f"- Notes: {row['notes']}",
                f"- Recommended layout: `{row['recommended_layout']}`",
                f"- Why: {row['layout_reason']}",
                f"- Signal: max={row['max_importance']}, avg={row['average_importance']}, stories={row['story_count']}, TypeB={row['focusos_story_count']}, TypeA={row['external_story_count']}",
            ]
        )
        if row["scan_violations"]:
            lines.append(f"- Scan issues: {'; '.join(row['scan_violations'])}")
        lines.append("")
        for story in row["stories"]:
            lines.append(
                f"- **{story['section']} / {story['domain']} / {story['posture']} / {story['story_type']}**: {story['title']} - {story['summary']}"
            )
        lines.append("")
    return "\n".join(lines)


def write_simulation_artifacts(total_days: int, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results = run_simulation(total_days)
    json_path = output_dir / "attention-simulation.json"
    markdown_path = output_dir / "attention-simulation.md"
    json_path.write_text(
        json.dumps(results, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(render_markdown(results) + "\n", encoding="utf-8")
    return json_path, markdown_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic FocusOS briefing days."
    )
    parser.add_argument("--days", type=int, default=50)
    parser.add_argument("--output-dir", type=Path, default=Path("docs/simulations"))
    args = parser.parse_args()
    json_path, markdown_path = write_simulation_artifacts(args.days, args.output_dir)
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")


if __name__ == "__main__":
    main()
