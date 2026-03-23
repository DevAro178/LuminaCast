import React, { useState, useEffect } from 'react';
import useStore from '../../store/useStore';
import { jobsApi } from '../../api/jobs';
import Button from '../ui/Button';
import Select from '../ui/Select';
import Loader from '../ui/Loader';
import OutlineReview from './OutlineReview';
import ScriptReview from './ScriptReview';
import VisualReview from './VisualReview';
import AssemblyView from './AssemblyView';

export default function ContentGrid() {
  const mode = useStore(state => state.mode);
  const advancedStep = useStore(state => state.advancedStep);
  const setActiveTab = useStore(state => state.setActiveTab);
  
  const [recentJobs, setRecentJobs] = useState([]);

  useEffect(() => {
    const fetchRecent = async () => {
      try {
        const data = await jobsApi.listJobs();
        setRecentJobs(data.filter(j => j.status === 'completed').slice(0, 5));
      } catch (err) {
        console.error(err);
      }
    };
    fetchRecent();
  }, []);

  const videoType = useStore(state => state.videoType);
  const setVideoType = useStore(state => state.setVideoType);
  const voiceType = useStore(state => state.voiceType);
  const setVoiceType = useStore(state => state.setVoiceType);
  
  const topicInput = useStore(state => state.topicInput);
  const setTopicInput = useStore(state => state.setTopicInput);
  const startJob = useStore(state => state.startJob);
  const isGenerating = useStore(state => state.isGenerating);
  const status = useStore(state => state.status);

  return (
    <div className="grid grid-cols-3 gap-6">
      {/* Dynamic Content based on Advanced Step */}
      {mode === 'basic' || advancedStep === 'input' ? (
        <>
          <div className="col-span-1 bento-card flex flex-col group hover:border-accent/20 transition-all">
            <h3 className="text-sm font-bold tracking-widest text-textSecondary uppercase mb-6 flex justify-between items-center">
               RECENT VIDEOS
               <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
            </h3>
            <div className="flex-1 space-y-3">
              {recentJobs.length === 0 ? (
                <div className="h-full flex items-center justify-center opacity-30">
                  <p className="text-xs font-bold uppercase tracking-widest">No recent videos</p>
                </div>
              ) : recentJobs.map(job => (
                <div 
                  key={job.id} 
                  onClick={() => {
                    useStore.setState({ activeTab: 'library', currentJobId: job.id });
                  }}
                  className="p-4 rounded-3xl bg-surface/5 hover:bg-accent/10 hover:translate-x-1 transition-all cursor-pointer border border-white/5"
                >
                  <p className="text-[10px] font-black text-accent mb-1 uppercase tracking-tighter">{job.video_type}</p>
                  <h4 className="text-sm font-black text-white truncate uppercase tracking-tighter leading-none">{job.topic}</h4>
                </div>
              ))}
            </div>
          </div>
          
          <div className="col-span-2 bento-card relative overflow-hidden transition-all duration-500 flex flex-col justify-center">
            {isGenerating && (status === 'generating_script' || status === 'queued') && (
              <Loader 
                title={mode === 'basic' ? "JOB CREATED!" : "DRAFTING SCRIPT..."}
                message={mode === 'basic' ? "Redirecting to Dashboard..." : "Analyzing prompt and framing scenes..."}
                fullScreen={true}
              />
            )}

            <h3 className="text-4xl font-black tracking-tight mb-2">
              {mode === 'basic' ? "QUICK START" : "STUDIO DRAFTING"}
            </h3>
            <p className="text-textSecondary mb-6 max-w-sm font-medium">
              {mode === 'basic' 
                ? "Enter a topic and let our models handle the script, visuals, and audio in one click."
                : "Describe your video vision in detail. We'll generate a comprehensive script for your approval."
              }
            </p>
            
            <div className="flex gap-4 mb-4 relative z-10">
              {mode === 'advanced' && (
                <Select 
                  value={videoType} 
                  onChange={setVideoType}
                  options={[
                    { value: 'short', label: 'Short Video (30-60s)' },
                    { value: 'long', label: 'Long Video (~7-8m)' }
                  ]}
                />
              )}
              <Select 
                value={voiceType} 
                onChange={setVoiceType}
                options={[
                  { value: 'female', label: 'Female Voice' },
                  { value: 'male', label: 'Male Voice' }
                ]}
              />
            </div>
            
            <div className="flex gap-2 relative z-10">
              <input 
                type="text" 
                value={topicInput}
                onChange={(e) => setTopicInput(e.target.value)}
                placeholder={mode === 'basic' ? "What's your video about?" : "Describe target audience, style, and tone..."} 
                className="flex-1 bg-white/5 rounded-full px-6 py-4 outline-none placeholder:text-white/30 text-white font-medium disabled:opacity-50 border border-white/5 focus:border-white/20 transition-all"
                disabled={isGenerating}
              />
              <Button 
                variant="primary"
                onClick={startJob}
                disabled={isGenerating || !topicInput}
              >
                {mode === 'basic' ? "GENERATE" : "DRAFT SCRIPT"}
              </Button>
            </div>
          </div>
        </>
      ) : advancedStep === 'outline' ? (
        <OutlineReview />
      ) : advancedStep === 'script' ? (
        <ScriptReview />
      ) : advancedStep === 'visuals' ? (
        <VisualReview />
      ) : (
        <AssemblyView />
      )}
    </div>
  );
}
