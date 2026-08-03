from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    theme_ratio: float = Field(ge=0.0, le=1.0)
    theme_contribution: float = Field(ge=0.0)
    color_ratio: float = Field(ge=0.0, le=1.0)
    color_contribution: float = Field(ge=0.0)
    popularity_score: float = Field(ge=0.0, le=1.0)
    popularity_contribution: float = Field(ge=0.0)
    final_score: float = Field(ge=0.0, le=1.0)


class SupportingCard(BaseModel):
    oracle_id: str
    scryfall_id: str | None = None
    scryfall_url: str
    image_url: str | None = None
    name: str
    quantity: int = Field(ge=1)
    edhrec_rank: int | None = Field(default=None, ge=1)


class ThemeSupport(BaseModel):
    theme: str
    supporting_card_count: int = Field(ge=0)
    example_cards: list[SupportingCard] = Field(max_length=5)


class CommanderRecommendation(BaseModel):
    oracle_id: str
    scryfall_id: str | None = None
    scryfall_url: str
    name: str
    image_url: str | None = None
    themes: list[str]
    matching_themes: list[str]
    edhrec_rank: int | None = Field(default=None, ge=1)
    color_identity: list[str]
    owned: bool
    theme_match_score: int = Field(ge=0)
    theme_support: list[ThemeSupport]
    score_breakdown: ScoreBreakdown


class CSVWarningResponse(BaseModel):
    code: str
    message: str
    row: int = Field(ge=2)
    value: str | None = None


class APIErrorDetail(BaseModel):
    code: str
    message: str
    unmatched_names: list[str] = Field(default_factory=list)
    warnings: list[CSVWarningResponse] = Field(default_factory=list)


class APIErrorResponse(BaseModel):
    detail: APIErrorDetail


class APIConfigResponse(BaseModel):
    max_upload_bytes: int = Field(gt=0)
    max_csv_rows: int = Field(gt=0)
    accepted_file_extensions: list[str]


class RecommendationResponse(BaseModel):
    unique_cards: int = Field(ge=0)
    total_cards: int = Field(ge=0)
    theme_scores: dict[str, int]
    top_themes: list[str]
    recommendations: list[CommanderRecommendation]
    unmatched_names: list[str]
    warnings: list[CSVWarningResponse]
