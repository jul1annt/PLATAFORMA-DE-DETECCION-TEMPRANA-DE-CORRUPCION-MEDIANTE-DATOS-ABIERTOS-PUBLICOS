import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Play } from 'lucide-react';
import toast from 'react-hot-toast';
import { 
  runProcesamiento, 
  getContratosProcesados, 
  getCalidadResumen, 
  getCalidadProblemas, 
  getCambios 
} from '../services/api';

import DashboardCards from './DashboardCards';
import ContractsTable from './ContractsTable';
import QualityTable from './QualityTable';
import ChangesTable from './ChangesTable';

export default function QualityDashboard() {
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  
  const [resumen, setResumen] = useState([]);
  const [contratos, setContratos] = useState([]);
  const [problemas, setProblemas] = useState([]);
  const [cambios, setCambios] = useState([]);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [resResumen, resContratos, resProblemas, resCambios] = await Promise.all([
        getCalidadResumen(),
        getContratosProcesados(),
        getCalidadProblemas(),
        getCambios()
      ]);

      setResumen(resResumen.data);
      setContratos(resContratos.data);
      setProblemas(resProblemas.data);
      setCambios(resCambios.data);
    } catch (err) {
      console.error('Error fetching quality data:', err);
      toast.error('Error al cargar datos del servidor');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleProcess = async () => {
    try {
      setProcessing(true);
      const loadingToast = toast.loading('Procesando datos crudos...');
      
      const { data } = await runProcesamiento();
      
      toast.success(
        `Procesamiento completado. Nuevos: ${data.new_records}, Actualizados: ${data.updated_records}`, 
        { id: loadingToast }
      );
      
      // Reload data
      fetchData();
    } catch (err) {
      console.error('Error running process:', err);
      toast.dismiss();
      toast.error('Error durante el procesamiento. Revisa los logs del servidor.');
    } finally {
      setProcessing(false);
    }
  };

  if (loading && contratos.length === 0) {
    return (
      <div className="py-24 flex flex-col items-center justify-center">
        <div className="w-8 h-8 border-4 border-brand-200 border-t-brand-600 rounded-full animate-spin"></div>
        <p className="text-gray-500 mt-4 font-medium">Cargando métricas de calidad...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-xl shadow-sm border border-gray-200">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Módulo de Calidad y Procesamiento</h2>
          <p className="text-sm text-gray-500 mt-1">
            Analiza inconsistencias, datos faltantes y mutaciones en los contratos extraídos.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchData}
            disabled={loading || processing}
            className="p-2 text-gray-500 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition-colors disabled:opacity-50"
            title="Refrescar datos"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
          
          <button 
            onClick={handleProcess}
            disabled={processing}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors shadow-sm focus:ring-2 focus:ring-offset-2 focus:ring-gray-900 disabled:opacity-75 disabled:cursor-not-allowed"
          >
            {processing ? (
              <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
            ) : (
              <Play className="w-4 h-4 fill-current" />
            )}
            Procesar Datos Crudos
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <DashboardCards resumen={resumen} />

      {/* Main Tables */}
      <ContractsTable contratos={contratos} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <QualityTable problemas={problemas} />
        <ChangesTable cambios={cambios} />
      </div>
    </div>
  );
}
