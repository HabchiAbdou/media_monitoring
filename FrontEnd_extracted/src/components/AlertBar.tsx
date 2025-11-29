import React from 'react';
import { X, Info, CheckCircle, AlertCircle } from 'lucide-react';

interface AlertBarProps {
  variant: 'info' | 'success' | 'error';
  message: string;
  onClose: () => void;
}

export function AlertBar({ variant, message, onClose }: AlertBarProps) {
  const variants = {
    info: {
      bg: 'bg-[var(--color-alert-info-bg)]',
      border: 'border-[var(--color-alert-info)]',
      text: 'text-[var(--color-alert-info)]',
      icon: Info
    },
    success: {
      bg: 'bg-[var(--color-alert-success-bg)]',
      border: 'border-[var(--color-alert-success)]',
      text: 'text-[var(--color-alert-success)]',
      icon: CheckCircle
    },
    error: {
      bg: 'bg-[var(--color-alert-error-bg)]',
      border: 'border-[var(--color-alert-error)]',
      text: 'text-[var(--color-alert-error)]',
      icon: AlertCircle
    }
  };

  const config = variants[variant];
  const Icon = config.icon;

  return (
    <div className={`${config.bg} border-l-4 ${config.border} p-4 flex items-center justify-between gap-4`}>
      <div className="flex items-center gap-3">
        <Icon className={`w-5 h-5 ${config.text} flex-shrink-0`} />
        <p className={`${config.text} text-sm`}>{message}</p>
      </div>
      <button
        onClick={onClose}
        className={`${config.text} hover:opacity-70 transition-opacity flex-shrink-0`}
        aria-label="Close alert"
      >
        <X className="w-5 h-5" />
      </button>
    </div>
  );
}
