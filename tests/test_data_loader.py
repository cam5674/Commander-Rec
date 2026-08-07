import unittest
from unittest.mock import patch

from backend.data_loader import (
    COMMANDERS_PATH,
    DEFAULT_PROCESSED_DATA_DIR,
    PROJECT_ROOT,
    clear_reference_data_caches,
    get_cards_by_id,
    get_commanders,
    get_name_to_id,
    get_theme_to_card_ids,
    resolve_processed_data_dir,
)


class CachedDataLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_reference_data_caches()

    def test_cards_are_loaded_only_once(self) -> None:
        expected = {"oracle-id": {"name": "Test Card"}}

        with (
            patch(
                "backend.data_loader.load_cards_by_id",
                return_value=expected,
            ) as loader,
            self.assertLogs("backend.data_loader", level="INFO") as logs,
        ):
            first_result = get_cards_by_id()
            second_result = get_cards_by_id()

        self.assertIs(first_result, second_result)
        loader.assert_called_once_with()
        self.assertIn("dataset=cards_by_id cache=miss", logs.output[0])
        self.assertIn("dataset=cards_by_id cache=hit", logs.output[1])

    def test_processed_data_directory_defaults_to_project_data(self) -> None:
        self.assertEqual(resolve_processed_data_dir(""), DEFAULT_PROCESSED_DATA_DIR)

    def test_relative_processed_data_directory_uses_project_root(self) -> None:
        self.assertEqual(
            resolve_processed_data_dir("fixtures/processed"),
            PROJECT_ROOT / "fixtures" / "processed",
        )

    def test_processed_data_directory_reads_environment(self) -> None:
        with patch.dict(
            "os.environ",
            {"REFERENCE_DATA_DIR": "deployment/reference-data"},
        ):
            self.assertEqual(
                resolve_processed_data_dir(),
                PROJECT_ROOT / "deployment" / "reference-data",
            )

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
