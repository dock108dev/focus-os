from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable


DOMAIN_TARGETS = {
    "Work": 240,
    "Finance & Markets": 220,
    "Technology & AI": 160,
    "Personal & Family": 90,
    "Dog": 70,
    "Sports & Golf": 110,
    "Golf Equipment": 60,
    "Books & Entertainment": 60,
    "Health": 70,
    "Life Logistics": 110,
    "Home Ownership": 80,
    "Travel": 80,
    "Side Projects": 90,
    "Watch Items": 60,
}

EVENT_CLASSES = [
    "Deadline",
    "Opportunity",
    "Context Change",
    "Monitoring",
    "Maintenance",
    "Noise",
]
EVALUATIONS = ["Ignore", "Monitor", "Mention", "Surface", "Lead Story"]
LEAD_STORY_TARGET = 26
SIMULATION_START = date(2026, 5, 3)
SIMULATION_DAYS = 50


@dataclass(frozen=True)
class AttentionScenario:
    domain: str
    event_class: str
    object: str
    subject: str
    title_templates: tuple[str, ...]
    description_templates: tuple[str, ...]
    mike_relevance: str
    value_if_caught: str
    loss_if_ignored: str
    sources: tuple[str, ...]
    lead_eligible: bool = False
    watch_conditions: tuple[str, ...] = ()


SCENARIOS: tuple[AttentionScenario, ...] = (
    AttentionScenario(
        "Work",
        "Deadline",
        "namespace migration adoption",
        "namespace migration",
        (
            "{repos} repos still not migrated before namespace freeze",
            "{teams} teams have not answered the namespace migration ask",
            "Namespace adoption stalled at {percent}% with freeze inside {days} days",
        ),
        (
            "This is not a project update; it is the unresolved adoption count Mike would need before the next escalation path closes.",
            "The useful fact is who is still exposed and whether silence has become the problem.",
        ),
        "Mike owns the posture of the migration, not the label of the migration project.",
        "A small nudge can unblock teams before the deadline becomes an executive problem.",
        "Late migration creates coordination churn and avoidable escalation.",
        ("GitHub Enterprise", "Slack", "migration tracker"),
        True,
    ),
    AttentionScenario(
        "Work",
        "Deadline",
        "executive decision packet",
        "executive deck",
        (
            "Executive deck due {weekday}; adoption story is still missing",
            "Tuesday deck needs the risk narrative before review",
            "Leadership review moved up with {days} days to reconcile metrics",
        ),
        (
            "The deck matters only because it compresses several workstreams into one decision surface.",
            "This belongs in the briefing when the narrative is the blocker, not when slides merely exist.",
        ),
        "Mike needs the decision-ready version before work fragments the day.",
        "Catching it early preserves time to turn scattered status into a clear ask.",
        "The meeting can turn into follow-up churn instead of a decision.",
        ("calendar", "slides", "Slack"),
        True,
    ),
    AttentionScenario(
        "Work",
        "Context Change",
        "security exposure count",
        "critical KEV exposure",
        (
            "Critical KEV now maps to {services} services",
            "{services} services inherited the new KEV exposure",
            "KEV blast radius grew after dependency inventory refresh",
        ),
        (
            "The important event is the change in blast radius, not a scanner headline.",
            "This changes where Mike should expect security attention to land today.",
        ),
        "Security work becomes real when the exposure maps to owned services.",
        "Mike can separate true escalation risk from generic vulnerability noise.",
        "The day starts with stale risk assumptions.",
        ("security tooling", "service inventory", "GitHub"),
        True,
    ),
    AttentionScenario(
        "Work",
        "Monitoring",
        "platform adoption",
        "Sonar onboarding",
        (
            "Sonar onboarding is at {percent}% of target",
            "{teams} teams still missing Sonar onboarding evidence",
            "Sonar coverage moved, but not enough to change posture",
        ),
        (
            "This should usually stay in monitoring until the gap threatens a review.",
            "The briefing should carry the adoption gap, not a generic rollout name.",
        ),
        "The attention object is coverage against a target.",
        "Mike knows whether to leave it quiet or ask for a status reset.",
        "A stalled adoption curve can hide until the review window is already closed.",
        ("Sonar", "Jira", "Slack"),
    ),
    AttentionScenario(
        "Work",
        "Context Change",
        "duplicate method cluster",
        "namespace code duplication",
        (
            "One namespace has {duplicates} duplicate methods",
            "Duplicate-method cluster is now concentrated in one namespace",
            "{duplicates} duplicate methods point to a consolidation candidate",
        ),
        (
            "This matters because it converts vague cleanup into one concrete attention object.",
            "It is worth mention when the code shape reveals leverage, not when a report is merely long.",
        ),
        "Mike responds to leverage points more than generic tech debt.",
        "A focused cleanup target can replace scattered low-value review.",
        "The useful consolidation opportunity remains hidden in raw reports.",
        ("static analysis", "repository scan", "GitHub"),
    ),
    AttentionScenario(
        "Work",
        "Monitoring",
        "team response gap",
        "team adoption silence",
        (
            "{teams} teams have not responded after the second reminder",
            "Adoption silence is now the blocker, not tooling",
            "Response gap grew while the deadline stayed fixed",
        ),
        (
            "The event is a social coordination gap that can become a delivery risk.",
            "This is not a status update; it identifies the part Mike may need to unblock.",
        ),
        "Mike needs to know when silence, not engineering, is the problem.",
        "A targeted follow-up can prevent a late surprise.",
        "No one notices the absence of response until there is no time left.",
        ("Slack", "email", "Jira"),
    ),
    AttentionScenario(
        "Work",
        "Context Change",
        "repo consolidation velocity",
        "repo consolidation",
        (
            "Repo consolidation slowed to {repos} merges this week",
            "Consolidation velocity fell below the adoption plan",
            "{repos} repos moved, but the long tail is no longer shrinking",
        ),
        (
            "The meaningful signal is whether the long tail is shrinking fast enough.",
            "A project name is irrelevant; the count and trajectory are the attention object.",
        ),
        "Mike cares whether the effort is still converting into fewer things to own.",
        "The briefing can distinguish temporary noise from a stuck consolidation plan.",
        "A slowed long tail becomes permanent maintenance cost.",
        ("GitHub", "migration tracker", "calendar"),
    ),
    AttentionScenario(
        "Finance & Markets",
        "Monitoring",
        "Bitcoin decision range",
        "Bitcoin",
        (
            "Bitcoin is {pct}% from Mike's accumulation range",
            "Bitcoin moved {pct}% this week but still has no decision hook",
            "Bitcoin pullback is close enough to keep quiet watch active",
        ),
        (
            "Bitcoin belongs in the corpus because it shapes Mike's world model even when no trade is implied.",
            "Most Bitcoin moves should die as monitoring unless the range actually matters.",
        ),
        "Mike tracks Bitcoin for context and optionality, not because every move deserves action.",
        "The system can monitor the range without forcing a portfolio decision.",
        "Mike goes back to checking market apps manually.",
        ("CoinGecko", "market close", "portfolio import"),
        True,
    ),
    AttentionScenario(
        "Finance & Markets",
        "Context Change",
        "market breadth",
        "S&P breadth",
        (
            "S&P breadth improved to {percent}% above the 50-day average",
            "SPY is flat, but breadth finally improved",
            "Market breadth no longer matches the index headline",
        ),
        (
            "The value is the change in market structure, not a raw index price.",
            "This gives Mike context for risk appetite without pretending to be advice.",
        ),
        "Mike follows the market backdrop as part of his model of the world.",
        "He can understand whether index strength is broadening or still narrow.",
        "The headline index move hides the real market posture.",
        ("market close", "index breadth", "finance topic"),
    ),
    AttentionScenario(
        "Finance & Markets",
        "Monitoring",
        "AI stock risk appetite",
        "AI infrastructure stocks",
        (
            "AI infrastructure stocks pulled back {pct}% from highs",
            "AI trade cooled while QQQ held its range",
            "AI-stock pullback is notable, but not a decision by itself",
        ),
        (
            "This belongs as world-model context, not as a trading prompt.",
            "The system should mention it only when it changes the risk backdrop.",
        ),
        "Mike pays attention to AI market temperature because it affects broader tech sentiment.",
        "He gets context without needing to scan tickers.",
        "The briefing misses a major shift in the tech risk backdrop.",
        ("market close", "QQQ", "sector watch"),
    ),
    AttentionScenario(
        "Finance & Markets",
        "Context Change",
        "healthcare holding risk",
        "UNH",
        (
            "UNH is down another {pct}% while healthcare lag widens",
            "UNH drawdown changed the portfolio context again",
            "UNH weakness is now large enough to re-check assumptions",
        ),
        (
            "This is relevant when it changes the story around a watched name.",
            "It should not become a generic holdings card.",
        ),
        "Mike follows UNH as a specific watched object in the market map.",
        "He can notice when the move becomes context, not just price noise.",
        "A meaningful holding-specific shift blends into daily market clutter.",
        ("portfolio import", "market close", "watch range"),
        True,
    ),
    AttentionScenario(
        "Finance & Markets",
        "Opportunity",
        "mortgage rate threshold",
        "mortgage rates",
        (
            "Mortgage rates moved back below {rate}%",
            "Mortgage-rate watch crossed Mike's review threshold",
            "Rate drop changes the housing math for the first time this month",
        ),
        (
            "This matters because it can change housing or cash posture, not because rates changed in isolation.",
            "A rate threshold is exactly the kind of object that should stay quiet until crossed.",
        ),
        "Mike tracks rates because they can change a real-life decision window.",
        "The system can surface a rare decision window instead of daily rate noise.",
        "A useful housing window may pass unnoticed.",
        ("FRED", "mortgage rate feed", "housing watch"),
        True,
    ),
    AttentionScenario(
        "Finance & Markets",
        "Context Change",
        "macro inflation path",
        "Fed and CPI path",
        (
            "Fed path shifted after CPI cooled to {pct}%",
            "CPI changed the expected rate path, not just the news cycle",
            "Labor data and CPI now point in different directions",
        ),
        (
            "The event is the posture change across rates, cash, and housing.",
            "This should be suppressed unless the macro picture changes Mike's assumptions.",
        ),
        "Mike follows macro because it changes how he interprets cash, stocks, and housing.",
        "He gets the practical posture change without reading generic Fed coverage.",
        "Macro headlines keep accumulating without a usable conclusion.",
        ("CPI calendar", "Fed calendar", "labor report"),
    ),
    AttentionScenario(
        "Finance & Markets",
        "Monitoring",
        "energy inflation pressure",
        "oil",
        (
            "Oil is up {pct}% this month",
            "Oil move is now large enough to affect inflation context",
            "Energy prices changed the macro backdrop but not a personal action",
        ),
        (
            "Oil belongs here as a world-model input, usually not a briefing lead.",
            "The system should distinguish macro context from personal urgency.",
        ),
        "Mike tracks oil as a macro pressure point.",
        "He can update context without being dragged into commodity news.",
        "A macro shift remains invisible until it shows up elsewhere.",
        ("market close", "energy market", "macro topic"),
    ),
    AttentionScenario(
        "Technology & AI",
        "Context Change",
        "coding-agent workflow",
        "Claude Code workflow",
        (
            "Claude Code now beats Mike's current workflow on test repair",
            "Coding-agent workflow crossed from interesting to usable",
            "Agent benchmark matters because it changes the default coding loop",
        ),
        (
            "The release is not the event; the event is whether Mike should change posture.",
            "This should suppress generic AI news and keep only practical workflow changes.",
        ),
        "Mike usually knows the release; he needs the posture change.",
        "He can decide whether the tool deserves more real work, not just curiosity.",
        "Tool defaults stay stale after capability has changed.",
        ("vendor changelog", "benchmark", "local workflow"),
        True,
    ),
    AttentionScenario(
        "Technology & AI",
        "Opportunity",
        "editor friction fix",
        "Cursor workflow",
        (
            "Cursor fixed the multi-file edit friction Mike keeps working around",
            "Cursor update finally removes a workflow tax",
            "Editor change matters because it fixes the exact loop Mike avoids",
        ),
        (
            "This is a tool posture event, not launch coverage.",
            "The item earns attention only if it changes how Mike would actually build.",
        ),
        "Mike cares when a tool removes recurring friction.",
        "Trying the update may save repeated project time.",
        "He keeps using a slower workflow out of habit.",
        ("release notes", "local workflow", "developer docs"),
        True,
    ),
    AttentionScenario(
        "Technology & AI",
        "Deadline",
        "WWDC posture change",
        "WWDC",
        (
            "WWDC keynote is tomorrow; three project assumptions may change",
            "WWDC happened; three iOS changes matter to Mike's projects",
            "WWDC follow-up window closes before the weekend",
        ),
        (
            "The event is not Apple news; it is the chance to update project assumptions.",
            "This belongs when the keynote changes what Mike would build or postpone.",
        ),
        "Mike needs a practical summary of what changed for his own apps.",
        "He can update project direction before stale assumptions harden.",
        "He misses a short window to adjust active iOS work.",
        ("Apple developer news", "WWDC", "project notes"),
        True,
        ("keynote date", "developer impact", "project assumptions"),
    ),
    AttentionScenario(
        "Technology & AI",
        "Monitoring",
        "model pricing posture",
        "AI pricing",
        (
            "AI pricing shifted but does not change Mike's default yet",
            "Model cost moved enough to keep side-project economics on watch",
            "Pricing change is real but still below the workflow threshold",
        ),
        (
            "Pricing is only useful when it changes project economics or tool defaults.",
            "The item should mostly stay quiet until there is a practical threshold crossing.",
        ),
        "Mike cares about cost when it affects what he can ship.",
        "He can avoid reacting to every pricing page change.",
        "Generic AI pricing news eats attention without changing behavior.",
        ("pricing page", "usage spend", "side-project plan"),
    ),
    AttentionScenario(
        "Personal & Family",
        "Deadline",
        "family date",
        "family calendar",
        (
            "{family_event} is inside {days} days",
            "{family_event} needs a gift or plan before the week fills up",
            "Family commitment moved from background to calendar risk",
        ),
        (
            "This restores personal context before work absorbs the day.",
            "The event belongs here because the cost of forgetting is social, not technical.",
        ),
        "Mike wants the system to remember the human calendar he would otherwise drop.",
        "A small early action prevents an avoidable scramble.",
        "The date is forgotten until it becomes awkward.",
        ("calendar", "notes", "messages"),
        True,
    ),
    AttentionScenario(
        "Dog",
        "Maintenance",
        "Bogey care schedule",
        "Bogey",
        (
            "Bogey's heartworm refill is due in {days} days",
            "Bogey grooming is overdue by {days} days",
            "Annual vet visit window opened for Bogey",
        ),
        (
            "Dog care is exactly the kind of real-life obligation the system should preserve.",
            "This is not a pet category; it is a concrete care object with expiration.",
        ),
        "Bogey belongs in the model because Mike cares and the tasks are easy to forget.",
        "The system can surface care windows before they become urgent.",
        "A small recurring obligation becomes stress or risk.",
        ("calendar", "vet email", "notes"),
    ),
    AttentionScenario(
        "Dog",
        "Deadline",
        "Bogey trip coverage",
        "Bogey boarding",
        (
            "Bogey boarding is not booked for the trip in {days} days",
            "Dog-care coverage is the open item for vacation",
            "Trip logistics depend on confirming Bogey coverage",
        ),
        (
            "This deserves attention when it blocks travel confidence.",
            "The system should catch pet logistics before they collide with departure.",
        ),
        "Dog logistics are part of the real plan, not a side note.",
        "Mike can close the loop while there are still options.",
        "Travel gets expensive or stressful at the last minute.",
        ("calendar", "boarding email", "travel notes"),
        True,
    ),
    AttentionScenario(
        "Sports & Golf",
        "Monitoring",
        "sports context",
        "Yankees and Rutgers",
        (
            "Yankees result changed nothing; standings context stays quiet",
            "Rutgers kickoff window matters only if travel logistics change",
            "Major championship weekend is watchable, but not attention-worthy yet",
        ),
        (
            "Sports should stay suppressed unless it changes planning or real context.",
            "The value is not a score; it is whether Mike's weekend or season posture changed.",
        ),
        "Mike follows sports, but routine results should not steal the briefing.",
        "The system proves it can suppress familiar low-value updates.",
        "The product drifts into a sports dashboard.",
        ("sports schedule", "team news", "ticket portal"),
    ),
    AttentionScenario(
        "Sports & Golf",
        "Noise",
        "routine score",
        "routine sports result",
        (
            "Yankees won a routine June game",
            "Rutgers offseason note has no planning effect",
            "Golf leaderboard moved, but Mike has no reason to act",
        ),
        (
            "This is intentionally present so the corpus proves routine sports can be ignored.",
            "A personal operating system should know Mike likes sports and still suppress low-value results.",
        ),
        "Sports interest is real, but routine scores should not become morning attention.",
        "The system protects the briefing from turning into a scoreboard.",
        "The product drifts into generic sports content.",
        ("sports schedule", "team news", "leaderboard"),
    ),
    AttentionScenario(
        "Golf Equipment",
        "Opportunity",
        "club setup",
        "golf equipment",
        (
            "Ping release creates a G430 replacement question",
            "Club fitting slot opened during Mike's range window",
            "Range pass renewal is inside {days} days",
        ),
        (
            "Golf equipment gets attention when it intersects timing, fit, or a real buying window.",
            "This is a specific Mike interest that generic personal categories miss.",
        ),
        "Mike spends enough attention here that the corpus should model it directly.",
        "He can catch useful fitting or renewal windows without browsing.",
        "A real hobby window is missed while generic sports items fill the corpus.",
        ("golf shop email", "manufacturer release", "range account"),
        True,
    ),
    AttentionScenario(
        "Books & Entertainment",
        "Monitoring",
        "media queue",
        "books and shows",
        (
            "{show_or_book} released, but no action is needed today",
            "Series finale is available after prior watch",
            "Book recommendation matches Mike's prior queue",
        ),
        (
            "Entertainment should exist in the world model while usually staying suppressed.",
            "It can be useful when it connects to prior watching or reading intent.",
        ),
        "Mike's actual life includes media and recommendations, not just work and markets.",
        "The system can preserve light personal context without over-promoting it.",
        "The corpus becomes too narrow and utilitarian to feel personal.",
        ("streaming queue", "book notes", "recommendation"),
    ),
    AttentionScenario(
        "Books & Entertainment",
        "Noise",
        "generic media release",
        "entertainment noise",
        (
            "Generic streaming release has no prior-watch hook",
            "Book list update does not match Mike's queue",
            "Trailer drop is interesting but not attention-worthy",
        ),
        (
            "The category exists, but most entertainment inputs should be suppressed.",
            "This prevents the corpus from confusing personal texture with required attention.",
        ),
        "Mike's interests should exist without creating fake obligations.",
        "The briefing remains personal without becoming a media feed.",
        "Low-value entertainment updates crowd out real context.",
        ("streaming feed", "book list", "recommendation"),
    ),
    AttentionScenario(
        "Health",
        "Maintenance",
        "basic health admin",
        "health logistics",
        (
            "Prescription refill window opens in {days} days",
            "Annual physical scheduling window is open",
            "Eye exam is due this month",
        ),
        (
            "This avoids medical interpretation and focuses on ordinary logistics.",
            "The event matters because it is easy to defer until appointments become harder.",
        ),
        "Health logistics are real attention objects without becoming medical advice.",
        "Mike can schedule routine care before it becomes annoying.",
        "Basic admin gets deferred until options narrow.",
        ("calendar", "pharmacy notice", "provider portal"),
    ),
    AttentionScenario(
        "Life Logistics",
        "Deadline",
        "civilian paperwork",
        "life logistics",
        (
            "Passport expires inside {days} days",
            "TSA PreCheck renewal window opened",
            "Car registration renewal is inside {days} days",
        ),
        (
            "These are the exact forgotten obligations that justify a personal operating system.",
            "The object is a real-world expiration with avoidable friction.",
        ),
        "Mike should not have to remember every low-frequency administrative deadline.",
        "A small timely action prevents future travel or paperwork friction.",
        "An avoidable expiration becomes a painful errand.",
        ("email", "calendar", "state portal"),
        True,
    ),
    AttentionScenario(
        "Life Logistics",
        "Maintenance",
        "household finance date",
        "property taxes",
        (
            "Property taxes are due inside {days} days",
            "Insurance document needs renewal before the mortgage file update",
            "Life-admin deadline is close enough to leave monitoring",
        ),
        (
            "Life logistics matter because forgetting them creates real cost.",
            "This should surface only when date pressure exists.",
        ),
        "The model needs mundane but consequential paperwork.",
        "Mike can handle it before it becomes a weekend tax.",
        "The missed item creates fee, friction, or stress.",
        ("email", "calendar", "home folder"),
        True,
    ),
    AttentionScenario(
        "Home Ownership",
        "Maintenance",
        "home maintenance",
        "home upkeep",
        (
            "HVAC service window is filling before the heat stretch",
            "Air filters are overdue by {days} days",
            "Dryer vent cleaning has been deferred twice",
        ),
        (
            "This is the right kind of maintenance: boring until ignored.",
            "It should appear when timing or risk turns a small chore into leverage.",
        ),
        "Home upkeep should be caught before it becomes a larger problem.",
        "Small maintenance prevents bigger cost or stress.",
        "The house accumulates avoidable deferred work.",
        ("home checklist", "calendar", "seasonal rule"),
    ),
    AttentionScenario(
        "Travel",
        "Deadline",
        "trip departure",
        "travel logistics",
        (
            "Flight departure is inside {days} days and parking is not confirmed",
            "Vacation weather changed the packing plan",
            "Return logistics are still open before departure",
        ),
        (
            "Travel attention should restore the specific open loop before the trip arrives.",
            "Destination content is noise; missing logistics are the event.",
        ),
        "Mike needs travel open loops surfaced before they become expensive.",
        "He can close parking, packing, or return details while there is time.",
        "Travel mistakes are costly to recover from.",
        ("calendar", "airline email", "weather"),
        True,
        ("flight", "weather", "parking", "return plan"),
    ),
    AttentionScenario(
        "Side Projects",
        "Context Change",
        "ship-or-stop decision",
        "side-project direction",
        (
            "Side project has gone {days} days without a user-facing step",
            "Validation evidence changed the ship-or-stop decision",
            "Infrastructure spend rose without product progress",
        ),
        (
            "The item matters when it changes whether Mike should keep investing attention.",
            "This should avoid task churn and focus on project posture.",
        ),
        "Mike wants side projects judged by momentum and fit, not backlog size.",
        "He can stop, ship, or narrow the next step with better context.",
        "A project becomes a quiet time sink.",
        ("GitHub", "billing email", "project notes"),
        True,
    ),
    AttentionScenario(
        "Watch Items",
        "Monitoring",
        "object plus conditions",
        "user-created watch",
        (
            "{watch_object} has no meaningful change yet",
            "{watch_object} condition changed enough to mention",
            "{watch_object} expires in {days} days",
        ),
        (
            "A watch is an object with conditions and expiration, not content to read.",
            "The correct default is silence until timing, threshold, or conditions change.",
        ),
        "Mike should not need to remember to re-check active watch objects.",
        "The system can surface only the watches that changed.",
        "Mike has to manually poll objects he already told the system about.",
        ("user-created watch", "calendar", "weather", "market threshold"),
        False,
        ("condition changed", "decision window", "expiration"),
    ),
)


SLOT_BANKS = {
    "repos": [40, 37, 32, 28, 24, 19, 14, 11, 8, 5],
    "teams": [5, 4, 7, 3, 6, 2],
    "percent": [41, 48, 52, 57, 63, 68, 74, 79, 83],
    "days": [2, 3, 4, 5, 6, 7, 10, 14, 21, 29, 43, 61],
    "services": [12, 9, 16, 21, 7, 18],
    "duplicates": [87, 73, 64, 58, 49, 112],
    "pct": [3.4, 4.8, 6.1, 7.6, 8.0, 11.5, 15.0, 18.2],
    "rate": [5.9, 6.0, 6.1, 6.2],
    "weekday": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "family_event": ["Father's Day", "nephew birthday", "family visit", "birthday dinner"],
    "show_or_book": [
        "The queued show",
        "The series finale",
        "The saved nonfiction recommendation",
        "The new season",
    ],
    "watch_object": [
        "WWDC",
        "outdoor concert",
        "vacation departure",
        "Rutgers renewal",
        "mortgage-rate watch",
        "Bitcoin range",
        "Bogey boarding",
        "golf trip weather",
    ],
}


TITLE_CONTEXTS = {
    "Work": [
        "after the second reminder",
        "before staff review",
        "with the freeze still fixed",
        "after the tracker refresh",
        "before the exec readout",
        "after owner silence",
        "with escalation risk rising",
        "before Friday status",
    ],
    "Finance & Markets": [
        "after market close",
        "before the Fed week",
        "with housing math in view",
        "after the weekly move",
        "before cash allocation review",
        "with breadth diverging",
        "after the CPI print",
        "with risk appetite cooling",
    ],
    "Technology & AI": [
        "after release notes landed",
        "before the next coding block",
        "after benchmark review",
        "with side projects in mind",
        "before tool defaults harden",
        "after WWDC follow-up",
        "with cost limits in view",
        "before workflow reset",
    ],
    "Dog": [
        "before the trip window",
        "after the calendar check",
        "before weekend errands",
        "with boarding options narrowing",
        "after the vet reminder",
        "before the refill gap",
    ],
    "Golf Equipment": [
        "before the fitting slots fill",
        "after the release note",
        "with range time planned",
        "before renewal pricing changes",
        "after the bag review",
        "with spring setup in mind",
    ],
    "Books & Entertainment": [
        "after queue refresh",
        "before weekend downtime",
        "with prior-watch context",
        "after recommendation review",
        "before it gets stale",
    ],
    "Health": [
        "before appointment slots narrow",
        "after provider reminder",
        "before refill gap",
        "with calendar space available",
        "after routine admin check",
    ],
    "Life Logistics": [
        "before paperwork friction",
        "after email scan",
        "with travel optionality in view",
        "before renewal window closes",
        "after calendar audit",
        "before weekend errands",
    ],
    "Home Ownership": [
        "before the heat stretch",
        "after seasonal checklist",
        "before service windows fill",
        "after deferral count changed",
        "with cost risk rising",
    ],
    "Travel": [
        "before departure week",
        "after weather refresh",
        "before parking fills",
        "with return plan still open",
        "after airline email",
    ],
    "Side Projects": [
        "after repo review",
        "before another build cycle",
        "with spend rising",
        "after validation notes",
        "before weekend coding time",
    ],
    "Watch Items": [
        "before expiration",
        "after condition check",
        "with no posture change",
        "as decision window nears",
        "after threshold review",
    ],
    "Personal & Family": [
        "before the week fills",
        "after calendar review",
        "before gift timing gets tight",
        "with work likely to crowd it out",
    ],
    "Sports & Golf": [
        "after scoreboard check",
        "before weekend plans",
        "with no standings change",
        "after ticket portal refresh",
    ],
}


SIMULATION_PATTERNS = [
    {"name": "quiet market and chores check", "dominant": None, "primary": None},
    {"name": "namespace adoption count becomes urgent", "dominant": "Work", "primary": "work", "subject": "namespace migration"},
    {"name": "mortgage rate threshold watch", "dominant": "Finance & Markets", "primary": "finance", "subject": "mortgage rates"},
    {"name": "trip parking and packing open loops", "dominant": "Travel", "primary": "travel", "subject": "travel logistics"},
    {"name": "deck deadline competes with family date", "dominant": "Work", "primary": "competing", "subject": "executive deck"},
    {"name": "routine sports and market noise", "dominant": None, "primary": None},
    {"name": "coding-agent workflow posture shift", "dominant": "Technology & AI", "primary": "technology", "subject": "Claude Code workflow"},
    {"name": "Bogey care window", "dominant": "Dog", "primary": "dog", "subject": "Bogey"},
    {"name": "property tax paperwork window", "dominant": "Life Logistics", "primary": "life", "subject": "property taxes"},
    {"name": "watch object stays quiet", "dominant": "Watch Items", "primary": None},
    {"name": "KEV blast radius widened", "dominant": "Work", "primary": "work", "subject": "critical KEV exposure"},
    {"name": "S&P breadth changed the backdrop", "dominant": "Finance & Markets", "primary": "finance", "subject": "S&P breadth"},
    {"name": "WWDC project assumptions changed", "dominant": "Technology & AI", "primary": "technology", "subject": "WWDC"},
    {"name": "home upkeep before weather shift", "dominant": "Home Ownership", "primary": "home", "subject": "home upkeep"},
    {"name": "side project ship-or-stop posture", "dominant": "Side Projects", "primary": "side-project", "subject": "side-project direction"},
    {"name": "nothing clears the attention bar", "dominant": None, "primary": None},
    {"name": "golf fitting window opened", "dominant": "Golf Equipment", "primary": "golf-equipment", "subject": "golf equipment"},
    {"name": "passport and travel paperwork", "dominant": "Life Logistics", "primary": "life", "subject": "life logistics"},
    {"name": "UNH drawdown changed context", "dominant": "Finance & Markets", "primary": "finance", "subject": "UNH"},
    {"name": "health admin scheduling window", "dominant": "Health", "primary": "health", "subject": "health logistics"},
    {"name": "team silence is the blocker", "dominant": "Work", "primary": "work", "subject": "team adoption silence"},
    {"name": "entertainment queue stays suppressed", "dominant": None, "primary": None},
    {"name": "club release but no same-day decision", "dominant": "Golf Equipment", "primary": "golf-equipment", "subject": "golf equipment"},
    {"name": "return travel detail still open", "dominant": "Travel", "primary": "travel", "subject": "travel logistics"},
    {"name": "macro data changed rate path", "dominant": "Finance & Markets", "primary": "finance", "subject": "Fed and CPI path"},
    {"name": "duplicate-method cluster is leverage", "dominant": "Work", "primary": "work", "subject": "namespace code duplication"},
    {"name": "AI pricing stays below threshold", "dominant": None, "primary": None},
    {"name": "Bogey trip coverage blocks confidence", "dominant": "Dog", "primary": "dog", "subject": "Bogey boarding"},
    {"name": "side-project cost without progress", "dominant": "Side Projects", "primary": "side-project", "subject": "side-project direction"},
    {"name": "home and family both need small actions", "dominant": "Personal & Family", "primary": "competing"},
    {"name": "oil move is only macro context", "dominant": None, "primary": None},
    {"name": "executive packet needs decision story", "dominant": "Work", "primary": "work", "subject": "executive deck"},
    {"name": "Bitcoin range nears but does not cross", "dominant": "Finance & Markets", "primary": "finance", "subject": "Bitcoin"},
    {"name": "Cursor removed recurring edit friction", "dominant": "Technology & AI", "primary": "technology", "subject": "Cursor workflow"},
    {"name": "car registration renewal surfaced", "dominant": "Life Logistics", "primary": "life", "subject": "life logistics"},
    {"name": "sports context stays low priority", "dominant": None, "primary": None},
    {"name": "travel weather changed packing", "dominant": "Travel", "primary": "travel", "subject": "travel logistics"},
    {"name": "annual physical scheduling window", "dominant": "Health", "primary": "health", "subject": "health logistics"},
    {"name": "repo consolidation long tail slowed", "dominant": "Work", "primary": "work", "subject": "repo consolidation"},
    {"name": "AI stocks pulled back but no action", "dominant": None, "primary": None},
    {"name": "family date has real timing risk", "dominant": "Personal & Family", "primary": "family", "subject": "family calendar"},
    {"name": "range pass renewal window", "dominant": "Golf Equipment", "primary": "golf-equipment", "subject": "golf equipment"},
    {"name": "household finance due date", "dominant": "Life Logistics", "primary": "life", "subject": "property taxes"},
    {"name": "watch expiration is near", "dominant": "Watch Items", "primary": "watch"},
    {"name": "Sonar adoption remains below target", "dominant": "Work", "primary": "work", "subject": "Sonar onboarding"},
    {"name": "no spotlight after suppression", "dominant": None, "primary": None},
    {"name": "Fed path affects housing math", "dominant": "Finance & Markets", "primary": "finance", "subject": "Fed and CPI path"},
    {"name": "dryer vent task became risk", "dominant": "Home Ownership", "primary": "home", "subject": "home upkeep"},
    {"name": "project validation changed direction", "dominant": "Side Projects", "primary": "side-project", "subject": "side-project direction"},
    {"name": "quiet Sunday review", "dominant": None, "primary": None},
]


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
    scenario: AttentionScenario, local_index: int, lead_stories_used: int
) -> tuple[str, int]:
    if (
        scenario.lead_eligible
        and lead_stories_used < LEAD_STORY_TARGET
        and local_index % 11 == 0
    ):
        return "Lead Story", lead_stories_used + 1
    if scenario.event_class == "Noise":
        return "Ignore", lead_stories_used
    if scenario.event_class == "Monitoring":
        return ("Mention" if local_index % 7 == 0 else "Monitor"), lead_stories_used
    if scenario.event_class == "Maintenance":
        return ("Surface" if local_index % 5 == 0 else "Mention"), lead_stories_used
    if scenario.event_class == "Deadline":
        return ("Surface" if local_index % 3 == 0 else "Mention"), lead_stories_used
    if scenario.event_class == "Opportunity":
        return ("Surface" if local_index % 4 == 0 else "Mention"), lead_stories_used
    return ("Surface" if local_index % 6 == 0 else "Mention"), lead_stories_used


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
    lead_stories_used: int,
) -> tuple[dict, int]:
    evaluation, lead_stories_used = evaluation_for(
        scenario, local_index, lead_stories_used
    )
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
        "suppression_rules": suppression_rules(
            scenario.event_class, scenario.subject, scenario.domain
        ),
        "tags": [
            scenario.domain.lower().replace(" & ", "-").replace(" ", "-"),
            scenario.event_class.lower().replace(" ", "-"),
            evaluation.lower().replace(" ", "-"),
        ],
    }
    if scenario.domain == "Watch Items" or scenario.watch_conditions:
        event["watch"] = watch_model_for(scenario, local_index, global_index)
    return event, lead_stories_used


def generate_event_corpus() -> list[dict]:
    events: list[dict] = []
    global_index = 1
    lead_stories_used = 0
    for domain, target in DOMAIN_TARGETS.items():
        scenarios = scenarios_for_domain(domain)
        if not scenarios:
            raise ValueError(f"No scenarios configured for domain {domain}")
        for local_index in range(target):
            scenario = scenarios[local_index % len(scenarios)]
            event, lead_stories_used = build_event(
                scenario, local_index, global_index, lead_stories_used
            )
            events.append(event)
            global_index += 1
    return events


def corpus_summary(events: Iterable[dict]) -> dict:
    rows = list(events)
    by_domain = {domain: 0 for domain in DOMAIN_TARGETS}
    by_class = {event_class: 0 for event_class in EVENT_CLASSES}
    by_evaluation = {evaluation: 0 for evaluation in EVALUATIONS}
    for row in rows:
        by_domain[row["domain"]] += 1
        by_class[row["event_class"]] += 1
        by_evaluation[row["evaluation"]] += 1
    return {
        "total_events": len(rows),
        "domain_counts": by_domain,
        "class_counts": by_class,
        "evaluation_counts": by_evaluation,
        "unique_title_count": len({row["title"] for row in rows}),
    }


def select_events(
    events: list[dict], domain: str, evaluation: str | None, count: int, offset: int
) -> list[dict]:
    candidates = [
        event
        for event in events
        if event["domain"] == domain
        and (evaluation is None or event["evaluation"] == evaluation)
    ]
    if not candidates:
        return []
    return [candidates[(offset + index) % len(candidates)] for index in range(count)]


def select_best_domain_events(
    events: list[dict],
    domain: str,
    count: int,
    offset: int,
    subject: str | None = None,
) -> list[dict]:
    scoped_events = [
        event
        for event in events
        if event["domain"] == domain and (subject is None or event["subject"] == subject)
    ]
    if not scoped_events and subject is not None:
        scoped_events = [event for event in events if event["domain"] == domain]
    selected: list[dict] = []
    selected.extend(select_events(scoped_events, domain, "Lead Story", 1, offset))
    for evaluation in ("Surface", "Mention"):
        selected.extend(
            select_events(scoped_events, domain, evaluation, count, offset + len(selected))
        )
        if len(selected) >= count:
            return selected[:count]
    return selected[:count]


def simulation_pattern(day_index: int) -> dict:
    return SIMULATION_PATTERNS[day_index % len(SIMULATION_PATTERNS)]


def build_simulation_day(events: list[dict], day_index: int) -> dict:
    current_date = SIMULATION_START + timedelta(days=day_index)
    pattern = simulation_pattern(day_index)
    candidate_events: list[dict] = []
    candidate_events.extend(select_events(events, "Finance & Markets", "Monitor", 2, day_index))
    candidate_events.extend(select_events(events, "Sports & Golf", "Ignore", 1, day_index))
    candidate_events.extend(select_events(events, "Books & Entertainment", "Ignore", 1, day_index))
    candidate_events.extend(select_events(events, "Technology & AI", "Mention", 1, day_index))
    candidate_events.extend(select_events(events, "Life Logistics", "Mention", 1, day_index))
    if pattern["dominant"]:
        candidate_events.extend(
            select_best_domain_events(
                events,
                pattern["dominant"],
                3,
                day_index,
                subject=pattern.get("subject"),
            )
        )
    if pattern["primary"] == "competing":
        candidate_events.extend(select_best_domain_events(events, "Personal & Family", 2, day_index))
        candidate_events.extend(select_best_domain_events(events, "Work", 2, day_index + 3))

    if pattern["primary"] is None:
        selected = [
            event for event in candidate_events if event["evaluation"] in {"Mention", "Monitor"}
        ][:4]
        primary_focus_id = None
    else:
        selected = [
            event for event in candidate_events if event["evaluation"] in {"Surface", "Lead Story"}
        ][:4]
        selected.extend(
            [event for event in candidate_events if event["evaluation"] == "Mention"][:2]
        )
        primary_focus_id = (
            max(selected, key=lambda event: event["attention_score"])["id"]
            if selected
            else None
        )

    suppressed = [event for event in candidate_events if event["evaluation"] == "Ignore"]
    outcome_counts = {evaluation: 0 for evaluation in EVALUATIONS}
    for event in candidate_events:
        outcome_counts[event["evaluation"]] += 1
    return {
        "date": current_date.isoformat(),
        "scenario": pattern["name"],
        "dominant_domain": pattern["dominant"],
        "primary_focus_id": primary_focus_id,
        "primary_focus_title": next(
            (event["title"] for event in selected if event["id"] == primary_focus_id),
            None,
        ),
        "allows_no_spotlight": primary_focus_id is None,
        "multiple_competing_focuses": pattern["primary"] == "competing"
        and sum(
            1
            for event in selected
            if event["evaluation"] in {"Surface", "Lead Story"}
        )
        > 1,
        "candidate_event_ids": [event["id"] for event in candidate_events],
        "selected_event_ids": [event["id"] for event in selected],
        "suppressed_event_ids": [event["id"] for event in suppressed],
        "outcome_counts": outcome_counts,
        "review_note": review_note(pattern["primary"]),
    }


def review_note(primary: str | None) -> str:
    if primary is None:
        return "Nothing deserves the spotlight today; verify the system does not manufacture a hero."
    if primary == "competing":
        return "Multiple high-value contexts compete; review whether one truly dominates."
    return "A dominant context exists; review whether it earns primary focus."


def build_may_june_simulation(events: list[dict] | None = None) -> list[dict]:
    rows = events or generate_event_corpus()
    return [build_simulation_day(rows, index) for index in range(SIMULATION_DAYS)]


def classification_rules() -> dict:
    return {
        "Deadline": "Time-bound event with meaningful loss if ignored.",
        "Opportunity": "Decision window where value can be captured or lost.",
        "Context Change": "New information changes future decisions or assumptions.",
        "Monitoring": "Object stays active but silent until conditions change.",
        "Maintenance": "Recurring or rare upkeep with date or risk pressure.",
        "Noise": "Generic update that should usually be suppressed.",
    }


def watch_model() -> dict:
    return {
        "definition": "A watch is object plus conditions plus expiration, not content.",
        "required_fields": ["object", "conditions", "expiration", "surface_when"],
        "default_behavior": "Monitor silently until a condition changes, a decision window opens, or expiration nears.",
        "examples": {
            "Outdoor Concert": {
                "object": "Concert",
                "conditions": ["weather", "parking", "timing", "venue changes"],
                "expiration": "event date",
            },
            "WWDC": {
                "object": "WWDC",
                "conditions": ["reminder", "major announcements", "developer impact"],
                "expiration": "7 days after keynote",
            },
            "Vacation": {
                "object": "Trip",
                "conditions": ["flight", "weather", "travel advisories"],
                "expiration": "return date",
            },
            "Mortgage Rate": {
                "object": "Mortgage-rate watch",
                "conditions": ["rate threshold", "Fed signal", "housing inventory"],
                "expiration": "configured review window",
            },
        },
    }


def render_rules_markdown(summary: dict) -> str:
    lines = [
        "# FocusOS Personal Attention Corpus (Mike v2)",
        "",
        "Purpose: validate the attention model against Mike-specific reality before any new UI work.",
        "",
        "## Corpus Summary",
        "",
        f"- Total events: {summary['total_events']}",
        f"- Unique titles: {summary['unique_title_count']}",
        f"- Lead-story candidates: {summary['evaluation_counts']['Lead Story']}",
        "",
        "### Domains",
        "",
    ]
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
            "- Keep the taxonomy, ranking model, and watch model.",
            "- Generate around attention objects Mike actually thinks about: counts, expirations, thresholds, people, pets, travel, hobbies, and posture changes.",
            "- Do not treat project names, launch names, or generic categories as events by themselves.",
            "- Lead stories are intentionally rare: target 20-30 candidates in a 1500-event corpus.",
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
            "## Watch Model",
            "",
            json.dumps(watch_model(), indent=2),
            "",
            "## Simulation",
            "",
            "The companion May-June 2026 simulation intentionally includes boring days, no-primary-focus days, competing-focus days, and Mike-specific work, finance, travel, dog, health, golf-equipment, and life-logistics days.",
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
        "summary": corpus_summary(events),
        "classification_rules": classification_rules(),
        "watch_model": watch_model(),
        "events": events,
    }
    simulation_payload = {
        "version": "mike-v2",
        "date_range": {
            "start": SIMULATION_START.isoformat(),
            "end": (SIMULATION_START + timedelta(days=SIMULATION_DAYS - 1)).isoformat(),
            "days": SIMULATION_DAYS,
        },
        "days": simulation,
    }
    corpus_path.write_text(json.dumps(corpus_payload, indent=2) + "\n", encoding="utf-8")
    simulation_path.write_text(
        json.dumps(simulation_payload, indent=2) + "\n", encoding="utf-8"
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
