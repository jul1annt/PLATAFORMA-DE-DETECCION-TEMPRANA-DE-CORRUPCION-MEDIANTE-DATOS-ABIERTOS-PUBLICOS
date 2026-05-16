import type { Procesado } from '../types/procesado';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const getProcesados = async (): Promise<Procesado[]> => {
  const response = await fetch(`${API_URL}/api/procesados/search?size=1000`);
  if (!response.ok) {
    throw new Error('Error al obtener procesados');
  }
  const data = await response.json();
  return data.items || [];

};
