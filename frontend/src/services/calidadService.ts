import api from '../api/axios';
import type { MetricasCalidadDTO, CampoFaltanteDTO } from '../types/calidad';

export const calidadService = {
  getMetricasCalidad: async (): Promise<MetricasCalidadDTO> => {
    const response = await api.get('/api/procesados/metricas/calidad');
    return response.data;
  },

  getCamposFaltantes: async (): Promise<CampoFaltanteDTO[]> => {
    const response = await api.get('/api/procesados/metricas/campos-faltantes');
    return response.data;
  },
};
