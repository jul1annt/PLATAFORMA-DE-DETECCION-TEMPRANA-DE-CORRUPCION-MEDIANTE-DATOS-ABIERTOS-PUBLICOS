import React from 'react';
import { ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

type BackButtonProps = {
  fallback: string;
  label?: string;
  className?: string;
};

/** Go back inside the SPA when possible; direct links get a useful local destination. */
export const BackButton: React.FC<BackButtonProps> = ({
  fallback,
  label = 'Volver',
  className = '',
}) => {
  const navigate = useNavigate();

  const goBack = () => {
    const index = window.history.state?.idx;
    if (typeof index === 'number' && index > 0) {
      navigate(-1);
      return;
    }
    navigate(fallback, { replace: true });
  };

  return (
    <button
      type="button"
      onClick={goBack}
      className={`inline-flex shrink-0 items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition-colors hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2 ${className}`}
      aria-label={label}
    >
      <ArrowLeft size={15} aria-hidden="true" />
      <span>{label}</span>
    </button>
  );
};
