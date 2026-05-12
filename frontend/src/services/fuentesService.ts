import api from '../api/axios';
import type {
  FuenteDatosCreateDTO,
  FuenteDatosResponseDTO,
  FuenteDatosUpdateDTO,
  ConexionTestResponseDTO,
} from '../types/fuente';

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

  sync: async (id: number): Promise<any> => {
    const response = await api.post(`/api/ingesta/fuentes/${id}/sincronizar`);
    return response.data;
  },
};
