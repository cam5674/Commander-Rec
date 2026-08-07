import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api import (
    DEFAULT_FRONTEND_ORIGINS,
    DEFAULT_MAX_UPLOAD_BYTES,
    MAX_CSV_ROWS,
    MAX_UPLOAD_BYTES,
    app,
    get_allowed_origins,
    get_max_upload_bytes,
)


class APITests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_config_returns_enforced_upload_limits(self) -> None:
        response = self.client.get("/config")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "max_upload_bytes": MAX_UPLOAD_BYTES,
                "max_csv_rows": MAX_CSV_ROWS,
                "accepted_file_extensions": [".csv"],
            },
        )

    def test_default_upload_limit_is_four_mebibytes(self) -> None:
        self.assertEqual(DEFAULT_MAX_UPLOAD_BYTES, 4 * 1024 * 1024)
        self.assertEqual(MAX_UPLOAD_BYTES, DEFAULT_MAX_UPLOAD_BYTES)

    def test_upload_limit_reads_environment(self) -> None:
        with patch.dict("os.environ", {"MAX_UPLOAD_BYTES": "1234"}):
            self.assertEqual(get_max_upload_bytes(), 1234)

    def test_invalid_upload_limit_is_rejected(self) -> None:
        with patch.dict("os.environ", {"MAX_UPLOAD_BYTES": "invalid"}):
            with self.assertRaisesRegex(RuntimeError, "whole number"):
                get_max_upload_bytes()

    def test_allowed_origins_read_environment(self) -> None:
        with patch.dict(
            "os.environ",
            {"ALLOWED_ORIGINS": "https://example.com, https://www.example.com"},
        ):
            self.assertEqual(
                get_allowed_origins(),
                ["https://example.com", "https://www.example.com"],
            )

    def test_allowed_origins_default_to_local_frontend(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(get_allowed_origins(), DEFAULT_FRONTEND_ORIGINS)

    def test_large_responses_are_gzipped(self) -> None:
        response = self.client.get(
            "/openapi.json",
            headers={"Accept-Encoding": "gzip"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-encoding"], "gzip")

    def test_config_allows_frontend_cors_request(self) -> None:
        response = self.client.options(
            "/config",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://localhost:5173",
        )

    def test_valid_csv_returns_recommendations(self) -> None:
        recommendation_result = {
            "unique_cards": 1,
            "total_cards": 2,
            "theme_scores": {"artifacts": 1},
            "top_themes": ["artifacts"],
            "recommendations": [],
        }

        with (
            patch(
                "backend.api.get_name_to_id",
                return_value={"sol ring": "oracle-sol-ring"},
            ),
            patch(
                "backend.api.get_cards_by_id",
                return_value={},
            ),
            patch(
                "backend.api.get_commanders",
                return_value=["oracle-commander"],
            ),
            patch(
                "backend.api.recommend_commanders",
                return_value=recommendation_result,
            ),
        ):
            response = self.client.post(
                "/recommendations",
                files={
                    "upload": (
                        "collection.csv",
                        b"Count,Name\n2,Sol Ring\n",
                        "text/csv",
                    ),
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["unique_cards"], 1)
        self.assertEqual(response.json()["unmatched_names"], [])
        self.assertEqual(response.json()["warnings"], [])

    def test_upload_runs_complete_recommendation_flow(self) -> None:
        cards_by_id = {
            "oracle-sol-ring": {
                "name": "Sol Ring",
                "scryfall_id": "scryfall-sol-ring",
                "image": "https://example.com/sol-ring.jpg",
                "themes": ["artifacts"],
                "color_identity": [],
                "edhrec_rank": 1,
            },
            "oracle-artifact-commander": {
                "name": "Artifact Commander",
                "scryfall_id": "scryfall-artifact-commander",
                "image": "https://example.com/commander.jpg",
                "themes": ["artifacts"],
                "commander_eligible": True,
                "keywords": [],
                "type_line": "Legendary Artifact Creature",
                "edhrec_rank": 100,
                "color_identity": [],
            },
        }

        with (
            patch(
                "backend.api.get_name_to_id",
                return_value={"sol ring": "oracle-sol-ring"},
            ),
            patch(
                "backend.api.get_cards_by_id",
                return_value=cards_by_id,
            ),
            patch(
                "backend.api.get_commanders",
                return_value=["oracle-artifact-commander"],
            ),
        ):
            response = self.client.post(
                "/recommendations",
                files={
                    "upload": (
                        "collection.csv",
                        b"Count,Name\n1,Sol Ring\n",
                        "text/csv",
                    ),
                },
            )

        self.assertEqual(response.status_code, 200)
        recommendation = response.json()["recommendations"][0]
        self.assertEqual(recommendation["name"], "Artifact Commander")
        self.assertFalse(recommendation["owned"])
        self.assertEqual(
            recommendation["image_url"],
            "https://example.com/commander.jpg",
        )
        self.assertEqual(
            recommendation["scryfall_id"],
            "scryfall-artifact-commander",
        )
        self.assertEqual(
            recommendation["scryfall_url"],
            "https://scryfall.com/search?q=oracleid%3Aoracle-artifact-commander",
        )
        self.assertEqual(
            recommendation["score_breakdown"]["theme_ratio"],
            0.6667,
        )
        self.assertEqual(
            recommendation["theme_support"][0]["example_cards"][0]["name"],
            "Sol Ring",
        )
        supporting_card = recommendation["theme_support"][0]["example_cards"][0]
        self.assertEqual(supporting_card["scryfall_id"], "scryfall-sol-ring")
        self.assertEqual(
            supporting_card["scryfall_url"],
            "https://scryfall.com/search?q=oracleid%3Aoracle-sol-ring",
        )
        self.assertEqual(
            supporting_card["image_url"],
            "https://example.com/sol-ring.jpg",
        )

    def test_upload_returns_empty_list_when_no_candidate_clears_gate(self) -> None:
        themes = [
            "artifacts",
            "card_draw",
            "graveyard",
            "sacrifice",
            "tokens",
        ]
        cards_by_id = {}
        name_to_id = {}
        csv_rows = ["Count,Name"]

        for theme in themes:
            oracle_id = f"oracle-{theme}-support"
            name = f"{theme} Support"
            name_to_id[name.casefold()] = oracle_id
            csv_rows.append(f"1,{name}")
            cards_by_id[oracle_id] = {
                "name": name,
                "themes": [theme],
                "color_identity": [],
                "edhrec_rank": None,
            }

        cards_by_id["oracle-commander"] = {
            "name": "Artifact Commander",
            "themes": ["artifacts"],
            "commander_eligible": True,
            "keywords": [],
            "type_line": "Legendary Creature — Test",
            "edhrec_rank": 100,
            "color_identity": [],
        }

        with (
            patch(
                "backend.api.get_name_to_id",
                return_value=name_to_id,
            ),
            patch(
                "backend.api.get_cards_by_id",
                return_value=cards_by_id,
            ),
            patch(
                "backend.api.get_commanders",
                return_value=["oracle-commander"],
            ),
        ):
            response = self.client.post(
                "/recommendations",
                files={
                    "upload": (
                        "collection.csv",
                        ("\n".join(csv_rows) + "\n").encode(),
                        "text/csv",
                    ),
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["unique_cards"], 5)
        self.assertEqual(response.json()["recommendations"], [])
        self.assertEqual(response.json()["unmatched_names"], [])
        self.assertEqual(response.json()["warnings"], [])

    def test_skipped_rows_return_structured_warnings(self) -> None:
        with (
            patch(
                "backend.api.get_name_to_id",
                return_value={},
            ),
            patch(
                "backend.api.recommend_commanders",
            ) as recommender,
        ):
            response = self.client.post(
                "/recommendations",
                files={
                    "upload": (
                        "collection.csv",
                        b"Count,Name\n1,\n",
                        "text/csv",
                    ),
                },
            )

        self.assertEqual(response.status_code, 400)
        detail = response.json()["detail"]

        self.assertEqual(detail["code"], "NO_RECOGNIZED_CARDS")
        self.assertEqual(
            detail["warnings"],
            [
                {
                    "code": "MISSING_CARD_NAME",
                    "message": "Card name is missing.",
                    "row": 2,
                    "value": None,
                }
            ],
        )
        recommender.assert_not_called()

    def test_all_unmatched_names_return_400(self) -> None:
        with (
            patch(
                "backend.api.get_name_to_id",
                return_value={},
            ),
            patch(
                "backend.api.recommend_commanders",
            ) as recommender,
        ):
            response = self.client.post(
                "/recommendations",
                files={
                    "upload": (
                        "collection.csv",
                        b"Count,Name\n1,Unknown Card\n",
                        "text/csv",
                    ),
                },
            )

        self.assertEqual(response.status_code, 400)
        detail = response.json()["detail"]
        self.assertEqual(detail["code"], "NO_RECOGNIZED_CARDS")
        self.assertEqual(detail["unmatched_names"], ["Unknown Card"])
        self.assertEqual(detail["warnings"], [])
        recommender.assert_not_called()

    def test_header_only_csv_returns_400(self) -> None:
        with (
            patch(
                "backend.api.get_name_to_id",
                return_value={},
            ),
            patch(
                "backend.api.recommend_commanders",
            ) as recommender,
        ):
            response = self.client.post(
                "/recommendations",
                files={
                    "upload": (
                        "collection.csv",
                        b"Count,Name\n",
                        "text/csv",
                    ),
                },
            )

        self.assertEqual(response.status_code, 400)
        detail = response.json()["detail"]
        self.assertEqual(detail["code"], "NO_RECOGNIZED_CARDS")
        self.assertEqual(detail["unmatched_names"], [])
        self.assertEqual(detail["warnings"], [])
        recommender.assert_not_called()

    def test_mixed_valid_and_invalid_rows_return_200(self) -> None:
        recommendation_result = {
            "unique_cards": 1,
            "total_cards": 1,
            "theme_scores": {"artifacts": 1},
            "top_themes": ["artifacts"],
            "recommendations": [],
        }

        with (
            patch(
                "backend.api.get_name_to_id",
                return_value={"sol ring": "oracle-sol-ring"},
            ),
            patch(
                "backend.api.get_cards_by_id",
                return_value={},
            ),
            patch(
                "backend.api.get_commanders",
                return_value=[],
            ),
            patch(
                "backend.api.recommend_commanders",
                return_value=recommendation_result,
            ),
        ):
            response = self.client.post(
                "/recommendations",
                files={
                    "upload": (
                        "collection.csv",
                        (
                            b"Count,Name\n"
                            b"1,Sol Ring\n"
                            b"1,Unknown Card\n"
                            b"many,Arcane Signet\n"
                        ),
                        "text/csv",
                    ),
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["unmatched_names"],
            ["Unknown Card"],
        )
        self.assertEqual(
            response.json()["warnings"],
            [
                {
                    "code": "INVALID_QUANTITY",
                    "message": "Quantity must be a whole number.",
                    "row": 4,
                    "value": "many",
                }
            ],
        )

    def test_invalid_csv_returns_400(self) -> None:
        with patch(
            "backend.api.get_name_to_id",
            return_value={},
        ):
            response = self.client.post(
                "/recommendations",
                files={
                    "upload": (
                        "collection.csv",
                        b"Unsupported,Headers\nvalue,value\n",
                        "text/csv",
                    ),
                },
            )

        self.assertEqual(response.status_code, 400)
        detail = response.json()["detail"]
        self.assertEqual(detail["code"], "INVALID_CSV")
        self.assertIn(
            "Unsupported CSV format",
            detail["message"],
        )
        self.assertEqual(detail["unmatched_names"], [])
        self.assertEqual(detail["warnings"], [])

    def test_non_csv_upload_returns_standard_400(self) -> None:
        response = self.client.post(
            "/recommendations",
            files={
                "upload": (
                    "collection.txt",
                    b"Count,Name\n1,Sol Ring\n",
                    "text/plain",
                ),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            {
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": "The uploaded collection must be a CSV file.",
                "unmatched_names": [],
                "warnings": [],
            },
        )

    def test_oversized_upload_returns_413(self) -> None:
        with patch("backend.api.MAX_UPLOAD_BYTES", 10):
            response = self.client.post(
                "/recommendations",
                files={
                    "upload": (
                        "collection.csv",
                        b"x" * 11,
                        "text/csv",
                    ),
                },
            )

        self.assertEqual(response.status_code, 413)
        detail = response.json()["detail"]
        self.assertEqual(detail["code"], "UPLOAD_TOO_LARGE")
        self.assertEqual(detail["unmatched_names"], [])
        self.assertEqual(detail["warnings"], [])

    def test_row_limit_overflow_returns_400(self) -> None:
        csv_data = (
            b"Count,Name\n"
            + b"1,Sol Ring\n" * 20_001
        )

        with (
            patch(
                "backend.api.get_name_to_id",
                return_value={"sol ring": "oracle-sol-ring"},
            ),
            patch(
                "backend.api.recommend_commanders",
            ) as recommender,
        ):
            response = self.client.post(
                "/recommendations",
                files={
                    "upload": (
                        "collection.csv",
                        csv_data,
                        "text/csv",
                    ),
                },
            )

        self.assertEqual(response.status_code, 400)
        detail = response.json()["detail"]
        self.assertEqual(detail["code"], "CSV_ROW_LIMIT_EXCEEDED")
        self.assertEqual(
            detail["message"],
            "Collection CSV exceeds the 20,000-row limit.",
        )
        recommender.assert_not_called()

    def test_missing_upload_returns_422(self) -> None:
        response = self.client.post("/recommendations")

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"],
            {
                "code": "MISSING_UPLOAD",
                "message": (
                    "A collection CSV must be provided in the upload field."
                ),
                "unmatched_names": [],
                "warnings": [],
            },
        )

    def test_unknown_endpoint_returns_standard_error_shape(self) -> None:
        response = self.client.get("/unknown")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["detail"],
            {
                "code": "HTTP_404",
                "message": "Not Found",
                "unmatched_names": [],
                "warnings": [],
            },
        )


if __name__ == "__main__":
    unittest.main()
