import React, { useEffect, useState } from 'react';
import useStore from '../../store/useStore';
import Button from '../ui/Button';
import { jobsApi } from '../../api/jobs';

export default function JobsDashboard() {
  const setActiveTab = useStore(state => state.setActiveTab);
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

  return (
    <div className="animate-in fade-in duration-300">
      <h2 className="text-2xl font-black tracking-tight mb-6">ACTIVE JOBS</h2>
      
      <div className="grid grid-cols-1 gap-4">
        {jobs.length === 0 ? (
          <div className="bento-card p-12 flex flex-col items-center justify-center opacity-50">
            <p>No jobs found.</p>
          </div>
        ) : jobs.map(job => (
          <div key={job.id} className="bento-card p-6 flex flex-row items-center gap-8 relative overflow-hidden">
            <div className="w-16 h-16 relative flex-shrink-0">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="45" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="10" />
                <circle 
                  cx="50" cy="50" r="45" fill="none" 
                  stroke="currentColor" strokeWidth="10" 
                  className="text-accent transition-all duration-300" 
                  strokeDasharray="283" 
                  strokeDashoffset={283 - (283 * (job.progress_pct || 0)) / 100} 
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center font-black text-sm text-white">
                {job.progress_pct}%
              </div>
            </div>
            
            <div className="flex-1">
              <h3 className="text-xl font-black text-white mb-1">{job.topic}</h3>
              <p className="text-textSecondary text-sm font-medium uppercase tracking-tighter">
                {job.status.replace('_', ' ')} 
                {job.status !== 'completed' && job.status !== 'failed' && "..."}
              </p>
            </div>
            
            <div className="flex gap-4">
               {job.status === 'completed' && (
                 <Button 
                    variant="accent"
                    className="px-6 py-2 text-xs"
                    onClick={() => setActiveTab('library')}
                  >
                    VIEW VIDEO
                  </Button>
               )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
