from __future__ import annotations

import re


LEGACY_DEFAULT_WATCH_TITLES = {
    "Portfolio & market positioning",
    "Yankees",
    "Rutgers",
    "Golf weather",
    "Golf equipment",
    "AI / developer tools",
    "Work / namespace migration",
    "Side projects",
    "Home maintenance",
    "Bogey",
    "Life logistics",
    "Travel",
}


def watch_config(
    name: str,
    *,
    watch_kind: str,
    priority: str,
    cadence: str,
    why_i_care: str,
    accounts: list[str],
    interests: list[str],
    owned_assets: list[str],
    ignored_accounts: list[str],
    connected_sources: list[str],
    available_sources: list[str],
    missing_sources: list[str],
    manual_inputs: list[str],
    surface_when: list[str],
    suppress_when: list[str],
    primary_focus_allowed: bool,
    manual_facts: dict | None = None,
) -> dict:
    return {
        "title": name,
        "name": name,
        "original_text": f"{name}\n{why_i_care}",
        "watch_kind": watch_kind,
        "priority": priority,
        "cadence": cadence,
        "watch_for": interests[:8] or manual_inputs[:4] or connected_sources[:4],
        "surface_when": surface_when,
        "suppress_when": suppress_when,
        "personal_context": {
            "why_i_care": why_i_care,
            "accounts": accounts,
            "interests": interests,
            "owned_assets": owned_assets,
            "ignored_accounts": ignored_accounts,
            "manual_facts": manual_facts or {},
        },
        "source_config": {
            "connected_sources": connected_sources,
            "available_sources": available_sources,
            "missing_sources": missing_sources,
            "manual_inputs": manual_inputs,
        },
        "evaluation_rules": {
            "surface_when": surface_when,
            "suppress_when": suppress_when,
            "primary_focus_allowed": primary_focus_allowed,
        },
    }


DEFAULT_MIKE_WATCHES = [
    watch_config(
        "Personal finance and liquidity runway",
        watch_kind="hybrid",
        priority="primary_allowed",
        cadence="daily",
        why_i_care="Mike's main financial goal is increasing liquid cash and maintaining enough safety to eventually leave corporate work.",
        accounts=["Fidelity", "SoFi", "Tastytrade"],
        interests=["liquidity", "cash runway", "year-end readiness", "2040 long-term target"],
        owned_assets=[],
        ignored_accounts=[],
        connected_sources=["manual_portfolio_csv", "market_price_adapter"],
        available_sources=["Plaid", "brokerage_adapters"],
        missing_sources=["direct Fidelity integration", "direct SoFi integration", "direct Tastytrade integration"],
        manual_inputs=["liquid cash balance", "side income", "large upcoming expenses"],
        manual_facts={
            "liquid_cash_target": 10000,
            "liquid_cash_minimum": 5000,
        },
        surface_when=[
            "liquid cash falls near or below $10,000 target",
            "liquid cash falls near or below $5,000 minimum",
            "side income materially changes runway",
            "year-end liquidity posture changes",
            "cash shortage risk appears",
        ],
        suppress_when=[
            "balances unchanged",
            "generic financial advice",
            "market movement has no liquidity implication",
            "same condition was already surfaced without change",
        ],
        primary_focus_allowed=True,
    ),
    watch_config(
        "Investing ideas and market pullbacks",
        watch_kind="hybrid",
        priority="primary_allowed",
        cadence="daily",
        why_i_care="Mike wants fact-based monitoring of companies, major mutuals/ETFs, and investment ideas when they drop enough to deserve review.",
        accounts=["Fidelity", "SoFi", "Tastytrade"],
        interests=["UNH", "BTC", "USO", "SPY", "QQQ", "AAPL", "S&P 500", "recommended stocks", "loud market chatter with verifiable data"],
        owned_assets=[],
        ignored_accounts=[],
        connected_sources=["market_price_adapter", "manual_investing_notes"],
        available_sources=["official filings/news", "earnings calendar", "market news adapter"],
        missing_sources=["direct brokerage positions unless adapter available"],
        manual_inputs=["investment thesis notes", "review ranges", "saved ideas"],
        manual_facts={
            "tracked_symbols": ["UNH", "BTC", "USO", "SPY", "QQQ", "AAPL", "S&P 500 proxy"],
            "symbol_notes": {
                "USO": {
                    "position": "short",
                    "note": "Short position. Surface lower moves as progress toward the short thesis, not as a buy-the-dip idea.",
                },
                "BTC": {
                    "position": "accumulate",
                    "note": "Accumulate only when the pullback is meaningful enough to improve or review cost basis.",
                },
            },
        },
        surface_when=[
            "tracked symbol drops at least 5% over roughly 72 hours",
            "major ETF/index/company has a verified drawdown or unusual move",
            "saved investing thesis is materially challenged or strengthened",
            "high-confidence opportunity is detected based on verifiable data",
            "loud market chatter maps to a tracked symbol and has factual support",
        ],
        suppress_when=[
            "opinion-only content",
            "unverified chatter",
            "routine price movement below threshold",
            "analyst opinions without data",
            "news that does not affect a tracked symbol or saved thesis",
        ],
        primary_focus_allowed=True,
    ),
    watch_config(
        "Bitcoin accumulation posture",
        watch_kind="hybrid",
        priority="primary_allowed",
        cadence="daily",
        why_i_care="Mike currently only cares about Bitcoin in crypto. Goal is to accumulate when BTC declines enough to improve or meaningfully review cost basis.",
        accounts=["SoFi"],
        interests=["BTC", "Bitcoin cost basis", "Bitcoin pullbacks"],
        owned_assets=["BTC if imported or manually supplied"],
        ignored_accounts=[],
        connected_sources=["CoinGecko", "manual_crypto_notes"],
        available_sources=["SoFi adapter if available", "crypto market news adapter"],
        missing_sources=["direct SoFi BTC cost basis unless adapter available"],
        manual_inputs=["BTC cost basis", "BTC holdings", "last purchase price if unavailable"],
        manual_facts={
            "accumulation_posture": "accumulate only when pullback is meaningful",
            "btc_cost_basis": 75000,
        },
        surface_when=[
            "Bitcoin falls materially over a few days",
            "Bitcoin falls around 10% after a significant prior rise",
            "Bitcoin decline creates possible cost-basis improvement",
            "Bitcoin decline is still above cost basis but large enough to consider review",
            "major Bitcoin-specific regulatory/platform/security event changes thesis",
        ],
        suppress_when=[
            "generic crypto headlines",
            "non-BTC crypto noise",
            "influencer commentary",
            "minor daily BTC movement",
            "memecoin or altcoin chatter",
        ],
        primary_focus_allowed=True,
    ),
    watch_config(
        "Trading systems and liquidity constraints",
        watch_kind="hybrid",
        priority="watch_only",
        cadence="weekly",
        why_i_care="Mike is interested in trading systems but is not currently liquid enough to trade actively.",
        accounts=["Fidelity", "Tastytrade"],
        interests=["algorithmic trading", "future trading systems", "strategy validation"],
        owned_assets=[],
        ignored_accounts=[],
        connected_sources=["manual_trading_notes"],
        available_sources=["broker adapters if available", "repo activity"],
        missing_sources=["live broker execution data"],
        manual_inputs=["strategy notes", "risk limits", "paper trading notes"],
        manual_facts={
            "trading_status": "interested but not active due liquidity",
        },
        surface_when=[
            "strategy validation materially changes",
            "broker/API change affects future automation",
            "liquidity changes enough to revisit active trading",
            "repo/action item blocks trading system progress",
        ],
        suppress_when=[
            "generic market news",
            "unvalidated strategy ideas",
            "routine repo activity",
            "trading content with no current liquidity relevance",
        ],
        primary_focus_allowed=False,
    ),
    watch_config(
        "Personal GitHub repo health",
        watch_kind="hybrid",
        priority="primary_allowed",
        cadence="daily",
        why_i_care="Mike wants a quick action queue for public personal repos in dock108dev: PRs, vulnerabilities, failing workflows, stale activity, and new tech that could improve a repo.",
        accounts=["GitHub org/user dock108dev"],
        interests=["active public repos", "repo health", "automated PRs", "security", "workflow failures", "stale projects"],
        owned_assets=[],
        ignored_accounts=["archived repos"],
        connected_sources=["GitHub API"],
        available_sources=["GitHub Actions", "GitHub Dependabot/security alerts if API scope allows"],
        missing_sources=["private repo access unless granted"],
        manual_inputs=["active repo allowlist optional"],
        manual_facts={
            "github_org": "dock108dev",
            "scope": "public non-archived repos only",
        },
        surface_when=[
            "open PR needs quick review",
            "automated PR is opened",
            "new vulnerability/security alert appears",
            "workflow starts failing",
            "active repo has no commits for about 2 weeks",
            "new tool/platform release could materially improve a repo",
            "repo has an obvious action item blocking progress",
        ],
        suppress_when=[
            "archived repos",
            "normal commits",
            "closed PRs",
            "inactive repo noise unless inactivity itself is the signal",
            "duplicate alerts already surfaced",
        ],
        primary_focus_allowed=True,
    ),
    watch_config(
        "Side project and FocusOS validation",
        watch_kind="personal_tracker",
        priority="primary_allowed",
        cadence="daily",
        why_i_care="Mike is building software for financial autonomy. FocusOS itself must prove daily usefulness through live data, suppression, and actionability.",
        accounts=["dock108dev public repos"],
        interests=["FocusOS", "Static", "algorithmic trading", "software products", "cash-flow projects"],
        owned_assets=[],
        ignored_accounts=[],
        connected_sources=["GitHub API", "manual_project_notes"],
        available_sources=[],
        missing_sources=[],
        manual_inputs=["daily product review notes", "validation notes", "ship-or-stop decisions"],
        surface_when=[
            "project has a ship-or-stop decision",
            "FocusOS produces noise that should have been suppressed",
            "FocusOS misses something that should have surfaced",
            "repo inactivity suggests project drift",
            "new validation changes project priority",
        ],
        suppress_when=[
            "generic motivation reminders",
            "normal repo activity",
            "UI-only complaint with no behavior impact",
            "duplicate feedback already captured",
        ],
        primary_focus_allowed=True,
    ),
    watch_config(
        "Big tech, AI, and major company releases",
        watch_kind="external_monitor",
        priority="watch_only",
        cadence="daily",
        why_i_care="Mike wants major tech news and releases that matter for software building, AI tools, investing context, or personal purchasing decisions.",
        accounts=[],
        interests=["AI", "developer tools", "major tech companies", "new product releases", "pricing changes", "major announcements"],
        owned_assets=[],
        ignored_accounts=[],
        connected_sources=["official changelog/RSS adapter", "major tech news adapter"],
        available_sources=["OpenAI", "Anthropic", "Google", "Apple", "Microsoft", "Meta", "Amazon", "Nvidia", "GitHub", "Cursor", "Cloudflare", "Vercel", "Hetzner"],
        missing_sources=[],
        manual_inputs=[],
        surface_when=[
            "major AI/model release changes workflow",
            "major developer platform release changes workflow",
            "pricing or access changes affect tools Mike uses",
            "major tech company announcement affects investing or shopping interests",
            "new release could improve one of Mike's repos or side projects",
        ],
        suppress_when=[
            "opinion-only tech commentary",
            "rumors unless clearly labeled and highly material",
            "benchmark-only AI chatter",
            "minor feature updates",
            "generic hype",
        ],
        primary_focus_allowed=False,
    ),
    watch_config(
        "Sports radar with spoiler-safe recap",
        watch_kind="external_monitor",
        priority="watch_only",
        cadence="daily",
        why_i_care="Mike wants top-of-mind sports info for teams/events he follows, reminders to watch meaningful events, major news, and next-day highlight links when possible without spoiling results in titles.",
        accounts=[],
        interests=["Rutgers football", "Rutgers basketball", "Yankees", "Cowboys", "major sports playoffs", "postseason", "World Cup", "Olympics", "global sports events", "F1", "PGA Tour", "golf majors"],
        owned_assets=["Rutgers season ticket interest"],
        ignored_accounts=[],
        connected_sources=["sports feed adapter"],
        available_sources=["ESPN or sports API", "YouTube API for official highlights if available", "F1 API", "PGA/golf feed"],
        missing_sources=["spoiler-safe highlight verification if API does not provide clean metadata"],
        manual_inputs=[],
        surface_when=[
            "game/event is worth remembering to watch",
            "major trade/injury/news occurs",
            "postseason/ranking/standings posture changes",
            "major global event or final is upcoming",
            "F1 race weekend/qualifying/race result is notable",
            "PGA major or notable final-round context appears",
            "spoiler-safe highlight link is available next day",
        ],
        suppress_when=[
            "routine score with no context",
            "generic preview",
            "hot take/debate content",
            "betting content",
            "spoiler-heavy highlight title when user has not opted into results",
        ],
        primary_focus_allowed=False,
    ),
    watch_config(
        "Golf weather for Basking Ridge",
        watch_kind="external_monitor",
        priority="watch_only",
        cadence="daily",
        why_i_care="Mike mainly cares about whether local golf weather is playable at/near Basking Ridge. He does not need golf equipment monitoring.",
        accounts=[],
        interests=["Basking Ridge golf weather", "playable windows"],
        owned_assets=[],
        ignored_accounts=[],
        connected_sources=["Open-Meteo"],
        available_sources=["weather API"],
        missing_sources=["tee time calendar unless connected later"],
        manual_inputs=["specific course optional"],
        manual_facts={
            "location": "Basking Ridge, NJ",
            "ideal_temperature_f": "60-85",
            "max_rain_probability_pct": 30,
            "suppress_monday": "course closed",
            "suppress_friday_afternoon": "likely crowded",
        },
        surface_when=[
            "weather is 60-85°F with less than 30% rain",
            "a standout playable window opens",
            "rain/wind makes likely play questionable",
            "weekend window is materially better or worse than expected",
        ],
        suppress_when=[
            "Monday because course is closed",
            "Friday afternoon unless weather is exceptional because it is likely packed",
            "ordinary weather with no notable window",
            "generic golf content",
            "equipment news",
        ],
        primary_focus_allowed=False,
    ),
    watch_config(
        "Shopping and product interest radar",
        watch_kind="hybrid",
        priority="quiet_by_default",
        cadence="daily",
        why_i_care="Mike wants occasional useful shopping/product updates for tech, gaming, PC builds, graphics cards, monitors, software, and major game/console news.",
        accounts=["Amazon if integration becomes feasible"],
        interests=["tech", "video games", "gaming PC", "graphics cards", "monitors", "software subscriptions", "console releases", "PS6-type news"],
        owned_assets=[],
        ignored_accounts=[],
        connected_sources=["manual_shopping_interests"],
        available_sources=["Steam API", "Amazon adapter if feasible", "Best Buy/product feed if feasible", "gaming news RSS"],
        missing_sources=["direct Amazon purchase/preference integration unless available"],
        manual_inputs=["saved products", "purchase interests", "target prices"],
        surface_when=[
            "saved product has meaningful price drop",
            "graphics card or PC component prices materially decline",
            "major console/game release news matches interest",
            "purchase would affect liquidity target",
            "new product release changes planned purchase timing",
        ],
        suppress_when=[
            "generic deals",
            "minor discounts",
            "unrelated products",
            "influencer shopping lists",
            "shopping item with no saved or inferred interest",
        ],
        primary_focus_allowed=False,
    ),
    watch_config(
        "Media and watchlist radar",
        watch_kind="hybrid",
        priority="quiet_by_default",
        cadence="weekly",
        why_i_care="Mike wants occasional movies, TV, podcast, YouTube, or media recommendations tied to actual preferences and availability. Blank starting data is allowed.",
        accounts=["YouTube", "YouTube TV", "Netflix", "Prime Video"],
        interests=["problem-solving stories", "dry humor", "Project Hail Mary / The Martian style", "Sherlock style", "clever history/heist videos", "short power-down content"],
        owned_assets=[],
        ignored_accounts=[],
        connected_sources=["manual_media_preferences"],
        available_sources=["YouTube API", "TMDB", "JustWatch", "podcast RSS"],
        missing_sources=["Netflix direct watchlist if unavailable", "Prime Video direct watchlist if unavailable"],
        manual_inputs=["liked shows/books/podcasts", "watchlist", "dislikes"],
        surface_when=[
            "saved item becomes available",
            "new release strongly matches known preferences",
            "high-confidence recommendation appears",
            "new YouTube/video item matches interest and is short/useful",
        ],
        suppress_when=[
            "generic top-10 lists",
            "celebrity news",
            "weak recommendations",
            "horror unless explicitly added",
            "long/slow content unless explicitly added",
        ],
        primary_focus_allowed=False,
    ),
    watch_config(
        "Life notes, reminders, and personal admin",
        watch_kind="personal_tracker",
        priority="primary_allowed",
        cadence="daily",
        why_i_care="Mike wants a flexible life section where he can add notes, dates, reminders, Bogey items, admin tasks, and personal watchlist items over time.",
        accounts=[],
        interests=["life reminders", "Bogey", "admin", "dates", "tasks"],
        owned_assets=[],
        ignored_accounts=[],
        connected_sources=["manual_notes"],
        available_sources=["calendar integration later", "email integration later"],
        missing_sources=["specific integrations until user opts in"],
        manual_inputs=["notes", "dates", "reminders", "care items"],
        surface_when=[
            "user-entered deadline enters warning window",
            "reminder becomes actionable",
            "personal note changes posture",
            "Bogey care item needs action",
            "admin item could cost money or create avoidable hassle",
        ],
        suppress_when=[
            "undated note with no action window",
            "generic reminders",
            "completed item",
            "duplicate reminder already surfaced",
        ],
        primary_focus_allowed=True,
    ),
]


def watch_key(value: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return key or "watch"


def source_watch_id(title: str) -> str:
    return f"watch:{watch_key(title)}"


def provenance_for_attention_item(item: dict) -> dict:
    source = str(item.get("source") or "").lower()
    topic = str(item.get("topic") or "").lower()
    detail_id = str(item.get("detail_id") or "")
    domain = str(item.get("domain") or item.get("vertical") or "").lower()
    title = str(item.get("title") or "").lower()
    why_today = str(item.get("why_today") or item.get("why_now") or "")

    if detail_id == "portfolio:review" or detail_id.startswith("finance:"):
        return {
            "source_watch_ids": [source_watch_id("Personal finance and liquidity runway")],
            "triggered_surface_rule": "portfolio review threshold crossed",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if source == "market" or detail_id.startswith("market:"):
        return {
            "source_watch_ids": [source_watch_id("Investing ideas and market pullbacks")],
            "triggered_surface_rule": "market move or pullback threshold crossed",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if source == "crypto" or detail_id.startswith("crypto:") or topic == "bitcoin":
        return {
            "source_watch_ids": [source_watch_id("Bitcoin accumulation posture")],
            "triggered_surface_rule": "Bitcoin range or daily move threshold crossed",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if source == "weather" or topic == "golf" or detail_id.startswith("weather:golf"):
        return {
            "source_watch_ids": [source_watch_id("Golf weather for Basking Ridge")],
            "triggered_surface_rule": "golf weather window crossed planning threshold",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if topic == "yankees" or "yankees" in title:
        return {
            "source_watch_ids": [source_watch_id("Sports radar with spoiler-safe recap")],
            "triggered_surface_rule": "watched team result or schedule update changed",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if topic == "rutgers" or "rutgers" in title:
        return {
            "source_watch_ids": [source_watch_id("Sports radar with spoiler-safe recap")],
            "triggered_surface_rule": "watched team result or schedule update changed",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if topic == "ai" or domain == "technology":
        return {
            "source_watch_ids": [source_watch_id("Big tech, AI, and major company releases")],
            "triggered_surface_rule": "developer-tool or AI update met attention threshold",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if source == "github" or topic == "github":
        return {
            "source_watch_ids": [source_watch_id("Personal GitHub repo health")],
            "triggered_surface_rule": "public repo health rule triggered",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if source == "watchlist":
        return {
            "source_watch_ids": list(item.get("source_watch_ids") or []),
            "triggered_surface_rule": str(item.get("triggered_surface_rule") or ""),
            "suppressed_by": item.get("suppressed_by"),
            "why_today": why_today,
        }
    return {
        "source_watch_ids": ["system:manual-or-topic-import"],
        "triggered_surface_rule": "system or manual source met briefing threshold",
        "suppressed_by": None,
        "why_today": why_today,
    }
