import React from 'react';
import { useNavigate } from 'react-router-dom';

export const HomePage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen font-sans text-slate-900 relative overflow-hidden bg-slate-50">
      {/* ── Mesh Gradient Background ────────────────────────────────── */}
      <div className="fixed inset-0 z-0 opacity-40 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-indigo-300 blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-violet-300 blur-[120px]" />
        <div className="absolute top-[20%] right-[10%] w-[30%] h-[30%] rounded-full bg-blue-200 blur-[100px]" />
      </div>

      {/* ── Header ──────────────────────────────────────────────────── */}
      <header className="bg-white/80 backdrop-blur-md border-b border-slate-100 sticky top-0 z-40">
        <div className="max-w-[1400px] mx-auto px-8 h-20 flex justify-between items-center">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 bg-indigo-600 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-indigo-200">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <span className="text-xl font-black text-indigo-950 tracking-tight">
              Plataforma Anticorrupción
            </span>
          </div>

          {/* Admin link */}
          <button
            id="home-admin-login-btn"
            onClick={() => navigate('/admin/login')}
            className="flex items-center gap-2 px-6 py-2.5 bg-[#05051e] text-white text-xs font-black uppercase tracking-widest rounded-full hover:bg-black transition-all shadow-xl shadow-indigo-100"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            Panel Administrativo
          </button>
        </div>
      </header>

      {/* ── Hero ────────────────────────────────────────────────────── */}
      <main className="max-w-[1400px] mx-auto px-8 relative z-10">
        <section className="pt-28 pb-20 text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-indigo-50 border border-indigo-100 rounded-full text-indigo-600 text-xs font-black uppercase tracking-widest mb-8 shadow-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
            Datos Abiertos · Colombia
          </div>

          <h1 className="text-6xl md:text-7xl font-black text-indigo-950 tracking-tighter leading-[1.05] mb-6 max-w-4xl mx-auto">
            Detección{' '}
            <span className="bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">
              Temprana
            </span>{' '}
            de Corrupción
          </h1>

          <p className="text-xl text-slate-500 font-medium max-w-2xl mx-auto mb-12 leading-relaxed">
            Plataforma de inteligencia de datos que analiza contratación pública,
            detecta anomalías y genera alertas de riesgo en tiempo real a partir de
            fuentes de datos abiertos.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              id="home-procesados-btn"
              onClick={() => navigate('/public/procesados')}
              className="flex items-center gap-3 px-8 py-4 bg-indigo-600 text-white text-sm font-black uppercase tracking-widest rounded-2xl hover:bg-indigo-700 active:scale-95 transition-all shadow-2xl shadow-indigo-300/50"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              Ir a Procesados
            </button>

            <button
              id="home-admin-btn"
              onClick={() => navigate('/admin/login')}
              className="flex items-center gap-3 px-8 py-4 bg-white text-slate-700 text-sm font-black uppercase tracking-widest rounded-2xl hover:bg-slate-50 active:scale-95 transition-all shadow-lg border border-slate-200"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              Panel Administrativo
            </button>
          </div>
        </section>

        {/* ── Feature Cards ────────────────────────────────────────── */}
        <section className="pb-24 grid md:grid-cols-3 gap-6">
          {/* Card 1 */}
          <div className="bg-white/70 backdrop-blur-sm border border-slate-100 rounded-3xl p-8 shadow-xl shadow-indigo-100/20 hover:shadow-2xl hover:shadow-indigo-100/30 hover:-translate-y-1 transition-all duration-300">
            <div className="w-12 h-12 bg-indigo-50 rounded-2xl flex items-center justify-center text-indigo-600 mb-5 shadow-inner">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
              </svg>
            </div>
            <h3 className="text-lg font-black text-indigo-950 mb-2 tracking-tight">Datos Abiertos</h3>
            <p className="text-slate-500 text-sm leading-relaxed">
              Ingesta y normalización automática de contratos públicos desde el SECOP y otras fuentes oficiales del estado colombiano.
            </p>
          </div>

          {/* Card 2 */}
          <div className="bg-white/70 backdrop-blur-sm border border-slate-100 rounded-3xl p-8 shadow-xl shadow-violet-100/20 hover:shadow-2xl hover:shadow-violet-100/30 hover:-translate-y-1 transition-all duration-300">
            <div className="w-12 h-12 bg-violet-50 rounded-2xl flex items-center justify-center text-violet-600 mb-5 shadow-inner">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <h3 className="text-lg font-black text-indigo-950 mb-2 tracking-tight">Análisis de Riesgo</h3>
            <p className="text-slate-500 text-sm leading-relaxed">
              Motor de análisis que detecta anomalías, registros incompletos y patrones sospechosos de corrupción en tiempo real.
            </p>
          </div>

          {/* Card 3 */}
          <div className="bg-white/70 backdrop-blur-sm border border-slate-100 rounded-3xl p-8 shadow-xl shadow-emerald-100/20 hover:shadow-2xl hover:shadow-emerald-100/30 hover:-translate-y-1 transition-all duration-300">
            <div className="w-12 h-12 bg-emerald-50 rounded-2xl flex items-center justify-center text-emerald-600 mb-5 shadow-inner">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-black text-indigo-950 mb-2 tracking-tight">Transparencia Pública</h3>
            <p className="text-slate-500 text-sm leading-relaxed">
              Resultados accesibles para ciudadanos, periodistas e investigadores sin necesidad de autenticación.
            </p>
          </div>
        </section>
      </main>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <footer className="border-t border-slate-100 bg-white/50 backdrop-blur-sm relative z-10">
        <div className="max-w-[1400px] mx-auto px-8 py-6 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">
            Plataforma Anticorrupción · Datos Abiertos Públicos
          </span>
          <span className="text-xs text-slate-300 font-medium">
            Universidad El Bosque · {new Date().getFullYear()}
          </span>
        </div>
      </footer>
    </div>
  );
};
