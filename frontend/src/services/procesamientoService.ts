import type { PaginatedProcesamientoLogsDTO } from '../types/procesado';
import type { BackgroundJobAccepted } from '../types/api.generated';
import api from '../api/axios';
import { jobsService } from './jobsService';

export const procesamientoService = {
  /**
   * Obtiene el historial de logs de reprocesamiento paginados
   */
  getLogs: async (page: number = 1, size: number = 20): Promise<PaginatedProcesamientoLogsDTO> => {
    return (await api.get('/api/procesados/logs', { params: { page, size } })).data;
  },

  /**
   * Ejecuta el pipeline de normalización (reprocesamiento)
   */
  reprocesar: async (forzar_reproceso: boolean = false): Promise<BackgroundJobAccepted> => {
    return jobsService.enqueue('/api/procesados/reprocesar', { forzar_reproceso });
  },
};
