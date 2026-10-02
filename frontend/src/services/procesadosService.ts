import api from '../api/axios';
import type { ExportJobAccepted, ExportJobStatus } from '../types/api.generated';
import type {
  AnomaliaContrato,
  AnomalyDistribution,
  CampoFaltante,
  DashboardMetrics,
  MetricasCalidad,
  Procesado,
  RiskDistribution,
  TopProvider,
  QualityFilterType,
} from '../types/procesado';

export function toProcesadosApiParams(searchParams: URLSearchParams): Record<string, string> {
  const mapping: Record<string, string> = {
    montoMin: 'valor_min', montoMax: 'valor_max',
    fechaDesde: 'fecha_inicio', fechaHasta: 'fecha_fin',
    modalidad: 'modalidad', entidad: 'entidad', proveedor: 'proveedor',
    estado: 'estado', nivelConfianzaMin: 'nivel_confianza_min',
    nivelConfianzaMax: 'nivel_confianza_max', q: 'q',
    limit: 'limit', offset: 'offset', sort: 'sort', order: 'order',
  };
  const params: Record<string, string> = {};
  for (const [from, to] of Object.entries(mapping)) {
    const value = searchParams.get(from);
    if (value) params[to] = value;
  }
  const filter = searchParams.get('calidad') as QualityFilterType | null;
  if (filter === 'INCOMPLETOS') params.solo_incompletos = 'true';
  if (filter === 'SOSPECHOSOS') params.solo_sospechosos = 'true';
  if (filter === 'ALTO_RIESGO') params.solo_alto_riesgo = 'true';
  return params;
}

export async function downloadProcesadosExport(
  format: 'csv' | 'xlsx' | 'pdf',
  params: Record<string, string>,
): Promise<void> {
  const { data: job } = await api.post<ExportJobAccepted>(`/api/procesados/export/${format}/jobs`, undefined, {
    params,
  });

  const headers = { 'X-Export-Token': job.access_token };
  const stopAt = Date.now() + 30 * 60 * 1000;
  let filename = `contratos_calidad.${format}`;
  while (Date.now() < stopAt && Date.now() < Date.parse(job.expires_at)) {
    const { data: status } = await api.get<ExportJobStatus>(job.status_url, { headers });

    if (status.status === 'ERROR') {
      throw new Error(status.error_message || 'No fue posible generar la exportación.');
    }
    if (status.status === 'EXITOSO') {
      const result = status.result as { filename?: string } | null;
      filename = result?.filename || filename;
      const { data } = await api.get(job.download_url, { headers, responseType: 'blob' });
      const url = URL.createObjectURL(data as Blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      return;
    }

    await new Promise((resolve) => window.setTimeout(resolve, 1500));
  }

  throw new Error('La exportación sigue en proceso. Inténtalo de nuevo más tarde.');
}

export interface PaginatedResult<T> {
  items: T[];
  total: number;
}

export interface Suggestion {
  text: string;
  type: 'ENTIDAD' | 'PROVEEDOR';
}

export async function getProcesados(
  params?: Record<string, string | number>,
  signal?: AbortSignal,
): Promise<PaginatedResult<Procesado>> {
  const response = await api.get('/api/procesados/search', { params, signal });
  return { items: response.data.items ?? [], total: response.data.total ?? 0 };
}

export async function getMetricasCalidad(signal?: AbortSignal): Promise<MetricasCalidad> {
  return (await api.get('/api/procesados/metricas/calidad', { signal })).data;
}

export async function getCamposFaltantes(signal?: AbortSignal): Promise<CampoFaltante[]> {
  return (await api.get('/api/procesados/metricas/campos-faltantes', { signal })).data;
}

export async function getProcesadoById(id: string | number): Promise<Procesado> {
  return (await api.get(`/api/procesados/${id}`)).data;
}

export async function getAnomaliasByRawSecopId(rawSecopId: number): Promise<AnomaliaContrato[]> {
  const response = await api.get('/api/procesados/anomalias/', {
    params: { raw_secop_id: rawSecopId },
  });
  return response.data.items ?? [];
}

export async function getAutocompleteSuggestions(query: string, signal?: AbortSignal): Promise<Suggestion[]> {
  if (query.trim().length < 2) return [];
  return (await api.get('/api/procesados/autocomplete', { params: { q: query.trim() }, signal })).data;
}

export async function getDashboardMetrics(signal?: AbortSignal): Promise<DashboardMetrics> {
  return (await api.get('/api/procesados/metricas/dashboard', { signal })).data;
}

export async function getTopProviders(limit = 10, signal?: AbortSignal): Promise<TopProvider[]> {
  return (await api.get('/api/procesados/metricas/top-proveedores', { params: { limit }, signal })).data;
}

export async function getRiskDistribution(signal?: AbortSignal): Promise<RiskDistribution[]> {
  return (await api.get('/api/procesados/metricas/distribucion-riesgo', { signal })).data;
}

export async function getAnomalyDistribution(signal?: AbortSignal): Promise<AnomalyDistribution[]> {
  return (await api.get('/api/procesados/metricas/distribucion-anomalias', { signal })).data;
}
