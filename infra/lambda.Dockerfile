FROM public.ecr.aws/sam/build-python3.12:latest-arm64

WORKDIR /build

COPY requirements-lambda.txt .
RUN python -m pip install --no-cache-dir -r requirements-lambda.txt --target /asset

RUN mkdir -p /asset/backend /asset/scripts /asset/data/processed
COPY backend/__init__.py backend/api.py backend/csv_parser.py backend/data_loader.py backend/lambda_handler.py backend/models.py backend/theme_scorer.py /asset/backend/
COPY scripts/process_scryfall.py /asset/scripts/
COPY data/processed/cards_by_id.json data/processed/commanders.json data/processed/name_to_id.json data/processed/theme_to_card_ids.json /asset/data/processed/
