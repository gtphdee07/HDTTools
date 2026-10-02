import type { ScaleTicketData, TrailerTagData, TruckTagData } from './types';

const API_BASE_URL = 'http://localhost:8000';

async function postFile<T>(path: string, file: File): Promise<T> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE_URL}${path}`, { method: 'POST', body: formData });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

export function extractTruckTag(file: File): Promise<TruckTagData> {
  return postFile('/api/extract/truck-tag', file);
}

export function extractTrailerTag(file: File): Promise<TrailerTagData> {
  return postFile('/api/extract/trailer-tag', file);
}

export function extractScaleTicket(file: File): Promise<ScaleTicketData> {
  return postFile('/api/extract/scale-ticket', file);
}

