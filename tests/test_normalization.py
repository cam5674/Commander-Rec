import gzip
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any

from scripts.process_scryfall import (
    THEME_RULES,
    add_name_mapping,
    classify_themes,
    combine_face_field,
    get_face_names,
    is_commander,
    normalize_card,
    normalize_lookup_name,
    process_cards,
    strip_reminder_text,
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
    def test_theme_rules_do_not_exceed_trigger_limit(self) -> None:
        for theme, triggers in THEME_RULES.items():
            with self.subTest(theme=theme):
                self.assertLessEqual(len(triggers), 15)

    def test_classifies_common_oracle_tag_wording(self) -> None:
        examples = {
            "graveyard": ("Flashback", "Sorcery", ["Flashback"]),
            "tokens": ("Populate.", "Sorcery", ["Populate"]),
            "lifegain": ("You gain 2 life.", "Instant", []),
            "plus_one_counters": ("", "Creature — Mutant", ["Evolve"]),
            "spellslinger": ("Magecraft — Whenever you cast or copy an instant or sorcery spell.", "Creature — Wizard", ["Magecraft"]),
            "card_draw": ("Draw three cards.", "Sorcery", []),
            "lands": ("Whenever a land you control enters, draw a card.", "Enchantment", []),
        }

        for expected_theme, (oracle_text, type_line, keywords) in examples.items():
            with self.subTest(theme=expected_theme):
                themes = classify_themes(oracle_text, type_line, keywords)
                self.assertIn(expected_theme, themes)

    def test_classifies_wheel_text(self) -> None:
        themes = classify_themes(
            oracle_text=(
                "Each player discards their hand, then draws seven cards."
            ),
            type_line="Sorcery",
            keywords=[],
        )
        self.assertIn("wheels", themes)

    def test_classifies_sacrifice_payoff_as_aristocrats_only(self) -> None:
        themes = classify_themes(
            oracle_text=(
                "Whenever you sacrifice another permanent, each opponent "
                "loses 1 life."
            ),
            type_line="Creature — Vampire",
            keywords=[],
        )
        self.assertIn("aristocrats", themes)
        self.assertNotIn("sacrifice", themes)

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

    def test_reanimator_evidence_is_not_double_counted_as_graveyard(self) -> None:
        themes = classify_themes(
            oracle_text=(
                "Return a creature card from your graveyard "
                "to the battlefield."
            ),
            type_line="Sorcery",
            keywords=[],
        )
        self.assertIn("reanimator", themes)
        self.assertNotIn("graveyard", themes)

    def test_strips_nested_reminder_text(self) -> None:
        self.assertEqual(
            strip_reminder_text(
                "Investigate. (Create a Clue token. "
                "(It is an artifact.) Draw a card.)"
            ),
            "Investigate. ",
        )

    def test_food_creation_is_tokens_and_lifegain(self) -> None:
        themes = classify_themes(
            oracle_text=(
                "Create a Food token. (It's an artifact with "
                '"{2}, {T}, Sacrifice this token: You gain 3 life.")'
            ),
            type_line="Sorcery",
            keywords=[],
        )

        self.assertEqual(set(themes), {"tokens", "lifegain"})

    def test_treasure_creation_is_tokens_only(self) -> None:
        themes = classify_themes(
            oracle_text=(
                "Create a Treasure token. (It's an artifact with "
                '"{T}, Sacrifice this token: Add one mana of any color.")'
            ),
            type_line="Sorcery",
            keywords=[],
        )

        self.assertEqual(themes, ["tokens"])

    def test_treasure_with_explicit_artifact_synergy_adds_artifacts(self) -> None:
        themes = classify_themes(
            oracle_text=(
                "Create a Treasure token. Whenever an artifact enters "
                "under your control, draw a card."
            ),
            type_line="Enchantment",
            keywords=[],
        )

        self.assertEqual(
            set(themes),
            {"tokens", "artifacts", "card_draw"},
        )

    def test_investigate_reminder_text_only_adds_tokens(self) -> None:
        themes = classify_themes(
            oracle_text=(
                "Investigate. (Create a Clue token. It's an artifact with "
                '"{2}, Sacrifice this token: Draw a card.")'
            ),
            type_line="Instant",
            keywords=["Investigate"],
        )

        self.assertEqual(themes, ["tokens"])

    def test_explicit_clue_payoff_adds_its_actual_themes(self) -> None:
        themes = classify_themes(
            oracle_text=(
                "Investigate. Whenever you sacrifice a Clue, "
                "draw two cards."
            ),
            type_line="Enchantment",
            keywords=["Investigate"],
        )

        self.assertEqual(
            set(themes),
            {"tokens", "card_draw", "aristocrats"},
        )

    def test_generic_artifact_type_line_adds_artifacts(self) -> None:
        themes = classify_themes(
            oracle_text="{T}: Add {C}.",
            type_line="Artifact",
            keywords=[],
        )

        self.assertEqual(themes, ["artifacts"])

    def test_clause_bounded_patterns_do_not_cross_sentences(self) -> None:
        themes = classify_themes(
            oracle_text=(
                "Whenever you cast a creature spell, scry 1. "
                "Noncreature spells cost {1} more to cast."
            ),
            type_line="Enchantment",
            keywords=[],
        )

        self.assertNotIn("spellslinger", themes)

    def test_proxy_keywords_do_not_add_unrelated_themes(self) -> None:
        examples = {
            "Convoke": "tokens",
            "Casualty": "sacrifice",
            "Emerge": "sacrifice",
            "Offering": "sacrifice",
            "Revolt": "aristocrats",
        }

        for keyword, excluded_theme in examples.items():
            with self.subTest(keyword=keyword):
                themes = classify_themes(
                    oracle_text="",
                    type_line="Creature",
                    keywords=[keyword],
                )
                self.assertNotIn(excluded_theme, themes)

    def test_mill_requires_collection_relevant_subject(self) -> None:
        self.assertNotIn(
            "graveyard",
            classify_themes(
                "Target opponent mills three cards.",
                "Sorcery",
                ["Mill"],
            ),
        )
        self.assertIn(
            "graveyard",
            classify_themes(
                "You mill three cards.",
                "Sorcery",
                ["Mill"],
            ),
        )

    def test_repeatable_sacrifice_outlet_adds_sacrifice(self) -> None:
        themes = classify_themes(
            oracle_text="Sacrifice another creature: Draw a card.",
            type_line="Enchantment",
            keywords=[],
        )

        self.assertIn("sacrifice", themes)
        self.assertIn("card_draw", themes)

    def test_repeated_commanders_lose_incidental_theme_tags(self) -> None:
        examples = {
            "Tamiyo": {
                "oracle_text": (
                    "Flying\nWhenever Tamiyo attacks, investigate. "
                    "(Create a Clue token. It's an artifact with "
                    '"{2}, Sacrifice this token: Draw a card.")\n'
                    "When you draw your third card in a turn, exile Tamiyo, "
                    "then return her to the battlefield transformed.\n//\n"
                    "−3: Return target instant or sorcery card from your "
                    "graveyard to your hand.\n−7: Draw cards equal to half "
                    "the number of cards in your library, rounded up."
                ),
                "type_line": (
                    "Legendary Creature — Moonfolk Wizard // "
                    "Legendary Planeswalker — Tamiyo"
                ),
                "keywords": ["Investigate"],
                "expected": {
                    "graveyard",
                    "tokens",
                    "spellslinger",
                    "card_draw",
                },
            },
            "Eloise": {
                "oracle_text": (
                    "Whenever another creature you control dies, "
                    "investigate. (Create a Clue token. It's an artifact "
                    'with "{2}, Sacrifice this token: Draw a card.")\n'
                    "Whenever you sacrifice a token, surveil 1."
                ),
                "type_line": "Legendary Creature — Human Rogue",
                "keywords": ["Investigate", "Surveil"],
                "expected": {"graveyard", "tokens", "aristocrats"},
            },
            "Lazav": {
                "oracle_text": (
                    "Whenever Lazav attacks, exile target card from a "
                    "graveyard, then investigate. (Create a Clue token. "
                    "It's an artifact with "
                    '"{2}, Sacrifice this token: Draw a card.")\n'
                    "Whenever you sacrifice a Clue, Lazav may become a copy "
                    "of a creature card exiled with it."
                ),
                "type_line": "Legendary Creature — Shapeshifter Detective",
                "keywords": ["Investigate"],
                "expected": {"graveyard", "tokens", "aristocrats"},
            },
            "Sauron": {
                "oracle_text": (
                    "Ward—Sacrifice a legendary artifact or legendary "
                    "creature.\nWhenever an opponent casts a spell, "
                    "amass Orcs 1.\nWhenever the Ring tempts you, you may "
                    "discard your hand. If you do, draw four cards."
                ),
                "type_line": "Legendary Creature — Avatar Horror",
                "keywords": ["Amass"],
                "expected": {"tokens", "card_draw"},
            },
            "Dennick": {
                "oracle_text": (
                    "Lifelink\nCards in graveyards can't be the targets of "
                    "spells or abilities.\nDisturb {2}{W}{U} (You may cast "
                    "this card from your graveyard transformed.)\n//\n"
                    "Whenever one or more creature cards are put into "
                    "graveyards from anywhere, investigate. (Create a Clue "
                    "token. It's an artifact with "
                    '"{2}, Sacrifice this token: Draw a card.")'
                ),
                "type_line": (
                    "Legendary Creature — Human Soldier // "
                    "Legendary Creature — Spirit Soldier"
                ),
                "keywords": ["Lifelink", "Investigate", "Disturb"],
                "expected": {"graveyard", "tokens", "lifegain"},
            },
        }

        for name, example in examples.items():
            with self.subTest(commander=name):
                themes = classify_themes(
                    example["oracle_text"],
                    example["type_line"],
                    example["keywords"],
                )
                self.assertEqual(set(themes), example["expected"])

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
        input_path = self.directory / "oracle_cards.jsonl.gz"
        with gzip.open(input_path, "wt", encoding="utf-8") as input_file:
            for card in (
                multiface_card,
                {"name": "Missing Oracle ID"},
                commander,
            ):
                input_file.write(json.dumps(card) + "\n")

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

        
if __name__ == "__main__":
    unittest.main()
