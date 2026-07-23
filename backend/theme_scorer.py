from backend.csv_parser import parse_collection
from collections import defaultdict
from pathlib import Path
from typing import Any
from .data_loader import load_name_to_id, load_cards_by_id
from scripts.process_scryfall import THEME_RULES

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "raw" / "test_collection.csv"



def print_theme_matches(
    collection: dict[str, int],
    cards_by_id: dict[str, dict],
    theme: str,
    limit: int = 20,
) -> None:
    matches = []

    for oracle_id in collection:
        card = cards_by_id.get(oracle_id)

        if card is None or theme not in card.get("themes", []):
            continue

        searchable_text = " ".join((
            card.get("type_line", ""),
            card.get("oracle_text", ""),
            *card.get("keywords", []),
        )).casefold()

        matched_triggers = [
            trigger
            for trigger in THEME_RULES[theme]
            if trigger in searchable_text
        ]

        matches.append((card["name"], matched_triggers))

    for name, triggers in sorted(matches)[:limit]:
        print(f"{name}: {', '.join(triggers)}")




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


def get_commanders(
        collection: dict[str, int], 
        cards_by_id: dict[str, dict[str, Any]],
        top_themes: list,
        ) ->dict[str, int]:


    for oracle_id in collection:
        card = cards_by_id.get(oracle_id)

        if card is None or card.get("commander_eligible") is False:
            continue

        else:
            if any(item in top_themes for item in card.get("themes")) and card.get("edhrec_rank") < 15000:
                print(f'Name: {card.get("name")} Themes: {card.get("themes")}')
            

        
    


def main()-> None:
    name_to_id = load_name_to_id()
    cards_by_id = load_cards_by_id()

    collection, _unmatched = parse_collection(CSV_PATH, name_to_id)

    theme_scores = calculate_theme_scores(collection, cards_by_id)

    print(theme_scores)

    # add this to the calculate function?
    top_5_themes = sorted(theme_scores, key=theme_scores.get, reverse=True)[:5]
    print(top_5_themes)


    print_theme_matches(
    collection,
    cards_by_id,
    theme="aristocrats",
    limit=20,
)

    get_commanders(collection, cards_by_id, top_5_themes)


if __name__ == "__main__":
    main()
