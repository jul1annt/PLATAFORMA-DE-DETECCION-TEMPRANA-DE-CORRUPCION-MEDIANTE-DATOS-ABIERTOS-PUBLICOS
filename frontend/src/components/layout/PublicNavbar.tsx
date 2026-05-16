import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

export const PublicNavbar: React.FC = () => {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const isActive = (path: string) =>
    pathname === path || pathname.startsWith(path + '/');

  return (
    <header className="sticky top-0 z-40 bg-white/70 backdrop-blur-xl border-b border-white/60 shadow-sm shadow-indigo-100/20">
      <div className="max-w-[1400px] mx-auto px-6 md:px-8 h-18 md:h-20 flex justify-between items-center gap-4 py-3">

        {/* ── Logo ────────────────────────────────────────────────────────── */}
        <button
          onClick={() => navigate('/public/dashboard')}
          className="flex items-center gap-3 flex-shrink-0 group"
        >
          <div className="w-10 h-10 md:w-11 md:h-11 bg-gradient-to-br from-indigo-600 to-violet-600 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-indigo-300/40 group-hover:scale-105 transition-transform">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 md:h-6 md:w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <div className="hidden sm:block">
            <span className="text-base md:text-lg font-black text-indigo-950 tracking-tight block leading-none">
              Plataforma Anticorrupción
            </span>
            <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest">
              Observatorio de Transparencia
            </span>
          </div>
        </button>

        {/* ── Nav Links ───────────────────────────────────────────────────── */}
        <nav className="flex items-center gap-1 md:gap-2">
          {/* Dashboard */}
          <button
            id="public-nav-dashboard"
            onClick={() => navigate('/public/dashboard')}
            className={`flex items-center gap-1.5 px-3 md:px-5 py-2 md:py-2.5 rounded-full text-xs font-black uppercase tracking-widest transition-all ${
              isActive('/public/dashboard')
                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-200'
                : 'text-slate-500 hover:text-indigo-700 hover:bg-indigo-50'
            }`}
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5 md:h-4 md:w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
            <span className="hidden md:inline">Dashboard</span>
          </button>

          {/* Contratos */}
          <button
            id="public-nav-contratos"
            onClick={() => navigate('/public/procesados')}
            className={`flex items-center gap-1.5 px-3 md:px-5 py-2 md:py-2.5 rounded-full text-xs font-black uppercase tracking-widest transition-all ${
              isActive('/public/procesados')
                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-200'
                : 'text-slate-500 hover:text-indigo-700 hover:bg-indigo-50'
            }`}
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5 md:h-4 md:w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span className="hidden md:inline">Contratos</span>
          </button>

          {/* Divider */}
          <div className="w-px h-6 bg-slate-200 mx-1 hidden md:block" />

          {/* Admin */}
          <button
            id="public-nav-admin"
            onClick={() => navigate('/admin/login')}
            className="flex items-center gap-1.5 px-3 md:px-5 py-2 md:py-2.5 bg-slate-900 text-white rounded-full text-xs font-black uppercase tracking-widest hover:bg-indigo-700 transition-all shadow-md shadow-slate-300/30"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5 md:h-4 md:w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            <span className="hidden sm:inline">Admin</span>
          </button>
        </nav>
      </div>
    </header>
  );
};
