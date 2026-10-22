import React, { useState, useEffect, useCallback } from 'react';
import { Play, Loader2, RefreshCw, AlertCircle, CheckCircle, XCircle, FileSpreadsheet, FileText } from 'lucide-react';
import { procesamientoService } from '../../services/procesamientoService';
import { jobsService } from '../../services/jobsService';
import type { PaginatedProcesamientoLogsDTO, ProcesamientoLogDTO } from '../../types/procesado';
import { cn } from '../../utils/utils';
import { downloadExport } from '../../utils/download';
import { getErrorMessage } from '../../utils/errors';

export const AdminReprocesamiento: React.FC = () => {
  const [logs, setLogs] = useState<PaginatedProcesamientoLogsDTO | null>(null);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [page, setPage] = useState(1);
  const [size] = useState(20);

  const [isReprocessing, setIsReprocessing] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const hasRunningProcess = logs?.items.some((log) => log.estado === 'EN_PROCESO') ?? false;
  const busy = isReprocessing || hasRunningProcess;
  const [forzarReproceso, setForzarReproceso] = useState(false);

  // Simple toast/alert state
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const fetchLogs = useCallback(async (hideLoading = false) => {
    if (!hideLoading) setLoadingLogs(true);
    try {
      const data = await procesamientoService.getLogs(page, size);
      setLogs(data);
    } catch (err: unknown) {
      console.error('Error fetching logs:', getErrorMessage(err, 'Error desconocido'));
    } finally {
      if (!hideLoading) setLoadingLogs(false);
    }
  }, [page, size]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchLogs();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [fetchLogs]);

  // Polling if any log is EN_PROCESO
  useEffect(() => {
    if (busy) {
      const interval = setInterval(() => {
        fetchLogs(true);
      }, 5000); // refresh every 5 seconds silently
      return () => clearInterval(interval);
    }
  }, [busy, fetchLogs]);

  useEffect(() => {
    if (!activeJobId) return;
    let cancelled = false;
    let checking = false;
    const checkStatus = async () => {
      if (checking) return;
      checking = true;
      try {
        const job = await jobsService.get(activeJobId);
        if (cancelled) return;
        if (job.status === 'EXITOSO' || job.status === 'ERROR' || job.status === 'PARCIAL') {
          setActiveJobId(null);
          setIsReprocessing(false);
          setToast(job.status === 'EXITOSO'
            ? { type: 'success', message: 'Reprocesamiento finalizado con éxito.' }
            : { type: 'error', message: job.error_message || 'El reprocesamiento no terminó correctamente.' });
          void fetchLogs();
        }
      } catch (error: unknown) {
        if (!cancelled) {
          console.error('Error checking reprocessing job:', getErrorMessage(error, 'Error desconocido'));
          setToast({ type: 'error', message: 'No se pudo consultar el estado. Se reintentará.' });
        }
      } finally {
        checking = false;
      }
    };
    void checkStatus();
    const interval = window.setInterval(() => { void checkStatus(); }, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [activeJobId, fetchLogs]);

  const handleReprocesar = async () => {
    if (busy) return;
    setIsReprocessing(true);
    setToast(null);
    try {
      const accepted = await procesamientoService.reprocesar(forzarReproceso);
      setActiveJobId(accepted.id);
      setToast({ type: 'success', message: 'Reprocesamiento iniciado. El avance se actualizará automáticamente.' });
      void fetchLogs();
    } catch (error: unknown) {
      console.error('Error in reprocesar:', getErrorMessage(error, 'Error desconocido'));
      setToast({ 
        type: 'error', 
        message: getErrorMessage(error, 'Error al ejecutar reprocesamiento.')
      });
      void fetchLogs();
      setIsReprocessing(false);
    }
  };

  const handleExportCSV = () => downloadExport('/api/procesados/logs/export/csv', 'historial_reprocesamiento.csv');
  const handleExportExcel = () => downloadExport('/api/procesados/logs/export/xlsx', 'historial_reprocesamiento.xlsx');

  const getStatusBadge = (estado: string) => {
    switch (estado) {
      case 'EXITOSO':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
            <CheckCircle size={12} />
            Exitoso
          </span>
        );
      case 'EN_PROCESO':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 animate-pulse">
            <Loader2 size={12} className="animate-spin" />
            En Proceso
          </span>
        );
      case 'ERROR':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
            <XCircle size={12} />
            Error
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-800">
            {estado}
          </span>
        );
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('es-CO');
  };

  return (
    <div className="space-y-6">
      {/* Header section */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <RefreshCw className="text-emerald-500" />
            Pipeline de Normalización
          </h1>
          <p className="text-slate-500 mt-1">
            Gestiona y supervisa la ejecución del pipeline de normalización de datos.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={handleExportCSV}
            disabled={!logs?.items?.length}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            <FileText size={15} />
            Exportar CSV
          </button>
          <button
            onClick={handleExportExcel}
            disabled={!logs?.items?.length}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-40 disabled:cursor-not-allowed shadow-sm transition-all"
          >
            <FileSpreadsheet size={15} />
            Exportar Excel
          </button>
        </div>
      </div>

      {/* Control Panel */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-4">Control de Ejecución</h2>
        
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-50 p-4 rounded-lg border border-slate-100">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <input 
                type="checkbox" 
                id="forzar_reproceso" 
                checked={forzarReproceso}
                onChange={(e) => setForzarReproceso(e.target.checked)}
                disabled={busy}
                className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
              />
              <label htmlFor="forzar_reproceso" className="text-sm font-medium text-slate-700 cursor-pointer">
                Forzar reproceso
              </label>
            </div>
            <p className="text-xs text-slate-500 pl-6">
              Si está activo, se volverán a evaluar todos los contratos y puede tardar varias horas.
              Si está inactivo, se procesarán los registros crudos nuevos o actualizados.
            </p>
          </div>
          
          <button
            onClick={handleReprocesar}
            disabled={busy}
            className={cn(
              "flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold text-white transition-all",
              busy
                ? "bg-emerald-400 cursor-not-allowed" 
                : "bg-emerald-600 hover:bg-emerald-700 shadow-sm hover:shadow"
            )}
          >
            {busy ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                Ejecutando...
              </>
            ) : (
              <>
                <Play size={18} />
                Ejecutar Reprocesamiento
              </>
            )}
          </button>
        </div>

        {/* Toast Notification */}
        {toast && (
          <div className={cn(
            "mt-4 p-4 rounded-lg flex items-center gap-3 border",
            toast.type === 'success' 
              ? "bg-emerald-50 border-emerald-200 text-emerald-800" 
              : "bg-red-50 border-red-200 text-red-800"
          )}>
            {toast.type === 'success' ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
            <span className="text-sm font-medium">{toast.message}</span>
          </div>
        )}
      </div>

      {/* Logs Table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col">
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-800">Historial de Ejecuciones</h2>
          {loadingLogs && !busy && (
            <Loader2 size={18} className="text-slate-400 animate-spin" />
          )}
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-white">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Estado</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Inicio / Fin</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Duración</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Eval</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Procesados</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Omitidos</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Anomalías</th>
                <th className="px-6 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">Forzado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {loadingLogs && !logs ? (
                <tr>
                  <td colSpan={8} className="px-6 py-8 text-center text-slate-500 text-sm">
                    Cargando historial...
                  </td>
                </tr>
              ) : logs?.items && logs.items.length > 0 ? (
                logs.items.map((log: ProcesamientoLogDTO) => (
                  <tr key={log.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(log.estado)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                      <div>{formatDate(log.fecha_hora_inicio)}</div>
                      <div className="text-xs text-slate-400 mt-0.5">{log.fecha_hora_fin ? formatDate(log.fecha_hora_fin) : '...'}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 text-right">
                      {log.duracion_segundos !== null ? `${log.duracion_segundos}s` : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 text-right font-medium">
                      {log.total_evaluados.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-emerald-600 text-right font-medium">
                      {log.procesados.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 text-right">
                      {log.omitidos.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-orange-500 text-right font-medium">
                      {log.anomalias_registradas.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <span className={cn(
                        "inline-flex px-2 py-0.5 text-xs rounded-md font-medium",
                        log.forzar_reproceso ? "bg-slate-200 text-slate-700" : "bg-slate-100 text-slate-500"
                      )}>
                        {log.forzar_reproceso ? 'SÍ' : 'NO'}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center text-slate-500 text-sm">
                    <div className="flex flex-col items-center gap-2">
                      <RefreshCw size={24} className="text-slate-300" />
                      <p>No hay registros de ejecución en el historial.</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination controls */}
        {logs && logs.total > size && (
          <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
            <span className="text-sm text-slate-500">
              Mostrando {logs.items.length} de {logs.total} registros
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 border border-slate-300 rounded text-sm text-slate-600 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-100 bg-white"
              >
                Anterior
              </button>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={page * size >= logs.total}
                className="px-3 py-1 border border-slate-300 rounded text-sm text-slate-600 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-100 bg-white"
              >
                Siguiente
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
