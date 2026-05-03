import React from 'react';
import { History } from 'lucide-react';

export default function ChangesTable({ cambios }) {
  // Destacar cambios de las últimas 24 horas
  const isRecent = (dateStr) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffHours = (now - date) / (1000 * 60 * 60);
    return diffHours <= 24;
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-200 flex items-center gap-2">
        <History className="w-5 h-5 text-brand-600" />
        <h3 className="text-lg font-bold text-gray-900">Historial de Cambios Detectados</h3>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-gray-600">
          <thead className="bg-gray-50 border-b border-gray-200 text-gray-900">
            <tr>
              <th className="px-6 py-3 font-semibold">ID Proceso</th>
              <th className="px-6 py-3 font-semibold">Campo Modificado</th>
              <th className="px-6 py-3 font-semibold">Valor Anterior</th>
              <th className="px-6 py-3 font-semibold">Valor Nuevo</th>
              <th className="px-6 py-3 font-semibold">Fecha Detección</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {cambios.length === 0 ? (
              <tr>
                <td colSpan="5" className="px-6 py-8 text-center text-gray-500">
                  No se han detectado mutaciones o cambios en los contratos existentes.
                </td>
              </tr>
            ) : (
              cambios.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 font-medium text-gray-900">{item.id_proceso}</td>
                  <td className="px-6 py-4 font-mono text-xs text-brand-600 bg-brand-50 rounded px-2 py-1 inline-block mt-2">
                    {item.campo}
                  </td>
                  <td className="px-6 py-4 text-gray-400 line-through truncate max-w-[200px]" title={item.valor_anterior}>
                    {item.valor_anterior || '(vacío)'}
                  </td>
                  <td className="px-6 py-4 text-green-700 font-medium truncate max-w-[200px]" title={item.valor_nuevo}>
                    {item.valor_nuevo || '(vacío)'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <span>{new Date(item.fecha).toLocaleString()}</span>
                      {isRecent(item.fecha) && (
                        <span className="flex h-2 w-2 relative">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-brand-500"></span>
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
