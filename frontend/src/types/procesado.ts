export interface Procesado {
  id: number;
  proveedor_normalizado?: string;
  entidad_normalizada?: string;
  modalidad_contratacion?: string;
  fecha_publicacion_normalizada?: string;
  valor_total_normalizado?: number;
  
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

export type QualityFilterType = 'ALL' | 'INCOMPLETOS' | 'SOSPECHOSOS' | 'MODIFICADOS';

export interface QualitySummaryProps {
  metricas: MetricasCalidad | null;
  camposFaltantes: CampoFaltante[];
  hayCambiosRecientes: boolean;
  onFilterChange: (filter: QualityFilterType) => void;
  activeFilter: QualityFilterType;
}
