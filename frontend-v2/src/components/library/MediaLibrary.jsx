import React, { useEffect, useState } from 'react';
import useStore from '../../store/useStore';
import { Play, Download, Trash2, ExternalLink } from 'lucide-react';
import { jobsApi } from '../../api/jobs';
import config from '../../config';
import Button from '../ui/Button';

export default function MediaLibrary() {
  const [jobs, setJobs] = useState([]);
  const currentJobId = useStore(state => state.currentJobId);
  const [selectedJob, setSelectedJob] = useState(null);

  const fetchJobs = async () => {
    try {
      const data = await jobsApi.listJobs();
      const completed = data.filter(j => j.status === 'completed');
      setJobs(completed);
      
      // Auto-select the job redirected from Jobs dashboard if any
      if (currentJobId && !selectedJob) {
        const target = completed.find(j => j.id === currentJobId);
        if (target) setSelectedJob(target);
      }
    } catch (error) {
      console.error("Failed to fetch jobs:", error);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [currentJobId]);

  const getDownloadUrl = (jobId) => `${config.apiBaseUrl}/api/jobs/${jobId}/download`;
  const getStreamUrl = (jobId) => `${config.apiBaseUrl}/api/v2/assets/jobs/${jobId}/output.mp4`;

  return (
    <div className="grid grid-cols-4 gap-6 animate-in fade-in duration-500">
      {/* Sidebar: List of Completed Videos */}
      <div className="col-span-1 space-y-4 max-h-[70vh] overflow-y-auto pr-2 custom-scrollbar">
        <h3 className="text-sm font-black text-textSecondary uppercase tracking-widest mb-4">COMPLETED CASTS</h3>
        {jobs.length === 0 ? (
          <div className="p-8 bento-card text-center opacity-30">
            <p className="text-xs font-bold">No videos yet</p>
          </div>
        ) : jobs.map(job => (
          <div 
            key={job.id} 
            onClick={() => setSelectedJob(job)}
            className={`p-4 rounded-3xl cursor-pointer transition-all border-2 ${
              selectedJob?.id === job.id 
                ? 'bg-accent/10 border-accent shadow-lg shadow-accent/5' 
                : 'bg-surface/5 border-transparent hover:bg-surface/10'
            }`}
          >
            <h4 className="text-xs font-black truncate text-white uppercase mb-1">{job.topic}</h4>
            <div className="flex justify-between items-center text-[10px] text-textSecondary font-bold">
              <span>{job.video_type?.toUpperCase()}</span>
              <span>{new Date(job.completed_at).toLocaleDateString()}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Main: Video Player Section */}
      <div className="col-span-3">
        {selectedJob ? (
          <div className="flex flex-col gap-6">
            <div className="bento-card-light relative group overflow-hidden bg-black aspect-video rounded-3xl shadow-2xl border border-white/5">
              <video 
                key={selectedJob.id}
                controls 
                className="w-full h-full object-contain"
                poster={`${config.apiBaseUrl}/api/v2/assets/jobs/${selectedJob.id}/frames/scene_0.jpg`}
              >
                <source src={getStreamUrl(selectedJob.id)} type="video/mp4" />
                Your browser does not support the video tag.
              </video>
            </div>

            <div className="bento-card p-8 flex justify-between items-center border border-white/5 bg-surface/5 backdrop-blur-xl">
              <div>
                <h2 className="text-3xl font-black text-white mb-2 uppercase tracking-tighter">{selectedJob.topic}</h2>
                <div className="flex gap-4 text-xs font-bold text-textSecondary uppercase">
                  <span className="flex items-center gap-1.5"><Play size={14} className="text-accent" /> {selectedJob.video_type} Video</span>
                  <span className="flex items-center gap-1.5 text-accent/80 opacity-50">• {selectedJob.id}</span>
                </div>
              </div>
              
              <div className="flex gap-3">
                <a 
                  href={getDownloadUrl(selectedJob.id)} 
                  target="_blank" 
                  rel="noreferrer"
                  className="flex items-center gap-2 bg-white/5 hover:bg-white/10 px-6 py-3 rounded-full text-xs font-black transition-all border border-white/10"
                >
                  <Download size={16} /> DOWNLOAD
                </a>
                <Button variant="accent" className="px-6 py-3 text-xs font-black">
                   SHARE CAST
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <div className="bento-card h-full flex flex-col items-center justify-center text-center p-20 opacity-30 grayscale border-dashed border-white/10">
             <div className="w-24 h-24 rounded-full bg-surface/10 flex items-center justify-center mb-6">
                <Play size={40} className="ml-1" />
             </div>
             <h3 className="text-xl font-black mb-2 uppercase tracking-tight">Select a video to preview</h3>
             <p className="text-sm max-w-xs font-medium">Completed videos from your pipeline will appear here for review and download.</p>
          </div>
        )}
      </div>
    </div>
  );
}
