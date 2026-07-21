import unittest
from typing import Any
import tempfile
from pathlib import Path

from scripts.process_scryfall import (
    classify_themes,
    combine_face_field,
    get_face_names,
    is_commander,
    normalize_card,
    normalize_lookup_name,
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

class CSVParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)

        self.directory = Path(self.temporary_directory.name)

    def write_csv(self, content: str) -> Path:
        csv_path = self.directory / "collection.csv"
        csv_path.write_text(content, encoding="utf-8")
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


        collection, unmatched = parse_collection(
        csv_path,
        name_to_id,
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

        collection, unmatched = parse_collection(
            csv_path,
            {},
        )

        self.assertEqual(collection, {})
        self.assertEqual(unmatched, ["Unknown Card"])




if __name__ == "__main__":
    unittest.main()
