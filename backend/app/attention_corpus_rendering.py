from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import timedelta
from pathlib import Path
from typing import Iterable

from .attention_corpus_generation import generate_event_corpus
from .attention_corpus_models import SIMULATION_DAYS, SIMULATION_START
from .attention_corpus_quality import (
    configured_watches,
    corpus_summary,
    planning_layers,
    preset_quality_reviews,
    watch_presets,
    watch_quality_reviews,
)
from .attention_corpus_simulation import (
    build_may_june_simulation,
    classification_rules,
    watch_model,
)

def render_rules_markdown(summary: dict) -> str:
    lines = [
        "# FocusOS Personal Attention Corpus (Mike v2)",
        "",
        "Purpose: validate the attention model against Mike-specific reality before any new UI work.",
        "",
        "## Corpus Summary",
        "",
        f"- Total events: {summary['total_events']}",
        f"- Configured watches: {summary['configured_watch_count']}",
        f"- Valid watches: {summary['valid_watch_count']}",
        f"- Valid presets: {summary['valid_preset_count']}",
        f"- Unique titles: {summary['unique_title_count']}",
        f"- Lead-story candidates: {summary['evaluation_counts']['Lead Story']}",
        "",
        "## Planning Layers",
        "",
    ]
    for name, description in planning_layers().items():
        lines.append(f"- {name}: {description}")
    lines.extend(
        [
            "",
            "## Configured Watches",
            "",
            "Configured watches are the user's source-of-truth attention config. The daily briefing is downstream of this layer.",
            "",
        ]
    )
    for watch in configured_watches():
        lines.extend(
            [
                f"### {watch['name']}",
                "",
                f"- Object: {watch['object']}",
                f"- Conditions: {', '.join(watch['conditions'])}",
                f"- Sources: {', '.join(watch['sources'])}",
                f"- Cadence: {watch['cadence']}",
                f"- Surface when: {'; '.join(watch['surface_rules'])}",
                f"- Do not surface: {'; '.join(watch['suppression_rules'])}",
                f"- Expire: {watch['expiration']}",
                f"- Preferred output: {watch['preferred_output']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Onboarding Presets",
            "",
            "Presets create editable watches. They are not fixed categories.",
            "",
        ]
    )
    for preset in watch_presets():
        lines.extend(
            [
                f"- {preset['name']}: creates {preset['creates_watch']} ({preset['created_watch_id']})",
            ]
        )
    lines.extend([""])
    lines.extend(
        [
            "## Watch Quality Review",
            "",
            "Each configured watch must support silent monitoring, useful surface, and explicit suppression before UI work continues.",
            "",
        ]
    )
    for review in watch_quality_reviews():
        outcomes = review["outcomes"]
        lines.extend(
            [
                f"### {review['name']}",
                "",
                f"- Valid: {'yes' if review['valid'] else 'no'}",
                f"- Silent: {outcomes['silent_monitoring']}",
                f"- Surface: {outcomes['useful_surface']}",
                f"- Suppress: {outcomes['explicit_suppression']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Preset Quality Review",
            "",
        ]
    )
    for review in preset_quality_reviews():
        lines.append(
            f"- {review['preset']}: {'valid' if review['valid'] else 'needs work'}; creates {review['created_watch_id']}"
        )
    lines.extend([""])
    lines.extend(
        [
            "## Generated Events Summary",
            "",
        "### Domains",
        "",
        ]
    )
    for domain, count in summary["domain_counts"].items():
        lines.append(f"- {domain}: {count}")
    lines.extend(["", "### Event Classes", ""])
    for name, rule in classification_rules().items():
        lines.append(f"- {name}: {rule}")
    lines.extend(
        [
            "",
            "## Generation Standard",
            "",
            "- Keep the taxonomy, ranking model, and watch admin model.",
            "- Generate events downstream of configured watches and other sources.",
            "- Keep configured watches, generated events, and briefing outputs separate.",
            "- Generate around attention objects users actually care about: counts, expirations, thresholds, people, pets, travel, hobbies, and posture changes.",
            "- Do not treat project names, launch names, or generic categories as events by themselves.",
            "- Lead stories are intentionally rare: target 20-30 candidates in a 1500-event corpus.",
            "- Briefing outputs must include source_watch_ids, triggered_surface_rule, suppressed_by, and why_today.",
            "",
            "## Promotion Model",
            "",
            "- Ignore: never show unless the event stops being noise.",
            "- Monitor: track silently; no briefing item.",
            "- Mention: one-line briefing item.",
            "- Surface: important enough to appear in the briefing.",
            "- Lead Story: eligible for primary focus, but only when the day truly has a dominant context.",
            "",
            "## Suppression Model",
            "",
            "- Suppress routine sports results, minor market moves, generic launch coverage, and news without a personal decision hook.",
            "- Suppress repeated items when nothing changed since the last evaluation.",
            "- Suppress any item whose value is merely informational and not context-restoring.",
            "",
            "## Watch Admin Model",
            "",
            json.dumps(watch_model(), indent=2),
            "",
            "## Simulation",
            "",
            "The companion May-June 2026 simulation intentionally includes boring days, no-primary-focus days, competing-focus days, and watch-driven outputs that land in real domains rather than a Watch Items domain.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_simulation_markdown(days: Iterable[dict]) -> str:
    rows = list(days)
    scenario_counts = Counter(row["scenario"] for row in rows)
    lines = [
        "# FocusOS Personal Attention Simulation (May-June 2026)",
        "",
        "Purpose: review the Mike v2 attention model across realistic mornings before changing UI.",
        "",
        "## Summary",
        "",
        f"- Simulated days: {len(rows)}",
        f"- Unique scenarios: {len(scenario_counts)}",
        f"- No-spotlight days: {sum(1 for row in rows if row['allows_no_spotlight'])}",
        f"- Competing-focus days: {sum(1 for row in rows if row['multiple_competing_focuses'])}",
        "",
        "## Days",
        "",
    ]
    for row in rows:
        primary = row["primary_focus_title"] or "Nothing deserves the spotlight today."
        lines.extend(
            [
                f"### {row['date']}: {row['scenario'].title()}",
                "",
                f"- Dominant domain: {row['dominant_domain'] or 'None'}",
                f"- Primary focus: {primary}",
                f"- Selected events: {len(row['selected_event_ids'])}",
                f"- Suppressed events: {len(row['suppressed_event_ids'])}",
                f"- Review note: {row['review_note']}",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def write_artifacts(output_dir: Path) -> tuple[Path, Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    events = generate_event_corpus()
    simulation = build_may_june_simulation(events)
    corpus_path = output_dir / "personal-attention-corpus-mike-v1.json"
    simulation_path = output_dir / "personal-attention-simulation-may-june-2026.json"
    simulation_markdown_path = (
        output_dir / "personal-attention-simulation-may-june-2026.md"
    )
    rules_path = output_dir / "personal-attention-corpus-mike-v1.md"
    corpus_payload = {
        "version": "mike-v2",
        "purpose": "Personal context restoration and attention management model validation.",
        "planning_layers": planning_layers(),
        "configured_watches": configured_watches(),
        "watch_presets": watch_presets(),
        "watch_quality_reviews": watch_quality_reviews(),
        "preset_quality_reviews": preset_quality_reviews(),
        "summary": corpus_summary(events),
        "classification_rules": classification_rules(),
        "watch_model": watch_model(),
        "generated_events": events,
        "events": events,
    }
    simulation_payload = {
        "version": "mike-v2",
        "planning_layers": planning_layers(),
        "date_range": {
            "start": SIMULATION_START.isoformat(),
            "end": (SIMULATION_START + timedelta(days=SIMULATION_DAYS - 1)).isoformat(),
            "days": SIMULATION_DAYS,
        },
        "briefing_outputs": {
            "definition": "Each day contains selected_event_ids, briefing_outputs, and an optional primary_focus_id. Non-selected generated events remain candidates only.",
            "required_provenance_fields": [
                "source_watch_ids",
                "triggered_surface_rule",
                "suppressed_by",
                "why_today",
            ],
        },
        "days": simulation,
    }
    corpus_path.write_text(
        json.dumps(corpus_payload, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    simulation_path.write_text(
        json.dumps(simulation_payload, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    simulation_markdown_path.write_text(
        render_simulation_markdown(simulation), encoding="utf-8"
    )
    rules_path.write_text(render_rules_markdown(corpus_summary(events)), encoding="utf-8")
    return corpus_path, simulation_path, simulation_markdown_path, rules_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Mike v2 attention corpus artifacts.")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/simulations"))
    args = parser.parse_args()
    for path in write_artifacts(args.output_dir):
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
