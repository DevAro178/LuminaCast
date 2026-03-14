import React, { useEffect, useState } from 'react';
import useStore from '../../store/useStore';
import Button from '../ui/Button';
import { jobsApi } from '../../api/jobs';

export default function JobsDashboard() {
  const setActiveTab = useStore(state => state.setActiveTab);
  const searchQuery = useStore(state => state.searchQuery);
  const [jobs, setJobs] = useState([]);

  const fetchJobs = async () => {
    try {
      const data = await jobsApi.listJobs();
      setJobs(data);
    } catch (error) {
      console.error("Failed to fetch jobs:", error);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, []);

  // Filtering logic
  const filteredJobs = jobs.filter(job => 
    job.topic.toLowerCase().includes(searchQuery.toLowerCase()) || 
    job.status.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="animate-in fade-in duration-300">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-black tracking-tight uppercase">
          {searchQuery ? `SEARCH RESULTS: "${searchQuery}"` : "ACTIVE JOBS"}
        </h2>
        <span className="text-xs font-bold text-textSecondary bg-surface/10 px-3 py-1 rounded-full">
          {filteredJobs.length} TOTAL
        </span>
      </div>
      
      <div className="grid grid-cols-1 gap-4">
        {filteredJobs.length === 0 ? (
          <div className="bento-card p-12 flex flex-col items-center justify-center opacity-50 border-dashed border-white/10">
            <p className="text-sm font-medium">No {searchQuery ? "matching" : "active"} jobs found.</p>
          </div>
        ) : filteredJobs.map(job => (
          <div key={job.id} className="bento-card p-6 flex flex-row items-center gap-8 relative overflow-hidden group hover:border-accent/30 transition-all duration-300">
            {/* Progress Circle */}
            <div className="w-16 h-16 relative flex-shrink-0">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="45" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="10" />
                <circle 
                  cx="50" cy="50" r="45" fill="none" 
                  stroke="currentColor" strokeWidth="10" 
                  className="text-accent transition-all duration-500 ease-out" 
                  strokeDasharray="283" 
                  strokeDashoffset={283 - (283 * (job.progress_pct || 0)) / 100} 
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center font-black text-sm text-white">
                {job.progress_pct}%
              </div>
            </div>
            
            <div className="flex-1">
              <h3 className="text-xl font-black text-white mb-1 group-hover:text-accent transition-colors">{job.topic}</h3>
              <div className="flex items-center gap-3">
                <p className="text-textSecondary text-xs font-bold uppercase tracking-widest flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${job.status === 'completed' ? 'bg-green-500' : 'bg-accent animate-pulse'}`} />
                  {job.status.replace(/_/g, ' ')}
                </p>
                {job.error_message && (
                  <span className="text-[10px] text-red-400 font-mono bg-red-400/10 px-2 py-0.5 rounded">
                    Error: {job.error_message}
                  </span>
                )}
              </div>
            </div>
            
            <div className="flex gap-4">
               {job.status === 'completed' && (
                 <Button 
                    variant="accent"
                    className="px-6 py-2 text-xs font-black shadow-lg shadow-accent/20"
                    onClick={() => {
                        // We'll set a local storage or store state for the player to pick up
                        useStore.setState({ activeTab: 'library', currentJobId: job.id });
                    }}
                  >
                    VIEW VIDEO
                  </Button>
               )}
               <div className="text-[10px] font-mono text-textSecondary opacity-30 mt-auto">
                 ID: {job.id}
               </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
