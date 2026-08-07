import type { APIErrorDetail, AppConfig, RecommendationResponse } from '../types/api';

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
const API_BASE_URL = (configuredBaseUrl || '/api').replace(/\/$/, '');

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

export async function fetchConfig(signal?: AbortSignal): Promise<AppConfig> {
  const response = await fetch(`${API_BASE_URL}/config`, { signal });

  if (!response.ok) {
    throw new APIError(response.status, await readErrorDetail(response));
  }

  return response.json();
}

export async function submitCollection(
  file: File,
  signal?: AbortSignal,
): Promise<RecommendationResponse> {
  const formData = new FormData();
  formData.append('upload', file);

  const response = await fetch(`${API_BASE_URL}/recommendations`, {
    method: 'POST',
    body: formData,
    signal,
  });

  if (!response.ok) {
    throw new APIError(response.status, await readErrorDetail(response));
  }

  return response.json();
}
