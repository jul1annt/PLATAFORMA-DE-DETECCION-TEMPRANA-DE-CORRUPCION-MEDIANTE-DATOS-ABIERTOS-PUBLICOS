import { formatDecimalAmount } from './format';

const VARIABLE_NAMES: Record<string, string> = {
  log_presupuesto: 'Presupuesto estimado (escala logarítmica)', log_adjudicado: 'Importe adjudicado (escala logarítmica)',
  plazo_dias: 'Plazo para presentar ofertas', duracion_dias: 'Duración estimada del proceso', procesos_previos: 'Procesos previos de la entidad',
  concentracion_previa: 'Concentración de adjudicaciones', oferentes: 'Oferentes registrados', reiteraciones_30d: 'Reiteración de compras en 30 días',
  directas_90d: 'Contratación directa en 90 días', categoria: 'Categoría de compra', modalidad: 'Modalidad', departamento: 'Departamento',
};

export function riskVariableLabel(value: string): string {
  const [name, detail] = value.split(':');
  return `${VARIABLE_NAMES[name] ?? 'Variable contextual'}${detail ? ` (${detail})` : ''}`;
}

export function riskReasonLabel(value: string): string {
  if (value.startsWith('sin_evidencia:')) return `Sin evidencia suficiente para: ${riskVariableLabel(value.slice(14))}.`;
  if (value.startsWith('dato_invalido:')) return `El registro contiene un valor inválido para: ${riskVariableLabel(value.slice(14))}. Se conservan las demás variables evaluables.`;
  if (value.startsWith('fuera_de_referencia:')) return `Valor fuera de la referencia del modelo: ${riskVariableLabel(value.slice(20))}.`;
  const reasons: Record<string, string> = {
    variables_esenciales_ausentes: 'Faltan variables esenciales para calcular el índice.',
    identidad_o_etapa_incompleta: 'No se pudo confirmar la identidad de la operación o su etapa.',
    identidad_adjudicacion_incompleta: 'Falta el identificador oficial de la adjudicación.',
    identidad_operacion_ambigua: 'Varias filas corresponden a la misma operación; se requiere aclarar su identidad.',
    fecha_etapa_ausente: 'No está disponible la fecha de la etapa; los datos corresponden al momento de captura.',
    evidencia_temporal_invalida: 'La evidencia temporal no permite evaluar esta operación.',
    sin_reconstruccion_temporal_de_etapa: 'Falta una reconstrucción documentada de los datos disponibles en esta etapa. La captura actual no permite calcular el índice histórico.',
    momento_de_prediccion_distinto_de_etapa: 'Los datos revisados no corresponden al momento de esta etapa.',
    fecha_etapa_no_verificable: 'No se pudo verificar la fecha de la etapa evaluada.',
    evidencia_de_etapa_no_verificable: 'No se pudo comprobar la evidencia conservada de esta etapa.',
    revisiones_de_etapa_en_conflicto: 'Las revisiones de esta etapa contienen datos diferentes; se requiere resolver la discrepancia.',
    resultado_numerico_no_evaluable: 'Los valores observados exceden el rango numérico evaluable por esta versión.',
  };
  return reasons[value] ?? 'Existe una limitación adicional de datos; consulta la metodología del corte.';
}

export function riskAmountLabel(value?: string | null): string {
  if (value == null || !/^\d+(\.\d+)?$/.test(value)) return 'No disponible';
  const [integer, fraction = ''] = value.split('.');
  return formatDecimalAmount(`${integer}.${fraction.padEnd(2, '0')}`);
}
