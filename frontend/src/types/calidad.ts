export interface MetricasCalidadDTO {
  total_contratos: number;
  completos: number;
  incompletos: number;
  sospechosos: number;
  porcentaje_completos: number;
  porcentaje_incompletos: number;
  porcentaje_sospechosos: number;
  promedio_confianza: number;
}

export interface CampoFaltanteDTO {
  campo: string;
  cantidad: number;
  porcentaje: number;
}
