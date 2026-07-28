import unittest
from unittest.mock import patch

from backend.data_loader import (
    COMMANDERS_PATH,
    get_cards_by_id,
    get_commanders,
    get_name_to_id,
    get_theme_to_card_ids,
)


class CachedDataLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        get_cards_by_id.cache_clear()
        get_commanders.cache_clear()
        get_name_to_id.cache_clear()
        get_theme_to_card_ids.cache_clear()

    def test_cards_are_loaded_only_once(self) -> None:
        expected = {"oracle-id": {"name": "Test Card"}}

        with patch(
            "backend.data_loader.load_cards_by_id",
            return_value=expected,
        ) as loader:
            first_result = get_cards_by_id()
            second_result = get_cards_by_id()

        self.assertIs(first_result, second_result)
        loader.assert_called_once_with()

    def test_commanders_use_processed_data_path(self) -> None:
        expected = ["oracle-commander"]

        with patch(
            "backend.data_loader.load_json",
            return_value=expected,
        ) as loader:
            result = get_commanders()

        self.assertEqual(result, expected)
        loader.assert_called_once_with(COMMANDERS_PATH)

    def test_invalid_commander_data_is_rejected(self) -> None:
        with patch(
            "backend.data_loader.load_json",
            return_value={"not": "a list"},
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "Expected a JSON array of Oracle IDs",
            ):
                get_commanders()