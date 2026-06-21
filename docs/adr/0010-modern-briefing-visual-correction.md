# ADR 0010: Modern briefing visual correction

## Status

Accepted.

## Context

ADR 0009 moved FocusOS toward a private morning briefing packet, but the first visual execution became too literal: heavy newspaper styling, warm archive colors, thick borders, large serif stacks, and visible implementation language.

The product should feel like a premium personal briefing for iPad reading, not a vintage newspaper replica or developer console.

## Decision

Supersede the literal newspaper execution from ADR 0009 with a modern briefing memo direction.

Visual rules:

- Use the Dark Ink palette: `#F7F7F4` background, `#FCFCFA` surfaces, `#111827` text, `#1E3A5F` accent, and `#4B5563` muted text.
- Use serif typography only for the page title and briefing item headlines.
- Use sans-serif typography for body copy, metadata, actions, tables, and detail text.
- Cut header height roughly in half from the first visual pass.
- Replace thick borders and boxed newspaper grids with thin dividers, quiet shadows, and softer section separation.
- Avoid green, burgundy, brown, tan, archive, and government filing-cabinet color cues.
- Use product language in the UI: `Evidence`, `Underlying data`, `Methodology`, and `Items not shown`.
- Hide raw payloads behind collapsed panels by default.
- Show readable tables and source links before raw payloads on evidence pages.

Responsive rules:

- Mobile uses a single-column briefing feed.
- Tablet uses a two-pane layout with the primary brief on the left and quiet portfolio or topic context on the right.
- Desktop remains a centered reading experience instead of becoming a full-width SaaS dashboard.

## Consequences

The app should feel closer to Apple News, Kindle, Financial Times, and a private intelligence memo than a themed dashboard.

Auditability remains, but the primary UI no longer exposes developer framing such as source packets, raw JSON, AI processing, or suppressed signals.
