import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api import app


class APITests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

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
        self.assertIn(
            "Unsupported CSV format",
            response.json()["detail"],
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

    def test_missing_upload_returns_422(self) -> None:
        response = self.client.post("/recommendations")

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
