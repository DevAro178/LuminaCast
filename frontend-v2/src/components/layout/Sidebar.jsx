import React from 'react';
import { LayoutDashboard, Film, FileVideo, Settings, User } from 'lucide-react';
import clsx from 'clsx';
import useStore from '../../store/useStore';

export default function Sidebar() {
  const activeTab = useStore(state => state.activeTab);
  const setActiveTab = useStore(state => state.setActiveTab);

  const tabs = [
    { id: 'create', icon: FileVideo, label: 'Create' },
    { id: 'jobs', icon: LayoutDashboard, label: 'Jobs' },
    { id: 'library', icon: Film, label: 'Library' },
  ];

  return (
    <aside className="fixed left-6 top-6 bottom-6 w-20 bg-card rounded-[32px] flex flex-col items-center py-8 z-50">
      {/* Logo Placeholder */}
      <div className="w-10 h-10 bg-accent rounded-full mb-12 flex items-center justify-center">
        <span className="text-white font-display font-bold text-xl">L</span>
      </div>

      {/* Nav Actions */}
      <nav className="flex flex-col gap-6 flex-1">
        {tabs.map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                "w-12 h-12 rounded-2xl flex items-center justify-center transition-all duration-200 group relative",
                isActive ? "bg-surface text-background shadow-md" : "text-textSecondary hover:text-white hover:bg-white/5"
              )}
            >
              <Icon size={22} strokeWidth={isActive ? 2.5 : 2} />
              
              {/* Tooltip */}
              <span className="absolute left-16 opacity-0 group-hover:opacity-100 bg-card text-white text-xs px-3 py-2 rounded-lg transition-opacity pointer-events-none whitespace-nowrap shadow-xl z-50">
                {tab.label}
              </span>
            </button>
          );
        })}
      </nav>

      {/* Bottom Actions */}
      <div className="flex flex-col gap-6 mt-auto items-center">
        <button className="text-textSecondary hover:text-white transition-colors">
          <Settings size={22} />
        </button>
        <div className="w-10 h-10 bg-white/10 rounded-full overflow-hidden flex items-center justify-center">
          <User size={22} className="text-textSecondary" />
        </div>
      </div>
    </aside>
  );
}
