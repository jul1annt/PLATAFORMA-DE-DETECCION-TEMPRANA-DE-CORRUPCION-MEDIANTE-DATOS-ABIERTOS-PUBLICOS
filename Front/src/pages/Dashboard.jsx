import { useState, useEffect, useCallback } from 'react';
import { Plus, Database, AlertTriangle, Activity, CheckCircle2 } from 'lucide-react';
import FuenteTable from '../components/FuenteTable';
import FuenteForm from '../components/FuenteForm';
import LogsModal from '../components/LogsModal';
import QualityDashboard from '../components/QualityDashboard';
import { 
  getFuentes, createFuente, updateFuente, 
  activarFuente, desactivarFuente, syncFuente, getLogs 
} from '../services/api';

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState('ingesta'); // 'ingesta' | 'calidad'

  // --- Estado de Ingesta (Épica 1) ---
  const [fuentes, setFuentes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [selectedFuenteToEdit, setSelectedFuenteToEdit] = useState(null);
  
  const [isLogsOpen, setIsLogsOpen] = useState(false);
  const [logsData, setLogsData] = useState([]);
  const [selectedFuenteForLogs, setSelectedFuenteForLogs] = useState(null);

  const fetchFuentes = useCallback(async () => {
    try {
      setLoading(true);
      const { data } = await getFuentes();
      setFuentes(data);
      setError(null);
    } catch (err) {
      console.error('Error fetching fuentes:', err);
      setError('No se pudo conectar con el servidor. Verifica que el backend esté en ejecución.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'ingesta') {
      fetchFuentes();
    }
  }, [fetchFuentes, activeTab]);

  const handleCreateOrUpdate = async (formData, isEdit) => {
    try {
      if (isEdit && selectedFuenteToEdit) {
        await updateFuente(selectedFuenteToEdit.id, formData);
      } else {
        await createFuente(formData);
      }
      await fetchFuentes();
      setIsFormOpen(false);
    } catch (err) {
      alert('Error guardando la fuente de datos.');
      console.error(err);
    }
  };

  const handleToggleStatus = async (fuente) => {
    try {
      if (fuente.estado === 'activa') {
        if (window.confirm(`¿Seguro que deseas desactivar ${fuente.nombre}? Dejará de sincronizarse.`)) {
          await desactivarFuente(fuente.id);
          fetchFuentes();
        }
      } else {
        await activarFuente(fuente.id);
        fetchFuentes();
      }
    } catch (err) {
      alert('Error cambiando el estado.');
    }
  };

  const handleSync = async (fuente) => {
    if (fuente.estado !== 'activa') {
      alert('Debes activar la fuente antes de poder sincronizarla.');
      return;
    }
    
    try {
      alert(`Sincronización iniciada para ${fuente.nombre}. Esto puede tardar unos segundos...`);
      await syncFuente(fuente.id);
      await fetchFuentes();
      alert(`Sincronización completada para ${fuente.nombre}`);
    } catch (err) {
      alert('Error durante la sincronización.');
    }
  };

  const handleViewLogs = async (fuente) => {
    try {
      const { data } = await getLogs(fuente.id);
      setLogsData(data);
      setSelectedFuenteForLogs(fuente);
      setIsLogsOpen(true);
    } catch (err) {
      alert('Error obteniendo los logs.');
    }
  };

  const openCreateForm = () => {
    setSelectedFuenteToEdit(null);
    setIsFormOpen(true);
  };

  const openEditForm = (fuente) => {
    setSelectedFuenteToEdit(fuente);
    setIsFormOpen(true);
  };

  return (
    <div className="space-y-6">
      
      {/* TABS NAVEGACIÓN */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8" aria-label="Tabs">
          <button
            onClick={() => setActiveTab('ingesta')}
            className={`
              whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors
              ${activeTab === 'ingesta'
                ? 'border-brand-500 text-brand-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }
            `}
          >
            <Database className="w-4 h-4" />
            Épica 1: Ingesta de Fuentes
          </button>

          <button
            onClick={() => setActiveTab('calidad')}
            className={`
              whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors
              ${activeTab === 'calidad'
                ? 'border-brand-500 text-brand-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }
            `}
          >
            <CheckCircle2 className="w-4 h-4" />
            Épica 2: Calidad y Procesamiento
          </button>
        </nav>
      </div>

      {/* RENDERIZADO CONDICIONAL POR PESTAÑA */}
      {activeTab === 'ingesta' && (
        <div className="space-y-6 animate-in fade-in duration-500">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <div>
              <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                <Database className="w-6 h-6 text-brand-600" />
                Fuentes de Datos
              </h2>
              <p className="text-gray-500 mt-1 text-sm">Gestiona los orígenes de datos (SECOP, etc) para la plataforma.</p>
            </div>
            <button 
              onClick={openCreateForm}
              className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-brand-600 text-white font-medium rounded-lg hover:bg-brand-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-500"
            >
              <Plus className="w-5 h-5" />
              Nueva Fuente
            </button>
          </div>

          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-medium text-red-800">Error de conexión</h3>
                <p className="text-red-600 text-sm mt-1">{error}</p>
              </div>
            </div>
          )}

          {loading ? (
            <div className="py-24 flex flex-col items-center justify-center">
              <div className="w-8 h-8 border-4 border-brand-200 border-t-brand-600 rounded-full animate-spin"></div>
              <p className="text-gray-500 mt-4 font-medium">Cargando fuentes...</p>
            </div>
          ) : (
            <FuenteTable 
              fuentes={fuentes} 
              onEdit={openEditForm}
              onToggleStatus={handleToggleStatus}
              onSync={handleSync}
              onViewLogs={handleViewLogs}
            />
          )}

          <FuenteForm 
            isOpen={isFormOpen} 
            onClose={() => setIsFormOpen(false)} 
            onSubmit={handleCreateOrUpdate}
            initialData={selectedFuenteToEdit}
          />

          <LogsModal 
            isOpen={isLogsOpen}
            onClose={() => setIsLogsOpen(false)}
            logs={logsData}
            fuenteNombre={selectedFuenteForLogs?.nombre}
          />
        </div>
      )}

      {activeTab === 'calidad' && (
        <QualityDashboard />
      )}

    </div>
  );
}
