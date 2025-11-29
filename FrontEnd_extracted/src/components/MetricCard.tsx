import React from 'react';

interface MetricCardProps {
  title: string;
  value: number | string;
  label: string;
  isUrgent?: boolean;
}

export function MetricCard({ title, value, label, isUrgent = false }: MetricCardProps) {
  return (
    <div className="bg-white border border-[var(--color-border)] rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
      <p className="text-[var(--color-text-secondary)] text-xs mb-2">{title}</p>
      <div className="flex items-end gap-2">
        <p className={`text-3xl ${isUrgent ? 'text-[var(--color-urgent)]' : 'text-[var(--color-text-main)]'}`}>
          {value.toLocaleString()}
        </p>
        {isUrgent && (
          <div className="bg-[var(--color-urgent)] text-white text-xs px-2 py-0.5 rounded mb-1">
            {label}
          </div>
        )}
      </div>
      {!isUrgent && (
        <p className="text-[var(--color-text-secondary)] text-xs mt-1">{label}</p>
      )}
    </div>
  );
}
