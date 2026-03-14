import React from 'react';
import useStore from '../../store/useStore';
import Button from '../ui/Button';
import Select from '../ui/Select';
import Loader from '../ui/Loader';
import ScriptReview from './ScriptReview';
import VisualReview from './VisualReview';
import AssemblyView from './AssemblyView';

export default function ContentGrid() {
  const mode = useStore(state => state.mode);
  const advancedStep = useStore(state => state.advancedStep);
  
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
          <div className="col-span-1 bento-card flex flex-col">
            <h3 className="text-sm font-bold tracking-widest text-textSecondary mb-4">RECENT VIDEOS</h3>
            <div className="flex-1 flex items-center justify-center">
              <p className="text-textSecondary/50 text-sm">No recent videos found.</p>
            </div>
          </div>
          
          <div className="col-span-2 bento-card-light relative overflow-hidden transition-all duration-500 flex flex-col justify-center">
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
            <p className="text-background/60 mb-6 max-w-sm">
              {mode === 'basic' 
                ? "Enter a topic and let our models handle the script, visuals, and audio in one click."
                : "Describe your video vision in detail. We'll generate a comprehensive script for your approval."
              }
            </p>
            
            <div className="flex gap-4 mb-4 relative z-10">
              <Select 
                value={videoType} 
                onChange={setVideoType}
                options={[
                  { value: 'short', label: 'Short Video (30-60s)' },
                  { value: 'long', label: 'Long Video (5-10m)' }
                ]}
              />
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
                className="flex-1 bg-background/5 rounded-full px-6 py-4 outline-none placeholder:text-background/40 font-medium disabled:opacity-50"
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
