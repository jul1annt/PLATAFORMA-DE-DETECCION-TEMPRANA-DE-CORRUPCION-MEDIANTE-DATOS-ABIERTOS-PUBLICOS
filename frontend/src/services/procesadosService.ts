import type { Procesado, MetricasCalidad, CampoFaltante } from '../types/procesado';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const getProcesados = async (): Promise<Procesado[]> => {
  const response = await fetch(`${API_URL}/api/procesados/search?size=1000`);
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
