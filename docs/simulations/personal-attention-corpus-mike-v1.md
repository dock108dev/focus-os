# FocusOS Personal Attention Corpus (Mike v2)

Purpose: validate the attention model against Mike-specific reality before any new UI work.

## Corpus Summary

- Total events: 1500
- Configured watches: 17
- Valid watches: 17
- Valid presets: 10
- Unique titles: 372
- Lead-story candidates: 26

## Planning Layers

- Configured Watches: User-authored attention configuration: what matters, what to check, where to check, cadence, surface rules, suppression rules, expiration, and preferred output.
- Generated Events: System observations produced from configured watches and other sources. These are candidates, not briefing items.
- Briefing Outputs: Only the filtered conclusions that changed, need attention now, or would otherwise be forgotten.

## Configured Watches

Configured watches are the user's source-of-truth attention config. The daily briefing is downstream of this layer.

### Outdoor concert Friday

- Object: outdoor concert
- Conditions: weather, parking prices, venue policy, timing
- Sources: calendar, weather, venue email, parking feed
- Cadence: daily until 72 hours out, then morning and afternoon
- Surface when: rain risk > 35%; parking changes materially; event is within 48 hours; venue sends an update
- Do not surface: generic reminders; unchanged weather; concert is coming up filler
- Expire: day after event
- Preferred output: brief only what changed or what needs a decision

### Bitcoin range

- Object: Bitcoin
- Conditions: price range, liquidity, macro risk, cash availability
- Sources: CoinGecko, market close, portfolio import
- Cadence: daily after market close
- Surface when: configured accumulation range crossed; weekly move changes risk posture
- Do not surface: minor daily moves; generic crypto headlines; price-only updates
- Expire: until range is retired
- Preferred output: decision-window note

### UNH watch

- Object: UNH
- Conditions: drawdown, healthcare sector context, portfolio exposure
- Sources: portfolio import, market close, sector watch
- Cadence: daily after market close
- Surface when: drawdown materially changes assumptions; sector weakness accelerates
- Do not surface: routine price noise; generic analyst notes
- Expire: until watch thesis is closed
- Preferred output: context change note

### Market backdrop

- Object: S&P breadth, AI trade, oil, and Fed path
- Conditions: S&P breadth, QQQ concentration, AI stocks, oil, Fed path
- Sources: market close, index breadth, sector watch, Fed calendar
- Cadence: daily after market close, plus after macro events
- Surface when: risk backdrop changes; breadth diverges from index; macro path changes
- Do not surface: minor index moves; generic market commentary; price-only updates
- Expire: until backdrop watch is retired
- Preferred output: context change note

### Mortgage rates

- Object: mortgage-rate watch
- Conditions: rate threshold, Fed signal, housing inventory
- Sources: FRED, mortgage rate feed, housing watch
- Cadence: weekly, plus after Fed/CPI events
- Surface when: rate threshold crossed; housing math changes materially
- Do not surface: unchanged rates; generic housing news
- Expire: configured review window
- Preferred output: decision-window note

### Bogey care

- Object: Bogey
- Conditions: vet schedule, heartworm refill, grooming, boarding
- Sources: calendar, vet email, notes, boarding email
- Cadence: weekly, daily inside travel windows
- Surface when: care deadline inside 7 days; boarding missing before travel
- Do not surface: generic pet reminders; completed care items
- Expire: after care window closes
- Preferred output: small action reminder

### Travel logistics

- Object: trip logistics
- Conditions: flight, parking, weather, packing, return plan
- Sources: calendar, airline email, weather, travel advisory
- Cadence: daily inside 7 days
- Surface when: departure is near; parking missing; weather changes packing or timing
- Do not surface: generic countdowns; unchanged itinerary; destination filler
- Expire: return date
- Preferred output: open travel loop

### Yankees and Rutgers

- Object: Yankees/Rutgers season and ticket posture
- Conditions: standings context, ticket deadlines, kickoff logistics
- Sources: sports schedule, team news, ticket portal
- Cadence: daily in season
- Surface when: planning or standings context changes; ticket deadline nears
- Do not surface: routine wins; routine losses; generic offseason notes
- Expire: end of season or renewal window
- Preferred output: only planning/context changes

### Golf weather and equipment

- Object: golf setup
- Conditions: weather window, tee time, equipment release, fitting slots
- Sources: weather, course email, manufacturer release, range account
- Cadence: weekly, plus day before tee times
- Surface when: playability changes; fitting slot opens; renewal window nears
- Do not surface: generic golf content; unchanged forecasts
- Expire: after tee time or renewal window
- Preferred output: planning or opportunity note

### Work migrations

- Object: work migration posture
- Conditions: adoption count, team response gap, deadline, blast radius
- Sources: GitHub Enterprise, Slack, Jira, security tooling
- Cadence: workday mornings
- Surface when: deadline or response gap threatens plan; exposure count changes
- Do not surface: project-name updates; unchanged status; generic rollout chatter
- Expire: after migration freeze
- Preferred output: posture change or escalation note

### Side projects

- Object: side-project direction
- Conditions: shipping momentum, validation evidence, cost, expiration
- Sources: GitHub, billing email, project notes, domain registrar
- Cadence: twice weekly
- Surface when: ship-or-stop posture changes; cost rises without progress
- Do not surface: task backlog churn; generic repo activity
- Expire: after project is shipped, stopped, or archived
- Preferred output: ship-or-stop note

### Home maintenance

- Object: home upkeep
- Conditions: service windows, seasonal risk, deferred tasks, renewals
- Sources: home checklist, calendar, email, seasonal rule
- Cadence: weekly
- Surface when: due inside 10 days; deferred repeatedly; season changes risk
- Do not surface: generic home tips; not-due-yet chores
- Expire: after task is completed or season passes
- Preferred output: small action reminder

### Life logistics

- Object: administrative deadlines
- Conditions: passport, TSA PreCheck, car registration, property taxes
- Sources: email, calendar, state portal, home folder
- Cadence: weekly, daily inside due windows
- Surface when: expiration or due date is inside action window; paperwork blocks travel
- Do not surface: generic reminders; paperwork with no open loop
- Expire: after deadline is closed
- Preferred output: small action reminder

### Family dates

- Object: family calendar
- Conditions: birthdays, holidays, gift windows, visit logistics
- Sources: calendar, notes, messages
- Cadence: weekly, daily inside 7 days
- Surface when: date inside 7 days; gift or plan not closed
- Do not surface: generic calendar reminders; events with no open loop
- Expire: day after event
- Preferred output: small action reminder

### WWDC and coding tools

- Object: developer tooling posture
- Conditions: workflow friction, developer impact, pricing, project assumptions
- Sources: vendor changelog, developer docs, project notes, pricing page
- Cadence: daily during event windows, otherwise weekly
- Surface when: tool default should change; project assumption changes; cost model changes
- Do not surface: generic launch coverage; unchanged benchmarks; rumor recap
- Expire: after event window or tool trial closes
- Preferred output: posture change note

### Health admin

- Object: health logistics
- Conditions: refill window, annual physical, eye exam, appointment availability
- Sources: calendar, pharmacy notice, provider portal
- Cadence: monthly, weekly inside due windows
- Surface when: routine care window opens; appointment slots narrow; refill gap nears
- Do not surface: medical interpretation; generic wellness content; not-due-yet reminders
- Expire: after appointment or refill is closed
- Preferred output: small action reminder

### Media queue

- Object: books and shows
- Conditions: prior-watch hook, saved recommendation, release timing
- Sources: streaming queue, book notes, recommendation
- Cadence: weekly
- Surface when: prior intent matches release; recommendation fits saved queue
- Do not surface: generic releases; trailer drops; lists with no prior intent
- Expire: after queue item is watched, read, or ignored
- Preferred output: light personal context note

## Onboarding Presets

Presets create editable watches. They are not fixed categories.

- Markets: creates Bitcoin range (watch:bitcoin-range)
- Sports teams: creates Yankees and Rutgers (watch:yankees-and-rutgers)
- Travel: creates Outdoor concert Friday (watch:outdoor-concert-friday)
- Family dates: creates Family dates (watch:family-dates)
- Home maintenance: creates Home maintenance (watch:home-maintenance)
- Pets: creates Bogey care (watch:bogey-care)
- Medical appointments: creates Health admin (watch:health-admin)
- Work projects: creates Work migrations (watch:work-migrations)
- Side projects: creates Side projects (watch:side-projects)
- Tech interests: creates WWDC and coding tools (watch:wwdc-and-coding-tools)

## Watch Quality Review

Each configured watch must support silent monitoring, useful surface, and explicit suppression before UI work continues.

### Outdoor concert Friday

- Valid: yes
- Silent: outdoor concert remains silent when weather is unchanged and no surface rule is met.
- Surface: Surface when rain risk > 35%: output as brief only what changed or what needs a decision.
- Suppress: Suppress when input is generic reminders.

### Bitcoin range

- Valid: yes
- Silent: Bitcoin remains silent when price range is unchanged and no surface rule is met.
- Surface: Surface when configured accumulation range crossed: output as decision-window note.
- Suppress: Suppress when input is minor daily moves.

### UNH watch

- Valid: yes
- Silent: UNH remains silent when drawdown is unchanged and no surface rule is met.
- Surface: Surface when drawdown materially changes assumptions: output as context change note.
- Suppress: Suppress when input is routine price noise.

### Market backdrop

- Valid: yes
- Silent: S&P breadth, AI trade, oil, and Fed path remains silent when S&P breadth is unchanged and no surface rule is met.
- Surface: Surface when risk backdrop changes: output as context change note.
- Suppress: Suppress when input is minor index moves.

### Mortgage rates

- Valid: yes
- Silent: mortgage-rate watch remains silent when rate threshold is unchanged and no surface rule is met.
- Surface: Surface when rate threshold crossed: output as decision-window note.
- Suppress: Suppress when input is unchanged rates.

### Bogey care

- Valid: yes
- Silent: Bogey remains silent when vet schedule is unchanged and no surface rule is met.
- Surface: Surface when care deadline inside 7 days: output as small action reminder.
- Suppress: Suppress when input is generic pet reminders.

### Travel logistics

- Valid: yes
- Silent: trip logistics remains silent when flight is unchanged and no surface rule is met.
- Surface: Surface when departure is near: output as open travel loop.
- Suppress: Suppress when input is generic countdowns.

### Yankees and Rutgers

- Valid: yes
- Silent: Yankees/Rutgers season and ticket posture remains silent when standings context is unchanged and no surface rule is met.
- Surface: Surface when planning or standings context changes: output as only planning/context changes.
- Suppress: Suppress when input is routine wins.

### Golf weather and equipment

- Valid: yes
- Silent: golf setup remains silent when weather window is unchanged and no surface rule is met.
- Surface: Surface when playability changes: output as planning or opportunity note.
- Suppress: Suppress when input is generic golf content.

### Work migrations

- Valid: yes
- Silent: work migration posture remains silent when adoption count is unchanged and no surface rule is met.
- Surface: Surface when deadline or response gap threatens plan: output as posture change or escalation note.
- Suppress: Suppress when input is project-name updates.

### Side projects

- Valid: yes
- Silent: side-project direction remains silent when shipping momentum is unchanged and no surface rule is met.
- Surface: Surface when ship-or-stop posture changes: output as ship-or-stop note.
- Suppress: Suppress when input is task backlog churn.

### Home maintenance

- Valid: yes
- Silent: home upkeep remains silent when service windows is unchanged and no surface rule is met.
- Surface: Surface when due inside 10 days: output as small action reminder.
- Suppress: Suppress when input is generic home tips.

### Life logistics

- Valid: yes
- Silent: administrative deadlines remains silent when passport is unchanged and no surface rule is met.
- Surface: Surface when expiration or due date is inside action window: output as small action reminder.
- Suppress: Suppress when input is generic reminders.

### Family dates

- Valid: yes
- Silent: family calendar remains silent when birthdays is unchanged and no surface rule is met.
- Surface: Surface when date inside 7 days: output as small action reminder.
- Suppress: Suppress when input is generic calendar reminders.

### WWDC and coding tools

- Valid: yes
- Silent: developer tooling posture remains silent when workflow friction is unchanged and no surface rule is met.
- Surface: Surface when tool default should change: output as posture change note.
- Suppress: Suppress when input is generic launch coverage.

### Health admin

- Valid: yes
- Silent: health logistics remains silent when refill window is unchanged and no surface rule is met.
- Surface: Surface when routine care window opens: output as small action reminder.
- Suppress: Suppress when input is medical interpretation.

### Media queue

- Valid: yes
- Silent: books and shows remains silent when prior-watch hook is unchanged and no surface rule is met.
- Surface: Surface when prior intent matches release: output as light personal context note.
- Suppress: Suppress when input is generic releases.

## Preset Quality Review

- Markets: valid; creates watch:bitcoin-range
- Sports teams: valid; creates watch:yankees-and-rutgers
- Travel: valid; creates watch:outdoor-concert-friday
- Family dates: valid; creates watch:family-dates
- Home maintenance: valid; creates watch:home-maintenance
- Pets: valid; creates watch:bogey-care
- Medical appointments: valid; creates watch:health-admin
- Work projects: valid; creates watch:work-migrations
- Side projects: valid; creates watch:side-projects
- Tech interests: valid; creates watch:wwdc-and-coding-tools

## Generated Events Summary

### Domains

- Work: 250
- Finance & Markets: 230
- Technology & AI: 165
- Personal & Family: 90
- Dog: 75
- Sports & Golf: 110
- Golf Equipment: 60
- Books & Entertainment: 60
- Health: 75
- Life Logistics: 120
- Home Ownership: 85
- Travel: 85
- Side Projects: 95

### Event Classes

- Deadline: Time-bound event with meaningful loss if ignored.
- Opportunity: Decision window where value can be captured or lost.
- Context Change: New information changes future decisions or assumptions.
- Monitoring: Object stays active but silent until conditions change.
- Maintenance: Recurring or rare upkeep with date or risk pressure.
- Noise: Generic update that should usually be suppressed.

## Generation Standard

- Keep the taxonomy, ranking model, and watch admin model.
- Generate events downstream of configured watches and other sources.
- Keep configured watches, generated events, and briefing outputs separate.
- Generate around attention objects users actually care about: counts, expirations, thresholds, people, pets, travel, hobbies, and posture changes.
- Do not treat project names, launch names, or generic categories as events by themselves.
- Lead stories are intentionally rare: target 20-30 candidates in a 1500-event corpus.
- Briefing outputs must include source_watch_ids, triggered_surface_rule, suppressed_by, and why_today.

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

## Watch Admin Model

{
  "definition": "A watch is user-authored attention infrastructure, not a passive briefing artifact.",
  "required_fields": [
    "object",
    "conditions",
    "sources",
    "cadence",
    "surface_rules",
    "suppression_rules",
    "expiration",
    "preferred_output"
  ],
  "default_behavior": "Evaluate on cadence, suppress unchanged or generic inputs, and emit briefing candidates only when surface rules are met.",
  "examples": {
    "Outdoor Concert": {
      "object": "outdoor concert",
      "conditions": [
        "weather",
        "parking",
        "timing",
        "venue changes"
      ],
      "sources": [
        "calendar",
        "weather",
        "venue email",
        "parking feed"
      ],
      "cadence": "daily until 72 hours out, then morning and afternoon",
      "surface_rules": [
        "rain risk > 35%",
        "parking changes materially",
        "event is within 48 hours",
        "venue sends an update"
      ],
      "suppression_rules": [
        "generic reminders",
        "unchanged weather",
        "concert is coming up filler"
      ],
      "expiration": "day after event",
      "preferred_output": "brief only what changed or what needs a decision"
    },
    "WWDC": {
      "object": "WWDC",
      "conditions": [
        "keynote date",
        "major announcements",
        "developer impact"
      ],
      "sources": [
        "Apple developer news",
        "calendar",
        "project notes"
      ],
      "cadence": "daily during event week",
      "surface_rules": [
        "project assumption changes",
        "developer tooling impact is practical"
      ],
      "suppression_rules": [
        "generic launch coverage",
        "unchanged rumor recap"
      ],
      "expiration": "7 days after keynote",
      "preferred_output": "project posture change"
    },
    "Vacation": {
      "object": "Trip",
      "conditions": [
        "flight",
        "weather",
        "travel advisories"
      ],
      "sources": [
        "calendar",
        "airline email",
        "weather"
      ],
      "cadence": "daily inside 7 days",
      "surface_rules": [
        "departure is near",
        "weather changes packing or timing"
      ],
      "suppression_rules": [
        "generic countdowns",
        "unchanged itinerary"
      ],
      "expiration": "return date",
      "preferred_output": "open travel loop"
    },
    "Mortgage Rate": {
      "object": "Mortgage-rate watch",
      "conditions": [
        "rate threshold",
        "Fed signal",
        "housing inventory"
      ],
      "sources": [
        "FRED",
        "mortgage rate feed",
        "housing watch"
      ],
      "cadence": "weekly, plus after Fed/CPI events",
      "surface_rules": [
        "rate threshold crossed",
        "housing math changes materially"
      ],
      "suppression_rules": [
        "unchanged rates",
        "generic housing news"
      ],
      "expiration": "configured review window",
      "preferred_output": "decision-window note"
    }
  }
}

## Simulation

The companion May-June 2026 simulation intentionally includes boring days, no-primary-focus days, competing-focus days, and watch-driven outputs that land in real domains rather than a Watch Items domain.
