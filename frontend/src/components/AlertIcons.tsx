import React from 'react';
import { AlertTooltip } from './AlertTooltip';
import type { Procesado } from '../types/procesado';

interface AlertIconsProps {
  procesado: Procesado;
}

export const AlertIcons: React.FC<AlertIconsProps> = ({ procesado }) => {
  return (
    <div className="flex gap-2 items-center">
      {procesado?.es_incompleto === true && (
        <AlertTooltip content="Registro incompleto">
          <span className="cursor-help text-lg" aria-label="Registro incompleto">⚠️</span>
        </AlertTooltip>
      )}
      {procesado?.clasificacion_riesgo === 'ALTO' && (
        <AlertTooltip content="Contrato de alto riesgo">
          <span className="cursor-help text-lg" aria-label="Contrato de alto riesgo">🚨</span>
        </AlertTooltip>
      )}
      {procesado?.datos_modificados === true && (
        <AlertTooltip content="Datos modificados">
          <span className="cursor-help text-lg" aria-label="Datos modificados">⚡</span>
        </AlertTooltip>
      )}
    </div>
  );
};
