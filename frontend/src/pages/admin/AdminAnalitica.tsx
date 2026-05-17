import React, { useState, useEffect } from 'react';
import { 
  Brain, 
  TrendingUp, 
  Layers, 
  Activity, 
  CheckCircle, 
  AlertCircle, 
  Loader2, 
  ShieldAlert, 
  Sparkles,
  Calendar,
  Sliders,
  RefreshCw
} from 'lucide-react';
import { analiticaService } from '../../services/analiticaService';
import type { PesoAnomaliaResponse } from '../../services/analiticaService';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { cn } from '../../utils/utils';

export const AdminAnalitica: React.FC = () => {
  // Loading states
  const [loadingOutliers, setLoadingOutliers] = useState(false);
  const [loadingDuplicados, setLoadingDuplicados] = useState(false);
  const [loadingDirectas, setLoadingDirectas] = useState(false);
  const [loadingRiesgo, setLoadingRiesgo] = useState(false);
  const [loadingPesos, setLoadingPesos] = useState(false);

  // MODALIDADES list
  const MODALIDADES = [
    'CONCURSO DE MÉRITOS ABIERTO',
    'CONTRATACIÓN DIRECTA',
    'CONTRATACIÓN DIRECTA (CON OFERTAS)',
    'CONTRATACIÓN RÉGIMEN ESPECIAL',
    'CONTRATACIÓN RÉGIMEN ESPECIAL (CON OFERTAS)',
    'ENAJENACIÓN DE BIENES CON SOBRE CERRADO',
    'ENAJENACIÓN DE BIENES CON SUBASTA',
    'LICITACIÓN PÚBLICA',
    'LICITACIÓN PÚBLICA ACUERDO MARCO DE PRECIOS',
    'LICITACIÓN PÚBLICA OBRA PUBLICA',
    'MÍNIMA CUANTÍA',
    'SELECCIÓN ABREVIADA DE MENOR CUANTÍA',
    'SELECCION ABREVIADA MENOR CUANTIA SIN MANIFESTACION INTERES',
    'SELECCIÓN ABREVIADA SUBASTA INVERSA',
    'SOLICITUD DE INFORMACIÓN A LOS PROVEEDORES',
    'SUBASTA DE PRUEBA'
  ];

  // Weights state
  const [pesos, setPesos] = useState<PesoAnomaliaResponse[]>([]);
  const [editingPesos, setEditingPesos] = useState<Record<string, string>>({});
  const [savingPeso, setSavingPeso] = useState<Record<string, boolean>>({});

  // Input states for Outliers
  const [outlierCampo, setOutlierCampo] = useState<'valor_total_normalizado' | 'precio_base_normalizado' | 'nivel_confianza' | 'cantidad_campos_faltantes'>('valor_total_normalizado');
  const [outlierFechaCampo, setOutlierFechaCampo] = useState<'fecha_publicacion_normalizada' | 'fecha_adjudicacion_normalizada' | ''>('');
  const [outlierFechaDesde, setOutlierFechaDesde] = useState('');
  const [outlierFechaHasta, setOutlierFechaHasta] = useState('');
  const [outlierModalidad, setOutlierModalidad] = useState('');

  // Input states for Duplicados
  const [duplicadoFechaDesde, setDuplicadoFechaDesde] = useState('');
  const [duplicadoFechaHasta, setDuplicadoFechaHasta] = useState('');

  // Input states for Adjudicaciones Directas
  const [directaFechaDesde, setDirectaFechaDesde] = useState('');
  const [directaFechaHasta, setDirectaFechaHasta] = useState('');
  const [directaMinimo, setDirectaMinimo] = useState(3);
  const [directaDiasVentana, setDirectaDiasVentana] = useState(90);

  // Toast / Results
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [results, setResults] = useState<Record<string, any>>({});

  // Fetch weights on mount
  useEffect(() => {
    fetchWeights();
  }, []);

  const fetchWeights = async () => {
    setLoadingPesos(true);
    try {
      const data = await analiticaService.getPesos();
      setPesos(data);
      const editing: Record<string, string> = {};
      data.forEach((p) => {
        editing[p.tipo_anomalia] = p.peso.toString();
      });
      setEditingPesos(editing);
    } catch (error) {
      console.error('Error fetching weights:', error);
      // Set some fallback defaults in case backend weights are empty/errored
      const fallbacks = [
        { tipo_anomalia: 'OUTLIER', peso: 1.0 },
        { tipo_anomalia: 'DUPLICADO_CORTO', peso: 1.5 },
        { tipo_anomalia: 'ABUSO_DIRECTO', peso: 2.0 }
      ];
      setPesos(fallbacks);
      setEditingPesos({ OUTLIER: '1.0', DUPLICADO_CORTO: '1.5', ABUSO_DIRECTO: '2.0' });
    } finally {
      setLoadingPesos(false);
    }
  };

  const showToast = (type: 'success' | 'error', message: string) => {
    setToast({ type, message });
    setTimeout(() => {
      setToast(null);
    }, 6000);
  };

  // Run calculation: Outliers
  const handleCalcularOutliers = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoadingOutliers(true);
    setToast(null);
    try {
      const payload: any = {
        campo: outlierCampo,
      };
      
      if (outlierFechaCampo) {
        payload.fecha_campo = outlierFechaCampo;
      }
      if (outlierFechaDesde) {
        payload.fecha_desde = outlierFechaDesde;
      }
      if (outlierFechaHasta) {
        payload.fecha_hasta = outlierFechaHasta;
      }
      if (outlierModalidad) {
        payload.modalidad = outlierModalidad;
      }

      const res = await analiticaService.calcularOutliers(payload);
      setResults((prev) => ({ ...prev, outliers: res }));
      showToast(
        'success',
        `Análisis IQR finalizado. Se procesaron ${res.total_contratos_analizados.toLocaleString()} contratos. Outliers detectados: ${res.total_outliers.toLocaleString()} (${(res.porcentaje_outliers * 100).toFixed(2)}%)`
      );
    } catch (err: any) {
      console.error(err);
      showToast('error', err.response?.data?.detail || 'Error al ejecutar análisis de outliers.');
    } finally {
      setLoadingOutliers(false);
    }
  };

  // Run calculation: Duplicados
  const handleCalcularDuplicados = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoadingDuplicados(true);
    setToast(null);
    try {
      const res = await analiticaService.calcularDuplicados({
        fecha_desde: duplicadoFechaDesde || null,
        fecha_hasta: duplicadoFechaHasta || null,
      });
      setResults((prev) => ({ ...prev, duplicados: res }));
      showToast(
        'success',
        `Análisis de duplicados finalizado. Se detectaron ${res.total_duplicados.toLocaleString()} contratos duplicados en período corto. Score promedio: ${res.promedio_score.toFixed(2)}`
      );
    } catch (err: any) {
      console.error(err);
      showToast('error', err.response?.data?.detail || 'Error al ejecutar análisis de duplicados.');
    } finally {
      setLoadingDuplicados(false);
    }
  };

  // Run calculation: Adjudicaciones Directas
  const handleCalcularDirectas = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoadingDirectas(true);
    setToast(null);
    try {
      const res = await analiticaService.calcularDirectas({
        fecha_desde: directaFechaDesde || null,
        fecha_hasta: directaFechaHasta || null,
        minimo_directas: directaMinimo,
        dias_ventana: directaDiasVentana,
      });
      setResults((prev) => ({ ...prev, directas: res }));
      showToast(
        'success',
        `Análisis de adjudicaciones directas finalizado. Se identificaron ${res.total_proveedores_detectados.toLocaleString()} proveedores con posible abuso de adjudicación directa.`
      );
    } catch (err: any) {
      console.error(err);
      showToast('error', err.response?.data?.detail || 'Error al ejecutar análisis de adjudicaciones directas.');
    } finally {
      setLoadingDirectas(false);
    }
  };

  // Run calculation: Riesgo Global
  const handleCalcularRiesgo = async () => {
    setLoadingRiesgo(true);
    setToast(null);
    try {
      const res = await analiticaService.calcularRiesgo();
      setResults((prev) => ({ ...prev, riesgo: res }));
      showToast(
        'success',
        `Riesgo global recalculado con éxito para ${res.total_proveedores_evaluados.toLocaleString()} proveedores. Score final promedio: ${res.promedio_score_final.toFixed(2)}`
      );
    } catch (err: any) {
      console.error(err);
      showToast('error', err.response?.data?.detail || 'Error al calcular riesgo global.');
    } finally {
      setLoadingRiesgo(false);
    }
  };

  // Update Weight
  const handleSavePeso = async (tipo: string) => {
    const rawVal = editingPesos[tipo];
    const val = parseFloat(rawVal);
    if (isNaN(val) || val < 0) {
      showToast('error', 'El peso debe ser un número decimal válido mayor o igual a 0.');
      return;
    }

    setSavingPeso((prev) => ({ ...prev, [tipo]: true }));
    try {
      await analiticaService.actualizarPeso(tipo, val);
      showToast('success', `Peso para ${tipo} actualizado a ${val} con éxito.`);
      fetchWeights();
    } catch (err: any) {
      console.error(err);
      showToast('error', err.response?.data?.detail || `Error al actualizar peso para ${tipo}.`);
    } finally {
      setSavingPeso((prev) => ({ ...prev, [tipo]: false }));
    }
  };

  const handleEditPesoChange = (tipo: string, val: string) => {
    setEditingPesos((prev) => ({
      ...prev,
      [tipo]: val,
    }));
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header section */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Brain className="text-indigo-600" />
            Motor Analítico y Pesos de Riesgo
          </h1>
          <p className="text-slate-500 mt-1">
            Ejecuta algoritmos de analítica avanzada y parametriza los pesos del score de riesgo combinado.
          </p>
        </div>
      </div>

      {/* Global alert / Toast status */}
      {toast && (
        <div className={cn(
          "p-4 rounded-xl flex items-start gap-3 border shadow-sm transition-all",
          toast.type === 'success' 
            ? "bg-indigo-50 border-indigo-200 text-indigo-800" 
            : "bg-red-50 border-red-200 text-red-800"
        )}>
          {toast.type === 'success' ? (
            <CheckCircle size={20} className="mt-0.5 text-indigo-600 flex-shrink-0" />
          ) : (
            <AlertCircle size={20} className="mt-0.5 text-red-600 flex-shrink-0" />
          )}
          <div className="text-sm font-semibold">{toast.message}</div>
        </div>
      )}

      {/* Grid for weights and global calculation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Side: Parameters / Weight Config */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader className="bg-slate-50 border-b border-slate-100">
              <CardTitle className="text-lg font-bold text-slate-800 flex items-center gap-2">
                <Sliders className="text-indigo-500" size={18} />
                Configuración de Pesos de Anomalías
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <p className="text-sm text-slate-500">
                Ajusta el nivel de impacto de cada anomalía en el cálculo final del Score de Riesgo Combinado.
                Los pesos son multiplicadores decimales libres sin requerimiento de suma obligatoria (ej. 1.0, 1.3, 2.5).
              </p>

              {loadingPesos ? (
                <div className="flex items-center justify-center py-6 text-slate-400 gap-2">
                  <Loader2 className="animate-spin" size={18} />
                  <span>Cargando pesos de base de datos...</span>
                </div>
              ) : (
                <div className="space-y-4">
                  {pesos.map((p) => {
                    const currentVal = editingPesos[p.tipo_anomalia] ?? p.peso.toString();
                    return (
                      <div 
                        key={p.tipo_anomalia} 
                        className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl border border-slate-100 bg-slate-50 hover:bg-slate-100/50 transition-colors"
                      >
                        <div className="space-y-1">
                          <span className="inline-flex px-2 py-0.5 text-xs font-bold rounded bg-indigo-100 text-indigo-800">
                            {p.tipo_anomalia === 'OUTLIER' ? 'Peso Outlier' : 
                             (p.tipo_anomalia === 'DUPLICADO' || p.tipo_anomalia === 'DUPLICADO_CORTO') ? 'Peso Duplicado' : 
                             (p.tipo_anomalia === 'DIRECTA' || p.tipo_anomalia === 'ABUSO_DIRECTO') ? 'Peso Directa' : p.tipo_anomalia}
                          </span>
                          <h4 className="text-sm font-semibold text-slate-800 mt-1">
                            {p.tipo_anomalia === 'OUTLIER' && 'Outliers / Precios Atípicos (IQR)'}
                            {(p.tipo_anomalia === 'DUPLICADO' || p.tipo_anomalia === 'DUPLICADO_CORTO') && 'Duplicados en Período Corto'}
                            {(p.tipo_anomalia === 'DIRECTA' || p.tipo_anomalia === 'ABUSO_DIRECTO') && 'Abuso de Contratación Directa'}
                          </h4>
                          {p.updated_at && (
                            <p className="text-xxs text-slate-400">
                              Última actualización: {new Date(p.updated_at).toLocaleString('es-CO')}
                            </p>
                          )}
                        </div>

                        <div className="flex items-center gap-3">
                          <div className="flex items-center gap-2">
                            <input
                              type="number"
                              min="0"
                              step="0.1"
                              inputMode="decimal"
                              value={currentVal}
                              onChange={(e) => handleEditPesoChange(p.tipo_anomalia, e.target.value)}
                              className="w-24 text-center rounded-lg border-slate-200 text-sm font-bold text-slate-800 focus:ring-indigo-500 focus:border-indigo-500"
                            />
                          </div>
                          <button
                            onClick={() => handleSavePeso(p.tipo_anomalia)}
                            disabled={savingPeso[p.tipo_anomalia]}
                            className="px-3.5 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 disabled:opacity-40 transition-colors flex items-center gap-1.5 shadow-sm"
                          >
                            {savingPeso[p.tipo_anomalia] ? (
                              <Loader2 size={12} className="animate-spin" />
                            ) : (
                              'Guardar'
                            )}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Side: Global Risk Action */}
        <div className="space-y-6">
          <Card className="h-full flex flex-col justify-between border-indigo-200 shadow-md">
            <CardHeader className="bg-gradient-to-br from-indigo-900 to-indigo-950 text-white rounded-t-xl">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg font-bold flex items-center gap-2">
                  <ShieldAlert className="text-indigo-400" size={20} />
                  Paso Final: Riesgo Global
                </CardTitle>
                <Sparkles size={16} className="text-amber-300 animate-pulse" />
              </div>
              <p className="text-indigo-200 text-xs mt-1">
                Recalcula el puntaje consolidado aplicando los pesos ponderados.
              </p>
            </CardHeader>
            <CardContent className="p-6 flex-1 flex flex-col justify-between space-y-6">
              <div className="text-slate-600 text-sm space-y-3">
                <p>
                  Esta acción consolida los resultados más recientes de:
                </p>
                <ul className="list-disc pl-5 space-y-1 text-xs text-slate-500 font-medium">
                  <li>Outliers (IQR)</li>
                  <li>Duplicados en período corto</li>
                  <li>Abuso de adjudicación directa</li>
                </ul>
                <p className="text-xs text-slate-400 italic">
                  Actualiza el score combinado por proveedor y detecta anomalías complejas.
                </p>
              </div>

              {results.riesgo && (
                <div className="bg-indigo-50 border border-indigo-100 p-3 rounded-lg text-xs text-indigo-950 space-y-1.5 font-medium">
                  <div className="flex items-center justify-between text-indigo-900">
                    <span>Proveedores Evaluados:</span>
                    <strong className="text-indigo-950">{results.riesgo.total_proveedores_evaluados.toLocaleString()}</strong>
                  </div>
                  <div className="flex items-center justify-between text-indigo-900">
                    <span>Score Final Promedio:</span>
                    <strong className="text-indigo-950">{results.riesgo.promedio_score_final.toFixed(2)}</strong>
                  </div>
                  <div className="text-xxs text-slate-400 text-right mt-1">
                    Último cálculo: {new Date(results.riesgo.fecha_calculo).toLocaleTimeString('es-CO')}
                  </div>
                </div>
              )}

              <button
                onClick={handleCalcularRiesgo}
                disabled={loadingRiesgo}
                className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl font-bold text-sm shadow-sm transition-all hover:shadow-md flex items-center justify-center gap-2 group"
              >
                {loadingRiesgo ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    <span>Recalculando...</span>
                  </>
                ) : (
                  <>
                    <RefreshCw size={16} className="group-hover:rotate-180 transition-transform duration-500" />
                    <span>Recalcular Riesgo Global</span>
                  </>
                )}
              </button>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Grid of calculations */}
      <h2 className="text-lg font-bold text-slate-800 border-b border-slate-200 pb-2 mt-8 flex items-center gap-2">
        <Activity size={18} className="text-indigo-600" />
        Ejecución de Algoritmos Individuales
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Card: Outliers */}
        <Card className="flex flex-col justify-between hover:shadow-md transition-shadow">
          <CardHeader className="bg-slate-50 border-b border-slate-100 flex flex-row items-center gap-3">
            <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600">
              <TrendingUp size={20} />
            </div>
            <div>
              <CardTitle className="text-base font-bold text-slate-800">
                Outliers de Precios (IQR)
              </CardTitle>
              <span className="text-slate-400 text-xxs block">Algoritmo Atípicos</span>
            </div>
          </CardHeader>
          <CardContent className="p-6 flex-1 flex flex-col justify-between space-y-6">
            <form onSubmit={handleCalcularOutliers} className="space-y-4 text-xs font-medium">
              <p className="text-slate-500">
                Detecta contratos atípicos usando el rango intercuartil (IQR) agrupando por modalidad.
              </p>

              {/* Input: Campo */}
              <div className="space-y-1">
                <label className="text-slate-700">Campo Numérico a Analizar</label>
                <select
                  value={outlierCampo}
                  onChange={(e: any) => setOutlierCampo(e.target.value)}
                  className="w-full rounded-lg border-slate-200 text-xs py-1.5 focus:ring-indigo-500 focus:border-indigo-500 font-medium"
                >
                  <option value="valor_total_normalizado">Valor Total Normalizado</option>
                  <option value="precio_base_normalizado">Precio Base Normalizado</option>
                  <option value="nivel_confianza">Nivel de Confianza</option>
                  <option value="cantidad_campos_faltantes">Cantidad de Campos Faltantes</option>
                </select>
              </div>

              {/* Input: Modalidad */}
              <div className="space-y-1">
                <label className="text-slate-700">Filtrar por Modalidad (Opcional)</label>
                <select
                  value={outlierModalidad}
                  onChange={(e) => setOutlierModalidad(e.target.value)}
                  className="w-full rounded-lg border-slate-200 text-xs py-1.5 focus:ring-indigo-500 focus:border-indigo-500 font-medium"
                >
                  <option value="">Todas las modalidades</option>
                  {MODALIDADES.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>

              {/* Input: Campo de fecha */}
              <div className="space-y-1">
                <label className="text-slate-700">Campo de Fecha a Filtrar (Opcional)</label>
                <select
                  value={outlierFechaCampo}
                  onChange={(e: any) => setOutlierFechaCampo(e.target.value)}
                  className="w-full rounded-lg border-slate-200 text-xs py-1.5 focus:ring-indigo-500 focus:border-indigo-500 font-medium"
                >
                  <option value="">Sin filtro de fecha</option>
                  <option value="fecha_publicacion_normalizada">Fecha de Publicación Normalizada</option>
                  <option value="fecha_adjudicacion_normalizada">Fecha de Adjudicación Normalizada</option>
                </select>
              </div>

              {/* Inputs: Fechas */}
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <label className="text-slate-700 flex items-center gap-1">
                    <Calendar size={12} className="text-slate-400" />
                    Desde
                  </label>
                  <input
                    type="date"
                    disabled={!outlierFechaCampo}
                    value={outlierFechaDesde}
                    onChange={(e) => setOutlierFechaDesde(e.target.value)}
                    className="w-full rounded-lg border-slate-200 text-xs py-1 px-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-slate-50 disabled:text-slate-400 font-medium"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-700 flex items-center gap-1">
                    <Calendar size={12} className="text-slate-400" />
                    Hasta
                  </label>
                  <input
                    type="date"
                    disabled={!outlierFechaCampo}
                    value={outlierFechaHasta}
                    onChange={(e) => setOutlierFechaHasta(e.target.value)}
                    className="w-full rounded-lg border-slate-200 text-xs py-1 px-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-slate-50 disabled:text-slate-400 font-medium"
                  />
                </div>
              </div>

              {results.outliers && (
                <div className="bg-indigo-50/50 p-2.5 rounded-lg border border-indigo-100 text-xxs space-y-1 text-slate-600">
                  <div className="flex justify-between">
                    <span>Analizados:</span>
                    <strong>{results.outliers.total_contratos_analizados.toLocaleString()}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Outliers:</span>
                    <strong className="text-indigo-700">{results.outliers.total_outliers.toLocaleString()}</strong>
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={loadingOutliers}
                className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg font-semibold transition-colors flex items-center justify-center gap-1.5"
              >
                {loadingOutliers ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    <span>Calculando...</span>
                  </>
                ) : (
                  <span>Ejecutar análisis de outliers</span>
                )}
              </button>
            </form>
          </CardContent>
        </Card>

        {/* Card: Duplicados */}
        <Card className="flex flex-col justify-between hover:shadow-md transition-shadow">
          <CardHeader className="bg-slate-50 border-b border-slate-100 flex flex-row items-center gap-3">
            <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600">
              <Layers size={20} />
            </div>
            <div>
              <CardTitle className="text-base font-bold text-slate-800">
                Duplicados Corto Plazo
              </CardTitle>
              <span className="text-slate-400 text-xxs block">Algoritmo Frecuencia</span>
            </div>
          </CardHeader>
          <CardContent className="p-6 flex-1 flex flex-col justify-between space-y-6">
            <form onSubmit={handleCalcularDuplicados} className="space-y-4 text-xs font-medium">
              <p className="text-slate-500">
                Detecta contratos de la misma entidad y proveedor con una diferencia menor a 30 días.
              </p>

              {/* Inputs: Fechas */}
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <label className="text-slate-700 flex items-center gap-1">
                    <Calendar size={12} className="text-slate-400" />
                    Desde
                  </label>
                  <input
                    type="date"
                    value={duplicadoFechaDesde}
                    onChange={(e) => setDuplicadoFechaDesde(e.target.value)}
                    className="w-full rounded-lg border-slate-200 text-xs py-1 px-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-700 flex items-center gap-1">
                    <Calendar size={12} className="text-slate-400" />
                    Hasta
                  </label>
                  <input
                    type="date"
                    value={duplicadoFechaHasta}
                    onChange={(e) => setDuplicadoFechaHasta(e.target.value)}
                    className="w-full rounded-lg border-slate-200 text-xs py-1 px-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
              </div>

              {results.duplicados && (
                <div className="bg-indigo-50/50 p-2.5 rounded-lg border border-indigo-100 text-xxs space-y-1 text-slate-600">
                  <div className="flex justify-between">
                    <span>Duplicados Detectados:</span>
                    <strong>{results.duplicados.total_duplicados.toLocaleString()}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Promedio Días Dif:</span>
                    <strong>{results.duplicados.promedio_dias_diferencia.toFixed(1)} días</strong>
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={loadingDuplicados}
                className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg font-semibold transition-colors flex items-center justify-center gap-1.5"
              >
                {loadingDuplicados ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    <span>Calculando...</span>
                  </>
                ) : (
                  <span>Ejecutar análisis de duplicados</span>
                )}
              </button>
            </form>
          </CardContent>
        </Card>

        {/* Card: Adjudicaciones Directas */}
        <Card className="flex flex-col justify-between hover:shadow-md transition-shadow">
          <CardHeader className="bg-slate-50 border-b border-slate-100 flex flex-row items-center gap-3">
            <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600">
              <ShieldAlert size={20} />
            </div>
            <div>
              <CardTitle className="text-base font-bold text-slate-800">
                Adjudicación Directa
              </CardTitle>
              <span className="text-slate-400 text-xxs block">Algoritmo Abuso</span>
            </div>
          </CardHeader>
          <CardContent className="p-6 flex-1 flex flex-col justify-between space-y-6">
            <form onSubmit={handleCalcularDirectas} className="space-y-4 text-xs font-medium">
              <p className="text-slate-500">
                Analiza la concentración anormal de contratos adjudicados directamente en ventanas cortas.
              </p>

              {/* Threshold inputs */}
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <label className="text-slate-700">Mín. Contratos Directos</label>
                  <input
                    type="number"
                    min="1"
                    value={directaMinimo}
                    onChange={(e) => setDirectaMinimo(parseInt(e.target.value) || 1)}
                    className="w-full rounded-lg border-slate-200 text-xs py-1 px-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-700">Días Ventana</label>
                  <input
                    type="number"
                    min="1"
                    value={directaDiasVentana}
                    onChange={(e) => setDirectaDiasVentana(parseInt(e.target.value) || 1)}
                    className="w-full rounded-lg border-slate-200 text-xs py-1 px-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
              </div>

              {/* Date Filters */}
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <label className="text-slate-700 flex items-center gap-1">
                    <Calendar size={12} className="text-slate-400" />
                    Desde
                  </label>
                  <input
                    type="date"
                    value={directaFechaDesde}
                    onChange={(e) => setDirectaFechaDesde(e.target.value)}
                    className="w-full rounded-lg border-slate-200 text-xs py-1 px-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-700 flex items-center gap-1">
                    <Calendar size={12} className="text-slate-400" />
                    Hasta
                  </label>
                  <input
                    type="date"
                    value={directaFechaHasta}
                    onChange={(e) => setDirectaFechaHasta(e.target.value)}
                    className="w-full rounded-lg border-slate-200 text-xs py-1 px-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
              </div>

              {results.directas && (
                <div className="bg-indigo-50/50 p-2.5 rounded-lg border border-indigo-100 text-xxs space-y-1 text-slate-600">
                  <div className="flex justify-between">
                    <span>Proveedores Detectados:</span>
                    <strong>{results.directas.total_proveedores_detectados.toLocaleString()}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Porcentaje Directos Promedio:</span>
                    <strong>{(results.directas.promedio_porcentaje_directos).toFixed(1)}%</strong>
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={loadingDirectas}
                className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg font-semibold transition-colors flex items-center justify-center gap-1.5"
              >
                {loadingDirectas ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    <span>Calculando...</span>
                  </>
                ) : (
                  <span>Ejecutar análisis directo</span>
                )}
              </button>
            </form>
          </CardContent>
        </Card>

      </div>
    </div>
  );
};
