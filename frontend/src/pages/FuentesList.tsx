import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Edit2, Trash2, Play, RefreshCw, AlertCircle, CheckCircle2, History } from 'lucide-react';
import toast from 'react-hot-toast';
import { fuentesService } from '../services/fuentesService';
import type { FuenteDatosResponseDTO, ConexionTestResponseDTO, SincronizacionHistorialResponseDTO } from '../types/fuente';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { Skeleton } from '../components/ui/Skeleton';
import { HistorialSyncModal } from '../components/fuentes/HistorialSyncModal';

export const FuentesList: React.FC = () => {
  const navigate = useNavigate();
  const [fuentes, setFuentes] = useState<FuenteDatosResponseDTO[]>([]);
  const [sincronizaciones, setSincronizaciones] = useState<SincronizacionHistorialResponseDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncingId, setSyncingId] = useState<number | null>(null);
  
  // Modals state
  const [deleteModal, setDeleteModal] = useState<{ isOpen: boolean; id: number | null }>({ isOpen: false, id: null });
  const [testModal, setTestModal] = useState<{ isOpen: boolean; result: ConexionTestResponseDTO | null; loading: boolean }>({ isOpen: false, result: null, loading: false });
  const [historialModal, setHistorialModal] = useState<{ isOpen: boolean; id: number | null; nombre: string }>({ isOpen: false, id: null, nombre: '' });

  const fetchFuentes = async () => {
    try {
      setLoading(true);
      const [dataFuentes, dataSyncs] = await Promise.all([
        fuentesService.getAll(),
        fuentesService.getSincronizacionesGlobales().catch(() => []) // Fallback si falla
      ]);
      setFuentes(dataFuentes);
      setSincronizaciones(dataSyncs);
    } catch (error) {
      toast.error('Error al cargar las fuentes de datos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFuentes();
  }, []);

  const handleDelete = async () => {
    if (!deleteModal.id) return;
    try {
      await fuentesService.delete(deleteModal.id);
      toast.success('Fuente eliminada exitosamente');
      setFuentes(fuentes.filter(f => f.id !== deleteModal.id));
      setDeleteModal({ isOpen: false, id: null });
    } catch (error) {
      toast.error('Error al eliminar la fuente');
    }
  };

  const handleTestConnection = async (id: number) => {
    setTestModal({ isOpen: true, result: null, loading: true });
    try {
      const result = await fuentesService.testConnection(id);
      setTestModal({ isOpen: true, result, loading: false });
    } catch (error: any) {
      setTestModal({ 
        isOpen: true, 
        result: { exitoso: false, mensaje: error?.response?.data?.detail || 'Error de conexión', registros_muestra: null }, 
        loading: false 
      });
    }
  };

  const handleSync = async (id: number) => {
    setSyncingId(id);
    try {
      await fuentesService.sync(id);
      toast.success('Sincronización iniciada exitosamente');
      await fetchFuentes();
    } catch (error) {
      toast.error('Error al sincronizar la fuente');
    } finally {
      setSyncingId(null);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Fuentes de Datos</h1>
          <p className="text-slate-500 mt-1">Gestiona las fuentes de información del sistema.</p>
        </div>
        <Button onClick={() => navigate('/admin/fuentes/nueva')} className="gap-2">
          <Plus size={18} />
          Nueva Fuente
        </Button>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-50 text-slate-600 font-medium border-b border-slate-200">
              <tr>
                <th className="px-6 py-4">ID</th>
                <th className="px-6 py-4">Nombre</th>
                <th className="px-6 py-4">Tipo / Formato</th>
                <th className="px-6 py-4">Frecuencia</th>
                <th className="px-6 py-4">Estado</th>
                <th className="px-6 py-4">Última Sync</th>
                <th className="px-6 py-4 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    <td className="px-6 py-4"><Skeleton className="h-4 w-8" /></td>
                    <td className="px-6 py-4"><Skeleton className="h-4 w-32" /></td>
                    <td className="px-6 py-4"><Skeleton className="h-4 w-24" /></td>
                    <td className="px-6 py-4"><Skeleton className="h-4 w-16" /></td>
                    <td className="px-6 py-4"><Skeleton className="h-6 w-16 rounded-full" /></td>
                    <td className="px-6 py-4"><Skeleton className="h-4 w-24" /></td>
                    <td className="px-6 py-4"><Skeleton className="h-8 w-32 ml-auto" /></td>
                  </tr>
                ))
              ) : fuentes.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-slate-500">
                    No hay fuentes registradas. Crea la primera fuente de datos.
                  </td>
                </tr>
              ) : (
                fuentes.map((fuente) => (
                  <tr key={fuente.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 font-medium text-slate-900">#{fuente.id}</td>
                    <td className="px-6 py-4 font-medium text-slate-900">{fuente.nombre}</td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-1">
                        <span className="text-slate-600">{fuente.tipo}</span>
                        <Badge variant="info" className="w-max px-1.5 py-0 text-[10px] uppercase">
                          {fuente.formato}
                        </Badge>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-slate-600">{fuente.frecuencia_dias} días</td>
                    <td className="px-6 py-4">
                      <Badge variant={fuente.activo ? 'success' : 'error'}>
                        {fuente.activo ? 'Activo' : 'Inactivo'}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 text-slate-600">
                      <div className="flex items-center gap-2">
                        {fuente.ultima_sync ? new Date(fuente.ultima_sync).toLocaleDateString() : 'Nunca'}
                        {(() => {
                          const fuenteSyncs = sincronizaciones.filter(s => s.fuente_id === fuente.id).sort((a, b) => new Date(b.fecha_inicio).getTime() - new Date(a.fecha_inicio).getTime());
                          if (fuenteSyncs.length > 0 && fuenteSyncs[0].estado === 'ERROR') {
                            return (
                              <div className="group relative flex items-center justify-center">
                                <AlertCircle size={16} className="text-red-500 cursor-help" />
                                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-max max-w-xs bg-slate-800 text-white text-xs rounded py-1 px-2 z-10 shadow-lg">
                                  La última sincronización falló: {fuenteSyncs[0].mensaje_error || 'Error desconocido'}
                                  <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-800" />
                                </div>
                              </div>
                            );
                          }
                          return null;
                        })()}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        <Button 
                          variant="outline" 
                          size="sm" 
                          className="h-8 w-8 p-0" 
                          title="Probar Conexión"
                          onClick={() => handleTestConnection(fuente.id)}
                        >
                          <Play size={14} className="text-blue-500" />
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm" 
                          className="h-8 w-8 p-0" 
                          title="Sincronizar"
                          onClick={() => handleSync(fuente.id)}
                          isLoading={syncingId === fuente.id}
                        >
                          <RefreshCw size={14} className="text-emerald-500" />
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm" 
                          className="h-8 w-8 p-0" 
                          title="Ver Historial"
                          onClick={() => setHistorialModal({ isOpen: true, id: fuente.id, nombre: fuente.nombre })}
                        >
                          <History size={14} className="text-slate-600" />
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm" 
                          className="h-8 w-8 p-0" 
                          title="Editar"
                          onClick={() => navigate(`/admin/fuentes/editar/${fuente.id}`)}
                        >
                          <Edit2 size={14} className="text-slate-600" />
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm" 
                          className="h-8 w-8 p-0 hover:bg-red-50 hover:text-red-600 hover:border-red-200" 
                          title="Eliminar"
                          onClick={() => setDeleteModal({ isOpen: true, id: fuente.id })}
                        >
                          <Trash2 size={14} />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Eliminar Modal */}
      <Modal 
        isOpen={deleteModal.isOpen} 
        onClose={() => setDeleteModal({ isOpen: false, id: null })}
        title="Confirmar eliminación"
      >
        <p className="text-slate-600 mb-6">
          ¿Estás seguro que deseas eliminar esta fuente de datos? Esta acción no se puede deshacer.
        </p>
        <div className="flex justify-end gap-3">
          <Button variant="outline" onClick={() => setDeleteModal({ isOpen: false, id: null })}>
            Cancelar
          </Button>
          <Button variant="danger" onClick={handleDelete}>
            Sí, Eliminar
          </Button>
        </div>
      </Modal>

      {/* Test Conexión Modal */}
      <Modal 
        isOpen={testModal.isOpen} 
        onClose={() => setTestModal({ isOpen: false, result: null, loading: false })}
        title="Prueba de Conexión"
      >
        {testModal.loading ? (
          <div className="flex flex-col items-center justify-center py-8">
            <RefreshCw className="h-8 w-8 text-blue-500 animate-spin mb-4" />
            <p className="text-slate-600 font-medium">Probando conexión al endpoint...</p>
          </div>
        ) : testModal.result ? (
          <div className="space-y-4">
            <div className={`p-4 rounded-lg flex items-start gap-3 ${testModal.result.exitoso ? 'bg-emerald-50 border border-emerald-200 text-emerald-800' : 'bg-red-50 border border-red-200 text-red-800'}`}>
              {testModal.result.exitoso ? <CheckCircle2 className="mt-0.5" /> : <AlertCircle className="mt-0.5" />}
              <div>
                <h4 className="font-semibold">{testModal.result.exitoso ? 'Conexión Exitosa' : 'Error de Conexión'}</h4>
                <p className="text-sm mt-1">{testModal.result.mensaje}</p>
              </div>
            </div>
            {testModal.result.registros_muestra && (
              <div>
                <h4 className="text-sm font-semibold text-slate-700 mb-2">IDs de Registros de Muestra:</h4>
                <div className="bg-slate-100 p-3 rounded-md border border-slate-200 font-mono text-sm overflow-auto">
                  {JSON.stringify(testModal.result.registros_muestra, null, 2)}
                </div>
              </div>
            )}
          </div>
        ) : null}
        <div className="flex justify-end mt-6">
          <Button onClick={() => setTestModal({ isOpen: false, result: null, loading: false })}>
            Cerrar
          </Button>
        </div>
      </Modal>

      {/* Historial Sync Modal */}
      <HistorialSyncModal
        isOpen={historialModal.isOpen}
        onClose={() => setHistorialModal({ isOpen: false, id: null, nombre: '' })}
        fuenteId={historialModal.id}
        fuenteNombre={historialModal.nombre}
      />
    </div>
  );
};
