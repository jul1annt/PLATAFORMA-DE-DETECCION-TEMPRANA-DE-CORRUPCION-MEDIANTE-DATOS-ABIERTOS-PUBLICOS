import type {
  ConexionTestResponseDto,
  EstadoSync as ApiEstadoSync,
  FuenteDatosCreateDto,
  FuenteDatosResponseDto as ApiFuenteDatosResponseDto,
  FuenteDatosUpdateDto,
  SincronizacionHistorialResponseDto as ApiSincronizacionHistorialResponseDto,
  TipoFormato,
} from './api.generated';

export type FormatoFuente = TipoFormato;
export type FuenteDatosCreateDTO = FuenteDatosCreateDto;
export type FuenteDatosResponseDTO = ApiFuenteDatosResponseDto;
export type FuenteDatosUpdateDTO = FuenteDatosUpdateDto;
export type ConexionTestResponseDTO = ConexionTestResponseDto;
export type EstadoSync = ApiEstadoSync;
export type SincronizacionHistorialResponseDTO = ApiSincronizacionHistorialResponseDto;
