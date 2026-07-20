#TODO: Make download script that makes a GET request to /bulk-data to download cards locally "https://scryfall.com/docs/api/bulk-data"

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import requests

API_DOWNLOAD_URL = "https://api.scryfall.com/bulk-data"

CHUNK_SIZE = 1024 * 1024

HEADERS = {
    "User-Agent": "MTGCommanderRecommender/0.1",
    "Accept": "application/json",
}



DEFAULT_OUTPUT_PATH = Path("data/raw/default_cards.json")

# Number of bytes downloaded at a time.
CHUNK_SIZE = 1024 * 1024  # 1 MB


def get_default_cards_metadata() -> dict[str, Any]:
    """
    Retrieve metadata for Scryfall's default_cards bulk-data file.
    """
    response = requests.get(
        API_DOWNLOAD_URL,
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()

    result = response.json()
    print("response success")
    # can change "type" to download other files from bulk-data
    for bulk_file in result["data"]:
        if bulk_file["type"] == "default_cards":
            return bulk_file

    raise RuntimeError(
        "Scryfall did not return a default_cards bulk-data entry."
    )


def download_file(download_url: str, output_path: Path) -> None:
    """
    Stream a remote file to disk without loading it all into memory.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = output_path.with_suffix(
        output_path.suffix + ".part"
    )

    with requests.get(
        download_url,
        headers=HEADERS,
        stream=True,
        timeout=(10, 300),
    ) as response:
        response.raise_for_status()

        total_bytes = int(
            response.headers.get("Content-Length", 0)
        )
        downloaded_bytes = 0

        with temporary_path.open("wb") as output_file:
            for chunk in response.iter_content(
                chunk_size=CHUNK_SIZE
            ):
                if not chunk:
                    continue

                output_file.write(chunk)
                downloaded_bytes += len(chunk)

                print_progress(
                    downloaded_bytes,
                    total_bytes,
                )

    temporary_path.replace(output_path)
    print(f"\nSaved bulk data to: {output_path}")


def print_progress(
    downloaded_bytes: int,
    total_bytes: int,
) -> None:
    """
    Print a simple download progress indicator.
    """
    downloaded_mb = downloaded_bytes / (1024 * 1024)

    if total_bytes:
        total_mb = total_bytes / (1024 * 1024)
        percentage = downloaded_bytes / total_bytes * 100

        message = (
            f"\rDownloaded {downloaded_mb:.1f} MB "
            f"of {total_mb:.1f} MB "
            f"({percentage:.1f}%)"
        )
    else:
        message = f"\rDownloaded {downloaded_mb:.1f} MB"

    print(message, end="", flush=True)


def main() -> None:
    try:
        print("Retrieving Scryfall bulk-data metadata...")

        metadata = get_default_cards_metadata()

        print(f"Bulk file: {metadata['name']}")
        print(f"Updated: {metadata['updated_at']}")
        print(f"Download URL: {metadata['download_uri']}")
        print("Starting download...")

        download_file(
            download_url=metadata["download_uri"],
            output_path=DEFAULT_OUTPUT_PATH,
        )

    except requests.Timeout:
        print(
            "\nThe request timed out.",
            file=sys.stderr,
        )
        sys.exit(1)

    except requests.HTTPError as error:
        print(
            f"\nScryfall returned an HTTP error: {error}",
            file=sys.stderr,
        )
        sys.exit(1)

    except requests.RequestException as error:
        print(
            f"\nA network error occurred: {error}",
            file=sys.stderr,
        )
        sys.exit(1)

    except (KeyError, ValueError, RuntimeError) as error:
        print(
            f"\nCould not process the Scryfall response: {error}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()




