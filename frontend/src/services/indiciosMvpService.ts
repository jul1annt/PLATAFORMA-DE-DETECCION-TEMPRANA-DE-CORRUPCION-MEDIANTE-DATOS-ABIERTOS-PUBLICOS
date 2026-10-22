export interface IndicioMvp {
  id: number;
  raw_secop_id: number;
  process_id: string | null;
  entity: string | null;
  supplier: string | null;
  published_at: string | null;
  contract_type: string | null;
  modality: string | null;
  amount: string | null;
  award_amount: string | null;
  source_url: string | null;
  signal: boolean;
  stage: 'CONVOCATORIA' | 'ADJUDICACION';
  comparison_period: string | null;
  status: 'CON_SENAL_CONFIRMADA' | 'EVIDENCIA_INSUFICIENTE' | 'NO_EVALUABLE' | 'SIN_SENAL_OBSERVADA';
  coverage: {
    evaluated_families: number;
    applicable_families: number;
    unevaluable_families: number;
    complete_score: number | null;
    score_interval: { min: number; max: number };
    families: Record<string, unknown>;
    indicators: Record<string, { status: string; reason: string | null }>;
  };
  missing_evidence: string[];
  priority: {
    priority_is_fully_resolved: boolean;
    review_route: string;
  };
  evidence: Record<string, unknown>;
  legacy_data_quality_flag: boolean;
}

export interface IndiciosMvpState {
  name: string;
  status: 'MVP_RULES_ONLY';
  snapshot_cut: string;
  cohort: { start: string | null; end: string | null; rows: number; method: string; period: string; groups: number | null; type_proxy: boolean; stage_scope: string };
  created_at: string;
  coverage: { signal: number; no_confirmed_signal: number; no_evaluable_family: number; partial_or_unknown: number; complete_family_evaluation: number; by_stage: Record<string, number> };
  index: { available: false; meaning: string };
  priority_analysis: { policy: string; weights_calibrated: false; fully_resolved_priorities: number; targets: number; limitations: string[] };
  source_hash_sha256: string | null;
  database_generation_consistency_verified: boolean;
  cohort_generation_note: string;
  filters: { contract_types: string[]; modalities: string[]; stages: string[] };
}

const API = import.meta.env.VITE_INDICIOS_API_URL || 'http://127.0.0.1:8011';

async function read<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API}${path}`, { signal, headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(response.status === 404 ? 'No hay evaluación disponible para este contrato.' : 'No se pudo cargar el corte de indicios.');
  return response.json() as Promise<T>;
}

export function getIndiciosState(signal?: AbortSignal) {
  return read<IndiciosMvpState>('/api/indicios/estado', signal);
}

export function getIndiciosMethodology(signal?: AbortSignal) {
  return read<{ methodology: string[]; status: string; index: IndiciosMvpState['index'] }>('/api/indicios/metodologia', signal);
}

export function getIndiciosPage(params: URLSearchParams, signal?: AbortSignal) {
  return read<{ total: number | null; has_more: boolean; page: number; size: number; items: IndicioMvp[] }>(`/api/indicios/resultados?${params}`, signal);
}

export function getIndicioByRawId(rawId: number, signal?: AbortSignal) {
  return read<IndicioMvp>(`/api/indicios/contrato?raw_id=${encodeURIComponent(rawId)}`, signal);
}
