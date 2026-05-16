import React from 'react';
import {
  RadialBarChart,
  RadialBar,
  Legend,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { AnomalyDistribution } from '../../types/procesado';

interface AnomalyChartProps {
  data: AnomalyDistribution[];
  total: number;
}

export const AnomalyChart: React.FC<AnomalyChartProps> = ({ data, total }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-400 text-sm font-medium">
        Sin anomalías detectadas
      </div>
    );
  }

  const chartData = data.map((d) => ({
    name: d.name,
    value: d.value,
    pct: total > 0 ? Math.round((d.value / total) * 100) : 0,
    fill: d.color,
  }));

  return (
    <div className="w-full">
      {/* Visual bars */}
      <div className="flex flex-col gap-3 mb-4">
        {chartData.map((d) => (
          <div key={d.name}>
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs font-bold text-slate-600">{d.name}</span>
              <div className="flex items-center gap-2">
                <span className="text-xs font-black text-slate-800">
                  {d.value.toLocaleString('es-ES')}
                </span>
                <span
                  className="text-[10px] font-bold px-2 py-0.5 rounded-full text-white"
                  style={{ background: d.fill }}
                >
                  {d.pct}%
                </span>
              </div>
            </div>
            <div className="h-2.5 w-full bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{
                  width: `${Math.max(d.pct, 1)}%`,
                  background: d.fill,
                }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Radial chart */}
      <ResponsiveContainer width="100%" height={200}>
        <RadialBarChart
          cx="50%"
          cy="50%"
          innerRadius={20}
          outerRadius={80}
          barSize={12}
          data={chartData}
        >
          <RadialBar
            background={{ fill: '#f1f5f9' }}
            dataKey="pct"
            cornerRadius={6}
          />
          <Tooltip
            formatter={(value: number, name: string) => [`${value}%`, name]}
            contentStyle={{
              background: 'rgba(15,23,42,0.92)',
              border: 'none',
              borderRadius: 12,
              color: '#f8fafc',
              fontSize: 12,
              fontWeight: 700,
            }}
          />
          <Legend
            iconSize={10}
            iconType="circle"
            formatter={(value) => (
              <span style={{ fontSize: 11, fontWeight: 700, color: '#475569' }}>
                {value}
              </span>
            )}
          />
        </RadialBarChart>
      </ResponsiveContainer>
    </div>
  );
};
