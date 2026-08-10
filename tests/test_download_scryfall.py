import unittest
from unittest.mock import Mock, patch

from scripts.download_scryfall import get_oracle_cards_metadata


class ScryfallMetadataTests(unittest.TestCase):
    @patch("scripts.download_scryfall.requests.get")
    def test_selects_oracle_cards_jsonl_download(self, mock_get: Mock) -> None:
        response = Mock()
        response.json.return_value = {
            "data": [
                {
                    "type": "default_cards",
                    "jsonl_download_uri": "https://example.test/default.jsonl.gz",
                },
                {
                    "type": "oracle_cards",
                    "name": "Oracle Cards",
                    "jsonl_download_uri": "https://example.test/oracle.jsonl.gz",
                },
            ]
        }
        mock_get.return_value = response

        metadata = get_oracle_cards_metadata()

        response.raise_for_status.assert_called_once_with()
        self.assertEqual(metadata["type"], "oracle_cards")
        self.assertEqual(
            metadata["jsonl_download_uri"],
            "https://example.test/oracle.jsonl.gz",
        )

    @patch("scripts.download_scryfall.requests.get")
    def test_rejects_oracle_metadata_without_jsonl_url(
        self,
        mock_get: Mock,
    ) -> None:
        response = Mock()
        response.json.return_value = {
            "data": [{"type": "oracle_cards", "name": "Oracle Cards"}]
        }
        mock_get.return_value = response

        with self.assertRaisesRegex(RuntimeError, "JSONL download URL"):
            get_oracle_cards_metadata()


if __name__ == "__main__":
    unittest.main()
