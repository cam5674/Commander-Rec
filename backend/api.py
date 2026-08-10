import os
from dataclasses import asdict
from pathlib import Path
from typing import NoReturn

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.csv_parser import CSVRowLimitError, parse_collection_bytes
from backend.data_loader import (
    get_cards_by_id,
    get_commanders,
    get_name_to_id,
)
from backend.models import (
    APIConfigResponse,
    APIErrorDetail,
    APIErrorResponse,
    RecommendationResponse,
)
from backend.theme_scorer import (
    MAX_RECOMMENDATIONS,
    MIN_THEME_MATCH_RATIO,
    recommend_commanders,
)

DEFAULT_FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
DEFAULT_MAX_UPLOAD_BYTES = 4 * 1024 * 1024
DEFAULT_API_DOCS_ENABLED = True


def get_allowed_origins() -> list[str]:
    configured_origins = os.getenv("ALLOWED_ORIGINS")
    if configured_origins is None:
        return DEFAULT_FRONTEND_ORIGINS.copy()

    origins = [
        origin.strip()
        for origin in configured_origins.split(",")
        if origin.strip()
    ]
    if not origins:
        raise RuntimeError("ALLOWED_ORIGINS must contain at least one origin.")

    return origins


def get_max_upload_bytes() -> int:
    configured_limit = os.getenv("MAX_UPLOAD_BYTES")
    if configured_limit is None:
        return DEFAULT_MAX_UPLOAD_BYTES

    try:
        limit = int(configured_limit)
    except ValueError as error:
        raise RuntimeError("MAX_UPLOAD_BYTES must be a whole number.") from error

    if limit <= 0:
        raise RuntimeError("MAX_UPLOAD_BYTES must be greater than zero.")

    return limit


def get_api_docs_enabled() -> bool:
    configured_value = os.getenv("ENABLE_API_DOCS")
    if configured_value is None:
        return DEFAULT_API_DOCS_ENABLED

    normalized_value = configured_value.strip().casefold()
    if normalized_value in {"1", "true", "yes", "on"}:
        return True
    if normalized_value in {"0", "false", "no", "off"}:
        return False

    raise RuntimeError(
        "ENABLE_API_DOCS must be a boolean value such as true or false."
    )


ALLOWED_ORIGINS = get_allowed_origins()
MAX_UPLOAD_BYTES = get_max_upload_bytes()
API_DOCS_ENABLED = get_api_docs_enabled()
MAX_CSV_ROWS = 20_000
ACCEPTED_FILE_EXTENSIONS = [".csv"]

app = FastAPI(
    title="Commander Recommender",
    docs_url="/docs" if API_DOCS_ENABLED else None,
    redoc_url="/redoc" if API_DOCS_ENABLED else None,
    openapi_url="/openapi.json" if API_DOCS_ENABLED else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.add_middleware(GZipMiddleware)


def raise_api_error(
    status_code: int,
    code: str,
    message: str,
    *,
    unmatched_names: list[str] | None = None,
    warnings: list[dict] | None = None,
) -> NoReturn:
    detail = APIErrorDetail(
        code=code,
        message=message,
        unmatched_names=unmatched_names or [],
        warnings=warnings or [],
    )
    raise HTTPException(
        status_code=status_code,
        detail=detail.model_dump(),
    )


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(
    _request: Request,
    exception: StarletteHTTPException,
) -> JSONResponse:
    if (
        isinstance(exception.detail, dict)
        and "code" in exception.detail
        and "message" in exception.detail
    ):
        detail = APIErrorDetail.model_validate(exception.detail)
    else:
        detail = APIErrorDetail(
            code=f"HTTP_{exception.status_code}",
            message=str(exception.detail),
        )

    return JSONResponse(
        status_code=exception.status_code,
        content={"detail": detail.model_dump()},
        headers=exception.headers,
    )


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    _request: Request,
    exception: RequestValidationError,
) -> JSONResponse:
    missing_upload = any(
        error.get("type") == "missing"
        and tuple(error.get("loc", ()))[-1:] == ("upload",)
        for error in exception.errors()
    )

    if missing_upload:
        detail = APIErrorDetail(
            code="MISSING_UPLOAD",
            message="A collection CSV must be provided in the upload field.",
        )
    else:
        detail = APIErrorDetail(
            code="INVALID_REQUEST",
            message="The request could not be validated.",
        )

    return JSONResponse(
        status_code=422,
        content={"detail": detail.model_dump()},
    )


@app.get(
    "/config",
    response_model=APIConfigResponse,
)
def get_api_config() -> dict:
    return {
        "max_upload_bytes": MAX_UPLOAD_BYTES,
        "max_csv_rows": MAX_CSV_ROWS,
        "accepted_file_extensions": ACCEPTED_FILE_EXTENSIONS,
    }


@app.post(
    "/recommendations",
    response_model=RecommendationResponse,
    responses={
        400: {"model": APIErrorResponse},
        413: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
)
async def create_recommendations(
    upload: UploadFile = File(...),
) -> dict:
    file_extension = Path(upload.filename or "").suffix.casefold()
    if file_extension not in ACCEPTED_FILE_EXTENSIONS:
        raise_api_error(
            400,
            "UNSUPPORTED_FILE_TYPE",
            "The uploaded collection must be a CSV file.",
        )

    csv_data = await upload.read(MAX_UPLOAD_BYTES + 1)

    if len(csv_data) > MAX_UPLOAD_BYTES:
        raise_api_error(
            413,
            "UPLOAD_TOO_LARGE",
            f"CSV upload exceeds the {MAX_UPLOAD_BYTES}-byte limit.",
        )

    try:
        parse_result = parse_collection_bytes(
            csv_data,
            get_name_to_id(),
            row_limit=MAX_CSV_ROWS,
        )
    except CSVRowLimitError as error:
        raise_api_error(
            400,
            "CSV_ROW_LIMIT_EXCEEDED",
            str(error),
        )
    except ValueError as error:
        raise_api_error(
            400,
            "INVALID_CSV",
            str(error),
        )

    if not parse_result.collection:
        raise_api_error(
            400,
            "NO_RECOGNIZED_CARDS",
            "The uploaded CSV did not contain any recognized cards.",
            unmatched_names=parse_result.unmatched_names,
            warnings=[
                asdict(warning)
                for warning in parse_result.warnings
            ],
        )

    results = recommend_commanders(
        parse_result.collection,
        get_cards_by_id(),
        get_commanders(),
        top_n=MAX_RECOMMENDATIONS,
        min_theme_ratio=MIN_THEME_MATCH_RATIO,
    )
    results["unmatched_names"] = parse_result.unmatched_names
    results["warnings"] = [
        asdict(warning)
        for warning in parse_result.warnings
    ]

    return results
