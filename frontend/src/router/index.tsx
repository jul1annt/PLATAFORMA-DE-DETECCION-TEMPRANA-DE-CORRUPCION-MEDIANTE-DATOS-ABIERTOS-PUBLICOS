import { createBrowserRouter, Navigate } from 'react-router-dom';
import { MainLayout } from '../layouts/MainLayout';
import { AdminLayout } from '../layouts/AdminLayout';
import { Dashboard } from '../pages/Dashboard';
import { FuentesList } from '../pages/FuentesList';
import { FuenteForm } from '../pages/FuenteForm';
import { DataQualityDashboard } from '../pages/DataQualityDashboard';
import { PublicProcesados } from '../pages/PublicProcesados';
import ProtectedRoute from './ProtectedRoute';
import AdminLogin from '../pages/admin/AdminLogin';
import AdminDashboard from '../pages/admin/AdminDashboard';
import AdminFuentes from '../pages/admin/AdminFuentes';
import AdminSyncLogs from '../pages/admin/AdminSyncLogs';

export const router = createBrowserRouter([
  // ── Public: procesados ────────────────────────────────────────────────────
  {
    path: '/public/procesados',
    element: <PublicProcesados />,
  },

  // ── Admin login (public) ──────────────────────────────────────────────────
  {
    path: '/admin/login',
    element: <AdminLogin />,
  },

  // ── Admin zone (protected) ────────────────────────────────────────────────
  {
    path: '/admin',
    element: <ProtectedRoute />,
    children: [
      {
        element: <AdminLayout />,
        children: [
          { index: true, element: <AdminDashboard /> },
          { path: 'fuentes', element: <AdminFuentes /> },
          { path: 'sync-logs', element: <AdminSyncLogs /> },
        ],
      },
    ],
  },

  // ── Main app (existing, unchanged) ───────────────────────────────────────
  {
    path: '/',
    element: <MainLayout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'fuentes', element: <FuentesList /> },
      { path: 'fuentes/nueva', element: <FuenteForm /> },
      { path: 'fuentes/editar/:id', element: <FuenteForm /> },
      { path: 'calidad', element: <DataQualityDashboard /> },
      {
        path: 'configuracion',
        element: (
          <div className="p-8 text-center text-slate-500">
            Módulo de configuración en construcción.
          </div>
        ),
      },
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
]);
