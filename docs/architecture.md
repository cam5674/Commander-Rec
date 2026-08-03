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
    D --> R[data/raw/oracle_cards.json]
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

## Reference-Data Pipeline

Run the pipeline from the repository root:

```powershell
python scripts/download_scryfall.py
python scripts/process_scryfall.py
```

### Download

`scripts/download_scryfall.py` retrieves Scryfall bulk-data metadata, selects
the `oracle_cards` download, and streams it to
`data/raw/oracle_cards.json`. The download is first written to a temporary
`.part` file so an interrupted request does not replace a valid dataset.

### Processing

`scripts/process_scryfall.py` reads the raw cards and:

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
3. Measures owned-card color compatibility.
4. Builds candidates from all eligible commanders, not only owned cards.
5. Excludes commanders requiring partners or backgrounds for the MVP.
6. Scores candidates using theme fit, color compatibility, and EDHREC rank.
7. Marks whether each recommended commander is owned.
8. Adds matching themes and highly ranked supporting owned cards.
9. Sorts candidates and returns the requested top results.

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
