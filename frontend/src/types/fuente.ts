export type FormatoFuente = "JSON" | "CSV" | "XML";

export interface FuenteDatosCreateDTO {
  nombre: string;
  tipo: string;
  formato: FormatoFuente;
  endpoint: string;
  api_key?: string | null;
  frecuencia_dias: number;
}

export interface FuenteDatosResponseDTO {
  id: number;
  nombre: string;
  tipo: string;
  formato: FormatoFuente;
  endpoint: string;
  frecuencia_dias: number;
  activo: boolean;
  ultima_sync: string | null;
  created_at: string;
}

export interface FuenteDatosUpdateDTO {
  nombre?: string;
  formato?: FormatoFuente;
  endpoint?: string;
  api_key?: string | null;
  frecuencia_dias?: number;
  activo?: boolean;
}

export interface ConexionTestResponseDTO {
  exitoso: boolean;
  mensaje: string;
  registros_muestra: number[] | null;
}

export type EstadoSync = "EN_PROCESO" | "EXITOSO" | "ERROR";

export interface SincronizacionHistorialResponseDTO {
  id: number;
  fuente_id: number;
  fuente_nombre: string | null;
  fecha_inicio: string;
  fecha_fin: string | null;
  registros_traidos: number;
  registros_insertados: number;
  registros_duplicados: number;
  estado: EstadoSync;
  mensaje_error: string | null;
}
