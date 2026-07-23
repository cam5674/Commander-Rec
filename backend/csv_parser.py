import csv
from collections import defaultdict
from pathlib import Path
from .data_loader import load_name_to_id
from scripts.process_scryfall import normalize_lookup_name


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "raw" / "test_collection.csv"
NAME_TO_ID_PATH = PROJECT_ROOT / "data" / "processed" / "name_to_id.json"
NAME_HEADER_ALIASES = ("name", "card name")
QUANTITY_HEADER_ALIASES = ("count", "quantity", "qty")


def resolve_csv_columns(fieldnames: list[str] | None) -> tuple[str, str]:
    if not fieldnames:
        raise ValueError("The collection CSV is empty.")

    normalized_headers = {
        header.strip().casefold(): header
        for header in fieldnames
        if header
    }
    name_column = next(
        (
            normalized_headers[alias]
            for alias in NAME_HEADER_ALIASES
            if alias in normalized_headers
        ),
        None,
    )
    quantity_column = next(
        (
            normalized_headers[alias]
            for alias in QUANTITY_HEADER_ALIASES
            if alias in normalized_headers
        ),
        None,
    )

    if name_column is None or quantity_column is None:
        detected_headers = ", ".join(fieldnames)
        raise ValueError(
            "Unsupported CSV format. Expected a card-name column "
            f"({', '.join(NAME_HEADER_ALIASES)}) and a quantity column "
            f"({', '.join(QUANTITY_HEADER_ALIASES)}). "
            f"Detected headers: {detected_headers}"
        )

    return name_column, quantity_column


def parse_collection(
    csv_path: Path,
    name_to_id: dict[str, str],
    row_limit: int | None = None,
) -> tuple[dict[str, int], list[str]]:
    collection: defaultdict[str, int] = defaultdict(int)
    unmatched_names: list[str] = []

    with csv_path.open(
        mode="r",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        reader = csv.DictReader(file)
        name_column, quantity_column = resolve_csv_columns(reader.fieldnames)

        for row_number, row in enumerate(reader, start=2):
            if row_limit is not None and row_number > row_limit + 1:
                break

            quantity_text = (row.get(quantity_column) or "").strip()
            name = (row.get(name_column) or "").strip()

            if not name:
                print(f"Skipping row {row_number}: card name is missing.")
                continue

            try:
                quantity = int(quantity_text)
            except ValueError:
                print(
                    f"Skipping row {row_number}: "
                    f"invalid quantity {quantity_text!r}."
                )
                continue

            if quantity <= 0:
                print(
                    f"Skipping row {row_number}: "
                    "quantity must be greater than zero."
                )
                continue

            normalized_name = normalize_lookup_name(name)
            oracle_id = name_to_id.get(normalized_name)

            if oracle_id is None:
                unmatched_names.append(name)
                continue

            collection[oracle_id] += quantity

    return dict(collection), unmatched_names


def main() -> None:
    name_to_id = load_name_to_id(NAME_TO_ID_PATH)
    collection, unmatched_names = parse_collection(
        CSV_PATH,
        name_to_id,
        row_limit=20_000,  # Remove this argument after testing.
    )

    print(collection)

    if unmatched_names:
        print("\nUnmatched card names:")
        for name in unmatched_names:
            print(f"- {name}")


if __name__ == "__main__":
    main()
