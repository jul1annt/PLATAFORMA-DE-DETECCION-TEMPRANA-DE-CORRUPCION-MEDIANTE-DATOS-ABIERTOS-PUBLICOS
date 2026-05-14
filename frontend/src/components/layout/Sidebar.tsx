import React from 'react';
import { NavLink } from 'react-router-dom';
import { Database, LayoutDashboard, Settings, ShieldAlert } from 'lucide-react';
import { cn } from '../../utils/utils';

export const Sidebar: React.FC = () => {
  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Fuentes de Datos', path: '/fuentes', icon: Database },
    { name: 'Calidad de Datos', path: '/calidad', icon: ShieldAlert },
    { name: 'Configuración', path: '/configuracion', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-white min-h-screen flex flex-col hidden md:flex fixed h-full z-10">
      <div className="h-16 flex items-center px-6 border-b border-slate-800">
        <h1 className="font-bold tracking-tight text-lg flex items-center gap-2">
          <Database className="text-emerald-400" size={20} />
          Anti-Corrupción
        </h1>
      </div>
      
      <nav className="flex-1 py-6 px-3 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
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
      
      <div className="p-4 border-t border-slate-800">
        <div className="flex items-center gap-3 px-2 py-2">
          <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-sm font-medium">
            AD
          </div>
          <div className="text-sm">
            <p className="font-medium text-white">Admin</p>
            <p className="text-slate-400 text-xs">admin@plataforma.com</p>
          </div>
        </div>
      </div>
    </aside>
  );
};
