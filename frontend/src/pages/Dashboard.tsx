import React, { useEffect, useState } from 'react';
import { Database, CheckCircle, XCircle, Clock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { fuentesService } from '../services/fuentesService';
import type { FuenteDatosResponseDTO } from '../types/fuente';

export const Dashboard: React.FC = () => {
  const [fuentes, setFuentes] = useState<FuenteDatosResponseDTO[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await fuentesService.getAll();
        setFuentes(data);
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const total = fuentes.length;
  const activas = fuentes.filter(f => f.activo).length;
  const inactivas = total - activas;
  const syncs = fuentes.filter(f => f.ultima_sync).map(f => new Date(f.ultima_sync as string).getTime());
  const ultimaSync = syncs.length > 0 ? new Date(Math.max(...syncs)).toLocaleString() : 'N/A';

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-slate-500 mt-1">Resumen de las fuentes de datos de la plataforma.</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Total de Fuentes</CardTitle>
            <Database className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-slate-900">
              {loading ? <span className="animate-pulse bg-slate-200 text-transparent rounded">00</span> : total}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Fuentes Activas</CardTitle>
            <CheckCircle className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-slate-900">
              {loading ? <span className="animate-pulse bg-slate-200 text-transparent rounded">00</span> : activas}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Fuentes Inactivas</CardTitle>
            <XCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-slate-900">
              {loading ? <span className="animate-pulse bg-slate-200 text-transparent rounded">00</span> : inactivas}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Última Sincronización</CardTitle>
            <Clock className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold text-slate-900 mt-1">
              {loading ? <span className="animate-pulse bg-slate-200 text-transparent rounded">Cargando...</span> : ultimaSync}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
