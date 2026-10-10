import type {
  AnomaliaResponseDto,
  CampoFaltanteDto as ApiCampoFaltanteDto,
  ContratoProcesadoResponseDto,
  DashboardMetricasDto,
  DistribucionDto,
  MetricasCalidadDto,
  PaginatedProcesamientoLogsDto,
  ProcesamientoLogDto as ApiProcesamientoLogDto,
  TopProveedorDto,
} from './api.generated';

// Public data contracts come from the backend's generated OpenAPI schema.
export type Procesado = ContratoProcesadoResponseDto;
export type MetricasCalidad = MetricasCalidadDto;
export type CampoFaltante = ApiCampoFaltanteDto;
export type CampoFaltanteDTO = ApiCampoFaltanteDto;
export type ProcesamientoLogDTO = ApiProcesamientoLogDto;
export type PaginatedProcesamientoLogsDTO = PaginatedProcesamientoLogsDto;
export type AnomaliaContrato = AnomaliaResponseDto;
export type DashboardMetrics = DashboardMetricasDto;
export type RiskDistribution = DistribucionDto;
export type TopProvider = TopProveedorDto;
export type AnomalyDistribution = DistribucionDto;

// The worker result is a job payload, not an HTTP response schema.
export interface ReprocesarResultadoDTO {
  total_evaluados: number;
  procesados: number;
  omitidos: number;
  anomalias_registradas: number;
  fecha_hora_inicio: string;
  fecha_hora_fin: string | null;
  duracion_segundos: number | null;
  estado: string;
}

export type QualityFilterType = 'ALL' | 'INCOMPLETOS' | 'SOSPECHOSOS' | 'ALTO_RIESGO';

export interface QualitySummaryProps {
  metricas: MetricasCalidad | null;
  camposFaltantes: CampoFaltante[];
  onFilterChange: (filter: QualityFilterType) => void;
  activeFilter: QualityFilterType;
}
