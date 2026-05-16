import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Database, RefreshCw, Edit, CheckCircle, XCircle, Loader2, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { fuentesService } from '../../services/fuentesService';
import type { FuenteDatosResponseDTO } from '../../types/fuente';

const AdminFuentes: React.FC = () => {
  const [fuentes, setFuentes] = useState<FuenteDatosResponseDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncingIds, setSyncingIds] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const fetchFuentes = async () => {
    try {
      setError(null);
      const data = await fuentesService.getAll();
      setFuentes(data);
    } catch {
      setError('No se pudieron cargar las fuentes de datos.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchFuentes(); }, []);

  const handleSync = async (fuente: FuenteDatosResponseDTO) => {
    setSyncingIds((prev) => new Set(prev).add(fuente.id));
    try {
      await fuentesService.sync(fuente.id);
      toast.success(`Sincronización iniciada para "${fuente.nombre}"`);
      setTimeout(fetchFuentes, 1500);
    } catch {
      toast.error(`Error al sincronizar "${fuente.nombre}"`);
    } finally {
      setSyncingIds((prev) => {
        const next = new Set(prev);
        next.delete(fuente.id);
        return next;
      });
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center">
            <Database size={20} className="text-blue-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Fuentes de Datos</h1>
            <p className="text-slate-500 text-sm">Gestión y sincronización de fuentes configuradas</p>
          </div>
        </div>
        <Link
          to="/fuentes/nueva"
          id="admin-nueva-fuente-btn"
          className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-white text-sm font-semibold rounded-lg transition-colors"
        >
          <Database size={15} />
          Nueva fuente
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base text-slate-700">
            {loading ? 'Cargando...' : `${fuentes.length} fuente${fuentes.length !== 1 ? 's' : ''} registrada${fuentes.length !== 1 ? 's' : ''}`}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-14 bg-slate-100 animate-pulse rounded-lg" />
              ))}
            </div>
          ) : error ? (
            <div className="flex flex-col items-center gap-2 py-10 text-red-500">
              <AlertCircle size={32} />
              <p className="text-sm">{error}</p>
              <button onClick={fetchFuentes} className="text-xs underline hover:no-underline">Reintentar</button>
            </div>
          ) : fuentes.length === 0 ? (
            <p className="text-center text-slate-400 py-10 text-sm">No hay fuentes configuradas.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-500 border-b border-slate-100">
                    <th className="pb-3 pr-4 font-medium">Nombre</th>
                    <th className="pb-3 pr-4 font-medium">Tipo / Formato</th>
                    <th className="pb-3 pr-4 font-medium">Estado</th>
                    <th className="pb-3 pr-4 font-medium">Última sync</th>
                    <th className="pb-3 pr-4 font-medium">Frecuencia</th>
                    <th className="pb-3 font-medium">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {fuentes.map((f) => {
                    const isSyncing = syncingIds.has(f.id);
                    return (
                      <tr key={f.id} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3 pr-4">
                          <span className="font-semibold text-slate-800">{f.nombre}</span>
                          <div className="text-xs text-slate-400 truncate max-w-[180px]">{f.endpoint}</div>
                        </td>
                        <td className="py-3 pr-4">
                          <span className="text-slate-700">{f.tipo}</span>
                          <span className="ml-1.5 inline-flex px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded text-xs font-mono">{f.formato}</span>
                        </td>
                        <td className="py-3 pr-4">
                          {f.activo ? (
                            <span className="inline-flex items-center gap-1 text-emerald-600 text-xs font-medium">
                              <CheckCircle size={12} /> Activa
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-red-500 text-xs font-medium">
                              <XCircle size={12} /> Inactiva
                            </span>
                          )}
                        </td>
                        <td className="py-3 pr-4 text-slate-500 text-xs">
                          {f.ultima_sync ? new Date(f.ultima_sync).toLocaleString('es-CO') : <span className="text-slate-300">Nunca</span>}
                        </td>
                        <td className="py-3 pr-4 text-slate-500 text-xs">c/ {f.frecuencia_dias}d</td>
                        <td className="py-3">
                          <div className="flex items-center gap-2">
                            <Link
                              to={`/fuentes/editar/${f.id}`}
                              id={`edit-fuente-${f.id}`}
                              className="p-1.5 text-slate-400 hover:text-blue-500 hover:bg-blue-50 rounded-md transition-colors"
                              title="Editar fuente"
                            >
                              <Edit size={14} />
                            </Link>
                            <button
                              id={`sync-fuente-${f.id}`}
                              onClick={() => handleSync(f)}
                              disabled={isSyncing || !f.activo}
                              title={f.activo ? 'Sincronizar ahora' : 'Fuente inactiva'}
                              className="p-1.5 text-slate-400 hover:text-emerald-500 hover:bg-emerald-50 rounded-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                              {isSyncing ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminFuentes;
