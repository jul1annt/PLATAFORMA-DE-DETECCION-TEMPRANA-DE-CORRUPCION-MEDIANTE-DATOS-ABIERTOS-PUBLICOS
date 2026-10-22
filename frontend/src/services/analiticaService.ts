import api from '../api/axios';
import { jobsService } from './jobsService';
import type {
  AdjudicacionDirectaCalculoRequest as ApiAdjudicacionDirectaCalculoRequest,
  DuplicadoCalculoRequest as ApiDuplicadoCalculoRequest,
  DuplicadoResumenResponse,
  EjecucionAnaliticaEstadoResponse,
  OutlierCalculoRequest as ApiOutlierCalculoRequest,
  PesoAnomaliaResponse,
  ProveedorDirectaResumenResponse,
  RiesgoGlobalResumenResponse,
  RunResumenResponse,
} from '../types/api.generated';

export type OutlierCalculoRequest = Omit<ApiOutlierCalculoRequest, 'campo' | 'fecha_campo'> & {
  campo: 'valor_total_normalizado' | 'precio_base_normalizado' | 'nivel_confianza' | 'cantidad_campos_faltantes';
  fecha_campo?: 'fecha_publicacion_normalizada' | 'fecha_adjudicacion_normalizada' | null;
};
export type DuplicadoCalculoRequest = ApiDuplicadoCalculoRequest;
export type AdjudicacionDirectaCalculoRequest = ApiAdjudicacionDirectaCalculoRequest;
export type {
  DuplicadoResumenResponse,
  EjecucionAnaliticaEstadoResponse,
  PesoAnomaliaResponse,
  ProveedorDirectaResumenResponse,
  RiesgoGlobalResumenResponse,
  RunResumenResponse,
};

export const analiticaService = {
  getUltimasEjecuciones: async (): Promise<EjecucionAnaliticaEstadoResponse[]> => {
    return (await api.get('/api/analitica/ejecuciones/ultimas')).data;
  },

  calcularOutliers: async (payload: OutlierCalculoRequest): Promise<RunResumenResponse> => {
    const job = await jobsService.enqueue('/api/analitica/outliers/calcular', payload);
    return jobsService.waitForResult<RunResumenResponse>(job.id, 45 * 60 * 1000);
  },

  calcularDuplicados: async (payload: DuplicadoCalculoRequest): Promise<DuplicadoResumenResponse> => {
    const job = await jobsService.enqueue('/api/analitica/duplicados/calcular', payload);
    return jobsService.waitForResult<DuplicadoResumenResponse>(job.id, 45 * 60 * 1000);
  },

  calcularDirectas: async (payload: AdjudicacionDirectaCalculoRequest): Promise<ProveedorDirectaResumenResponse> => {
    const job = await jobsService.enqueue('/api/analitica/directas/calcular', payload);
    return jobsService.waitForResult<ProveedorDirectaResumenResponse>(job.id, 45 * 60 * 1000);
  },

  calcularRiesgo: async (): Promise<RiesgoGlobalResumenResponse> => {
    const job = await jobsService.enqueue('/api/analitica/riesgo/calcular', {});
    return jobsService.waitForResult<RiesgoGlobalResumenResponse>(job.id, 45 * 60 * 1000);
  },

  getPesos: async (): Promise<PesoAnomaliaResponse[]> => {
    return (await api.get('/api/analitica/pesos')).data;
  },

  actualizarPeso: async (tipo_anomalia: string, peso: number): Promise<PesoAnomaliaResponse> => {
    return (await api.put(`/api/analitica/pesos/${tipo_anomalia}`, { peso })).data;
  },
};
