import React, { useState, useCallback, useRef } from 'react';
import useStore from '../../store/useStore';
import Button from '../ui/Button';
import Loader from '../ui/Loader';
import config from '../../config';
import { jobsApi } from '../../api/jobs';

// ─── Image Lightbox Modal ───────────────────────────────────────────────────
function ImageModal({ imageUrl, sceneLabel, onClose }) {
  const [scale, setScale] = useState(1);
  const [dragging, setDragging] = useState(false);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const dragStart = useRef(null);

  const zoomIn = () => setScale(s => Math.min(s + 0.5, 4));
  const zoomOut = () => setScale(s => Math.max(s - 0.5, 0.5));
  const resetZoom = () => { setScale(1); setPos({ x: 0, y: 0 }); };

  const handleMouseDown = (e) => {
    if (scale > 1) {
      setDragging(true);
      dragStart.current = { x: e.clientX - pos.x, y: e.clientY - pos.y };
    }
  };
  const handleMouseMove = (e) => {
    if (dragging && dragStart.current) {
      setPos({ x: e.clientX - dragStart.current.x, y: e.clientY - dragStart.current.y });
    }
  };
  const handleMouseUp = () => setDragging(false);

  return (
    <div
      className="fixed inset-0 z-50 bg-black/90 backdrop-blur-sm flex flex-col items-center justify-center"
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* Header */}
      <div className="flex items-center justify-between w-full max-w-5xl px-6 py-4">
        <h4 className="font-display font-black text-lg tracking-widest uppercase text-white/80">{sceneLabel}</h4>
        <div className="flex items-center gap-3">
          <button onClick={zoomOut} className="w-9 h-9 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center font-bold text-lg transition-all">−</button>
          <span className="font-mono text-white/60 text-sm min-w-[48px] text-center">{Math.round(scale * 100)}%</span>
          <button onClick={zoomIn} className="w-9 h-9 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center font-bold text-lg transition-all">+</button>
          <button onClick={resetZoom} className="px-3 py-1 rounded-full bg-white/10 hover:bg-white/20 text-white text-xs font-display font-black uppercase transition-all">RESET</button>
          <button onClick={onClose} className="w-9 h-9 rounded-full bg-white/10 hover:bg-accent text-white flex items-center justify-center font-bold text-lg transition-all ml-2">✕</button>
        </div>
      </div>

      {/* Image */}
      <div
        className="overflow-hidden flex-1 w-full max-w-5xl flex items-center justify-center"
        style={{ cursor: scale > 1 ? (dragging ? 'grabbing' : 'grab') : 'default' }}
      >
        <img
          src={imageUrl}
          alt={sceneLabel}
          draggable={false}
          onMouseDown={handleMouseDown}
          style={{
            transform: `scale(${scale}) translate(${pos.x / scale}px, ${pos.y / scale}px)`,
            transition: dragging ? 'none' : 'transform 0.2s ease',
            maxWidth: '100%',
            maxHeight: '70vh',
            objectFit: 'contain',
            userSelect: 'none',
          }}
        />
      </div>

      {/* Footer hint */}
      <p className="text-white/30 text-xs font-mono py-4">Click backdrop to close • Scroll = zoom • Drag when zoomed</p>
    </div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────────────
export default function VisualReview() {
  const scriptScenes = useStore(state => state.scriptScenes);
  const setAdvancedStep = useStore(state => state.setAdvancedStep);
  const startPolling = useStore(state => state.startPolling);
  const currentJobId = useStore(state => state.currentJobId);
  const jobVideoType = useStore(state => state.videoType);
  const isGenerating = useStore(state => state.isGenerating);
  const status = useStore(state => state.status);
  const progress = useStore(state => state.progress);

  const [lightbox, setLightbox] = useState(null);
  const [regeneratingScenes, setRegeneratingScenes] = useState(new Set());
  const [timestamps, setTimestamps] = useState({});
  const [loadedImages, setLoadedImages] = useState(new Set()); // Track which images have loaded

  const isPortrait = jobVideoType === 'short';

  const handleApproveAll = async () => {
    useStore.setState({ isGenerating: true, status: 'assembling' });
    try {
      await jobsApi.assemble(currentJobId);
      startPolling(currentJobId);
    } catch (error) {
      console.error("Assembly failed:", error);
      useStore.setState({ isGenerating: false });
    }
  };

  const handleRegenerate = async (e, sceneIndex) => {
    e.stopPropagation(); // don't open lightbox
    setRegeneratingScenes(prev => new Set([...prev, sceneIndex]));
    try {
      await jobsApi.regenerateScene(currentJobId, sceneIndex);
      // Poll until server finishes (~20s delay then bust cache)
      setTimeout(() => {
        setTimestamps(prev => ({ ...prev, [sceneIndex]: Date.now() }));
        setRegeneratingScenes(prev => {
          const next = new Set(prev);
          next.delete(sceneIndex);
          return next;
        });
      }, 22000); // Easy Diffusion typically takes 15-25s
    } catch (error) {
      console.error("Regeneration failed:", error);
      setRegeneratingScenes(prev => {
        const next = new Set(prev);
        next.delete(sceneIndex);
        return next;
      });
    }
  };

  const getImageUrl = (sceneIndex, ts) => {
    const padded = String(sceneIndex).padStart(3, '0');
    return `${config.apiBaseUrl}/api/v2/assets/jobs/${currentJobId}/images/scene_${padded}.jpg?t=${ts || Date.now()}`;
  };

  // ── Loading States ──────────────────────────────────────────────────────
  if (status === 'generating_images' || status === 'queued') {
    return (
      <div className="col-span-3 bento-card relative h-[400px]">
        <Loader title="GENERATING VISUALS..." message={`Stable Diffusion is creating frames for your scenes (${progress}%)...`} />
      </div>
    );
  }

  if (status === 'assembling' || status === 'generating_audio' || status === 'adding_captions') {
    return (
      <div className="col-span-3 bento-card relative h-[400px]">
        <Loader title="ASSEMBLING VIDEO..." message="Generating audio, captions, and stitching scenes together..." />
      </div>
    );
  }

  // ── Main View ───────────────────────────────────────────────────────────
  return (
    <>
      {/* Lightbox */}
      {lightbox && (
        <div onClick={() => setLightbox(null)}>
          <ImageModal imageUrl={lightbox.url} sceneLabel={lightbox.label} onClose={() => setLightbox(null)} />
        </div>
      )}

      <div className="col-span-3 bento-card animate-in slide-in-from-right-8 duration-500">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-2xl font-display font-black">VISUAL REVIEW</h3>
          <div className="flex gap-4">
            <Button
              variant="outline"
              className="px-6 py-2 text-xs font-display font-black tracking-widest uppercase"
              onClick={() => setAdvancedStep('script')}
              disabled={isGenerating}
            >
              BACK TO SCRIPT
            </Button>
            <Button
              variant="accent"
              className="px-6 py-2 text-xs font-display font-black tracking-widest uppercase"
              onClick={handleApproveAll}
              disabled={isGenerating}
            >
              {isGenerating ? 'ASSEMBLING...' : 'APPROVE ALL & FINISH VIDEO'}
            </Button>
          </div>
        </div>

        {/* Grid — 3 columns for landscape, 4 columns for portrait */}
        <div className={`grid gap-5 ${isPortrait ? 'grid-cols-4' : 'grid-cols-3'}`}>
          {scriptScenes.map((scene, i) => {
            const idx = scene.scene_index;
            const isRegen = regeneratingScenes.has(idx);
            const ts = timestamps[idx] || '';
            const url = getImageUrl(idx, ts);

            return (
              <div
                key={idx}
                className="bg-background rounded-2xl overflow-hidden border border-white/5 hover:border-accent/30 transition-all group cursor-pointer"
                onClick={() => !isRegen && setLightbox({ url, label: `Scene ${i + 1}` })}
              >
                {/* Image wrapper — ratio locked */}
                <div className={`relative w-full ${isPortrait ? 'aspect-[9/16]' : 'aspect-video'} overflow-hidden bg-white/5`}>
                  {isRegen ? (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-background/80 gap-3">
                      <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                      <span className="text-[10px] font-display font-black text-accent uppercase tracking-widest">Generating...</span>
                    </div>
                  ) : (
                    <>
                      {/* Shimmer skeleton — shown while image is loading */}
                      {!loadedImages.has(idx) && (
                        <div className="absolute inset-0 animate-pulse bg-gradient-to-br from-white/5 via-white/10 to-white/5" />
                      )}
                      <img
                        src={url}
                        alt={`Scene ${i + 1}`}
                        className={`w-full h-full object-cover group-hover:scale-105 transition-all duration-500 ${loadedImages.has(idx) ? 'opacity-100' : 'opacity-0'}`}
                        onLoad={() => setLoadedImages(prev => new Set([...prev, idx]))}
                        onError={(e) => {
                          setLoadedImages(prev => new Set([...prev, idx]));
                          e.target.src = `https://placehold.co/400x${isPortrait ? '720' : '225'}/1A3333/4A7A7A?text=Scene+${i + 1}`;
                        }}
                      />
                      {/* Hover expand hint */}
                      {loadedImages.has(idx) && (
                        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/30">
                          <span className="text-white text-xs font-display font-black tracking-widest uppercase bg-black/50 px-3 py-1 rounded-full">CLICK TO EXPAND</span>
                        </div>
                      )}
                    </>
                  )}
                </div>

                {/* Footer */}
                <div className="p-3">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-display font-bold text-sm">Scene {i + 1}</span>
                    <button
                      className="text-[10px] font-display font-black bg-accent/20 text-accent px-3 py-1 rounded-full uppercase tracking-tighter hover:bg-accent hover:text-white transition-all disabled:opacity-40"
                      onClick={(e) => handleRegenerate(e, idx)}
                      disabled={isRegen}
                    >
                      {isRegen ? '...' : 'REGENERATE'}
                    </button>
                  </div>
                  <p className="text-[10px] text-textSecondary truncate font-mono opacity-50 leading-tight">
                    {scene.edited_tags || scene.image_prompt}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}
