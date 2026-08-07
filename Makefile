build-ApiFunction:
	python -m pip install -r requirements-lambda.txt --target "$(ARTIFACTS_DIR)"
	mkdir -p "$(ARTIFACTS_DIR)/backend"
	cp backend/__init__.py backend/api.py backend/csv_parser.py backend/data_loader.py backend/lambda_handler.py backend/models.py backend/theme_scorer.py "$(ARTIFACTS_DIR)/backend/"
	mkdir -p "$(ARTIFACTS_DIR)/scripts"
	cp scripts/process_scryfall.py "$(ARTIFACTS_DIR)/scripts/"
	mkdir -p "$(ARTIFACTS_DIR)/data/processed"
	cp data/processed/cards_by_id.json data/processed/commanders.json data/processed/name_to_id.json data/processed/theme_to_card_ids.json "$(ARTIFACTS_DIR)/data/processed/"
