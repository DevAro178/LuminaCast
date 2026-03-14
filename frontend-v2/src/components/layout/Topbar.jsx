import React from 'react';
import { Search } from 'lucide-react';

export default function Topbar() {
  return (
    <header className="flex justify-between items-center mb-8">
      {/* Search */}
      <div className="relative">
        <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none z-10 text-background/50">
          <Search size={18} />
        </div>
        <input 
          type="text" 
          placeholder="SEARCH VIDEOS..." 
          className="pl-12 pr-6 py-4 bg-surface/90 backdrop-blur-md rounded-full text-sm font-bold tracking-wider text-background placeholder:text-background/50 outline-none w-64 shadow-lg focus:w-80 transition-all duration-300"
        />
      </div>
    </header>
  );
}
