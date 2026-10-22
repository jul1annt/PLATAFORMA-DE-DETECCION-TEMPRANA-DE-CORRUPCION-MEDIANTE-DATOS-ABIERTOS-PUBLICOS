import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ExternalLink, Search, ShieldAlert, X } from 'lucide-react';
import { PublicNavbar } from '../components/layout/PublicNavbar';
import { getIndiciosPage, getIndiciosState, type IndicioMvp, type IndiciosMvpState } from '../services/indiciosMvpService';
import { formatDecimalAmount } from '../utils/format';
import { secopSourceUrl } from '../utils/secopLink';

const PAGE_SIZE = 25;
const money = (value: string | null) => value ? formatDecimalAmount(value.replace(/(\.\d*?[1-9])0+$/, '$1').replace(/\.0+$/, '')) : 'Sin dato';
const displayName = (value: string | null, empty = 'No informado') => !value || /^(NO DEFINIDO|NO INFORMADO|SIN INFORMACIÓN)$/i.test(value.trim()) ? empty : value;

const familyNames: Record<string, string> = {
  IMPORTE_ATIPICO: 'Importe atípico',
  COMPETENCIA: 'Competencia',
  CONCENTRACION_REITERACION: 'Concentración y reiteración',
};
const indicatorNames: Record<string, string> = {
  IMPORTE_ATIPICO: 'Importe frente a operaciones pares',
  OFERENTE_UNICO: 'Oferente único',
  DIRECTAS_90D: 'Contratación directa en 90 días',
  REITERACION_30D: 'Reiteración en 30 días',
};
const familyIndicators: Record<string, string[]> = {
  IMPORTE_ATIPICO: ['IMPORTE_ATIPICO'],
  COMPETENCIA: ['OFERENTE_UNICO'],
  CONCENTRACION_REITERACION: ['DIRECTAS_90D', 'REITERACION_30D'],
};
const stateNames: Record<string, string> = {
  DETECTADA: 'Señal confirmada',
  SIN_SENAL: 'Evaluada sin señal observada',
  NO_EVALUABLE: 'Evidencia insuficiente',
  NO_APLICA: 'No aplica a esta etapa',
};

export function PublicIndiciosMvp() {
  const [query, setQuery] = useSearchParams();
  const [state, setState] = useState<IndiciosMvpState | null>(null);
  const [rows, setRows] = useState<IndicioMvp[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<IndicioMvp | null>(null);
  const page = Math.max(1, Number(query.get('page') || 1));
  const type = query.get('tipo') || '';
  const modality = query.get('modalidad') || '';
  const status = query.get('estado') || '';
  const signal = query.get('senal') || '';
  const stage = query.get('etapa') || '';
  const term = query.get('q') || '';

  const apiQuery = useMemo(() => {
    const params = new URLSearchParams({ page: String(page), size: String(PAGE_SIZE) });
    if (type) params.set('contract_type', type);
    if (modality) params.set('modality', modality);
    if (status) params.set('status', status);
    if (signal) params.set('signal', signal);
    if (stage) params.set('stage', stage);
    if (term.length >= 3) params.set('q', term);
    return params;
  }, [page, type, modality, status, signal, stage, term]);

  useEffect(() => {
    const controller = new AbortController();
    getIndiciosState(controller.signal).then(setState).catch((e: Error) => setError(e.message));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getIndiciosPage(apiQuery, controller.signal)
      .then((result) => { setRows(result.items); setTotal(result.total); setHasMore(result.has_more); setError(null); })
      .catch((e: Error) => { if (e.name !== 'AbortError') { setRows([]); setTotal(null); setHasMore(false); setError(e.message); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [apiQuery]);

  useEffect(() => {
    if (!selected) return;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === 'Escape') setSelected(null); };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [selected]);

  const change = (key: string, value: string) => {
    const next = new URLSearchParams(query);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== 'page') next.delete('page');
    setQuery(next);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <PublicNavbar />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="flex flex-col gap-5 border-b border-slate-200 pb-7 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-[.18em] text-indigo-700">Motor analítico · corte local</p>
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Señales de riesgo en contratos</h1>
            <p className="mt-3 max-w-3xl text-base leading-7 text-slate-600">Consulta anomalías estadísticas con su evidencia y cobertura. Cada señal orienta una revisión humana; no prueba corrupción, sobreprecio ni responsabilidad.</p>
          </div>
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-indigo-200 bg-white px-3 py-2 text-sm font-semibold text-indigo-900"><ShieldAlert size={17} aria-hidden="true" /> Reglas explicables · sin modelo entrenado</span>
        </header>

        {state && <>
          <section className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Resumen de cobertura">
            <Metric title="Contratos procesados" value={state.cohort.rows.toLocaleString('es-CO')} detail={`${state.cohort.start || 'Sin fecha'} a ${state.cohort.end || 'Sin fecha'} · corte ${state.snapshot_cut}`} />
            <Metric title="Con señal confirmada" value={state.coverage.signal.toLocaleString('es-CO')} detail="Anomalía estadística en importe base" />
            <Metric title="Sin señal confirmada" value={state.coverage.no_confirmed_signal.toLocaleString('es-CO')} detail="No descarta riesgos no evaluados" />
            <Metric title="Con evidencia incompleta" value={state.coverage.partial_or_unknown.toLocaleString('es-CO')} detail="Competencia e historia pueden faltar" />
          </section>

          <section className="mt-8 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5" aria-label="Filtros de contratos">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
              <Filter label="Tipo de contrato" value={type} onChange={(value) => change('tipo', value)} options={state.filters.contract_types} all="Todos" />
              <Filter label="Modalidad" value={modality} onChange={(value) => change('modalidad', value)} options={state.filters.modalities} all="Todas" />
              <label className="text-sm font-medium text-slate-700">Resultado <select value={status} onChange={(e) => change('estado', e.target.value)} className="mt-1 block w-full rounded-lg border-slate-300 bg-white p-2.5 text-sm focus:border-indigo-600 focus:ring-indigo-600"><option value="">Todos</option><option value="CON_SENAL_CONFIRMADA">Con señal confirmada</option><option value="EVIDENCIA_INSUFICIENTE">Evidencia insuficiente</option><option value="SIN_SENAL_OBSERVADA">Sin señal observada</option><option value="NO_EVALUABLE">No evaluable</option></select></label>
              <label className="text-sm font-medium text-slate-700">Señal <select value={signal} onChange={(e) => change('senal', e.target.value)} className="mt-1 block w-full rounded-lg border-slate-300 bg-white p-2.5 text-sm focus:border-indigo-600 focus:ring-indigo-600"><option value="">Todas</option><option value="true">Con señal</option><option value="false">Sin señal confirmada</option></select></label>
              <label className="text-sm font-medium text-slate-700">Etapa <select value={stage} onChange={(e) => change('etapa', e.target.value)} className="mt-1 block w-full rounded-lg border-slate-300 bg-white p-2.5 text-sm focus:border-indigo-600 focus:ring-indigo-600"><option value="">Todas</option>{state.filters.stages.map((v) => <option key={v} value={v}>{v === 'ADJUDICACION' ? 'Adjudicación' : 'Convocatoria'}</option>)}</select></label>
              <label className="text-sm font-medium text-slate-700">Entidad, proveedor o proceso <span className="relative mt-1 block"><Search size={16} className="absolute left-3 top-3 text-slate-400" aria-hidden="true" /><input value={term} onChange={(e) => change('q', e.target.value)} placeholder="Buscar texto (mín. 3 caracteres)" className="w-full rounded-lg border-slate-300 py-2.5 pl-9 pr-3 text-sm focus:border-indigo-600 focus:ring-indigo-600" /></span></label>
            </div>
          </section>

          {error && <p role="alert" className="mt-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">{error}</p>}
          <div className="mt-5 flex items-center justify-between text-sm text-slate-600" aria-live="polite"><span>{total !== null ? `${total.toLocaleString('es-CO')} contratos en esta selección` : `Mostrando ${rows.length} contratos en esta página`}</span><span>Página {page}</span></div>
          <div className="mt-3 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <ul className="divide-y divide-slate-200">
              {rows.map((row) => <ContractCard key={row.raw_secop_id} row={row} onOpen={() => setSelected(row)} />)}
              {loading && <li className="p-8 text-center text-slate-600">Cargando contratos…</li>}
              {!loading && !error && !rows.length && <li className="p-8 text-center text-slate-600">No hay contratos para esos filtros.</li>}
            </ul>
          </div>
          <div className="mt-5 flex justify-end gap-2">
            <button disabled={loading || page <= 1} onClick={() => change('page', String(page - 1))} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-40">Anterior</button>
            <button disabled={loading || !hasMore} onClick={() => change('page', String(page + 1))} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-40">Siguiente</button>
          </div>

          <details className="mt-10 rounded-xl border border-slate-200 bg-white p-5">
            <summary className="cursor-pointer text-base font-semibold">Metodología, cobertura y límites</summary>
            <ul className="mt-4 list-disc space-y-2 pl-5 text-sm leading-6 text-slate-700">
              <li>Cohorte completa del {state.cohort.start} al {state.cohort.end}; fecha del corte publicado: {state.snapshot_cut}. Incluye {state.cohort.rows.toLocaleString('es-CO')} operaciones, agrupadas por mes, tipo de contrato y modalidad.</li>
              <li>Importe atípico: valor base fuera de Q1 − 1,5×IQR o Q3 + 1,5×IQR; requiere 30 importes positivos de procesos únicos e IQR mayor que cero. La referencia es mensual.</li>
              <li>El valor es un importe total reportado, no un precio unitario; la moneda y la escala no se verificaron con los documentos de cada proceso.</li>
              <li>La categoría oficial SECOP no está disponible en esta lectura; el tipo de contrato se usa como proxy y se identifica como tal.</li>
              <li>Oferente único no se evalúa sin ofertas verificadas. Reiteración y contratación directa tampoco se evalúan sin una historia completa y una identidad comprobable.</li>
              <li>Los pesos por familia son una referencia descriptiva no calibrada. La prioridad conserva límites por datos desconocidos; no se presenta un orden total ni una probabilidad.</li>
              <li>El total exacto se presenta sin filtros; las selecciones filtradas usan paginación por continuación. El corte no expone un token transaccional común, por lo que no certifica una generación transaccional entre páginas.</li>
              <li>No hay modelo entrenado con decisiones judiciales firmes vinculadas a estas operaciones. Ningún resultado es una etiqueta de corrupción.</li>
              <li>La bandera histórica de calidad de datos se mantiene separada y no participa en las señales.</li>
            </ul>
          </details>
          {selected && <DetailDialog row={selected} cut={state.snapshot_cut} onClose={() => setSelected(null)} />}
        </>}
        {!state && !error && <p role="status" className="mt-8 text-slate-600">Cargando el corte local de evaluación…</p>}
      </main>
    </div>
  );
}

function Filter({ label, value, onChange, options, all }: { label: string; value: string; onChange: (value: string) => void; options: string[]; all: string }) {
  return <label className="text-sm font-medium text-slate-700">{label}<select value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 block w-full rounded-lg border-slate-300 bg-white p-2.5 text-sm focus:border-indigo-600 focus:ring-indigo-600"><option value="">{all}</option>{options.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>;
}

function Metric({ title, value, detail }: { title: string; value: string; detail: string }) {
  return <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p><p className="mt-2 text-3xl font-bold tabular-nums text-slate-950">{value}</p><p className="mt-1 text-sm text-slate-600">{detail}</p></div>;
}

function Detail({ label, value }: { label: string; value: string }) {
  return <div className="min-w-0"><dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</dt><dd className="mt-1 break-words text-sm font-medium text-slate-900">{value}</dd></div>;
}

function statusText(status: unknown) {
  const value = typeof status === 'string'
    ? status
    : status && typeof status === 'object' && 'status' in status && typeof status.status === 'string'
      ? status.status
      : null;
  if (!value) return 'Estado no disponible';
  return stateNames[value] || value.replaceAll('_', ' ').toLowerCase();
}
function familyText(name: string) { return familyNames[name] || name; }
function indicatorText(name: string) { return indicatorNames[name] || name.replaceAll('_', ' ').toLowerCase(); }
function reasonText(reason: unknown) {
  return typeof reason === 'string' ? reason.replaceAll('_', ' ') : '';
}

function DetailDialog({ row, cut, onClose }: { row: IndicioMvp; cut: string; onClose: () => void }) {
  const source = secopSourceUrl(row.source_url);
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section role="dialog" aria-modal="true" aria-labelledby="indicio-detail-title" className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl sm:p-8">
      <div className="flex items-start justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-wider text-indigo-700">Evidencia · corte {cut}</p><h2 id="indicio-detail-title" className="mt-1 text-2xl font-bold text-slate-950">{displayName(row.entity, 'Entidad sin nombre disponible')}</h2></div><button aria-label="Cerrar detalle" onClick={onClose} className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-600"><X size={20} aria-hidden="true" /></button></div>
      <dl className="mt-6 grid gap-4 sm:grid-cols-2">
        <Detail label="Proceso SECOP" value={displayName(row.process_id, 'No disponible')} />
        <Detail label="Proveedor" value={displayName(row.supplier)} />
        <Detail label="Fecha de publicación" value={row.published_at || 'No disponible'} />
        <Detail label="Etapa del corte" value={row.stage === 'ADJUDICACION' ? 'Adjudicación observada' : 'Convocatoria'} />
        <Detail label="Modalidad" value={row.modality || 'No disponible'} />
        <Detail label="Tipo de contrato (proxy)" value={row.contract_type || 'No disponible'} />
        <Detail label="Presupuesto base" value={money(row.amount)} />
        <Detail label="Importe adjudicado" value={row.award_amount && Number(row.award_amount) > 0 ? money(row.award_amount) : 'No disponible'} />
        <Detail label="Cobertura de familias" value={`${row.coverage.evaluated_families} de ${row.coverage.applicable_families} evaluables`} />
        <Detail label="Orden de revisión" value="Señales estadísticas primero; después fecha. Sin ranking calibrado." />
      </dl>
      <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-4">
        <h3 className="font-semibold text-slate-900">Familias analizadas</h3>
        <ul className="mt-3 space-y-3 text-sm leading-6">
          {Object.entries(row.coverage.families).map(([name, status]) => <li key={name} className="border-t border-slate-200 pt-3"><strong>{familyText(name)}:</strong> {statusText(status)}.
            {(familyIndicators[name] || []).map((indicatorName) => {
              const indicator = row.coverage.indicators[indicatorName];
              if (!indicator) return null;
              const observed = indicatorName === 'IMPORTE_ATIPICO' ? row.evidence : null;
              const range = observed && ('lower' in observed || 'upper' in observed) ? ` Referencia: ${money(String(observed.lower ?? ''))}–${money(String(observed.upper ?? ''))} en ${String(observed.n ?? '—')} procesos.` : '';
              const reason = reasonText(indicator.reason);
              return <p key={indicatorName} className="mt-1 text-slate-700">{indicatorText(indicatorName)}{range}{reason ? ` Motivo: ${reason}.` : ''}</p>;
            })}
          </li>)}
        </ul>
      </div>
      <p className="mt-4 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm leading-6 text-amber-950">Una señal indica una anomalía que merece revisión. No es una acusación y no demuestra corrupción o sobreprecio.</p>
      {row.legacy_data_quality_flag && <p className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-950">Bandera histórica de calidad de datos, separada de las señales de riesgo.</p>}
      {source && <a href={source} target="_blank" rel="noopener noreferrer" className="mt-6 inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-800"><ExternalLink size={16} aria-hidden="true" /> Abrir registro original en SECOP</a>}
    </section>
  </div>;
}

function ContractCard({ row, onOpen }: { row: IndicioMvp; onOpen: () => void }) {
  const source = secopSourceUrl(row.source_url);
  const badge = row.signal ? 'Señal de riesgo' : row.status === 'EVIDENCIA_INSUFICIENTE' ? 'Evidencia incompleta' : row.status === 'NO_EVALUABLE' ? 'No evaluable' : 'Sin señal observada';
  const badgeClass = row.signal ? 'bg-rose-100 text-rose-800' : row.status === 'EVIDENCIA_INSUFICIENTE' || row.status === 'NO_EVALUABLE' ? 'bg-amber-100 text-amber-900' : 'bg-emerald-100 text-emerald-800';
  return <li className="p-4 sm:p-5">
    <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${badgeClass}`}>{badge}</span>
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">{row.stage === 'ADJUDICACION' ? 'Adjudicación observada' : 'Convocatoria'}</span>
          <span className="text-xs font-medium text-slate-600">Cobertura: {row.coverage.evaluated_families}/{row.coverage.applicable_families} familias</span>
          {row.legacy_data_quality_flag && <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-900">Calidad de datos, señal separada</span>}
        </div>
        <h2 className="mt-2 truncate text-lg font-semibold text-slate-950">{displayName(row.entity, 'Entidad sin nombre disponible')}</h2>
        <p className="mt-1 text-sm text-slate-700">Proveedor: {displayName(row.supplier)} · Proceso: <span className="font-mono">{displayName(row.process_id, 'No disponible')}</span></p>
        <p className="mt-1 text-sm text-slate-600">{row.contract_type || 'Tipo no disponible'} · {row.modality || 'Modalidad no disponible'} · Publicado {row.published_at || 'sin fecha'}</p>
        <p className="mt-2 text-sm text-slate-800">Presupuesto base: <strong>{money(row.amount)}</strong>{row.award_amount && Number(row.award_amount) > 0 && <> · Valor adjudicado disponible: {money(row.award_amount)}</>}</p>
        {row.signal && <p className="mt-2 text-sm leading-6 text-rose-900">Presupuesto fuera del rango mensual de pares: {money(String(row.evidence.lower ?? ''))}–{money(String(row.evidence.upper ?? ''))} ({String(row.evidence.n ?? '—')} procesos únicos). Es una anomalía que requiere revisión.</p>}
        {!row.signal && row.missing_evidence.length > 0 && <p className="mt-2 text-sm text-slate-600">Pendiente de evidencia: {row.missing_evidence.join(', ').replaceAll('_', ' ')}.</p>}
        <p className="mt-2 text-xs text-slate-500">Ordenada por señal estadística y fecha. No hay ranking calibrado ni clasificación de corrupción.</p>
      </div>
      <div className="flex shrink-0 flex-wrap gap-2">
        <button onClick={onOpen} className="rounded-lg bg-indigo-700 px-3.5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-800 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:ring-offset-2">Ver evidencia</button>
        {source && <a href={source} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm font-semibold text-slate-800 hover:bg-slate-50"><ExternalLink size={15} aria-hidden="true" /> SECOP</a>}
      </div>
    </div>
  </li>;
}
