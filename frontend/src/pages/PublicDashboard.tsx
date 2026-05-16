import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getDashboardMetrics,
  getTopProviders,
  getRiskDistribution,
  getAnomalyDistribution,
} from '../services/procesadosService';
import type {
  DashboardMetrics,
  RiskDistribution,
  TopProvider,
  AnomalyDistribution,
} from '../types/procesado';
import { KpiCard } from '../components/dashboard/KpiCard';
import { RiskChart } from '../components/dashboard/RiskChart';
import { TopProvidersChart } from '../components/dashboard/TopProvidersChart';
import { AnomalyChart } from '../components/dashboard/AnomalyChart';
import { PublicNavbar } from '../components/layout/PublicNavbar';

const POLL_INTERVAL_MS = 60_000;

const ShieldIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
  </svg>
);

const ContractIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const WarningIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
  </svg>
);

const AlertIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
  </svg>
);

const ChartSection: React.FC<{ title: string; subtitle?: string; children: React.ReactNode }> = ({
  title, subtitle, children,
}) => (
  <div className="bg-white/80 backdrop-blur-md rounded-[32px] p-8 shadow-xl shadow-indigo-100/30 border border-white/60 flex flex-col">
    <div className="mb-6">
      <h3 className="text-base font-black text-indigo-950 uppercase tracking-widest">{title}</h3>
      {subtitle && <p className="text-xs text-slate-400 font-medium mt-1">{subtitle}</p>}
    </div>
    {children}
  </div>
);

export const PublicDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [riskData, setRiskData] = useState<RiskDistribution[]>([]);
  const [topProviders, setTopProviders] = useState<TopProvider[]>([]);
  const [anomalyData, setAnomalyData] = useState<AnomalyDistribution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadData = useCallback(async () => {
    try {
      setError(null);
      const [m, risk, providers, anomaly] = await Promise.all([
        getDashboardMetrics(),
        getRiskDistribution(),
        getTopProviders(10),
        getAnomalyDistribution(),
      ]);
      setMetrics(m);
      setRiskData(risk);
      setTopProviders(providers);
      setAnomalyData(anomaly);
      setLastUpdated(new Date());
    } catch (err: any) {
      setError(err.message || 'Error al cargar el dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [loadData]);

  return (
    <div className="min-h-screen font-sans text-slate-900 relative overflow-hidden bg-gradient-to-br from-slate-50 via-indigo-50/30 to-violet-50/20">
      {/* Mesh Gradient Blobs */}
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-15%] left-[-10%] w-[55%] h-[55%] rounded-full bg-indigo-200/40 blur-[130px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[45%] h-[45%] rounded-full bg-violet-300/30 blur-[130px]" />
        <div className="absolute top-[30%] right-[5%] w-[35%] h-[35%] rounded-full bg-blue-200/30 blur-[110px]" />
      </div>

      {/* ── Shared Navbar ─────────────────────────────────────────────────── */}
      <PublicNavbar />

      {/* ── Main ─────────────────────────────────────────────────────────── */}
      <main className="max-w-[1400px] mx-auto px-8 py-14 relative z-10">

        {/* ── Hero ─────────────────────────────────────────────────────────── */}
        <div className="mb-16 text-center max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 bg-indigo-50 border border-indigo-100 px-4 py-2 rounded-full text-indigo-600 text-[10px] font-black uppercase tracking-widest mb-6 shadow-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Sistema Activo · Datos en Tiempo Real
          </div>
          <h1 className="text-6xl font-black text-indigo-950 tracking-tighter mb-5 leading-[1.05]">
            Dashboard de{' '}
            <span className="bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">
              Transparencia
            </span>
          </h1>
          <p className="text-lg text-slate-500 font-medium leading-relaxed max-w-2xl mx-auto">
            Monitoreo en tiempo real del sistema de contratación pública. Detectamos anomalías,
            evaluamos riesgos y garantizamos la integridad de los datos.
          </p>
          {lastUpdated && (
            <p className="mt-4 text-[11px] font-bold text-slate-400 uppercase tracking-widest">
              Última actualización: {lastUpdated.toLocaleTimeString('es-ES')} · Actualiza cada 60s
            </p>
          )}
        </div>

        {/* ── Loading / Error ───────────────────────────────────────────────── */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-32">
            <div className="relative">
              <div className="w-20 h-20 border-4 border-indigo-100 rounded-full" />
              <div className="absolute inset-0 w-20 h-20 border-4 border-indigo-600 rounded-full border-t-transparent animate-spin" />
            </div>
            <p className="mt-6 text-slate-400 font-bold uppercase tracking-widest text-xs animate-pulse">
              Cargando inteligencia de datos...
            </p>
          </div>
        ) : error ? (
          <div className="p-8 bg-red-50 border border-red-100 text-red-700 rounded-3xl flex items-center gap-4 shadow-sm mb-10">
            <WarningIcon />
            <div>
              <p className="font-black text-sm">Error al cargar el dashboard</p>
              <p className="text-xs font-medium opacity-80">{error}</p>
            </div>
            <button onClick={loadData} className="ml-auto px-5 py-2 bg-red-600 text-white text-xs font-black uppercase tracking-widest rounded-xl hover:bg-red-700 transition-colors shadow">
              Reintentar
            </button>
          </div>
        ) : (
          <>
            {/* ── KPI Cards ──────────────────────────────────────────────────── */}
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6 mb-12">
              {/* Total → /public/procesados (sin filtro) */}
              <KpiCard
                title="Total Contratos"
                value={metrics!.total_contratos.toLocaleString('es-ES')}
                subtitle="Contratos procesados en el sistema"
                icon={<ContractIcon />}
                gradient="bg-gradient-to-br from-indigo-50 to-indigo-100/60"
                border="border-indigo-200/50"
                textColor="text-indigo-950"
                badgeColor="bg-indigo-600 text-white"
                badge="TOTAL"
                onClick={() => navigate('/public/procesados')}
              />
              {/* Incompletos → ?filter=INCOMPLETOS */}
              <KpiCard
                title="% Incompletos"
                value={`${metrics!.pct_incompletos.toFixed(1)}%`}
                subtitle={`${metrics!.total_incompletos.toLocaleString('es-ES')} registros con campos faltantes`}
                icon={<WarningIcon />}
                gradient="bg-gradient-to-br from-amber-50 to-amber-100/60"
                border="border-amber-200/50"
                textColor="text-amber-950"
                badgeColor="bg-amber-500 text-white"
                badge="⚠️"
                onClick={() => navigate('/public/procesados?calidad=INCOMPLETOS')}
              />
              {/* Sospechosos → ?filter=SOSPECHOSOS */}
              <KpiCard
                title="% Sospechosos"
                value={`${metrics!.pct_sospechosos.toFixed(1)}%`}
                subtitle={`${metrics!.total_sospechosos.toLocaleString('es-ES')} anomalías detectadas`}
                icon={<AlertIcon />}
                gradient="bg-gradient-to-br from-rose-50 to-rose-100/60"
                border="border-rose-200/50"
                textColor="text-rose-950"
                badgeColor="bg-rose-500 text-white"
                badge="🚨"
                onClick={() => navigate('/public/procesados?calidad=SOSPECHOSOS')}
              />
              {/* Alto Riesgo → ?filter=ALTO_RIESGO */}
              <KpiCard
                title="% Alto Riesgo"
                value={`${metrics!.pct_alto_riesgo.toFixed(1)}%`}
                subtitle={`${metrics!.total_alto_riesgo.toLocaleString('es-ES')} contratos clasificados ALTO`}
                icon={<ShieldIcon />}
                gradient="bg-gradient-to-br from-violet-50 to-violet-100/60"
                border="border-violet-200/50"
                textColor="text-violet-950"
                badgeColor="bg-violet-600 text-white"
                badge="RIESGO"
                onClick={() => navigate('/public/procesados?calidad=ALTO_RIESGO')}
              />
            </div>

            {/* ── Confianza Banner ─────────────────────────────────────────────── */}
            <div className="mb-10 bg-gradient-to-r from-indigo-600 to-violet-600 rounded-[28px] p-8 flex flex-col md:flex-row items-center justify-between gap-6 shadow-2xl shadow-indigo-200/50">
              <div className="text-white text-center md:text-left">
                <p className="text-xs font-black uppercase tracking-widest opacity-70 mb-1">
                  Índice de Confianza de Datos
                </p>
                <p className="text-5xl font-black tracking-tighter">
                  {metrics!.promedio_confianza.toFixed(1)}
                  <span className="text-2xl opacity-60 ml-1">/ 100</span>
                </p>
                <p className="text-sm opacity-70 font-medium mt-2">
                  Promedio del sistema basado en completitud y consistencia de datos.
                </p>
              </div>
              <div className="flex flex-col items-center gap-2">
                <div className="relative w-28 h-28">
                  <svg className="w-28 h-28 -rotate-90" viewBox="0 0 100 100">
                    <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth="10" />
                    <circle
                      cx="50" cy="50" r="40" fill="none" stroke="white" strokeWidth="10"
                      strokeLinecap="round"
                      strokeDasharray={`${2 * Math.PI * 40}`}
                      strokeDashoffset={`${2 * Math.PI * 40 * (1 - metrics!.promedio_confianza / 100)}`}
                      className="transition-all duration-1000"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-white text-xl font-black">
                      {Math.round(metrics!.promedio_confianza)}%
                    </span>
                  </div>
                </div>
                <span className="text-white/60 text-xs font-bold uppercase tracking-widest">
                  {metrics!.promedio_confianza >= 80 ? '✅ Excelente' : metrics!.promedio_confianza >= 60 ? '⚠️ Aceptable' : '🚨 Bajo'}
                </span>
              </div>
            </div>

            {/* ── Charts Row ───────────────────────────────────────────────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-10">
              <ChartSection title="Distribución de Riesgo" subtitle="Clasificación por nivel de riesgo detectado">
                <RiskChart data={riskData} />
              </ChartSection>
              <div className="lg:col-span-2">
                <ChartSection title="Top 10 Proveedores" subtitle="Proveedores con mayor número de contratos">
                  <TopProvidersChart data={topProviders} />
                </ChartSection>
              </div>
            </div>

            {/* ── Anomalies Row ─────────────────────────────────────────────────── */}
            <div className="mb-10">
              <ChartSection title="Tipos de Anomalías" subtitle="Distribución de irregularidades detectadas en el sistema">
                <AnomalyChart data={anomalyData} total={metrics!.total_contratos} />
              </ChartSection>
            </div>

            {/* ── Quick Stats Footer ─────────────────────────────────────────────── */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                {
                  label: 'Contratos Completos',
                  value: (metrics!.total_contratos - metrics!.total_incompletos).toLocaleString('es-ES'),
                  color: 'text-emerald-600',
                  bg: 'bg-emerald-50 border-emerald-100',
                  filter: '',
                },
                {
                  label: 'Contratos Incompletos',
                  value: metrics!.total_incompletos.toLocaleString('es-ES'),
                  color: 'text-amber-600',
                  bg: 'bg-amber-50 border-amber-100',
                  filter: 'INCOMPLETOS',
                },
                {
                  label: 'Con Anomalías',
                  value: metrics!.total_sospechosos.toLocaleString('es-ES'),
                  color: 'text-rose-600',
                  bg: 'bg-rose-50 border-rose-100',
                  filter: 'SOSPECHOSOS',
                },
                {
                  label: 'Alto Riesgo',
                  value: metrics!.total_alto_riesgo.toLocaleString('es-ES'),
                  color: 'text-violet-600',
                  bg: 'bg-violet-50 border-violet-100',
                  filter: 'ALTO_RIESGO',
                },
              ].map((stat) => (
                <div
                  key={stat.label}
                  className={`${stat.bg} border rounded-2xl p-5 text-center cursor-pointer hover:scale-[1.02] transition-transform`}
                  onClick={() =>
                    navigate(stat.filter ? `/public/procesados?calidad=${stat.filter}` : '/public/procesados')
                  }
                >
                  <p className={`text-3xl font-black ${stat.color} tracking-tighter mb-1`}>{stat.value}</p>
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">{stat.label}</p>
                </div>
              ))}
            </div>
          </>
        )}
      </main>

      {/* ── Footer ───────────────────────────────────────────────────────────── */}
      <footer className="relative z-10 mt-20 border-t border-slate-100 bg-white/60 backdrop-blur-md">
        <div className="max-w-[1400px] mx-auto px-8 py-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white">
              <ShieldIcon />
            </div>
            <span className="text-sm font-black text-indigo-950">Plataforma Anticorrupción</span>
          </div>
          <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">
            Datos públicos · Transparencia · Auditoría
          </p>
          <div className="flex items-center gap-2 text-xs font-bold text-emerald-600">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Sistema Operativo
          </div>
        </div>
      </footer>
    </div>
  );
};
