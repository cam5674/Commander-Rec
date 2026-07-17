# MTG Commander Recommender

## Short description

Commander recommendation app that allows users to upload their collection and find a commander that matches the cards they already own. For example, you have a lot of wheel cards and big flashy card-draw, then the card recommendation app will suggest The Locust God or other commanders that use a wheel strategy. 

## Goals

1. Learn AWS by building a serverless application.
2. Keep it under $10-$20 
3. Allow users to upload their whole collection and still give them quick results - 10-20k items


## Tech Stack

- Python
- FastAPI
- AWS Lambda
- API Gateway
- S3
- DynamoDB
- Scryfall API
- GitHub

## Architecture

Frontend (S3 static website) -> API gateway -> Lambda -> S3 (processed card db) -> Recommendation Engine -> Send recommendations back to user

## Data Pipeline

1. Download Scryfall bulk data locally - to save costs. Possibly update it every week 
2. Process it into a smaller lookup JSON
3. Upload the process JSON to S3
4. Lambda downloads/reads the process lookup
5. Users upload a collection
6. Lambda classifies themes and recommends commanders







## Planned Features

- CSV upload
- Theme classification
- Card recommendation engine
- Recommendation explanations
- Save previous uploads
- User accounts (stretch goal)
- Weekly script to download Scryfall data locally - can use one version to compress the file size

