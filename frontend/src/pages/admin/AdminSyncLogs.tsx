import React, { useEffect, useState } from 'react';
import { RefreshCw, AlertCircle, CheckCircle, XCircle, Clock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { fuentesService } from '../../services/fuentesService';
import type { SincronizacionHistorialResponseDTO, EstadoSync } from '../../types/fuente';

const STATUS_STYLES: Record<EstadoSync, string> = {
  EXITOSO: 'bg-emerald-100 text-emerald-700',
  EN_PROCESO: 'bg-amber-100 text-amber-700',
  ERROR: 'bg-red-100 text-red-700',
};

const STATUS_ICONS: Record<EstadoSync, React.ReactNode> = {
  EXITOSO: <CheckCircle size={12} />,
  EN_PROCESO: <Clock size={12} />,
  ERROR: <XCircle size={12} />,
};

const AdminSyncLogs: React.FC = () => {
  const [logs, setLogs] = useState<SincronizacionHistorialResponseDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fuentesService.getSincronizacionesGlobales();
      setLogs(data);
    } catch {
      setError('No se pudieron cargar los logs de sincronización.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchLogs(); }, []);

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center">
            <RefreshCw size={20} className="text-purple-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Logs de Sincronización</h1>
            <p className="text-slate-500 text-sm">
              Historial completo de sincronizaciones de todas las fuentes
            </p>
          </div>
        </div>
        <button
          id="sync-logs-refresh-btn"
          onClick={fetchLogs}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 border border-slate-200 hover:bg-slate-50 text-slate-600 text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Actualizar
        </button>
      </div>

      {/* Summary badges */}
      {!loading && !error && (
        <div className="flex gap-3 flex-wrap">
          {(['EXITOSO', 'EN_PROCESO', 'ERROR'] as EstadoSync[]).map((s) => {
            const count = logs.filter((l) => l.estado === s).length;
            return (
              <span
                key={s}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold ${STATUS_STYLES[s]}`}
              >
                {STATUS_ICONS[s]}
                {s}: {count}
              </span>
            );
          })}
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600">
            Total: {logs.length}
          </span>
        </div>
      )}

      {/* Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base text-slate-700">Historial</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-12 bg-slate-100 animate-pulse rounded-lg" />
              ))}
            </div>
          ) : error ? (
            <div className="flex flex-col items-center gap-2 py-10 text-red-500">
              <AlertCircle size={32} />
              <p className="text-sm">{error}</p>
              <button onClick={fetchLogs} className="text-xs underline hover:no-underline">
                Reintentar
              </button>
            </div>
          ) : logs.length === 0 ? (
            <p className="text-center text-slate-400 py-10 text-sm">
              No hay logs de sincronización registrados.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-500 border-b border-slate-100">
                    <th className="pb-3 pr-4 font-medium">ID</th>
                    <th className="pb-3 pr-4 font-medium">Fuente</th>
                    <th className="pb-3 pr-4 font-medium">Inicio</th>
                    <th className="pb-3 pr-4 font-medium">Fin</th>
                    <th className="pb-3 pr-4 font-medium">Traídos</th>
                    <th className="pb-3 pr-4 font-medium">Insertados</th>
                    <th className="pb-3 pr-4 font-medium">Duplicados</th>
                    <th className="pb-3 font-medium">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {logs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3 pr-4 text-slate-400 font-mono text-xs">#{log.id}</td>
                      <td className="py-3 pr-4 font-medium text-slate-700">
                        {log.fuente_nombre ?? `Fuente #${log.fuente_id}`}
                      </td>
                      <td className="py-3 pr-4 text-slate-500 text-xs whitespace-nowrap">
                        {new Date(log.fecha_inicio).toLocaleString('es-CO')}
                      </td>
                      <td className="py-3 pr-4 text-slate-500 text-xs whitespace-nowrap">
                        {log.fecha_fin
                          ? new Date(log.fecha_fin).toLocaleString('es-CO')
                          : <span className="text-slate-300">—</span>}
                      </td>
                      <td className="py-3 pr-4 text-slate-600 text-center">{log.registros_traidos}</td>
                      <td className="py-3 pr-4 text-emerald-600 text-center">{log.registros_insertados}</td>
                      <td className="py-3 pr-4 text-amber-600 text-center">{log.registros_duplicados}</td>
                      <td className="py-3">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                            STATUS_STYLES[log.estado] ?? 'bg-slate-100 text-slate-600'
                          }`}
                        >
                          {STATUS_ICONS[log.estado]}
                          {log.estado}
                        </span>
                        {log.mensaje_error && (
                          <p className="text-xs text-red-400 mt-0.5 max-w-[200px] truncate" title={log.mensaje_error}>
                            {log.mensaje_error}
                          </p>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminSyncLogs;
