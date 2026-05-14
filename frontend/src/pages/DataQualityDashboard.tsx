import React, { useEffect, useState } from 'react';
import { ShieldAlert, RefreshCcw } from 'lucide-react';
import toast from 'react-hot-toast';
import { calidadService } from '../services/calidadService';
import { fuentesService } from '../services/fuentesService';
import type { MetricasCalidadDTO, CampoFaltanteDTO } from '../types/calidad';
import type { FuenteDatosResponseDTO, SincronizacionHistorialResponseDTO } from '../types/fuente';
import { QualityScoreCard } from '../components/calidad/QualityScoreCard';
import { CamposFaltantesTable } from '../components/calidad/CamposFaltantesTable';
import { ComparativaSincronizaciones } from '../components/calidad/ComparativaSincronizaciones';
import { Button } from '../components/ui/Button';
import { Skeleton } from '../components/ui/Skeleton';

export const DataQualityDashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [metricas, setMetricas] = useState<MetricasCalidadDTO | null>(null);
  const [camposFaltantes, setCamposFaltantes] = useState<CampoFaltanteDTO[]>([]);
  const [fuentes, setFuentes] = useState<FuenteDatosResponseDTO[]>([]);
  const [sincronizaciones, setSincronizaciones] = useState<SincronizacionHistorialResponseDTO[]>([]);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [
        metricasData,
        camposData,
        fuentesData,
        sincronizacionesData
      ] = await Promise.all([
        calidadService.getMetricasCalidad(),
        calidadService.getCamposFaltantes(),
        fuentesService.getAll(),
        fuentesService.getSincronizacionesGlobales()
      ]);

      setMetricas(metricasData);
      setCamposFaltantes(camposData);
      setFuentes(fuentesData);
      setSincronizaciones(sincronizacionesData);
    } catch (error) {
      toast.error('Error al cargar los datos del dashboard de calidad');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

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
        <Button onClick={fetchDashboardData} variant="outline" className="gap-2" isLoading={loading}>
          <RefreshCcw size={16} />
          Actualizar Datos
        </Button>
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
      ) : metricas ? (
        <div className="space-y-6">
          <section>
            <h2 className="text-lg font-semibold text-slate-800 mb-4">Resumen Global (Post-Transformación)</h2>
            <QualityScoreCard metricas={metricas} />
          </section>

          <section>
            <ComparativaSincronizaciones fuentes={fuentes} sincronizaciones={sincronizaciones} />
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
