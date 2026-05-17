import type { PaginatedProcesamientoLogsDTO, ReprocesarResultadoDTO } from '../types/procesado';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const procesamientoService = {
  /**
   * Obtiene el historial de logs de reprocesamiento paginados
   */
  getLogs: async (page: number = 1, size: number = 20): Promise<PaginatedProcesamientoLogsDTO> => {
    const url = new URL(`${API_URL}/api/procesados/logs`);
    url.searchParams.set('page', page.toString());
    url.searchParams.set('size', size.toString());

    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error('Error al obtener historial de ejecuciones');
    }
    return response.json();
  },

  /**
   * Ejecuta el pipeline de normalización (reprocesamiento)
   */
  reprocesar: async (forzar_reproceso: boolean = true): Promise<ReprocesarResultadoDTO> => {
    const response = await fetch(`${API_URL}/api/procesados/reprocesar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ forzar_reproceso }),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw Object.assign(new Error('Error al ejecutar reprocesamiento'), { response: { data: errorData } });
    }
    return response.json();
  },
};
