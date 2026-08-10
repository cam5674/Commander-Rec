from __future__ import annotations

import gzip
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

INPUT_PATH = Path("data/raw/oracle_cards.jsonl.gz")
CARDS_OUTPUT_PATH = Path("data/processed/cards_by_id.json")
NAME_LOOKUP_OUTPUT_PATH = Path("data/processed/name_to_id.json")
COMMANDERS_OUTPUT_PATH = Path("data/processed/commanders.json")
THEME_INDEX_OUTPUT_PATH = Path("data/processed/theme_to_card_ids.json")


CLAUSE_GAP = r"[^.;\n]{0,160}?"
ORACLE_CLAUSE_BOUNDARY = re.compile(
    r"(?:\n+|(?<=[.;])\s+|\s+//\s+|\s+•\s+)"
)

THEME_ORDER = (
    "reanimator",
    "graveyard",
    "sacrifice",
    "tokens",
    "artifacts",
    "lifegain",
    "plus_one_counters",
    "spellslinger",
    "card_draw",
    "lands",
    "aristocrats",
    "wheels",
)

THEME_TYPE_RULES: dict[str, tuple[str, ...]] = {
    "artifacts": (r"\bartifact\b",),
}

GRAVEYARD_USE_PATTERN = (
    rf"\b(?:return|cast|play|exile|copy)\b{CLAUSE_GAP}"
    r"\bfrom (?:a|your|an opponent's) graveyard\b"
)

THEME_ORACLE_RULES: dict[str, tuple[str, ...]] = {
    "reanimator": (
        rf"\b(?:return|put)\b{CLAUSE_GAP}"
        rf"\b(?:creature|permanent) cards?\b{CLAUSE_GAP}"
        rf"\bfrom (?:a|your) graveyard\b{CLAUSE_GAP}"
        r"\b(?:onto|to) the battlefield\b",
        rf"\bcast\b{CLAUSE_GAP}"
        rf"\b(?:creature|permanent) spells?\b{CLAUSE_GAP}"
        r"\bfrom your graveyard\b",
    ),
    "graveyard": (
        r"\byou mill(?:ed)?\b",
        r"\beach player mills?\b",
        r"\bsurveil\b",
        rf"\b(?:cards?|creatures?|permanents?)\b{CLAUSE_GAP}"
        r"\bin your graveyard\b",
        rf"\bput\b{CLAUSE_GAP}\binto (?:your |a )?graveyards?\b",
        GRAVEYARD_USE_PATTERN,
    ),
    "sacrifice": (
        rf"\byou may sacrifice\b{CLAUSE_GAP}"
        r"\b(?:a|an|another|one or more|any number of)\b",
        rf"\bas an additional cost\b{CLAUSE_GAP}\bsacrifice\b",
        rf"\bsacrifice (?:this|a|an|another)\b{CLAUSE_GAP}:",
        rf"\bsacrifice (?:this|a|an|another)\b{CLAUSE_GAP}\bto\b",
    ),
    "tokens": (
        rf"\bcreate\b{CLAUSE_GAP}\btokens?\b",
        rf"\bput\b{CLAUSE_GAP}\btokens?\b{CLAUSE_GAP}"
        r"\bonto the battlefield\b",
        r"\btokens? you control\b",
        rf"\bwhenever\b{CLAUSE_GAP}\btokens?\b{CLAUSE_GAP}"
        r"\b(?:enter|enters|die|dies|leave|leaves)\b",
        r"\btokens? would be created\b",
    ),
    "artifacts": (
        r"\bartifact spells? you cast\b",
        r"\bartifacts? you control\b",
        rf"\bwhenever\b{CLAUSE_GAP}\bartifact\b{CLAUSE_GAP}"
        r"\benters\b",
        r"\bnumber of artifacts you control\b",
        rf"\breturn\b{CLAUSE_GAP}\bartifact card\b",
        r"\bsacrifice an artifact\b",
    ),
    "lifegain": (
        r"\bgain life\b",
        r"\bwhenever you gain life\b",
        r"\bgain [123] life\b",
        r"\bgain that much life\b",
        r"\bgain life equal to\b",
        rf"\bcreate\b{CLAUSE_GAP}\bfood tokens?\b",
    ),
    "plus_one_counters": (
        r"\+1/\+1 counters?\b",
    ),
    "spellslinger": (
        rf"\b(?:cast|copy|return)\b{CLAUSE_GAP}"
        r"\binstant or sorcery\b",
        rf"\bcopy\b{CLAUSE_GAP}\binstant or sorcery spell\b",
        r"\binstant and sorcery spells? you cast\b",
        rf"\bwhenever you cast\b{CLAUSE_GAP}\bnoncreature spell\b",
        r"\bcast an instant\b",
        r"\bcast a sorcery\b",
    ),
    "card_draw": (
        r"\bdraw a card\b",
        r"\bdraw two cards\b",
        r"\bdraw that many cards\b",
        r"\bdraw three cards\b",
        r"\bdraw four cards\b",
        r"\bdraw x cards\b",
        r"\bdraw cards equal to\b",
        r"\bdraws a card\b",
        r"\bdraw an additional card\b",
        r"\bwhenever you draw\b",
        r"\beach player draws\b",
        r"\bdraw seven cards\b",
    ),
    "lands": (
        r"\bwhenever a land\b",
        r"\bplay an additional land\b",
        r"\bsearch your library for a land\b",
        r"\bput a land card from your hand onto the battlefield\b",
        r"\breturn target land card from your graveyard\b",
        r"\bland cards in your graveyard\b",
        r"\bwhenever one or more lands enter\b",
    ),
    "aristocrats": (
        rf"\bwhenever\b{CLAUSE_GAP}"
        rf"\b(?:creature|permanent|token)s?\b{CLAUSE_GAP}\bdies?\b",
        r"\bwhenever you sacrifice\b",
        r"\bwhenever a permanent is sacrificed\b",
        r"\bwhen this creature dies\b",
    ),
    "wheels": (
        r"\beach player discards their hand,? then draws\b",
        r"\beach player discards their hand and draws\b",
        r"\bdiscard your hand,? then draw\b",
        rf"\bshuffles? their hand\b{CLAUSE_GAP}\bthen draws\b",
        r"\bdiscards? their hand,? then draws\b",
        r"\bdiscard your hand and draw\b",
        rf"\bshuffle your hand into your library\b{CLAUSE_GAP}\bthen draw\b",
        rf"\bputs? their hand on the bottom of their library\b"
        rf"{CLAUSE_GAP}\bthen draws\b",
        r"\bdiscard any number of cards,? then draw\b",
    ),
}

THEME_KEYWORD_RULES: dict[str, tuple[str, ...]] = {
    "graveyard": (
        "surveil",
        "flashback",
        "dredge",
        "escape",
        "delve",
        "threshold",
        "descend",
        "undergrowth",
    ),
    "sacrifice": ("exploit", "devour"),
    "tokens": (
        "investigate",
        "populate",
        "fabricate",
        "incubate",
        "amass",
        "living weapon",
        "offspring",
    ),
    "artifacts": (
        "metalcraft",
        "affinity for artifacts",
        "improvise",
    ),
    "lifegain": ("lifelink", "extort"),
    "plus_one_counters": (
        "proliferate",
        "evolve",
        "adapt",
        "bolster",
        "mentor",
        "riot",
        "backup",
        "fabricate",
        "monstrosity",
        "outlast",
    ),
    "spellslinger": ("magecraft", "storm", "prowess"),
    "lands": ("landfall", "landcycling", "domain", "explore"),
    "aristocrats": ("morbid", "afterlife"),
}

THEME_RULES: dict[str, tuple[str, ...]] = {
    theme: (
        THEME_TYPE_RULES.get(theme, ())
        + THEME_ORACLE_RULES.get(theme, ())
        + THEME_KEYWORD_RULES.get(theme, ())
    )
    for theme in THEME_ORDER
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


def strip_reminder_text(oracle_text: str) -> str:
    """Remove parenthetical reminder text, including nested parentheses."""
    stripped_characters: list[str] = []
    parenthesis_depth = 0

    for character in oracle_text:
        if character == "(":
            parenthesis_depth += 1
            continue

        if character == ")" and parenthesis_depth:
            parenthesis_depth -= 1
            continue

        if parenthesis_depth == 0:
            stripped_characters.append(character)

    return "".join(stripped_characters)


def split_oracle_clauses(oracle_text: str) -> tuple[str, ...]:
    """Return reminder-free clauses that regex gaps cannot cross."""
    rules_text = strip_reminder_text(oracle_text).casefold()
    return tuple(
        clause.strip()
        for clause in ORACLE_CLAUSE_BOUNDARY.split(rules_text)
        if clause.strip()
    )


def get_theme_matches(
    oracle_text: str,
    type_line: str,
    keywords: list[str],
) -> dict[str, list[str]]:
    """Return the source-aware rules that matched each assigned theme."""
    type_text = type_line.casefold()
    oracle_clauses = split_oracle_clauses(oracle_text)
    keyword_set = {
        str(keyword).casefold()
        for keyword in keywords
    }
    matches_by_theme: dict[str, list[str]] = {}

    for theme in THEME_ORDER:
        matches: list[str] = []

        matches.extend(
            pattern
            for pattern in THEME_TYPE_RULES.get(theme, ())
            if re.search(pattern, type_text)
        )
        matches.extend(
            pattern
            for pattern in THEME_ORACLE_RULES.get(theme, ())
            if any(
                re.search(pattern, clause)
                for clause in oracle_clauses
            )
        )
        matches.extend(
            keyword
            for keyword in THEME_KEYWORD_RULES.get(theme, ())
            if keyword in keyword_set
        )

        if matches:
            matches_by_theme[theme] = matches

    if (
        "reanimator" in matches_by_theme
        and matches_by_theme.get("graveyard") == [GRAVEYARD_USE_PATTERN]
    ):
        del matches_by_theme["graveyard"]

    return matches_by_theme


def classify_themes(
    oracle_text: str,
    type_line: str,
    keywords: list[str],
) -> list[str]:
    """
    Apply source-aware, clause-bounded rules to assign themes.
    """
    return list(get_theme_matches(
        oracle_text,
        type_line,
        keywords,
    ))


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
        "edhrec_rank": card.get("edhrec_rank"),
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

    with gzip.open(
        input_path,
        "rt",
        encoding="utf-8",
    ) as source_file:
        for line_number, line in enumerate(source_file, start=1):
            if not line.strip():
                continue

            try:
                raw_card = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid Scryfall JSONL on line {line_number}."
                ) from error

            # Defensive check in case the input contains an unusual object.
            if not raw_card.get("oracle_id") or not raw_card.get("name"):
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
