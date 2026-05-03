import { useState, useEffect } from 'react';
import { X, Save, RefreshCw } from 'lucide-react';

export default function FuenteForm({ isOpen, onClose, onSubmit, initialData }) {
  const [formData, setFormData] = useState({
    nombre: '',
    tipo: 'secop_mock',
    endpoint: '',
    frecuencia_dias: 1
  });
  
  const [isTesting, setIsTesting] = useState(false);
  const [testSuccess, setTestSuccess] = useState(null);

  useEffect(() => {
    if (initialData) {
      setFormData({
        nombre: initialData.nombre || '',
        tipo: initialData.tipo || 'secop_mock',
        endpoint: initialData.endpoint || '',
        frecuencia_dias: initialData.frecuencia_dias || 1
      });
    } else {
      setFormData({ nombre: '', tipo: 'secop_mock', endpoint: '', frecuencia_dias: 1 });
    }
    setTestSuccess(null);
  }, [initialData, isOpen]);

  if (!isOpen) return null;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ 
      ...prev, 
      [name]: name === 'frecuencia_dias' ? parseInt(value) || 1 : value 
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData, !!initialData);
  };

  const handleTestConnection = () => {
    setIsTesting(true);
    setTestSuccess(null);
    // Simulate connection test
    setTimeout(() => {
      setIsTesting(false);
      setTestSuccess(formData.endpoint.length > 5); // simple mock logic
    }, 1500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm transition-opacity">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md flex flex-col animate-in fade-in zoom-in-95 duration-200">
        
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <h2 className="text-xl font-bold text-gray-900">
            {initialData ? 'Editar Fuente de Datos' : 'Nueva Fuente de Datos'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nombre</label>
            <input 
              required
              type="text" 
              name="nombre"
              value={formData.nombre}
              onChange={handleChange}
              placeholder="Ej. SECOP II Contratos"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-shadow"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de Conector</label>
            <select 
              name="tipo"
              value={formData.tipo}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white"
            >
              <option value="secop_mock">SECOP II (Mock)</option>
              <option value="api_rest">API REST Genérica</option>
              <option value="socrata">Socrata Open Data</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Endpoint / URL</label>
            <input 
              required
              type="text" 
              name="endpoint"
              value={formData.endpoint}
              onChange={handleChange}
              placeholder="https://www.datos.gov.co/resource/..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-shadow"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Frecuencia (Días)</label>
            <input 
              required
              type="number" 
              min="1"
              name="frecuencia_dias"
              value={formData.frecuencia_dias}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-shadow"
            />
          </div>

          {/* Test Connection Area */}
          <div className="pt-2">
            <button 
              type="button" 
              onClick={handleTestConnection}
              disabled={isTesting || !formData.endpoint}
              className="text-sm font-medium text-brand-600 hover:text-brand-700 flex items-center gap-1.5 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isTesting ? 'animate-spin' : ''}`} />
              {isTesting ? 'Probando...' : 'Probar conexión'}
            </button>
            {testSuccess === true && <p className="text-xs text-green-600 mt-1">✓ Conexión exitosa</p>}
            {testSuccess === false && <p className="text-xs text-red-600 mt-1">✗ Error de conexión</p>}
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-100 mt-2">
            <button 
              type="button" 
              onClick={onClose}
              className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition-colors"
            >
              Cancelar
            </button>
            <button 
              type="submit"
              className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 font-medium transition-colors flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              Guardar Fuente
            </button>
          </div>
        </form>

      </div>
    </div>
  );
}
