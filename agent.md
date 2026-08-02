# Agent Instructions — MTG Commander Recommender (Frontend)

You are the frontend designer/developer for this application. Read this file
in full before starting any task. It reflects decisions made across multiple
prior sessions — treat it as authoritative context, not a suggestion.

## Project Overview

MTG Commander Recommender is a serverless web app that helps Magic: The
Gathering players find Commander decks that fit cards they already own.
Users upload a CSV of their collection; the backend detects strategic
themes (wheels, tokens, graveyard recursion, artifacts, spellslinger,
lifegain, aristocrats, +1/+1 counters) and returns the top 5 commander
recommendations with explanations.

Tech stack: Python, FastAPI (+ Mangum on Lambda), API Gateway, S3,
DynamoDB (unused in MVP), Scryfall bulk data. Frontend: static, deployed
to S3, styled with Tailwind.

Read `README.md` and `docs/architecture.md` before making changes if you
haven't already reviewed them this session — they define the API contract,
error shapes, and backend module responsibilities.

## Scope Boundaries

- You only touch files in `/frontend`.
- You may read the backend to understand data models and API endpoints,
  but you may not edit backend files.
- If a backend change seems necessary, stop and describe it in your report
  — do not create workarounds, mock endpoints, or shims to compensate.
- Do not add or remove dependencies without asking first.
- Do not introduce new components, pages, or structural changes during a
  styling/polish/UX pass — flag structural gaps in your report instead of
  fixing them inline.
- Do not hardcode colors, spacing, font sizes, or arbitrary Tailwind
  bracket values — use the token system defined in `tailwind.config`. If a
  needed value doesn't exist yet, flag it rather than inventing one.

## Workflow Norms

- **Always propose a plan and wait for explicit approval before writing
  code**, unless a prompt explicitly says otherwise. Do not treat "report
  and I'll approve" as license to continue implementing — stop fully and
  wait for a reply.
- For multi-part work, proceed in the specified order and pause for review
  after each group/section rather than completing everything at once.
- For bug reports: investigate and report your diagnosis before fixing,
  especially when a bug could be systemic (e.g. affecting a shared
  component/token) rather than isolated to one instance. Fix systemic
  issues once at the shared level, not via per-instance patches.
- When reporting, be concrete: what changed, what was flagged instead of
  fixed, and how I can view the result.

## Design System

**Theme:** Dark mode is the default and primary experience. Card art is
highly saturated and varied — UI chrome stays neutral so it never competes
with card images.

- Background: near-black/charcoal (not pure black)
- Surfaces/panels: one or two steps lighter than background, for layering
- Text: off-white primary, mid-gray secondary/muted
- Borders/dividers: subtle, low-contrast

**Accent colors (WUBRG):** Mapped to Magic's own color-identity system —
White, Blue, Black, Red, Green, Colorless, Multicolor/gold. Used **only**
for functional/meaningful UI: color-identity badges/pips, filter chips,
color-based grouping. Never used for primary buttons, links, or generic
actions — those use one separate neutral accent (e.g. gold/bronze), kept
visually distinct from mana-color meaning.

All tokens are defined in `tailwind.config`, not inline.

**Typography:** Clean sans-serif for all UI/body/list text (legibility at
small sizes matters — deck lists and mana costs are dense). Optional
display/serif for major headers or the logo only — never extended to body
text.

**Spacing:** Tailwind's default scale unless there's a specific reason to
extend it. Card grids preserve the true Magic card aspect ratio (2.5:3.5)
at all sizes.

**Accessibility baseline:** WCAG AA contrast for all text/background
pairs, including text over card art (use a scrim/gradient as needed).
Respect `prefers-reduced-motion` for all transitions.

## Page & Component Structure

**Upload page:** drag-drop/picker CSV upload (references `GET /config` for
client-side limits), loading state, distinct error states per error code
(400/413/422, using the structured `{code, message, unmatched_names,
warnings}` response shape).

**Results page:**
- Collection summary (counts, strongest themes) — collapsible, low visual
  priority.
- Warnings/unmatched card names — collapsed by default, but should carry
  more visual weight if a large fraction of the collection is unmatched
  (don't treat this as universally low-priority).
- Recommendation list: 5 ranked commander cards.

**CommanderCard — the focal component of the app.** Two states:

*Collapsed (default, always visible):*
- Commander image (large — art matters) and name — primary focal point
- Ownership badge, theme tags, human-readable explanation sentence —
  clearly secondary to image/name
- Color identity indicator is **not** shown here (moved to expanded state)

*Expanded (toggle):*
- Supporting owned cards, score breakdown, color identity indicator
- Should read as "drilled-in detail" — de-emphasized relative to collapsed
  state even when open

The explanation sentence is assembled by the frontend from structured
theme/score/supporting-card data — the backend returns data, not prose.

## Established Interaction Patterns

**Card image zoom (full-size view):**
- The card image itself is the zoom target, separate from the rest of the
  card (which handles expand/collapse).
- Desktop: hovering the image shows a full-size overlay.
- Touch: a persistent small zoom icon overlaid on the image (since there's
  no hover) — visible always on touch, hover-revealed on desktop.
- Overlay repositions to stay fully on-screen near grid edges; dismiss on
  mouse-leave (desktop) or tap-outside/close control (touch).

**Expand signal:** hovering/tapping anywhere on the card *other than the
image* signals it's expandable (elevation/border highlight) — distinct
from the zoom interaction above.

**Interactive elements generally:** must have visible hover and
active/pressed states (cursor change, visual feedback on click) — this has
been a recurring bug (buttons firing correctly but with no visual
feedback). When fixing, check whether the shared token-level hover/active
styles are actually being inherited before patching individual instances.

**Theme badges:** use domain jargon (wheels, aristocrats, spellslinger) —
consider hover tooltips with plain-language definitions for newer players.

## Backend Constraints Relevant to Frontend

- `GET /config` returns current upload limits — do not hardcode limits in
  the frontend, fetch them.
- **Known issue:** the documented 5 MB upload limit is likely too high for
  a synchronous Lambda invocation behind API Gateway (base64 encoding
  inflates payload ~33%, and Lambda's sync payload cap is ~6 MiB) — if
  asked to change this, prefer aligning the frontend's client-side
  validation to whatever limit `/config` actually returns rather than
  assuming 5 MB is final.
- All backend errors use one structure:
  `{ "detail": { "code", "message", "unmatched_names", "warnings" } }`.
- User-uploaded collections are never persisted — don't build any frontend
  assumption of saved/returnable uploads.

## Model Selection Notes (for whoever is prompting)

- Default to Sonnet for structural planning, implementation, and bounded
  bug fixes.
- Escalate to Opus for broad evaluative work — UX/consistency audits,
  reconciling implementation against accumulated context, judgment-heavy
  review — then hand concrete findings back to Sonnet for implementation.

## Open Items / Suggested Next Steps

Roughly in this order, as of the last session:
1. Responsive/mobile layout pass (grid behavior, touch target sizes,
   summary/warnings stacking) — not yet done as its own pass.
2. Accessibility audit (keyboard-only flow, screen reader labels/alt text,
   color-blind-safe treatment of WUBRG badges — color should never be the
   only signal).
3. Real-data QA pass against the live local backend, using constructed
   test CSVs (happy path, weak/no theme signal, large ~20k-row collection,
   heavy unmatched names, tiny collection, empty/invalid file).

After these, remaining work shifts from frontend design to
deployment/integration (S3 + CloudFront, CORS, live API wiring).
