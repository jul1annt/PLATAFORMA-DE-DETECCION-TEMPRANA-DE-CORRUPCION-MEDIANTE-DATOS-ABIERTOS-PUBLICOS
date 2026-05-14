import React from 'react';
import type { CampoFaltanteDTO } from '../../types/calidad';
import { Card } from '../ui/Card';
import { AlertCircle } from 'lucide-react';

interface CamposFaltantesTableProps {
  campos: CampoFaltanteDTO[];
}

export const CamposFaltantesTable: React.FC<CamposFaltantesTableProps> = ({ campos }) => {
  if (!campos || campos.length === 0) {
    return (
      <Card className="p-8 flex flex-col items-center justify-center text-slate-500">
        <AlertCircle size={40} className="mb-4 text-emerald-500" />
        <h4 className="text-lg font-medium text-slate-700">Calidad Óptima</h4>
        <p className="text-sm mt-1">No se detectaron campos faltantes frecuentes en los registros.</p>
      </Card>
    );
  }

  // Sort by count descending just in case
  const sortedCampos = [...campos].sort((a, b) => b.cantidad - a.cantidad);

  return (
    <Card className="overflow-hidden">
      <div className="p-5 border-b border-slate-200 bg-white flex justify-between items-center">
        <div>
          <h3 className="font-semibold text-slate-800">Campos Faltantes Frecuentes</h3>
          <p className="text-sm text-slate-500 mt-1">Problemas detectados por columna a nivel global.</p>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-slate-50 text-slate-600 font-medium">
            <tr>
              <th className="px-5 py-3 w-1/3">Nombre del Campo</th>
              <th className="px-5 py-3 w-1/3 text-right">Registros Afectados</th>
              <th className="px-5 py-3 w-1/3">Impacto (Porcentaje)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {sortedCampos.map((campo, index) => (
              <tr key={index} className="hover:bg-slate-50">
                <td className="px-5 py-3 font-medium text-slate-700">{campo.campo}</td>
                <td className="px-5 py-3 text-right text-slate-600">{campo.cantidad.toLocaleString()}</td>
                <td className="px-5 py-3">
                  <div className="flex items-center gap-3">
                    <span className="w-12 text-right font-medium text-amber-600">
                      {campo.porcentaje.toFixed(2)}%
                    </span>
                    <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full ${campo.porcentaje > 50 ? 'bg-red-500' : campo.porcentaje > 20 ? 'bg-amber-500' : 'bg-blue-500'}`}
                        style={{ width: `${Math.min(campo.porcentaje, 100)}%` }}
                      />
                    </div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
};
