import React from 'react';
import type { QualitySummaryProps } from '../types/procesado';

export const QualitySummaryBanner: React.FC<QualitySummaryProps> = ({
  metricas,
  camposFaltantes,
  hayCambiosRecientes,
  onFilterChange,
  activeFilter,
}) => {
  if (!metricas) return null;

  return (
    <div className="mb-10 flex flex-col gap-6">
      {/* Banner de Alerta - Estilo Screenshot */}
      {hayCambiosRecientes && (
        <div className="bg-red-50 border border-red-200 rounded-3xl p-5 flex items-center justify-between shadow-sm relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-red-500"></div>
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-red-500 rounded-full flex items-center justify-center text-white shadow-lg">
              <span className="text-2xl italic font-black">⚡</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-red-600">⚡</span>
                <h4 className="text-red-700 font-bold">ALERTA: Se detectaron cambios recientes en los datos sincronizados</h4>
              </div>
              <p className="text-red-600/80 text-sm">Hay registros que han sido modificados desde la última sincronización.</p>
            </div>
          </div>
          <button 
            onClick={() => onFilterChange('MODIFICADOS')}
            className="px-6 py-2 border border-red-300 rounded-xl text-red-700 font-semibold text-sm hover:bg-red-100 transition-colors flex items-center gap-2 bg-white/50"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4.5h14.25M3 9h9.75M3 13.5h9.75m4.5-4.5v12m0 0l-3.75-3.75M17.25 21L21 17.25" />
            </svg>
            Ver registros modificados
          </button>
        </div>
      )}

      {/* Grid de Cards - Estilo Screenshot */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Total Registros */}
        <div 
          onClick={() => onFilterChange('ALL')}
          className={`relative overflow-hidden bg-[#edf2ff] border border-slate-100 rounded-3xl p-6 shadow-sm cursor-pointer transition-all ${activeFilter === 'ALL' ? 'ring-2 ring-indigo-500' : ''}`}
        >
          <div className="relative z-10 flex items-start gap-4">
            <div className="w-12 h-12 bg-white rounded-2xl flex items-center justify-center text-indigo-500 shadow-sm border border-slate-100">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <p className="text-[10px] font-bold text-indigo-600 uppercase tracking-widest mb-1">Total Registros</p>
              <p className="text-4xl font-black text-slate-800 tracking-tighter">{metricas.total_contratos.toLocaleString('es-ES')}</p>
              <p className="text-[10px] font-medium text-slate-500 mt-2 uppercase">Volumen procesado actual</p>
            </div>
          </div>
          {/* Wave Decoration */}
          <div className="absolute bottom-0 left-0 right-0 h-12 opacity-30">
            <svg viewBox="0 0 500 150" preserveAspectRatio="none" className="h-full w-full">
              <path d="M0.00,49.98 C149.99,150.00 349.89,-49.98 500.00,49.98 L500.00,150.00 L0.00,150.00 Z" fill="#6366f1"></path>
            </svg>
          </div>
        </div>

        {/* Incompletos */}
        <div 
          onClick={() => onFilterChange('INCOMPLETOS')}
          className={`relative overflow-hidden bg-[#fff9db] border border-slate-100 rounded-3xl p-6 shadow-sm cursor-pointer transition-all ${activeFilter === 'INCOMPLETOS' ? 'ring-2 ring-amber-500' : ''}`}
        >
          <div className="relative z-10">
            <div className="flex justify-between items-start mb-1">
              <p className="text-[10px] font-bold text-amber-700 uppercase tracking-widest">Incompletos ⚠️</p>
              <span className="bg-[#ffec99] text-amber-900 text-[10px] font-black px-2 py-1 rounded-lg">
                {metricas.porcentaje_incompletos.toFixed(2)}%
              </span>
            </div>
            <p className="text-4xl font-black text-slate-800 tracking-tighter">{metricas.incompletos.toLocaleString('es-ES')}</p>
            <p className="text-[10px] font-medium text-slate-500 mt-2 uppercase">Registros con campos faltantes</p>
          </div>
          {/* Wave Decoration */}
          <div className="absolute bottom-0 left-0 right-0 h-12 opacity-30">
            <svg viewBox="0 0 500 150" preserveAspectRatio="none" className="h-full w-full">
              <path d="M0.00,49.98 C149.99,150.00 349.89,-49.98 500.00,49.98 L500.00,150.00 L0.00,150.00 Z" fill="#f59e0b"></path>
            </svg>
          </div>
        </div>

        {/* Sospechosos */}
        <div 
          onClick={() => onFilterChange('SOSPECHOSOS')}
          className={`relative overflow-hidden bg-[#fff0f0] border border-slate-100 rounded-3xl p-6 shadow-sm cursor-pointer transition-all ${activeFilter === 'SOSPECHOSOS' ? 'ring-2 ring-red-500' : ''}`}
        >
          <div className="relative z-10">
            <div className="flex justify-between items-start mb-1">
              <p className="text-[10px] font-bold text-red-700 uppercase tracking-widest">Sospechosos 🚨</p>
              <span className="bg-[#ffc9c9] text-red-900 text-[10px] font-black px-2 py-1 rounded-lg">
                {metricas.porcentaje_sospechosos.toFixed(2)}%
              </span>
            </div>
            <p className="text-4xl font-black text-slate-800 tracking-tighter">{metricas.sospechosos.toLocaleString('es-ES')}</p>
            <p className="text-[10px] font-medium text-slate-500 mt-2 uppercase">Anomalías detectadas</p>
          </div>
          {/* Wave Decoration */}
          <div className="absolute bottom-0 left-0 right-0 h-12 opacity-30">
            <svg viewBox="0 0 500 150" preserveAspectRatio="none" className="h-full w-full">
              <path d="M0.00,49.98 C149.99,150.00 349.89,-49.98 500.00,49.98 L500.00,150.00 L0.00,150.00 Z" fill="#ef4444"></path>
            </svg>
          </div>
        </div>

        {/* Top Campos Faltantes */}
        <div className="bg-[#ebfbee] border border-slate-100 rounded-3xl p-6 shadow-sm flex flex-col">
          <p className="text-[10px] font-bold text-teal-700 uppercase tracking-widest mb-4">Top Campos Faltantes</p>
          <div className="flex flex-col gap-3 flex-1 justify-center">
            {camposFaltantes.slice(0, 3).map((cf, idx) => (
              <div key={idx} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 overflow-hidden">
                  <span className={`w-5 h-5 flex items-center justify-center rounded-full text-[10px] font-bold text-white ${idx === 0 ? 'bg-teal-500' : idx === 1 ? 'bg-teal-400' : 'bg-teal-300'}`}>
                    {idx + 1}
                  </span>
                  <span className="font-bold text-slate-700 truncate capitalize">{cf.campo.replace(/_/g, ' ')}</span>
                </div>
                <span className="font-bold text-slate-800 flex-shrink-0">
                  {cf.cantidad} <span className="text-slate-400 font-normal ml-1">({cf.porcentaje.toFixed(2)}%)</span>
                </span>
              </div>
            ))}
          </div>
          <button className="mt-4 text-[10px] font-bold text-teal-600 uppercase flex items-center gap-1 hover:gap-2 transition-all">
            Ver todos los campos →
          </button>
        </div>
      </div>
    </div>
  );
};
