import React from 'react';
import { AlertTooltip } from './AlertTooltip';
import type { Procesado } from '../types/procesado';

interface AlertIconsProps {
  procesado: Procesado;
}

export const AlertIcons: React.FC<AlertIconsProps> = ({ procesado }) => {
  // Lógica de detección inteligente en Frontend
  const isIncompleto = 
    procesado?.es_incompleto || 
    procesado?.proveedor_normalizado === 'NO DEFINIDO' || 
    procesado?.entidad_normalizada === 'NO DEFINIDO' ||
    !procesado?.proveedor_normalizado ||
    !procesado?.entidad_normalizada;

  const isAltoRiesgo = 
    procesado?.clasificacion_riesgo === 'ALTO' || 
    Number(procesado?.valor_total_normalizado) === 0;

  const isModificado = 
    procesado?.datos_modificados || 
    procesado?.es_sospechoso;

  return (
    <div className="flex gap-2 items-center">
      {isIncompleto && (
        <AlertTooltip content="Registro incompleto o 'NO DEFINIDO'">
          <span className="cursor-help text-lg" aria-label="Registro incompleto">⚠️</span>
        </AlertTooltip>
      )}
      {isAltoRiesgo && (
        <AlertTooltip content="Contrato de alto riesgo / Monto en cero">
          <span className="cursor-help text-lg" aria-label="Contrato de alto riesgo">🚨</span>
        </AlertTooltip>
      )}
      {isModificado && (
        <AlertTooltip content="Datos modificados / sospechosos">
          <span className="cursor-help text-lg" aria-label="Datos modificados">⚡</span>
        </AlertTooltip>
      )}
    </div>
  );
};
