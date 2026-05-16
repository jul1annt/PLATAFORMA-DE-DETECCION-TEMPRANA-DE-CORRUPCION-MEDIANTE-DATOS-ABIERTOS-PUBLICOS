import React, { useEffect, useState } from 'react';
import {
  Database,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  ShieldCheck,
  User,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { useAuth } from '../../context/AuthContext';
import { fuentesService } from '../../services/fuentesService';
import type { FuenteDatosResponseDTO, SincronizacionHistorialResponseDTO } from '../../types/fuente';

const AdminDashboard: React.FC = () => {
  const { admin } = useAuth();
  const [fuentes, setFuentes] = useState<FuenteDatosResponseDTO[]>([]);
  const [recentSyncs, setRecentSyncs] = useState<SincronizacionHistorialResponseDTO[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [f, s] = await Promise.all([
          fuentesService.getAll(),
          fuentesService.getSincronizacionesGlobales(),
        ]);
        setFuentes(f);
        setRecentSyncs(s.slice(0, 5));
      } catch (err) {
        console.error('Error cargando dashboard:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const total = fuentes.length;
  const activas = fuentes.filter((f) => f.activo).length;
  const inactivas = total - activas;
  const syncTimes = fuentes
    .filter((f) => f.ultima_sync)
    .map((f) => new Date(f.ultima_sync as string).getTime());
  const ultimaSync =
    syncTimes.length > 0 ? new Date(Math.max(...syncTimes)).toLocaleString('es-CO') : 'N/A';

  const statCards = [
    { label: 'Total de Fuentes', value: total, icon: Database, color: 'text-blue-400' },
    { label: 'Fuentes Activas', value: activas, icon: CheckCircle, color: 'text-emerald-400' },
    { label: 'Fuentes Inactivas', value: inactivas, icon: XCircle, color: 'text-red-400' },
    { label: 'Última Sync', value: ultimaSync, icon: Clock, color: 'text-amber-400', small: true },
  ];

  const statusBadge: Record<string, string> = {
    EXITOSO: 'bg-emerald-100 text-emerald-700',
    EN_PROCESO: 'bg-amber-100 text-amber-700',
    ERROR: 'bg-red-100 text-red-700',
  };

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
                  <div className={`font-bold text-slate-900 ${card.small ? 'text-base' : 'text-3xl'}`}>
                    {card.value}
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Recent syncs table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <RefreshCw size={16} className="text-slate-500" />
            Últimas sincronizaciones
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-10 bg-slate-100 animate-pulse rounded" />
              ))}
            </div>
          ) : recentSyncs.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-6">
              No hay sincronizaciones registradas.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-500 border-b border-slate-100">
                    <th className="pb-2 pr-4 font-medium">Fuente</th>
                    <th className="pb-2 pr-4 font-medium">Inicio</th>
                    <th className="pb-2 pr-4 font-medium">Registros</th>
                    <th className="pb-2 font-medium">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {recentSyncs.map((s) => (
                    <tr key={s.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-2.5 pr-4 font-medium text-slate-700">
                        {s.fuente_nombre ?? `Fuente #${s.fuente_id}`}
                      </td>
                      <td className="py-2.5 pr-4 text-slate-500">
                        {new Date(s.fecha_inicio).toLocaleString('es-CO')}
                      </td>
                      <td className="py-2.5 pr-4 text-slate-600">{s.registros_traidos}</td>
                      <td className="py-2.5">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                            statusBadge[s.estado] ?? 'bg-slate-100 text-slate-600'
                          }`}
                        >
                          {s.estado}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

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
