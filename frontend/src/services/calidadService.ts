import type { MetricasCalidadDTO, CampoFaltanteDTO } from '../types/calidad';
import type { BackgroundJobAccepted } from '../types/api.generated';
import api from '../api/axios';
import { procesamientoService } from './procesamientoService';

export const calidadService = {
  getMetricasCalidad: async (signal?: AbortSignal): Promise<MetricasCalidadDTO> => {
    const response = await api.get('/api/procesados/metricas/calidad', { signal });
    return response.data;
  },

  getCamposFaltantes: async (signal?: AbortSignal): Promise<CampoFaltanteDTO[]> => {
    const response = await api.get('/api/procesados/metricas/campos-faltantes', { signal });
    return response.data;
  },

  reprocesar: async (forzar: boolean = false): Promise<BackgroundJobAccepted> => {
    return procesamientoService.reprocesar(forzar);
  },
};
