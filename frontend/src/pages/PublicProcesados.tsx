import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import type { Procesado, MetricasCalidad, CampoFaltante, QualityFilterType } from '../types/procesado';
import { getProcesados, getMetricasCalidad, getCamposFaltantes } from '../services/procesadosService';
import { AlertIcons } from '../components/AlertIcons';
import { QualitySummaryBanner } from '../components/QualitySummaryBanner';
import { SearchAutocomplete } from '../components/SearchAutocomplete';
import { PublicNavbar } from '../components/layout/PublicNavbar';

export const PublicProcesados: React.FC = () => {
  const [procesados, setProcesados] = useState<Procesado[]>([]);
  const [metricas, setMetricas] = useState<MetricasCalidad | null>(null);
  const [camposFaltantes, setCamposFaltantes] = useState<CampoFaltante[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // Bridge: if ?filter= came from dashboard KPI cards, translate to ?calidad=
  useEffect(() => {
    const filterParam = searchParams.get('filter');
    if (filterParam) {
      const newParams = new URLSearchParams(searchParams);
      newParams.delete('filter');
      newParams.set('calidad', filterParam);
      setSearchParams(newParams, { replace: true });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);


  const activeFilter = (searchParams.get('calidad') as QualityFilterType) || 'ALL';
  const setActiveFilter = (filter: QualityFilterType) => {
    const newParams = new URLSearchParams(searchParams);
    if (filter === 'ALL') {
      newParams.delete('calidad');
    } else {
      newParams.set('calidad', filter);
    }
    newParams.set('offset', '0');
    setSearchParams(newParams);
  };

  const [totalItems, setTotalItems] = useState(0);
  


  const limitStr = searchParams.get('limit') || '25';
  const limit = parseInt(limitStr, 10);
  const offsetStr = searchParams.get('offset') || '0';
  const offset = parseInt(offsetStr, 10);
  const sort = searchParams.get('sort') || '';
  const order = searchParams.get('order') || 'desc';

  const [montoMin, setMontoMin] = useState(searchParams.get('montoMin') || '');
  const [montoMax, setMontoMax] = useState(searchParams.get('montoMax') || '');
  const [fechaDesde, setFechaDesde] = useState(searchParams.get('fechaDesde') || '');
  const [fechaHasta, setFechaHasta] = useState(searchParams.get('fechaHasta') || '');
  const [modalidad, setModalidad] = useState<string>(searchParams.get('modalidad') || '');
  
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

  const [entidad, setEntidad] = useState(searchParams.get('entidad') || '');
  const [proveedor, setProveedor] = useState(searchParams.get('proveedor') || '');
  const [estado, setEstado] = useState(searchParams.get('estado') || '');
  const [nivelConfianzaMin, setNivelConfianzaMin] = useState(searchParams.get('nivelConfianzaMin') || '');
  const [nivelConfianzaMax, setNivelConfianzaMax] = useState(searchParams.get('nivelConfianzaMax') || '');
  const [isFilterOpen, setIsFilterOpen] = useState(false);

  const applyFilters = () => {
    const newParams = new URLSearchParams(searchParams);
    if (montoMin) newParams.set('montoMin', montoMin); else newParams.delete('montoMin');
    if (montoMax) newParams.set('montoMax', montoMax); else newParams.delete('montoMax');
    if (fechaDesde) newParams.set('fechaDesde', fechaDesde); else newParams.delete('fechaDesde');
    if (fechaHasta) newParams.set('fechaHasta', fechaHasta); else newParams.delete('fechaHasta');
    if (modalidad) newParams.set('modalidad', modalidad); else newParams.delete('modalidad');
    if (entidad) newParams.set('entidad', entidad); else newParams.delete('entidad');
    if (proveedor) newParams.set('proveedor', proveedor); else newParams.delete('proveedor');
    if (estado) newParams.set('estado', estado); else newParams.delete('estado');
    if (nivelConfianzaMin) newParams.set('nivelConfianzaMin', nivelConfianzaMin); else newParams.delete('nivelConfianzaMin');
    if (nivelConfianzaMax) newParams.set('nivelConfianzaMax', nivelConfianzaMax); else newParams.delete('nivelConfianzaMax');
    newParams.set('offset', '0');
    setSearchParams(newParams);
  };

  const clearFilters = () => {
    setMontoMin('');
    setMontoMax('');
    setFechaDesde('');
    setFechaHasta('');
    setModalidad('');
    setEntidad('');
    setProveedor('');
    setEstado('');
    setNivelConfianzaMin('');
    setNivelConfianzaMax('');
    const newParams = new URLSearchParams();
    newParams.set('limit', limitStr);
    setSearchParams(newParams);
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const params: Record<string, string> = {};
        const pMontoMin = searchParams.get('montoMin');
        const pMontoMax = searchParams.get('montoMax');
        const pFechaDesde = searchParams.get('fechaDesde');
        const pFechaHasta = searchParams.get('fechaHasta');
        const pModalidad = searchParams.get('modalidad');
        const pEntidad = searchParams.get('entidad');
        const pProveedor = searchParams.get('proveedor');
        const pEstado = searchParams.get('estado');
        const pNivelConfianzaMin = searchParams.get('nivelConfianzaMin');
        const pNivelConfianzaMax = searchParams.get('nivelConfianzaMax');

        if (pMontoMin) params.valor_min = pMontoMin;
        if (pMontoMax) params.valor_max = pMontoMax;
        if (pFechaDesde) params.fecha_inicio = pFechaDesde;
        if (pFechaHasta) params.fecha_fin = pFechaHasta;
        if (pModalidad) params.modalidad = pModalidad;
        if (pEntidad) params.entidad = pEntidad;
        if (pProveedor) params.proveedor = pProveedor;
        if (pEstado) params.estado = pEstado;
        if (pNivelConfianzaMin) params.nivel_confianza_min = pNivelConfianzaMin;
        if (pNivelConfianzaMax) params.nivel_confianza_max = pNivelConfianzaMax;
        
        params.limit = limitStr;
        params.offset = offsetStr;
        if (sort) params.sort = sort;
        if (order) params.order = order;
        
        if (activeFilter === 'INCOMPLETOS') params.solo_incompletos = 'true';
        if (activeFilter === 'SOSPECHOSOS') params.solo_sospechosos = 'true';
        if (activeFilter === 'ALTO_RIESGO') params.solo_alto_riesgo = 'true';


        const [procesadosData, metricasData, camposData] = await Promise.all([
          getProcesados(params),
          getMetricasCalidad(),
          getCamposFaltantes()
        ]);
        setProcesados(procesadosData.items);
        setTotalItems(procesadosData.total);
        setMetricas(metricasData);
        setCamposFaltantes(camposData);
      } catch (err: any) {
        setError(err.message || 'Error al cargar los datos');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [searchParams]);

  const hayCambiosRecientes = useMemo(() => {
    return procesados.some(p => p.datos_modificados === true);
  }, [procesados]);

  const searchQuery = searchParams.get('q') || '';

  const displayedProcesados = useMemo(() => {
    let filtered = procesados;

    // 1. Aplicar filtro de búsqueda de texto (Autocomplete)
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(p => {
        if (!p) return false;
        const e = String(p.entidad_normalizada || p.entidad || '').toLowerCase();
        const pr = String(p.proveedor_normalizado || p.proveedor || '').toLowerCase();
        return e.includes(q) || pr.includes(q);
      });
    }

    if (activeFilter === 'MODIFICADOS') {
      filtered = filtered.filter(p => p.datos_modificados === true);
    }
    
    return filtered;
  }, [procesados, activeFilter, searchQuery]);

  const totalPages = Math.ceil(totalItems / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  const handleSort = (field: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (sort === field) {
      newParams.set('order', order === 'asc' ? 'desc' : 'asc');
    } else {
      newParams.set('sort', field);
      newParams.set('order', 'asc');
    }
    newParams.set('offset', '0');
    setSearchParams(newParams);
  };

  const handlePageChange = (page: number) => {
    const newParams = new URLSearchParams(searchParams);
    newParams.set('offset', String((page - 1) * limit));
    setSearchParams(newParams);
  };

  const handleLimitChange = (newLimit: number) => {
    const newParams = new URLSearchParams(searchParams);
    newParams.set('limit', String(newLimit));
    newParams.set('offset', '0');
    setSearchParams(newParams);
  };

  const SortIcon = ({ field }: { field: string }) => {
    if (sort !== field) return <span className="opacity-0 group-hover:opacity-30">↕</span>;
    return <span>{order === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <div className="min-h-screen font-sans text-slate-900 relative overflow-hidden bg-slate-50">
      {/* Mesh Gradient Background */}
      <div className="fixed inset-0 z-0 opacity-40 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-indigo-300 blur-[120px]"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-violet-300 blur-[120px]"></div>
        <div className="absolute top-[20%] right-[10%] w-[30%] h-[30%] rounded-full bg-blue-200 blur-[100px]"></div>
      </div>

      {/* ── Shared Public Navbar ─────────────────────────────────────────────── */}
      <PublicNavbar />


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

            {/* Controles de Filtros */}
            <div className="flex flex-col gap-4 mb-8">
              <div className="flex justify-between items-center">
                <button
                  onClick={() => setIsFilterOpen(!isFilterOpen)}
                  className="flex items-center gap-2 bg-white border border-slate-200 px-5 py-2.5 rounded-2xl shadow-sm hover:bg-slate-50 transition-colors text-sm font-black text-indigo-950"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                  </svg>
                  {isFilterOpen ? 'Ocultar Filtros Avanzados' : 'Mostrar Filtros Avanzados'}
                </button>

                <div className="inline-flex items-center gap-3 bg-white border border-slate-200 px-5 py-2.5 rounded-2xl shadow-sm">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Filtro de calidad:</span>
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

              {/* Panel de Filtros Avanzados */}
              {isFilterOpen && (
                <div className="bg-white p-6 rounded-[24px] border border-slate-200 shadow-xl shadow-indigo-100/50 animate-in fade-in slide-in-from-top-4 duration-300">
                  {/* Nueva sección de Búsqueda Inteligente */}
                  <div className="mb-8 p-6 bg-slate-50/50 rounded-3xl border border-dashed border-slate-200">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white shadow-md">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                      </div>
                      <h4 className="text-sm font-black text-indigo-950 uppercase tracking-widest">Búsqueda Inteligente (Autocomplete)</h4>
                    </div>
                    <SearchAutocomplete data={procesados} />
                    <p className="mt-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                      Escribe el nombre de una entidad o proveedor para filtrar instantáneamente.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {/* Monto */}
                    <div>
                      <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">Rango de Monto</h4>
                      <div className="flex gap-3">
                        <div className="flex-1">
                          <label className="text-[10px] font-bold text-slate-400 block mb-1">Mínimo</label>
                          <input 
                            type="number" 
                            min="0"
                            placeholder="Ej. 1000000"
                            value={montoMin}
                            onChange={(e) => setMontoMin(e.target.value)}
                            className="w-full text-sm font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                          />
                        </div>
                        <div className="flex-1">
                          <label className="text-[10px] font-bold text-slate-400 block mb-1">Máximo</label>
                          <input 
                            type="number" 
                            min="0"
                            placeholder="Ej. 50000000"
                            value={montoMax}
                            onChange={(e) => setMontoMax(e.target.value)}
                            className="w-full text-sm font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Fecha */}
                    <div>
                      <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">Período</h4>
                      <div className="flex gap-3">
                        <div className="flex-1">
                          <label className="text-[10px] font-bold text-slate-400 block mb-1">Desde</label>
                          <input 
                            type="date" 
                            value={fechaDesde}
                            onChange={(e) => setFechaDesde(e.target.value)}
                            className="w-full text-sm font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                          />
                        </div>
                        <div className="flex-1">
                          <label className="text-[10px] font-bold text-slate-400 block mb-1">Hasta</label>
                          <input 
                            type="date" 
                            value={fechaHasta}
                            onChange={(e) => setFechaHasta(e.target.value)}
                            className="w-full text-sm font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Modalidad */}
                    <div>
                      <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">Modalidad</h4>
                      <div className="relative">
                        <select
                          value={modalidad}
                          onChange={(e) => setModalidad(e.target.value)}
                          className="w-full text-sm font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 pr-10 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all cursor-pointer appearance-none"
                        >
                          <option value="">Seleccionar modalidad...</option>
                          {MODALIDADES.map(mod => (
                            <option key={mod} value={mod}>{mod}</option>
                          ))}
                        </select>
                        <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none">
                          <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
                          </svg>
                        </div>
                      </div>
                    </div>

                    {/* Actores (Entidad y Proveedor) */}
                    <div>
                      <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">Actores</h4>
                      <div className="flex flex-col gap-3">
                        <div>
                          <label className="text-[10px] font-bold text-slate-400 block mb-1">Entidad</label>
                          <input 
                            type="text" 
                            placeholder="Nombre de la entidad"
                            value={entidad}
                            onChange={(e) => setEntidad(e.target.value)}
                            className="w-full text-sm font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                          />
                        </div>
                        <div>
                          <label className="text-[10px] font-bold text-slate-400 block mb-1">Proveedor</label>
                          <input 
                            type="text" 
                            placeholder="Nombre o NIT"
                            value={proveedor}
                            onChange={(e) => setProveedor(e.target.value)}
                            className="w-full text-sm font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Estado y Confianza */}
                    <div className="md:col-span-2 lg:col-span-2">
                      <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">Calidad y Estado</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <label className="text-[10px] font-bold text-slate-400 block mb-1">Estado del Procedimiento</label>
                          <input 
                            type="text" 
                            placeholder="Ej. Celebrado, Liquidado..."
                            value={estado}
                            onChange={(e) => setEstado(e.target.value)}
                            className="w-full text-sm font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                          />
                        </div>
                        <div className="flex gap-3">
                          <div className="flex-1">
                            <label className="text-[10px] font-bold text-slate-400 block mb-1">Confianza Mínima (%)</label>
                            <input 
                              type="number" 
                              min="0" max="100"
                              placeholder="0"
                              value={nivelConfianzaMin}
                              onChange={(e) => setNivelConfianzaMin(e.target.value)}
                              className="w-full text-sm font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                            />
                          </div>
                          <div className="flex-1">
                            <label className="text-[10px] font-bold text-slate-400 block mb-1">Confianza Máxima (%)</label>
                            <input 
                              type="number" 
                              min="0" max="100"
                              placeholder="100"
                              value={nivelConfianzaMax}
                              onChange={(e) => setNivelConfianzaMax(e.target.value)}
                              className="w-full text-sm font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-8 flex justify-end gap-3 border-t border-slate-100 pt-6">
                    <button 
                      onClick={clearFilters}
                      className="px-6 py-2 bg-white text-slate-500 text-xs font-black uppercase tracking-widest rounded-xl hover:bg-slate-50 border border-slate-200 transition-all"
                    >
                      Limpiar Filtros
                    </button>
                    <button 
                      onClick={applyFilters}
                      className="px-6 py-2 bg-indigo-600 text-white text-xs font-black uppercase tracking-widest rounded-xl hover:bg-indigo-700 shadow-lg shadow-indigo-200 transition-all"
                    >
                      Aplicar Filtros
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Listado de Contratos */}
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
                <div className="flex items-center gap-3">
                  <span className="text-xs font-black px-5 py-2.5 bg-indigo-50 text-indigo-600 rounded-2xl border border-indigo-100">
                    Total: {totalItems}
                  </span>
                  <span className="text-xs font-bold text-slate-400">
                    Página {currentPage} de {totalPages || 1}
                  </span>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead>
                    <tr className="bg-slate-50/30 border-b border-slate-50">
                      <th onClick={() => handleSort('entidad')} className="cursor-pointer group px-6 py-5 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.15em] hover:bg-slate-100 transition-colors">
                        Entidad <SortIcon field="entidad" />
                      </th>
                      <th onClick={() => handleSort('proveedor')} className="cursor-pointer group px-6 py-5 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.15em] hover:bg-slate-100 transition-colors">
                        Proveedor <SortIcon field="proveedor" />
                      </th>
                      <th onClick={() => handleSort('valor')} className="cursor-pointer group px-6 py-5 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.15em] hover:bg-slate-100 transition-colors">
                        Valor <SortIcon field="valor" />
                      </th>
                      <th onClick={() => handleSort('fecha')} className="cursor-pointer group px-6 py-5 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.15em] hover:bg-slate-100 transition-colors">
                        Fecha <SortIcon field="fecha" />
                      </th>
                      <th className="px-6 py-5 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.15em]">
                        Modalidad
                      </th>
                      <th className="px-6 py-5 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.15em]">
                        Riesgo / Indicadores
                      </th>
                      <th className="px-6 py-5 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.15em]">
                        Estado Calidad
                      </th>
                      <th onClick={() => handleSort('riesgo')} className="cursor-pointer group px-6 py-5 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.15em] hover:bg-slate-100 transition-colors">
                        Nivel de Confianza <SortIcon field="riesgo" />
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    {displayedProcesados.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="px-10 py-24 text-center">
                          <div className="flex flex-col items-center justify-center">
                            <div className="w-16 h-16 bg-slate-50 text-slate-300 rounded-full flex items-center justify-center text-3xl mb-4 shadow-inner">
                              🔍
                            </div>
                            <h4 className="text-lg font-black text-slate-700 mb-1">No se encontraron contratos relacionados</h4>
                            <p className="text-sm font-medium text-slate-400">Intenta con otros términos de búsqueda o limpia los filtros.</p>
                          </div>
                        </td>
                      </tr>
                    ) : (
                      displayedProcesados.map((p, idx) => {
                        const isIncompleto = p.es_incompleto === true;
                        const isSospechoso = p.es_sospechoso === true;
                        const confianza = p.nivel_confianza ?? 100;

                        let rowClass = "hover:bg-slate-50/50 transition-colors group border-l-4";
                        if (isSospechoso) {
                          rowClass += " bg-red-50/10 border-red-500";
                        } else if (isIncompleto) {
                          rowClass += " bg-amber-50/10 border-amber-500";
                        } else {
                          rowClass += " border-emerald-400/50";
                        }

                        let estadoCalidadText = "Óptimo";
                        if (isSospechoso && isIncompleto) estadoCalidadText = "Sospechoso / Incompleto";
                        else if (isSospechoso) estadoCalidadText = "Sospechoso";
                        else if (isIncompleto) estadoCalidadText = "Incompleto";

                        return (
                          <tr 
                            key={p.id || idx} 
                            onClick={() => navigate(`/public/procesados/${p.id}`)}
                            className={`${rowClass} cursor-pointer`}
                          >
                            <td className="px-6 py-4">
                              <div className="text-xs font-bold text-slate-700 line-clamp-2" title={p.entidad_normalizada}>
                                {p.entidad_normalizada || 'N/A'}
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              <div className="text-xs font-bold text-slate-600 line-clamp-2" title={p.proveedor_normalizado}>
                                {p.proveedor_normalizado || 'N/A'}
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              <div className="text-xs font-black text-slate-900 whitespace-nowrap">
                                $ {p.valor_total_normalizado?.toLocaleString('es-ES') || '0'}
                              </div>
                            </td>
                            <td className="px-6 py-4 text-xs font-bold text-slate-500 whitespace-nowrap">
                              {p.fecha_publicacion_normalizada ? new Date(p.fecha_publicacion_normalizada).toLocaleDateString('es-ES') : 'N/A'}
                            </td>
                            <td className="px-6 py-4">
                              <span className={`inline-flex items-center px-2 py-1 rounded text-[9px] font-black tracking-wider uppercase ${
                                idx % 3 === 0 ? 'bg-indigo-50 text-indigo-500' : 
                                idx % 3 === 1 ? 'bg-emerald-50 text-emerald-500' : 
                                'bg-violet-50 text-violet-500'
                              }`}>
                                {p.modalidad_contratacion || 'N/A'}
                              </span>
                            </td>
                            <td className="px-6 py-4">
                              <div className="flex gap-2 items-center">
                                {isSospechoso && (
                                  <span className="cursor-help text-base" title="Contrato sospechoso">🚨</span>
                                )}
                                {isIncompleto && (
                                  <span className="cursor-help text-base" title="Datos incompletos">⚠️</span>
                                )}
                                {!isSospechoso && !isIncompleto && (
                                  <span className="text-emerald-500 text-sm">✅</span>
                                )}
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              <span className={`text-xs font-bold ${
                                isSospechoso ? 'text-red-600' : 
                                isIncompleto ? 'text-amber-600' : 
                                'text-emerald-600'
                              }`}>
                                {estadoCalidadText}
                              </span>
                            </td>
                            <td className="px-6 py-4">
                              <div className="flex items-center gap-2">
                                <div className="w-full bg-slate-100 rounded-full h-2 max-w-[60px]">
                                  <div 
                                    className={`h-2 rounded-full ${
                                      confianza >= 80 ? 'bg-emerald-500' : 
                                      confianza >= 50 ? 'bg-amber-500' : 
                                      'bg-red-500'
                                    }`}
                                    style={{ width: `${confianza}%` }}
                                  ></div>
                                </div>
                                <span className="text-xs font-black text-slate-600">{confianza}%</span>
                              </div>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>

              {/* Controles de Paginación */}
              {totalPages > 1 && (
                <div className="px-10 py-6 bg-slate-50/30 border-t border-slate-50 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-slate-500">Filas por página:</span>
                    <select 
                      value={limit}
                      onChange={(e) => handleLimitChange(Number(e.target.value))}
                      className="text-xs font-black text-slate-700 bg-white border border-slate-200 rounded-xl px-2 py-1 outline-none cursor-pointer"
                    >
                      <option value={20}>20</option>
                      <option value={25}>25</option>
                      <option value={50}>50</option>
                      <option value={100}>100</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-4">
                    <button
                      onClick={() => handlePageChange(currentPage - 1)}
                      disabled={currentPage === 1}
                      className="px-6 py-2 bg-white border border-slate-200 rounded-xl text-xs font-black uppercase tracking-widest text-slate-600 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-slate-50 transition-colors shadow-sm"
                    >
                      Anterior
                    </button>
                    <div className="flex items-center gap-2">
                      {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                        let pageNum = i + 1;
                        if (totalPages > 5 && currentPage > 3) {
                          pageNum = Math.min(currentPage - 2 + i, totalPages - 4 + i);
                        }
                        return (
                          <button
                            key={pageNum}
                            onClick={() => handlePageChange(pageNum)}
                            className={`w-10 h-10 rounded-xl text-xs font-black transition-all ${
                              currentPage === pageNum 
                              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-100' 
                              : 'bg-white border border-slate-200 text-slate-400 hover:border-indigo-300'
                            }`}
                          >
                            {pageNum}
                          </button>
                        );
                      })}
                    </div>
                    <button
                      onClick={() => handlePageChange(currentPage + 1)}
                      disabled={currentPage === totalPages}
                      className="px-6 py-2 bg-white border border-slate-200 rounded-xl text-xs font-black uppercase tracking-widest text-slate-600 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-slate-50 transition-colors shadow-sm"
                    >
                      Siguiente
                    </button>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
};
