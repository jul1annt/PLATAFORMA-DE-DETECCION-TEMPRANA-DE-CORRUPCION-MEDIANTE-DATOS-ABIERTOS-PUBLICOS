import { createBrowserRouter, Navigate } from 'react-router-dom';
import { MainLayout } from '../layouts/MainLayout';
import { AdminLayout } from '../layouts/AdminLayout';
import { HomePage } from '../pages/HomePage';
import { Dashboard } from '../pages/Dashboard';
import { FuentesList } from '../pages/FuentesList';
import { FuenteForm } from '../pages/FuenteForm';
import { DataQualityDashboard } from '../pages/DataQualityDashboard';
import { PublicProcesados } from '../pages/PublicProcesados';
import { PublicContratoDetalle } from '../pages/PublicContratoDetalle';
import { PublicDashboard } from '../pages/PublicDashboard';
import ProtectedRoute from './ProtectedRoute';
import AdminLogin from '../pages/admin/AdminLogin';
import AdminDashboard from '../pages/admin/AdminDashboard';
import AdminSyncLogs from '../pages/admin/AdminSyncLogs';
import { AdminReprocesamiento } from '../pages/admin/AdminReprocesamiento';

export const router = createBrowserRouter([
  // ── Landing / Home ────────────────────────────────────────────────────────
  {
    path: '/',
    element: <HomePage />,
  },

  // ── Public: dashboard ──────────────────────────────────────────────────────
  {
    path: '/public/dashboard',
    element: <PublicDashboard />,
  },

  // ── Public: procesados ────────────────────────────────────────────────────
  {
    path: '/public/procesados',
    element: <PublicProcesados />,
  },
  {
    path: '/public/procesados/:id',
    element: <PublicContratoDetalle />,
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
          { path: 'fuentes', element: <FuentesList /> },
          { path: 'fuentes/nueva', element: <FuenteForm /> },
          { path: 'fuentes/editar/:id', element: <FuenteForm /> },
          { path: 'calidad', element: <DataQualityDashboard /> },
          { path: 'reprocesamiento', element: <AdminReprocesamiento /> },
          { path: 'sync-logs', element: <AdminSyncLogs /> },
        ],
      },
    ],
  },

  // ── Legacy internal app (MainLayout) ─────────────────────────────────────
  // Kept under /app to preserve all existing functionality
  {
    path: '/app',
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
    ],
  },

  // ── Catch-all ─────────────────────────────────────────────────────────────
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);
