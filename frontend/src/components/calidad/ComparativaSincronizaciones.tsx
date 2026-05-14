import React from 'react';
import type { FuenteDatosResponseDTO, SincronizacionHistorialResponseDTO } from '../../types/fuente';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { RefreshCw, Database, Copy } from 'lucide-react';

interface ComparativaSincronizacionesProps {
  fuentes: FuenteDatosResponseDTO[];
  sincronizaciones: SincronizacionHistorialResponseDTO[];
}

export const ComparativaSincronizaciones: React.FC<ComparativaSincronizacionesProps> = ({ fuentes, sincronizaciones }) => {
  // Aggregate stats per source based on their last sync or total syncs
  const statsPorFuente = fuentes.map(fuente => {
    const syncsFuente = sincronizaciones.filter(s => s.fuente_id === fuente.id);
    const ultimaSync = syncsFuente.sort((a, b) => new Date(b.fecha_inicio).getTime() - new Date(a.fecha_inicio).getTime())[0];
    
    return {
      fuente,
      ultimaSync,
      totalTraidos: syncsFuente.reduce((acc, curr) => acc + curr.registros_traidos, 0),
      totalInsertados: syncsFuente.reduce((acc, curr) => acc + curr.registros_insertados, 0),
      totalDuplicados: syncsFuente.reduce((acc, curr) => acc + curr.registros_duplicados, 0),
    };
  });

  return (
    <Card className="overflow-hidden">
      <div className="p-5 border-b border-slate-200 bg-white">
        <h3 className="font-semibold text-slate-800">Comparativa por Fuente de Datos</h3>
        <p className="text-sm text-slate-500 mt-1">
          Rendimiento y calidad de inserción basados en el historial de sincronizaciones.
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-slate-50 text-slate-600 font-medium">
            <tr>
              <th className="px-5 py-3">Fuente</th>
              <th className="px-5 py-3">Estado Última Sync</th>
              <th className="px-5 py-3 text-right">Traídos (Histórico)</th>
              <th className="px-5 py-3 text-right">Insertados (Nuevos)</th>
              <th className="px-5 py-3 text-right">Duplicados (Rechazados)</th>
              <th className="px-5 py-3">Tasa de Duplicidad</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {statsPorFuente.map((stat) => {
              const totalProcesados = stat.totalInsertados + stat.totalDuplicados;
              const tasaDuplicidad = totalProcesados > 0 
                ? (stat.totalDuplicados / totalProcesados) * 100 
                : 0;

              return (
                <tr key={stat.fuente.id} className="hover:bg-slate-50">
                  <td className="px-5 py-4">
                    <div className="font-medium text-slate-800">{stat.fuente.nombre}</div>
                    <div className="text-xs text-slate-500">{stat.fuente.endpoint}</div>
                  </td>
                  <td className="px-5 py-4">
                    {stat.ultimaSync ? (
                      <Badge variant={stat.ultimaSync.estado === 'EXITOSO' ? 'success' : stat.ultimaSync.estado === 'ERROR' ? 'error' : 'warning'}>
                        {stat.ultimaSync.estado}
                      </Badge>
                    ) : (
                      <span className="text-slate-400 italic text-xs">Sin sincronizaciones</span>
                    )}
                  </td>
                  <td className="px-5 py-4 text-right">
                    <div className="flex items-center justify-end gap-1 text-slate-700">
                      <RefreshCw size={14} className="text-slate-400" />
                      {stat.totalTraidos.toLocaleString()}
                    </div>
                  </td>
                  <td className="px-5 py-4 text-right">
                    <div className="flex items-center justify-end gap-1 text-emerald-600 font-medium">
                      <Database size={14} />
                      {stat.totalInsertados.toLocaleString()}
                    </div>
                  </td>
                  <td className="px-5 py-4 text-right">
                    <div className="flex items-center justify-end gap-1 text-amber-500 font-medium">
                      <Copy size={14} />
                      {stat.totalDuplicados.toLocaleString()}
                    </div>
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex items-center gap-2">
                      <span className={`w-10 text-right font-medium ${tasaDuplicidad > 50 ? 'text-red-600' : 'text-slate-600'}`}>
                        {tasaDuplicidad.toFixed(1)}%
                      </span>
                      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden w-24">
                        <div 
                          className={`h-full rounded-full ${tasaDuplicidad > 50 ? 'bg-red-500' : 'bg-amber-400'}`}
                          style={{ width: `${Math.min(tasaDuplicidad, 100)}%` }}
                        />
                      </div>
                    </div>
                  </td>
                </tr>
              );
            })}
            {statsPorFuente.length === 0 && (
              <tr>
                <td colSpan={6} className="px-5 py-8 text-center text-slate-500">
                  No hay fuentes registradas para comparar.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
};
