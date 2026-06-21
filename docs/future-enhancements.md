# Future Enhancements

This document captures future-state ideas discussed during planning. None of these are required for MVP completion. The purpose is to preserve ideas so they do not consume current development effort.

## Topic-Based AI Briefings

Allow users to create custom topics and receive AI-generated summaries each morning. Topics can range from finance and sports to geopolitical events and hobbies.

The system should determine what changed, why it matters, and whether action is required rather than simply summarizing articles.

## Sports Intelligence Module

Track favorite teams, leagues, and sporting events. Generate briefings that focus on results, upcoming games, injuries, major storylines, and championship implications.

The objective is reducing the need to visit multiple sports sites while remaining informed.

## Spoiler-Safe Highlights

Provide links to game highlights while intentionally hiding scores and outcomes. This allows users to remain informed that highlights are available without spoiling games they have not watched.

Future implementations could include title filtering and score detection.

## Global Sports Calendar

Maintain a continuously updated schedule of major sporting events around the world. Examples include Grand Slam tennis events, golf majors, World Cups, Formula 1 races, major soccer competitions, bowling majors, and Olympic events.

The goal is ensuring important events are never missed due to lack of awareness.

## Golf Recommendation Engine

Combine weather forecasts, calendar availability, and user preferences to identify optimal golf days.

Examples include identifying the best weather windows, least windy days, and ideal tee time opportunities.

## Weather-Based Recommendations

Move beyond weather reporting and provide actionable recommendations.

Examples:

- Best day for golf
- Best day for outdoor work
- Best travel day
- Best dog-walking weather

## YouTube and Content Tracking

Monitor subscribed creators and surface meaningful uploads.

Rather than displaying every new video, prioritize content most aligned with user interests and recent activity.

## Podcast Monitoring

Track podcast releases and highlight episodes likely to be most relevant.

Potential future enhancements include AI-generated summaries and episode importance scoring.

## Book and Media Tracking

Monitor upcoming book releases, TV premieres, documentaries, and films related to selected interests.

The focus should remain on relevance rather than comprehensive entertainment coverage.

## Financial Opportunity Engine

Identify potential opportunities based on predefined signals.

Examples:

- Large-cap stocks down a specified percentage
- Bitcoin pullbacks
- Sector weakness
- Historical mean-reversion opportunities

The system should highlight opportunities rather than generate trading recommendations.

## Data Source Expansion

Structured sources should be added only after the homepage proves useful. The likely order is captured in [data-sources.md](data-sources.md).

Immediate structured candidates:

- Yahoo Finance for market prices
- CoinGecko for crypto
- OpenWeather or Pirate Weather for weather-driven recommendations
- ESPN APIs for Yankees, Rutgers, and major scores

AI-source candidates:

- Geopolitics such as Iran, China/Taiwan, and Ukraine
- AI industry developments across OpenAI, Anthropic, Google, and major model releases
- Major world sports summaries derived from a curated calendar rather than live scraping

## Portfolio Rebalancing Suggestions

Monitor allocations and identify positions that have drifted beyond target thresholds.

Future versions could simulate allocation changes and estimate portfolio impacts before any action is taken.

## Capital Allocation Dashboard

Provide a unified view of deployable capital across accounts.

This would help answer:

- How much cash is available?
- Where is idle capital sitting?
- What opportunities currently exist?

## Trade Journal

Automatically record investment decisions and allow manual rationale entries.

Over time, the system could identify patterns, mistakes, and successful decision-making processes.

## Market Regime Detection

Classify broader market conditions.

Examples:

- Risk-on
- Risk-off
- Correction
- Recovery
- High volatility

This provides context for interpreting signals and opportunities.

## Arbitrage Discovery Engine

Monitor user-defined markets for pricing discrepancies.

Potential future use cases include sports, financial products, prediction markets, and other opportunities where price differences create actionable situations.

## Personal Calendar Integration

Incorporate calendar awareness into daily recommendations.

The system could avoid recommending activities during conflicts and identify free windows for hobbies, travel, or personal projects.

## Travel Awareness

Track planned trips and upcoming travel opportunities.

Examples:

- Passport expiration reminders
- Flight pricing changes
- Event overlap with destinations
- Weather considerations

## Personal Task Awareness

Surface tasks that deserve attention based on age, priority, and context.

The objective is not task management but identifying forgotten items that are becoming important.

## Life Operating System

Long-term evolution of the platform.

The platform becomes a personal chief of staff that continuously evaluates:

- finances
- sports
- travel
- weather
- content
- tasks
- opportunities

and answers one question:

> What deserves my attention today?

## AI Attention Scoring

Assign an importance score to all surfaced items.

The score should consider:

- relevance
- urgency
- impact
- personal interests
- historical engagement

to determine what appears in the daily briefing.

## Historical Attention Analytics

Track which recommendations were acted on and which were ignored.

Over time the system could learn what consistently attracts attention and adjust future briefings accordingly.

## Personalized Signal Learning

Learn from user interactions and engagement patterns.

The goal is creating a briefing that becomes increasingly tailored over time rather than relying on static rules.

## Mobile Application

Native iOS application providing the daily briefing experience.

Potential future features include widgets, lock-screen summaries, Apple Watch support, and morning notification delivery.

## FocusOS

Ultimate future vision.

A single application that reduces information overload and continuously converts noise into signal across all areas of life.

The user should feel less compelled to check multiple applications because the platform already surfaces what matters most.
