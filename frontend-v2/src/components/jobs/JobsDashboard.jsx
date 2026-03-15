import React, { useEffect, useState } from 'react';
import useStore from '../../store/useStore';
import Button from '../ui/Button';
import { jobsApi } from '../../api/jobs';

const PENDING_STATUSES = ['script_review', 'visual_review'];

function getStatusColor(status) {
  if (status === 'completed') return 'bg-green-500';
  if (status === 'error' || status === 'failed') return 'bg-red-500';
  if (PENDING_STATUSES.includes(status)) return 'bg-yellow-400';
  return 'bg-accent animate-pulse';
}

function getStatusLabel(status) {
  if (status === 'script_review') return 'AWAITING SCRIPT REVIEW';
  if (status === 'visual_review') return 'AWAITING VISUAL REVIEW';
  return status.replace(/_/g, ' ').toUpperCase();
}

export default function JobsDashboard() {
  const setActiveTab = useStore(state => state.setActiveTab);
  const searchQuery = useStore(state => state.searchQuery);
  const resumeJob = useStore(state => state.resumeJob);
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

  const filteredJobs = jobs.filter(job =>
    job.topic.toLowerCase().includes(searchQuery.toLowerCase()) ||
    job.status.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="animate-in fade-in duration-300">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-display font-black tracking-tight uppercase">
          {searchQuery ? `SEARCH: "${searchQuery}"` : "ACTIVE JOBS"}
        </h2>
        <span className="text-xs font-display font-bold text-textSecondary bg-surface/10 px-3 py-1 rounded-full">
          {filteredJobs.length} TOTAL
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {filteredJobs.length === 0 ? (
          <div className="bento-card p-12 flex flex-col items-center justify-center opacity-50 border-dashed border-white/10">
            <p className="text-sm font-medium">No {searchQuery ? "matching" : "active"} jobs found.</p>
          </div>
        ) : filteredJobs.map(job => {
          const isPendingReview = PENDING_STATUSES.includes(job.status);

          return (
            <div
              key={job.id}
              className={`bento-card p-6 flex flex-row items-center gap-8 relative overflow-hidden group transition-all duration-300 ${isPendingReview ? 'border-yellow-400/20 hover:border-yellow-400/50' : 'hover:border-accent/30'}`}
            >
              {/* Progress Circle */}
              <div className="w-16 h-16 relative flex-shrink-0">
                <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="45" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="10" />
                  <circle
                    cx="50" cy="50" r="45" fill="none"
                    stroke="currentColor" strokeWidth="10"
                    className={`transition-all duration-500 ease-out ${isPendingReview ? 'text-yellow-400' : 'text-accent'}`}
                    strokeDasharray="283"
                    strokeDashoffset={283 - (283 * (job.progress_pct || 0)) / 100}
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center font-display font-black text-sm text-white">
                  {job.progress_pct}%
                </div>
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <h3 className="text-xl font-display font-black text-white mb-1 truncate group-hover:text-accent transition-colors">
                  {job.topic}
                </h3>
                <div className="flex flex-wrap items-center gap-3">
                  <p className="text-textSecondary text-xs font-display font-bold uppercase tracking-widest flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full flex-shrink-0 ${getStatusColor(job.status)}`} />
                    {getStatusLabel(job.status)}
                  </p>
                  {isPendingReview && (
                    <span className="text-[10px] font-display font-black text-yellow-400 bg-yellow-400/10 px-2 py-0.5 rounded-full uppercase tracking-widest">
                      YOUR ACTION NEEDED
                    </span>
                  )}
                  {job.error_message && (
                    <span className="text-[10px] text-red-400 font-mono bg-red-400/10 px-2 py-0.5 rounded">
                      {job.error_message.slice(0, 60)}
                    </span>
                  )}
                </div>
                <p className="text-[10px] font-mono text-textSecondary/30 mt-2">ID: {job.id}</p>
              </div>

              {/* Actions */}
              <div className="flex gap-3 flex-shrink-0">
                {isPendingReview && (
                  <Button
                    variant="outline"
                    className="px-6 py-2 text-xs font-display font-black tracking-widest border-yellow-400/40 text-yellow-300 hover:bg-yellow-400/10"
                    onClick={() => resumeJob(job.id)}
                  >
                    RESUME
                  </Button>
                )}
                {job.status === 'completed' && (
                  <Button
                    variant="accent"
                    className="px-6 py-2 text-xs font-display font-black shadow-lg shadow-accent/20"
                    onClick={() => useStore.setState({ activeTab: 'library', currentJobId: job.id })}
                  >
                    VIEW VIDEO
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
