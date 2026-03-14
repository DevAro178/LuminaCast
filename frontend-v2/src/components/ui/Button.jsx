import React from 'react';
import clsx from 'clsx';

export default function Button({ 
  children, 
  onClick, 
  variant = 'primary', // 'primary', 'secondary', 'outline', 'ghost'
  className,
  disabled = false,
  ...props 
}) {
  const baseStyles = "px-8 py-4 font-bold tracking-wider rounded-full transition-all flex items-center justify-center gap-2";
  
  const variants = {
    primary: "bg-background text-surface hover:bg-card disabled:opacity-50",
    secondary: "bg-surface text-background shadow-lg scale-105 hover:scale-100 disabled:opacity-50",
    accent: "bg-accent/80 text-white shadow-lg shadow-accent/20 border-2 border-accent hover:bg-accent disabled:opacity-50",
    outline: "bg-transparent border-2 border-white/20 text-textSecondary hover:text-white hover:border-white text-sm disabled:opacity-50",
    ghost: "bg-transparent text-textSecondary hover:text-white hover:bg-white/5 px-4 py-2 border border-transparent disabled:opacity-50"
  };

  return (
    <button 
      onClick={onClick}
      disabled={disabled}
      className={clsx(baseStyles, variants[variant], className)}
      {...props}
    >
      {children}
    </button>
  );
}
