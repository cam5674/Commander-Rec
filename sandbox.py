import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any

from scripts.process_scryfall import normalize_lookup_name

PROCESSED_DIR = Path("data/processed")
NAME_LOOKUP_PATH = PROCESSED_DIR / "name_to_id.json"
CARDS_PATH = PROCESSED_DIR / "cards_by_id.json"


def load_json(path: Path) -> Any:
    """Load a processed JSON file with a useful error message."""
    try:
        with path.open(encoding="utf-8") as source_file:
            return json.load(source_file)
    except FileNotFoundError as error:
        raise RuntimeError(
            f"Missing processed data file: {path}\n"
            "Run 'python scripts/process_scryfall.py' first."
        ) from error
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Invalid JSON in {path}: {error}\n"
            "Delete the processed files and run the processing script again."
        ) from error


def pretty_print_card(card_name: str) -> bool:
    name_to_id: dict[str, str] = load_json(NAME_LOOKUP_PATH)

    lookup_name = normalize_lookup_name(card_name)
    oracle_id = name_to_id.get(lookup_name)

    if oracle_id is None:
        print(f"Card not found: {card_name}", file=sys.stderr)
        suggestions = difflib.get_close_matches(
            lookup_name,
            name_to_id,
            n=5,
            cutoff=0.6,
        )

        if suggestions:
            print(
                "Did you mean: " + ", ".join(suggestions),
                file=sys.stderr,
            )

        return False

    cards_by_id: dict[str, dict[str, Any]] = load_json(CARDS_PATH)
    card = cards_by_id.get(oracle_id)

    if card is None:
        raise RuntimeError(
            f"Oracle ID {oracle_id} is missing from {CARDS_PATH}.\n"
            "Run the processing script again to rebuild consistent indexes."
        )

    print(json.dumps(card, indent=2, ensure_ascii=False))
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pretty-print a processed Scryfall card record.",
    )
    parser.add_argument(
        "card_name",
        nargs="+",
        help="card name, such as 'The Locust God'",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    print(args)
    card_name = " ".join(args.card_name)
    print(card_name)

    if not card_name:
        print("Card name cannot be empty.", file=sys.stderr)
        return 2

    if len(card_name) > 200:
        print("Card name is unexpectedly long.", file=sys.stderr)
        return 2

    print(f"Looking up: {card_name}", file=sys.stderr)

    try:
        return 0 if pretty_print_card(card_name) else 1
    except (OSError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
