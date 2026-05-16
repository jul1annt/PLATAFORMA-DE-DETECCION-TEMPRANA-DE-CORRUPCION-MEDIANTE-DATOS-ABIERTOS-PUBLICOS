import type { Procesado, MetricasCalidad, CampoFaltante, DashboardMetrics, RiskDistribution, TopProvider, AnomalyDistribution } from '../types/procesado';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface PaginatedResult<T> {
  items: T[];
  total: number;
}

export const getProcesados = async (params?: Record<string, string | number>): Promise<PaginatedResult<Procesado>> => {
  const url = new URL(`${API_URL}/api/procesados/search`);
  
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        url.searchParams.append(key, value.toString());
      }
    });
  }

  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error('Error al obtener procesados');
  }
  const data = await response.json();
  return { items: data.items || [], total: data.total || 0 };
};

export const getMetricasCalidad = async (): Promise<MetricasCalidad> => {
  const response = await fetch(`${API_URL}/api/procesados/metricas/calidad`);
  if (!response.ok) {
    throw new Error('Error al obtener métricas de calidad');
  }
  return response.json();
};

export const getCamposFaltantes = async (): Promise<CampoFaltante[]> => {
  const response = await fetch(`${API_URL}/api/procesados/metricas/campos-faltantes`);
  if (!response.ok) {
    throw new Error('Error al obtener campos faltantes');
  }
  return response.json();
};

export const getProcesadoById = async (id: string | number): Promise<Procesado> => {
  const response = await fetch(`${API_URL}/api/procesados/${id}`);
  if (!response.ok) {
    throw new Error('Contrato procesado no encontrado');
  }
  return response.json();
};

export const getAnomaliasByRawSecopId = async (rawSecopId: number): Promise<any[]> => {
  const response = await fetch(`${API_URL}/api/procesados/anomalias/?raw_secop_id=${rawSecopId}`);
  if (!response.ok) {
    return [];
  }
  const data = await response.json();
  return data.items || [];
};

export interface Suggestion {
  text: string;
  type: 'ENTIDAD' | 'PROVEEDOR';
}

export const getAutocompleteSuggestions = (query: string, data: Procesado[]): Suggestion[] => {
  if (!query || query.length < 2) return [];
  const normalizedQuery = query.toLowerCase();
  const suggestionsMap = new Map<string, Suggestion>();

  data.forEach((p) => {
    if (!p) return;
    const entidad = String(p.entidad_normalizada || p.entidad || '');
    const proveedor = String(p.proveedor_normalizado || p.proveedor || '');

    if (entidad && entidad.toLowerCase().includes(normalizedQuery)) {
      if (!suggestionsMap.has(entidad)) {
        suggestionsMap.set(entidad, { text: entidad, type: 'ENTIDAD' });
      }
    }
    if (proveedor && proveedor.toLowerCase().includes(normalizedQuery)) {
      if (!suggestionsMap.has(proveedor)) {
        suggestionsMap.set(proveedor, { text: proveedor, type: 'PROVEEDOR' });
      }
    }
  });

  return Array.from(suggestionsMap.values()).slice(0, 8);
};

// ── Dashboard helpers (client-side aggregations) ────────────────────────────

/** Fetch all items (up to 1000) as a flat array for client-side aggregation. */
const fetchAllItems = async (): Promise<Procesado[]> => {
  const result = await getProcesados({ size: 1000 });
  return Array.isArray(result) ? result : (result as any).items ?? [];
};

export const getDashboardMetrics = async (): Promise<DashboardMetrics> => {
  const metricas = await getMetricasCalidad();
  const items = await fetchAllItems();

  const total = metricas.total_contratos || 0;
  const totalAltoRiesgo = items.filter(
    (p) => p.clasificacion_riesgo === 'ALTO'
  ).length;

  return {
    total_contratos: total,
    pct_incompletos: metricas.porcentaje_incompletos ?? 0,
    pct_sospechosos: metricas.porcentaje_sospechosos ?? 0,
    pct_alto_riesgo: total > 0 ? Math.round((totalAltoRiesgo / total) * 100 * 10) / 10 : 0,
    total_incompletos: metricas.incompletos ?? 0,
    total_sospechosos: metricas.sospechosos ?? 0,
    total_alto_riesgo: totalAltoRiesgo,
    promedio_confianza: metricas.promedio_confianza ?? 0,
  };
};

export const getTopProviders = async (limit = 10): Promise<TopProvider[]> => {
  const items = await fetchAllItems();
  const counts = new Map<string, number>();
  items.forEach((p) => {
    const name = String(p.proveedor_normalizado || p.proveedor || '').trim();
    if (name && name.toUpperCase() !== 'NO DEFINIDO') {
      counts.set(name, (counts.get(name) ?? 0) + 1);
    }
  });
  return Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([name, contracts]) => ({ name, contracts }));
};

export const getRiskDistribution = async (): Promise<RiskDistribution[]> => {
  const items = await fetchAllItems();
  const alto = items.filter((p) => p.clasificacion_riesgo === 'ALTO').length;
  const medio = items.filter((p) => p.clasificacion_riesgo === 'MEDIO').length;
  const bajo = items.filter(
    (p) => !p.clasificacion_riesgo || p.clasificacion_riesgo === 'BAJO'
  ).length;
  return [
    { name: 'Alto Riesgo', value: alto, color: '#ef4444' },
    { name: 'Riesgo Medio', value: medio, color: '#f59e0b' },
    { name: 'Riesgo Bajo', value: bajo, color: '#10b981' },
  ].filter((d) => d.value > 0);
};

export const getAnomalyDistribution = async (): Promise<AnomalyDistribution[]> => {
  const items = await fetchAllItems();
  const incompletos = items.filter((p) => p.es_incompleto === true).length;
  const modificados = items.filter((p) => p.datos_modificados === true).length;
  const sospechosos = items.filter((p) => p.es_sospechoso === true).length;
  const altoRiesgo = items.filter((p) => p.clasificacion_riesgo === 'ALTO').length;
  return [
    { name: 'Incompletos', value: incompletos, color: '#f59e0b' },
    { name: 'Modificados', value: modificados, color: '#ef4444' },
    { name: 'Sospechosos', value: sospechosos, color: '#8b5cf6' },
    { name: 'Alto Riesgo', value: altoRiesgo, color: '#ec4899' },
  ].filter((d) => d.value > 0);
};
