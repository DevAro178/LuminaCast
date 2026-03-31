import React, { useState, useEffect } from 'react';
import useStore from '../../store/useStore';
import { jobsApi } from '../../api/jobs';
import Select from '../ui/Select';

export default function StudioSettings() {
  const [voices, setVoices] = useState([]);
  const [models, setModels] = useState([]);
  const [isOpen, setIsOpen] = useState(false);

  const voiceId = useStore(state => state.voiceId);
  const setVoiceId = useStore(state => state.setVoiceId);
  const sdModelId = useStore(state => state.sdModelId);
  const setSdModelId = useStore(state => state.setSdModelId);
  const ttsExaggeration = useStore(state => state.ttsExaggeration);
  const setTtsExaggeration = useStore(state => state.setTtsExaggeration);
  const ttsCfgWeight = useStore(state => state.ttsCfgWeight);
  const setTtsCfgWeight = useStore(state => state.setTtsCfgWeight);
  const ttsSpeed = useStore(state => state.ttsSpeed);
  const setTtsSpeed = useStore(state => state.setTtsSpeed);
  const captionStyle = useStore(state => state.captionStyle);
  const setCaptionStyle = useStore(state => state.setCaptionStyle);
  
  // Actually effectIds is an array, but we only have a single select in UI for simplicity right now
  const effectIds = useStore(state => state.effectIds);
  const setEffectIds = useStore(state => state.setEffectIds);

  useEffect(() => {
    jobsApi.getVoices().then(data => setVoices(data)).catch(console.error);
    jobsApi.getSdModels().then(data => setModels(data)).catch(console.error);
  }, []);

  const voiceOptions = voices.map(v => ({ value: v.id, label: v.name }));
  const modelOptions = [
    { value: '', label: 'Default GenAI Model' },
    ...models.map(m => ({ value: m.id, label: m.name }))
  ];
  
  const effectOptions = [
    { value: 'ken_burns', label: 'Ken Burns (Slow Zoom)' },
    { value: 'pan_left', label: 'Pan Left' },
    { value: 'pan_right', label: 'Pan Right' },
    { value: 'zoom_out', label: 'Zoom Out' }
  ];

  const currentEffect = effectIds.length > 0 ? effectIds[0] : 'ken_burns';

  if (!isOpen) {
    return (
      <button 
        onClick={() => setIsOpen(true)}
        className="text-[10px] font-black tracking-widest uppercase text-accent hover:text-white transition-colors flex items-center gap-2 mb-4"
      >
        <span className="w-4 h-4 rounded-full bg-accent/20 flex items-center justify-center">+</span>
        Studio Settings
      </button>
    );
  }

  return (
    <div className="bg-white/5 border border-white/5 rounded-3xl p-6 mb-4 space-y-4">
      <div className="flex justify-between items-center mb-2">
        <h4 className="text-sm font-black tracking-widest uppercase text-white">Studio Engine Settings</h4>
        <button onClick={() => setIsOpen(false)} className="text-white/30 hover:text-white text-xs font-bold uppercase tracking-widest">Close</button>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-[10px] font-black tracking-widest uppercase text-textSecondary block mb-2">Avatar Voice</label>
          <Select 
            value={voiceId} 
            onChange={setVoiceId}
            options={voiceOptions.length > 0 ? voiceOptions : [{value: 'adam', label: 'Loading...'}]}
          />
        </div>
        <div>
          <label className="text-[10px] font-black tracking-widest uppercase text-textSecondary block mb-2">Visual Model</label>
          <Select 
            value={sdModelId || ''} 
            onChange={(val) => setSdModelId(val === '' ? null : val)}
            options={modelOptions}
          />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="text-[10px] font-black tracking-widest uppercase text-textSecondary block mb-2">Caption Style</label>
          <Select 
            value={captionStyle} 
            onChange={setCaptionStyle}
            options={[
              { value: 'chunked', label: 'Standard Block' },
              { value: 'word_pop', label: 'Viral Word Pop' }
            ]}
          />
        </div>
        <div className="col-span-2">
          <label className="text-[10px] font-black tracking-widest uppercase text-textSecondary block mb-2">Camera Motion</label>
          <Select 
            value={currentEffect} 
            onChange={(val) => setEffectIds([val])}
            options={effectOptions}
          />
        </div>
      </div>

      <div className="space-y-4 pt-4 border-t border-white/5">
        <h5 className="text-[10px] font-black tracking-widest uppercase text-accent">Expressive Voice Controls</h5>
        
        <div className="grid grid-cols-3 gap-6">
          <div>
            <div className="flex justify-between mb-1">
              <label className="text-[10px] font-bold text-textSecondary uppercase">Emotion/Exaggeration</label>
              <span className="text-[10px] text-white">{ttsExaggeration.toFixed(2)}</span>
            </div>
            <input 
              type="range" min="0" max="1" step="0.05" 
              value={ttsExaggeration} onChange={(e) => setTtsExaggeration(parseFloat(e.target.value))}
              className="w-full accent-accent bg-white/10 h-1 rounded-full appearance-none"
            />
          </div>
          <div>
            <div className="flex justify-between mb-1">
              <label className="text-[10px] font-bold text-textSecondary uppercase">Likeness/CFG</label>
              <span className="text-[10px] text-white">{ttsCfgWeight.toFixed(2)}</span>
            </div>
            <input 
              type="range" min="0" max="1" step="0.05" 
              value={ttsCfgWeight} onChange={(e) => setTtsCfgWeight(parseFloat(e.target.value))}
              className="w-full accent-accent bg-white/10 h-1 rounded-full appearance-none"
            />
          </div>
          <div>
            <div className="flex justify-between mb-1">
              <label className="text-[10px] font-bold text-textSecondary uppercase">Pacing</label>
              <span className="text-[10px] text-white">{ttsSpeed.toFixed(2)}x</span>
            </div>
            <input 
              type="range" min="0.5" max="2.0" step="0.05" 
              value={ttsSpeed} onChange={(e) => setTtsSpeed(parseFloat(e.target.value))}
              className="w-full accent-accent bg-white/10 h-1 rounded-full appearance-none"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
