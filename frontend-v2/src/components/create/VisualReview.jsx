import React from 'react';
import useStore from '../../store/useStore';
import Button from '../ui/Button';
import Loader from '../ui/Loader';
import config from '../../config';

export default function VisualReview() {
  const scriptScenes = useStore(state => state.scriptScenes);
  const setAdvancedStep = useStore(state => state.setAdvancedStep);
  const startPolling = useStore(state => state.startPolling);
  const currentJobId = useStore(state => state.currentJobId);
  const isGenerating = useStore(state => state.isGenerating);
  const status = useStore(state => state.status);
  const progress = useStore(state => state.progress);
  
  // Handlers
  const handleApproveAll = async () => {
    const { jobsApi } = await import('../../api/jobs');
    useStore.setState({ isGenerating: true });
    try {
      await jobsApi.assemble(currentJobId);
      // Step transition is handled by polling in useStore
      startPolling(currentJobId);
    } catch (error) {
      console.error("Assembly failed:", error);
      useStore.setState({ isGenerating: false });
    }
  };

  if (status === 'generating_images' || status === 'queued') {
    return (
      <div className="col-span-3 bento-card relative h-[400px]">
        <Loader 
          title="GENERATING VISUALS..."
          message={`Stable Diffusion is creating frames for your scenes (${progress}%)...`}
        />
      </div>
    );
  }

  return (
    <div className="col-span-3 bento-card animate-in slide-in-from-right-8 duration-500">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-2xl font-black">VISUAL REVIEW</h3>
        <div className="flex gap-4">
          <Button 
            variant="outline"
            className="px-6 py-2 text-sm"
            onClick={() => setAdvancedStep('script')}
            disabled={isGenerating}
          >
            BACK TO SCRIPT
          </Button>
          <Button 
            variant="secondary" 
            className="px-6 py-2 text-sm"
            onClick={handleApproveAll}
            disabled={isGenerating}
          >
            {isGenerating ? "STARTING ASSEMBLY..." : "APPROVE ALL & FINISH VIDEO"}
          </Button>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-6">
        {scriptScenes.map((scene, i) => {
          const imageUrl = `${config.apiBaseUrl}/api/v2/assets/jobs/${currentJobId}/frames/scene_${scene.scene_index}.jpg?t=${Date.now()}`;
          return (
            <div key={i} className="bg-background rounded-2xl overflow-hidden group relative p-2 border border-white/5 hover:border-accent/30 transition-all">
              <img 
                src={imageUrl} 
                alt={`Scene ${i+1}`} 
                className="w-full h-48 object-cover rounded-xl"
                onError={(e) => {
                  e.target.src = "https://placehold.co/600x400/2C4A4A/FFFFFF?text=Generating...";
                }}
              />
              <div className="mt-4 px-2 pb-2">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold text-sm">Scene {i+1}</span>
                  <button className="text-[10px] font-black bg-accent/10 text-accent px-3 py-1 rounded-full uppercase tracking-tighter hover:bg-accent hover:text-white transition-all">
                    REGENERATE
                  </button>
                </div>
                <p className="text-[11px] text-textSecondary truncate font-mono opacity-60">
                  {scene.edited_tags || scene.image_prompt}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
