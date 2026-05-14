import React from 'react';
import type { MetricasCalidadDTO } from '../../types/calidad';
import { Card } from '../ui/Card';
import { CheckCircle2, AlertTriangle, FileWarning, ShieldCheck } from 'lucide-react';

interface QualityScoreCardProps {
  metricas: MetricasCalidadDTO;
}

export const QualityScoreCard: React.FC<QualityScoreCardProps> = ({ metricas }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Total Processed */}
      <Card className="p-4 flex items-center gap-4 border-l-4 border-l-blue-500">
        <div className="p-3 bg-blue-50 rounded-lg">
          <ShieldCheck className="text-blue-600" size={24} />
        </div>
        <div>
          <p className="text-sm text-slate-500 font-medium">Total Procesados</p>
          <h3 className="text-2xl font-bold text-slate-900">{metricas.total_contratos.toLocaleString()}</h3>
          <p className="text-xs text-slate-400 mt-1">Confianza Promedio: {metricas.promedio_confianza.toFixed(1)}%</p>
        </div>
      </Card>

      {/* Completos */}
      <Card className="p-4 flex items-center gap-4 border-l-4 border-l-emerald-500">
        <div className="p-3 bg-emerald-50 rounded-lg">
          <CheckCircle2 className="text-emerald-600" size={24} />
        </div>
        <div>
          <p className="text-sm text-slate-500 font-medium">Registros Completos</p>
          <h3 className="text-2xl font-bold text-slate-900">{metricas.completos.toLocaleString()}</h3>
          <p className="text-xs text-emerald-600 font-medium mt-1">{metricas.porcentaje_completos.toFixed(1)}% del total</p>
        </div>
      </Card>

      {/* Incompletos */}
      <Card className="p-4 flex items-center gap-4 border-l-4 border-l-amber-500">
        <div className="p-3 bg-amber-50 rounded-lg">
          <AlertTriangle className="text-amber-600" size={24} />
        </div>
        <div>
          <p className="text-sm text-slate-500 font-medium">Registros Incompletos</p>
          <h3 className="text-2xl font-bold text-slate-900">{metricas.incompletos.toLocaleString()}</h3>
          <p className="text-xs text-amber-600 font-medium mt-1">{metricas.porcentaje_incompletos.toFixed(1)}% del total</p>
        </div>
      </Card>

      {/* Sospechosos */}
      <Card className="p-4 flex items-center gap-4 border-l-4 border-l-red-500">
        <div className="p-3 bg-red-50 rounded-lg">
          <FileWarning className="text-red-600" size={24} />
        </div>
        <div>
          <p className="text-sm text-slate-500 font-medium">Valores Sospechosos</p>
          <h3 className="text-2xl font-bold text-slate-900">{metricas.sospechosos.toLocaleString()}</h3>
          <p className="text-xs text-red-600 font-medium mt-1">{metricas.porcentaje_sospechosos.toFixed(1)}% del total</p>
        </div>
      </Card>
    </div>
  );
};
