#TODO: implement color-identity compatibility (can see the most common color pairings in the collection)


from pprint import pprint
from backend.csv_parser import parse_collection
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import quote
from .data_loader import get_cards_by_id, get_commanders, get_name_to_id
from scripts.process_scryfall import get_theme_matches

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "raw" / "test_collection.csv"
COLOR_ORDER = "WUBRG"
THEME_WEIGHT = 0.75
COLOR_WEIGHT = 0.20
POPULARITY_WEIGHT = 0.05
MAX_EDHREC_RANK = 15_000
MAX_RECOMMENDATIONS = 20
MIN_THEME_MATCH_RATIO = 0.60
RATIO_PRIOR_MATCHES = 1
RATIO_PRIOR_MISSES = 1
PAIRING_KEYWORDS = {
    "partner",
    "partner with",
    "choose a background",
    "doctor's companion",
    "friends forever",
}


def get_scryfall_card_url(oracle_id: str) -> str:
    query = quote(f"oracleid:{oracle_id}", safe="")
    return f"https://scryfall.com/search?q={query}"


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

        matched_triggers = get_theme_matches(
            card.get("oracle_text", ""),
            card.get("type_line", ""),
            card.get("keywords", []),
        ).get(theme, [])

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
    """Return the smoothed share of relevant cards legal in the colors."""
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

    return calculate_smoothed_ratio(compatible_cards, evaluated_cards)


def calculate_smoothed_ratio(matches: int, total: int) -> float:
    """Return a Laplace-smoothed ratio using symmetric unit priors."""
    return (
        matches + RATIO_PRIOR_MATCHES
    ) / (
        total + RATIO_PRIOR_MATCHES + RATIO_PRIOR_MISSES
    )

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

def get_score_breakdown(
    theme_ratio: float,
    color_ratio: float,
    edhrec_rank: int | None,
) -> dict[str, float]:
    popularity_score = (
        max(0, MAX_EDHREC_RANK - edhrec_rank) / MAX_EDHREC_RANK
        if edhrec_rank is not None
        else 0.0
    )

    theme_contribution = theme_ratio * THEME_WEIGHT
    color_contribution = color_ratio * COLOR_WEIGHT
    popularity_contribution = popularity_score * POPULARITY_WEIGHT
    final_score = (
        theme_contribution
        + color_contribution
        + popularity_contribution
    )

    return {
        "theme_ratio": round(theme_ratio, 4),
        "theme_contribution": round(theme_contribution, 4),
        "color_ratio": round(color_ratio, 4),
        "color_contribution": round(color_contribution, 4),
        "popularity_score": round(popularity_score, 4),
        "popularity_contribution": round(popularity_contribution, 4),
        "final_score": round(final_score, 4),
    }


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

def get_theme_supporting_cards(
    candidate_oracle_id: str,
    theme: str,
    collection: dict[str, int],
    cards_by_id: dict[str, dict[str, Any]],
    commander_colors: set[str],
    limit: int = 5,
) -> tuple[int, list[dict[str, Any]]]:
    """Return the count and top owned cards supporting one theme."""
    supporting_cards = []
    for oracle_id, quantity in collection.items():
        if candidate_oracle_id == oracle_id:
            continue
        card = cards_by_id.get(oracle_id)

        if card is None:
            continue

        if theme not in card.get("themes", []):
            continue

        card_colors = set(card.get("color_identity", []))

        if not card_colors.issubset(commander_colors):
            continue

        supporting_cards.append({
            "oracle_id": oracle_id,
            "scryfall_id": card.get("scryfall_id"),
            "scryfall_url": get_scryfall_card_url(oracle_id),
            "image_url": card.get("image"),
            "name": card["name"],
            "quantity": quantity,
            "edhrec_rank": card.get("edhrec_rank"),
        })

    supporting_cards.sort(
        key=lambda card: (
            (
                card["edhrec_rank"]
                if card["edhrec_rank"] is not None
                else float("inf")
            ),
            card["name"],
        )
    )

    return len(supporting_cards), supporting_cards[:limit]


def get_commander_candidates(
    collection: dict[str, int],
    cards_by_id: dict[str, dict[str, Any]],
    commander_ids: list[str],
    top_themes: list[str],
) -> list[dict[str, Any]]:
    """Select eligible commanders matching at least one top theme."""
    candidates = []

    for oracle_id in commander_ids:
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
                "scryfall_id": card.get("scryfall_id"),
                "scryfall_url": get_scryfall_card_url(oracle_id),
                "name": card["name"],
                "image_url": card.get("image"),
                "themes": card.get("themes", []),
                "matching_themes": sorted(matching_themes),
                "edhrec_rank": card.get("edhrec_rank"),
                "color_identity": card.get("color_identity", []),
                "owned": oracle_id in collection,
            }

        )

    return candidates


def score_commander_candidate(
    candidate: dict[str, Any],
    theme_scores: dict[str, int],
    top_theme_total: int,
    collection: dict[str, int],
    cards_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Return a candidate with its theme, color, and popularity scores."""
    theme_match_score = sum(
        theme_scores.get(theme, 0)
        for theme in candidate["matching_themes"]
    )
    theme_ratio = calculate_smoothed_ratio(
        theme_match_score,
        top_theme_total,
    )
    color_ratio = calculate_color_compatibility_ratio(
        candidate,
        collection,
        cards_by_id,
        relevant_themes=candidate["matching_themes"],
    )

    return {
        **candidate,
        "theme_match_score": theme_match_score,
        "score_breakdown": get_score_breakdown(
            theme_ratio,
            color_ratio,
            candidate["edhrec_rank"],
        ),
    }


def build_commander_theme_support(
    commander: dict[str, Any],
    collection: dict[str, int],
    cards_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build per-theme support evidence for a ranked commander."""
    theme_support = []

    for theme in commander["matching_themes"]:
        supporting_card_count, example_cards = get_theme_supporting_cards(
            candidate_oracle_id=commander["oracle_id"],
            theme=theme,
            collection=collection,
            cards_by_id=cards_by_id,
            commander_colors=set(commander["color_identity"]),
        )

        theme_support.append(
            {
                "theme": theme,
                "supporting_card_count": supporting_card_count,
                "example_cards": example_cards,
            }
        )

    return theme_support


def rank_commanders(
    candidates: list[dict[str, Any]],
    theme_scores: dict[str, int],
    top_themes: list[str],
    collection: dict[str, int],
    cards_by_id: dict[str, dict[str, Any]],
    top_n: int = 5,
    min_theme_ratio: float = 0.0,
) -> list[dict[str, Any]]:
    """Score, order, and enrich the top commander candidates."""
    if not 0.0 <= min_theme_ratio <= 1.0:
        raise ValueError("min_theme_ratio must be between zero and one.")

    top_theme_total = sum(
        theme_scores.get(theme, 0)
        for theme in top_themes
    )

    ranked_commanders = [
        score_commander_candidate(
            candidate,
            theme_scores,
            top_theme_total,
            collection,
            cards_by_id,
        )
        for candidate in candidates
    ]
    eligible_commanders = [
        commander
        for commander in ranked_commanders
        if (
            commander["theme_match_score"] / top_theme_total
            if top_theme_total
            else 0.0
        ) >= min_theme_ratio
    ]

    eligible_commanders.sort(
        key=lambda commander: (
            -commander["score_breakdown"]["final_score"],
            (
                commander["edhrec_rank"]
                if commander["edhrec_rank"] is not None
                else float("inf")
            ),
            commander["name"],
            commander["oracle_id"],
        )
    )

    return [
        {
            **commander,
            "theme_support": build_commander_theme_support(
                commander,
                collection,
                cards_by_id,
            ),
        }
        for commander in eligible_commanders[:top_n]
    ]

def recommend_commanders(
    collection: dict[str, int],
    cards_by_id: dict[str, dict[str, Any]],
    commander_ids: list[str],
    *,
    top_n: int = MAX_RECOMMENDATIONS,
    theme_limit: int = 5,
    min_theme_ratio: float = MIN_THEME_MATCH_RATIO,
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
        commander_ids,
        top_themes,
    )

    recommendations = rank_commanders(
        candidates,
        theme_scores,
        top_themes,
        collection,
        cards_by_id,
        top_n=top_n,
        min_theme_ratio=min_theme_ratio,
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
    commander_ids = get_commanders()

    parse_result = parse_collection(
        CSV_PATH,
        name_to_id,
    )

    results = recommend_commanders(
        parse_result.collection,
        cards_by_id,
        commander_ids,
        top_n=2,
    )

    results["unmatched_names"] = parse_result.unmatched_names
    results["warnings"] = parse_result.warnings

    pprint(results)

if __name__ == "__main__":
    main()
