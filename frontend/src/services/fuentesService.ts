import api from '../api/axios';
import type {
  FuenteDatosCreateDTO,
  FuenteDatosResponseDTO,
  FuenteDatosUpdateDTO,
  ConexionTestResponseDTO,
  SincronizacionHistorialResponseDTO,
} from '../types/fuente';
import type {
  ComparativaFuenteDto,
  SincronizacionHistorialPaginaDto,
  SincronizacionHistorialResumenDto,
} from '../types/api.generated';
import { jobsService } from './jobsService';

export interface SincronizacionResultadoDTO {
  historial_id: number;
  registros_traidos: number;
  registros_insertados: number;
  registros_duplicados: number;
  fuente: string;
  desde: string;
  hasta: string;
  parcial: boolean;
  cursor: string | null;
}

export type ComparativaFuenteDTO = ComparativaFuenteDto;
export type SincronizacionHistorialResumenDTO = SincronizacionHistorialResumenDto;
export type SincronizacionHistorialPaginaDTO = SincronizacionHistorialPaginaDto;

export const fuentesService = {
  getAll: async (): Promise<FuenteDatosResponseDTO[]> => {
    const response = await api.get('/api/ingesta/fuentes/');
    return response.data;
  },

  getById: async (id: number): Promise<FuenteDatosResponseDTO> => {
    const response = await api.get(`/api/ingesta/fuentes/${id}`);
    return response.data;
  },

  create: async (data: FuenteDatosCreateDTO): Promise<FuenteDatosResponseDTO> => {
    const response = await api.post('/api/ingesta/fuentes/', data);
    return response.data;
  },

  update: async (id: number, data: FuenteDatosUpdateDTO): Promise<FuenteDatosResponseDTO> => {
    const response = await api.put(`/api/ingesta/fuentes/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/api/ingesta/fuentes/${id}`);
  },

  testConnection: async (id: number): Promise<ConexionTestResponseDTO> => {
    const response = await api.post(`/api/ingesta/fuentes/${id}/probar`);
    return response.data;
  },

  sync: async (id: number): Promise<SincronizacionResultadoDTO> => {
    const accepted = await jobsService.enqueue(`/api/ingesta/fuentes/${id}/sincronizar`, {});
    return jobsService.waitForResult<SincronizacionResultadoDTO>(accepted.id);
  },

  getSincronizacionesGlobales: async (): Promise<SincronizacionHistorialResponseDTO[]> => {
    const response = await api.get('/api/ingesta/fuentes/sincronizaciones');
    return response.data;
  },

  getPaginaSincronizaciones: async (page: number, size: number, signal?: AbortSignal): Promise<SincronizacionHistorialPaginaDTO> => {
    const response = await api.get('/api/ingesta/fuentes/sincronizaciones/pagina', {
      params: { page, size },
      signal,
    });
    return response.data;
  },

  getResumenSincronizaciones: async (signal?: AbortSignal): Promise<SincronizacionHistorialResumenDTO> => {
    const response = await api.get('/api/ingesta/fuentes/sincronizaciones/resumen', { signal });
    return response.data;
  },

  getComparativa: async (signal?: AbortSignal): Promise<ComparativaFuenteDTO[]> => {
    const response = await api.get('/api/ingesta/fuentes/comparativa', { signal });
    return response.data;
  },

  getHistorialByFuenteId: async (id: number): Promise<SincronizacionHistorialResponseDTO[]> => {
    const response = await api.get(`/api/ingesta/fuentes/${id}/sincronizaciones`);
    return response.data;
  },

  getPaginaHistorialByFuenteId: async (
    id: number,
    page: number,
    size: number,
  ): Promise<SincronizacionHistorialPaginaDTO> => {
    const response = await api.get(`/api/ingesta/fuentes/${id}/sincronizaciones/pagina`, {
      params: { page, size },
    });
    return response.data;
  },
};
