import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Fuentes
export const getFuentes = () => api.get('/fuentes/');
export const createFuente = (data) => api.post('/fuentes/', data);
export const updateFuente = (id, data) => api.put(`/fuentes/${id}`, data);
export const activarFuente = (id) => api.patch(`/fuentes/${id}/activar`);
export const desactivarFuente = (id) => api.patch(`/fuentes/${id}/desactivar`);

// Sync
export const syncFuente = (id) => api.post(`/sync/${id}`);

// Logs
export const getLogs = (id) => api.get(`/logs/${id}`);

export default api;
