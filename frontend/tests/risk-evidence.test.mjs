import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { createServer } from 'vite';
import { readFile } from 'node:fs/promises';

let vite;
let riskReasonLabel;
let riskAmountLabel;
let getRiskResults;
let getRiskStatus;
let getProcesados;
let getMetricasCalidad;
let api;
let secopSourceUrl;
before(async () => {
  vite = await createServer({ configFile: false, logLevel: 'silent', server: { middlewareMode: true }, appType: 'custom' });
  ({ riskReasonLabel, riskAmountLabel } = await vite.ssrLoadModule('/src/utils/riskEvidence.ts'));
  ({ getRiskResults,getRiskStatus } = await vite.ssrLoadModule('/src/services/riskService.ts'));
  ({ getProcesados,getMetricasCalidad } = await vite.ssrLoadModule('/src/services/procesadosService.ts'));
  ({ default: api } = await vite.ssrLoadModule('/src/api/axios.ts'));
  ({ secopSourceUrl } = await vite.ssrLoadModule('/src/utils/secopLink.ts'));
});
after(async () => { await vite?.close(); });

test('risk explanations describe missing evidence and ambiguous identity in citizen language', () => {
  assert.match(riskReasonLabel('sin_evidencia:log_presupuesto'), /Presupuesto estimado/);
  assert.match(riskReasonLabel('fuera_de_referencia:categoria'), /Categoría de compra/);
  assert.match(riskReasonLabel('identidad_operacion_ambigua'), /misma operación/);
  assert.match(riskReasonLabel('sin_reconstruccion_temporal_de_etapa'), /captura actual/);
  assert.match(riskReasonLabel('revisiones_de_etapa_en_conflicto'), /discrepancia/);
  assert.match(riskReasonLabel('unknown_internal_code'), /limitación adicional/);
});

test('risk amounts preserve large decimal strings and show missing values explicitly', () => {
  assert.equal(riskAmountLabel('123456789012345678901234.25'), '123.456.789.012.345.678.901.234,25');
  assert.equal(riskAmountLabel('9007199254740991.25'), '9.007.199.254.740.991,25');
  assert.equal(riskAmountLabel(null), 'No disponible');
  assert.equal(riskAmountLabel('NaN'), 'No disponible');
  assert.equal(riskAmountLabel('100.25'), '100,25');
});

test('risk results pin the cut selected by the status request', async () => {
  const previous = api.get;
  api.get = async (url, config) => {
    assert.equal(url, '/api/riesgo/resultados');
    assert.equal(config.params.get('cut_id'), 'frozen-cut');
    assert.deepEqual(config.params.getAll('raw_secop_ids'), ['7', '9']);
    return { data: { items: [], total: 0, cut_id: 'frozen-cut' } };
  };
  try { await getRiskResults([7, 9], undefined, 'frozen-cut'); }
  finally { api.get = previous; }
});

test('official SECOP links share the backend fixtures and reject unsafe destinations', async () => {
  const examples = JSON.parse(await readFile(new URL('../../Backend/tests/fixtures/secop_links.json', import.meta.url), 'utf8'));
  for (const example of examples) assert.equal(secopSourceUrl(example.input), example.expected, JSON.stringify(example.input));
});

test('data, quality and risk requests pin the same citizen cut without global mutable defaults',async()=>{
  const previous=api.get;
  const calls=[];
  api.get=async (url,config)=>{
    calls.push([url,config.headers['X-Public-Cut']]);
    return {data:{items:[],total:0,available:false,cut_id:null},headers:{'x-public-cut':'citizen-v1'}};
  };
  try {
    await getRiskStatus(undefined,'citizen-v1');
    const rows=await getProcesados({},undefined,'citizen-v1');
    await getMetricasCalidad(undefined,rows.publicCutId);
    await getRiskResults([1],undefined,'risk-v1','citizen-v1');
    await getRiskStatus(undefined,'citizen-v2');
    assert.deepEqual(calls.map(x=>x[1]),['citizen-v1','citizen-v1','citizen-v1','citizen-v1','citizen-v2']);
    assert.equal(api.defaults.headers.common['X-Public-Cut'],undefined);
  } finally {api.get=previous;}
});
