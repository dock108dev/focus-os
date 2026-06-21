# ADR 0014: Product voice and appendix design

## Status

Accepted.

## Context

Generated briefing copy started sounding like a generic assistant:

- "Mike should care because..."
- "Review whether..."
- "Consider whether..."
- repetitive fact / rationale / action structure

That voice makes FocusOS feel like an AI-generated dashboard instead of a product with an opinion.

The appendix also exposed implementation records such as provider, source type, parsed title, and parsed action too prominently.

## Decision

FocusOS should write like an editor:

- Never say "Mike should care because."
- Do not explain that the user should care.
- Do not use generic action text unless action is genuinely warranted.
- Keep action payload fields empty unless a concrete immediate action is genuinely warranted.
- Let simple informational items stand on their own.
- Vary rhythm across items: some can be one sentence, some can include brief context, and only rare items should imply action.

The appendix should read like research support:

- Headline
- Summary
- Sources
- Supporting facts
- Details collapsed by default

Implementation details such as prompts, parsed fields, raw payloads, scores, and hidden items belong inside collapsed Details.

## Consequences

Briefing copy should feel less like ChatGPT output and more like a concise editorial product.

Existing generated text is cleaned at serialization/render time, and future AI prompts explicitly ban the patronizing phrasing.
