from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable

from .attention import (
    build_morning_attention_feed,
    homepage_scan_violations,
)


@dataclass(frozen=True)
class SimulatedScenario:
    name: str
    notes: str
    financial: list[dict]
    topical: list[dict]


def signal(
    title: str,
    why_now: str,
    *,
    category: str,
    source: str,
    topic: str | None = None,
    priority: int = 5,
    importance: int | None = None,
    actionability: int | None = None,
    detail_id: str | None = None,
    story_type: str | None = None,
) -> dict:
    return {
        "title": title,
        "why_now": why_now,
        "action": "",
        "priority": priority,
        "source": source,
        "topic": topic,
        "detail_id": detail_id
        or f"sim:{source}:{title.lower().replace(' ', '-')[:60]}",
        "category": category,
        "importance_score": importance if importance is not None else priority * 10,
        "actionability_score": actionability if actionability is not None else 10,
        "expiration_hours": 72 if category in {"action", "opportunity"} else 168,
        "why_user_cares": why_now,
        "story_type": story_type,
    }


def finance_signal(
    title: str,
    why_now: str,
    *,
    category: str = "action",
    priority: int = 8,
    importance: int = 86,
) -> dict:
    return signal(
        title,
        why_now,
        category=category,
        source="portfolio",
        topic="portfolio",
        priority=priority,
        importance=importance,
        actionability=80 if category == "action" else 54,
        detail_id=f"finance:sim:{title.lower().replace(' ', '-')[:50]}",
        story_type="focusos",
    )


def scenario_catalog() -> list[SimulatedScenario]:
    return [
        SimulatedScenario(
            "normal tuesday",
            "Low-signal day where a forced hero would overstate importance.",
            [],
            [
                signal(
                    "Wednesday is likely your best golf window this week",
                    "Forecast conditions are materially better than the rest of the week.",
                    category="opportunity",
                    source="weather",
                    topic="Golf",
                    priority=7,
                    importance=76,
                    actionability=48,
                    story_type="focusos",
                ),
                signal(
                    "Yankees won 5-0",
                    "Good result, but no meaningful change to your posture today.",
                    category="awareness",
                    source="topic",
                    topic="Yankees",
                    priority=5,
                    importance=45,
                ),
                signal(
                    "AI policy discussion stayed mostly procedural",
                    "Useful context, but not a shift that should dominate the morning.",
                    category="awareness",
                    source="topic",
                    topic="AI",
                    priority=5,
                    importance=48,
                ),
            ],
        ),
        SimulatedScenario(
            "boring market day",
            "Portfolio is stable; external context should not inflate the page.",
            [],
            [
                signal(
                    "Markets were quiet overnight",
                    "No configured portfolio or market threshold changed.",
                    category="awareness",
                    source="market",
                    topic="Bitcoin",
                    priority=4,
                    importance=35,
                ),
                signal(
                    "Yankees had a scheduled off day",
                    "Nothing changed in the season picture.",
                    category="awareness",
                    source="topic",
                    topic="Yankees",
                    priority=4,
                    importance=35,
                ),
                signal(
                    "Golf forecast remains playable but ordinary",
                    "No day is materially better than the rest of the week.",
                    category="awareness",
                    source="weather",
                    topic="Golf",
                    priority=4,
                    importance=42,
                    story_type="focusos",
                ),
            ],
        ),
        SimulatedScenario(
            "market crash day",
            "Major portfolio day where a dominant hero is justified.",
            [
                finance_signal(
                    "Technology allocation dropped 9.0% in one session",
                    "A large move changed portfolio risk and rebalancing context.",
                    importance=96,
                ),
                finance_signal(
                    "MSFT crossed drawdown threshold",
                    "MSFT moved from ordinary volatility into a review zone.",
                    category="opportunity",
                    priority=8,
                    importance=88,
                ),
                finance_signal(
                    "Cash reserve is below target after market move",
                    "Available cash no longer covers the configured reserve target.",
                    importance=90,
                ),
            ],
            [
                signal(
                    "Bitcoin fell 14.0% over 24 hours",
                    "Crypto moved into a review range, but it belongs inside the portfolio state.",
                    category="opportunity",
                    source="crypto",
                    topic="Bitcoin",
                    priority=8,
                    importance=86,
                ),
                signal(
                    "Yankees won 4-2",
                    "Good result, no meaningful change to season outlook.",
                    category="awareness",
                    source="topic",
                    topic="Yankees",
                    priority=4,
                    importance=36,
                ),
            ],
        ),
        SimulatedScenario(
            "crypto crash day",
            "Crypto should matter only when it changes the user's portfolio posture.",
            [
                finance_signal(
                    "BTC crossed drawdown threshold",
                    "Bitcoin moved from background tracking into a portfolio review zone.",
                    category="opportunity",
                    priority=8,
                    importance=86,
                ),
                finance_signal(
                    "Cash remains deployable",
                    "Cash is above reserve threshold during a crypto drawdown.",
                    category="opportunity",
                    priority=7,
                    importance=79,
                ),
            ],
            [
                signal(
                    "Bitcoin fell 18.0% over 24 hours",
                    "The move is large enough to affect portfolio review context.",
                    category="opportunity",
                    source="crypto",
                    topic="Bitcoin",
                    priority=8,
                    importance=84,
                ),
                signal(
                    "AI product launches were routine",
                    "No material change to the AI landscape.",
                    category="awareness",
                    source="topic",
                    topic="AI",
                    priority=4,
                    importance=38,
                ),
            ],
        ),
        SimulatedScenario(
            "no news day",
            "Tests whether the layout can avoid inventing a hero.",
            [],
            [
                signal(
                    "No major portfolio actions currently identified",
                    "Portfolio thresholds were checked and none require attention.",
                    category="awareness",
                    source="portfolio",
                    topic="portfolio",
                    priority=3,
                    importance=34,
                    story_type="focusos",
                ),
                signal(
                    "Golf forecast is ordinary this week",
                    "No day stands out enough to plan around.",
                    category="awareness",
                    source="weather",
                    topic="Golf",
                    priority=3,
                    importance=36,
                    story_type="focusos",
                ),
                signal(
                    "Yankees schedule is quiet",
                    "No result or injury materially changes the outlook.",
                    category="awareness",
                    source="topic",
                    topic="Yankees",
                    priority=3,
                    importance=34,
                ),
            ],
        ),
        SimulatedScenario(
            "golf weather week",
            "A Type B life-planning item should lead if portfolio is quiet.",
            [],
            [
                signal(
                    "Thursday is likely your best golf window this month",
                    "Forecast conditions are materially better than the rest of the ten-day window.",
                    category="opportunity",
                    source="weather",
                    topic="Golf",
                    priority=8,
                    importance=82,
                    actionability=56,
                    story_type="focusos",
                ),
                signal(
                    "Portfolio thresholds remain quiet",
                    "No allocation or drawdown threshold changed.",
                    category="awareness",
                    source="portfolio",
                    topic="portfolio",
                    priority=3,
                    importance=34,
                    story_type="focusos",
                ),
                signal(
                    "AI funding news stayed incremental",
                    "No major capability or access shift.",
                    category="awareness",
                    source="topic",
                    topic="AI",
                    priority=4,
                    importance=40,
                ),
            ],
        ),
        SimulatedScenario(
            "yankees playoff clinch",
            "Sports can matter when it changes context, but should not feel like a task.",
            [],
            [
                signal(
                    "Yankees clinched a playoff spot",
                    "This changes the season context and upcoming stakes.",
                    category="awareness",
                    source="topic",
                    topic="Yankees",
                    priority=8,
                    importance=72,
                ),
                signal(
                    "Portfolio thresholds remain quiet",
                    "No portfolio review condition changed.",
                    category="awareness",
                    source="portfolio",
                    topic="portfolio",
                    priority=3,
                    importance=34,
                    story_type="focusos",
                ),
                signal(
                    "Weekend golf weather is playable",
                    "Conditions are fine but not meaningfully better than alternatives.",
                    category="awareness",
                    source="weather",
                    topic="Golf",
                    priority=4,
                    importance=42,
                    story_type="focusos",
                ),
            ],
        ),
        SimulatedScenario(
            "yankees routine win",
            "Routine sports reporting should recede or be omitted.",
            [],
            [
                signal(
                    "Yankees won 6-3",
                    "Good result, but no meaningful change to your posture today.",
                    category="awareness",
                    source="topic",
                    topic="Yankees",
                    priority=4,
                    importance=36,
                ),
                signal(
                    "Wednesday is likely your best golf window this week",
                    "Forecast conditions are better than the rest of the week.",
                    category="opportunity",
                    source="weather",
                    topic="Golf",
                    priority=7,
                    importance=76,
                    story_type="focusos",
                ),
                signal(
                    "AI regulation discussion stayed unresolved",
                    "Worth tracking, but no new decision context.",
                    category="awareness",
                    source="topic",
                    topic="AI",
                    priority=5,
                    importance=46,
                ),
            ],
        ),
        SimulatedScenario(
            "rutgers game week",
            "A personal calendar-adjacent item should outrank generic news.",
            [],
            [
                signal(
                    "Rutgers game week needs a plan",
                    "Kickoff, travel, and ticket timing make this a real planning item.",
                    category="action",
                    source="rutgers",
                    topic="Rutgers",
                    priority=8,
                    importance=84,
                    actionability=78,
                    story_type="focusos",
                ),
                signal(
                    "Portfolio thresholds remain quiet",
                    "No portfolio state changed.",
                    category="awareness",
                    source="portfolio",
                    topic="portfolio",
                    priority=3,
                    importance=34,
                    story_type="focusos",
                ),
                signal(
                    "Yankees won 5-4",
                    "Good result, no meaningful change to season outlook.",
                    category="awareness",
                    source="topic",
                    topic="Yankees",
                    priority=4,
                    importance=36,
                ),
            ],
        ),
        SimulatedScenario(
            "rutgers tickets renew friday",
            "Deadline-like personal item should be Today, but not corporate.",
            [],
            [
                signal(
                    "Rutgers tickets renew Friday",
                    "The window closes soon, so this belongs on your radar today.",
                    category="action",
                    source="rutgers",
                    topic="Rutgers",
                    priority=9,
                    importance=88,
                    actionability=86,
                    story_type="focusos",
                ),
                signal(
                    "Golf weather is ordinary",
                    "No day is clearly better than the rest.",
                    category="awareness",
                    source="weather",
                    topic="Golf",
                    priority=3,
                    importance=34,
                    story_type="focusos",
                ),
                signal(
                    "AI model news was incremental",
                    "No major access or capability shift.",
                    category="awareness",
                    source="topic",
                    topic="AI",
                    priority=4,
                    importance=40,
                ),
            ],
        ),
        SimulatedScenario(
            "vacation week",
            "Travel planning should lead when dates create risk.",
            [],
            [
                signal(
                    "Vacation departure needs a travel check",
                    "Weather and airport timing could affect departure planning.",
                    category="action",
                    source="travel",
                    topic="Travel",
                    priority=8,
                    importance=86,
                    actionability=80,
                    story_type="focusos",
                ),
                signal(
                    "Portfolio thresholds remain quiet",
                    "No review condition changed while travel is approaching.",
                    category="awareness",
                    source="portfolio",
                    topic="portfolio",
                    priority=3,
                    importance=34,
                    story_type="focusos",
                ),
                signal(
                    "Yankees start a normal series",
                    "No special stakes beyond the schedule.",
                    category="awareness",
                    source="topic",
                    topic="Yankees",
                    priority=4,
                    importance=36,
                ),
            ],
        ),
        SimulatedScenario(
            "busy work week",
            "Work context should dominate only if inactivity or deadline signals exist.",
            [],
            [
                signal(
                    "Two projects have been inactive for 10 days",
                    "This may create hidden drag if it is not reviewed.",
                    category="action",
                    source="work",
                    topic="Work",
                    priority=8,
                    importance=84,
                    actionability=78,
                    story_type="focusos",
                ),
                signal(
                    "Wednesday is a good golf window",
                    "Good weather exists, but work context may constrain timing.",
                    category="opportunity",
                    source="weather",
                    topic="Golf",
                    priority=6,
                    importance=68,
                    story_type="focusos",
                ),
                signal(
                    "AI policy news remains background",
                    "Worth knowing, not a near-term decision.",
                    category="awareness",
                    source="topic",
                    topic="AI",
                    priority=4,
                    importance=42,
                ),
            ],
        ),
        SimulatedScenario(
            "ai breakthrough day",
            "External news can lead if the signal is genuinely high.",
            [],
            [
                signal(
                    "AI capability jump changes tool landscape",
                    "A major model release may affect which tools are worth using this week.",
                    category="awareness",
                    source="topic",
                    topic="AI",
                    priority=9,
                    importance=88,
                ),
                signal(
                    "Portfolio thresholds remain quiet",
                    "No portfolio review condition changed.",
                    category="awareness",
                    source="portfolio",
                    topic="portfolio",
                    priority=3,
                    importance=34,
                    story_type="focusos",
                ),
                signal(
                    "Golf forecast is ordinary",
                    "No strong planning window emerged.",
                    category="awareness",
                    source="weather",
                    topic="Golf",
                    priority=3,
                    importance=34,
                    story_type="focusos",
                ),
            ],
        ),
        SimulatedScenario(
            "iran escalation day",
            "World news should be Background unless it changes practical posture.",
            [],
            [
                signal(
                    "Iran escalation raises oil and travel risk",
                    "The situation may affect markets and travel planning, but no personal action is implied yet.",
                    category="awareness",
                    source="topic",
                    topic="Iran",
                    priority=8,
                    importance=76,
                ),
                signal(
                    "Portfolio thresholds remain quiet",
                    "No portfolio review condition changed.",
                    category="awareness",
                    source="portfolio",
                    topic="portfolio",
                    priority=3,
                    importance=34,
                    story_type="focusos",
                ),
                signal(
                    "Yankees won 2-1",
                    "Good result, no meaningful change to season outlook.",
                    category="awareness",
                    source="topic",
                    topic="Yankees",
                    priority=4,
                    importance=36,
                ),
            ],
        ),
        SimulatedScenario(
            "major event day",
            "Single external event may justify one dominant story.",
            [],
            [
                signal(
                    "Major market closure disrupts normal trading",
                    "This changes how portfolio signals should be interpreted today.",
                    category="action",
                    source="market",
                    topic="Markets",
                    priority=10,
                    importance=98,
                    actionability=88,
                ),
                signal(
                    "Travel advisory issued for vacation route",
                    "The advisory could affect departure timing.",
                    category="action",
                    source="travel",
                    topic="Travel",
                    priority=8,
                    importance=86,
                    actionability=78,
                    story_type="focusos",
                ),
                signal(
                    "Yankees game postponed",
                    "Schedule changed, but no broader season impact.",
                    category="awareness",
                    source="topic",
                    topic="Yankees",
                    priority=4,
                    importance=36,
                ),
            ],
        ),
        SimulatedScenario(
            "liquidity warning day",
            "Liquid cash below target should become Needs attention.",
            [
                finance_signal(
                    "Liquid cash is below the $10,000 target",
                    "Available liquid cash is close enough to the configured target to change spending and runway posture.",
                    importance=92,
                ),
            ],
            [
                signal(
                    "Opinion-only market chatter stayed noisy",
                    "No verified price or thesis change was attached to the chatter.",
                    category="awareness",
                    source="market",
                    topic="Markets",
                    priority=3,
                    importance=30,
                ),
            ],
        ),
        SimulatedScenario(
            "github action queue day",
            "Public repo health should create a practical action queue.",
            [],
            [
                signal(
                    "focus-os has an automated PR",
                    "An automated PR is open and likely quick to review.",
                    category="action",
                    source="github",
                    topic="github",
                    priority=8,
                    importance=84,
                    actionability=74,
                    story_type="focusos",
                ),
                signal(
                    "Archived repo emitted noise",
                    "Archived repositories are explicitly suppressed.",
                    category="awareness",
                    source="github",
                    topic="github",
                    priority=2,
                    importance=20,
                ),
            ],
        ),
        SimulatedScenario(
            "shopping media quiet day",
            "Shopping and media should remain optional unless tied to saved interests.",
            [],
            [
                signal(
                    "Generic sale stayed quiet",
                    "No saved product or target price matched the deal.",
                    category="awareness",
                    source="shopping",
                    topic="Shopping",
                    priority=2,
                    importance=24,
                ),
                signal(
                    "High-confidence media match is available",
                    "A short recommendation matches known preferences and current availability.",
                    category="awareness",
                    source="media",
                    topic="Media",
                    priority=5,
                    importance=58,
                ),
            ],
        ),
        SimulatedScenario(
            "life reminder action day",
            "User-entered personal admin should surface when the warning window opens.",
            [],
            [
                signal(
                    "Bogey medication refill enters warning window",
                    "The user-entered refill date is close enough to avoid a scramble.",
                    category="action",
                    source="watchlist",
                    topic="Life",
                    priority=9,
                    importance=90,
                    actionability=84,
                    story_type="focusos",
                ),
                signal(
                    "Undated note stayed quiet",
                    "The note has no action window or posture change.",
                    category="awareness",
                    source="watchlist",
                    topic="Life",
                    priority=2,
                    importance=22,
                    story_type="focusos",
                ),
            ],
        ),
    ]


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
    json_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
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
