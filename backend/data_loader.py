"""Purpose of file: Load and validate processed reference data only"""

import json
import logging
import os
from functools import cache
from pathlib import Path
from time import perf_counter
from typing import Any


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"


def resolve_processed_data_dir(configured_dir: str | None = None) -> Path:
    raw_path = configured_dir
    if raw_path is None:
        raw_path = os.getenv("REFERENCE_DATA_DIR")

    if not raw_path:
        return DEFAULT_PROCESSED_DATA_DIR

    path = Path(raw_path)
    return path if path.is_absolute() else PROJECT_ROOT / path


PROCESSED_DATA_DIR = resolve_processed_data_dir()

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


def load_name_to_id(path: Path = NAME_TO_ID_PATH) -> dict[str, str]:
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
def _get_cards_by_id_cached() -> dict[str, dict[str, Any]]:
    return load_cards_by_id()


@cache
def _get_name_to_id_cached() -> dict[str, str]:
    return load_name_to_id()


@cache
def _get_commanders_cached() -> list[str]:
    data = load_json(COMMANDERS_PATH)

    if not isinstance(data, list) or not all(
        isinstance(oracle_id, str) for oracle_id in data
    ):
        raise RuntimeError(
            f"Expected a JSON array of Oracle IDs in {COMMANDERS_PATH}."
        )

    return data


@cache
def _get_theme_to_card_ids_cached() -> dict[str, list[str]]:
    data = load_json(THEME_TO_CARD_IDS_PATH)

    if not isinstance(data, dict):
        raise RuntimeError(
            f"Expected a JSON object in {THEME_TO_CARD_IDS_PATH}."
        )

    return data


def _log_reference_access(
    dataset: str,
    cache_hit: bool,
    started_at: float,
) -> None:
    LOGGER.info(
        "reference_data_access dataset=%s cache=%s duration_ms=%.2f",
        dataset,
        "hit" if cache_hit else "miss",
        (perf_counter() - started_at) * 1000,
    )


def get_cards_by_id() -> dict[str, dict[str, Any]]:
    cache_hit = _get_cards_by_id_cached.cache_info().currsize > 0
    started_at = perf_counter()
    data = _get_cards_by_id_cached()
    _log_reference_access("cards_by_id", cache_hit, started_at)
    return data


def get_name_to_id() -> dict[str, str]:
    cache_hit = _get_name_to_id_cached.cache_info().currsize > 0
    started_at = perf_counter()
    data = _get_name_to_id_cached()
    _log_reference_access("name_to_id", cache_hit, started_at)
    return data


def get_commanders() -> list[str]:
    cache_hit = _get_commanders_cached.cache_info().currsize > 0
    started_at = perf_counter()
    data = _get_commanders_cached()
    _log_reference_access("commanders", cache_hit, started_at)
    return data


def get_theme_to_card_ids() -> dict[str, list[str]]:
    cache_hit = _get_theme_to_card_ids_cached.cache_info().currsize > 0
    started_at = perf_counter()
    data = _get_theme_to_card_ids_cached()
    _log_reference_access("theme_to_card_ids", cache_hit, started_at)
    return data


def clear_reference_data_caches() -> None:
    _get_cards_by_id_cached.cache_clear()
    _get_name_to_id_cached.cache_clear()
    _get_commanders_cached.cache_clear()
    _get_theme_to_card_ids_cached.cache_clear()
