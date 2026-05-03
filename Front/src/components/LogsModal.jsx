import { useState } from 'react';
import { X, CheckCircle2, AlertCircle } from 'lucide-react';

export default function LogsModal({ isOpen, onClose, logs, fuenteNombre }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm transition-opacity">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col animate-in fade-in zoom-in-95 duration-200">
        
        <div className="flex items-center justify-between p-6 border-b border-gray-100">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Logs de Sincronización</h2>
            <p className="text-sm text-gray-500 mt-1">
              Historial de ejecuciones para <span className="font-semibold text-gray-700">{fuenteNombre}</span>
            </p>
          </div>
          <button 
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-auto p-6">
          {logs.length === 0 ? (
            <div className="text-center py-12 text-gray-500 flex flex-col items-center">
              <AlertCircle className="w-12 h-12 text-gray-300 mb-3" />
              <p>No hay logs registrados para esta fuente todavía.</p>
            </div>
          ) : (
            <div className="overflow-hidden border border-gray-200 rounded-lg shadow-sm">
              <table className="w-full text-sm text-left">
                <thead className="bg-gray-50 text-gray-600 font-medium border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-4">Fecha</th>
                    <th className="px-6 py-4">Estado</th>
                    <th className="px-6 py-4">Registros Nuevos</th>
                    <th className="px-6 py-4">Mensaje</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {logs.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap text-gray-700 font-medium">
                        {new Date(log.fecha).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {log.estado === 'success' ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Éxito
                          </span>
                        ) : log.estado === 'failed' ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
                            <AlertCircle className="w-3.5 h-3.5" /> Falló
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                            <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></span> En progreso
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap font-semibold text-gray-700">
                        {log.cantidad_registros}
                      </td>
                      <td className="px-6 py-4 text-gray-600 max-w-xs truncate" title={log.mensaje}>
                        {log.mensaje || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-end rounded-b-xl">
          <button 
            onClick={onClose}
            className="px-5 py-2.5 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition-colors shadow-sm"
          >
            Cerrar
          </button>
        </div>

      </div>
    </div>
  );
}
