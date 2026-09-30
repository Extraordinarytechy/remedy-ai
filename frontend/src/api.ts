import type { ExtractResponse, NormalizedCase, RemedyEvaluation, SourcesResponse } from './types';

/*
 * Privacy note on photos: photoToBase64 redraws each photo on a canvas and re-encodes it as JPEG
 * before upload. That drops EXIF metadata such as GPS location and camera details. Nothing is sent
 * until the user clicks "Read photos"; choosing a file only keeps it in the browser.
 */

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
  /** The server re-evaluates the case itself; only the case is sent. */
  async claimPdf(c: NormalizedCase): Promise<Blob> {
    const res = await fetch(`${API_BASE}/api/generate-package`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ case: c }),
    });
    if (!res.ok || !(res.headers.get('content-type') ?? '').includes('application/pdf')) {
      let detail = `Could not prepare the claim PDF (${res.status}).`;
      try {
        const body = await res.json();
        if (typeof body?.detail === 'string') detail = body.detail;
      } catch {
        /* not JSON */
      }
      throw new Error(detail);
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
