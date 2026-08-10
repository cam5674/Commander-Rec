"""Generate a Lambda HTTP API v2 event for a multipart CSV benchmark."""

import argparse
import base64
import json
from pathlib import Path
from typing import Sequence


DEFAULT_BOUNDARY = "CommanderRecPhase7Boundary"
DEFAULT_MAX_UPLOAD_BYTES = 4 * 1024 * 1024
DEFAULT_HOST = "benchmark.execute-api.us-west-1.amazonaws.com"


def build_multipart_body(
    csv_data: bytes,
    filename: str,
    *,
    boundary: str = DEFAULT_BOUNDARY,
) -> bytes:
    if not csv_data:
        raise ValueError("Benchmark CSV must not be empty.")
    if Path(filename).suffix.casefold() != ".csv":
        raise ValueError("Benchmark input must use a .csv extension.")
    if any(character in filename for character in ('"', "\r", "\n")):
        raise ValueError("Benchmark filename contains unsupported characters.")
    if not boundary or any(character in boundary for character in ("\r", "\n")):
        raise ValueError("Multipart boundary must be a non-empty single line.")

    prefix = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="upload"; filename="{filename}"\r\n'
        "Content-Type: text/csv\r\n"
        "\r\n"
    ).encode("utf-8")
    suffix = f"\r\n--{boundary}--\r\n".encode("ascii")
    return prefix + csv_data + suffix


def build_http_api_event(
    csv_data: bytes,
    filename: str,
    *,
    boundary: str = DEFAULT_BOUNDARY,
    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
) -> dict[str, object]:
    if max_upload_bytes <= 0:
        raise ValueError("Maximum upload size must be greater than zero.")
    if len(csv_data) > max_upload_bytes:
        raise ValueError(
            f"Benchmark CSV exceeds the {max_upload_bytes}-byte upload limit."
        )

    multipart_body = build_multipart_body(
        csv_data,
        filename,
        boundary=boundary,
    )
    return {
        "version": "2.0",
        "routeKey": "POST /recommendations",
        "rawPath": "/recommendations",
        "rawQueryString": "",
        "cookies": [],
        "headers": {
            "accept": "application/json",
            "content-length": str(len(multipart_body)),
            "content-type": f"multipart/form-data; boundary={boundary}",
            "host": DEFAULT_HOST,
            "x-forwarded-for": "127.0.0.1",
            "x-forwarded-port": "443",
            "x-forwarded-proto": "https",
        },
        "requestContext": {
            "accountId": "benchmark",
            "apiId": "benchmark",
            "domainName": DEFAULT_HOST,
            "domainPrefix": "benchmark",
            "http": {
                "method": "POST",
                "path": "/recommendations",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "commander-rec-phase7-benchmark",
            },
            "requestId": "commander-rec-phase7-benchmark",
            "routeKey": "POST /recommendations",
            "stage": "$default",
            "time": "01/Jan/2026:00:00:00 +0000",
            "timeEpoch": 1767225600000,
        },
        "body": base64.b64encode(multipart_body).decode("ascii"),
        "isBase64Encoded": True,
    }


def default_output_path(csv_path: Path) -> Path:
    return Path("tmp/phase7") / f"{csv_path.stem}-event.json"


def write_benchmark_event(
    csv_path: Path,
    output_path: Path,
    *,
    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
) -> tuple[int, int]:
    csv_data = csv_path.read_bytes()
    event = build_http_api_event(
        csv_data,
        csv_path.name,
        max_upload_bytes=max_upload_bytes,
    )
    serialized_event = json.dumps(
        event,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(serialized_event)
    return len(csv_data), len(serialized_event)


def parse_args(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a base64-encoded API Gateway HTTP API v2 event for "
            "direct Lambda benchmarking."
        )
    )
    parser.add_argument("csv_path", type=Path, help="Collection CSV to upload")
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON path; defaults to tmp/phase7/<csv-name>-event.json",
    )
    parser.add_argument(
        "--max-upload-bytes",
        type=int,
        default=DEFAULT_MAX_UPLOAD_BYTES,
        help="Maximum accepted raw CSV size",
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    args = parse_args(arguments)
    output_path = args.output or default_output_path(args.csv_path)

    try:
        csv_size, event_size = write_benchmark_event(
            args.csv_path,
            output_path,
            max_upload_bytes=args.max_upload_bytes,
        )
    except (OSError, ValueError) as error:
        raise SystemExit(f"Could not generate benchmark event: {error}") from error

    print(f"Input CSV: {args.csv_path}")
    print(f"Raw CSV bytes: {csv_size:,}")
    print(f"Event JSON bytes: {event_size:,}")
    print(f"Wrote Lambda benchmark event to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
