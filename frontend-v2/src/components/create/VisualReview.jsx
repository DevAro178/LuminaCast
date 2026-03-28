import React, { useState, useRef, useEffect } from 'react';
import useStore from '../../store/useStore';
import Button from '../ui/Button';
import Loader from '../ui/Loader';
import config from '../../config';
import { jobsApi } from '../../api/jobs';

// ─── Image Lightbox Modal ───────────────────────────────────────────────────
function ImageModal({ blobUrl, sceneLabel, onClose }) {
  const [scale, setScale] = useState(1);
  const [imgLoaded, setImgLoaded] = useState(false);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const dragStart = useRef(null);

  const zoomIn  = (e) => { e.stopPropagation(); setScale(s => Math.min(+(s + 0.25).toFixed(2), 5)); };
  const zoomOut = (e) => { e.stopPropagation(); setScale(s => Math.max(+(s - 0.25).toFixed(2), 0.25)); };
  const resetZoom = (e) => { if (e) e.stopPropagation(); setScale(1); setPos({ x: 0, y: 0 }); };

  const handleWheel = (e) => {
    e.preventDefault();
    const delta = e.deltaY < 0 ? 0.15 : -0.15;
    setScale(s => Math.min(Math.max(+(s + delta).toFixed(2), 0.25), 5));
  };

  const handleMouseDown = (e) => {
    e.stopPropagation();
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

  // Lock body scroll while open
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);

  // blobUrl is a local object URL — no network request
  // If we don't have a blob yet, the image may still load instantly if browser-cached
  const isBlob = blobUrl?.startsWith('blob:');

  return (
    <div
      className="fixed inset-0 z-50 bg-black/95 backdrop-blur-md flex flex-col items-center justify-center"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      onWheel={handleWheel}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* Header */}
      <div className="flex items-center justify-between w-full max-w-5xl px-6 py-4 flex-shrink-0" onClick={e => e.stopPropagation()}>
        <h4 className="font-display font-black text-sm tracking-widest uppercase text-white/70">{sceneLabel}</h4>
        <div className="flex items-center gap-2">
          <button onClick={zoomOut} className="w-9 h-9 rounded-full bg-white/10 hover:bg-white/25 text-white flex items-center justify-center font-bold text-xl transition-all select-none">−</button>
          <span className="font-mono text-white/60 text-sm w-14 text-center select-none">{Math.round(scale * 100)}%</span>
          <button onClick={zoomIn} className="w-9 h-9 rounded-full bg-white/10 hover:bg-white/25 text-white flex items-center justify-center font-bold text-xl transition-all select-none">+</button>
          <button onClick={resetZoom} className="px-3 py-2 rounded-full bg-white/10 hover:bg-white/25 text-white text-xs font-display font-black uppercase transition-all select-none">RESET</button>
          <button onClick={(e) => { e.stopPropagation(); onClose(); }} className="w-9 h-9 rounded-full bg-white/10 hover:bg-red-500/80 text-white flex items-center justify-center font-bold text-base transition-all ml-1 select-none">✕</button>
        </div>
      </div>

      {/* Image area */}
      <div
        className="relative flex-1 w-full max-w-5xl flex items-center justify-center overflow-hidden"
        style={{ cursor: scale > 1 ? (dragging ? 'grabbing' : 'grab') : 'default' }}
        onClick={e => e.stopPropagation()}
        onMouseDown={handleMouseDown}
      >
        {!imgLoaded && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-10 h-10 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        <img
          src={blobUrl}
          alt={sceneLabel}
          draggable={false}
          onLoad={() => setImgLoaded(true)}
          style={{
            opacity: imgLoaded ? 1 : 0,
            transform: `scale(${scale}) translate(${pos.x / scale}px, ${pos.y / scale}px)`,
            transition: dragging ? 'opacity 0.3s' : 'opacity 0.3s, transform 0.2s ease',
            maxWidth: '100%',
            maxHeight: '72vh',
            objectFit: 'contain',
            userSelect: 'none',
          }}
        />
      </div>

      <p className="text-white/25 text-xs font-mono py-3 flex-shrink-0 select-none" onClick={e => e.stopPropagation()}>
        Scroll to zoom • Drag to pan when zoomed • Click backdrop or ✕ to close
      </p>
    </div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────────────
export default function VisualReview() {
  const scriptScenes        = useStore(state => state.scriptScenes);
  const setAdvancedStep     = useStore(state => state.setAdvancedStep);
  const startPolling        = useStore(state => state.startPolling);
  const currentJobId        = useStore(state => state.currentJobId);
  const jobVideoType        = useStore(state => state.videoType);
  const isGenerating        = useStore(state => state.isGenerating);
  const status              = useStore(state => state.status);
  const progress            = useStore(state => state.progress);
  // Regeneration state lives in the store so it survives navigation
  const regeneratingScenes  = useStore(state => state.regeneratingScenes);
  const addRegeneratingScene    = useStore(state => state.addRegeneratingScene);
  const removeRegeneratingScene = useStore(state => state.removeRegeneratingScene);
  const updateSceneTags     = useStore(state => state.updateSceneTags);

  const [lightbox, setLightbox]       = useState(null); // { blobUrl, label }
  const [timestamps, setTimestamps]   = useState({});
  const [loadedImages, setLoadedImages] = useState(new Set());
  // Blob object URLs for scenes so lightbox has zero network overhead
  const blobUrls  = useRef({});             // { sceneIndex: blobObjectUrl }
  const stableTs  = useRef(Date.now());     // stable per mount, won't cause re-fetch loops
  // X/Y Generated counter
  const [generatedCount, setGeneratedCount] = useState(null);

  const isPortrait  = jobVideoType === 'short';
  const totalScenes = scriptScenes.length;

  // Live-poll scene completion counter AND bust per-scene timestamps as new images arrive
  const prevCompletedRef = useRef(0);

  useEffect(() => {
    if (!currentJobId) return;
    let cancelled = false;

    const poll = async () => {
      try {
        const job = await jobsApi.getJobStatus(currentJobId);
        if (cancelled) return;

        const doneStatuses = ['visual_review', 'assembling', 'generating_audio', 'adding_captions', 'completed'];
        const isDone = doneStatuses.includes(job.status);
        const completed = isDone ? totalScenes : (job.completed_scenes ?? 0);

        setGeneratedCount(completed);

        // Bust cache for any scenes that just finished since the last poll
        const prev = prevCompletedRef.current;
        if (completed > prev) {
          const freshTs = Date.now();
          setTimestamps(existing => {
            const next = { ...existing };
            for (let i = prev; i < completed; i++) {
              next[i] = freshTs; // override so getImageUrl returns a fresh URL
            }
            return next;
          });
          // Also clear loadedImages for new scenes so skeleton → real image transition plays
          setLoadedImages(existing => {
            const next = new Set(existing);
            for (let i = prev; i < completed; i++) next.delete(i);
            return next;
          });
          prevCompletedRef.current = completed;
        }
      } catch { /* silent */ }
    };

    poll();
    const id = setInterval(poll, 3000);
    return () => { cancelled = true; clearInterval(id); };
  }, [currentJobId, totalScenes]);

  // Cleanup blob object URLs on unmount
  useEffect(() => {
    return () => {
      Object.values(blobUrls.current).forEach(u => URL.revokeObjectURL(u));
    };
  }, []);

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleApproveAll = async () => {
    useStore.setState({ isGenerating: true, status: 'assembling' });
    try {
      await jobsApi.assemble(currentJobId);
      startPolling(currentJobId);
    } catch (err) {
      console.error("Assembly failed:", err);
      useStore.setState({ isGenerating: false });
    }
  };

  const handleRegenerate = async (e, sceneIndex) => {
    e.stopPropagation();
    addRegeneratingScene(sceneIndex);
    // Remove from loaded + blob cache so skeleton shows when new image arrives
    setLoadedImages(prev => { const n = new Set(prev); n.delete(sceneIndex); return n; });
    if (blobUrls.current[sceneIndex]) {
      URL.revokeObjectURL(blobUrls.current[sceneIndex]);
      delete blobUrls.current[sceneIndex];
    }
    try {
      const scene = useStore.getState().scriptScenes.find(s => s.scene_index === sceneIndex);
      const tags = scene?.edited_tags || scene?.image_prompt;
      
      // Backend now waits for generation to finish before responding
      await jobsApi.regenerateScene(currentJobId, sceneIndex, tags);
      
      const newTs = Date.now();
      setTimestamps(prev => ({ ...prev, [sceneIndex]: newTs }));
      removeRegeneratingScene(sceneIndex);
    } catch (err) {
      console.error("Regen failed:", err);
      removeRegeneratingScene(sceneIndex);
    }
  };

  // Called when card <img> loads — cache a blob URL from the img element via canvas
  const handleImageLoad = (e, idx) => {
    setLoadedImages(prev => new Set([...prev, idx]));
    try {
      const img = e.target;
      const canvas = document.createElement('canvas');
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      canvas.getContext('2d').drawImage(img, 0, 0);
      canvas.toBlob(blob => {
        if (!blob) return;
        if (blobUrls.current[idx]) URL.revokeObjectURL(blobUrls.current[idx]);
        blobUrls.current[idx] = URL.createObjectURL(blob);
      }, 'image/jpeg', 0.95);
    } catch { /* cross-origin or canvas blocked */ }
  };

  const getImageUrl = (i) => {
    const scene = scriptScenes[i];
    if (scene?.image_path) {
      const ts = timestamps[scene.scene_index] || stableTs.current;
      const separator = scene.image_path.includes('?') ? '&' : '?';
      return `${scene.image_path}${separator}t=${ts}`;
    }

    const idx = scene?.scene_index ?? i;
    const padded = String(idx).padStart(3, '0');
    const ts = timestamps[idx] || stableTs.current;
    return `${config.apiBaseUrl}/api/v2/assets/jobs/${currentJobId}/images/scene_${padded}.jpg?t=${ts}`;
  };

  const openLightbox = (e, idx, label) => {
    e.stopPropagation();
    // Use cached blob URL — zero network request; fallback to regular URL
    const src = blobUrls.current[idx] || getImageUrl(idx);
    setLightbox({ blobUrl: src, label });
  };

  // ── Loading States ─────────────────────────────────────────────────────────
  if ((status === 'generating_images' || status === 'queued' || status.includes('AI Visuals')) && generatedCount === 0) {
    return (
      <div className="col-span-3 bento-card relative h-[400px]">
        <Loader title="GENERATING VISUALS..." message={`Creating scene images... (${progress}%)`} />
      </div>
    );
  }
  if (status === 'assembling' || status === 'generating_audio' || status === 'adding_captions') {
    return (
      <div className="col-span-3 bento-card relative h-[400px]">
        <Loader title="ASSEMBLING VIDEO..." message="Generating audio, captions, and stitching scenes..." />
      </div>
    );
  }

  // ── Main View ──────────────────────────────────────────────────────────────
  return (
    <>
      {lightbox && (
        <ImageModal blobUrl={lightbox.blobUrl} sceneLabel={lightbox.label} onClose={() => setLightbox(null)} />
      )}

      <div className="col-span-3 bento-card animate-in slide-in-from-right-8 duration-500">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-4">
            <h3 className="text-2xl font-display font-black">VISUAL REVIEW</h3>
            {regeneratingScenes.size > 0 ? (
              <span className="text-xs font-display font-black bg-accent/20 text-accent px-3 py-1 rounded-full tracking-widest">
                REGENERATING {regeneratingScenes.size} VISUAL{regeneratingScenes.size !== 1 ? 'S' : ''}...
              </span>
            ) : generatedCount !== null && generatedCount < totalScenes ? (
              <span className="text-xs font-display font-black bg-accent/20 text-accent px-3 py-1 rounded-full tracking-widest">
                {generatedCount}/{totalScenes} GENERATED
              </span>
            ) : generatedCount !== null && generatedCount >= totalScenes ? (
              <span className="text-xs font-display font-black bg-green-500/20 text-green-400 px-3 py-1 rounded-full tracking-widest">
                ✓ ALL {totalScenes} READY
              </span>
            ) : null}
          </div>
          <div className="flex gap-4">
            <Button variant="outline" className="px-6 py-2 text-xs font-display font-black tracking-widest uppercase" onClick={() => setAdvancedStep('script')} disabled={isGenerating}>
              BACK TO SCRIPT
            </Button>
            <Button variant="accent" className="px-6 py-2 text-xs font-display font-black tracking-widest uppercase" onClick={handleApproveAll} disabled={isGenerating}>
              {isGenerating ? 'ASSEMBLING...' : 'APPROVE ALL & FINISH VIDEO'}
            </Button>
          </div>
        </div>

        {/* Grid */}
        <div className={`grid gap-5 ${isPortrait ? 'grid-cols-4' : 'grid-cols-3'}`}>
          {scriptScenes.map((scene, i) => {
            const idx     = scene.scene_index;
            const isRegen = regeneratingScenes.has(idx);
            const loaded  = loadedImages.has(idx);
            const url     = getImageUrl(idx);

            return (
              <div key={idx} className="bg-background rounded-2xl overflow-hidden border border-white/5 hover:border-accent/30 transition-all group select-none">
                {/* Image area */}
                <div
                  className={`relative w-full ${isPortrait ? 'aspect-[9/16]' : 'aspect-video'} overflow-hidden bg-white/5 ${loaded && !isRegen ? 'cursor-pointer' : ''}`}
                  onClick={(e) => !isRegen && loaded && openLightbox(e, idx, `Scene ${i + 1}`)}
                >
                  {isRegen ? (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-background/80 gap-3">
                      <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                      <span className="text-[10px] font-display font-black text-accent uppercase tracking-widest">Generating...</span>
                    </div>
                  ) : (
                    <>
                      {!loaded && <div className="absolute inset-0 animate-pulse bg-gradient-to-br from-white/5 via-white/10 to-white/5" />}
                      <img
                        src={url}
                        alt={`Scene ${i + 1}`}
                        draggable={false}
                        className={`w-full h-full object-cover group-hover:scale-105 transition-all duration-500 ${loaded ? 'opacity-100' : 'opacity-0'}`}
                        onLoad={(e) => handleImageLoad(e, idx)}
                        onError={(e) => {
                          setLoadedImages(prev => new Set([...prev, idx]));
                          e.target.src = `https://placehold.co/400x${isPortrait ? '720' : '225'}/0D2222/2A5555?text=Scene+${i + 1}`;
                        }}
                      />
                      {loaded && (
                        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/30">
                          <span className="text-white text-[10px] font-display font-black tracking-widest uppercase bg-black/60 px-3 py-1 rounded-full">CLICK TO EXPAND</span>
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
                      className="text-[10px] font-display font-black bg-accent/20 text-accent px-3 py-1 rounded-full uppercase tracking-tighter hover:bg-accent hover:text-white transition-all disabled:opacity-30"
                      onClick={(e) => handleRegenerate(e, idx)}
                      disabled={isRegen}
                    >
                      {isRegen ? '...' : 'REGENERATE'}
                    </button>
                  </div>
                  <input 
                    type="text"
                    value={scene.edited_tags ?? scene.image_prompt}
                    onChange={(e) => updateSceneTags(i, e.target.value)}
                    className="w-full bg-white/5 text-[10px] text-textSecondary font-mono border border-white/5 rounded px-2 py-1 outline-none focus:border-accent/40 focus:bg-white/10 transition-all"
                    disabled={isRegen}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}
