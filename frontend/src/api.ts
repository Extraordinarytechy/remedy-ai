import type { ExtractResponse, NormalizedCase, RemedyEvaluation, SourcesResponse } from './types';

// Same origin in production (CloudFront routes /api/* to the API). The Vite dev server
// proxies /api to the local backend. VITE_API_BASE_URL overrides both if set.
const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  });
  const type = res.headers.get('content-type') ?? '';
  if (!type.includes('application/json')) {
    throw new Error(`The RemedyAI API returned ${res.status} without JSON.`);
  }
  const body = await res.json();
  if (!res.ok) {
    const detail = typeof body?.detail === 'string' ? body.detail : `Request failed (${res.status}).`;
    throw new Error(detail);
  }
  return body as T;
}

export const api = {
  fixtures: () => request<Record<string, NormalizedCase>>('/api/fixtures'),
  sources: () => request<SourcesResponse>('/api/sources'),
  evaluate: (c: NormalizedCase) => request<RemedyEvaluation>('/api/evaluate', { method: 'POST', body: JSON.stringify(c) }),
  extract: (payload: { receipt_base64?: string; defect_image_base64?: string; product_hint?: string }) =>
    request<ExtractResponse>('/api/extract', { method: 'POST', body: JSON.stringify(payload) }),
  async claimPdf(c: NormalizedCase, evaluation: RemedyEvaluation): Promise<Blob> {
    const res = await fetch(`${API_BASE}/api/generate-package`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ case: c, evaluation }),
    });
    if (!res.ok || !(res.headers.get('content-type') ?? '').includes('application/pdf')) {
      throw new Error(`Could not generate the claim PDF (${res.status}).`);
    }
    return res.blob();
  },
};

/** Downscales a photo in the browser to a JPEG (max 1600 px) and returns base64 without the data-URL prefix. */
export async function photoToBase64(file: File, maxSide = 1600): Promise<string> {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('This browser cannot process images.');
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
  return dataUrl.split(',', 2)[1];
}
