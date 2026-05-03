import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { Database, AlertCircle, AlertTriangle } from 'lucide-react';

export default function DashboardCards({ resumen }) {
  // resumen is an array, we take the most recent (first item) or sum them up
  const latest = resumen && resumen.length > 0 ? resumen[0] : { total_registros: 0, incompletos: 0, sospechosos: 0 };
  
  const total = latest.total_registros || 0;
  const incompletos = latest.incompletos || 0;
  const sospechosos = latest.sospechosos || 0;
  const ok = total - incompletos - sospechosos;

  const pctIncompletos = total ? ((incompletos / total) * 100).toFixed(1) : 0;
  const pctSospechosos = total ? ((sospechosos / total) * 100).toFixed(1) : 0;

  const data = [
    { name: 'OK', value: ok, color: '#10B981' }, // green-500
    { name: 'INCOMPLETO', value: incompletos, color: '#F59E0B' }, // amber-500
    { name: 'SOSPECHOSO', value: sospechosos, color: '#EF4444' }, // red-500
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      {/* Cards */}
      <div className="lg:col-span-3 grid grid-cols-1 sm:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-blue-50 flex items-center justify-center shrink-0">
            <Database className="w-6 h-6 text-blue-600" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Total Registros</p>
            <h3 className="text-2xl font-bold text-gray-900">{total.toLocaleString()}</h3>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-amber-50 flex items-center justify-center shrink-0">
            <AlertCircle className="w-6 h-6 text-amber-600" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">% Incompletos</p>
            <div className="flex items-baseline gap-2">
              <h3 className="text-2xl font-bold text-gray-900">{pctIncompletos}%</h3>
              <span className="text-sm font-medium text-amber-600">({incompletos})</span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center shrink-0">
            <AlertTriangle className="w-6 h-6 text-red-600" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">% Sospechosos</p>
            <div className="flex items-baseline gap-2">
              <h3 className="text-2xl font-bold text-gray-900">{pctSospechosos}%</h3>
              <span className="text-sm font-medium text-red-600">({sospechosos})</span>
            </div>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 flex flex-col items-center justify-center h-48">
        <h4 className="text-sm font-medium text-gray-500 w-full text-center mb-2">Distribución de Calidad</h4>
        {total === 0 ? (
          <p className="text-sm text-gray-400 my-auto">Sin datos</p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={30}
                outerRadius={50}
                paddingAngle={5}
                dataKey="value"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => value.toLocaleString()} />
              <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
