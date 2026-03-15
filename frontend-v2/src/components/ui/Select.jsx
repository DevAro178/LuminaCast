import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import clsx from 'clsx';

export default function Select({ 
  value, 
  onChange, 
  options = [], 
  className 
}) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  const selectedOption = options.find(opt => opt.value === value) || options[0];

  // Close when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className={clsx("relative inline-block text-left", className)} ref={containerRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="bg-white/5 text-white px-6 py-2.5 rounded-full text-sm font-bold flex items-center gap-3 hover:bg-white/10 transition-all active:scale-95 outline-none border border-white/10"
      >
        <span>{selectedOption?.label}</span>
        <ChevronDown 
          size={16} 
          className={clsx("transition-transform duration-300", isOpen && "rotate-180")} 
        />
      </button>

      {isOpen && (
        <div className="absolute left-0 bottom-full mb-2 w-full min-w-[200px] bg-background/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl z-[100] overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-200">
          <div className="py-1">
            {options.map((opt) => (
              <button
                key={opt.value}
                onClick={() => {
                  onChange(opt.value);
                  setIsOpen(false);
                }}
                className={clsx(
                  "w-full text-left px-5 py-3 text-sm font-bold transition-colors flex items-center justify-between",
                  value === opt.value 
                    ? "bg-accent text-white" 
                    : "text-white/70 hover:bg-white/5 hover:text-white"
                )}
              >
                {opt.label}
                {value === opt.value && (
                   <div className="w-1.5 h-1.5 bg-white rounded-full"></div>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
