import React, { useState } from 'react';
import { Filter } from 'lucide-react';

export default function QualityTable({ problemas }) {
  const [filterTipo, setFilterTipo] = useState('');

  const filteredData = problemas.filter((item) => {
    return filterTipo ? item.tipo_problema === filterTipo : true;
  });

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h3 className="text-lg font-bold text-gray-900">Problemas de Calidad Detallados</h3>
        
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <select
            value={filterTipo}
            onChange={(e) => setFilterTipo(e.target.value)}
            className="pl-9 pr-8 py-2 border border-gray-300 rounded-lg text-sm appearance-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white"
          >
            <option value="">Todos los problemas</option>
            <option value="INCOMPLETO">INCOMPLETO</option>
            <option value="SOSPECHOSO">SOSPECHOSO</option>
          </select>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-gray-600">
          <thead className="bg-gray-50 border-b border-gray-200 text-gray-900">
            <tr>
              <th className="px-6 py-3 font-semibold">ID Contrato (Interno)</th>
              <th className="px-6 py-3 font-semibold">Tipo de Problema</th>
              <th className="px-6 py-3 font-semibold">Campo Afectado</th>
              <th className="px-6 py-3 font-semibold">Descripción</th>
              <th className="px-6 py-3 font-semibold">Fecha Detección</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filteredData.length === 0 ? (
              <tr>
                <td colSpan="5" className="px-6 py-8 text-center text-gray-500">
                  No hay problemas de calidad registrados. ¡Todo se ve bien!
                </td>
              </tr>
            ) : (
              filteredData.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 font-mono text-xs text-gray-500 truncate max-w-[150px]" title={item.contrato_id}>
                    {item.contrato_id}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      item.tipo_problema === 'INCOMPLETO' ? 'bg-amber-100 text-amber-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {item.tipo_problema}
                    </span>
                  </td>
                  <td className="px-6 py-4 font-medium text-gray-900">{item.campo || '-'}</td>
                  <td className="px-6 py-4 max-w-md">{item.descripcion}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {new Date(item.fecha).toLocaleString()}
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
