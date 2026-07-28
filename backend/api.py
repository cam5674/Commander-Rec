from fastapi import FastAPI, File, HTTPException, UploadFile

from backend.csv_parser import parse_collection_bytes
from backend.data_loader import (
    get_cards_by_id,
    get_commanders,
    get_name_to_id,
)
from backend.theme_scorer import recommend_commanders


MAX_UPLOAD_BYTES = 5 * 1024 * 1024

app = FastAPI(title="Commander Recommender")


@app.post("/recommendations")
async def create_recommendations(
    upload: UploadFile = File(...),
) -> dict:
    csv_data = await upload.read(MAX_UPLOAD_BYTES + 1)

    if len(csv_data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="CSV upload exceeds the 5 MB limit.",
        )

    try:
        collection, unmatched_names = parse_collection_bytes(
            csv_data,
            get_name_to_id(),
            row_limit=20_000,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    results = recommend_commanders(
        collection,
        get_cards_by_id(),
        get_commanders(),
    )
    results["unmatched_names"] = unmatched_names

    return results
