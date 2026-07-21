import csv
import json
from collections import defaultdict
from pathlib import Path
from process_scryfall import normalize_lookup_name


collection = defaultdict(int)
CSV_PATH = Path("../data/raw/test_collection.csv")
NAME_TO_ID_PATH = Path("../data/processed/name_to_id.json")



def load_name_to_id(path: Path) -> dict[str, str]:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as error:
        raise RuntimeError(
            f"Name lookup file was not found: {path}"
        ) from error
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Name lookup file contains invalid JSON: {path}"
        ) from error


def parse_collection( csv_path: Path, name_to_id: dict[str, str], 
                     row_limit: int | None = None,
) -> tuple[dict[str, int], list[str]]:
    collection: defaultdict[str, int] = defaultdict(int)
    unmatched_names: list[str] = []

    with csv_path.open(
        mode="r",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        reader = csv.reader(file)

        try:
            header = next(reader)
        except StopIteration:
            raise ValueError("The collection CSV is empty.")

        for row_number, row in enumerate(reader, start=2):
            if row_limit is not None and row_number > row_limit + 1:
                break

            if len(row) < 3:
                print(f"Skipping row {row_number}: not enough columns.")
                continue

            quantity_text = row[0].strip()
            name = row[2].strip()

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


name_to_id = load_name_to_id(NAME_TO_ID_PATH)

collection, unmatched_names = parse_collection(
    CSV_PATH,
    name_to_id,
    row_limit=20000,  # Remove this argument after testing.
)

print(collection)

if unmatched_names:
    print("\nUnmatched card names:")
    for name in unmatched_names:
        print(f"- {name}")