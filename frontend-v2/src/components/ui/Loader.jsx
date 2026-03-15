import React from 'react';
import clsx from 'clsx';

export default function Loader({ 
  title = "LOADING...", 
  message = "Please wait", 
  fullScreen = false
}) {
  return (
    <div className={clsx(
      "flex flex-col items-center justify-center animate-in fade-in duration-300 z-50",
      fullScreen ? "absolute inset-0 bg-background/95 backdrop-blur-sm" : "py-20"
    )}>
      <div className={clsx(
        "border-4 rounded-full animate-spin mb-4",
        fullScreen ? "w-12 h-12 border-surface/10 border-t-accent" : "w-16 h-16 border-surface/20 border-t-accent"
      )}></div>
      <h3 className={clsx(
        "font-black mb-2 tracking-tight",
        fullScreen ? "text-white text-lg" : "text-white text-2xl"
      )}>
        {title}
      </h3>
      <p className={clsx(
        "text-sm font-bold",
        fullScreen ? "text-textSecondary" : "text-textSecondary"
      )}>
        {message}
      </p>
    </div>
  );
}
