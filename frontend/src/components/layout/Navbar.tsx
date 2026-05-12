import React from 'react';
import { Bell, Search, Menu } from 'lucide-react';

export const Navbar: React.FC = () => {
  return (
    <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-4 sm:px-6 z-10 sticky top-0">
      <div className="flex items-center gap-4">
        <button className="md:hidden text-slate-500 hover:text-slate-700">
          <Menu size={20} />
        </button>
        <div className="hidden sm:flex items-center text-slate-500 bg-slate-100 rounded-md px-3 py-1.5 focus-within:ring-2 focus-within:ring-slate-900 focus-within:bg-white transition-colors">
          <Search size={16} className="mr-2" />
          <input 
            type="text" 
            placeholder="Buscar fuentes..." 
            className="bg-transparent border-none outline-none text-sm w-64 placeholder:text-slate-500"
          />
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        <button className="relative p-2 text-slate-500 hover:bg-slate-100 rounded-full transition-colors">
          <Bell size={20} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
        </button>
      </div>
    </header>
  );
};
