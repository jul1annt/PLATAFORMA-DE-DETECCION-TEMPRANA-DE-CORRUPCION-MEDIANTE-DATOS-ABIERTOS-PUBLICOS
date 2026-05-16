import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Procesado } from '../types/procesado';
import { getProcesados } from '../services/procesadosService';
import { AlertIcons } from '../components/AlertIcons';

export const PublicProcesados: React.FC = () => {
  const [procesados, setProcesados] = useState<Procesado[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [soloAlertas, setSoloAlertas] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchProcesados = async () => {
      try {
        setLoading(true);
        const data = await getProcesados();
        setProcesados(data);
      } catch (err: any) {
        setError(err.message || 'Error al cargar los datos');
      } finally {
        setLoading(false);
      }
    };
    fetchProcesados();
  }, []);

  const filteredProcesados = useMemo(() => {
    if (!soloAlertas) return procesados;
    return procesados.filter((p) => {
      const isIncompleto = p?.es_incompleto || p?.proveedor_normalizado === 'NO DEFINIDO' || p?.entidad_normalizada === 'NO DEFINIDO' || !p?.proveedor_normalizado || !p?.entidad_normalizada;
      const isAltoRiesgo = p?.clasificacion_riesgo === 'ALTO' || Number(p?.valor_total_normalizado) === 0;
      const isModificado = p?.datos_modificados || p?.es_sospechoso;
      return isIncompleto || isAltoRiesgo || isModificado;
    });
  }, [procesados, soloAlertas]);

  const stats = useMemo(() => {
    const total = procesados.length;
    const conAlertas = procesados.filter((p) => {
      const isIncompleto = p?.es_incompleto || p?.proveedor_normalizado === 'NO DEFINIDO' || p?.entidad_normalizada === 'NO DEFINIDO' || !p?.proveedor_normalizado || !p?.entidad_normalizada;
      const isAltoRiesgo = p?.clasificacion_riesgo === 'ALTO' || Number(p?.valor_total_normalizado) === 0;
      const isModificado = p?.datos_modificados || p?.es_sospechoso;
      return isIncompleto || isAltoRiesgo || isModificado;
    }).length;
    return { total, conAlertas };
  }, [procesados]);

  return (
    <div className="min-h-screen bg-[#f8fafc] font-sans text-slate-900">
      {/* Header Premium */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
        <div className="max-w-[1400px] mx-auto px-6 h-16 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-200">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <span className="text-xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-violet-600">
              Portal de Transparencia
            </span>
          </div>
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 px-5 py-2.5 bg-slate-900 text-white text-sm font-semibold rounded-full hover:bg-slate-800 transition-all active:scale-95 shadow-md shadow-slate-200"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Panel Administrativo
          </button>
        </div>
      </header>

      <main className="max-w-[1400px] mx-auto px-6 py-10">
        {/* Hero Section */}
        <div className="mb-10">
          <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight mb-3">
            Monitoreo de Contratación Pública
          </h1>
          <p className="text-lg text-slate-600 max-w-3xl leading-relaxed">
            Visualice los procesos de contratación detectados y procesados por nuestro sistema. 
            Utilice los indicadores visuales para identificar posibles anomalías o datos incompletos.
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <p className="text-sm font-medium text-slate-500 mb-1">Total Registros</p>
            <p className="text-3xl font-bold text-slate-900">{stats.total}</p>
          </div>
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <p className="text-sm font-medium text-slate-500 mb-1">Registros con Alertas</p>
            <p className="text-3xl font-bold text-amber-600">{stats.conAlertas}</p>
          </div>
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-500 mb-1">Filtro Activo</p>
              <p className="text-xl font-bold text-slate-900">{soloAlertas ? 'Solo con Alertas' : 'Todos los Registros'}</p>
            </div>
            <button
              onClick={() => setSoloAlertas(!soloAlertas)}
              className={`w-12 h-6 flex items-center rounded-full p-1 transition-colors duration-300 ${soloAlertas ? 'bg-indigo-600' : 'bg-slate-300'}`}
            >
              <div className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform duration-300 ${soloAlertas ? 'translate-x-6' : ''}`} />
            </button>
          </div>
        </div>

        {/* Table Container */}
        <div className="bg-white rounded-3xl shadow-xl shadow-slate-200/50 border border-slate-200 overflow-hidden">
          <div className="px-6 py-5 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
            <h3 className="font-bold text-slate-800">Listado de Contratos</h3>
            <span className="text-xs font-semibold px-2.5 py-1 bg-slate-200 text-slate-600 rounded-lg">
              Mostrando {filteredProcesados.length} resultados
            </span>
          </div>

          {loading ? (
            <div className="flex flex-col items-center justify-center py-20">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mb-4"></div>
              <p className="text-slate-500 font-medium">Sincronizando datos con el servidor...</p>
            </div>
          ) : error ? (
            <div className="m-6 p-4 bg-red-50 border border-red-100 text-red-700 rounded-xl flex items-center gap-3">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              {error}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-100">
                <thead>
                  <tr className="bg-slate-50/50">
                    <th className="px-6 py-4 text-left text-[11px] font-bold text-slate-500 uppercase tracking-wider">Proveedor</th>
                    <th className="px-6 py-4 text-left text-[11px] font-bold text-slate-500 uppercase tracking-wider">Entidad</th>
                    <th className="px-6 py-4 text-left text-[11px] font-bold text-slate-500 uppercase tracking-wider">Modalidad</th>
                    <th className="px-6 py-4 text-left text-[11px] font-bold text-slate-500 uppercase tracking-wider">Fecha</th>
                    <th className="px-6 py-4 text-left text-[11px] font-bold text-slate-500 uppercase tracking-wider">Monto</th>
                    <th className="px-6 py-4 text-left text-[11px] font-bold text-slate-500 uppercase tracking-wider">Alertas</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredProcesados.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-20 text-center">
                        <div className="flex flex-col items-center">
                          <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-4">
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                            </svg>
                          </div>
                          <p className="text-slate-500 font-medium">No se encontraron registros que coincidan</p>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    filteredProcesados.map((p, idx) => (
                      <tr key={p.id || idx} className="hover:bg-indigo-50/30 transition-colors group">
                        <td className="px-6 py-4">
                          <div className="font-semibold text-slate-800 group-hover:text-indigo-700 transition-colors">
                            {p.proveedor_normalizado || p.proveedor || 'N/A'}
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm text-slate-600 line-clamp-1">{p.entidad_normalizada || p.entidad || 'N/A'}</div>
                        </td>
                        <td className="px-6 py-4">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
                            {p.modalidad_contratacion || p.modalidad || 'N/A'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm text-slate-500 font-medium">
                          {p.fecha_publicacion_normalizada ? new Date(p.fecha_publicacion_normalizada).toLocaleDateString() : 'N/A'}
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm font-bold text-slate-900">
                            {p.valor_total_normalizado != null 
                              ? new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP' }).format(p.valor_total_normalizado) 
                              : 'N/A'}
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <AlertIcons procesado={p} />
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Footer info */}
        <footer className="mt-10 text-center border-t border-slate-200 pt-8">
          <p className="text-sm text-slate-400 font-medium">
            © 2026 Plataforma de Detección Temprana de Corrupción. Datos abiertos públicos.
          </p>
        </footer>
      </main>
    </div>
  );
};
