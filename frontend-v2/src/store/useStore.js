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
  advancedStep: 'input', // 'input', 'script', 'visuals', 'assemble'
  setAdvancedStep: (step) => set({ advancedStep: step }),

  // Job Configuration
  videoType: 'short', // 'short', 'long'
  setVideoType: (type) => set({ videoType: type }),
  
  voiceType: 'female', // 'male', 'female'
  setVoiceType: (type) => set({ voiceType: type }),

  // Form State
  topicInput: '',
  setTopicInput: (val) => set({ topicInput: val }),

  // Job Tracking State
  currentJobId: null,
  isGenerating: false,
  status: 'idle', // 'idle', 'generating_script', 'script_review', etc.
  progress: 0,
  
  // Script Data State (for editing)
  scriptScenes: [],
  setScriptScenes: (scenes) => set({ scriptScenes: scenes }),
  
  // Actions
  startJob: async () => {
    const { topicInput, videoType, voiceType, mode } = get();
    if (!topicInput) return;

    set({ isGenerating: true, progress: 0 });

    try {
      const { job_id } = await jobsApi.createJob(topicInput, videoType, voiceType, mode);
      set({ currentJobId: job_id });

      if (mode === 'advanced') {
        // Step 1: Draft script
        await jobsApi.draftScript(job_id);
        set({ status: 'generating_script' });
        get().startPolling(job_id);
      } else {
        // Basic mode: redirect to jobs page immediately
        set({ isGenerating: false });
        set({ activeTab: 'jobs' });
      }
    } catch (error) {
      console.error("Failed to start job:", error);
      set({ isGenerating: false });
    }
  },

  startPolling: (jobId) => {
    const pollInterval = setInterval(async () => {
      try {
        const job = await jobsApi.getJobStatus(jobId);
        set({ status: job.status, progress: job.progress_pct });

        // Dynamic State Transitions
        if (job.status === 'script_review') {
          const scenes = await jobsApi.getScenes(jobId);
          set({ scriptScenes: scenes, advancedStep: 'script', isGenerating: false });
          clearInterval(pollInterval); // Stop polling until user approves script
        } 
        else if (job.status === 'generating_images' || job.status === 'visual_review') {
          set({ advancedStep: 'visuals' });
          if (job.status === 'visual_review') {
            set({ isGenerating: false });
            clearInterval(pollInterval); // Stop polling until user approves visuals
          }
        }
        else if (job.status === 'assembling' || job.status === 'completed') {
          set({ advancedStep: 'assemble' });
          if (job.status === 'completed') {
            set({ isGenerating: false });
            clearInterval(pollInterval);
          }
        }
        else if (job.status === 'error' || job.status === 'failed') {
          set({ isGenerating: false });
          clearInterval(pollInterval);
        }
      } catch (error) {
        console.error("Polling error:", error);
        clearInterval(pollInterval);
        set({ isGenerating: false });
      }
    }, 2000);
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
  
  updateSceneTags: (index, tags) => set((state) => ({
    scriptScenes: state.scriptScenes.map((s, i) => i === index ? { ...s, edited_tags: tags } : s)
  })),
}));

export default useStore;
