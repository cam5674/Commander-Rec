#TODO: implement color-identity compatibility (can see the most common color pairings in the collection)



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


def get_commander_candidates(
        collection: dict[str, int],
        cards_by_id: dict[str, dict[str, Any]],
        top_themes: list,
        ) -> list [dict[str, Any]]:

    candidates = []

    for oracle_id in collection:
        card = cards_by_id.get(oracle_id)

        if card is None or not card.get("commander_eligible", False):
            continue

        matching_themes = set(card.get("themes", [])) & set(top_themes)

        if not matching_themes:
            continue

        candidates.append(
            {
                "oracle_id": oracle_id,
                "name": card["name"],
                "themes": card.get("themes", []),
                "matching_themes": sorted(matching_themes),
                "edhrec_rank": card.get("edhrec_rank"),
            }

        )

    return candidates


def rank_commanders(
        candidates: list[dict[str, Any]],
        theme_scores: dict[str, int],
        top_n: int = 5,
        ) -> list[dict[str, Any]]:


        ranked_commanders = []

        for candidate in candidates:

            theme_match_score = 0

            for theme in candidate["matching_themes"]:
                theme_match_score += theme_scores.get(theme, 0)

            edhrec_rank = candidate["edhrec_rank"]


            # experiment with rank(15000)
            popularity_score = (
                max(0, 15000 - edhrec_rank) / 15000
                if edhrec_rank is not None else
                0
            )

            final_score = theme_match_score + popularity_score


            ranked_commanders.append(
                {
                    **candidate,
                    "theme_match_score": theme_match_score,
                    "popularity_score": popularity_score,
                    "final_score": final_score
                }
            )

        ranked_commanders.sort(
                key=lambda commander: (
                    -commander["final_score"],
                    commander["edhrec_rank"] or float("inf"),
                    commander["name"],
                            )
        )

        return ranked_commanders[:top_n]


def main()-> None:
    name_to_id = load_name_to_id()
    cards_by_id = load_cards_by_id()

    collection, unmatched = parse_collection(CSV_PATH, name_to_id)

    theme_scores = calculate_theme_scores(collection, cards_by_id)


    # add this to the calculate function?
    top_5_themes = sorted(theme_scores, key=theme_scores.get, reverse=True)[:5]

   # print_theme_matches(
   # collection,
   # cards_by_id,
   # theme="aristocrats",
   # limit=20,
#)

    candidates = get_commander_candidates(collection, cards_by_id, top_5_themes)

    top_n = rank_commanders(candidates, theme_scores, 10)
    print(top_n)

    for dict in top_n:
        for key, value in dict.items():
            print(f"{key}: {value}")

if __name__ == "__main__":
    main()
