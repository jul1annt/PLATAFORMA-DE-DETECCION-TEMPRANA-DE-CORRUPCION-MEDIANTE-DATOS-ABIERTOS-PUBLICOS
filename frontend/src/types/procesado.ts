export interface Procesado {
  id: number;
  proveedor_normalizado?: string;
  entidad_normalizada?: string;
  modalidad_contratacion?: string;
  fecha_publicacion_normalizada?: string;
  valor_total_normalizado?: number;
  precio_base_normalizado?: number;
  urlproceso?: string;
  
  // Compatibilidad con nombres cortos solicitados (si se mapean o para evitar errores)
  proveedor?: string;
  entidad?: string;
  modalidad?: string;
  fecha?: string;
  monto?: number;

  // Alertas
  es_incompleto?: boolean;
  clasificacion_riesgo?: string;
  datos_modificados?: boolean;
  es_sospechoso?: boolean;
  nivel_confianza?: number;
  
  [key: string]: any;
}

export interface MetricasCalidad {
  total_contratos: number;
  completos: number;
  incompletos: number;
  sospechosos: number;
  porcentaje_completos: number;
  porcentaje_incompletos: number;
  porcentaje_sospechosos: number;
  promedio_confianza: number;
}

export interface CampoFaltante {
  campo: string;
  cantidad: number;
  porcentaje: number;
}

export interface CampoFaltanteDTO {
  campo: string;
  cantidad: number;
  porcentaje: number;
}

export interface ProcesamientoLogDTO {
  id: number;
  fecha_hora_inicio: string;
  fecha_hora_fin: string | null;
  estado: string;
  forzar_reproceso: boolean;
  duracion_segundos: number | null;
  total_evaluados: number;
  procesados: number;
  omitidos: number;
  anomalias_registradas: number;
  mensaje_error: string | null;
  created_at: string;
}

export interface PaginatedProcesamientoLogsDTO {
  items: ProcesamientoLogDTO[];
  total: number;
  page: number;
  size: number;
}

export interface ReprocesarResultadoDTO {
  total_evaluados: number;
  procesados: number;
  omitidos: number;
  anomalias_registradas: number;
  fecha_hora_inicio: string;
  fecha_hora_fin: string;
  duracion_segundos: number;
  estado: string;
}

export type QualityFilterType = 'ALL' | 'INCOMPLETOS' | 'SOSPECHOSOS' | 'MODIFICADOS' | 'ALTO_RIESGO';

export interface QualitySummaryProps {
  metricas: MetricasCalidad | null;
  camposFaltantes: CampoFaltante[];
  hayCambiosRecientes: boolean;
  onFilterChange: (filter: QualityFilterType) => void;
  activeFilter: QualityFilterType;
}


export interface AnomaliaContrato {
  id: number;
  raw_secop_id: number;
  id_contrato_procesado?: number;
  campo_afectado?: string;
  motivo: string;
  descripcion?: string;
  valor_original?: string;
  nivel_confianza: number;
  clasificacion_riesgo?: string;
  created_at?: string;
}

// ── Dashboard types ────────────────────────────────────────────────────────────

export interface DashboardMetrics {
  total_contratos: number;
  pct_incompletos: number;
  pct_sospechosos: number;
  pct_alto_riesgo: number;
  total_incompletos: number;
  total_sospechosos: number;
  total_alto_riesgo: number;
  promedio_confianza: number;
}

export interface RiskDistribution {
  name: string;
  value: number;
  color: string;
}

export interface TopProvider {
  name: string;
  contracts: number;
}

export interface AnomalyDistribution {
  name: string;
  value: number;
  color: string;
}
