import React from 'react';
import clsx from 'clsx';
import useStore from '../../store/useStore';
import Button from '../ui/Button';

export default function MainHero() {
  const mode = useStore(state => state.mode);
  const setMode = useStore(state => state.setMode);
  const advancedStep = useStore(state => state.advancedStep);
  const setAdvancedStep = useStore(state => state.setAdvancedStep);

  // Focus Mode Trigger: If we are in advanced mode AND past the input step, shrink to a top bar.
  const isFocusMode = mode === 'advanced' && advancedStep !== 'input';

  if (isFocusMode) {
    return (
      <div className="w-full h-20 bento-card flex items-center justify-between px-8 py-0 mb-6 animate-in slide-in-from-top-8 duration-500 overflow-hidden relative group">
        <div className="absolute inset-0 bg-gradient-to-r from-accent/20 to-transparent pointer-events-none"></div>
        <div className="flex items-center gap-6 relative z-10">
          <h2 className="text-2xl font-black tracking-tight">Focus Mode</h2>
          <div className="h-6 w-[2px] bg-white/10"></div>
          <p className="text-textSecondary text-sm font-medium">
            {advancedStep === 'script' ? 'Drafting & Reviewing Script' : 
             advancedStep === 'visuals' ? 'Curating Scene Visuals' : 'Assembling Final Video'}
          </p>
        </div>
        <button 
          onClick={() => {
            setAdvancedStep('input');
            setMode('basic');
          }}
          className="relative z-10 text-xs font-bold tracking-wider text-textSecondary hover:text-white px-4 py-2 rounded-full border border-white/10 hover:bg-white/5 transition-all"
        >
          EXIT TO BASIC MODE
        </button>
      </div>
    );
  }

  return (
    <div className="relative w-full h-[500px] bento-card overflow-hidden flex items-center p-12 transition-all duration-500 mb-6">
      {/* Background Graphic placeholder */}
      <div className="absolute inset-0 bg-gradient-to-br from-card to-background/50 pointer-events-none"></div>
      
      <div className="relative z-10 max-w-2xl">
        <h1 className="text-[110px] leading-[0.9] font-black tracking-tight mb-6">
          <span className="font-light">LUMINA</span><br/>CAST
        </h1>
        <p className="text-textSecondary text-lg max-w-md leading-relaxed mb-8 h-20">
          {mode === 'basic' 
            ? "The next generation of AI video creation. One click magic to generate a full narrated video from a single prompt."
            : "Professional studio mode. Granular frame-by-frame control, script optimization, and scene-by-scene approval."
          }
        </p>
        
        <div className="flex gap-4">
          <Button 
            variant={mode === 'basic' ? 'secondary' : 'outline'}
            onClick={() => setMode('basic')}
          >
            BASIC MODE
          </Button>
          <Button 
            variant={mode === 'advanced' ? 'accent' : 'outline'}
            onClick={() => setMode('advanced')}
          >
            ADVANCED MODE
          </Button>
        </div>
      </div>
      
      {/* Visual Illustration (Right Side) */}
      <div className="absolute right-12 bottom-0 w-[400px] h-[400px] pointer-events-none flex items-end justify-center">
        <div className="relative w-full h-full flex items-center justify-center">
          {/* Abstract geometric anime-style eye/lens graphic */}
          <div className={clsx(
            "absolute w-[300px] h-[300px] rounded-full border-[12px] border-white/10 transition-all duration-1000 flex items-center justify-center",
            mode === 'basic' ? "rotate-0 scale-100" : "rotate-45 scale-110 border-accent/30"
          )}>
            <div className={clsx(
              "w-[200px] h-[200px] rounded-full transition-all duration-1000",
              mode === 'basic' ? "bg-surface/10" : "bg-accent/20"
            )}></div>
            <div className="absolute w-[60px] h-[60px] bg-white rounded-full shadow-[0_0_40px_rgba(255,255,255,0.8)]"></div>
            <div className="absolute w-[20px] h-[20px] bg-background rounded-full translate-x-3 -translate-y-3"></div>
          </div>
          
          {/* Floating tech accents */}
          <div className="absolute top-[20%] right-[10%] w-3 h-3 bg-white rounded-full animate-pulse"></div>
          <div className="absolute bottom-[30%] left-[10%] w-12 h-2 bg-white/20 rounded-full"></div>
          <div className="absolute top-[40%] text-white/5 font-display font-black text-9xl tracking-tighter mix-blend-overlay">
            {mode === 'basic' ? 'B1' : 'A2'}
          </div>
        </div>
      </div>
      
      {/* Decorative right-side glow */}
      <div className={clsx(
        "absolute right-0 bottom-0 w-[500px] h-full rounded-l-full blur-[100px] pointer-events-none transition-colors duration-1000 -z-10",
        mode === 'basic' ? "bg-accent/20" : "bg-purple-500/10"
      )}></div>
    </div>
  );
}
