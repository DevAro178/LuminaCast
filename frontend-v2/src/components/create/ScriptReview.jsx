import React from 'react';
import useStore from '../../store/useStore';
import Button from '../ui/Button';

export default function ScriptReview() {
  const scriptScenes = useStore(state => state.scriptScenes);
  const updateSceneText = useStore(state => state.updateSceneText);
  const updateSceneTags = useStore(state => state.updateSceneTags);
  const saveScriptEdits = useStore(state => state.saveScriptEdits);
  const isGenerating = useStore(state => state.isGenerating);

  return (
    <div className="col-span-3 bento-card animate-in slide-in-from-right-8 duration-500">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-2xl font-black">SCRIPT REVIEW</h3>
        <div className="flex gap-4">
          <Button variant="outline" className="px-6 py-2 text-sm">
            AI REVISION
          </Button>
          <Button 
            variant="accent" 
            className="px-6 py-2 text-sm"
            onClick={saveScriptEdits}
            disabled={isGenerating}
          >
            {isGenerating ? "SAVING..." : "APPROVE & GENERATE VISUALS"}
          </Button>
        </div>
      </div>
      <div className="space-y-4">
        {scriptScenes.map((scene, index) => (
          <div key={index} className="p-4 bg-background rounded-2xl flex gap-6">
            <div className="w-12 h-12 rounded-full bg-surface/10 flex items-center justify-center font-bold flex-shrink-0">
              {index + 1}
            </div>
            <div className="flex-1 space-y-3">
              <div>
                <label className="text-xs font-bold text-textSecondary uppercase mb-1 block">Narration</label>
                <textarea 
                  value={scene.edited_text || scene.narration_text}
                  onChange={(e) => updateSceneText(index, e.target.value)}
                  className="w-full bg-surface/5 rounded-xl p-3 text-sm outline-none focus:bg-surface/10 border border-transparent focus:border-accent/50 resize-none h-20 leading-relaxed disabled:opacity-50"
                  disabled={isGenerating}
                />
              </div>
              <div>
                <label className="text-xs font-bold text-accent uppercase mb-1 block">Visual Tags</label>
                <input 
                  type="text"
                  value={scene.edited_tags || scene.image_prompt}
                  onChange={(e) => updateSceneTags(index, e.target.value)}
                  className="w-full bg-accent/10 text-accent rounded-xl p-3 text-sm outline-none focus:bg-accent/20 border border-transparent focus:border-accent/50 font-mono disabled:opacity-50"
                  disabled={isGenerating}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
