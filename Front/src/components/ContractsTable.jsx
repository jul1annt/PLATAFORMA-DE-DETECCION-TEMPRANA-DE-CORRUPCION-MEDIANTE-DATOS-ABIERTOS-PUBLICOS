import React, { useState } from 'react';
import { Search, Filter } from 'lucide-react';

export default function ContractsTable({ contratos }) {
  const [filterEstado, setFilterEstado] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const filteredData = contratos.filter((item) => {
    const matchesEstado = filterEstado ? item.estado_calidad === filterEstado : true;
    const searchString = searchTerm.toLowerCase();
    const matchesSearch = 
      (item.id_proceso || '').toLowerCase().includes(searchString) ||
      (item.entidad || '').toLowerCase().includes(searchString) ||
      (item.proveedor || '').toLowerCase().includes(searchString);
    return matchesEstado && matchesSearch;
  });

  const getStatusStyle = (estado) => {
    switch (estado) {
      case 'OK':
        return 'bg-green-100 text-green-800';
      case 'INCOMPLETO':
        return 'bg-amber-100 text-amber-800';
      case 'SOSPECHOSO':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h3 className="text-lg font-bold text-gray-900">Contratos Procesados</h3>
        
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar entidad, prov..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 w-full sm:w-64"
            />
          </div>
          
          {/* Filter */}
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <select
              value={filterEstado}
              onChange={(e) => setFilterEstado(e.target.value)}
              className="pl-9 pr-8 py-2 border border-gray-300 rounded-lg text-sm appearance-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white"
            >
              <option value="">Todos los estados</option>
              <option value="OK">OK</option>
              <option value="INCOMPLETO">INCOMPLETO</option>
              <option value="SOSPECHOSO">SOSPECHOSO</option>
            </select>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-gray-600">
          <thead className="bg-gray-50 border-b border-gray-200 text-gray-900">
            <tr>
              <th className="px-6 py-3 font-semibold">ID Proceso</th>
              <th className="px-6 py-3 font-semibold">Entidad</th>
              <th className="px-6 py-3 font-semibold">Proveedor</th>
              <th className="px-6 py-3 font-semibold">Valor</th>
              <th className="px-6 py-3 font-semibold">Fecha</th>
              <th className="px-6 py-3 font-semibold">Estado Calidad</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filteredData.length === 0 ? (
              <tr>
                <td colSpan="6" className="px-6 py-8 text-center text-gray-500">
                  No se encontraron contratos que coincidan con la búsqueda.
                </td>
              </tr>
            ) : (
              filteredData.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 font-medium text-gray-900">{item.id_proceso}</td>
                  <td className="px-6 py-4 max-w-xs truncate" title={item.entidad}>{item.entidad || '-'}</td>
                  <td className="px-6 py-4 max-w-xs truncate" title={item.proveedor}>{item.proveedor || '-'}</td>
                  <td className="px-6 py-4">
                    {item.valor ? `$${Number(item.valor).toLocaleString()}` : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">{item.fecha || '-'}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusStyle(item.estado_calidad)}`}>
                      {item.estado_calidad}
                    </span>
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
