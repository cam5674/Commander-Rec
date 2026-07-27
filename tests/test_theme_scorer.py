import unittest

from backend.theme_scorer import (
    calculate_color_compatibility_ratio,
    calculate_color_identity_counts,
    calculate_theme_scores,
    get_commander_candidates,
    normalize_color_identity,
    rank_commanders,
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



    def test_color_ratio_uses_unique_compatible_cards(self) -> None:
        commander = {
            "oracle_id": "oracle-token-maker",
            "color_identity": ["W", "G"],
        }

        average = calculate_color_compatibility_ratio(
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

        average = calculate_color_compatibility_ratio(
            commander,
            self.collection,
            self.cards_by_id,
        )

        self.assertEqual(average, 1.0)

    def test_color_ratio_returns_zero_without_evaluable_cards(self) -> None:
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

        average = calculate_color_compatibility_ratio(
            commander,
            collection,
            cards_by_id,
        )

        self.assertEqual(average, 0.0)

    def test_color_ratio_ignores_unrelated_theme_cards(self) -> None:
        commander = {
            "oracle_id": "oracle-green-commander",
            "color_identity": ["G"],
        }
        collection = {
            "oracle-green-token": 1,
            "oracle-black-graveyard": 1,
        }
        cards_by_id = {
            "oracle-green-token": {
                "color_identity": ["G"],
                "themes": ["tokens"],
            },
            "oracle-black-graveyard": {
                "color_identity": ["B"],
                "themes": ["graveyard"],
            },
        }

        ratio = calculate_color_compatibility_ratio(
            commander,
            collection,
            cards_by_id,
            relevant_themes=["tokens"],
        )

        self.assertEqual(ratio, 1.0)


class CommanderRankingTests(unittest.TestCase):
    def test_pairing_commanders_are_excluded_from_mvp_candidates(self) -> None:
        def make_commander(
            name: str,
            *,
            keywords: list[str] | None = None,
            type_line: str = "Legendary Creature — Human",
        ) -> dict:
            return {
                "name": name,
                "commander_eligible": True,
                "themes": ["tokens"],
                "keywords": keywords or [],
                "type_line": type_line,
                "edhrec_rank": None,
                "color_identity": ["W"],
            }

        cards_by_id = {
            "oracle-standalone": make_commander("Standalone Commander"),
            "oracle-partner": make_commander(
                "Partner Commander",
                keywords=["Partner"],
            ),
            "oracle-partner-with": make_commander(
                "Partner With Commander",
                keywords=["Partner with"],
            ),
            "oracle-background-choice": make_commander(
                "Background Commander",
                keywords=["Choose a background"],
            ),
            "oracle-doctor": make_commander(
                "Doctor Companion",
                keywords=["Doctor's companion"],
            ),
            "oracle-friends": make_commander(
                "Friends Forever Commander",
                keywords=["Friends forever"],
            ),
            "oracle-background": make_commander(
                "Legendary Background",
                type_line="Legendary Enchantment — Background",
            ),
        }
        collection = {
            oracle_id: 1
            for oracle_id in cards_by_id
        }

        candidates = get_commander_candidates(
            collection,
            cards_by_id,
            ["tokens"],
        )

        self.assertEqual(
            [candidate["name"] for candidate in candidates],
            ["Standalone Commander"],
        )

    def test_theme_fit_outweighs_five_color_compatibility(self) -> None:
        collection = {
            "oracle-green-support": 1,
            "oracle-white-support": 1,
        }
        cards_by_id = {
            "oracle-green-support": {
                "color_identity": ["G"],
                "themes": ["tokens", "artifacts"],
            },
            "oracle-white-support": {
                "color_identity": ["W"],
                "themes": ["tokens"],
            },
        }
        candidates = [
            {
                "oracle_id": "oracle-theme-focused",
                "name": "Theme Focused",
                "matching_themes": ["tokens", "artifacts"],
                "edhrec_rank": None,
                "color_identity": ["R"],
            },
            {
                "oracle_id": "oracle-five-color",
                "name": "Five Color",
                "matching_themes": ["tokens"],
                "edhrec_rank": None,
                "color_identity": ["W", "U", "B", "R", "G"],
            },
        ]

        ranked = rank_commanders(
            candidates,
            {"tokens": 10, "artifacts": 8},
            ["tokens", "artifacts"],
            collection,
            cards_by_id,
        )

        self.assertEqual(ranked[0]["name"], "Theme Focused")
        self.assertEqual(ranked[0]["theme_ratio"], 1.0)
        self.assertEqual(ranked[0]["color_ratio"], 0.0)
        self.assertEqual(ranked[0]["final_score"], 0.75)

    def test_color_ratio_breaks_equal_theme_fit(self) -> None:
        collection = {
            "oracle-green-support": 1,
            "oracle-colorless-support": 1,
        }
        cards_by_id = {
            "oracle-green-support": {
                "color_identity": ["G"],
                "themes": ["tokens"],
            },
            "oracle-colorless-support": {
                "color_identity": [],
                "themes": ["tokens"],
            },
        }
        candidates = [
            {
                "oracle_id": "oracle-black-commander",
                "name": "Black Commander",
                "matching_themes": ["tokens"],
                "edhrec_rank": None,
                "color_identity": ["B"],
            },
            {
                "oracle_id": "oracle-green-commander",
                "name": "Green Commander",
                "matching_themes": ["tokens"],
                "edhrec_rank": None,
                "color_identity": ["G"],
            },
        ]

        ranked = rank_commanders(
            candidates,
            {"tokens": 10},
            ["tokens"],
            collection,
            cards_by_id,
        )

        self.assertEqual(
            [commander["name"] for commander in ranked],
            ["Green Commander", "Black Commander"],
        )

    def test_popularity_breaks_equal_theme_and_color_fit(self) -> None:
        collection = {"oracle-green-support": 1}
        cards_by_id = {
            "oracle-green-support": {
                "color_identity": ["G"],
                "themes": ["tokens"],
            },
        }
        candidates = [
            {
                "oracle_id": "oracle-unranked",
                "name": "Unranked Commander",
                "matching_themes": ["tokens"],
                "edhrec_rank": None,
                "color_identity": ["G"],
            },
            {
                "oracle_id": "oracle-popular",
                "name": "Popular Commander",
                "matching_themes": ["tokens"],
                "edhrec_rank": 100,
                "color_identity": ["G"],
            },
        ]

        ranked = rank_commanders(
            candidates,
            {"tokens": 10},
            ["tokens"],
            collection,
            cards_by_id,
        )

        self.assertEqual(
            [commander["name"] for commander in ranked],
            ["Popular Commander", "Unranked Commander"],
        )


if __name__ == "__main__":
    unittest.main()
