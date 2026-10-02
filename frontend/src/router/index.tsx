import { createBrowserRouter, Navigate } from 'react-router-dom';
import { Suspense, type ReactNode } from 'react';
import { AdminLayout } from '../layouts/AdminLayout';
import ProtectedRoute from './ProtectedRoute';
import {
  HomePageRoute,
  FuentesListRoute,
  FuenteFormRoute,
  DataQualityDashboardRoute,
  PublicProcesadosRoute,
  PublicContratoDetalleRoute,
  PublicDashboardRoute,
  AdminLoginRoute,
  AdminDashboardRoute,
  AdminSyncLogsRoute,
  AdminReprocesamientoRoute,
  AdminAnaliticaRoute,
} from './lazyPages';

function withSuspense(element: ReactNode) {
  return <Suspense fallback={<div className="p-8 text-center text-slate-500">Cargando…</div>}>{element}</Suspense>;
}

export const router = createBrowserRouter([
  // ── Landing / Home ────────────────────────────────────────────────────────
  {
    path: '/',
    element: withSuspense(<HomePageRoute />),
  },

  // ── Public: dashboard ──────────────────────────────────────────────────────
  {
    path: '/public/dashboard',
    element: withSuspense(<PublicDashboardRoute />),
  },

  // ── Public: procesados ────────────────────────────────────────────────────
  {
    path: '/public/procesados',
    element: withSuspense(<PublicProcesadosRoute />),
  },
  {
    path: '/public/procesados/:id',
    element: withSuspense(<PublicContratoDetalleRoute />),
  },

  // ── Admin login (public) ──────────────────────────────────────────────────
  {
    path: '/admin/login',
    element: withSuspense(<AdminLoginRoute />),
  },

  // ── Admin zone (protected) ────────────────────────────────────────────────
  {
    path: '/admin',
    element: <ProtectedRoute />,
    children: [
      {
        element: <AdminLayout />,
        children: [
          { index: true, element: withSuspense(<AdminDashboardRoute />) },
          { path: 'fuentes', element: withSuspense(<FuentesListRoute />) },
          { path: 'fuentes/nueva', element: withSuspense(<FuenteFormRoute />) },
          { path: 'fuentes/editar/:id', element: withSuspense(<FuenteFormRoute />) },
          { path: 'calidad', element: withSuspense(<DataQualityDashboardRoute />) },
          { path: 'analitica', element: withSuspense(<AdminAnaliticaRoute />) },
          { path: 'reprocesamiento', element: withSuspense(<AdminReprocesamientoRoute />) },
          { path: 'sync-logs', element: withSuspense(<AdminSyncLogsRoute />) },
        ],
      },
    ],
  },

  {
    path: '/app/*',
    element: <Navigate to="/admin" replace />,
  },

  // ── Catch-all ─────────────────────────────────────────────────────────────
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);
