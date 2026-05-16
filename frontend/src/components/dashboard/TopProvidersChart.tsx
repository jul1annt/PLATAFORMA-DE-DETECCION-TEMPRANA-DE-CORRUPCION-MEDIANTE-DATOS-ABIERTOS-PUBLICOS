import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import type { TopProvider } from '../../types/procesado';

interface TopProvidersChartProps {
  data: TopProvider[];
}

const COLORS = [
  '#6366f1', '#8b5cf6', '#a78bfa', '#7c3aed', '#4f46e5',
  '#818cf8', '#c4b5fd', '#5b21b6', '#4338ca', '#3730a3',
];

const truncate = (str: string, n = 28) =>
  str.length > n ? str.slice(0, n) + '…' : str;

export const TopProvidersChart: React.FC<TopProvidersChartProps> = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-400 text-sm font-medium">
        Sin datos de proveedores
      </div>
    );
  }

  const chartData = data.map((d) => ({
    ...d,
    shortName: truncate(d.name),
  }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(280, data.length * 38)}>
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ top: 0, right: 24, left: 8, bottom: 0 }}
        barCategoryGap="30%"
      >
        <XAxis
          type="number"
          tick={{ fontSize: 10, fontWeight: 700, fill: '#94a3b8' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="shortName"
          width={170}
          tick={{ fontSize: 10, fontWeight: 700, fill: '#475569' }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          cursor={{ fill: 'rgba(99,102,241,0.05)' }}
          formatter={(value: number) => [
            value.toLocaleString('es-ES') + ' contratos',
            'Total',
          ]}
          labelFormatter={(label) => `Proveedor: ${label}`}
          contentStyle={{
            background: 'rgba(15,23,42,0.92)',
            border: 'none',
            borderRadius: 12,
            color: '#f8fafc',
            fontSize: 12,
            fontWeight: 700,
          }}
        />
        <Bar dataKey="contracts" radius={[0, 8, 8, 0]}>
          {chartData.map((_entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
};
