import React, { useEffect, useState } from 'react';
import { Modal } from '../ui/Modal';
import { Badge } from '../ui/Badge';
import { Skeleton } from '../ui/Skeleton';
import { fuentesService } from '../../services/fuentesService';
import type { SincronizacionHistorialResponseDTO, EstadoSync } from '../../types/fuente';
import { AlertCircle, CheckCircle2, Clock, Info, ChevronLeft, ChevronRight } from 'lucide-react';
import toast from 'react-hot-toast';

interface HistorialSyncModalProps {
  isOpen: boolean;
  onClose: () => void;
  fuenteId: number | null;
  fuenteNombre: string;
}

export const HistorialSyncModal: React.FC<HistorialSyncModalProps> = ({ isOpen, onClose, fuenteId, fuenteNombre }) => {
  const PAGE_SIZE = 20;
  const [logs, setLogs] = useState<SincronizacionHistorialResponseDTO[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isOpen || !fuenteId) return;
    let cancelled = false;
    const timer = window.setTimeout(() => {
      setLoading(true);
      void fuentesService.getPaginaHistorialByFuenteId(fuenteId, page, PAGE_SIZE)
        .then((data) => {
          if (!cancelled) {
            setLogs(data.items);
            setTotal(data.total);
            const lastPage = Math.max(1, Math.ceil(data.total / PAGE_SIZE));
            if (page > lastPage) setPage(lastPage);
          }
        })
        .catch(() => {
          if (!cancelled) toast.error('Error al cargar el historial de sincronizaciones');
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, 0);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [isOpen, fuenteId, page]);

  const getStatusConfig = (estado: EstadoSync) => {
    switch (estado) {
      case 'EXITOSO':
        return { variant: 'success' as const, icon: <CheckCircle2 size={14} className="mr-1" />, label: 'Exitoso' };
      case 'ERROR':
        return { variant: 'error' as const, icon: <AlertCircle size={14} className="mr-1" />, label: 'Error' };
      case 'EN_PROCESO':
        return { variant: 'warning' as const, icon: <Clock size={14} className="mr-1" />, label: 'En Proceso' };
      default:
        return { variant: 'info' as const, icon: <Info size={14} className="mr-1" />, label: estado };
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Historial de Sincronización: ${fuenteNombre}`}
      className="max-w-4xl"
    >
      <div className="overflow-x-auto max-h-[60vh]">
        <table className="w-full text-sm text-left">
          <thead className="bg-slate-50 text-slate-600 font-medium border-b border-slate-200 sticky top-0 z-10">
            <tr>
              <th className="px-4 py-3">Fecha Inicio</th>
              <th className="px-4 py-3">Duración</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3 text-right">Traídos</th>
              <th className="px-4 py-3 text-right">Insertados</th>
              <th className="px-4 py-3 text-right">Duplicados</th>
              <th className="px-4 py-3 w-1/3">Detalle</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i}>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-24" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-16" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-6 w-20 rounded-full" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-8 ml-auto" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-8 ml-auto" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-8 ml-auto" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-full" /></td>
                </tr>
              ))
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                  No hay registros de sincronización para esta fuente.
                </td>
              </tr>
            ) : (
              logs.map((log) => {
                const config = getStatusConfig(log.estado);
                const inicio = new Date(log.fecha_inicio);
                const fin = log.fecha_fin ? new Date(log.fecha_fin) : null;
                const duracionSegundos = fin ? Math.round((fin.getTime() - inicio.getTime()) / 1000) : null;

                return (
                  <tr key={log.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 text-slate-900">
                      {inicio.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {duracionSegundos !== null ? `${duracionSegundos}s` : '-'}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={config.variant} className="flex items-center w-max px-2 py-0.5">
                        {config.icon}
                        {config.label}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right font-medium text-slate-700">{log.registros_traidos}</td>
                    <td className="px-4 py-3 text-right font-medium text-emerald-600">{log.registros_insertados}</td>
                    <td className="px-4 py-3 text-right font-medium text-orange-500">{log.registros_duplicados}</td>
                    <td className="px-4 py-3 text-slate-600 text-xs truncate max-w-[200px]" title={log.mensaje_error || ''}>
                      {log.mensaje_error ? (
                        <div className="flex items-start gap-1 text-red-600">
                          <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
                          <span className="line-clamp-2">{log.mensaje_error}</span>
                        </div>
                      ) : (
                        <span className="text-slate-400 italic">Sin observaciones</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
      {total > 0 && (
        <div className="flex items-center justify-between gap-3 border-t border-slate-100 pt-3 mt-3">
          <span className="text-xs text-slate-500">
            Página {page} de {Math.max(1, Math.ceil(total / PAGE_SIZE))} · {total.toLocaleString('es-CO')} sincronizaciones
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              disabled={loading || page <= 1}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-600 disabled:opacity-40"
            >
              <ChevronLeft size={14} /> Anterior
            </button>
            <button
              onClick={() => setPage((current) => current + 1)}
              disabled={loading || page >= Math.ceil(total / PAGE_SIZE)}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-600 disabled:opacity-40"
            >
              Siguiente <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
};
