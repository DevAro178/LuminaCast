import React from 'react';
import useStore from '../../store/useStore';
import Button from '../ui/Button';
import Loader from '../ui/Loader';

export default function ScriptReview() {
  const scriptScenes = useStore(state => state.scriptScenes);
  const updateSceneText = useStore(state => state.updateSceneText);
  const updateSceneAudio = useStore(state => state.updateSceneAudio);
  const updateSceneTags = useStore(state => state.updateSceneTags);
  const saveScriptEdits = useStore(state => state.saveScriptEdits);
  const reviseScript = useStore(state => state.reviseScript);
  const isGenerating = useStore(state => state.isGenerating);
  const status = useStore(state => state.status);

  const handleAiRevision = () => {
    reviseScript(); // Logic moved to store
  };

  return (
    <div className="col-span-3 bento-card animate-in slide-in-from-right-8 duration-500 relative">
      {/* AI Revision in-progress overlay */}
      {status === 'revising_script' && (
        <div className="absolute inset-0 z-10 bg-card/80 backdrop-blur-sm rounded-[24px] flex items-center justify-center">
          <Loader
            title="AI REVISING SCRIPT..."
            message="Analysing your edits and generating an improved script..."
          />
        </div>
      )}
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-3xl font-display font-black tracking-tighter">SCRIPT REVIEW</h3>
        <div className="flex gap-4">
          <Button 
            variant="outline" 
            className="px-6 py-2 text-xs font-display font-black tracking-widest uppercase hover:bg-accent/10 transition-colors"
            onClick={handleAiRevision}
            disabled={isGenerating}
          >
            {status === 'revising_script' ? "AI REVISING..." : "AI REVISION"}
          </Button>
          <Button 
            variant="accent" 
            className="px-6 py-2 text-xs font-display font-black tracking-widest uppercase shadow-[0_0_20px_-5px_rgba(255,107,0,0.4)]"
            onClick={saveScriptEdits}
            disabled={isGenerating}
          >
            {isGenerating && status !== 'revising_script' ? "PROCESSING..." : "APPROVE & GENERATE VISUALS"}
          </Button>
        </div>
      </div>
      <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-2 custom-scrollbar">
        {scriptScenes.map((scene, index) => (
          <div key={index} className="p-6 bg-surface/5 rounded-[2rem] flex gap-8 border border-white/5 hover:border-accent/20 transition-all group">
            <div className="w-14 h-14 rounded-full bg-accent/10 flex items-center justify-center font-display font-black text-accent flex-shrink-0 border border-accent/20">
              {index + 1}
            </div>
            <div className="flex-1 space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-[10px] font-black font-display text-textSecondary uppercase mb-2 block tracking-widest opacity-50">On-Screen Captions</label>
                  <textarea 
                    value={scene.edited_text !== undefined ? scene.edited_text : scene.narration_text}
                    onChange={(e) => updateSceneText(index, e.target.value)}
                    className="w-full bg-white/5 rounded-2xl p-4 text-sm outline-none focus:bg-white/10 border border-transparent focus:border-accent/30 resize-none h-24 leading-relaxed font-medium transition-all"
                    disabled={isGenerating}
                  />
                </div>
                <div>
                  <label className="text-[10px] font-black font-display text-textSecondary uppercase mb-2 block tracking-widest opacity-50">Phonetic Audio (TTS)</label>
                  <textarea 
                    value={scene.edited_audio !== undefined ? scene.edited_audio : (scene.narration_audio || scene.narration_text)}
                    onChange={(e) => updateSceneAudio(index, e.target.value)}
                    className="w-full bg-white/5 rounded-2xl p-4 text-sm outline-none focus:bg-white/10 border border-transparent focus:border-accent/30 resize-none h-24 leading-relaxed font-medium transition-all"
                    disabled={isGenerating}
                  />
                </div>
              </div>
              <div className="relative group-hover:translate-x-1 transition-transform">
                <label className="text-[10px] font-black font-display text-accent uppercase mb-2 block tracking-widest">Visual Tags (SDXL)</label>
                <div className="relative">
                  <input 
                    type="text"
                    value={scene.edited_tags || scene.image_prompt}
                    onChange={(e) => updateSceneTags(index, e.target.value)}
                    className="w-full bg-accent/30 text-white rounded-2xl p-5 text-sm outline-none border border-accent/50 focus:border-accent focus:bg-accent/40 font-mono font-bold shadow-inner-accent transition-all placeholder:text-white/20"
                    disabled={isGenerating}
                  />
                  <div className="absolute top-1/2 right-4 -translate-y-1/2 w-2 h-2 rounded-full bg-accent animate-pulse" />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
