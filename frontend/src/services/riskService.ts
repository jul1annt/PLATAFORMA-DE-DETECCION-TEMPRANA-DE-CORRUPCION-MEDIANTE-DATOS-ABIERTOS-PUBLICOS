import api from '../api/axios';
import axios from 'axios';
import type { RiskStatusResponse, PageResponse } from '../types/api.generated';

export function riskMethodologyUrl(): string {
  const origin = new URL(api.defaults.baseURL || '/', window.location.origin);
  return new URL('/api/riesgo/metodologia', origin).href;
}

export function publicCutHeaders(publicCutId?: string | null): Record<string,string> {
  return publicCutId ? { 'X-Public-Cut': publicCutId } : {};
}

export async function getRiskStatus(signal?: AbortSignal, publicCutId?: string | null): Promise<RiskStatusResponse | null> {
  try {
    return (await api.get('/api/riesgo/estado', { signal, headers: publicCutHeaders(publicCutId) })).data;
  } catch (error) {
    // Older local releases expose the contract read API without the new risk routes.
    // Keep public data browsing available and leave risk evidence explicitly pending.
    if (axios.isAxiosError(error) && error.response?.status === 404) return null;
    throw error;
  }
}

export async function getRiskResults(rawIds: number[], signal?: AbortSignal, cutId?: string, publicCutId?: string | null): Promise<PageResponse> {
  const params = new URLSearchParams({ limit: '200' });
  if (cutId) params.set('cut_id', cutId);
  for (const id of rawIds) params.append('raw_secop_ids', String(id));
  return (await api.get('/api/riesgo/resultados', { params, signal, headers: publicCutHeaders(publicCutId) })).data;
}
