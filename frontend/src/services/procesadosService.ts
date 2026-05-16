import type { Procesado, MetricasCalidad, CampoFaltante } from '../types/procesado';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const getProcesados = async (params?: Record<string, string | number>): Promise<Procesado[]> => {
  const url = new URL(`${API_URL}/api/procesados/search`);
  url.searchParams.append('size', '1000');
  
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
  return data.items || [];
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
