import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Database,
  CheckCircle,
  ShieldCheck,
  User,
  ShieldAlert,
  FileWarning,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { useAuth } from '../../context/useAuth';
import { fuentesService } from '../../services/fuentesService';
import { calidadService } from '../../services/calidadService';
import { ComparativaSincronizaciones } from '../../components/calidad/ComparativaSincronizaciones';
import type { ComparativaFuenteDTO } from '../../services/fuentesService';
import type { MetricasCalidadDTO } from '../../types/calidad';
import { getErrorMessage } from '../../utils/errors';

const AdminDashboard: React.FC = () => {
  const { admin } = useAuth();
  const navigate = useNavigate();
  const [comparativa, setComparativa] = useState<ComparativaFuenteDTO[] | null>(null);
  const [metricas, setMetricas] = useState<MetricasCalidadDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const activeRequest = useRef<AbortController | null>(null);

  const fetchData = useCallback(async () => {
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    setLoading(true);
    setError(null);
    try {
      const [c, m] = await Promise.all([
        fuentesService.getComparativa(controller.signal),
        calidadService.getMetricasCalidad(controller.signal),
      ]);
      if (controller.signal.aborted) return;
      setComparativa(c);
      setMetricas(m);
    } catch (err: unknown) {
      if (controller.signal.aborted) return;
      setError(getErrorMessage(err, 'Error al cargar el dashboard'));
    } finally {
      if (activeRequest.current === controller) {
        activeRequest.current = null;
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchData();
    }, 0);
    return () => {
      window.clearTimeout(timer);
      activeRequest.current?.abort();
      activeRequest.current = null;
    };
  }, [fetchData]);

  const total: number | null = comparativa?.length ?? null;
  
  const statCards = [
    { label: 'Total de Fuentes', value: total, icon: Database, color: 'text-blue-400' },
    { label: 'Contratos Procesados', value: metricas?.total_contratos ?? null, icon: ShieldAlert, color: 'text-indigo-400' },
    { label: 'Calidad de Datos', value: metricas?.porcentaje_completos == null ? null : `${metricas.porcentaje_completos.toFixed(1)}%`, icon: CheckCircle, color: 'text-emerald-400' },
    { label: 'Registros Sospechosos', value: metricas?.sospechosos ?? null, icon: FileWarning, color: 'text-red-400' },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Welcome header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center">
          <ShieldCheck size={20} className="text-emerald-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dashboard Administrativo</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            Bienvenido,{' '}
            <span className="font-semibold text-slate-700">{admin?.username}</span> ·{' '}
            {new Date().toLocaleDateString('es-CO', {
              weekday: 'long',
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </p>
        </div>
      </div>

      {error && (
        <Card role="alert" className="border-red-200 bg-red-50">
          <CardContent className="flex items-center justify-between gap-4 py-4">
            <div>
              <p className="font-semibold text-red-800">No se pudo cargar el resumen.</p>
              <p className="text-sm text-red-700">{error}</p>
            </div>
            <button onClick={() => void fetchData()} className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700">
              Reintentar
            </button>
          </CardContent>
        </Card>
      )}

      {/* Stats grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <Card key={card.label}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">{card.label}</CardTitle>
                <Icon className={`h-4 w-4 ${card.color}`} />
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="h-8 bg-slate-100 animate-pulse rounded w-16" />
                ) : (
                  <div className="font-bold text-slate-900 text-3xl">
                    {card.value ?? '—'}
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Recent syncs and Quality Summary */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Sync Comparison (Rich Table) */}
        <div className="lg:col-span-2">
          {loading ? (
            <Card className="h-64 flex items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
            </Card>
          ) : error ? (
            <Card className="h-64 flex items-center justify-center text-sm text-slate-500">Resumen no disponible.</Card>
          ) : (
            <ComparativaSincronizaciones comparativa={comparativa ?? []} />
          )}
        </div>

        {/* Quality Summary Mini-Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ShieldAlert size={16} className="text-indigo-500" />
              Resumen de Calidad
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {loading ? (
              <div className="space-y-4">
                <div className="h-4 bg-slate-100 animate-pulse rounded w-full" />
                <div className="h-4 bg-slate-100 animate-pulse rounded w-3/4" />
                <div className="h-10 bg-slate-100 animate-pulse rounded w-full" />
              </div>
            ) : error ? (
              <p className="text-sm text-slate-500">Resumen no disponible.</p>
            ) : metricas ? (
              <>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm font-medium">
                    <span className="text-slate-500">Integridad de datos</span>
                    <span className="text-indigo-600">{metricas.porcentaje_completos == null ? '—' : `${metricas.porcentaje_completos.toFixed(1)}%`}</span>
                  </div>
                  <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-indigo-500 rounded-full" 
                      style={{ width: `${metricas.porcentaje_completos ?? 0}%` }}
                    />
                  </div>
                  <p className="text-[10px] text-slate-400">
                    Basado en {metricas.total_contratos.toLocaleString('es-CO')} registros procesados.
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                    <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Incompletos</p>
                    <p className="text-lg font-bold text-slate-700">{metricas.incompletos.toLocaleString('es-CO')}</p>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                    <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Sospechosos</p>
                    <p className="text-lg font-bold text-red-500">{metricas.sospechosos.toLocaleString('es-CO')}</p>
                  </div>
                </div>

                <button 
                  onClick={() => navigate('/admin/calidad')}
                  className="w-full py-2.5 bg-indigo-50 text-indigo-600 text-xs font-black uppercase tracking-widest rounded-xl hover:bg-indigo-100 transition-all border border-indigo-100"
                >
                  Ver Informe Detallado
                </button>
              </>
            ) : (
              <p className="text-sm text-slate-500">No hay datos de calidad disponibles.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Admin info card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <User size={16} className="text-slate-500" />
            Información de sesión
          </CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            {[
              { label: 'Usuario', value: admin?.username },
              { label: 'Email', value: admin?.email },
              { label: 'ID', value: admin?.id },
              { label: 'Estado', value: admin?.is_active ? 'Activo' : 'Inactivo' },
            ].map((item) => (
              <div key={item.label}>
                <dt className="text-xs font-medium text-slate-400 uppercase tracking-wide">
                  {item.label}
                </dt>
                <dd className="mt-0.5 font-medium text-slate-700">{item.value}</dd>
              </div>
            ))}
          </dl>
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminDashboard;
