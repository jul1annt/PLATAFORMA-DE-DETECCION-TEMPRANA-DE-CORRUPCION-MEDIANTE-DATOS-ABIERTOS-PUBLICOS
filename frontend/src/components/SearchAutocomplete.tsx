import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getAutocompleteSuggestions, type Suggestion } from '../services/procesadosService';
import type { Procesado } from '../types/procesado';

interface SearchAutocompleteProps {
  data: Procesado[];
}

export const SearchAutocomplete: React.FC<SearchAutocompleteProps> = ({ data }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') || '';

  const [query, setQuery] = useState(initialQuery);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Sync state with URL if URL changes externally
  useEffect(() => {
    setQuery(searchParams.get('q') || '');
  }, [searchParams]);

  // Debounced search for suggestions
  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      if (query.trim().length >= 2) {
        const results = getAutocompleteSuggestions(query, data);
        setSuggestions(results);
        setIsOpen(results.length > 0);
      } else {
        setSuggestions([]);
        setIsOpen(false);
      }
      setFocusedIndex(-1);
    }, 200);

    return () => clearTimeout(delayDebounceFn);
  }, [query, data]);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [wrapperRef]);

  const handleSelect = (text: string) => {
    setQuery(text);
    setIsOpen(false);
    updateSearchParams(text);
  };

  const updateSearchParams = (text: string) => {
    const params = new URLSearchParams(searchParams);
    if (text) {
      params.set('q', text);
    } else {
      params.delete('q');
    }
    setSearchParams(params);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setFocusedIndex((prev) => (prev < suggestions.length - 1 ? prev + 1 : prev));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setFocusedIndex((prev) => (prev > 0 ? prev - 1 : -1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (focusedIndex >= 0 && focusedIndex < suggestions.length) {
        handleSelect(suggestions[focusedIndex].text);
      } else {
        // Just search whatever is typed
        setIsOpen(false);
        updateSearchParams(query);
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  const highlightMatch = (text: string, match: string) => {
    if (!match) return text;
    // Escapar caracteres especiales de regex
    const escapedMatch = match.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const parts = text.split(new RegExp(`(${escapedMatch})`, 'gi'));
    return (
      <>
        {parts.map((part, i) =>
          part.toLowerCase() === match.toLowerCase() ? (
            <span key={i} className="text-indigo-600 bg-indigo-50 font-black rounded-sm px-0.5">{part}</span>
          ) : (
            <span key={i}>{part}</span>
          )
        )}
      </>
    );
  };

  return (
    <div ref={wrapperRef} className="relative w-full max-w-2xl mx-auto mb-8 z-30">
      <div className="relative group">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-indigo-400 group-focus-within:text-indigo-600 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <input
          type="text"
          className="w-full pl-12 pr-12 py-4 bg-white/70 backdrop-blur-xl border border-slate-200 rounded-2xl shadow-sm text-slate-700 font-bold placeholder-slate-400 focus:outline-none focus:ring-4 focus:ring-indigo-500/20 focus:border-indigo-500 focus:bg-white transition-all text-lg"
          placeholder="Buscar entidad o proveedor..."
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            if (e.target.value === '') updateSearchParams('');
          }}
          onFocus={() => {
            if (suggestions.length > 0) setIsOpen(true);
          }}
          onKeyDown={handleKeyDown}
        />
        {query && (
          <button
            onClick={() => {
              setQuery('');
              updateSearchParams('');
              setIsOpen(false);
            }}
            className="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-400 hover:text-slate-600 transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 bg-slate-100 rounded-full p-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {isOpen && (
        <div className="absolute w-full mt-2 bg-white/90 backdrop-blur-2xl border border-slate-100 rounded-2xl shadow-2xl overflow-hidden py-2 animate-in fade-in slide-in-from-top-2">
          {suggestions.map((suggestion, index) => (
            <div
              key={index}
              onClick={() => handleSelect(suggestion.text)}
              className={`px-4 py-3 cursor-pointer flex items-center justify-between transition-colors ${
                focusedIndex === index ? 'bg-indigo-50/80' : 'hover:bg-slate-50'
              }`}
            >
              <div className="flex items-center gap-3 overflow-hidden">
                <div className={`shrink-0 w-8 h-8 rounded-xl flex items-center justify-center text-xs shadow-sm ${
                  suggestion.type === 'ENTIDAD' ? 'bg-emerald-100 text-emerald-600' : 'bg-violet-100 text-violet-600'
                }`}>
                  {suggestion.type === 'ENTIDAD' ? '🏢' : '👤'}
                </div>
                <div className="text-sm font-bold text-slate-700 truncate">
                  {highlightMatch(suggestion.text, query.trim())}
                </div>
              </div>
              <span className={`text-[9px] font-black tracking-widest uppercase px-2 py-1 rounded-md shrink-0 ${
                suggestion.type === 'ENTIDAD' ? 'bg-emerald-50 text-emerald-500' : 'bg-violet-50 text-violet-500'
              }`}>
                {suggestion.type}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
