
import json
import tempfile
import unittest
from io import StringIO
from pathlib import Path



from backend.csv_parser import (
    CSVRowLimitError,
    CSVWarning,
    parse_collection,
    parse_collection_bytes,
    parse_collection_stream,
)
from backend.data_loader import load_name_to_id

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
        result = parse_collection(csv_path, name_to_id)

        self.assertEqual(result.collection, {"oracle-sol-ring": 4})
        self.assertEqual(result.unmatched_names, [])
        self.assertEqual(result.warnings, [])

    def test_tracks_unmatched_cards(self) -> None:
        csv_path = self.write_csv(
        "Count,Tradelist Count,Name\n"
        "1,0,Unknown Card\n"
         )

        result = parse_collection(csv_path, {})

        self.assertEqual(result.collection, {})
        self.assertEqual(result.unmatched_names, ["Unknown Card"])
        self.assertEqual(result.warnings, [])

    def test_case_and_whitespace(self) -> None:
        name_to_id = {
        "the locust god": "oracle-the-locust-god",
        }

        csv_path = self.write_csv(
            "Count,Tradelist Count,Name\n"
            "3, 0, THE  LOcust GoD\n"
        )

        result = parse_collection(csv_path, name_to_id)

        self.assertEqual(result.collection, {"oracle-the-locust-god": 3})
        self.assertEqual(result.unmatched_names, [])

    def test_different_csv_format(self) -> None:
        name_to_id = {
        "the locust god": "oracle-the-locust-god",
        }

        csv_path = self.write_csv(
            "Name, Count\n"
            "The Locust God, 2\n"
        )

        result = parse_collection(csv_path, name_to_id)

        self.assertEqual(result.collection, {"oracle-the-locust-god": 2})
        self.assertEqual(result.unmatched_names, [])

    def test_missing_names(self) -> None:

        name_to_id = {
        "the locust god": "oracle-the-locust-god",
        }

        csv_path = self.write_csv(
            "Name, Count\n"
            ", 2\n"
        )

        result = parse_collection(csv_path, name_to_id)

        self.assertEqual(result.collection, {})
        self.assertEqual(result.unmatched_names, [])
        self.assertEqual(
            result.warnings,
            [
                CSVWarning(
                    code="MISSING_CARD_NAME",
                    message="Card name is missing.",
                    row=2,
                )
            ],
        )

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

        result = parse_collection(csv_path, name_to_id)

        self.assertEqual(result.collection, {"oracle-valki": 2})
        self.assertEqual(result.unmatched_names, [])

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
                result = parse_collection(csv_path, name_to_id)

                self.assertEqual(result.collection, {"oracle-sol-ring": 2})
                self.assertEqual(result.unmatched_names, [])

    def test_invalid_quantities_are_rejected(self) -> None:
        name_to_id = {"sol ring": "oracle-sol-ring"}
        csv_path = self.write_csv(
            "Name,Count\n"
            "Sol Ring,many\n"
            "Sol Ring,0\n"
            "Sol Ring,-2\n"
        )

        result = parse_collection(csv_path, name_to_id)

        self.assertEqual(result.collection, {})
        self.assertEqual(result.unmatched_names, [])
        self.assertEqual(
            [warning.code for warning in result.warnings],
            [
                "INVALID_QUANTITY",
                "NON_POSITIVE_QUANTITY",
                "NON_POSITIVE_QUANTITY",
            ],
        )
        self.assertEqual(
            [warning.row for warning in result.warnings],
            [2, 3, 4],
        )

    def test_rows_with_too_few_columns_are_rejected(self) -> None:
        csv_path = self.write_csv("Name,Count\nSol Ring\n")

        result = parse_collection(csv_path, {})

        self.assertEqual(result.collection, {})
        self.assertEqual(result.unmatched_names, [])
        self.assertEqual(
            result.warnings,
            [
                CSVWarning(
                    code="INVALID_QUANTITY",
                    message="Quantity must be a whole number.",
                    row=2,
                    value="",
                )
            ],
        )

    def test_utf8_bom_file_parses(self) -> None:
        name_to_id = {"sol ring": "oracle-sol-ring"}
        csv_path = self.write_csv(
            "Count,Name\n1,Sol Ring\n",
            encoding="utf-8-sig",
        )

        result = parse_collection(csv_path, name_to_id)

        self.assertEqual(result.collection, {"oracle-sol-ring": 1})
        self.assertEqual(result.unmatched_names, [])

    def test_text_stream_parses(self) -> None:
        name_to_id = {"sol ring": "oracle-sol-ring"}
        csv_file = StringIO("Count,Name\n2,Sol Ring\n", newline="")

        result = parse_collection_stream(
            csv_file,
            name_to_id,
        )

        self.assertEqual(result.collection, {"oracle-sol-ring": 2})
        self.assertEqual(result.unmatched_names, [])

    def test_utf8_bom_bytes_parse(self) -> None:
        name_to_id = {"sol ring": "oracle-sol-ring"}
        csv_data = "Count,Name\n1,Sol Ring\n".encode("utf-8-sig")

        result = parse_collection_bytes(
            csv_data,
            name_to_id,
        )

        self.assertEqual(result.collection, {"oracle-sol-ring": 1})
        self.assertEqual(result.unmatched_names, [])

    def test_invalid_utf8_bytes_raise_useful_error(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "collection CSV must use UTF-8 encoding",
        ):
            parse_collection_bytes(b"\xff\xfe\x00", {})

    def test_empty_csv_raises_expected_error(self) -> None:
        csv_path = self.write_csv("")

        with self.assertRaisesRegex(ValueError, "collection CSV is empty"):
            parse_collection(csv_path, {})

    def test_row_limit_rejects_extra_data_rows(self) -> None:
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

        with self.assertRaisesRegex(
            CSVRowLimitError,
            "exceeds the 2-row limit",
        ):
            parse_collection(
                csv_path,
                name_to_id,
                row_limit=2,
            )

    def test_row_limit_allows_exact_number_of_data_rows(self) -> None:
        name_to_id = {
            "sol ring": "oracle-sol-ring",
            "arcane signet": "oracle-arcane-signet",
        }
        csv_path = self.write_csv(
            "Count,Name\n"
            "1,Sol Ring\n"
            "2,Arcane Signet\n"
        )

        result = parse_collection(
            csv_path,
            name_to_id,
            row_limit=2,
        )

        self.assertEqual(
            result.collection,
            {
                "oracle-sol-ring": 1,
                "oracle-arcane-signet": 2,
            },
        )
        self.assertEqual(result.unmatched_names, [])
        self.assertEqual(result.warnings, [])

    def test_missing_name_lookup_file_has_useful_error(self) -> None:
        missing_path = self.directory / "missing.json"

        with self.assertRaisesRegex(
            RuntimeError,
            "Could not find file",
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
            "Invalid JSON in file",
        ):
            load_name_to_id(malformed_path)


if __name__ == "__main__":
    unittest.main()
