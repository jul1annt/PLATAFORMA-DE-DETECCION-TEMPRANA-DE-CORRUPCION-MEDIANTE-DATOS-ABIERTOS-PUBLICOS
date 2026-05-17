const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface OutlierCalculoRequest {
  campo: 'valor_total_normalizado' | 'precio_base_normalizado' | 'nivel_confianza' | 'cantidad_campos_faltantes';
  fecha_campo?: 'fecha_publicacion_normalizada' | 'fecha_adjudicacion_normalizada' | null;
  fecha_desde?: string | null;
  fecha_hasta?: string | null;
  modalidad?: string | null;
}

export interface DuplicadoCalculoRequest {
  fecha_desde?: string | null;
  fecha_hasta?: string | null;
}

export interface AdjudicacionDirectaCalculoRequest {
  fecha_desde?: string | null;
  fecha_hasta?: string | null;
  minimo_directas: number;
  dias_ventana: number;
}

export interface RunResumenResponse {
  run_id: string;
  campo_analizado: string;
  total_contratos_analizados: number;
  total_outliers: number;
  porcentaje_outliers: number;
  total_outliers_alto: number;
  total_outliers_bajo: number;
  grupos_procesados: number;
  fecha_calculo: string;
}

export interface DuplicadoResumenResponse {
  run_id: string;
  total_duplicados: number;
  promedio_dias_diferencia: number;
  promedio_score: number;
  fecha_calculo: string;
}

export interface ProveedorDirectaResumenResponse {
  run_id: string;
  total_proveedores_detectados: number;
  promedio_porcentaje_directos: number;
  promedio_score: number;
  fecha_calculo: string;
}

export interface RiesgoGlobalResumenResponse {
  run_id: string;
  total_proveedores_evaluados: number;
  promedio_score_final: number;
  fecha_calculo: string;
}

export interface PesoAnomaliaResponse {
  tipo_anomalia: string;
  peso: number;
  updated_at?: string | null;
}

export const analiticaService = {
  calcularOutliers: async (payload: OutlierCalculoRequest): Promise<RunResumenResponse> => {
    const response = await fetch(`${API_URL}/api/analitica/outliers/calcular`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw Object.assign(new Error('Error al calcular outliers'), { response: { data: errorData } });
    }
    return response.json();
  },

  calcularDuplicados: async (payload: DuplicadoCalculoRequest): Promise<DuplicadoResumenResponse> => {
    const response = await fetch(`${API_URL}/api/analitica/duplicados/calcular`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw Object.assign(new Error('Error al calcular duplicados'), { response: { data: errorData } });
    }
    return response.json();
  },

  calcularDirectas: async (payload: AdjudicacionDirectaCalculoRequest): Promise<ProveedorDirectaResumenResponse> => {
    const response = await fetch(`${API_URL}/api/analitica/directas/calcular`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw Object.assign(new Error('Error al calcular adjudicaciones directas'), { response: { data: errorData } });
    }
    return response.json();
  },

  calcularRiesgo: async (): Promise<RiesgoGlobalResumenResponse> => {
    const response = await fetch(`${API_URL}/api/analitica/riesgo/calcular`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw Object.assign(new Error('Error al calcular riesgo global'), { response: { data: errorData } });
    }
    return response.json();
  },

  getPesos: async (): Promise<PesoAnomaliaResponse[]> => {
    const response = await fetch(`${API_URL}/api/analitica/pesos`);
    if (!response.ok) {
      throw new Error('Error al obtener pesos de anomalías');
    }
    return response.json();
  },

  actualizarPeso: async (tipo_anomalia: string, peso: number): Promise<PesoAnomaliaResponse> => {
    const response = await fetch(`${API_URL}/api/analitica/pesos/${tipo_anomalia}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ peso }),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw Object.assign(new Error(`Error al actualizar peso para ${tipo_anomalia}`), { response: { data: errorData } });
    }
    return response.json();
  },
};
