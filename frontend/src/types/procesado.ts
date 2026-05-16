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
