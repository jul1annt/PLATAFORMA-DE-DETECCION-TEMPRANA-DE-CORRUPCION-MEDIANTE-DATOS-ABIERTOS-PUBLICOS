import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getProcesadoById, getAnomaliasByRawSecopId } from '../services/procesadosService';
import type { Procesado, AnomaliaContrato } from '../types/procesado';
import { PublicNavbar } from '../components/layout/PublicNavbar';


export const PublicContratoDetalle: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const [contrato, setContrato] = useState<Procesado | null>(null);
  const [anomalias, setAnomalias] = useState<AnomaliaContrato[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        if (!id) throw new Error("ID no proporcionado");
        
        const contratoData = await getProcesadoById(id);
        setContrato(contratoData);
        
        // Fetch anomalies if the record has suspicious/incomplete flags
        if (contratoData.raw_secop_id && (contratoData.es_sospechoso || contratoData.es_incompleto)) {
          const anomaliasData = await getAnomaliasByRawSecopId(contratoData.raw_secop_id);
          setAnomalias(anomaliasData);
        }
      } catch (err: any) {
        setError(err.message || "Error al cargar los detalles del contrato");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen font-sans bg-slate-50 relative overflow-hidden flex flex-col items-center justify-center">
        <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-indigo-600 mb-6"></div>
        <p className="text-indigo-900 font-bold uppercase tracking-widest text-sm animate-pulse">Analizando contrato...</p>
      </div>
    );
  }

  if (error || !contrato) {
    return (
      <div className="min-h-screen font-sans bg-slate-50 flex flex-col items-center justify-center p-8">
        <div className="bg-white p-10 rounded-[40px] shadow-2xl shadow-red-100 border border-red-50 text-center max-w-md w-full">
          <div className="w-20 h-20 bg-red-100 text-red-500 rounded-full flex items-center justify-center text-4xl mx-auto mb-6">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-2xl font-black text-slate-800 mb-2">Contrato no encontrado</h2>
          <p className="text-slate-500 mb-8 font-medium">{error || "El registro solicitado no existe o no está disponible."}</p>
          <button 
            onClick={() => navigate('/public/procesados')}
            className="w-full py-4 bg-slate-900 text-white rounded-2xl font-bold uppercase tracking-widest text-sm hover:bg-slate-800 transition-colors"
          >
            Volver al listado
          </button>
        </div>
      </div>
    );
  }

  const isIncompleto = contrato.es_incompleto === true;
  const isAltoRiesgo = contrato.clasificacion_riesgo === 'ALTO';
  const isModificado = contrato.datos_modificados === true;
  const hasAlerts = isIncompleto || isAltoRiesgo || isModificado;

  return (
    <div className="min-h-screen font-sans text-slate-900 relative overflow-hidden bg-slate-50 pb-20">
      {/* Mesh Gradient Background */}
      <div className="fixed inset-0 z-0 opacity-40 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-indigo-300 blur-[120px]"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-violet-300 blur-[120px]"></div>
        <div className="absolute top-[20%] right-[10%] w-[30%] h-[30%] rounded-full bg-blue-200 blur-[100px]"></div>
      </div>

      {/* ── Shared Public Navbar ───────────────────────────────────────────── */}
      <PublicNavbar />

      <main className="max-w-[1000px] mx-auto px-8 py-6 relative z-10">
        {/* Back button */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/public/procesados')}
            className="flex items-center gap-2 px-5 py-2.5 bg-white border border-slate-200 text-slate-600 text-xs font-bold uppercase tracking-widest rounded-full hover:bg-slate-50 transition-all shadow-sm"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Volver al listado
          </button>
        </div>

        
        {/* Banner Alertas Superiores */}
        {hasAlerts && (
          <div className="mb-10 flex flex-col gap-3">
            {isModificado && (
              <div className="bg-red-50 border border-red-200 rounded-2xl p-4 flex items-center gap-4 shadow-sm relative overflow-hidden">
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-red-500"></div>
                <div className="w-10 h-10 bg-red-500 rounded-full flex items-center justify-center text-white shadow-lg shrink-0">
                  <span className="text-xl italic font-black">⚡</span>
                </div>
                <div>
                  <h4 className="text-red-700 font-bold uppercase tracking-wider text-sm">Datos Modificados</h4>
                  <p className="text-red-600/80 text-xs font-medium">Este registro ha sufrido modificaciones importantes desde su publicación original.</p>
                </div>
              </div>
            )}
            {isAltoRiesgo && (
              <div className="bg-rose-50 border border-rose-200 rounded-2xl p-4 flex items-center gap-4 shadow-sm relative overflow-hidden">
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-rose-500"></div>
                <div className="w-10 h-10 bg-rose-500 rounded-full flex items-center justify-center text-white shadow-lg shrink-0">
                  <span className="text-xl">🚨</span>
                </div>
                <div>
                  <h4 className="text-rose-700 font-bold uppercase tracking-wider text-sm">Riesgo Alto Detectado</h4>
                  <p className="text-rose-600/80 text-xs font-medium">El sistema de analítica ha clasificado este contrato con un nivel de riesgo elevado.</p>
                </div>
              </div>
            )}
            {isIncompleto && (
              <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex items-center gap-4 shadow-sm relative overflow-hidden">
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-amber-500"></div>
                <div className="w-10 h-10 bg-amber-500 rounded-full flex items-center justify-center text-white shadow-lg shrink-0">
                  <span className="text-xl">⚠️</span>
                </div>
                <div>
                  <h4 className="text-amber-700 font-bold uppercase tracking-wider text-sm">Registro Incompleto</h4>
                  <p className="text-amber-600/80 text-xs font-medium">Faltan campos críticos obligatorios en la estructura de este contrato.</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Título */}
        <div className="mb-8">
          <h1 className="text-4xl font-black text-indigo-950 tracking-tighter mb-2 leading-tight">
            Detalle del Contrato
          </h1>
          <p className="text-slate-500 font-medium">ID Interno: {contrato.id} • Secop ID: {contrato.raw_secop_id}</p>
        </div>

        {/* Sección: Información General */}
        <div className="bg-white rounded-[40px] shadow-xl shadow-indigo-100/50 border border-slate-100 overflow-hidden mb-10">
          <div className="px-8 py-6 border-b border-slate-50 bg-slate-50/50">
            <h3 className="text-lg font-black text-slate-800 uppercase tracking-widest">Información General</h3>
          </div>
          <div className="p-8 grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Entidad</span>
              <span className="text-lg font-black text-slate-800 leading-tight">{contrato.entidad_normalizada || 'No especificada'}</span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Proveedor Normalizado</span>
              <span className="text-lg font-black text-slate-800 leading-tight text-indigo-700">{contrato.proveedor_normalizado || 'No especificado'}</span>
            </div>
            
            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Modalidad de Contratación</span>
              <div>
                <span className="inline-flex px-3 py-1 bg-indigo-50 text-indigo-600 rounded-lg text-xs font-bold uppercase tracking-widest border border-indigo-100">
                  {contrato.modalidad_contratacion || 'N/A'}
                </span>
              </div>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Tipo de Contrato</span>
              <span className="text-sm font-bold text-slate-600">{contrato.tipo_contrato_normalizado || 'N/A'}</span>
            </div>

            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Valor Total Normalizado</span>
              <span className="text-2xl font-black text-emerald-600 bg-emerald-50 self-start px-4 py-1 rounded-xl border border-emerald-100">
                $ {contrato.valor_total_normalizado?.toLocaleString('es-ES') || '0'}
              </span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Fechas Relevantes</span>
              <div className="flex flex-col gap-1 mt-1">
                <div className="flex items-center gap-2 text-sm text-slate-600 font-medium">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  Publicación: <strong className="text-slate-800">{contrato.fecha_publicacion_normalizada ? new Date(contrato.fecha_publicacion_normalizada).toLocaleDateString('es-ES') : 'N/A'}</strong>
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-600 font-medium">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Adjudicación: <strong className="text-slate-800">{contrato.fecha_adjudicacion_normalizada ? new Date(contrato.fecha_adjudicacion_normalizada).toLocaleDateString('es-ES') : 'N/A'}</strong>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Ubicación</span>
              <span className="text-sm font-bold text-slate-600">{contrato.ciudad_entidad || 'Ciudad N/A'}, {contrato.departamento_entidad || 'Dpto N/A'}</span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Estado</span>
              <div>
                <span className="inline-flex px-3 py-1 bg-slate-100 text-slate-600 rounded-lg text-xs font-bold uppercase tracking-widest">
                  {contrato.estado_normalizado || 'N/A'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Sección: Anomalías Detectadas */}
        <div className="mb-10">
          <h3 className="text-xl font-black text-slate-800 uppercase tracking-widest mb-6 px-2">Anomalías Detectadas</h3>
          
          {anomalias.length === 0 ? (
            <div className="bg-emerald-50 border border-emerald-100 rounded-3xl p-8 flex items-center gap-6 shadow-sm">
              <div className="w-16 h-16 bg-emerald-400 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-emerald-200">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div>
                <h4 className="text-emerald-800 font-black text-xl mb-1">Registro Limpio</h4>
                <p className="text-emerald-700/80 font-medium">Este contrato no presenta anomalías detectadas en su estructura o valores.</p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {anomalias.map((a) => {
                let colorClass = "bg-blue-50 border-blue-200 text-blue-800";
                let icon = "ℹ️";
                let label = "INFO";
                
                if (a.clasificacion_riesgo === 'ALTO') {
                  colorClass = "bg-rose-50 border-rose-200 text-rose-800";
                  icon = "🚨";
                  label = "RIESGO ALTO";
                } else if (a.clasificacion_riesgo === 'MEDIO' || a.motivo === 'CAMPO_FALTANTE') {
                  colorClass = "bg-amber-50 border-amber-200 text-amber-800";
                  icon = "⚠️";
                  label = "ADVERTENCIA";
                }

                return (
                  <div key={a.id} className={`rounded-[32px] border p-6 flex flex-col md:flex-row gap-6 items-start md:items-center ${colorClass}`}>
                    <div className="flex items-center gap-4 w-full md:w-1/3">
                      <div className="text-3xl bg-white w-14 h-14 rounded-2xl flex items-center justify-center shadow-sm">
                        {icon}
                      </div>
                      <div>
                        <span className="text-[10px] font-black tracking-widest uppercase opacity-70 block mb-1">{label}</span>
                        <strong className="text-lg font-black leading-tight block">{a.motivo.replace(/_/g, ' ')}</strong>
                      </div>
                    </div>
                    
                    <div className="w-full md:w-2/3 bg-white/60 p-4 rounded-2xl border border-white">
                      <p className="text-sm font-medium opacity-90 mb-2">
                        {a.descripcion || 'Se detectó una inconsistencia en los datos del contrato.'}
                      </p>
                      {a.campo_afectado && (
                        <div className="flex flex-wrap gap-4 text-xs font-bold">
                          <span className="bg-white px-3 py-1.5 rounded-lg shadow-sm border border-white/50">
                            Campo: <span className="uppercase opacity-80">{a.campo_afectado}</span>
                          </span>
                          {a.valor_original && (
                            <span className="bg-white px-3 py-1.5 rounded-lg shadow-sm border border-white/50">
                              Valor Crudo: <span className="opacity-80 line-through">{a.valor_original}</span>
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Sección: Origen y Metadata */}
        <div className="bg-white rounded-[40px] shadow-xl shadow-indigo-100/50 border border-slate-100 overflow-hidden">
          <div className="px-8 py-6 border-b border-slate-50 bg-slate-50/50">
            <h3 className="text-lg font-black text-slate-800 uppercase tracking-widest">Metadata de Sincronización</h3>
          </div>
          <div className="p-8">
            <div className="flex flex-col md:flex-row gap-8 justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-slate-100 rounded-2xl flex items-center justify-center text-slate-400">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                  </svg>
                </div>
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-1">Fuente del Dato</span>
                  <span className="text-sm font-black text-slate-700">SECOP (Datos Abiertos Públicos)</span>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-slate-100 rounded-2xl flex items-center justify-center text-slate-400">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-1">Última Actualización</span>
                  <span className="text-sm font-black text-slate-700">
                    {contrato.created_at ? new Date(contrato.created_at).toLocaleString('es-ES') : 'N/A'}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-indigo-50 rounded-2xl flex items-center justify-center text-indigo-400">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <div className="max-w-[200px]">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-1">Data Hash (Integridad)</span>
                  <span className="text-xs font-mono font-bold text-indigo-600 truncate block" title={contrato.normalized_hash}>
                    {contrato.normalized_hash || 'No disponible'}
                  </span>
                </div>
              </div>
            </div>
            
            <div className="mt-8 pt-8 border-t border-slate-100 flex justify-center">
              {(() => {
                const getCleanUrl = (url?: string): string => {
                  if (!url) return '';
                  const trimmed = url.trim();
                  if (!trimmed) return '';
                  
                  if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
                    const match = trimmed.match(/https?:\/\/[^\s'}"]+/);
                    if (match) return match[0];
                  }
                  return trimmed;
                };
                
                const cleanUrl = getCleanUrl(contrato.urlproceso);
                
                if (cleanUrl) {
                  return (
                    <button 
                      onClick={() => window.open(cleanUrl, "_blank", "noopener,noreferrer")}
                      className="flex items-center gap-2 px-6 py-3 bg-slate-900 text-white rounded-xl text-xs font-black uppercase tracking-widest hover:bg-indigo-600 transition-colors shadow-lg shadow-slate-200"
                    >
                      Ver Original en SECOP
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </button>
                  );
                }
                
                return (
                <button 
                  disabled
                  className="flex items-center gap-2 px-6 py-3 bg-slate-200 text-slate-400 rounded-xl text-xs font-black uppercase tracking-widest cursor-not-allowed"
                >
                  URL no disponible
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </button>
                  );
              })()}
            </div>
          </div>
        </div>

      </main>
    </div>
  );
};
