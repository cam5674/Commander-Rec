# Architecture

This document describes the implemented data-processing and recommendation
pipelines for the MTG Commander Recommender MVP.

## System Overview

The project has two distinct workflows:

1. A local reference-data pipeline downloads and normalizes Scryfall data.
2. A request pipeline parses an uploaded collection and returns recommendations.

```mermaid
flowchart LR
    S[Scryfall Oracle Cards] --> D[download_scryfall.py]
    D --> R[data/raw/oracle_cards.jsonl.gz]
    R --> P[process_scryfall.py]
    P --> J[data/processed JSON files]
    J --> L[data_loader.py cache]

    F[Frontend CSV upload] --> A[FastAPI /recommendations]
    A --> C[csv_parser.py]
    C --> T[theme_scorer.py]
    L --> C
    L --> T
    T --> M[Pydantic response models]
    M --> F
```

This diagram describes the implemented application flow independently of its
hosting environment. The repository currently runs FastAPI/Uvicorn and Vite
locally, reads reference JSON from `data/processed`, and uses localhost API and
CORS settings. The S3, API Gateway, Lambda, and Mangum topology in the README is
the target deployment architecture; its adapter, infrastructure configuration,
production origins, and S3-backed reference-data loading are not implemented
in this repository yet.

## Reference-Data Pipeline

Run the pipeline from the repository root:

```powershell
python scripts/download_scryfall.py
python scripts/process_scryfall.py
```

### Download

`scripts/download_scryfall.py` retrieves Scryfall bulk-data metadata, selects
the compressed `oracle_cards` JSONL download, and streams it to
`data/raw/oracle_cards.jsonl.gz`. The download is first written to a
temporary `.part` file so an interrupted request does not replace a valid
dataset.

### Processing

`scripts/process_scryfall.py` reads the gzip-compressed JSONL one card at a
time and:

- skips cards that are unavailable in paper
- keeps the fields required by the recommendation engine
- normalizes names for case-insensitive lookup
- adds names and aliases for multiface cards
- determines Commander eligibility
- classifies cards using the local theme rules
- preserves color identity, image URL, and EDHREC rank

The script writes these files to `data/processed`:

| File | Purpose |
| --- | --- |
| `cards_by_id.json` | Normalized card records keyed by Oracle ID |
| `name_to_id.json` | Normalized card and face names mapped to Oracle IDs |
| `commanders.json` | Oracle IDs for Commander-eligible cards |
| `theme_to_card_ids.json` | Reverse index of themes to matching Oracle IDs |

Oracle IDs are the stable internal identifiers used across parsing, scoring,
and API responses.

### Theme Classification

`scripts/process_scryfall.py` classifies cards using three independent
evidence sources: type line, Oracle text, and Scryfall keywords. Parenthetical
reminder text is removed before Oracle-text matching, and matching is scoped
to individual clauses so unrelated abilities cannot combine into one signal.

Theme rules distinguish mechanics a card provides from mechanics it rewards.
For example, a repeatable sacrifice outlet informs Sacrifice, while a death or
sacrifice payoff informs Aristocrats. A card receives both tags only when it
independently supports both roles.

Creating a token informs Tokens, but the token's permanent types do not
automatically add other themes:

| Token | Theme(s) | Rationale |
| --- | --- | --- |
| Food | Tokens, Lifegain | Food's defined payoff is life gain |
| Clue | Tokens | Its reminder-text draw ability is ignored without independent draw text |
| Treasure | Tokens | Ramp and mana fixing are not current themes |

Generic Artifact cards still receive Artifacts from their type line. This
preserves artifact-density strategies alongside cards with explicit artifact
synergy.

Regression fixtures in `tests/test_normalization.py` define the expected
classification behavior. After changing theme rules, regenerate the processed
JSON files and restart the backend so its cached reference data is refreshed.

### Eligibility and Result Size

A candidate must clear a raw theme-match threshold to be eligible for
recommendation at all:

```text
theme_ratio = matched top-theme score / total top-five theme score
```

Candidates below `theme_ratio >= 0.60` are excluded before color compatibility
and final-score calculation (see Performance below). This threshold is
evaluated against the *raw* ratio, not the Laplace-smoothed one used for
scoring and display (see Confidence-Adjusted Fit): eligibility asks whether a
candidate is a genuine textual match; the smoothed score reflects confidence
in that match.

The endpoint returns up to 20 eligible candidates, sorted by final score.
A collection with weak or scattered theme signal may legitimately return
fewer than 20, or zero — this is expected behavior, not an error.

### Confidence-Adjusted Fit

Theme and color fit use symmetric Laplace smoothing so very small collections
cannot produce perfect scores from only one or two supporting cards:

```text
adjusted ratio = (matches + 1) / (total + 2)
```

The raw theme ratio still determines eligibility at the 60% threshold; the
smoothed ratio affects scoring and display confidence only. As evidence grows,
the adjustment approaches the raw ratio. Small-evidence behavior is covered in
`tests/test_theme_scorer.py`.

### Performance

Color-compatibility scoring (`calculate_color_compatibility_ratio()`) scans
every unique card in the collection and is the most expensive operation per
candidate. It runs only for candidates that have already cleared the raw
60% theme-eligibility gate above, not for the full theme-matching candidate
pool. This ordering matters: profiling a 20,000-row collection found 1,806
theme-matching candidates, of which only 25 passed eligibility, so scoring
color compatibility before filtering meant performing roughly 1,781
unnecessary full-collection scans per request.

Supporting-card evidence is sorted and limited to the retained set (5 per
theme) before constructing Scryfall URLs for the response, rather than
building URLs for every matching card and discarding most of them.

Measured effect on the 20,000-row fixture (warm, in-process): median request
time dropped from 10.50s to 0.573s. Response bodies remained byte-identical
(SHA-256) for seeds 101, 202, 303, and 404 and the showcase collection. No
aggregate or reusable supporting-evidence indexes were introduced; those are
the next code-level optimization targets if the collection or commander pool
grows. Lambda memory and timeout settings should be evaluated later with
deployed benchmarks.

## Request Pipeline

### 1. Upload Validation

The frontend sends a CSV as the `upload` field of a multipart request:

```text
POST /recommendations
```

`backend/api.py`:

- limits the upload to 5 MB
- limits parsing to 20,000 data rows
- exposes the enforced limits through `GET /config`
- rejects collections with no recognized cards
- converts all client errors into one structured response shape
- validates successful responses with Pydantic models

Uploads are held in memory for the request and are not stored permanently.

### 2. CSV Parsing

`backend/csv_parser.py` accepts bytes, streams, or filesystem paths. It:

- recognizes common card-name and quantity column aliases
- handles UTF-8 BOM files
- normalizes names and resolves them through `name_to_id.json`
- combines duplicate rows under the same Oracle ID
- records unmatched names
- returns structured warnings for invalid rows

The parsed collection is represented as quantities keyed by Oracle ID:

```python
{
    "oracle-id-123": 4,
    "oracle-id-456": 1,
}
```

Quantities are retained for collection reporting, while theme and color
analysis evaluates unique owned cards because Commander is a singleton format.

### 3. Reference-Data Loading

`backend/data_loader.py` loads the processed JSON files and caches them in
memory. The API reuses this immutable reference data between requests when the
process remains warm. User collection data is never placed in these caches.

### 4. Recommendation Scoring

`backend/theme_scorer.py`:

1. Calculates theme scores for the recognized collection.
2. Selects the collection's strongest themes.
3. Builds candidates from all Commander-eligible reference cards that match at
   least one strongest theme, not only owned cards; commanders requiring a
   partner or background are excluded, and ownership is recorded.
4. Applies the raw 60% theme-eligibility gate (see Eligibility and Result
   Size) before the more expensive color-compatibility calculation.
5. Scores eligible candidates using smoothed theme fit, smoothed owned-card
   color compatibility, and EDHREC rank.
6. Sorts candidates deterministically and retains up to 20 results.
7. Adds ranked supporting owned cards for each matching theme.

Theme fit has more influence than color compatibility. EDHREC rank is a
smaller popularity signal and a later tie-breaker rather than the primary
recommendation factor.

## API Response

`backend/models.py` defines the frontend-facing response contract. A successful
response includes:

- unique-card and total-card counts
- all detected theme scores and the strongest themes
- commander recommendations
- commander image URLs, Scryfall identity links, and ownership status
- matching themes and supporting owned cards with image and Scryfall metadata
- theme, color, popularity, and final score components
- unmatched card names and structured CSV warnings

The backend returns explanation data rather than presentation text. The
frontend should turn the score breakdown, matching themes, and supporting cards
into readable recommendation explanations.

## Module Responsibilities

| Module | Responsibility |
| --- | --- |
| `backend/api.py` | HTTP boundary, upload validation, and response assembly |
| `backend/csv_parser.py` | CSV format handling and collection normalization |
| `backend/data_loader.py` | Validated, cached reference-data loading |
| `backend/theme_scorer.py` | Collection analysis and commander ranking |
| `backend/models.py` | Stable API response schemas |
| `scripts/download_scryfall.py` | Scryfall Oracle Cards download |
| `scripts/process_scryfall.py` | Reference-data normalization and indexing |

## MVP Boundaries

- No user accounts or persistent collection storage
- No partner or background pair recommendations
- No live Scryfall lookup during an upload request
- No machine-learning recommendation model
- No automatic Scryfall refresh

These constraints keep the recommendation path deterministic, explainable, and
testable. Partner pairing, automated data refresh, deployment packaging, and
persistent user features can be added after the MVP.
