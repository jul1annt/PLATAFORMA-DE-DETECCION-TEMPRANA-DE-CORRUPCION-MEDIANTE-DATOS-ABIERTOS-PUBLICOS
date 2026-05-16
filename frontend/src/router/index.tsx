import { createBrowserRouter, Navigate } from 'react-router-dom';
import { MainLayout } from '../layouts/MainLayout';
import { Dashboard } from '../pages/Dashboard';
import { FuentesList } from '../pages/FuentesList';
import { FuenteForm } from '../pages/FuenteForm';
import { DataQualityDashboard } from '../pages/DataQualityDashboard';
import { PublicProcesados } from '../pages/PublicProcesados';

export const router = createBrowserRouter([
  {
    path: '/public/procesados',
    element: <PublicProcesados />,
  },
  {
    path: '/',
    element: <MainLayout />,
    children: [
      {
        index: true,
        element: <Dashboard />,
      },
      {
        path: 'fuentes',
        element: <FuentesList />,
      },
      {
        path: 'fuentes/nueva',
        element: <FuenteForm />,
      },
      {
        path: 'fuentes/editar/:id',
        element: <FuenteForm />,
      },
      {
        path: 'calidad',
        element: <DataQualityDashboard />,
      },
      {
        path: 'configuracion',
        element: <div className="p-8 text-center text-slate-500">Módulo de configuración en construcción.</div>,
      },
      {
        path: '*',
        element: <Navigate to="/" replace />,
      },
    ],
  },
]);
