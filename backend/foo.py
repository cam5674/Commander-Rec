import requests


HEADERS = {
    "User-Agent": "MTGCommanderRecommender/0.1"
}

URL = "https://api.scryfall.com/cards/search"

params = {
    "q": "is:commander id=grixis",
    "order": "cmc",
}



response = requests.get(URL, params=params, headers=HEADERS, timeout=10)

response.raise_for_status()


result = response.json()


for card in result["data"]:
    if card["cmc"] == 7:
        print ((card["name"]))



