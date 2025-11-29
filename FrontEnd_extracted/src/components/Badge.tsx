import React from 'react';

interface BadgeProps {
  variant: 'press' | 'social' | 'youtube' | 'positive' | 'negative' | 'neutral' | 'urgent';
  children: React.ReactNode;
  className?: string;
}

export function Badge({ variant, children, className = '' }: BadgeProps) {
  const baseStyles = 'inline-flex items-center px-2.5 py-0.5 rounded-md text-xs';
  
  const variants = {
    press: 'bg-blue-100 text-[var(--color-press)]',
    social: 'bg-purple-100 text-[var(--color-social)]',
    youtube: 'bg-red-100 text-[var(--color-youtube)]',
    positive: 'bg-green-100 text-[var(--color-positive)]',
    negative: 'bg-red-100 text-[var(--color-urgent)]',
    neutral: 'bg-[var(--color-neutral-badge)] text-[var(--color-text-secondary)]',
    urgent: 'bg-[var(--color-urgent)] text-white'
  };

  return (
    <span className={`${baseStyles} ${variants[variant]} ${className}`}>
      {children}
    </span>
  );
}
