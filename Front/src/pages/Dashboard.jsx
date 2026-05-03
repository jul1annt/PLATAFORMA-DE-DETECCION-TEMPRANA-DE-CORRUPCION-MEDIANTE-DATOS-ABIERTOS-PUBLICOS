import { useState, useEffect, useCallback } from 'react';
import { Plus, Database, AlertTriangle } from 'lucide-react';
import FuenteTable from '../components/FuenteTable';
import FuenteForm from '../components/FuenteForm';
import LogsModal from '../components/LogsModal';
import { 
  getFuentes, createFuente, updateFuente, 
  activarFuente, desactivarFuente, syncFuente, getLogs 
} from '../services/api';

export default function Dashboard() {
  const [fuentes, setFuentes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modals state
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
    fetchFuentes();
  }, [fetchFuentes]);

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
    
    // Optimistic minimal UI feedback could go here
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
      {/* Header Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Database className="w-6 h-6 text-brand-600" />
            Fuentes de Datos
          </h2>
          <p className="text-gray-500 mt-1">Gestiona los orígenes de datos para la plataforma anticorrupción.</p>
        </div>
        <button 
          onClick={openCreateForm}
          className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-brand-600 text-white font-medium rounded-lg hover:bg-brand-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-500"
        >
          <Plus className="w-5 h-5" />
          Nueva Fuente
        </button>
      </div>

      {/* Error State */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-red-800">Error de conexión</h3>
            <p className="text-red-600 text-sm mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Loading & Table Area */}
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

      {/* Modals */}
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
  );
}
