import React from 'react';
import useStore from './store/useStore';

// Layout
import Sidebar from './components/layout/Sidebar';
import Topbar from './components/layout/Topbar';

// Feature Modules
import MainHero from './components/create/MainHero';
import ContentGrid from './components/create/ContentGrid';
import JobsDashboard from './components/jobs/JobsDashboard';
import MediaLibrary from './components/library/MediaLibrary';

function App() {
  const activeTab = useStore(state => state.activeTab);

  return (
    <div className="min-h-screen bg-background text-textPrimary selection:bg-accent/30 selection:text-white">
      <Sidebar />
      
      <main className="ml-32 min-h-screen p-6 max-w-[1600px] mx-auto">
        <Topbar />
        
        {activeTab === 'create' && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out flex flex-col h-full">
            <MainHero />
            <ContentGrid />
          </div>
        )}
        
        {activeTab === 'jobs' && (
          <JobsDashboard />
        )}
        
        {activeTab === 'library' && (
          <MediaLibrary />
        )}
      </main>
    </div>
  );
}

export default App;
