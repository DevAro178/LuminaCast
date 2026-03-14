import React from 'react';
import useStore from '../../store/useStore';
import Button from '../ui/Button';

export default function VisualReview() {
  const scriptScenes = useStore(state => state.scriptScenes);
  const setAdvancedStep = useStore(state => state.setAdvancedStep);
  const startPolling = useStore(state => state.startPolling);
  const currentJobId = useStore(state => state.currentJobId);
  const isGenerating = useStore(state => state.isGenerating);
  
  // Handlers
  const handleApproveAll = async () => {
    const { jobsApi } = await import('../../api/jobs');
    useStore.setState({ isGenerating: true });
    try {
      await jobsApi.assemble(currentJobId);
      setAdvancedStep('assemble');
      startPolling(currentJobId);
    } catch (error) {
      console.error("Assembly failed:", error);
      useStore.setState({ isGenerating: false });
    }
  };

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
        {scriptScenes.map((scene, i) => (
          <div key={i} className="bg-background rounded-2xl overflow-hidden group relative p-2">
            <img 
              src={`https://placehold.co/600x400/2C4A4A/FFFFFF?text=Scene+${i+1}+Visual`} 
              alt={`Scene ${i+1}`} 
              className="w-full h-48 object-cover rounded-xl" 
            />
            <div className="mt-4 px-2 pb-2">
              <div className="flex justify-between items-center mb-2">
                <span className="font-bold">Scene {i+1}</span>
                <button className="text-xs font-bold bg-accent/20 text-accent px-3 py-1 rounded-full hover:bg-accent hover:text-white transition-colors">
                  REGENERATE
                </button>
              </div>
              <p className="text-xs text-textSecondary truncate font-mono">
                {scene.edited_tags || scene.image_prompt}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
