import type {
  BreakdownItem,
  HistoryEntry,
  Rig,
  ScaleTicketData,
  TrailerTagData,
  TruckTagData,
  VerdictInfo,
} from './types';

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

interface RigOut {
  id: number;
  truck_name: string;
  trailer_name: string;
}

export async function fetchRigs(): Promise<Rig[]> {
  const res = await fetch(`${API_BASE_URL}/api/rigs`);
  if (!res.ok) throw new Error('Failed to load rigs.');
  const rigs: RigOut[] = await res.json();
  return rigs.map((r) => ({ id: String(r.id), truckName: r.truck_name, trailerName: r.trailer_name }));
}

interface CheckOut {
  id: number;
  truck_name: string;
  trailer_name: string;
  date: string;
  verdict: 'pass' | 'fail';
}

export async function fetchHistory(): Promise<HistoryEntry[]> {
  const res = await fetch(`${API_BASE_URL}/api/checks`);
  if (!res.ok) throw new Error('Failed to load history.');
  const checks: CheckOut[] = await res.json();
  return checks.map((c) => ({
    id: String(c.id),
    date: c.date,
    truckName: c.truck_name,
    trailerName: c.trailer_name,
    verdict: c.verdict,
  }));
}

export interface CreateCheckResult {
  id: string;
  date: string;
  verdict: 'pass' | 'fail';
  breakdownItems: BreakdownItem[];
  verdictInfo: VerdictInfo;
}

export async function createCheck(
  rigId: string,
  truck: TruckTagData,
  trailer: TrailerTagData,
  scale: ScaleTicketData,
): Promise<CreateCheckResult> {
  const res = await fetch(`${API_BASE_URL}/api/checks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rig_id: Number(rigId), truck, trailer, scale }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${res.status})`);
  }
  const data = await res.json();
  return { id: String(data.id), date: data.date, verdict: data.verdict, breakdownItems: data.breakdownItems, verdictInfo: data.verdictInfo };
}
