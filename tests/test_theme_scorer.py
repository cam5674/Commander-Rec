import unittest

from backend.theme_scorer import (
    calculate_color_average,
    calculate_color_identity_counts,
    calculate_theme_scores,
    normalize_color_identity,
)


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
                "color_identity": ["W", "G"],
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
                "color_identity": ["B"],
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
                "color_identity": [],
            },
            "oracle-untagged-card": {
                "name": "Test Vanilla Creature",
                "type_line": "Creature — Bear",
                "oracle_text": "",
                "keywords": [],
                "themes": [],
                "color_identity": ["G"],
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

    def test_color_identity_count(self)-> None:
 
        count = calculate_color_identity_counts(self.collection, self.cards_by_id)

        self.assertEqual(
            count,
            {
                "B": 1,
                "WG": 1,
                "G": 1,
                "":1,
            }
            )

    def test_normalizes_color_identity_order(self) -> None:
        self.assertEqual(
            normalize_color_identity(["G", "W", "G"]),
            "WG",
        )



    def test_color_average_uses_unique_compatible_cards(self) -> None:
        commander = {
            "oracle_id": "oracle-token-maker",
            "color_identity": ["W", "G"],
        }

        average = calculate_color_average(
            commander,
            self.collection,
            self.cards_by_id,
        )

        self.assertEqual(average, 2 / 3)

    def test_five_color_commander_accepts_every_color_identity(self) -> None:
        commander = {
            "oracle_id": "oracle-five-color-commander",
            "color_identity": ["W", "U", "B", "R", "G"],
        }

        average = calculate_color_average(
            commander,
            self.collection,
            self.cards_by_id,
        )

        self.assertEqual(average, 1.0)

    def test_color_average_returns_zero_without_evaluable_cards(self) -> None:
        commander = {
            "oracle_id": "oracle-only-commander",
            "color_identity": ["G"],
        }
        collection = {
            "oracle-only-commander": 1,
            "oracle-missing-card": 1,
        }
        cards_by_id = {
            "oracle-only-commander": {
                "color_identity": ["G"],
            },
        }

        average = calculate_color_average(
            commander,
            collection,
            cards_by_id,
        )

        self.assertEqual(average, 0.0)


if __name__ == "__main__":
    unittest.main()
