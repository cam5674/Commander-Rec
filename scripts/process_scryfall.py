from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import ijson


INPUT_PATH = Path("data/raw/oracle_cards.json")
CARDS_OUTPUT_PATH = Path("data/processed/cards_by_id.json")
NAME_LOOKUP_OUTPUT_PATH = Path("data/processed/name_to_id.json")
COMMANDERS_OUTPUT_PATH = Path("data/processed/commanders.json")
THEME_INDEX_OUTPUT_PATH = Path("data/processed/theme_to_card_ids.json")


THEME_RULES: dict[str, tuple[str, ...]] = {
    "reanimator": (
        "return target creature card from your graveyard",
        "return a creature card from your graveyard",
        "put target creature card from a graveyard onto the battlefield",
    ),
    "graveyard": (
        "graveyard",
        "mill",
        "surveil",
    ),
    "sacrifice": (
        "sacrifice",
        "dies",
        "whenever another creature you control dies",
    ),
    "tokens": (
        "create a",
        "create two",
        "create three",
        "creature token",
    ),
    "artifacts": (
        "artifact",
        "artifacts you control",
        "artifact card",
    ),
    "lifegain": (
        "gain life",
        "whenever you gain life",
        "lifelink",
    ),
    "plus_one_counters": (
        "+1/+1 counter",
        "proliferate",
    ),
    "spellslinger": (
        "instant or sorcery",
        "noncreature spell",
        "whenever you cast",
    ),
    "card_draw": (
        "draw a card",
        "draw two cards",
        "draw that many cards",
    ),
    "lands": (
        "landfall",
        "land card",
        "lands you control",
        "play an additional land",
    ),
    "aristocrats": (
        "whenever a creature dies",
        "whenever another creature dies",
        "whenever another creature you control dies",
        "whenever you sacrifice",
        "whenever you sacrifice another",
        "whenever a permanent is sacrificed",
    ),
    "wheels": (
        "each player discards their hand, then draws",
        "each player discards their hand and draws",
        "discard your hand, then draw",
        "shuffles their hand and graveyard into their library, then draws",
        "shuffles their hand into their library, then draws",
    ),
}


def get_image_url(card: dict[str, Any]) -> str | None:
    """Return the best image URL for a card."""

    # Normal single-faced card
    if "image_uris" in card:
        return card["image_uris"].get("normal")

    # MDFCs / Transform cards
    for face in card.get("card_faces", []):
        if "image_uris" in face:
            return face["image_uris"].get("normal")

    return None


def normalize_lookup_name(name: str) -> str:
    """
    Produce a consistent key for card-name lookup.

    Examples:
        "Sol Ring" -> "sol ring"
        "  Muldrotha, the Gravetide  "
            -> "muldrotha, the gravetide"
    """
    normalized = unicodedata.normalize("NFKC", name)
    normalized = normalized.casefold()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"\s*//\s*", " // ", normalized)

    return normalized.strip()


def combine_face_field(
    card: dict[str, Any],
    field: str,
    separator: str = " // ",
) -> str:
    """
    Return a top-level field when available, otherwise combine
    the values from each card face.
    """
    top_level_value = card.get(field)

    if top_level_value:
        return str(top_level_value)

    face_values = [
        str(face[field])
        for face in card.get("card_faces", [])
        if face.get(field)
    ]

    return separator.join(face_values)


def get_face_names(card: dict[str, Any]) -> list[str]:
    """
    Return individual face names that can also be used as aliases.
    """
    return [
        face["name"]
        for face in card.get("card_faces", [])
        if face.get("name")
    ]


def normalize_faces(card: dict[str, Any]) -> list[dict[str, Any]]:
    """Preserve the useful fields for every face of a multifaced card."""
    return [
        {
            "name": face.get("name", ""),
            "mana_cost": face.get("mana_cost", ""),
            "type_line": face.get("type_line", ""),
            "oracle_text": face.get("oracle_text", ""),
            "image": get_image_url(face),
        }
        for face in card.get("card_faces", [])
    ]


def classify_themes(
    oracle_text: str,
    type_line: str,
    keywords: list[str],
) -> list[str]:
    """
    Apply simple keyword rules to assign themes.

    This is intentionally a first-version classifier.
    """
    searchable_text = " ".join(
        (type_line, oracle_text, *keywords)
    ).casefold()
    themes: list[str] = []

    for theme, phrases in THEME_RULES.items():
        if any(phrase in searchable_text for phrase in phrases):
            themes.append(theme)

    return themes


def is_commander(card: dict[str, Any]) -> bool:
    """
    Determine whether the card can currently be used as a commander.

    This checks legality and the common commander eligibility rules.
    """
    legalities = card.get("legalities", {})

    if legalities.get("commander") != "legal":
        return False

    face_type_lines = [
        str(face["type_line"]).casefold()
        for face in card.get("card_faces", [])
        if face.get("type_line")
    ]
    type_lines = face_type_lines or [
        combine_face_field(card, "type_line").casefold()
    ]
    oracle_text = combine_face_field(card, "oracle_text").casefold()

    is_legendary_creature = any(
        "legendary" in type_line and "creature" in type_line
        for type_line in type_lines
    )
    is_legendary_background = any(
        "legendary" in type_line and "background" in type_line
        for type_line in type_lines
    )

    explicitly_can_be_commander = (
        "can be your commander" in oracle_text
    )
    is_creature_outside_battlefield = (
        "isn't on the battlefield" in oracle_text
        and "creature in addition to its other types" in oracle_text
    )

    return any((
        is_legendary_creature,
        is_legendary_background,
        explicitly_can_be_commander,
        is_creature_outside_battlefield,
    ))


def normalize_card(card: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a Scryfall card object into the application's smaller schema.
    """
    oracle_text = combine_face_field(
        card,
        "oracle_text",
        separator="\n//\n",
    )
    type_line = combine_face_field(card, "type_line")
    keywords = [str(keyword) for keyword in card.get("keywords", [])]
    commander_eligible = is_commander(card)

    return {
        "oracle_id": card["oracle_id"],
        "scryfall_id": card["id"],
        "name": card["name"],
        "layout": card.get("layout", "normal"),
        "mana_cost": combine_face_field(card, "mana_cost"),
        "mana_value": float(card.get("cmc") or 0),
        "type_line": type_line,
        "oracle_text": oracle_text,
        "keywords": keywords,
        "color_identity": card.get("color_identity", []),
        "commander_format_legal": (
            card.get("legalities", {}).get("commander") == "legal"
        ),
        "commander_eligible": commander_eligible,
        "themes": classify_themes(
            oracle_text=oracle_text,
            type_line=type_line,
            keywords=keywords,
        ),
        "image": get_image_url(card),
        "faces": normalize_faces(card),
    }


def add_name_mapping(
    name_to_id: dict[str, str],
    primary_keys: set[str],
    collisions: set[str],
    name: str,
    oracle_id: str,
    *,
    is_primary: bool,
) -> None:
    """Add a normalized name while preserving canonical-name precedence."""
    lookup_key = normalize_lookup_name(name)
    existing_id = name_to_id.get(lookup_key)

    if existing_id is not None and existing_id != oracle_id:
        collisions.add(lookup_key)

    if is_primary:
        if lookup_key not in primary_keys:
            name_to_id[lookup_key] = oracle_id
            primary_keys.add(lookup_key)
        return

    name_to_id.setdefault(lookup_key, oracle_id)


def process_cards(
    input_path: Path,
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, str],
    list[str],
    dict[str, list[str]],
]:
    """
    Stream the raw bulk file and produce application indexes.
    """
    cards_by_id: dict[str, dict[str, Any]] = {}
    name_to_id: dict[str, str] = {}
    commander_ids: list[str] = []
    theme_to_card_ids: dict[str, list[str]] = {}
    primary_keys: set[str] = set()
    name_collisions: set[str] = set()

    processed_count = 0
    skipped_non_paper_count = 0

    with input_path.open("rb") as source_file:
        for raw_card in ijson.items(
            source_file,
            "item",
            use_float=True,
        ):
            # Defensive check in case the input contains an unusual object.
            if not raw_card.get("oracle_id") or not raw_card.get("name"):
                continue

            games = raw_card.get("games", [])

            if games and "paper" not in games:
                skipped_non_paper_count += 1
                continue

            normalized_card = normalize_card(raw_card)
            oracle_id = raw_card["oracle_id"]

            cards_by_id[oracle_id] = normalized_card
            add_name_mapping(
                name_to_id,
                primary_keys,
                name_collisions,
                raw_card["name"],
                oracle_id,
                is_primary=True,
            )

            # Also support looking up an individual face name.
            for face_name in get_face_names(raw_card):
                add_name_mapping(
                    name_to_id,
                    primary_keys,
                    name_collisions,
                    face_name,
                    oracle_id,
                    is_primary=False,
                )

            if normalized_card["commander_eligible"]:
                commander_ids.append(oracle_id)

            for theme in normalized_card["themes"]:
                theme_to_card_ids.setdefault(theme, []).append(oracle_id)

            processed_count += 1

            if processed_count % 5_000 == 0:
                print(f"Processed {processed_count:,} cards...")

    cards_by_id = dict(sorted(
        cards_by_id.items(),
        key=lambda item: item[1]["name"].casefold(),
    ))
    name_to_id = dict(sorted(name_to_id.items()))
    commander_ids.sort(
        key=lambda oracle_id: cards_by_id[oracle_id]["name"].casefold()
    )
    theme_to_card_ids = {
        theme: sorted(
            oracle_ids,
            key=lambda oracle_id: cards_by_id[oracle_id]["name"].casefold(),
        )
        for theme, oracle_ids in sorted(theme_to_card_ids.items())
    }

    print(f"Processed cards: {processed_count:,}")
    print(f"Skipped non-paper cards: {skipped_non_paper_count:,}")
    print(f"Lookup keys: {len(name_to_id):,}")
    print(f"Name collisions: {len(name_collisions):,}")

    if name_collisions:
        collision_examples = ", ".join(sorted(name_collisions)[:10])
        print(f"Name collision examples: {collision_examples}")

    print(f"Commanders: {len(commander_ids):,}")

    return cards_by_id, name_to_id, commander_ids, theme_to_card_ids


def write_json(
    output_path: Path,
    data: Any,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = output_path.with_suffix(
        output_path.suffix + ".part"
    )

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            data,
            output_file,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    temporary_path.replace(output_path)


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_PATH}\n"
            "Run the Scryfall download script first."
        )

    (
        cards_by_id,
        name_to_id,
        commander_ids,
        theme_to_card_ids,
    ) = process_cards(INPUT_PATH)

    write_json(CARDS_OUTPUT_PATH, cards_by_id)
    write_json(NAME_LOOKUP_OUTPUT_PATH, name_to_id)
    write_json(COMMANDERS_OUTPUT_PATH, commander_ids)
    write_json(THEME_INDEX_OUTPUT_PATH, theme_to_card_ids)

    print(f"Saved cards to: {CARDS_OUTPUT_PATH}")
    print(f"Saved name lookup to: {NAME_LOOKUP_OUTPUT_PATH}")
    print(f"Saved commanders to: {COMMANDERS_OUTPUT_PATH}")
    print(f"Saved theme index to: {THEME_INDEX_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
