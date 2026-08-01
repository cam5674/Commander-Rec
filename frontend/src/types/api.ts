// Mirrors backend/models.py — keep in sync with the FastAPI response contract.

export interface ScoreBreakdown {
  theme_ratio: number;
  theme_contribution: number;
  color_ratio: number;
  color_contribution: number;
  popularity_score: number;
  popularity_contribution: number;
  final_score: number;
}

export interface SupportingCard {
  oracle_id: string;
  name: string;
  quantity: number;
  edhrec_rank: number | null;
}

export interface ThemeSupport {
  theme: string;
  supporting_card_count: number;
  example_cards: SupportingCard[];
}

export interface CommanderRecommendation {
  oracle_id: string;
  name: string;
  image_url: string | null;
  themes: string[];
  matching_themes: string[];
  edhrec_rank: number | null;
  color_identity: string[];
  owned: boolean;
  theme_match_score: number;
  theme_support: ThemeSupport[];
  score_breakdown: ScoreBreakdown;
}

export interface CSVWarning {
  code: string;
  message: string;
  row: number;
  value: string | null;
}

export interface RecommendationResponse {
  unique_cards: number;
  total_cards: number;
  theme_scores: Record<string, number>;
  top_themes: string[];
  recommendations: CommanderRecommendation[];
  unmatched_names: string[];
  warnings: CSVWarning[];
}

export interface APIErrorDetail {
  code: string;
  message: string;
  unmatched_names: string[];
  warnings: CSVWarning[];
}

export interface AppConfig {
  max_upload_bytes: number;
  max_csv_rows: number;
  accepted_file_extensions: string[];
}
