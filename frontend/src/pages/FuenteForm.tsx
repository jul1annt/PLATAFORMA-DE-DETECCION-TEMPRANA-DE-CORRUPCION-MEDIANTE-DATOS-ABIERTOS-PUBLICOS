import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { ArrowLeft, Save } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Card, CardContent } from '../components/ui/Card';
import { fuentesService } from '../services/fuentesService';
import type { FormatoFuente } from '../types/fuente';

const fuenteSchema = z.object({
  nombre: z.string().min(1, 'El nombre es requerido'),
  tipo: z.string().min(1, 'El tipo es requerido'),
  formato: z.enum(['JSON', 'CSV', 'XML'] as const),
  endpoint: z.string().url('Debe ser una URL válida'),
  api_key: z.string().optional(),
  frecuencia_dias: z.number().min(1, 'Debe ser al menos 1 día').max(365, 'Máximo 365 días'),
});

type FuenteFormData = z.infer<typeof fuenteSchema>;

export const FuenteForm: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const isEditing = !!id;
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FuenteFormData>({
    resolver: zodResolver(fuenteSchema),
    defaultValues: {
      formato: 'JSON',
      frecuencia_dias: 1,
    },
  });

  useEffect(() => {
    if (isEditing && id) {
      const loadFuente = async () => {
        try {
          const data = await fuentesService.getById(parseInt(id));
          reset({
            nombre: data.nombre,
            tipo: data.tipo,
            formato: data.formato as FormatoFuente,
            endpoint: data.endpoint,
            frecuencia_dias: data.frecuencia_dias,
            api_key: '', // La API key usualmente no se devuelve por seguridad, la dejamos vacía para no sobreescribir si no se toca
          });
        } catch (error) {
          toast.error('Error al cargar la fuente');
          navigate('/admin/fuentes');
        }
      };
      loadFuente();
    }
  }, [id, isEditing, reset, navigate]);

  const onSubmit = async (data: FuenteFormData) => {
    setIsSubmitting(true);
    try {
      if (isEditing && id) {
        await fuentesService.update(parseInt(id), {
          ...data,
          api_key: data.api_key || null, // Convertir string vacía a null
        });
        toast.success('Fuente actualizada exitosamente');
      } else {
        await fuentesService.create({
          ...data,
          api_key: data.api_key || null,
        });
        toast.success('Fuente creada exitosamente');
      }
      navigate('/admin/fuentes');
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Ocurrió un error al guardar');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500 max-w-3xl mx-auto">
      <div className="flex items-center gap-4">
        <button 
          onClick={() => navigate('/admin/fuentes')}
          className="p-2 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-full transition-colors"
        >
          <ArrowLeft size={20} />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            {isEditing ? 'Editar Fuente de Datos' : 'Nueva Fuente de Datos'}
          </h1>
          <p className="text-slate-500 mt-1">
            {isEditing ? 'Modifica los parámetros de conexión.' : 'Configura una nueva fuente para ingesta.'}
          </p>
        </div>
      </div>

      <Card>
        <CardContent className="p-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Input
                label="Nombre de la fuente"
                placeholder="Ej. SECOP II Contratos"
                {...register('nombre')}
                error={errors.nombre?.message}
              />
              <Input
                label="Tipo de entidad/dato"
                placeholder="Ej. Contratación Pública"
                {...register('tipo')}
                error={errors.tipo?.message}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Select
                label="Formato de respuesta"
                {...register('formato')}
                error={errors.formato?.message}
                options={[
                  { value: 'JSON', label: 'JSON' },
                  { value: 'CSV', label: 'CSV' },
                  { value: 'XML', label: 'XML' },
                ]}
              />
              <Input
                label="Frecuencia (Días)"
                type="number"
                min={1}
                max={365}
                {...register('frecuencia_dias', { valueAsNumber: true })}
                error={errors.frecuencia_dias?.message}
              />
            </div>

            <Input
              label="Endpoint URL"
              placeholder="https://api.datos.gov.co/resource/..."
              {...register('endpoint')}
              error={errors.endpoint?.message}
            />

            <Input
              label="API Key (Opcional)"
              type="password"
              placeholder="Deja en blanco si es pública o si no deseas cambiarla"
              {...register('api_key')}
              error={errors.api_key?.message}
            />

            <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
              <Button type="button" variant="outline" onClick={() => navigate('/admin/fuentes')}>
                Cancelar
              </Button>
              <Button type="submit" isLoading={isSubmitting} className="gap-2">
                <Save size={18} />
                Guardar Fuente
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};
