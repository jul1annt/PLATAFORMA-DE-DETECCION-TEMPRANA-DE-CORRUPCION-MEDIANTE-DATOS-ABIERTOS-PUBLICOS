import React from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  Database,
  LayoutDashboard,
  LogOut,
  RefreshCw,
  ShieldCheck,
  ShieldAlert,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { cn } from '../utils/utils';

const navItems = [
  { name: 'Dashboard', path: '/admin', icon: LayoutDashboard, end: true },
  { name: 'Fuentes de Datos', path: '/admin/fuentes', icon: Database, end: false },
  { name: 'Calidad de Datos', path: '/admin/calidad', icon: ShieldAlert, end: false },
  { name: 'Logs de Sync', path: '/admin/sync-logs', icon: RefreshCw, end: false },
];

export const AdminLayout: React.FC = () => {
  const { admin, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/admin/login', { replace: true });
  };

  const initials = admin?.username?.slice(0, 2).toUpperCase() ?? 'AD';

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      {/* ── Sidebar ─────────────────────────────────────────────── */}
      <aside className="w-64 bg-slate-900 text-white min-h-screen flex flex-col hidden md:flex fixed h-full z-10">
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b border-slate-800">
          <h1 className="font-bold tracking-tight text-lg flex items-center gap-2">
            <ShieldCheck className="text-emerald-400" size={20} />
            <span>
              Admin <span className="text-emerald-400">Panel</span>
            </span>
          </h1>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-6 px-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  )
                }
              >
                <Icon size={18} />
                {item.name}
              </NavLink>
            );
          })}
        </nav>

        {/* User + Logout */}
        <div className="p-4 border-t border-slate-800 space-y-2">
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-sm font-bold text-emerald-400">
              {initials}
            </div>
            <div className="text-sm overflow-hidden">
              <p className="font-medium text-white truncate">{admin?.username}</p>
              <p className="text-slate-400 text-xs truncate">{admin?.email}</p>
            </div>
          </div>
          <button
            id="admin-logout-btn"
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium text-slate-300 hover:bg-red-500/10 hover:text-red-400 transition-colors"
          >
            <LogOut size={18} />
            Cerrar sesión
          </button>
        </div>
      </aside>

      {/* ── Main content ─────────────────────────────────────────── */}
      <div className="flex flex-col flex-1 w-full md:pl-64">
        {/* Top bar */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-4 sm:px-6 z-10 sticky top-0">
          <div className="flex items-center gap-2">
            <ShieldCheck size={18} className="text-emerald-500" />
            <span className="text-sm font-semibold text-slate-700">
              Módulo Administrativo
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400 hidden sm:block">
              Sesión activa como{' '}
              <strong className="text-slate-600">{admin?.username}</strong>
            </span>
            <button
              onClick={handleLogout}
              className="md:hidden flex items-center gap-1.5 text-xs text-red-500 hover:text-red-600 transition-colors"
            >
              <LogOut size={14} />
              Salir
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-4 sm:p-6 lg:p-8">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
