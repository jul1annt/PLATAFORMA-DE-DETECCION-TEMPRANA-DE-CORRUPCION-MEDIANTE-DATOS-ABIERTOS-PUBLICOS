import React from 'react';
import type { ComparativaFuenteDTO } from '../../services/fuentesService';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { RefreshCw, Database, Copy } from 'lucide-react';

interface ComparativaSincronizacionesProps {
  comparativa: ComparativaFuenteDTO[];
}

export const ComparativaSincronizaciones: React.FC<ComparativaSincronizacionesProps> = ({ comparativa }) => {
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
            {comparativa.map((stat) => (
                <tr key={stat.fuente_id} className="hover:bg-slate-50">
                  <td className="px-5 py-4">
                    <div className="font-medium text-slate-800">{stat.nombre}</div>
                    <div className="text-xs text-slate-500">{stat.endpoint}</div>
                  </td>
                  <td className="px-5 py-4">
                    {stat.ultima_sync_estado ? (
                      <Badge variant={stat.ultima_sync_estado === 'EXITOSO' ? 'success' : stat.ultima_sync_estado === 'ERROR' ? 'error' : 'warning'}>
                        {stat.ultima_sync_estado}
                      </Badge>
                    ) : (
                      <span className="text-slate-400 italic text-xs">Sin sincronizaciones</span>
                    )}
                  </td>
                  <td className="px-5 py-4 text-right">
                    <div className="flex items-center justify-end gap-1 text-slate-700">
                      <RefreshCw size={14} className="text-slate-400" />
                      {stat.total_traidos.toLocaleString()}
                    </div>
                  </td>
                  <td className="px-5 py-4 text-right">
                    <div className="flex items-center justify-end gap-1 text-emerald-600 font-medium">
                      <Database size={14} />
                      {stat.total_insertados.toLocaleString()}
                    </div>
                  </td>
                  <td className="px-5 py-4 text-right">
                    <div className="flex items-center justify-end gap-1 text-amber-500 font-medium">
                      <Copy size={14} />
                      {stat.total_duplicados.toLocaleString()}
                    </div>
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex items-center gap-2">
                      <span className="w-10 text-right font-medium text-slate-600">
                        {stat.tasa_duplicidad.toFixed(1)}%
                      </span>
                      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden w-24">
                        <div 
                          className="h-full rounded-full bg-amber-400"
                          style={{ width: `${Math.min(stat.tasa_duplicidad, 100)}%` }}
                        />
                      </div>
                    </div>
                  </td>
                </tr>
            ))}
            {comparativa.length === 0 && (
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
