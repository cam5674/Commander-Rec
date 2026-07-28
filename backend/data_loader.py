"""Purpose of file: Load and validate processed reference data only"""

import json
from pathlib import Path
from typing import Any
from functools import cache



PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

NAME_TO_ID_PATH = PROCESSED_DATA_DIR / "name_to_id.json"
CARDS_BY_ID_PATH = PROCESSED_DATA_DIR / "cards_by_id.json"
COMMANDERS_PATH = PROCESSED_DATA_DIR / "commanders.json"
THEME_TO_CARD_IDS_PATH = PROCESSED_DATA_DIR / "theme_to_card_ids.json"





def load_json(path: Path) -> object:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as error:
        raise RuntimeError(f"Could not find file: {path}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Invalid JSON in file: {path}") from error



def load_name_to_id(path: Path= NAME_TO_ID_PATH) -> dict[str, str]:
    data = load_json(path)
    if not isinstance(data, dict):
        raise RuntimeError(f"Expected a JSON object in {path}.")

    return data

def load_cards_by_id(
    path: Path = CARDS_BY_ID_PATH,
) -> dict[str, dict[str, Any]]:
    data = load_json(path)

    if not isinstance(data, dict):
        raise RuntimeError(f"Expected a JSON object in {path}.")

    return data


@cache
def get_cards_by_id() -> dict[str, dict[str, Any]]:
    return load_cards_by_id()


@cache
def get_name_to_id() -> dict[str, str]:
    return load_name_to_id()


@cache
def get_commanders() -> list[str]:
    data = load_json(COMMANDERS_PATH)

    if not isinstance(data, list) or not all(
        isinstance(oracle_id, str) for oracle_id in data
    ):
        raise RuntimeError(
            f"Expected a JSON array of Oracle IDs in {COMMANDERS_PATH}."
        )

    return data


@cache
def get_theme_to_card_ids() -> dict[str, list[str]]:
    data = load_json(THEME_TO_CARD_IDS_PATH)

    if not isinstance(data, dict):
        raise RuntimeError(
            f"Expected a JSON object in {THEME_TO_CARD_IDS_PATH}."
        )

    return data