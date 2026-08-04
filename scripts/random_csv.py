import json
import csv
from pathlib import Path
import random
from backend.data_loader import (
    get_cards_by_id,
    get_commanders,
    get_name_to_id,
    get_theme_to_card_ids,
)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "data" / "raw" / "random_csv.csv"
THEMES_PATH = PROJECT_ROOT / "data" / "processed" / "theme_to_card_ids.json"
FIELDNAMES = ["name", "count"]





collection = {}


theme_cards = get_theme_to_card_ids()
cards_by_id = get_cards_by_id()
commanders = get_commanders()



with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8') as csv_file:
     
    writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)

    writer.writeheader() 

    for theme in theme_cards :
        collection[theme] = random.sample(list(theme_cards[theme]), 100)


    collection["commanders"] = random.sample(commanders,10)


    for card_list in collection.values():
        for oracle_id in card_list:
            card = cards_by_id.get(oracle_id)
            if card is None:
                continue

            writer.writerow({
                "name": card["name"],
                "count": 1,
            })

