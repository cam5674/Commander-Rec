"""Purpose of file: Load and validate processed reference data only"""
import json
from pathlib import Path



PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

NAME_TO_ID_PATH = PROCESSED_DATA_DIR / "name_to_id.json"
CARDS_BY_ID_PATH = PROCESSED_DATA_DIR / "cards_by_id.json"





def load_json(path: Path) -> dict:
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

def load_cards_by_id(path: Path = CARDS_BY_ID_PATH)-> dict[str, object]:
    data = load_json(path)

    if not isinstance(data, dict):
        raise RuntimeError(f"Expected a JSON object in {path}.")

    return data
