import { create } from 'zustand';
import { jobsApi } from '../api/jobs';

const useStore = create((set, get) => ({
  // App Navigation State
  activeTab: 'create', // 'create', 'jobs', 'library'
  setActiveTab: (tab) => set({ activeTab: tab }),

  // Mode Selection
  mode: 'basic', // 'basic', 'advanced'
  setMode: (newMode) => set({ mode: newMode, advancedStep: 'input' }),
  
  // Advanced Pipeline Step
  advancedStep: 'input', // 'input', 'outline', 'script', 'visuals', 'assemble'
  setAdvancedStep: (step) => set({ advancedStep: step }),

  // Job Configuration
  videoType: 'short', // 'short', 'long'
  setVideoType: (type) => set({ videoType: type }),
  

  // Studio Settings
  voiceId: 'adam',
  setVoiceId: (id) => set({ voiceId: id }),
  sdModelId: null,
  setSdModelId: (id) => set({ sdModelId: id }),
  ttsExaggeration: 0.5,
  setTtsExaggeration: (v) => set({ ttsExaggeration: v }),
  ttsCfgWeight: 0.5,
  setTtsCfgWeight: (v) => set({ ttsCfgWeight: v }),
  ttsSpeed: 1.0,
  setTtsSpeed: (v) => set({ ttsSpeed: v }),
  effectIds: ['ken_burns'],
  setEffectIds: (ids) => set({ effectIds: ids }),
  captionStyle: 'chunked',
  setCaptionStyle: (style) => set({ captionStyle: style }),

  // Form State
  topicInput: '',
  setTopicInput: (val) => set({ topicInput: val }),

  userScript: '',
  setUserScript: (val) => set({ userScript: val }),

  isCustomScript: false,
  setIsCustomScript: (val) => set({ isCustomScript: val }),

  searchQuery: '',
  setSearchQuery: (query) => {
    set({ searchQuery: query });
    if (query && get().activeTab !== 'jobs') {
      set({ activeTab: 'jobs' });
    }
  },

  // Per-scene regeneration tracking (survives navigation)
  regeneratingScenes: new Set(),
  addRegeneratingScene: (idx) => set(s => ({ regeneratingScenes: new Set([...s.regeneratingScenes, idx]) })),
  removeRegeneratingScene: (idx) => set(s => { const n = new Set(s.regeneratingScenes); n.delete(idx); return { regeneratingScenes: n }; }),

  // Job Tracking State
  currentJobId: null,
  isGenerating: false,
  status: 'idle', // 'idle', 'generating_script', 'script_review', etc.
  progress: 0,
  
  // Script Data State (for editing)
  scriptScenes: [],
  setScriptScenes: (scenes) => set({ scriptScenes: scenes }),
  
  // Outline Data State
  outlineData: [],
  setOutlineData: (data) => set({ outlineData: data }),
  
  // Actions
  startJob: async () => {
    const { topicInput, userScript, isCustomScript, videoType, mode } = get();
    if (isCustomScript && !userScript) return;
    if (!isCustomScript && !topicInput) return;

    // Force videoType to short in basic mode
    const actualVideoType = mode === 'basic' ? 'short' : videoType;

    // Set generating BEFORE calling API to prevent flicker
    set({ isGenerating: true, progress: 0, status: 'queued', advancedStep: 'input', videoType: actualVideoType });

    try {
      const advancedConfig = {
        voice_id: get().voiceId,
        sd_model_id: get().sdModelId,
        tts_exaggeration: get().ttsExaggeration,
        tts_cfg_weight: get().ttsCfgWeight,
        tts_speed: get().ttsSpeed,
        effect_ids: JSON.stringify(get().effectIds),
        caption_style: get().captionStyle
      };

      const { job_id } = await jobsApi.createJob(
        isCustomScript ? (userScript.slice(0, 100) + "...") : topicInput, 
        actualVideoType, 
        mode,
        isCustomScript ? userScript : null,
        advancedConfig
      );
      set({ currentJobId: job_id });

      if (mode === 'advanced') {
        // Step 1: Draft script (or outline for long-form)
        await jobsApi.draftScript(job_id);
        const status = videoType === 'long' ? 'generating_outline' : 'generating_script';
        set({ status });
        get().startPolling(job_id);
      } else {
        // Basic mode: redirect to jobs page immediately
        set({ isGenerating: false, activeTab: 'jobs' });
      }
    } catch (error) {
      console.error("Failed to start job:", error);
      set({ isGenerating: false, status: 'idle' });
    }
  },

  reviseScript: async (feedback = "") => {
    const { currentJobId, scriptScenes, originalScript } = get();
    set({ isGenerating: true, status: 'revising_script' });
    
    // Logic: Compare current scriptScenes vs originalScript to see if user edited anything
    const isEdited = JSON.stringify(scriptScenes) !== JSON.stringify(originalScript);
    
    try {
      // Always send current scenes for reference, but adjust the message
      const defaultFeedback = isEdited 
        ? "Please refine the script while keeping and honoring my manual edits to the narration and tags." 
        : "Please regenerate a significantly better version of this script with more depth and engagement.";
      
      await jobsApi.reviseScript(currentJobId, feedback || defaultFeedback, scriptScenes);
      get().startPolling(currentJobId);
    } catch (error) {
      console.error("Failed to revise script:", error);
      set({ isGenerating: false, status: 'idle' });
    }
  },

  deleteScene: (index) => {
    set(state => {
      const newScenes = [...state.scriptScenes];
      newScenes.splice(index, 1);
      return { scriptScenes: newScenes };
    });
  },

  startPolling: (jobId) => {
    let failureCount = 0;
    const pollInterval = setInterval(async () => {
      try {
        const job = await jobsApi.getJobStatus(jobId);
        failureCount = 0; // Reset on success
        set({ status: job.status, progress: job.progress_pct });

        // Dynamic State Transitions
        if (job.status === 'outline_review') {
          const outline = await jobsApi.getOutline(jobId);
          set({
            outlineData: outline,
            advancedStep: 'outline',
            isGenerating: false,
            status: 'idle'
          });
          clearInterval(pollInterval);
        }
        else if (job.status === 'script_review' || job.status.includes('Drafted')) {
          const scenes = await jobsApi.getScenes(jobId);
          // Wait to hide loader until scenes are loaded to prevent flash
          set({ 
            scriptScenes: scenes,
            originalScript: [...scenes], // Capture original state for comparison
            advancedStep: 'script', 
            isGenerating: false,
            status: 'idle'
          });
          clearInterval(pollInterval);
        } 
        else if (job.status === 'generating_images' || job.status === 'visual_review' || job.status.includes('AI Visuals')) {
          set({ advancedStep: 'visuals' });
          if (job.status === 'visual_review') {
            set({ isGenerating: false, status: 'idle' });
            clearInterval(pollInterval); 
          }
        }
        else if (['revising_script', 'Revising Script...'].includes(job.status)) {
           set({ isGenerating: true, status: 'revising_script' });
        }
        else if (job.status === 'expanding_scenes') {
           set({ isGenerating: true, status: 'expanding_scenes' });
        }
        else if (['assembling', 'generating_audio', 'adding_captions', 'completed'].includes(job.status)) {
          set({ advancedStep: 'assemble' });
          if (job.status === 'completed') {
            // Redirect to Jobs tab when finished
            set({ 
              isGenerating: false,
              activeTab: 'jobs',
              currentJobId: null,
              mode: 'basic',
              advancedStep: 'input'
            });
            clearInterval(pollInterval);
          }
        }
        else if (job.status === 'error' || job.status === 'failed') {
          set({ isGenerating: false });
          clearInterval(pollInterval);
        }
      } catch (error) {
        failureCount++;
        console.error(`Polling error (attempt ${failureCount}):`, error);
        if (failureCount > 3) {
          clearInterval(pollInterval);
          set({ isGenerating: false });
        }
      }
    }, 2000);
  },

  approveOutline: async (editedItems) => {
    const { currentJobId } = get();
    set({ isGenerating: true, status: 'expanding_scenes' });
    try {
      if (editedItems && editedItems.length > 0) {
        await jobsApi.updateOutline(currentJobId, editedItems);
      }
      await jobsApi.expandOutline(currentJobId);
      get().startPolling(currentJobId);
    } catch (error) {
      console.error("Failed to approve outline:", error);
      set({ isGenerating: false, status: 'idle' });
    }
  },

  saveScriptEdits: async () => {
    const { currentJobId, scriptScenes } = get();
    set({ isGenerating: true });
    try {
      await jobsApi.updateScenes(currentJobId, scriptScenes);
      // Backend automatically sets approved_script=True in the endpoint
      // Now trigger visual generation
      await jobsApi.generateVisuals(currentJobId);
      set({ status: 'generating_images' });
      get().startPolling(currentJobId);
    } catch (error) {
       console.error("Failed to save script:", error);
       set({ isGenerating: false });
    }
  },

  updateSceneText: (index, text) => set((state) => ({
    scriptScenes: state.scriptScenes.map((s, i) => i === index ? { ...s, edited_text: text } : s)
  })),

  updateSceneAudio: (index, audio) => set((state) => ({
    scriptScenes: state.scriptScenes.map((s, i) => i === index ? { ...s, edited_audio: audio } : s)
  })),
  
  updateSceneTags: (index, tags) => set((state) => ({
    scriptScenes: state.scriptScenes.map((s, i) => i === index ? { ...s, edited_tags: tags } : s)
  })),

  // Resume an existing job from the Jobs dashboard into Focus Mode
  resumeJob: async (jobId) => {
    set({ isGenerating: true, currentJobId: jobId, activeTab: 'create', mode: 'advanced' });
    try {
      const job = await jobsApi.getJobStatus(jobId);
      set({ status: job.status, progress: job.progress_pct, videoType: job.video_type });

      if (job.status === 'outline_review') {
        const outline = await jobsApi.getOutline(jobId);
        set({
          outlineData: outline,
          advancedStep: 'outline',
          isGenerating: false,
          status: 'idle',
        });
      } else if (job.status === 'script_review') {
        const scenes = await jobsApi.getScenes(jobId);
        set({
          scriptScenes: scenes,
          originalScript: [...scenes],
          advancedStep: 'script',
          isGenerating: false,
          status: 'idle',
        });
      } else if (job.status === 'visual_review') {
        const scenes = await jobsApi.getScenes(jobId);
        set({
          scriptScenes: scenes,
          advancedStep: 'visuals',
          isGenerating: false,
        });
      } else if (job.status === 'generating_images') {
        set({ advancedStep: 'visuals', isGenerating: true });
        get().startPolling(jobId);
      } else if (job.status === 'expanding_scenes') {
        set({ advancedStep: 'outline', isGenerating: true });
        get().startPolling(jobId);
      } else if (job.status === 'generating_script' || job.status === 'generating_outline' || job.status === 'queued') {
        set({ advancedStep: 'input', isGenerating: true });
        get().startPolling(jobId);
      } else {
        set({ isGenerating: false, advancedStep: 'input' });
      }
    } catch (err) {
      console.error("Failed to resume job:", err);
      set({ isGenerating: false });
    }
  },

  // Calls the backend endpoint to force-resume a cancelled or stuck job
  forceRestartJob: async (jobId) => {
    try {
      await jobsApi.resumeJob(jobId);
      // After hitting the endpoint, just use the existing resumeJob to open it
      get().resumeJob(jobId);
    } catch (err) {
      console.error("Failed to force restart job:", err);
    }
  },
}));

export default useStore;
