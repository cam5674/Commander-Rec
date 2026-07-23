import unittest

from backend.theme_scorer import calculate_theme_scores


class ThemeScorerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.collection = {
            "oracle-token-maker": 4,
            "oracle-graveyard-card": 1,
            "oracle-artifact-engine": 2,
            "oracle-untagged-card": 1,
            "oracle-missing-card": 1,
        }
        self.cards_by_id = {
            "oracle-token-maker": {
                "name": "Test Token Maker",
                "type_line": "Creature — Wizard",
                "oracle_text": "Create a 1/1 creature token.",
                "keywords": [],
                "themes": ["tokens", "reanimator"],
            },
            "oracle-graveyard-card": {
                "name": "Test Reanimator",
                "type_line": "Sorcery",
                "oracle_text": (
                    "Return target creature card from your graveyard "
                    "to the battlefield."
                ),
                "keywords": [],
                "themes": ["graveyard", "reanimator"],
            },
            "oracle-artifact-engine": {
                "name": "Test Artifact Engine",
                "type_line": "Artifact",
                "oracle_text": (
                    "Whenever you sacrifice an artifact, draw a card."
                ),
                "keywords": [],
                "themes": [
                    "artifacts",
                    "sacrifice",
                    "card_draw",
                ],
            },
            "oracle-untagged-card": {
                "name": "Test Vanilla Creature",
                "type_line": "Creature — Bear",
                "oracle_text": "",
                "keywords": [],
                "themes": [],
            },
        }

    def test_counts_each_owned_card_once_per_theme(self) -> None:
        scores = calculate_theme_scores(
            self.collection,
            self.cards_by_id,
        )

        self.assertEqual(
            scores,
            {
                "tokens": 1,
                "graveyard": 1,
                "reanimator": 2,
                "artifacts": 1,
                "sacrifice": 1,
                "card_draw": 1,
            },
        )

    def test_empty_collection_returns_empty_scores(self) -> None:
        scores = calculate_theme_scores({}, self.cards_by_id)

        self.assertEqual(scores, {})

    def test_multiple_themes(self) -> None:
        self.collection["oracle-all-themes"] = 1
        self.cards_by_id["oracle-graveyard-card"]["themes"] = [
            "graveyard",
            "reanimator",
            "aristocrats",
            "card_draw",
        ]
        self.cards_by_id["oracle-all-themes"] = {
            "themes": [
                "wheels",
                "aristocrats",
                "lands",
                "card_draw",
                "spellslinger",
                "plus_one_counters",
                "lifegain",
                "artifacts",
                "tokens",
                "sacrifice",
                "graveyard",
                "reanimator",
            ]
        }

        scores = calculate_theme_scores(
            self.collection,
            self.cards_by_id,
        )

        self.assertEqual(
            scores,
            {
                "tokens": 2,
                "graveyard": 2,
                "reanimator": 3,
                "artifacts": 2,
                "sacrifice": 2,
                "lifegain": 1,
                "plus_one_counters": 1,
                "spellslinger": 1,
                "aristocrats": 2,
                "wheels": 1,
                "card_draw": 3,
                "lands": 1,
            },
        )

    def test_card_with_no_theme(self) -> None:
        self.collection["oracle-no_theme"] = 3
        self.cards_by_id["oracle-no_theme"] = {
            "themes": [],
        }

        scores = calculate_theme_scores(self.collection, self.cards_by_id)

        self.assertEqual(
            scores,
            {
                "tokens": 1,
                "graveyard": 1,
                "reanimator": 2,
                "artifacts": 1,
                "sacrifice": 1,
                "card_draw": 1,
            },
        )

    def test_empty_collection_and_cards_by_id(self) -> None:
        collection, cards_by_id = {}, {}

        scores = calculate_theme_scores(collection, cards_by_id)

        self.assertEqual(scores, {})

if __name__ == "__main__":
    unittest.main()
