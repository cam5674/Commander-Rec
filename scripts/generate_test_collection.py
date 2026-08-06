"""
Generates a synthetic but structurally realistic 20,000-row collection CSV
for Phase 0 measurement 2, matching Moxfield's real export column schema:

    Count, Tradelist Count, Name, Edition, Condition, Language, Foil, Tags,
    Last Modified, Collector Number, Alter, Proxy, Purchase Price

Card names are sampled from the app's own data/processed/name_to_id.json,
so they are real cards that will actually resolve through csv_parser.py --
this measures upload size AND exercises the real parse path, not just the
reject-as-unmatched path a fully-random name list would hit.

Run from the repository root:
    pip install faker --break-system-packages
    python scripts/generate_test_collection.py
"""

import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

fake = Faker()
random.seed(42)  # reproducible fixture

ROW_COUNT = 20_000
OUTPUT_PATH = Path("data/raw/test_collection_realistic.csv")
NAME_TO_ID_PATH = Path("data/processed/name_to_id.json")

# Rough real-world distributions -- tune these if a genuine export sample
# later shows different proportions.
CONDITIONS = ["Near Mint", "Lightly Played", "Moderately Played",
              "Heavily Played", "Damaged"]
CONDITION_WEIGHTS = [0.55, 0.25, 0.12, 0.06, 0.02]
LANGUAGES = ["English", "Japanese", "German", "Spanish"]
LANGUAGE_WEIGHTS = [0.90, 0.05, 0.03, 0.02]
FOIL_VALUES = ["", "foil", "etched"]
FOIL_WEIGHTS = [0.80, 0.18, 0.02]

# Placeholder set codes -- swap for real ones sampled from cards_by_id.json
# if exact edition-name length matters for the measurement.
SET_CODES = ["MH3", "LTR", "ONE", "BRO", "DMU", "SNC", "NEO", "VOW",
             "MID", "AFR", "STX", "KHM", "ZNR", "M21", "IKO"]


def load_card_names(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as f:
        name_to_id = json.load(f)
    # name_to_id.json includes normalized keys and face names; card records
    # in the app keep the original display name, but for a byte-size and
    # parse-path measurement the normalized keys are close enough. Swap in
    # cards_by_id.json's display-name field instead if exact casing matters.
    return list(name_to_id.keys())


def random_date_within(days_back: int = 900) -> str:
    d = datetime.now() - timedelta(days=random.randint(0, days_back))
    return d.strftime("%Y-%m-%d")


def generate_row(card_names: list[str]) -> dict:
    name = random.choice(card_names)
    return {
        "Count": random.randint(1, 4),
        "Tradelist Count": random.randint(0, 2),
        "Name": name,
        "Edition": random.choice(SET_CODES),
        "Condition": random.choices(CONDITIONS, weights=CONDITION_WEIGHTS)[0],
        "Language": random.choices(LANGUAGES, weights=LANGUAGE_WEIGHTS)[0],
        "Foil": random.choices(FOIL_VALUES, weights=FOIL_WEIGHTS)[0],
        "Tags": fake.word() if random.random() < 0.15 else "",
        "Last Modified": random_date_within(),
        "Collector Number": str(random.randint(1, 350)),
        "Alter": "",
        "Proxy": "",
        "Purchase Price": f"{random.uniform(0.10, 45.00):.2f}"
                           if random.random() < 0.6 else "",
    }


def main():
    card_names = load_card_names(NAME_TO_ID_PATH)
    fieldnames = ["Count", "Tradelist Count", "Name", "Edition", "Condition",
                  "Language", "Foil", "Tags", "Last Modified",
                  "Collector Number", "Alter", "Proxy", "Purchase Price"]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for _ in range(ROW_COUNT):
            writer.writerow(generate_row(card_names))

    size_bytes = OUTPUT_PATH.stat().st_size
    print(f"Wrote {ROW_COUNT} rows to {OUTPUT_PATH}")
    print(f"Size: {size_bytes:,} bytes ({size_bytes / 1_048_576:.2f} MiB)")
    print(f"Bytes/row: {size_bytes / ROW_COUNT:.1f}")


if __name__ == "__main__":
    main()
