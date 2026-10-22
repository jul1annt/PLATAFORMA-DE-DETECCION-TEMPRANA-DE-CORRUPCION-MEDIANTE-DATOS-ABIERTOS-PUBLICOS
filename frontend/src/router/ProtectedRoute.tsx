import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/useAuth';

/**
 * Protects all /admin routes.
 * - While session is being validated: full-page spinner
 * - Not authenticated: redirect to /admin/login
 * - Authenticated: render child routes
 */
const ProtectedRoute: React.FC = () => {
  const { admin, loading, restoreError, retrySessionRestore } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-slate-400 text-sm">Verificando sesión...</p>
        </div>
      </div>
    );
  }

  if (restoreError) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 px-6">
        <div role="alert" className="max-w-md rounded-2xl border border-amber-700 bg-slate-900 p-6 text-center">
          <p className="font-semibold text-white">No fue posible verificar la sesión</p>
          <p className="mt-2 text-sm text-slate-300">{restoreError}</p>
          <button
            onClick={retrySessionRestore}
            className="mt-5 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  if (!admin) {
    return <Navigate to="/admin/login" replace />;
  }

  return <Outlet />;
};

export default ProtectedRoute;
