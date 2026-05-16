import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Procesado, MetricasCalidad, CampoFaltante, QualityFilterType } from '../types/procesado';
import { getProcesados, getMetricasCalidad, getCamposFaltantes } from '../services/procesadosService';
import { AlertIcons } from '../components/AlertIcons';
import { QualitySummaryBanner } from '../components/QualitySummaryBanner';

export const PublicProcesados: React.FC = () => {
  const [procesados, setProcesados] = useState<Procesado[]>([]);
  const [metricas, setMetricas] = useState<MetricasCalidad | null>(null);
  const [camposFaltantes, setCamposFaltantes] = useState<CampoFaltante[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<QualityFilterType>('ALL');
  
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [procesadosData, metricasData, camposData] = await Promise.all([
          getProcesados(),
          getMetricasCalidad(),
          getCamposFaltantes()
        ]);
        setProcesados(procesadosData);
        setMetricas(metricasData);
        setCamposFaltantes(camposData);
      } catch (err: any) {
        setError(err.message || 'Error al cargar los datos');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const hayCambiosRecientes = useMemo(() => {
    return procesados.some(p => p.datos_modificados === true);
  }, [procesados]);

  const filteredProcesados = useMemo(() => {
    switch (activeFilter) {
      case 'INCOMPLETOS':
        return procesados.filter(p => p.es_incompleto === true);
      case 'SOSPECHOSOS':
        return procesados.filter(p => p.es_sospechoso === true);
      case 'MODIFICADOS':
        return procesados.filter(p => p.datos_modificados === true);
      case 'ALL':
      default:
        return procesados;
    }
  }, [procesados, activeFilter]);

  return (
    <div className="min-h-screen font-sans text-slate-900 relative overflow-hidden bg-slate-50">
      {/* Mesh Gradient Background */}
      <div className="fixed inset-0 z-0 opacity-40 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-indigo-300 blur-[120px]"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-violet-300 blur-[120px]"></div>
        <div className="absolute top-[20%] right-[10%] w-[30%] h-[30%] rounded-full bg-blue-200 blur-[100px]"></div>
      </div>

      {/* Header Estilo Screenshot */}
      <header className="bg-white/80 backdrop-blur-md border-b border-slate-100 sticky top-0 z-40">
        <div className="max-w-[1400px] mx-auto px-8 h-20 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 bg-indigo-600 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-indigo-200">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <span className="text-xl font-black text-indigo-950 tracking-tight">
              Plataforma Anticorrupcion
            </span>
          </div>
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 px-6 py-2.5 bg-[#05051e] text-white text-xs font-black uppercase tracking-widest rounded-full hover:bg-black transition-all shadow-xl shadow-indigo-100"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            Panel Administrativo
          </button>
        </div>
      </header>

      <main className="max-w-[1400px] mx-auto px-8 py-12 relative z-10">
        {/* Título Principal */}
        <div className="mb-12">
          <h1 className="text-5xl font-black text-indigo-950 tracking-tighter mb-4">
            Monitoreo de Calidad de Datos
          </h1>
          <p className="text-lg text-slate-500 max-w-3xl font-medium">
            Resumen post-sincronización. Visualice los problemas detectados en la calidad de los datos y 
            filtre los registros haciendo click en las tarjetas.
          </p>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-32">
            <div className="animate-spin rounded-full h-14 w-14 border-b-2 border-indigo-600 mb-6"></div>
            <p className="text-slate-400 font-bold uppercase tracking-widest text-xs">Cargando inteligencia de datos...</p>
          </div>
        ) : error ? (
          <div className="p-6 bg-red-50 border-2 border-red-100 text-red-700 rounded-3xl flex items-center gap-4 shadow-sm">
            <span className="text-2xl">⚠️</span>
            <span className="font-bold">{error}</span>
          </div>
        ) : (
          <>
            <QualitySummaryBanner 
              metricas={metricas}
              camposFaltantes={camposFaltantes}
              hayCambiosRecientes={hayCambiosRecientes}
              activeFilter={activeFilter}
              onFilterChange={setActiveFilter}
            />

            {/* Filtro Dropdown Estilo Screenshot */}
            <div className="flex justify-end mb-8">
              <div className="inline-flex items-center gap-3 bg-white border border-slate-200 px-5 py-2.5 rounded-2xl shadow-sm">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Filtro activo:</span>
                <select 
                  value={activeFilter}
                  onChange={(e) => setActiveFilter(e.target.value as QualityFilterType)}
                  className="text-sm font-black text-indigo-700 bg-transparent border-none focus:ring-0 cursor-pointer outline-none min-w-[160px]"
                >
                  <option value="ALL">Mostrar Todos</option>
                  <option value="INCOMPLETOS">Solo Incompletos ⚠️</option>
                  <option value="SOSPECHOSOS">Solo Sospechosos 🚨</option>
                  <option value="MODIFICADOS">Solo Modificados ⚡</option>
                </select>
              </div>
            </div>

            {/* Listado de Contratos Estilo Screenshot */}
            <div className="bg-white rounded-[40px] shadow-2xl shadow-indigo-100/30 border border-slate-100 overflow-hidden">
              <div className="px-10 py-8 border-b border-slate-50 flex justify-between items-center bg-white">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-indigo-50 rounded-xl flex items-center justify-center text-indigo-600 shadow-inner">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                  </div>
                  <h3 className="text-xl font-black text-indigo-950">Listado de Contratos</h3>
                </div>
                <span className="text-xs font-black px-5 py-2.5 bg-indigo-50 text-indigo-600 rounded-2xl border border-indigo-100">
                  Mostrando {filteredProcesados.length} resultados
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead>
                    <tr className="bg-slate-50/30 border-b border-slate-50">
                      <th className="px-10 py-5 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.15em]">Proveedor</th>
                      <th className="px-10 py-5 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.15em]">Entidad</th>
                      <th className="px-10 py-5 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.15em]">Modalidad</th>
                      <th className="px-10 py-5 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.15em]">Fecha</th>
                      <th className="px-10 py-5 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.15em]">Monto</th>
                      <th className="px-10 py-5 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.15em]">Alertas</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    {filteredProcesados.map((p, idx) => (
                      <tr key={p.id || idx} className="hover:bg-slate-50/50 transition-colors group">
                        <td className="px-10 py-6">
                          <div className="text-sm font-bold text-slate-700 tracking-tight">{p.proveedor_normalizado || 'N/A'}</div>
                        </td>
                        <td className="px-10 py-6">
                          <div className="flex items-center gap-3">
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-indigo-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                            </svg>
                            <div className="text-sm font-bold text-slate-500 uppercase tracking-tighter line-clamp-1">{p.entidad_normalizada || 'N/A'}</div>
                          </div>
                        </td>
                        <td className="px-10 py-6">
                          <span className={`inline-flex items-center px-4 py-1 rounded-xl text-[10px] font-black tracking-widest uppercase ${
                            idx % 3 === 0 ? 'bg-indigo-50 text-indigo-500 border border-indigo-100' : 
                            idx % 3 === 1 ? 'bg-emerald-50 text-emerald-500 border border-emerald-100' : 
                            'bg-violet-50 text-violet-500 border border-violet-100'
                          }`}>
                            {p.modalidad_contratacion || 'N/A'}
                          </span>
                        </td>
                        <td className="px-10 py-6 text-sm font-bold text-slate-500">
                          {p.fecha_publicacion_normalizada ? new Date(p.fecha_publicacion_normalizada).toLocaleDateString('es-ES') : 'N/A'}
                        </td>
                        <td className="px-10 py-6">
                          <div className="text-sm font-black text-slate-900 tracking-tight">
                            $ {p.valor_total_normalizado?.toLocaleString('es-ES') || '0'}
                          </div>
                        </td>
                        <td className="px-10 py-6">
                          <AlertIcons procesado={p} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
};
