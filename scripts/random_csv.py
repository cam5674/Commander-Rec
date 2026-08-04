"""Generate reproducible collection CSVs for end-to-end testing.

Examples:
    python -m scripts.random_csv --profile showcase --seed 42
    python -m scripts.random_csv --profile boundary --rows 20000
    python -m scripts.random_csv --profile warnings --invalid-rate 0.2
    python -m scripts.random_csv --themes graveyard tokens --colors B G
"""

import argparse
import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from backend.data_loader import (
    get_cards_by_id,
    get_commanders,
    get_name_to_id,
    get_theme_to_card_ids,
)
from scripts.process_scryfall import normalize_lookup_name


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "raw" / "random_csv.csv"
FIELDNAMES = ["name", "count"]
VALID_COLORS = frozenset("WUBRG")

PROFILE_DEFAULTS = {
    "showcase": {
        "rows": 500,
        "themes": ("graveyard", "tokens"),
        "theme_ratio": 0.85,
        "commander_count": 25,
        "duplicate_rate": 0.05,
        "invalid_rate": 0.0,
    },
    "random": {
        "rows": 500,
        "themes": (),
        "theme_ratio": 0.0,
        "commander_count": 25,
        "duplicate_rate": 0.05,
        "invalid_rate": 0.0,
    },
    "boundary": {
        "rows": 20_000,
        "themes": (),
        "theme_ratio": 0.0,
        "commander_count": 50,
        "duplicate_rate": 0.05,
        "invalid_rate": 0.0,
    },
    "warnings": {
        "rows": 100,
        "themes": (),
        "theme_ratio": 0.0,
        "commander_count": 5,
        "duplicate_rate": 0.1,
        "invalid_rate": 0.15,
    },
}


@dataclass(frozen=True)
class CardCandidate:
    oracle_id: str
    name: str
    themes: frozenset[str]
    color_identity: frozenset[str]


@dataclass(frozen=True)
class GenerationConfig:
    rows: int
    themes: tuple[str, ...]
    theme_ratio: float
    colors: frozenset[str] | None
    commander_count: int
    duplicate_rate: float
    invalid_rate: float
    min_quantity: int
    max_quantity: int
    seed: int


@dataclass(frozen=True)
class GenerationResult:
    rows: list[dict[str, str | int]]
    selected_cards: tuple[CardCandidate, ...]
    duplicate_rows: int
    invalid_rows: int
    themed_cards: int
    valid_quantity: int


def build_candidates(
    cards_by_id: dict[str, dict[str, Any]],
    name_to_id: dict[str, str],
    theme_to_card_ids: dict[str, list[str]],
) -> tuple[dict[str, CardCandidate], int]:
    """Build cards whose names round-trip through the CSV parser."""
    themes_by_id: dict[str, set[str]] = {}
    for theme, oracle_ids in theme_to_card_ids.items():
        for oracle_id in oracle_ids:
            themes_by_id.setdefault(oracle_id, set()).add(theme)

    candidates: dict[str, CardCandidate] = {}
    skipped_cards = 0

    for oracle_id, card in cards_by_id.items():
        name = card.get("name")
        if (
            not isinstance(name, str)
            or name_to_id.get(normalize_lookup_name(name)) != oracle_id
        ):
            skipped_cards += 1
            continue

        color_identity = card.get("color_identity", [])
        if not isinstance(color_identity, list):
            color_identity = []

        candidates[oracle_id] = CardCandidate(
            oracle_id=oracle_id,
            name=name,
            themes=frozenset(themes_by_id.get(oracle_id, set())),
            color_identity=frozenset(
                color
                for color in color_identity
                if isinstance(color, str)
            ),
        )

    return candidates, skipped_cards


def validate_config(
    config: GenerationConfig,
    available_themes: set[str],
) -> None:
    if config.rows < 1:
        raise ValueError("--rows must be at least 1.")
    if config.commander_count < 0:
        raise ValueError("--commander-count cannot be negative.")
    if not 0 <= config.theme_ratio <= 1:
        raise ValueError("--theme-ratio must be between 0 and 1.")
    if not 0 <= config.duplicate_rate < 1:
        raise ValueError("--duplicate-rate must be at least 0 and below 1.")
    if not 0 <= config.invalid_rate < 1:
        raise ValueError("--invalid-rate must be at least 0 and below 1.")
    if config.min_quantity < 1:
        raise ValueError("--min-quantity must be at least 1.")
    if config.max_quantity < config.min_quantity:
        raise ValueError("--max-quantity cannot be below --min-quantity.")
    if config.theme_ratio and not config.themes:
        raise ValueError("--theme-ratio requires at least one --themes value.")
    if config.colors is not None and not config.colors.issubset(VALID_COLORS):
        raise ValueError("Color filters may only contain W, U, B, R, or G.")

    unknown_themes = sorted(set(config.themes) - available_themes)
    if unknown_themes:
        raise ValueError(
            "Unknown theme(s): " + ", ".join(unknown_themes)
        )


def filter_candidates(
    candidates: dict[str, CardCandidate],
    colors: frozenset[str] | None,
) -> dict[str, CardCandidate]:
    if colors is None:
        return candidates

    return {
        oracle_id: candidate
        for oracle_id, candidate in candidates.items()
        if candidate.color_identity.issubset(colors)
    }


def select_balanced_theme_cards(
    candidates: dict[str, CardCandidate],
    themes: tuple[str, ...],
    count: int,
    selected_ids: set[str],
    rng: random.Random,
) -> list[CardCandidate]:
    theme_pools: dict[str, list[str]] = {}
    for theme in themes:
        theme_pool = sorted(
            oracle_id
            for oracle_id, candidate in candidates.items()
            if theme in candidate.themes and oracle_id not in selected_ids
        )
        rng.shuffle(theme_pool)
        theme_pools[theme] = theme_pool

    selected_cards: list[CardCandidate] = []
    while len(selected_cards) < count:
        made_progress = False
        for theme in themes:
            theme_pool = theme_pools[theme]
            while theme_pool and theme_pool[-1] in selected_ids:
                theme_pool.pop()

            if not theme_pool:
                continue

            oracle_id = theme_pool.pop()
            selected_ids.add(oracle_id)
            selected_cards.append(candidates[oracle_id])
            made_progress = True

            if len(selected_cards) == count:
                break

        if not made_progress:
            break

    return selected_cards


def select_cards(
    candidates: dict[str, CardCandidate],
    commander_ids: Sequence[str],
    unique_target: int,
    config: GenerationConfig,
    rng: random.Random,
) -> list[CardCandidate]:
    if config.commander_count > unique_target:
        raise ValueError(
            "--commander-count cannot exceed the number of unique valid rows."
        )

    commander_pool = sorted(
        oracle_id
        for oracle_id in commander_ids
        if oracle_id in candidates
    )
    if config.commander_count > len(commander_pool):
        raise ValueError(
            f"Only {len(commander_pool):,} commanders satisfy the filters; "
            f"cannot select {config.commander_count:,}."
        )

    preferred_commanders = [
        oracle_id
        for oracle_id in commander_pool
        if config.theme_ratio
        and candidates[oracle_id].themes.intersection(config.themes)
    ]
    preferred_count = min(
        config.commander_count,
        len(preferred_commanders),
    )
    selected_commander_ids = rng.sample(
        preferred_commanders,
        preferred_count,
    )
    remaining_commander_pool = sorted(
        set(commander_pool) - set(selected_commander_ids)
    )
    selected_commander_ids.extend(
        rng.sample(
            remaining_commander_pool,
            config.commander_count - preferred_count,
        )
    )

    selected_ids: set[str] = set()
    selected_cards: list[CardCandidate] = []
    for oracle_id in selected_commander_ids:
        selected_ids.add(oracle_id)
        selected_cards.append(candidates[oracle_id])

    selected_themed = sum(
        bool(candidate.themes.intersection(config.themes))
        for candidate in selected_cards
    )
    themed_target = math.ceil(unique_target * config.theme_ratio)
    themed_needed = max(0, themed_target - selected_themed)
    available_slots = unique_target - len(selected_cards)
    if themed_needed > available_slots:
        raise ValueError(
            "The requested commander count leaves too few rows to satisfy "
            "--theme-ratio. Reduce --commander-count or --theme-ratio."
        )
    themed_cards = select_balanced_theme_cards(
        candidates,
        config.themes,
        themed_needed,
        selected_ids,
        rng,
    )
    selected_cards.extend(themed_cards)

    if len(themed_cards) < themed_needed:
        available = selected_themed + len(themed_cards)
        raise ValueError(
            f"Only {available:,} unique cards match the selected themes and "
            f"filters; {themed_target:,} are required by --theme-ratio."
        )

    remaining_count = unique_target - len(selected_cards)
    if remaining_count < 0:
        raise ValueError(
            "Commander selection exceeds the requested unique row count."
        )

    selected_theme_set = set(config.themes)
    noise_pool = sorted(
        oracle_id
        for oracle_id, candidate in candidates.items()
        if oracle_id not in selected_ids
        and not candidate.themes.intersection(selected_theme_set)
    )
    fill_ids = rng.sample(
        noise_pool,
        min(remaining_count, len(noise_pool)),
    )
    selected_ids.update(fill_ids)
    selected_cards.extend(candidates[oracle_id] for oracle_id in fill_ids)
    remaining_count = unique_target - len(selected_cards)

    if remaining_count:
        fallback_pool = sorted(set(candidates) - selected_ids)
        if remaining_count > len(fallback_pool):
            raise ValueError(
                f"Only {len(candidates):,} unique cards satisfy the filters; "
                f"{unique_target:,} are required. Increase --duplicate-rate "
                "or reduce --rows."
            )
        fill_ids = rng.sample(fallback_pool, remaining_count)
        selected_cards.extend(candidates[oracle_id] for oracle_id in fill_ids)

    return selected_cards


def build_invalid_rows(
    count: int,
    selected_cards: Sequence[CardCandidate],
) -> list[dict[str, str | int]]:
    invalid_rows: list[dict[str, str | int]] = []
    real_name = selected_cards[0].name

    for index in range(count):
        scenario = index % 6
        if scenario == 0:
            row = {
                "name": f"Definitely Not a Real Card {index + 1}",
                "count": 1,
            }
        elif scenario == 1:
            row = {"name": "", "count": 1}
        elif scenario == 2:
            row = {"name": real_name, "count": ""}
        elif scenario == 3:
            row = {"name": real_name, "count": "many"}
        elif scenario == 4:
            row = {"name": real_name, "count": 0}
        else:
            row = {"name": real_name, "count": -1}
        invalid_rows.append(row)

    return invalid_rows


def generate_collection(
    candidates: dict[str, CardCandidate],
    commander_ids: Sequence[str],
    available_themes: set[str],
    config: GenerationConfig,
) -> GenerationResult:
    validate_config(config, available_themes)
    filtered_candidates = filter_candidates(candidates, config.colors)
    rng = random.Random(config.seed)

    invalid_count = int(config.rows * config.invalid_rate)
    valid_count = config.rows - invalid_count
    duplicate_count = int(valid_count * config.duplicate_rate)
    unique_target = valid_count - duplicate_count
    if unique_target < 1:
        raise ValueError(
            "The selected rates leave no unique valid rows to generate."
        )

    selected_cards = select_cards(
        filtered_candidates,
        commander_ids,
        unique_target,
        config,
        rng,
    )
    valid_rows: list[dict[str, str | int]] = [
        {
            "name": candidate.name,
            "count": rng.randint(
                config.min_quantity,
                config.max_quantity,
            ),
        }
        for candidate in selected_cards
    ]

    for _ in range(duplicate_count):
        candidate = rng.choice(selected_cards)
        valid_rows.append(
            {
                "name": candidate.name,
                "count": rng.randint(
                    config.min_quantity,
                    config.max_quantity,
                ),
            }
        )

    rows = valid_rows + build_invalid_rows(invalid_count, selected_cards)
    rng.shuffle(rows)
    themed_cards = sum(
        bool(candidate.themes.intersection(config.themes))
        for candidate in selected_cards
    )

    return GenerationResult(
        rows=rows,
        selected_cards=tuple(selected_cards),
        duplicate_rows=duplicate_count,
        invalid_rows=invalid_count,
        themed_cards=themed_cards,
        valid_quantity=sum(int(row["count"]) for row in valid_rows),
    )


def write_csv(
    output_path: Path,
    rows: Sequence[dict[str, str | int]],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def normalize_themes(themes: Sequence[str]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            theme.strip().casefold().replace("-", "_").replace(" ", "_")
            for theme in themes
            if theme.strip()
        )
    )


def parse_colors(values: Sequence[str] | None) -> frozenset[str] | None:
    if values is None:
        return None

    tokens = "".join(values).replace(",", "").upper()
    tokens = tokens.replace("COLORLESS", "C")
    unknown_colors = sorted(set(tokens) - VALID_COLORS - {"C"})
    if unknown_colors:
        raise ValueError(
            "Unknown color code(s): " + ", ".join(unknown_colors)
        )
    return frozenset(set(tokens).intersection(VALID_COLORS))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a randomized collection CSV using current processed "
            "card data."
        )
    )
    parser.add_argument(
        "--profile",
        choices=tuple(PROFILE_DEFAULTS),
        default="showcase",
        help="Preset defaults: showcase, random, boundary, or warnings.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output CSV path; relative paths resolve from the project root.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--rows", type=int)
    parser.add_argument(
        "--themes",
        nargs="+",
        help="Themes to concentrate, such as graveyard tokens.",
    )
    parser.add_argument(
        "--theme-ratio",
        type=float,
        help="Minimum share of unique cards matching a selected theme.",
    )
    parser.add_argument(
        "--colors",
        nargs="+",
        help="Constrain color identity with WUBRG codes; use C for colorless.",
    )
    parser.add_argument("--commander-count", type=int)
    parser.add_argument(
        "--duplicate-rate",
        type=float,
        help="Share of valid physical rows that repeat selected card names.",
    )
    parser.add_argument(
        "--invalid-rate",
        type=float,
        help="Share of rows containing deliberate parser errors/warnings.",
    )
    parser.add_argument("--min-quantity", type=int, default=1)
    parser.add_argument("--max-quantity", type=int, default=4)
    return parser


def config_from_args(args: argparse.Namespace) -> GenerationConfig:
    defaults = PROFILE_DEFAULTS[args.profile]
    rows = args.rows if args.rows is not None else defaults["rows"]
    duplicate_rate = (
        args.duplicate_rate
        if args.duplicate_rate is not None
        else defaults["duplicate_rate"]
    )
    invalid_rate = (
        args.invalid_rate
        if args.invalid_rate is not None
        else defaults["invalid_rate"]
    )
    valid_rows = rows - int(rows * invalid_rate)
    unique_rows = valid_rows - int(valid_rows * duplicate_rate)
    commander_count = (
        args.commander_count
        if args.commander_count is not None
        else min(defaults["commander_count"], max(0, unique_rows))
    )
    themes = (
        normalize_themes(args.themes)
        if args.themes is not None
        else defaults["themes"]
    )
    return GenerationConfig(
        rows=rows,
        themes=themes,
        theme_ratio=(
            args.theme_ratio
            if args.theme_ratio is not None
            else defaults["theme_ratio"]
        ),
        colors=parse_colors(args.colors),
        commander_count=commander_count,
        duplicate_rate=duplicate_rate,
        invalid_rate=invalid_rate,
        min_quantity=args.min_quantity,
        max_quantity=args.max_quantity,
        seed=args.seed,
    )


def resolve_output_path(output_path: Path) -> Path:
    if output_path.is_absolute():
        return output_path
    return PROJECT_ROOT / output_path


def print_summary(
    output_path: Path,
    result: GenerationResult,
    config: GenerationConfig,
    skipped_cards: int,
) -> None:
    valid_rows = len(result.rows) - result.invalid_rows
    print(f"Wrote {len(result.rows):,} rows to {output_path}")
    print(
        f"Valid rows: {valid_rows:,}; unique cards: "
        f"{len(result.selected_cards):,}; duplicate rows: "
        f"{result.duplicate_rows:,}; invalid rows: {result.invalid_rows:,}"
    )
    print(f"Valid quantity total: {result.valid_quantity:,}")
    if config.themes:
        concentration = result.themed_cards / len(result.selected_cards)
        print(
            f"Theme concentration ({', '.join(config.themes)}): "
            f"{result.themed_cards:,}/{len(result.selected_cards):,} "
            f"({concentration:.1%})"
        )
    print(
        f"Excluded {skipped_cards:,} non-canonical name collisions or "
        "incomplete card records."
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        config = config_from_args(args)
        theme_to_card_ids = get_theme_to_card_ids()
        candidates, skipped_cards = build_candidates(
            get_cards_by_id(),
            get_name_to_id(),
            theme_to_card_ids,
        )
        result = generate_collection(
            candidates,
            get_commanders(),
            set(theme_to_card_ids),
            config,
        )
    except ValueError as error:
        parser.error(str(error))

    output_path = resolve_output_path(args.output)
    write_csv(output_path, result.rows)
    print_summary(output_path, result, config, skipped_cards)


if __name__ == "__main__":
    main()
