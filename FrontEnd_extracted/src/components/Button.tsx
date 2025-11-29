import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'outline';
  children: React.ReactNode;
}

export function Button({ variant = 'primary', children, className = '', disabled, ...props }: ButtonProps) {
  const baseStyles = 'px-4 py-2 rounded-lg transition-all duration-200 inline-flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed';
  
  const variants = {
    primary: 'bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-hover)] disabled:hover:bg-[var(--color-primary)]',
    secondary: 'bg-[var(--color-hover-bg)] text-[var(--color-text-main)] hover:bg-[var(--color-neutral-badge)] disabled:hover:bg-[var(--color-hover-bg)]',
    ghost: 'bg-transparent text-[var(--color-text-main)] hover:bg-[var(--color-hover-bg)] disabled:hover:bg-transparent',
    outline: 'bg-transparent border-2 border-white text-white hover:bg-white/10 disabled:hover:bg-transparent'
  };

  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${className}`}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
}
