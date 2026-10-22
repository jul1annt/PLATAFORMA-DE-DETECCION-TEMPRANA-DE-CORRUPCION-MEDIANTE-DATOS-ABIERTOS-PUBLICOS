import { useEffect, useState } from 'react';
import type { RiskStatusResponse, ResultResponse } from '../types/api.generated';
import { getRiskResults, getRiskStatus } from '../services/riskService';
import { riskVariableLabel, riskReasonLabel, riskAmountLabel } from '../utils/riskEvidence';
import { secopSourceUrl } from '../utils/secopLink';
import { formatCalendarDate } from '../utils/format';

type EvidenceResult = {
  index?: number | null;
  coverage?: number;
  model_version?: string;
  prediction_at?: string;
  interpretation?: string;
  temporal_scope?: string;
  reasons?: string[];
  signals?: { variable: string; contribution: number }[];
  provenance?: { process_id?: string; source_row_id?: string; award_id?: string | null; lot_id?: string | null; source_url?: string };
  observed?: { budget?: string | null; awarded_amount?: string | null; modality?: string; direct_justification?: string | null };
  context?: { directas_90d?: { processes?: number | null; amount?: string | null } };
};

export function RiskEvidence({ rawIds = [], publicCutId }: { rawIds?: number[]; publicCutId?: string | null }) {
  const [status, setStatus] = useState<RiskStatusResponse | null>(null);
  const [items, setItems] = useState<ResultResponse[]>([]);
  const [settled, setSettled] = useState<{ key: string; error: boolean } | null>(null);
  const idsKey = rawIds.join(',');
  const requestKey = `${idsKey}|${publicCutId === undefined ? 'latest' : publicCutId ?? 'unversioned'}`;
  const loading = settled?.key !== requestKey;
  const error = settled?.key === requestKey && settled.error;

  useEffect(() => {
    const controller = new AbortController();
    const ids = idsKey ? idsKey.split(',').map(Number) : [];
    // Read a single version even if publication switches between HTTP calls.
    // A parent with unversioned source data cannot attach a newer index.
    const pending = publicCutId === null ? Promise.resolve(null) : getRiskStatus(controller.signal, publicCutId);
    pending.then(async state => {
      const page = ids.length && state?.available && state.cut_id
        ? await getRiskResults(ids, controller.signal, state.cut_id, state.public_cut_id) : { items: [] };
      if (!controller.signal.aborted) {
        setStatus(state);
        setItems(page.items);
        setSettled({ key: requestKey, error: false });
      }
    }).catch(() => {
      if (!controller.signal.aborted) setSettled({ key: requestKey, error: true });
    });
    return () => controller.abort();
  }, [idsKey,publicCutId,requestKey]);

  return <section aria-label="Señales de riesgo contractual" className="my-8 min-w-0 break-words border-y border-slate-200 py-6 text-slate-800">
    <h2 className="text-xl font-bold text-indigo-950">Señales de riesgo contractual</h2>
    <p className="mt-2 max-w-prose text-sm">La calidad del registro, una anomalía estadística y un indicio de riesgo son resultados diferentes. Las alertas orientan la revisión del expediente y no acreditan corrupción.</p>
    {!loading && !error && !status?.available && status?.public_data_cut_at ? <p className="mt-3 text-sm">Datos publicados: {formatCalendarDate(status.public_data_cut_at)}.</p> : null}
    {loading ? <p role="status" className="mt-3 text-sm">Consultando el último corte analítico…</p>
      : error ? <p role="status" className="mt-3 text-sm">No fue posible consultar el motor. Puedes seguir revisando los datos publicados y el expediente SECOP.</p>
      : !status?.available ? <p className="mt-3 text-sm">El nuevo índice está pendiente de modelos validados y de un corte completo. La ausencia de un índice no significa ausencia de riesgo.</p>
      : <>
        <p className="mt-3 text-sm">Corte validado: {status.data_cut_at ? new Date(status.data_cut_at).toLocaleString('es-CO', { timeZone: 'America/Bogota' }) : 'Sin fecha disponible'} · Actualización diaria {status.daily_enabled ? 'habilitada' : 'pausada'}.</p>
        {status.update_status === 'BLOQUEADO' ? <p className="mt-2 text-sm">La última actualización se detuvo. Se conserva el corte validado que muestra esta página.</p> : null}
        {rawIds.length > 0 && items.length === 0 ? <p className="mt-3 text-sm">Estos registros no tienen una evaluación publicada en el corte actual.</p> : null}
        <ul className="mt-4 divide-y divide-slate-200">
          {items.map(item => {
            const result = item.result as EvidenceResult;
            const sourceUrl = secopSourceUrl(result.provenance?.source_url);
            return <li key={`${item.raw_secop_id}-${item.stage}`} className="py-4">
              <h3 className="break-words font-semibold">Proceso {result.provenance?.process_id || `sin identificador disponible (registro ${item.raw_secop_id})`} · {item.stage === 'CONVOCATORIA' ? 'Convocatoria' : 'Adjudicación'}</h3>
              <p className="mt-1 text-sm">{typeof result.index === 'number' ? `Prioridad de revisión: ${result.index.toLocaleString('es-CO')} / 100` : 'Sin índice: revisa los motivos de abstención'} · Cobertura de variables: {Math.round((result.coverage ?? 0) * 100)} %.</p>
              {result.model_version ? <p className="mt-1 break-words text-xs">Versión: {result.model_version}</p> : null}
              {result.prediction_at ? <p className="mt-1 text-xs">Momento evaluado: {new Date(result.prediction_at).toLocaleString('es-CO', { timeZone: 'America/Bogota' })}.</p> : null}
              {result.temporal_scope === 'historical_stage_snapshot' ? <p className="mt-1 text-xs">Evaluación retrospectiva con datos documentados de esta etapa, conocidos hasta la fecha indicada.</p> : null}
              {result.temporal_scope === 'observed_at_capture_not_backdated' ? <p className="mt-1 text-xs">Datos observados al capturar el corte. Este resultado no reconstruye el estado histórico en la fecha original de la operación.</p> : null}
              <details className="mt-2 text-sm">
                <summary className="cursor-pointer rounded focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-indigo-700">Ver variables y límites de la evaluación</summary>
                <p className="mt-2">Las contribuciones describen la decisión del modelo; no demuestran una relación causal.</p>
                <dl className="mt-3 grid gap-1">
                  <div><dt className="inline font-medium">Fila oficial SECOP: </dt><dd className="inline break-all">{result.provenance?.source_row_id || 'No disponible'}</dd></div>
                  {item.stage === 'ADJUDICACION' ? <div><dt className="inline font-medium">Adjudicación: </dt><dd className="inline break-all">{result.provenance?.award_id || 'Identidad sin confirmar'}</dd></div> : null}
                  <div><dt className="inline font-medium">Lote: </dt><dd className="inline break-all">{result.provenance?.lot_id || 'Sin identificador de lote disponible; la evaluación corresponde a la operación indicada'}</dd></div>
                </dl>
                {result.observed ? <dl className="mt-3 grid gap-1">
                  <div><dt className="inline font-medium">Modalidad: </dt><dd className="inline">{result.observed.modality || 'No disponible'}</dd></div>
                  <div><dt className="inline font-medium">Presupuesto observado: </dt><dd className="inline">{riskAmountLabel(result.observed.budget)}</dd></div>
                  {item.stage === 'ADJUDICACION' ? <div><dt className="inline font-medium">Importe adjudicado: </dt><dd className="inline">{riskAmountLabel(result.observed.awarded_amount)}</dd></div> : null}
                  <div><dt className="inline font-medium">Justificación de modalidad: </dt><dd className="inline">{result.observed.direct_justification || 'No disponible en el registro'}</dd></div>
                </dl> : null}
                {item.stage === 'ADJUDICACION' && result.context?.directas_90d ? <p className="mt-3">Otras compras directas conocidas de esta entidad con el proveedor en 90 días: {result.context.directas_90d.processes ?? 'Sin evaluación'} procesos · Importe de sus adjudicaciones: {riskAmountLabel(result.context.directas_90d.amount)}. Se excluye el proceso actual; esto no demuestra abuso de la modalidad.</p> : null}
                <ul className="mt-2 list-disc pl-5">
                  {result.signals?.map(signal => <li key={signal.variable}>{riskVariableLabel(signal.variable)}: {signal.contribution.toLocaleString('es-CO', { maximumSignificantDigits: 5 })}</li>)}
                  {result.reasons?.map(reason => <li key={reason}>{riskReasonLabel(reason)}</li>)}
                </ul>
                {sourceUrl ? <a href={sourceUrl} target="_blank" rel="noreferrer" className="mt-3 inline-block text-indigo-800 underline underline-offset-4">Revisar expediente SECOP</a> : null}
              </details>
            </li>;
          })}
        </ul>
      </>}
    <p className="mt-4 text-sm">El índice expresa prioridad relativa, no una probabilidad de corrupción. Compara resultados de la misma etapa y versión.</p>
    <div className="mt-4 rounded-xl bg-indigo-50 p-4 text-sm leading-6">
      <h3 className="font-bold text-indigo-950">Cómo se obtienen estos resultados</h3>
      <p className="mt-1">La señal estadística compara el importe base con contratos del mismo tipo y modalidad publicados en el mismo mes. Se marca cuando queda fuera del rango intercuartílico del grupo (Q1−1,5×IQR o Q3+1,5×IQR), con al menos 30 procesos distintos e IQR mayor que cero.</p>
      <p className="mt-2">Los registros incompletos y las alertas históricas se cuentan por separado. “Riesgo histórico alto” requiere que un mismo registro tenga ambas marcas; es una prioridad para revisar el expediente, no una conclusión de corrupción.</p>
      <p className="mt-2">Estado actual del nuevo índice: no disponible; pesos: sin calibrar; modelo judicial: no entrenado. Por eso el tablero presenta conteos y señales disponibles, sin convertirlos en una probabilidad.</p>
    </div>
  </section>;
}
