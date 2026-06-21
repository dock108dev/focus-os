# ADR 0012: Briefing information classes

## Status

Accepted.

## Context

Treating every signal as a task turns FocusOS into another inbox. Most daily information does not require action. If every item says "review," "decide," or "consider," the briefing creates guilt instead of confidence.

The product is not primarily:

> What should I do today?

The product is:

> What should I know today?

Sometimes that leads to action. Most of the time it should not.

## Decision

Classify every homepage briefing item into one of three classes:

- `Action Required`: rare threshold breaks or urgent events that genuinely need attention.
- `Potential Opportunity`: favorable windows or notable pullbacks worth considering, without becoming tasks.
- `Worth Knowing`: relevant context with no action implied.

Homepage rules:

- No action text unless action is genuinely warranted.
- Awareness items should stand on their own without a call to action.
- Opportunity items should describe why the window may matter, not instruct Mike to act.
- Action-required items should be rare, ideally 0-3 per day.
- The appendix can show calculations, scores, evidence, and source details.

## Consequences

The homepage can inform Mike without making him feel behind.

The attention engine now optimizes for confidence and useful context, not task generation.
