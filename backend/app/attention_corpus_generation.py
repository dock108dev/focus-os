from __future__ import annotations

from datetime import timedelta

from .attention_corpus_models import (
    AttentionScenario,
    DOMAIN_TARGETS,
    LEAD_STORY_TARGET,
    SIMULATION_DAYS,
    SIMULATION_START,
)
from .attention_corpus_quality import (
    source_watch_ids_for_event,
    suppressed_by_for_event,
    triggered_surface_rule_for_event,
)
from .attention_corpus_scenarios import SCENARIOS
from .attention_corpus_templates import SLOT_BANKS, TITLE_CONTEXTS

def values_for(index: int, global_index: int) -> dict:
    values = {
        key: bank[(index + global_index) % len(bank)]
        for key, bank in SLOT_BANKS.items()
    }
    values["date"] = (SIMULATION_START + timedelta(days=index % SIMULATION_DAYS)).isoformat()
    return values


def render_template(template: str, local_index: int, global_index: int) -> str:
    return template.format(**values_for(local_index, global_index))


def title_context(domain: str, local_index: int, global_index: int) -> str:
    contexts = TITLE_CONTEXTS[domain]
    return contexts[(local_index + global_index) % len(contexts)]


def scenarios_for_domain(domain: str) -> list[AttentionScenario]:
    return [scenario for scenario in SCENARIOS if scenario.domain == domain]


def evaluation_for(
    scenario: AttentionScenario, local_index: int, force_lead_story: bool = False
) -> str:
    if force_lead_story:
        return "Lead Story"
    if scenario.event_class == "Noise":
        return "Ignore"
    if scenario.event_class == "Monitoring":
        return "Mention" if local_index % 7 == 0 else "Monitor"
    if scenario.event_class == "Maintenance":
        return "Surface" if local_index % 5 == 0 else "Mention"
    if scenario.event_class == "Deadline":
        return "Surface" if local_index % 3 == 0 else "Mention"
    if scenario.event_class == "Opportunity":
        return "Surface" if local_index % 4 == 0 else "Mention"
    return "Surface" if local_index % 6 == 0 else "Mention"


def score_for(evaluation: str, event_class: str, index: int) -> int:
    base = {
        "Ignore": 10,
        "Monitor": 30,
        "Mention": 55,
        "Surface": 76,
        "Lead Story": 91,
    }[evaluation]
    if event_class == "Deadline":
        base += 2
    if event_class == "Noise":
        base -= 4
    return max(1, min(99, base + (index % 6)))


def promotion_rules(event_class: str, subject: str) -> dict:
    if event_class == "Noise":
        return {
            "monitor": "Do not monitor unless it attaches to a real Mike-owned object.",
            "mention": "Only mention if the posture changes.",
            "surface": "No surface path for routine noise.",
            "lead_story": "Never lead.",
        }
    if event_class == "Deadline":
        return {
            "monitor": "Deadline exists but is outside the useful action window.",
            "mention": "Inside the window but no same-day decision is required.",
            "surface": "Date pressure or missing prerequisite can change today's plan.",
            "lead_story": "Rare, high-loss deadline with a concrete same-day posture change.",
        }
    if event_class == "Opportunity":
        return {
            "monitor": "Conditions are approaching Mike's range.",
            "mention": "One condition crossed but action remains optional.",
            "surface": "Window is open and delay can lose value.",
            "lead_story": "Rare window tied to money, travel, work, health, or shipping.",
        }
    if event_class == "Context Change":
        return {
            "monitor": f"Track {subject} until practical impact is known.",
            "mention": "Meaning changed, but it does not yet alter today's plan.",
            "surface": "The change alters a near-term decision or assumption.",
            "lead_story": "The change invalidates a default posture.",
        }
    if event_class == "Maintenance":
        return {
            "monitor": "Not due yet.",
            "mention": "Due this month or easy to batch.",
            "surface": "Due soon, deferred repeatedly, or likely to become friction.",
            "lead_story": "Safety, cost, travel, or deadline risk is imminent.",
        }
    return {
        "monitor": "Object is active but quiet.",
        "mention": "Condition changed slightly.",
        "surface": "Condition changed enough to affect planning.",
        "lead_story": "Condition plus timing creates a same-day decision.",
    }


def suppression_rules(event_class: str, subject: str, domain: str) -> list[str]:
    rules = [
        "Suppress when it does not change Mike's posture today.",
        "Suppress when it is generic news without a personal decision hook.",
    ]
    if event_class == "Noise":
        rules.append("Suppress by default; routine result or minor move.")
    if domain in {"Sports & Golf", "Books & Entertainment"}:
        rules.append("Suppress routine enjoyment updates unless timing or prior intent changes.")
    if domain == "Finance & Markets":
        rules.append("Suppress market moves outside configured ranges or world-model shifts.")
    if domain == "Technology & AI":
        rules.append("Suppress launch coverage Mike likely already knows unless workflow posture changed.")
    if subject in {"Sonar onboarding", "team adoption silence"}:
        rules.append("Suppress unless the gap threatens a review, deadline, or escalation path.")
    return rules


def watch_model_for(scenario: AttentionScenario, local_index: int, global_index: int) -> dict:
    conditions = (
        list(scenario.watch_conditions)
        if scenario.watch_conditions
        else ["timing", "material change", "expiration"]
    )
    return {
        "object": render_template("{watch_object}", local_index, global_index),
        "conditions": conditions,
        "expiration": (
            SIMULATION_START + timedelta(days=(local_index % SIMULATION_DAYS) + 7)
        ).isoformat(),
        "surface_when": [
            "condition changes materially",
            "decision window opens",
            "expiration is near",
        ],
        "default_state": "Monitor silently",
    }


def build_event(
    scenario: AttentionScenario,
    local_index: int,
    global_index: int,
    force_lead_story: bool = False,
) -> dict:
    evaluation = evaluation_for(scenario, local_index, force_lead_story)
    title = render_template(
        scenario.title_templates[local_index % len(scenario.title_templates)],
        local_index,
        global_index,
    )
    title = f"{title}; {title_context(scenario.domain, local_index, global_index)}"
    description = render_template(
        scenario.description_templates[local_index % len(scenario.description_templates)],
        local_index,
        global_index,
    )
    event_suppression_rules = suppression_rules(
        scenario.event_class, scenario.subject, scenario.domain
    )
    event = {
        "id": f"mike-v2-{global_index:04d}",
        "domain": scenario.domain,
        "event_class": scenario.event_class,
        "object": scenario.object,
        "subject": scenario.subject,
        "title": title,
        "description": description,
        "mike_relevance": scenario.mike_relevance,
        "source_inputs": [
            scenario.sources[local_index % len(scenario.sources)],
            scenario.sources[(local_index + 2) % len(scenario.sources)],
        ],
        "evaluation": evaluation,
        "attention_score": score_for(evaluation, scenario.event_class, local_index),
        "value_if_caught": scenario.value_if_caught,
        "loss_if_ignored": scenario.loss_if_ignored,
        "promotion_rules": promotion_rules(scenario.event_class, scenario.subject),
        "suppression_rules": event_suppression_rules,
        "source_watch_ids": source_watch_ids_for_event(
            scenario.domain, scenario.subject
        ),
        "triggered_surface_rule": triggered_surface_rule_for_event(
            scenario.event_class, evaluation
        ),
        "suppressed_by": suppressed_by_for_event(evaluation, event_suppression_rules),
        "why_today": scenario.value_if_caught
        if evaluation in {"Lead Story", "Surface", "Mention"}
        else "No briefing output today; the configured watch remains below threshold.",
        "tags": [
            scenario.domain.lower().replace(" & ", "-").replace(" ", "-"),
            scenario.event_class.lower().replace(" ", "-"),
            evaluation.lower().replace(" ", "-"),
        ],
    }
    if scenario.domain == "Watch Items" or scenario.watch_conditions:
        event["watch"] = watch_model_for(scenario, local_index, global_index)
    return event


def generate_event_corpus() -> list[dict]:
    events: list[dict] = []
    global_index = 1
    lead_eligible_total = sum(
        1
        for domain, target in DOMAIN_TARGETS.items()
        for local_index in range(target)
        if scenarios_for_domain(domain)[local_index % len(scenarios_for_domain(domain))].lead_eligible
    )
    lead_eligible_seen = 0
    lead_stories_used = 0
    for domain, target in DOMAIN_TARGETS.items():
        scenarios = scenarios_for_domain(domain)
        if not scenarios:
            raise ValueError(f"No scenarios configured for domain {domain}")
        for local_index in range(target):
            scenario = scenarios[local_index % len(scenarios)]
            force_lead_story = False
            if scenario.lead_eligible:
                lead_eligible_seen += 1
                target_leads_seen = (
                    lead_eligible_seen * LEAD_STORY_TARGET
                ) // lead_eligible_total
                force_lead_story = target_leads_seen > lead_stories_used
                if force_lead_story:
                    lead_stories_used += 1
            event = build_event(scenario, local_index, global_index, force_lead_story)
            events.append(event)
            global_index += 1
    return events

