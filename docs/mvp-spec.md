# FocusOS MVP Specification

## Product Rule

FocusOS is for Mike. Nobody else exists.

The MVP replaces the morning loop of opening finance apps, sports apps, weather, YouTube, and news sites with a single briefing that answers:

> What deserves my attention today?

The answer should take less than 60 seconds to read.

## Revised Scope

Finance remains the first structured source. The product direction is broader:

> What deserves my attention today?

The MVP now supports both structured sources and AI-generated topic briefings.

Allowed:

- Manual CSV import
- Fidelity holdings
- SoFi holdings
- Tastytrade holdings
- Portfolio value
- Daily and monthly change from import snapshots
- Cash available
- Allocation
- Portfolio state
- Portfolio intelligence
- Attention items
- Internal attention item classification: Action Required, Potential Opportunity, or Worth Knowing
- Opportunity candidates
- User-defined topics
- AI-generated topic briefings
- Structured source placeholders for market, crypto, weather, and sports APIs

Banned:

- Stock screener
- Trading interface
- Order entry
- Options chains
- Candlestick charts
- Raw news feeds
- Watchlists
- Social features
- AI chat
- Multi-user portfolios
- Backtesting
- Arbitrage
- Betting tools
- Sports dashboards
- Weather dashboards
- YouTube
- Calendar
- Tasks
- Reminders
- Notifications
- Mobile app
- Browser extension
- Trading decisions
- Portfolio management
- Financial advice
- Order execution

## Topic Model

Every topic has:

- name
- priority
- source type: structured or unstructured
- category
- refresh frequency
- prompt

Initial topics:

- Yankees
- Bitcoin
- Iran
- Major World Sports
- AI
- Golf

## Homepage

One page.

- Morning Briefing
- one curated scroll of edited briefing items
- one featured item and secondary stories
- briefing appendix modal after tapping an item

No navigation, settings, profile, administration, or dashboard sprawl.

Homepage rules:

- Do not show priority, category, confidence, scores, or source labels in the primary briefing.
- Do not show generic calls to action such as "review whether," "decide whether," or "consider whether" in the primary briefing.
- The existence of an item implies it is worth attention.
- Each line should read like an editor already interpreted the data.
- Audit details belong in the appendix modal, not on the homepage.
- Routine portfolio facts do not belong in the Morning Briefing.
- Portfolio, Portfolio Intelligence, and Topics are inputs. They should not appear as separate homepage sections.
- Portfolio concentration, allocation, cash, and holdings analysis belongs off the homepage unless it is important enough to be an actual morning event.

Information classes are internal ranking/context only. They must not appear as homepage section headers.

- Action Required: rare threshold breaks or urgent events, ideally 0-3 per day.
- Potential Opportunity: windows worth considering, without turning them into tasks.
- Worth Knowing: relevant context with no action implied.

Portfolio layers:

- Portfolio State: value, cash, allocation, holdings, and performance. This is context.
- Portfolio Intelligence: concentration, threshold crossings, allocation drift, and potential opportunities. This is analysis.
- Attention Feed: conclusions and events that genuinely deserve morning attention.

Implementation rule: `/api/briefing.attention` is the single supported homepage feed. Finance, structured sources, and topic briefings may contribute inputs, but the frontend must not reconstruct the feed from alternate portfolio or topic payloads.

## Morning Workflow

- 06:00 scheduled jobs run
- 06:05 structured data collected
- 06:10 AI topic briefings generated
- 06:15 daily briefing assembled
- 07:00 ready for consumption

The local Docker stack includes a scheduler service that triggers `/api/jobs/morning-briefing` daily. Startup seeds fallback topic briefings without spending AI calls; the scheduled or manual job performs live generation when sources are configured.

The job endpoint returns a `job_id` immediately and performs refresh work in the background. Job progress can be read from `/api/jobs/morning-briefing/{job_id}`.

Scheduling is handled by APScheduler in the scheduler service.

## Attention Engine

Every item must satisfy:

1. What happened?
2. Is it interesting or consequential?
3. Is action genuinely required?

If any answer is no, do not show it.

Bad:

> Apple is $214.22

Good:

> Apple has fallen 6.1% in five trading days.

## 30-Day Success Metric

After 30 consecutive days, Mike voluntarily opened the app at least 25 days.

If not, stop development and reassess. More integrations are not the answer until the homepage proves it changes behavior.

## Product Direction

The app is not a dashboard. It should feel like a chief of staff.

Signals explain what changed. The homepage should not delegate the thinking back to Mike with generic action copy.

The product should answer:

> What should I know today?

Sometimes that leads to action. Most of the time it does not.

Every card should be interesting or consequential without saying "why Mike should care" or exposing implementation details such as source setup, API status, provider names, or missing connectors.

## Recommendation Details

Every homepage item should be clickable.

The homepage stays concise. The appendix modal provides trust through transparency:

- final recommendation text
- why it was generated
- thresholds and rules triggered
- underlying data used
- sources and fetch metadata
- methodology when AI or rules were involved
- items not shown and why they were hidden

Raw payloads may exist for auditability, but they should be collapsed by default and secondary to readable evidence.

## Personalization

Mike-specific thresholds live in code so they are visible and adjustable:

- cash review threshold
- technology concentration threshold
- single-position concentration threshold
- pullback review threshold
- market move review threshold

The current finance copy reflects Mike’s stated behavior: large-cap pullbacks are review moments, not automatic trades.

## Future Ideas

Future-state ideas are captured separately in [future-enhancements.md](future-enhancements.md). That document is a parking lot, not MVP scope.
