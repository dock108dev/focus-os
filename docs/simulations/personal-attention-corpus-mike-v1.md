# FocusOS Personal Attention Corpus (Mike v2)

Purpose: validate the attention model against Mike-specific reality before any new UI work.

## Corpus Summary

- Total events: 1500
- Unique titles: 429
- Lead-story candidates: 26

### Domains

- Work: 240
- Finance & Markets: 220
- Technology & AI: 160
- Personal & Family: 90
- Dog: 70
- Sports & Golf: 110
- Golf Equipment: 60
- Books & Entertainment: 60
- Health: 70
- Life Logistics: 110
- Home Ownership: 80
- Travel: 80
- Side Projects: 90
- Watch Items: 60

### Event Classes

- Deadline: Time-bound event with meaningful loss if ignored.
- Opportunity: Decision window where value can be captured or lost.
- Context Change: New information changes future decisions or assumptions.
- Monitoring: Object stays active but silent until conditions change.
- Maintenance: Recurring or rare upkeep with date or risk pressure.
- Noise: Generic update that should usually be suppressed.

## Generation Standard

- Keep the taxonomy, ranking model, and watch model.
- Generate around attention objects Mike actually thinks about: counts, expirations, thresholds, people, pets, travel, hobbies, and posture changes.
- Do not treat project names, launch names, or generic categories as events by themselves.
- Lead stories are intentionally rare: target 20-30 candidates in a 1500-event corpus.

## Promotion Model

- Ignore: never show unless the event stops being noise.
- Monitor: track silently; no briefing item.
- Mention: one-line briefing item.
- Surface: important enough to appear in the briefing.
- Lead Story: eligible for primary focus, but only when the day truly has a dominant context.

## Suppression Model

- Suppress routine sports results, minor market moves, generic launch coverage, and news without a personal decision hook.
- Suppress repeated items when nothing changed since the last evaluation.
- Suppress any item whose value is merely informational and not context-restoring.

## Watch Model

{
  "definition": "A watch is object plus conditions plus expiration, not content.",
  "required_fields": [
    "object",
    "conditions",
    "expiration",
    "surface_when"
  ],
  "default_behavior": "Monitor silently until a condition changes, a decision window opens, or expiration nears.",
  "examples": {
    "Outdoor Concert": {
      "object": "Concert",
      "conditions": [
        "weather",
        "parking",
        "timing",
        "venue changes"
      ],
      "expiration": "event date"
    },
    "WWDC": {
      "object": "WWDC",
      "conditions": [
        "reminder",
        "major announcements",
        "developer impact"
      ],
      "expiration": "7 days after keynote"
    },
    "Vacation": {
      "object": "Trip",
      "conditions": [
        "flight",
        "weather",
        "travel advisories"
      ],
      "expiration": "return date"
    },
    "Mortgage Rate": {
      "object": "Mortgage-rate watch",
      "conditions": [
        "rate threshold",
        "Fed signal",
        "housing inventory"
      ],
      "expiration": "configured review window"
    }
  }
}

## Simulation

The companion May-June 2026 simulation intentionally includes boring days, no-primary-focus days, competing-focus days, and Mike-specific work, finance, travel, dog, health, golf-equipment, and life-logistics days.
