from backend.csv_parser import parse_collection
from collections import defaultdict
from pathlib import Path
from typing import Any
from .data_loader import load_name_to_id, load_cards_by_id

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "raw" / "test_collection.csv"


def calculate_theme_scores(
    collection: dict[str, int],
    cards_by_id: dict[str, dict[str, Any]],
    ) -> dict[str, int]:

    scores = defaultdict(int)


    for oracle_id in collection:
        card = cards_by_id.get(oracle_id)

        if card is None:
            continue

        for theme in card.get("themes", []):
            scores[theme] += 1


    return dict(scores)



def main()-> None:
    name_to_id = load_name_to_id()
    cards_by_id = load_cards_by_id()

    collection, _unmatched = parse_collection(CSV_PATH, name_to_id)

    theme_scores = calculate_theme_scores(collection, cards_by_id)

    print(theme_scores)




if __name__ == "__main__":
    main()
