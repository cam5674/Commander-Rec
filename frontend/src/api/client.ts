import type { APIErrorDetail, AppConfig, RecommendationResponse } from '../types/api';

const API_BASE_URL = 'http://127.0.0.1:8000';

export class APIError extends Error {
  readonly status: number;
  readonly detail: APIErrorDetail;

  constructor(status: number, detail: APIErrorDetail) {
    super(detail.message);
    this.status = status;
    this.detail = detail;
  }
}

async function readErrorDetail(response: Response): Promise<APIErrorDetail> {
  try {
    const body = await response.json();
    if (body?.detail?.code && body?.detail?.message) {
      return body.detail as APIErrorDetail;
    }
  } catch {
    // Body wasn't JSON — fall through to the generic detail below.
  }

  return {
    code: `HTTP_${response.status}`,
    message: response.statusText || 'The request failed.',
    unmatched_names: [],
    warnings: [],
  };
}

export async function fetchConfig(): Promise<AppConfig> {
  const response = await fetch(`${API_BASE_URL}/config`);

  if (!response.ok) {
    throw new APIError(response.status, await readErrorDetail(response));
  }

  return response.json();
}

export async function submitCollection(file: File): Promise<RecommendationResponse> {
  const formData = new FormData();
  formData.append('upload', file);

  const response = await fetch(`${API_BASE_URL}/recommendations`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new APIError(response.status, await readErrorDetail(response));
  }

  return response.json();
}
