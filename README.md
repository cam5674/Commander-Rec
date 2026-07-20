# MTG Commander Recommender

## Short Description

MTG Commander Recommender is a serverless web application that helps Magic: The Gathering players find commanders that fit the cards they already own.

Users upload a card collection, and the app analyzes the collection for Commander-relevant themes such as wheels, tokens, graveyard recursion, artifacts, spellslinger, lifegain, aristocrats, and +1/+1 counters. It then recommends commanders that match those themes and explains why each commander was selected.

Example: if a user owns many wheel effects and card-draw payoffs, the app may recommend commanders such as The Locust God because those cards support a wheel-based strategy.

## Project Goals

1. Learn AWS by building and deploying a serverless application.
2. Keep expected AWS costs under $10-$20 per month during development.
3. Support large user collections, roughly 10,000-20,000 cards.
4. Build a recommendation engine that is understandable, testable, and explainable.


## MVP Scope

The first version should stay focused on the core recommendation workflow:

1. Accept a CSV upload containing a user's card collection.
2. Normalize uploaded card names against processed Scryfall data.
3. Detect strategic themes present in the collection.
4. Score commanders based on theme match, color identity, and owned support cards.
5. Return the top commander recommendations with short explanations.
6. Discard the uploaded collection after the request completes.

The MVP should not require user accounts or permanent storage of user collections.

## Tech Stack

- Python
- FastAPI
- Mangum for running FastAPI on AWS Lambda
- AWS Lambda
- API Gateway
- S3
- DynamoDB
- Scryfall bulk data
- GitHub

## Architecture

Initial MVP architecture:

```text
Static frontend on S3
        |
        v
API Gateway
        |
        v
AWS Lambda running FastAPI via Mangum
        |
        v
Recommendation engine
        |
        v
JSON response with commander recommendations
```

The Lambda function should use cached reference data, not cached user data.

Reference data includes:

- processed Scryfall card lookup
- commander metadata
- theme tags
- precomputed commander/theme indexes

User-uploaded collections should be treated as temporary request data for the MVP.

## Data Pipeline

1. Download Scryfall bulk data locally or through a scheduled script.
2. Process the bulk data into smaller lookup files needed by the recommender.
3. Generate commander metadata, card lookup data, and theme indexes.
4. Store the processed reference data in the repository, Lambda package, or S3 depending on file size.
5. Load reference data once per Lambda cold start and reuse it from memory when possible.
6. Parse each uploaded collection during the request.
7. Score commanders and return recommendations.

Avoid downloading a large processed card database from S3 on every request. That would add latency and make performance harder to control.

### Processed Scryfall Outputs

Run the local data pipeline from the repository root:

```text
python scripts/download_scryfall.py
python scripts/process_scryfall.py
```

The processing script generates compact reference files in `data/processed`:

- `cards_by_id.json`: one normalized card record per Oracle ID
- `name_to_id.json`: case-insensitive card and card-face name lookup
- `commanders.json`: Oracle IDs for commander-eligible cards
- `theme_to_card_ids.json`: reverse index from theme tags to Oracle IDs

## Recommendation Strategy

The recommendation engine should start with a simple, explainable scoring model:

1. Identify cards in the user's collection.
2. Assign theme tags to recognized cards.
3. Count theme density across the collection.
4. Compare the user's strongest themes against commander theme profiles.
5. Filter or penalize commanders whose color identity does not fit enough owned cards.
6. Score commanders based on theme overlap and number of owned support cards.
7. Return explanations showing which owned cards contributed to the recommendation.

Example explanation:

> Recommended The Locust God because your collection contains multiple wheel effects, card-draw payoffs, and token support cards.

## Planned Features

### MVP Features

- CSV collection upload
- Scryfall-based card name normalization
- Theme classification
- Commander recommendation scoring
- Recommendation explanations
- Basic static frontend
- Serverless API deployment

### Stretch Features

- Save previous uploads
- User accounts
- DynamoDB-backed recommendation history
- Async processing for very large uploads
- Automated weekly Scryfall data refresh
- Commander detail pages
- Deck-building suggestions for missing support cards

## Cost and Performance Targets

- Keep AWS development costs under $10-$20 per month.
- Return recommendations for a 10,000-20,000 card collection within a few seconds.
- Minimize repeated S3 reads inside request handling.
- Prefer preprocessed, compact reference data over large raw JSON files.

## Development Notes

- Use Scryfall bulk data instead of calling the Scryfall API for every uploaded card.
- Keep the first recommendation model rule-based and explainable.
- Add tests around card normalization, theme detection, and commander scoring.
