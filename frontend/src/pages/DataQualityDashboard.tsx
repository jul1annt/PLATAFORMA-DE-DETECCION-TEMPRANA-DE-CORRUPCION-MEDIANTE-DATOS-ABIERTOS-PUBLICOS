import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ShieldAlert, RefreshCcw } from 'lucide-react';
import toast from 'react-hot-toast';
import { calidadService } from '../services/calidadService';
import { fuentesService } from '../services/fuentesService';
import { getErrorMessage } from '../utils/errors';
import type { ComparativaFuenteDTO } from '../services/fuentesService';
import type { MetricasCalidadDTO, CampoFaltanteDTO } from '../types/calidad';
import { QualityScoreCard } from '../components/calidad/QualityScoreCard';
import { CamposFaltantesTable } from '../components/calidad/CamposFaltantesTable';
import { ComparativaSincronizaciones } from '../components/calidad/ComparativaSincronizaciones';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Skeleton } from '../components/ui/Skeleton';

export const DataQualityDashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metricas, setMetricas] = useState<MetricasCalidadDTO | null>(null);
  const [camposFaltantes, setCamposFaltantes] = useState<CampoFaltanteDTO[]>([]);
  const [comparativa, setComparativa] = useState<ComparativaFuenteDTO[]>([]);
  const activeRequest = useRef<AbortController | null>(null);

  const fetchDashboardData = useCallback(async () => {
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    setLoading(true);
    setError(null);
    try {
      const [
        metricasData,
        camposData,
        comparativaData,
      ] = await Promise.all([
        calidadService.getMetricasCalidad(controller.signal),
        calidadService.getCamposFaltantes(controller.signal),
        fuentesService.getComparativa(controller.signal)
      ]);

      if (controller.signal.aborted) return;
      setMetricas(metricasData);
      setCamposFaltantes(camposData);
      setComparativa(comparativaData);
    } catch (err: unknown) {
      if (controller.signal.aborted) return;
      setError(getErrorMessage(err, 'Error al cargar los datos del dashboard de calidad'));
    } finally {
      if (activeRequest.current === controller) {
        activeRequest.current = null;
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchDashboardData();
    }, 0);
    return () => {
      window.clearTimeout(timer);
      activeRequest.current?.abort();
      activeRequest.current = null;
    };
  }, [fetchDashboardData]);

  return (
    <div className="space-y-6 animate-in fade-in duration-500 pb-10">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <ShieldAlert className="text-indigo-600" />
            Calidad de Datos
          </h1>
          <p className="text-slate-500 mt-1">
            Monitoreo global de la integridad y salud de los contratos procesados.
          </p>
        </div>
        <div className="flex gap-2">
          <Button 
            onClick={async () => {
              try {
                toast.loading('Iniciando reprocesamiento...', { id: 'reproceso' });
                await calidadService.reprocesar();
                toast.success('Reprocesamiento iniciado. Consulta el avance en Reprocesamiento.', { id: 'reproceso' });
              } catch {
                toast.error('Error al reprocesar datos', { id: 'reproceso' });
              }
            }} 
            variant="secondary" 
            className="gap-2"
          >
            <RefreshCcw size={16} />
            Reprocesar Datos
          </Button>
          <Button onClick={fetchDashboardData} variant="outline" className="gap-2" isLoading={loading}>
            <RefreshCcw size={16} />
            Actualizar Datos
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-32 w-full rounded-xl" />
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Skeleton className="h-96 w-full lg:col-span-2 rounded-xl" />
            <Skeleton className="h-96 w-full rounded-xl" />
          </div>
        </div>
      ) : error ? (
        <Card role="alert" className="border-red-200 bg-red-50 p-8 text-red-800">
          <h2 className="font-semibold">No se pudo cargar el dashboard de calidad</h2>
          <p className="mt-2 text-sm">{error}</p>
          <Button onClick={() => void fetchDashboardData()} variant="secondary" className="mt-4">
            Reintentar
          </Button>
        </Card>
      ) : metricas ? (
        <div className="space-y-6">
          <section>
            <h2 className="text-lg font-semibold text-slate-800 mb-4">Resumen Global (Post-Transformación)</h2>
            <QualityScoreCard metricas={metricas} />
          </section>

          <section>
            <ComparativaSincronizaciones comparativa={comparativa} />
          </section>

          <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="lg:col-span-2">
              <CamposFaltantesTable campos={camposFaltantes} />
            </div>
          </section>
        </div>
      ) : (
        <div className="text-center py-20 text-slate-500">
          No hay datos de calidad disponibles. Ejecute el reprocesamiento.
        </div>
      )}
    </div>
  );
};
