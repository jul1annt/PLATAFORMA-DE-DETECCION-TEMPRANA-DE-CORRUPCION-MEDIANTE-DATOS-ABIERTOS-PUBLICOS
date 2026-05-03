import { Play, FileText, Edit2, Power, PowerOff } from 'lucide-react';

export default function FuenteTable({ fuentes, onEdit, onToggleStatus, onSync, onViewLogs }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-gray-50 text-gray-600 font-semibold border-b border-gray-200">
            <tr>
              <th className="px-6 py-4">Nombre / Endpoint</th>
              <th className="px-6 py-4">Tipo</th>
              <th className="px-6 py-4">Frec.</th>
              <th className="px-6 py-4">Estado</th>
              <th className="px-6 py-4">Última Sincronización</th>
              <th className="px-6 py-4 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {fuentes.length === 0 ? (
              <tr>
                <td colSpan="6" className="px-6 py-12 text-center text-gray-500">
                  No hay fuentes de datos registradas. Crea una para comenzar.
                </td>
              </tr>
            ) : (
              fuentes.map((fuente) => (
                <tr key={fuente.id} className="hover:bg-gray-50/80 transition-colors group">
                  <td className="px-6 py-4">
                    <div className="font-semibold text-gray-900">{fuente.nombre}</div>
                    <div className="text-xs text-gray-500 mt-0.5 truncate max-w-[200px]" title={fuente.endpoint}>
                      {fuente.endpoint}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-700 border border-gray-200">
                      {fuente.tipo}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-600">
                    {fuente.frecuencia_dias} {fuente.frecuencia_dias === 1 ? 'día' : 'días'}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <span className={`relative flex h-2.5 w-2.5`}>
                        {fuente.estado === 'activa' && (
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                        )}
                        <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${fuente.estado === 'activa' ? 'bg-green-500' : 'bg-red-500'}`}></span>
                      </span>
                      <span className={`font-medium ${fuente.estado === 'activa' ? 'text-green-700' : 'text-red-700'}`}>
                        {fuente.estado === 'activa' ? 'Activa' : 'Inactiva'}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-gray-600">
                    {fuente.ultima_sincronizacion 
                      ? new Date(fuente.ultima_sincronizacion).toLocaleString() 
                      : <span className="text-gray-400 italic">Nunca</span>}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
                      
                      <button 
                        onClick={() => onSync(fuente)}
                        title="Sincronizar ahora"
                        className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
                      >
                        <Play className="w-4 h-4" />
                      </button>

                      <button 
                        onClick={() => onViewLogs(fuente)}
                        title="Ver Logs"
                        className="p-1.5 text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
                      >
                        <FileText className="w-4 h-4" />
                      </button>
                      
                      <div className="w-px h-4 bg-gray-300 mx-1"></div>
                      
                      <button 
                        onClick={() => onEdit(fuente)}
                        title="Editar"
                        className="p-1.5 text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>

                      <button 
                        onClick={() => onToggleStatus(fuente)}
                        title={fuente.estado === 'activa' ? 'Desactivar' : 'Activar'}
                        className={`p-1.5 rounded-md transition-colors ${
                          fuente.estado === 'activa' 
                          ? 'text-red-600 hover:bg-red-50' 
                          : 'text-green-600 hover:bg-green-50'
                        }`}
                      >
                        {fuente.estado === 'activa' ? <PowerOff className="w-4 h-4" /> : <Power className="w-4 h-4" />}
                      </button>
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
