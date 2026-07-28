#TODO: implement color-identity compatibility (can see the most common color pairings in the collection)


from pprint import pprint
from backend.csv_parser import parse_collection
from collections import defaultdict
from pathlib import Path
from typing import Any
from .data_loader import get_cards_by_id, get_name_to_id
from scripts.process_scryfall import THEME_RULES

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "raw" / "test_collection.csv"
COLOR_ORDER = "WUBRG"
THEME_WEIGHT = 0.75
COLOR_WEIGHT = 0.20
POPULARITY_WEIGHT = 0.05
MAX_EDHREC_RANK = 15_000
PAIRING_KEYWORDS = {
    "partner",
    "partner with",
    "choose a background",
    "doctor's companion",
    "friends forever",
}


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


def normalize_color_identity(
        colors: list[str]
        )->str:
    color_set = set(colors or [])


    colors = []

    for color in COLOR_ORDER:
        if color in color_set:
            colors.append(color)

    return "".join(colors)



def calculate_color_identity_counts(
    collection: dict[str,int],
    cards_by_id: dict[str, dict[str, Any]],
    )-> dict[str,int]:

    color_identity_counts = defaultdict(int)

    # ignore quantity for theme scorer - possibly keep another dict for total?
    for oracle_id in collection:
        card = cards_by_id.get(oracle_id)

        if card is None:
            continue

        identity = normalize_color_identity(card.get("color_identity", []))

        color_identity_counts[identity] += 1

    return dict(color_identity_counts)

def calculate_color_compatibility_ratio(
    commander: dict[str, Any],
    collection: dict[str, int],
    cards_by_id: dict[str, dict[str, Any]],
    relevant_themes: list[str] | None = None,
) -> float:
    """Return the share of relevant, unique cards legal in the commander's colors."""
    commander_colors = set(commander.get("color_identity") or [])
    commander_id = commander.get("oracle_id")
    relevant_theme_set = set(relevant_themes or [])
    compatible_cards = 0
    evaluated_cards = 0

    for oracle_id in collection:
        if oracle_id == commander_id:
            continue

        card = cards_by_id.get(oracle_id)

        if card is None:
            continue

        if (
            relevant_theme_set
            and not relevant_theme_set.intersection(card.get("themes", []))
        ):
            continue

        card_colors = set(card.get("color_identity") or [])

        if card_colors.issubset(commander_colors):
            compatible_cards += 1

        evaluated_cards += 1

    return compatible_cards / evaluated_cards if evaluated_cards else 0.0

def calculate_theme_scores(
    collection: dict[str, int],
    cards_by_id: dict[str, dict[str, Any]],
    ) -> dict[str, int]:
    """Count each owned Oracle ID once for every assigned theme."""
    scores = defaultdict(int)


    for oracle_id in collection:
        card = cards_by_id.get(oracle_id)

        if card is None:
            continue

        for theme in card.get("themes", []):
            scores[theme] += 1


    return dict(scores)


def requires_pairing(card: dict[str, Any]) -> bool:
    """Return whether a commander needs a partner or Background pairing."""
    keywords = {
        str(keyword).casefold()
        for keyword in card.get("keywords", [])
    }
    type_line = str(card.get("type_line") or "").casefold()

    return (
        bool(keywords & PAIRING_KEYWORDS)
        or "background" in type_line
    )


def get_commander_candidates(
    collection: dict[str, int],
    cards_by_id: dict[str, dict[str, Any]],
    top_themes: list[str],
) -> list[dict[str, Any]]:
    """Select owned, eligible commanders matching at least one top theme."""
    candidates = []

    for oracle_id in collection:
        card = cards_by_id.get(oracle_id)

        if (
            card is None
            or not card.get("commander_eligible", False)
            or requires_pairing(card)
        ):
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
                "color_identity": card.get("color_identity", []),
            }

        )

    return candidates


def rank_commanders(
    candidates: list[dict[str, Any]],
    theme_scores: dict[str, int],
    top_themes: list[str],
    collection: dict[str, int],
    cards_by_id: dict[str, dict[str, Any]],
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """Rank commanders by weighted theme fit, color support, and popularity."""
    ranked_commanders = []
    top_theme_total = sum(
        theme_scores.get(theme, 0)
        for theme in top_themes
    )

    for candidate in candidates:
        theme_match_score = sum(
            theme_scores.get(theme, 0)
            for theme in candidate["matching_themes"]
        )
        theme_ratio = (
            theme_match_score / top_theme_total
            if top_theme_total
            else 0.0
        )
        color_ratio = calculate_color_compatibility_ratio(
            candidate,
            collection,
            cards_by_id,
            relevant_themes=candidate["matching_themes"],
        )
        edhrec_rank = candidate["edhrec_rank"]
        popularity_score = (
            max(0, MAX_EDHREC_RANK - edhrec_rank) / MAX_EDHREC_RANK
            if edhrec_rank is not None
            else 0.0
        )
        final_score = (
            theme_ratio * THEME_WEIGHT
            + color_ratio * COLOR_WEIGHT
            + popularity_score * POPULARITY_WEIGHT
        )

        ranked_commanders.append(
            {
                **candidate,
                "theme_match_score": theme_match_score,
                "theme_ratio": theme_ratio,
                "color_ratio": color_ratio,
                "popularity_score": popularity_score,
                "final_score": final_score,
            }
        )

    ranked_commanders.sort(
        key=lambda commander: (
            -commander["final_score"],
            (
                commander["edhrec_rank"]
                if commander["edhrec_rank"] is not None
                else float("inf")
            ),
            commander["name"],
        )
    )

    return ranked_commanders[:top_n]

def recommend_commanders(
    collection: dict[str, int],
    cards_by_id: dict[str, dict[str, Any]],
    *,
    top_n: int = 5,
    theme_limit: int = 5,
) -> dict[str, Any]:
    """Return explainable commander recommendations for a collection."""
    if top_n <= 0:
        raise ValueError("top_n must be greater than zero.")

    if theme_limit <= 0:
        raise ValueError("theme_limit must be greater than zero.")

    theme_scores = calculate_theme_scores(collection, cards_by_id)

    top_themes = [
        theme
        for theme, _ in sorted(
            theme_scores.items(),
            key=lambda item: (-item[1], item[0]),
        )[:theme_limit]
    ]

    candidates = get_commander_candidates(
        collection,
        cards_by_id,
        top_themes,
    )

    recommendations = rank_commanders(
        candidates,
        theme_scores,
        top_themes,
        collection,
        cards_by_id,
        top_n=top_n,
    )

    return {
        "unique_cards": len(collection),
        "total_cards": sum(collection.values()),
        "theme_scores": theme_scores,
        "top_themes": top_themes,
        "recommendations": recommendations,
    }


def main()-> None:
    name_to_id = get_name_to_id()
    cards_by_id = get_cards_by_id()

    collection, unmatched_names = parse_collection(
        CSV_PATH, name_to_id
        )

    results = recommend_commanders(
        collection,
        cards_by_id,
        top_n=5,
    )

    results["unmatched_names"] = unmatched_names
    
    pprint(results)

if __name__ == "__main__":
    main()
