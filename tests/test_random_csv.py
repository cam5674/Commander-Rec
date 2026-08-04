import tempfile
import unittest
from pathlib import Path

from backend.csv_parser import parse_collection
from scripts.process_scryfall import normalize_lookup_name
from scripts.random_csv import (
    GenerationConfig,
    build_candidates,
    build_parser,
    config_from_args,
    generate_collection,
    write_csv,
)


class RandomCSVTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.output_path = (
            Path(self.temporary_directory.name) / "collection.csv"
        )

        definitions = [
            ("g1", "Grave One", ["B"], ["graveyard"]),
            ("g2", "Grave Two", ["B"], ["graveyard"]),
            ("g3", "Grave Three", ["G"], ["graveyard"]),
            ("g4", "Grave Four", ["B", "G"], ["graveyard"]),
            ("t1", "Token One", ["W"], ["tokens"]),
            ("t2", "Token Two", ["G"], ["tokens"]),
            ("b1", "Both Themes", ["B"], ["graveyard", "tokens"]),
            ("n1", "Neutral One", ["B"], []),
            ("n2", "Neutral Two", [], []),
            ("n3", "Neutral Three", ["U"], []),
            ("n4", "Neutral Four", ["R"], []),
            ("n5", "Neutral Five", ["W"], []),
            ("n6", "Æther Adept", ["G"], []),
        ]
        self.cards_by_id = {
            oracle_id: {
                "name": name,
                "color_identity": colors,
            }
            for oracle_id, name, colors, _ in definitions
        }
        self.cards_by_id["token-g1"] = {
            "name": "Grave One",
            "color_identity": ["B"],
        }
        self.name_to_id = {
            normalize_lookup_name(name): oracle_id
            for oracle_id, name, _, _ in definitions
        }
        self.theme_to_card_ids = {
            theme: [
                oracle_id
                for oracle_id, _, _, themes in definitions
                if theme in themes
            ]
            for theme in ("graveyard", "tokens")
        }
        self.candidates, self.skipped_cards = build_candidates(
            self.cards_by_id,
            self.name_to_id,
            self.theme_to_card_ids,
        )

    def config(self, **overrides: object) -> GenerationConfig:
        values = {
            "rows": 10,
            "themes": ("graveyard", "tokens"),
            "theme_ratio": 0.5,
            "colors": None,
            "commander_count": 1,
            "duplicate_rate": 0.2,
            "invalid_rate": 0.0,
            "min_quantity": 1,
            "max_quantity": 1,
            "seed": 42,
        }
        values.update(overrides)
        return GenerationConfig(**values)

    def test_generated_csv_round_trips_and_combines_duplicates(self) -> None:
        result = generate_collection(
            self.candidates,
            ["n1", "g1"],
            set(self.theme_to_card_ids),
            self.config(),
        )
        write_csv(self.output_path, result.rows)

        parsed = parse_collection(self.output_path, self.name_to_id)

        self.assertEqual(len(result.rows), 10)
        self.assertEqual(len(result.selected_cards), 8)
        self.assertEqual(result.duplicate_rows, 2)
        self.assertGreaterEqual(result.themed_cards, 4)
        self.assertEqual(len(parsed.collection), 8)
        self.assertEqual(sum(parsed.collection.values()), 10)
        self.assertTrue(
            any(quantity > 1 for quantity in parsed.collection.values())
        )
        self.assertEqual(parsed.unmatched_names, [])
        self.assertEqual(parsed.warnings, [])

    def test_noncanonical_name_collision_is_excluded(self) -> None:
        self.assertIn("g1", self.candidates)
        self.assertNotIn("token-g1", self.candidates)
        self.assertEqual(self.skipped_cards, 1)

    def test_warning_profile_exercises_all_invalid_row_types(self) -> None:
        result = generate_collection(
            self.candidates,
            [],
            set(self.theme_to_card_ids),
            self.config(
                rows=12,
                themes=(),
                theme_ratio=0.0,
                commander_count=0,
                duplicate_rate=0.0,
                invalid_rate=0.5,
            ),
        )
        write_csv(self.output_path, result.rows)

        parsed = parse_collection(self.output_path, self.name_to_id)

        self.assertEqual(len(result.rows), 12)
        self.assertEqual(result.invalid_rows, 6)
        self.assertEqual(len(parsed.collection), 6)
        self.assertEqual(len(parsed.unmatched_names), 1)
        self.assertCountEqual(
            [warning.code for warning in parsed.warnings],
            [
                "MISSING_CARD_NAME",
                "INVALID_QUANTITY",
                "INVALID_QUANTITY",
                "NON_POSITIVE_QUANTITY",
                "NON_POSITIVE_QUANTITY",
            ],
        )

    def test_color_filter_limits_selected_color_identities(self) -> None:
        result = generate_collection(
            self.candidates,
            [],
            set(self.theme_to_card_ids),
            self.config(
                rows=3,
                themes=(),
                theme_ratio=0.0,
                colors=frozenset({"B"}),
                commander_count=0,
                duplicate_rate=0.0,
            ),
        )

        self.assertTrue(
            all(
                card.color_identity.issubset({"B"})
                for card in result.selected_cards
            )
        )

    def test_same_seed_produces_identical_rows(self) -> None:
        first = generate_collection(
            self.candidates,
            ["n1", "g1"],
            set(self.theme_to_card_ids),
            self.config(),
        )
        second = generate_collection(
            dict(reversed(tuple(self.candidates.items()))),
            ["n1", "g1"],
            set(self.theme_to_card_ids),
            self.config(),
        )

        self.assertEqual(first.rows, second.rows)

    def test_profiles_and_small_row_overrides_are_parameterized(self) -> None:
        parser = build_parser()
        boundary_config = config_from_args(
            parser.parse_args(["--profile", "boundary"])
        )
        small_config = config_from_args(parser.parse_args(["--rows", "1"]))

        self.assertEqual(boundary_config.rows, 20_000)
        self.assertEqual(small_config.rows, 1)
        self.assertEqual(small_config.commander_count, 1)

    def test_writer_preserves_utf8_card_names(self) -> None:
        write_csv(
            self.output_path,
            [{"name": "Æther Adept", "count": 1}],
        )

        parsed = parse_collection(self.output_path, self.name_to_id)

        self.assertEqual(parsed.collection, {"n6": 1})


if __name__ == "__main__":
    unittest.main()
