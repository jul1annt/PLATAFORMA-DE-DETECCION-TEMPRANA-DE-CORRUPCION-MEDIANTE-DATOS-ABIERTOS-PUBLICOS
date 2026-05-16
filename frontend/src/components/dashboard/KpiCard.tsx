import React from 'react';

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  gradient: string;
  border: string;
  textColor: string;
  badgeColor: string;
  badge?: string;
  onClick?: () => void;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  gradient,
  border,
  textColor,
  badgeColor,
  badge,
  onClick,
}) => {
  return (
    <div
      onClick={onClick}
      className={`
        relative overflow-hidden rounded-[28px] p-7
        ${gradient} ${border} border
        shadow-xl transition-all duration-300
        ${onClick ? 'cursor-pointer hover:scale-[1.02] hover:shadow-2xl' : ''}
      `}
    >
      {/* Background glow */}
      <div className="absolute inset-0 opacity-20 pointer-events-none">
        <div className="absolute -top-10 -right-10 w-40 h-40 rounded-full bg-white blur-3xl" />
      </div>

      <div className="relative z-10">
        {/* Header */}
        <div className="flex items-start justify-between mb-5">
          <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${badgeColor} shadow-lg`}>
            {icon}
          </div>
          {badge && (
            <span className={`text-[10px] font-black uppercase tracking-widest px-3 py-1.5 rounded-full ${badgeColor} ${textColor} opacity-80`}>
              {badge}
            </span>
          )}
        </div>

        {/* Value */}
        <p className={`text-5xl font-black tracking-tighter mb-1 ${textColor}`}>
          {value}
        </p>

        {/* Title */}
        <p className={`text-xs font-black uppercase tracking-widest mb-1 ${textColor} opacity-70`}>
          {title}
        </p>

        {/* Subtitle */}
        {subtitle && (
          <p className={`text-xs font-medium ${textColor} opacity-50 mt-2`}>
            {subtitle}
          </p>
        )}
      </div>
    </div>
  );
};
