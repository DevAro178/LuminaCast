/**
 * spinning-photon — Frontend Application
 * Dashboard logic: form handling, job polling, video playback
 */

const API_BASE = '';  // Same origin
const POLL_INTERVAL = 2000;  // 2 seconds

// --- State ---
let currentVideoType = 'short';
let currentVoiceType = 'female';
let pollTimer = null;

// --- DOM Elements ---
const form = document.getElementById('generate-form');
const topicInput = document.getElementById('topic-input');
const btnGenerate = document.getElementById('btn-generate');
const btnRefresh = document.getElementById('btn-refresh');
const jobsList = document.getElementById('jobs-list');
const emptyState = document.getElementById('empty-state');
const modalOverlay = document.getElementById('modal-overlay');
const modalTitle = document.getElementById('modal-title');
const modalClose = document.getElementById('modal-close');
const videoPlayer = document.getElementById('video-player');
const downloadLink = document.getElementById('download-link');

// --- Toggle Buttons ---
function setupToggles() {
    document.querySelectorAll('.toggle-group').forEach(group => {
        group.querySelectorAll('.toggle-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                group.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                const value = btn.dataset.value;
                if (group.id === 'video-type-toggle') currentVideoType = value;
                if (group.id === 'voice-type-toggle') currentVoiceType = value;
            });
        });
    });
}

// --- Form Submit ---
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const topic = topicInput.value.trim();
    if (!topic) return;

    btnGenerate.disabled = true;
    btnGenerate.classList.add('loading');
    btnGenerate.querySelector('.btn-icon').textContent = '⟳';

    try {
        const res = await fetch(`${API_BASE}/api/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                topic,
                video_type: currentVideoType,
                voice_type: currentVoiceType,
            }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Failed to start generation');
        }

        topicInput.value = '';
        await loadJobs();
        startPolling();
    } catch (err) {
        alert('Error: ' + err.message);
    } finally {
        btnGenerate.disabled = false;
        btnGenerate.classList.remove('loading');
        btnGenerate.querySelector('.btn-icon').textContent = '▶';
    }
});

// --- Load Jobs ---
async function loadJobs() {
    try {
        const res = await fetch(`${API_BASE}/api/jobs`);
        if (!res.ok) throw new Error('Failed to load jobs');
        const jobs = await res.json();

        if (jobs.length === 0) {
            jobsList.innerHTML = '';
            jobsList.appendChild(emptyState);
            emptyState.style.display = 'block';
            return;
        }

        emptyState.style.display = 'none';
        renderJobs(jobs);

        // Check if any jobs are still running
        const hasActiveJobs = jobs.some(j =>
            !['completed', 'error'].includes(j.status)
        );
        if (hasActiveJobs) {
            startPolling();
        } else {
            stopPolling();
        }
    } catch (err) {
        console.error('Failed to load jobs:', err);
    }
}

// --- Render Jobs ---
function renderJobs(jobs) {
    const cards = jobs.map(job => createJobCard(job)).join('');
    jobsList.innerHTML = cards;

    // Reattach event listeners
    jobsList.querySelectorAll('.btn-play').forEach(btn => {
        btn.addEventListener('click', () => openVideoModal(btn.dataset.jobId, btn.dataset.topic));
    });
    jobsList.querySelectorAll('.btn-script').forEach(btn => {
        btn.addEventListener('click', () => viewScript(btn.dataset.jobId));
    });
}

function createJobCard(job) {
    const statusInfo = getStatusInfo(job.status);
    const isActive = !['completed', 'error'].includes(job.status);
    const timeAgo = formatTimeAgo(job.created_at);

    const scenesText = job.total_scenes
        ? `${job.completed_scenes || 0}/${job.total_scenes} scenes`
        : '';

    let actionsHtml = '';
    if (job.status === 'completed') {
        actionsHtml = `
            <button class="btn-action btn-play" data-job-id="${job.id}" data-topic="${escapeHtml(job.topic)}">
                ▶ Play
            </button>
            <button class="btn-action btn-script" data-job-id="${job.id}">
                📄 Script
            </button>
        `;
    } else if (job.status === 'error') {
        actionsHtml = `
            <span class="btn-action" style="color: var(--accent-danger); border-color: var(--accent-danger); cursor: default;"
                  title="${escapeHtml(job.error_message || 'Unknown error')}">
                ⚠ Error
            </span>
        `;
    }

    return `
        <div class="job-card">
            <div class="job-card-header">
                <div class="job-topic">${escapeHtml(job.topic)}</div>
                <div class="job-badges">
                    <span class="badge badge-${job.video_type}">${job.video_type}</span>
                    <span class="badge badge-${job.voice_type}">${job.voice_type}</span>
                </div>
            </div>

            <div class="job-progress">
                <div class="progress-bar">
                    <div class="progress-fill ${isActive ? 'active' : ''}"
                         style="width: ${job.progress_pct}%"></div>
                </div>
            </div>

            <div class="job-footer">
                <div class="job-status status-${job.status}">
                    <span class="status-icon">${statusInfo.icon}</span>
                    <span class="status-text">${statusInfo.label}</span>
                    <span class="job-scenes-count">${scenesText}</span>
                </div>
                <div class="job-meta">
                    <span class="job-time">${timeAgo}</span>
                    <div class="job-actions">${actionsHtml}</div>
                </div>
            </div>
        </div>
    `;
}

function getStatusInfo(status) {
    const map = {
        'queued': { icon: '⏳', label: 'Queued' },
        'generating_script': { icon: '📝', label: 'Writing Script...' },
        'generating_images': { icon: '🎨', label: 'Generating Images...' },
        'generating_audio': { icon: '🔊', label: 'Generating Audio...' },
        'generating_captions': { icon: '📑', label: 'Creating Captions...' },
        'assembling_video': { icon: '🎬', label: 'Assembling Video...' },
        'completed': { icon: '✅', label: 'Completed' },
        'error': { icon: '❌', label: 'Failed' },
    };
    return map[status] || { icon: '❓', label: status };
}

// --- Polling ---
function startPolling() {
    if (pollTimer) return;
    pollTimer = setInterval(loadJobs, POLL_INTERVAL);
}

function stopPolling() {
    if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
    }
}

// --- Video Modal ---
function openVideoModal(jobId, topic) {
    modalTitle.textContent = topic;
    videoPlayer.src = `${API_BASE}/api/jobs/${jobId}/download`;
    downloadLink.href = `${API_BASE}/api/jobs/${jobId}/download`;
    modalOverlay.style.visibility = 'visible';
    modalOverlay.classList.add('visible');
}

function closeVideoModal() {
    modalOverlay.classList.remove('visible');
    modalOverlay.style.visibility = 'hidden';
    videoPlayer.pause();
    videoPlayer.src = '';
}

modalClose.addEventListener('click', closeVideoModal);
modalOverlay.addEventListener('click', (e) => {
    if (e.target === modalOverlay) closeVideoModal();
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeVideoModal();
});

// --- View Script ---
async function viewScript(jobId) {
    try {
        const res = await fetch(`${API_BASE}/api/jobs/${jobId}/script`);
        if (!res.ok) throw new Error('Script not found');
        const script = await res.json();

        const text = script.scenes
            .map((s, i) => `[Scene ${i + 1}]\n${s.narration_text}\n🎨 ${s.image_prompt}`)
            .join('\n\n');

        // Open in a new window
        const win = window.open('', '_blank', 'width=600,height=700');
        win.document.write(`
            <html><head><title>Script — ${escapeHtml(script.title || jobId)}</title>
            <style>
                body { font-family: 'Inter', sans-serif; background: #0a0a12; color: #f0f0f8; 
                       padding: 2rem; line-height: 1.7; white-space: pre-wrap; }
                h1 { font-size: 1.2rem; margin-bottom: 1rem; color: #a855f7; }
            </style></head>
            <body><h1>${escapeHtml(script.title || 'Generated Script')}</h1>${escapeHtml(text)}</body></html>
        `);
    } catch (err) {
        alert('Could not load script: ' + err.message);
    }
}

// --- Utilities ---
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatTimeAgo(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
}

// --- Refresh Button ---
btnRefresh.addEventListener('click', loadJobs);

// --- Init ---
setupToggles();
loadJobs();
