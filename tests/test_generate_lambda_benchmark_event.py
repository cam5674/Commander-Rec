import base64
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.lambda_handler import handler
from scripts.generate_lambda_benchmark_event import (
    DEFAULT_BOUNDARY,
    build_http_api_event,
)


class LambdaBenchmarkEventTests(unittest.TestCase):
    def test_builds_base64_multipart_http_api_v2_event(self) -> None:
        csv_data = b"Count,Name\n2,Sol Ring\n"

        event = build_http_api_event(csv_data, "collection.csv")
        multipart_body = base64.b64decode(event["body"])

        self.assertEqual(event["version"], "2.0")
        self.assertEqual(event["routeKey"], "POST /recommendations")
        self.assertEqual(event["rawPath"], "/recommendations")
        self.assertTrue(event["isBase64Encoded"])
        self.assertEqual(
            event["headers"]["content-type"],
            f"multipart/form-data; boundary={DEFAULT_BOUNDARY}",
        )
        self.assertEqual(
            event["headers"]["content-length"],
            str(len(multipart_body)),
        )
        self.assertIn(
            b'Content-Disposition: form-data; name="upload"; '
            b'filename="collection.csv"',
            multipart_body,
        )
        self.assertIn(csv_data, multipart_body)
        self.assertTrue(
            multipart_body.endswith(
                f"\r\n--{DEFAULT_BOUNDARY}--\r\n".encode("ascii")
            )
        )

    def test_generated_event_completes_mangum_upload_flow(self) -> None:
        event = build_http_api_event(
            b"Count,Name\n2,Sol Ring\n",
            "collection.csv",
        )
        recommendation_result = {
            "unique_cards": 1,
            "total_cards": 2,
            "theme_scores": {"artifacts": 1},
            "top_themes": ["artifacts"],
            "recommendations": [],
        }
        lambda_context = SimpleNamespace(
            aws_request_id="phase7-test-request",
            function_name="commander-rec-cdk-api",
            function_version="$LATEST",
            invoked_function_arn=(
                "arn:aws:lambda:us-west-1:000000000000:"
                "function:commander-rec-cdk-api"
            ),
            memory_limit_in_mb="1024",
        )

        with (
            patch(
                "backend.api.get_name_to_id",
                return_value={"sol ring": "oracle-sol-ring"},
            ),
            patch("backend.api.get_cards_by_id", return_value={}),
            patch(
                "backend.api.get_commanders",
                return_value=["oracle-commander"],
            ),
            patch(
                "backend.api.recommend_commanders",
                return_value=recommendation_result,
            ),
        ):
            response = handler(event, lambda_context)

        self.assertEqual(response["statusCode"], 200)
        self.assertFalse(response["isBase64Encoded"])
        response_body = json.loads(response["body"])
        self.assertEqual(response_body["unique_cards"], 1)
        self.assertEqual(response_body["total_cards"], 2)
        self.assertEqual(response_body["recommendations"], [])
        self.assertEqual(response_body["unmatched_names"], [])
        self.assertEqual(response_body["warnings"], [])

    def test_rejects_files_above_configured_upload_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "exceeds"):
            build_http_api_event(
                b"Count,Name\n1,Sol Ring\n",
                "collection.csv",
                max_upload_bytes=5,
            )


if __name__ == "__main__":
    unittest.main()
