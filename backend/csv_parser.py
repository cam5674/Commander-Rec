import csv
from collections import defaultdict
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import TextIO

from .data_loader import load_name_to_id
from scripts.process_scryfall import normalize_lookup_name


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "raw" / "test_collection.csv"
NAME_TO_ID_PATH = PROJECT_ROOT / "data" / "processed" / "name_to_id.json"
NAME_HEADER_ALIASES = ("name", "card name")
QUANTITY_HEADER_ALIASES = ("count", "quantity", "qty")


class CSVRowLimitError(ValueError):
    """Indicate that a CSV contains more data rows than allowed."""


@dataclass(frozen=True)
class CSVWarning:
    """Describe a recoverable CSV row validation problem."""

    code: str
    message: str
    row: int
    value: str | None = None


@dataclass
class CollectionParseResult:
    """Contain parsed cards, unmatched names, and row warnings."""

    collection: dict[str, int]
    unmatched_names: list[str] = field(default_factory=list)
    warnings: list[CSVWarning] = field(default_factory=list)


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


def parse_collection_stream(
    csv_file: TextIO,
    name_to_id: dict[str, str],
    row_limit: int | None = None,
) -> CollectionParseResult:
    collection: defaultdict[str, int] = defaultdict(int)
    unmatched_names: list[str] = []
    warnings: list[CSVWarning] = []

    reader = csv.DictReader(csv_file)
    name_column, quantity_column = resolve_csv_columns(reader.fieldnames)

    for row_number, row in enumerate(reader, start=2):
        if row_limit is not None and row_number > row_limit + 1:
            raise CSVRowLimitError(
                f"Collection CSV exceeds the {row_limit:,}-row limit."
            )

        quantity_text = (row.get(quantity_column) or "").strip()
        name = (row.get(name_column) or "").strip()

        if not name:
            warnings.append(
                CSVWarning(
                    code="MISSING_CARD_NAME",
                    message="Card name is missing.",
                    row=row_number,
                )
            )
            continue

        try:
            quantity = int(quantity_text)
        except ValueError:
            warnings.append(
                CSVWarning(
                    code="INVALID_QUANTITY",
                    message="Quantity must be a whole number.",
                    row=row_number,
                    value=quantity_text,
                )
            )
            continue

        if quantity <= 0:
            warnings.append(
                CSVWarning(
                    code="NON_POSITIVE_QUANTITY",
                    message="Quantity must be greater than zero.",
                    row=row_number,
                    value=quantity_text,
                )
            )
            continue

        normalized_name = normalize_lookup_name(name)
        oracle_id = name_to_id.get(normalized_name)

        if oracle_id is None:
            unmatched_names.append(name)
            continue

        collection[oracle_id] += quantity

    return CollectionParseResult(
        collection=dict(collection),
        unmatched_names=unmatched_names,
        warnings=warnings,
    )


def parse_collection(
    csv_path: Path,
    name_to_id: dict[str, str],
    row_limit: int | None = None,
) -> CollectionParseResult:
    with csv_path.open(
        mode="r",
        newline="",
        encoding="utf-8-sig",
    ) as csv_file:
        return parse_collection_stream(
            csv_file,
            name_to_id,
            row_limit=row_limit,
        )


def parse_collection_bytes(
    csv_data: bytes,
    name_to_id: dict[str, str],
    row_limit: int | None = None,
) -> CollectionParseResult:
    try:
        csv_text = csv_data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError(
            "The collection CSV must use UTF-8 encoding."
        ) from error

    return parse_collection_stream(
        StringIO(csv_text, newline=""),
        name_to_id,
        row_limit=row_limit,
    )


def main() -> None:
    name_to_id = load_name_to_id(NAME_TO_ID_PATH)
    parse_result = parse_collection(
        CSV_PATH,
        name_to_id,
        row_limit=20_000,  # Remove this argument after testing.
    )

    print(parse_result.collection)

    if parse_result.unmatched_names:
        print("\nUnmatched card names:")
        for name in parse_result.unmatched_names:
            print(f"- {name}")

    if parse_result.warnings:
        print("\nWarnings:")
        for warning in parse_result.warnings:
            print(f"- Row {warning.row}: {warning.message}")


if __name__ == "__main__":
    main()
