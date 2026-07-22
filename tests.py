import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any

from scripts.process_scryfall import (
    add_name_mapping,
    classify_themes,
    combine_face_field,
    get_face_names,
    is_commander,
    normalize_card,
    normalize_lookup_name,
    process_cards,
)

from backend.csv_parser import(
    load_name_to_id,
    parse_collection,
)


def make_card(**overrides: Any) -> dict[str, Any]:
    card: dict[str, Any] = {
        "id": "scryfall-id",
        "oracle_id": "oracle-id",
        "name": "Test Card",
        "layout": "normal",
        "mana_cost": "{2}{G}",
        "cmc": 3.0,
        "type_line": "Creature — Human",
        "oracle_text": "Vigilance",
        "keywords": ["Vigilance"],
        "color_identity": ["G"],
        "legalities": {"commander": "legal"},
        "games": ["paper"],
        "image_uris": {"normal": "https://example.test/card.jpg"},
    }
    card.update(overrides)
    return card


class NameNormalizationTests(unittest.TestCase):
    def test_normalizes_case_and_whitespace(self) -> None:
        self.assertEqual(
            normalize_lookup_name("  MULDROTHA,   the Gravetide  "),
            "muldrotha, the gravetide",
        )

    def test_normalizes_unicode_compatibility_characters(self) -> None:
        self.assertEqual(
            normalize_lookup_name("ＳＯＬ　ＲＩＮＧ"),
            "sol ring",
        )

    def test_normalizes_multiface_separator_spacing(self) -> None:
        self.assertEqual(
            normalize_lookup_name("Valki, God of Lies//Tibalt, Cosmic Impostor"),
            "valki, god of lies // tibalt, cosmic impostor",
        )


class MultifaceCardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.card = make_card(
            name="Front Face // Back Face",
            layout="transform",
            cmc=2.0,
            type_line=None,
            oracle_text=None,
            mana_cost=None,
            card_faces=[
                {
                    "name": "Front Face",
                    "mana_cost": "{1}{G}",
                    "type_line": "Legendary Creature — Human",
                    "oracle_text": "Create a 1/1 green creature token.",
                    "image_uris": {
                        "normal": "https://example.test/front.jpg",
                    },
                },
                {
                    "name": "Back Face",
                    "mana_cost": "",
                    "type_line": "Land",
                    "oracle_text": "{T}: Add {G}.",
                    "image_uris": {
                        "normal": "https://example.test/back.jpg",
                    },
                },
            ],
        )
        self.card.pop("image_uris")

    def test_combines_face_fields(self) -> None:
        self.assertEqual(
            combine_face_field(self.card, "type_line"),
            "Legendary Creature — Human // Land",
        )
        self.assertEqual(
            combine_face_field(
                self.card,
                "oracle_text",
                separator="\n//\n",
            ),
            "Create a 1/1 green creature token.\n//\n{T}: Add {G}.",
        )

    def test_normalizes_faces_and_aliases(self) -> None:
        normalized = normalize_card(self.card)

        self.assertEqual(get_face_names(self.card), ["Front Face", "Back Face"])
        self.assertEqual(normalized["image"], "https://example.test/front.jpg")
        self.assertEqual(len(normalized["faces"]), 2)
        self.assertEqual(normalized["faces"][0]["name"], "Front Face")
        self.assertEqual(
            normalized["faces"][1]["image"],
            "https://example.test/back.jpg",
        )


class CommanderEligibilityTests(unittest.TestCase):
    def test_legal_legendary_creature_is_commander(self) -> None:
        card = make_card(type_line="Legendary Creature — Elf Druid")
        self.assertTrue(is_commander(card))

    def test_format_illegal_card_is_not_commander(self) -> None:
        card = make_card(
            type_line="Legendary Creature — Elf Druid",
            legalities={"commander": "not_legal"},
        )
        self.assertFalse(is_commander(card))

    def test_explicit_commander_text_is_supported(self) -> None:
        card = make_card(
            type_line="Legendary Planeswalker — Test",
            oracle_text="Test can be your commander.",
        )
        self.assertTrue(is_commander(card))

    def test_legendary_background_is_supported(self) -> None:
        card = make_card(
            type_line="Legendary Enchantment — Background",
            oracle_text="Commander creatures you own have vigilance.",
        )
        self.assertTrue(is_commander(card))

    def test_creature_status_outside_battlefield_is_supported(self) -> None:
        card = make_card(
            type_line="Legendary Planeswalker — Test",
            oracle_text=(
                "As long as Test isn't on the battlefield, it's a 1/1 "
                "creature in addition to its other types."
            ),
        )
        self.assertTrue(is_commander(card))

    def test_legendary_and_creature_must_be_on_same_face(self) -> None:
        card = make_card(
            type_line=None,
            oracle_text=None,
            card_faces=[
                {
                    "name": "Front",
                    "type_line": "Legendary Enchantment",
                    "oracle_text": "Vigilance",
                },
                {
                    "name": "Back",
                    "type_line": "Creature — Bear",
                    "oracle_text": "Trample",
                },
            ],
        )
        self.assertFalse(is_commander(card))


class ThemeClassificationTests(unittest.TestCase):
    def test_classifies_wheel_text(self) -> None:
        themes = classify_themes(
            oracle_text=(
                "Each player discards their hand, then draws seven cards."
            ),
            type_line="Sorcery",
            keywords=[],
        )
        self.assertIn("wheels", themes)

    def test_classifies_aristocrats_and_sacrifice_text(self) -> None:
        themes = classify_themes(
            oracle_text=(
                "Whenever you sacrifice another permanent, each opponent "
                "loses 1 life."
            ),
            type_line="Creature — Vampire",
            keywords=[],
        )
        self.assertIn("aristocrats", themes)
        self.assertIn("sacrifice", themes)

    def test_classifies_keywords(self) -> None:
        themes = classify_themes(
            oracle_text="",
            type_line="Creature — Elf",
            keywords=["Landfall", "Lifelink", "Proliferate"],
        )
        self.assertTrue({
            "lands",
            "lifegain",
            "plus_one_counters",
        }.issubset(themes))

    def test_classifies_overlapping_graveyard_themes(self) -> None:
        themes = classify_themes(
            oracle_text="Return a creature card from your graveyard.",
            type_line="Sorcery",
            keywords=[],
        )
        self.assertIn("reanimator", themes)
        self.assertIn("graveyard", themes)

    def test_leaves_unrelated_card_untagged(self) -> None:
        themes = classify_themes(
            oracle_text="Flying, vigilance",
            type_line="Creature — Bird",
            keywords=["Flying", "Vigilance"],
        )
        self.assertEqual(themes, [])


class DataPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.directory = Path(self.temporary_directory.name)

    def test_process_cards_builds_required_indexes(self) -> None:
        commander = make_card(
            id="scryfall-captain",
            oracle_id="oracle-captain",
            name="Token Captain",
            type_line="Legendary Creature — Human",
            oracle_text="Create a 1/1 creature token.",
        )
        multiface_card = make_card(
            id="scryfall-valki",
            oracle_id="oracle-valki",
            name="Valki, God of Lies // Tibalt, Cosmic Impostor",
            layout="modal_dfc",
            type_line=None,
            oracle_text=None,
            mana_cost=None,
            legalities={"commander": "not_legal"},
            card_faces=[
                {
                    "name": "Valki, God of Lies",
                    "mana_cost": "{1}{B}",
                    "type_line": "Legendary Creature — God",
                    "oracle_text": "Menace",
                },
                {
                    "name": "Tibalt, Cosmic Impostor",
                    "mana_cost": "{5}{B}{R}",
                    "type_line": "Legendary Planeswalker — Tibalt",
                    "oracle_text": "+2: Exile the top card of each player's library.",
                },
            ],
        )
        multiface_card.pop("image_uris")
        input_path = self.directory / "oracle_cards.json"
        input_path.write_text(
            json.dumps([
                multiface_card,
                {"name": "Missing Oracle ID"},
                commander,
            ]),
            encoding="utf-8",
        )

        with redirect_stdout(StringIO()):
            cards, names, commanders, themes = process_cards(input_path)

        self.assertEqual(set(cards), {"oracle-captain", "oracle-valki"})
        self.assertEqual(names["token captain"], "oracle-captain")
        self.assertEqual(names["valki, god of lies"], "oracle-valki")
        self.assertEqual(names["tibalt, cosmic impostor"], "oracle-valki")
        self.assertEqual(commanders, ["oracle-captain"])
        self.assertIn("oracle-captain", themes["tokens"])

    def test_canonical_name_overrides_conflicting_face_alias(self) -> None:
        name_to_id: dict[str, str] = {}
        primary_keys: set[str] = set()
        collisions: set[str] = set()

        add_name_mapping(
            name_to_id,
            primary_keys,
            collisions,
            "Shared Name",
            "oracle-face-alias",
            is_primary=False,
        )
        add_name_mapping(
            name_to_id,
            primary_keys,
            collisions,
            "SHARED   NAME",
            "oracle-canonical",
            is_primary=True,
        )
        add_name_mapping(
            name_to_id,
            primary_keys,
            collisions,
            "Shared Name",
            "oracle-later-alias",
            is_primary=False,
        )

        self.assertEqual(name_to_id["shared name"], "oracle-canonical")
        self.assertIn("shared name", primary_keys)
        self.assertEqual(collisions, {"shared name"})


class CSVParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)

        self.directory = Path(self.temporary_directory.name)

    def write_csv(self, content: str, *, encoding: str = "utf-8") -> Path:
        csv_path = self.directory / "collection.csv"
        csv_path.write_text(content, encoding=encoding)
        return csv_path




    def test_combines_duplicate_cards(self) -> None:
        name_to_id = {
        "sol ring": "oracle-sol-ring",
        }

        csv_path = self.write_csv (
        "Count,Tradelist Count,Name\n"
        "1,0,Sol Ring\n"
        "3,0,SOL RING\n"
            )


        # CSV contains two Sol Ring rows with quantities 1 and 3.
        collection, unmatched = parse_collection(csv_path, name_to_id)

        self.assertEqual(collection, {"oracle-sol-ring": 4})
        self.assertEqual(unmatched, [])

    def test_tracks_unmatched_cards(self) -> None:
        csv_path = self.write_csv(
        "Count,Tradelist Count,Name\n"
        "1,0,Unknown Card\n"
         )

        collection, unmatched = parse_collection(csv_path,{}, )

        self.assertEqual(collection, {})
        self.assertEqual(unmatched, ["Unknown Card"])

    def test_case_and_whitespace(self) -> None:
        name_to_id = {
        "the locust god": "oracle-the-locust-god",
        }

        csv_path = self.write_csv(
            "Count,Tradelist Count,Name\n"
            "3, 0, THE  LOcust GoD\n"
        )

        collection, unmatched = parse_collection(csv_path, name_to_id)
        self.assertEqual(collection,{"oracle-the-locust-god": 3} )
        self.assertEqual(unmatched, [])

    def test_different_csv_format(self) -> None:
        name_to_id = {
        "the locust god": "oracle-the-locust-god",
        }

        csv_path = self.write_csv(
            "Name, Count\n"
            "The Locust God, 2\n"
        )

        collection, unmatched = parse_collection(csv_path, name_to_id)
        self.assertEqual(collection,{"oracle-the-locust-god": 2} )
        self.assertEqual(unmatched, [])

    def test_missing_names(self) -> None:

        name_to_id = {
        "the locust god": "oracle-the-locust-god",
        }

        csv_path = self.write_csv(
            "Name, Count\n"
            ", 2\n"
        )

        with redirect_stdout(StringIO()) as output:
            collection, unmatched = parse_collection(csv_path, name_to_id)

        self.assertEqual(collection,{} )
        self.assertEqual(unmatched, [])
        self.assertIn("card name is missing", output.getvalue())

    def test_multiface_aliases_resolve_to_the_same_oracle_id(self) -> None:
        name_to_id = {
            "valki, god of lies // tibalt, cosmic impostor": "oracle-valki",
            "tibalt, cosmic impostor": "oracle-valki",
        }
        csv_path = self.write_csv(
            "Count,Name\n"
            "1,\"Valki, God of Lies//Tibalt, Cosmic Impostor\"\n"
            "1,\"Tibalt, Cosmic Impostor\"\n"
        )

        collection, unmatched = parse_collection(csv_path, name_to_id)

        self.assertEqual(collection, {"oracle-valki": 2})
        self.assertEqual(unmatched, [])

    def test_common_csv_header_formats(self) -> None:
        name_to_id = {"sol ring": "oracle-sol-ring"}
        formats = {
            "count_name_with_extra_columns": (
                "Count,Tradelist Count,Name,Edition\n"
                "2,0,Sol Ring,CMM\n"
            ),
            "quantity_name": "Quantity,Name\n2,Sol Ring\n",
            "card_name_quantity": "Card Name,Quantity\nSol Ring,2\n",
            "qty_with_reordered_columns": (
                "Set,Card Name,Foil,Qty\nCMM,Sol Ring,false,2\n"
            ),
            "mixed_case_and_spaced_headers": " NAME , qTy \nSol Ring,2\n",
        }

        for format_name, content in formats.items():
            with self.subTest(format_name=format_name):
                csv_path = self.write_csv(content)
                collection, unmatched = parse_collection(csv_path, name_to_id)

                self.assertEqual(collection, {"oracle-sol-ring": 2})
                self.assertEqual(unmatched, [])

    def test_invalid_quantities_are_rejected(self) -> None:
        name_to_id = {"sol ring": "oracle-sol-ring"}
        csv_path = self.write_csv(
            "Name,Count\n"
            "Sol Ring,many\n"
            "Sol Ring,0\n"
            "Sol Ring,-2\n"
        )

        with redirect_stdout(StringIO()) as output:
            collection, unmatched = parse_collection(csv_path, name_to_id)

        self.assertEqual(collection, {})
        self.assertEqual(unmatched, [])
        self.assertIn("invalid quantity 'many'", output.getvalue())
        self.assertEqual(
            output.getvalue().count("quantity must be greater than zero"),
            2,
        )

    def test_rows_with_too_few_columns_are_rejected(self) -> None:
        csv_path = self.write_csv("Name,Count\nSol Ring\n")

        with redirect_stdout(StringIO()) as output:
            collection, unmatched = parse_collection(csv_path, {})

        self.assertEqual(collection, {})
        self.assertEqual(unmatched, [])
        self.assertIn("invalid quantity ''", output.getvalue())

    def test_utf8_bom_file_parses(self) -> None:
        name_to_id = {"sol ring": "oracle-sol-ring"}
        csv_path = self.write_csv(
            "Count,Name\n1,Sol Ring\n",
            encoding="utf-8-sig",
        )

        collection, unmatched = parse_collection(csv_path, name_to_id)

        self.assertEqual(collection, {"oracle-sol-ring": 1})
        self.assertEqual(unmatched, [])

    def test_empty_csv_raises_expected_error(self) -> None:
        csv_path = self.write_csv("")

        with self.assertRaisesRegex(ValueError, "collection CSV is empty"):
            parse_collection(csv_path, {})

    def test_row_limit_counts_only_data_rows(self) -> None:
        name_to_id = {
            "sol ring": "oracle-sol-ring",
            "arcane signet": "oracle-arcane-signet",
            "command tower": "oracle-command-tower",
        }
        csv_path = self.write_csv(
            "Count,Name\n"
            "1,Sol Ring\n"
            "2,Arcane Signet\n"
            "3,Command Tower\n"
        )

        collection, unmatched = parse_collection(
            csv_path,
            name_to_id,
            row_limit=2,
        )

        self.assertEqual(
            collection,
            {
                "oracle-sol-ring": 1,
                "oracle-arcane-signet": 2,
            },
        )
        self.assertEqual(unmatched, [])

    def test_missing_name_lookup_file_has_useful_error(self) -> None:
        missing_path = self.directory / "missing.json"

        with self.assertRaisesRegex(
            RuntimeError,
            "Name lookup file was not found",
        ):
            load_name_to_id(missing_path)

    def test_valid_name_lookup_file_loads(self) -> None:
        lookup_path = self.directory / "name_to_id.json"
        expected = {
            "sol ring": "oracle-sol-ring",
            "the locust god": "oracle-the-locust-god",
        }
        lookup_path.write_text(json.dumps(expected), encoding="utf-8")

        self.assertEqual(load_name_to_id(lookup_path), expected)

    def test_malformed_name_lookup_file_has_useful_error(self) -> None:
        malformed_path = self.directory / "name_to_id.json"
        malformed_path.write_text("{not valid json", encoding="utf-8")

        with self.assertRaisesRegex(
            RuntimeError,
            "Name lookup file contains invalid JSON",
        ):
            load_name_to_id(malformed_path)






if __name__ == "__main__":
    unittest.main()
