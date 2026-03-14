import axios from 'axios';
import config from '../config';

const api = axios.create({
  baseURL: config.apiBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const jobsApi = {
  // Initialize a new job
  createJob: async (topic, videoType, voiceType, workflowMode) => {
    const response = await api.post('/api/v2/jobs', {
      topic,
      video_type: videoType,
      voice_type: voiceType,
      workflow_mode: workflowMode,
    });
    return response.data;
  },

  // Trigger script drafting
  draftScript: async (jobId) => {
    const response = await api.post(`/api/v2/jobs/${jobId}/draft_script`);
    return response.data;
  },

  // Get job status/details (generic endpoint)
  getJobStatus: async (jobId) => {
    const response = await api.get(`/api/jobs/${jobId}`);
    return response.data;
  },

  // Get scenes for a job
  getScenes: async (jobId) => {
    const response = await api.get(`/api/v2/jobs/${jobId}/scenes`);
    return response.data;
  },

  // Update scenes (save edits)
  updateScenes: async (jobId, scenes) => {
    const response = await api.put(`/api/v2/jobs/${jobId}/scenes`, {
      scenes: scenes.map(s => ({
        scene_index: s.scene_index,
        edited_text: s.edited_text || s.narration_text,
        edited_tags: s.edited_tags || s.image_prompt,
      })),
    });
    return response.data;
  },

  // Trigger visual generation
  generateVisuals: async (jobId) => {
    const response = await api.post(`/api/v2/jobs/${jobId}/generate_visuals`);
    return response.data;
  },

  // Trigger final assembly
  assemble: async (jobId) => {
    const response = await api.post(`/api/v2/jobs/${jobId}/assemble`);
    return response.data;
  },

  // AI Revision
  reviseScript: async (jobId, feedback = "", scenes = []) => {
    const response = await api.post(`/api/v2/jobs/${jobId}/revise_script`, {
      feedback,
      scenes: scenes.map(s => ({
        scene_index: s.scene_index,
        narration_text: s.edited_text || s.narration_text,
        image_prompt: s.edited_tags || s.image_prompt,
      })),
    });
    return response.data;
  },

  // List all jobs
  listJobs: async () => {
    const response = await api.get('/api/jobs');
    return response.data;
  },
};
