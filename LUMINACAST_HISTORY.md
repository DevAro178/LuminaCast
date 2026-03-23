# LuminaCast - Project Context & Sync History

**Purpose**: This document tracks the core architecture, recent problems solved, and current status of the LuminaCast (formerly spinning-photon) project. 
**Usage**: When syncing this repo to a new machine or starting a new AI agent session, provide this file as the exact starting context to resume work seamlessly.

---

## 1. Project Overview
**LuminaCast** is a fully automated AI video generation SaaS. It takes a text topic and generates a complete video (Short or Long form) featuring:
- **TTS Narration** (Kokoro TTS)
- **Anime-style Visuals per scene** (Easy Diffusion / Stable Diffusion XL)
- **Generated Script** (Ollama / Mistral)
- **Hardcoded Anime Styled ASS Subtitles**
- **Automated Video Stitching with Ken Burns pan/zoom** (MoviePy/FFmpeg)

## 2. Tech Stack & Architecture
- **Backend**: FastAPI, `aiosqlite` (SQLite), Python 3.12+ 
- **Frontend**: Vanilla HTML/CSS/JS (TailwindCSS via CDN)
- **Deployment**: Local testing -> AWS EC2 (Ubuntu). 
- **Process Orchestration**: 
  - `main.py`: Central FastAPI server. Serves frontend UI and handles API.
  - `database.py`: Manages jobs and scene metadata asynchronously.
  - `orchestrator.py`: Runs the background pipeline step-by-step.
  - `start_all.sh`: (AWS Specific) Bash script that boots 5 detached `screen` sessions to run Top, Ollama, Easy Diffusion, Kokoro, and LuminaCast simultaneously.
- **Paths & Config**: All API keys and local URLs are stored in `backend/config.py`. 

## 3. Deployment & Development Workflow
- **Development**: Local machine (Windows) for coding and logic changes. 
- **Testing/Deployment**: Remote AWS EC2 instance (Ubuntu).
  - Code is synced via `git pull origin main` on the remote server.
  - Services are restarted to apply changes.
- **Infrastructure**: Single-instance "Monolithic" setup.
  - All services run on the same machine for lower latency and simpler management.
  - Uses `GNU Screen` for persistent background sessions.
  - `start_all.sh` orchestrates the boot of: Ollama, Easy Diffusion, Kokoro TTS, and the FastAPI Backend.
- **Workflow Policy**:
  - **Feature Brunching**: Always develop new features or significant improvements on a separate `feature/` branch (e.g., `feature/audio-visual-enhancements`). Merge to `main` only after stability and manual verification.
  - **Context Maintenance**: Update `LUMINACAST_HISTORY.md` at every major milestone to ensure context for future agents.
## 4. Recently Solved Issues & Design Choices
If modifying the codebase, **do not undo these fixes**:

- **Easy Diffusion Image Format Bug**: The pipeline was failing because we requested PNGs but the web UI default (and API return) was JPEG. 
  *Fix*: Updated `config.py` and `image_generator.py` to strictly use `.jpg` everywhere. 
- **Asynchronous Easy Diffusion Polling Bug**: The `/render` endpoint wasn't returning base64 images; it returned a `task_id`.
  *Fix*: Refactored `image_generator.py` to take the task ID and poll the `http://.../image/stream/<task_id>` endpoint. 
- **NDJSON Stream Parsing Bug**: The `/image/stream/<task_id>` endpoint returned concatenated JSON strings (JSON Lines/NDJSON) like `{"step": 0...}{"status": "succeeded"}` which broke standard `response.json()` parsing.
  *Fix*: Wrote a robust text slicer in `image_generator.py` that isolates the `{"status": "succeeded"` block and parses it cleanly.
- **Kokoro TTS Speed**: The default Kokoro TTS speech (`1.0`) sounded way too fast and unnatural.
  *Fix*: Forced the default speed down to `0.85` in `tts_engine.py` and `kokoro_server.py`.
- **Stuck Jobs on Server Restart**: If the FastAPI server restarted mid-generation, the database kept jobs stuck in `Processing`, causing the frontend to poll infinitely.
  *Fix*: Added `db.mark_stuck_jobs_as_failed()` to the `lifespan` startup event in `main.py` to automatically clear out zombies.
- **Rebranding**: Renamed the entire project natively from "spinning-photon" to "LuminaCast" on 03/13/2026.

## 5. Improvement Log (03/13/2026+)

### Video Generation Architecture
LuminaCast handles two distinct types of video generation:
1.  **Short-Form / Basic Mode:** Single-shot LLM generation. The topic is sent to Mistral in one prompt, generating 7-17 scenes immediately.
2.  **Long-Form / Advanced Mode (Iterative Expansion):** A 3-tier process to bypass LLM output token limits and generate 120-150 scenes:
    - **Step 1:** Generate Outline (Chapters + Sections)
    - **Step 2:** User reviews and approves Outline in the UI
    - **Step 3:** Backend expands each section individually into 8-15 scenes, accumulating context, then merges them.

### Improvement 1: Smarter Script Prompts + Per-Scene Negative Prompts
- **`config.py`**: Replaced generic negative prompt with proven animagine-xl-4.0 defaults.
- **`script_generator.py`**: Updated prompts to include `negative_prompt` and enforce **Danbooru-style comma-separated tags** for `image_prompt`. This format is optimized for `animagine-xl-4.0`.
- **`image_generator.py`**: Now merges scene-level negative prompts with global defaults.

### Improvement 2: Toned-Down, Cinematic Visuals
- **`image_generator.py`**: Replaced `ANIME_STYLE_PREFIX` — removed "vibrant colors" and "high quality", added "masterpiece, best quality, cinematic lighting, warm color palette, atmospheric, meaningful composition". Balanced to avoid overly dark/dull output.
- **`config.py`**: Appended "oversaturated, neon colors, overly bright, garish" to global negative prompt.

### Improvement 3: Caption Chunking with Pop/Fade Transitions
- **`caption_generator.py`**: Complete rewrite. Added `_chunk_sentence(text, max_words=5)` that splits narration into 3-6 word phrases with natural break detection (commas, semicolons). Each chunk gets its own ASS dialogue event with pop-in scale animation (`\fscx80\fscy80\t(0,80,\fscx100\fscy100)`) and fade transitions (`\fad(120,80)`). Timing is word-count weighted with cumulative drift correction. Also pre-applied Montserrat font and wider outlines (4px) in ASS headers.

### Improvement 4: Premium Font + Dependency & Shutdown Scripts
- **`caption_generator.py`**: ASS headers already updated in Improvement 3 to use Montserrat ExtraBold (60pt long / 68pt short), 4px outline, 2px shadow.
- **`setup_dependencies.sh`** [NEW]: Checks/installs ffmpeg, `fonts-montserrat`, Python venv, and pip packages. Called by `start_all.sh` automatically.
- **`shutdown_all.sh`** [NEW]: Kills all LuminaCast screen sessions (`monitor`, `ollama`, `sd`, `kokoro`, `web`).
- **`start_all.sh`**: Now calls `setup_dependencies.sh` before starting services. Aborts if dependency check fails.

### Refinement: Dependency Script + Branch Policy
- **`setup_dependencies.sh`**: Enhanced with `python3-venv` and `sqlite3` checks to cover base system requirements.
- **Workflow**: Adopted separate branching for feature development (`feature/audio-visual-enhancements`).

## 6. Current State & Next Steps
**Status**: V1 Pipeline is fully functional and refined. Improvements 1-4 are complete. Improvement 5 (Music) is deferred. The `feature/audio-visual-enhancements` branch has been merged into `main`.

**Remaining Improvements (V1)**:
1. ~~Smarter Script Prompts~~ (Refined to tag-style) ✅
2. ~~Toned-Down Visuals~~ ✅
3. ~~Caption Chunking + Transitions~~ ✅
4. ~~Premium Font + Dependency Scripts~~ ✅
5. ~~Background Music~~ (Deferred to V2)

**Next Major Milestone**:
Transition to **LuminaCast Version 2** (Interactive Advanced/Basic Pipelines with a React Frontend). See `v2_roadmap.md` in the project artifacts for the complete architecture and flow design.

## 📅 March 14, 2026 - V2 Architectural Refactor & Pure API Transition

### 🚀 Major Milestones
- **Monolithic React to Modular Refactor**: Decoupled `App.jsx` into standalone components in `src/components/` (Sidebar, Topbar, MainHero, ContentGrid, ScriptReview, VisualReview, AssemblyView, JobsDashboard).
- **Global State Implementation**: Switched to **Zustand** for state management. Created `src/store/useStore.js` to handle navigation, job status, polling, and interactive pipeline steps.
- **Pure API Migration**: Removed static file serving from FastAPI. The backend now runs as an API-only service on port 8000, while the frontend is built into `dist/` for production web serving.
- **Granular Backend Pipeline**: Orchestrator refactored to support user-in-the-loop steps. Script drafting is now a discrete async step callable via `/api/v2/jobs/{id}/draft_script`.
- **Interactive Script Editing**: Implemented `PUT /api/v2/jobs/{id}/scenes` to persist user-edited narration and image tags.

### 🎨 UI/UX Excellence
- **Focus Mode**: Added a dynamic Hero transition that minimizes the header into a focus bar during the advanced scripting phase.
- **Custom Premium Components**: 
  - `Button.jsx`: Universal action button with variants and loading support.
  - `Select.jsx`: High-end custom dropdown replacing native OS elements, featuring glassmorphism and smooth animations.
- **Production Readiness**: Verified with `npm run build`, generating optimized bundles in `frontend-v2/dist`.

### 🛠️ Infrastructure & Scripts
- **Startup Automation**: Expanded `start_all.sh` to include a 6th screen session for the Vite development server (`npm run dev`).
- **Axios Integration**: Established `src/api/jobs.js` as the source of truth for all backend communications.

---

## 📅 March 15, 2026 - AI Revisions & UX Polish (Phase 7)

### 🚀 Major Milestones
- **AI Revisions Functional**: Implemented a complete feedback loop for script refining.
  - **Backend**: Added `POST /api/v2/jobs/{id}/revise_script` which accepts user feedback and existing scenes to generate a refined script.
  - **Orchestration**: Refactored `orchestrator.py` to support `revise_job_script`, handling scene deletion and re-insertion safely.
- **Dynamic Recent Videos Sidebar**: Built a "live" sidebar in the `ContentGrid` that fetches the 5 most recent successfully completed jobs.
  - Includes click-to-view deep linking directly into the Media Library.
- **Search-Driven Navigation**: Connected the Topbar search to global navigation. Typing in search now automatically transitions the user to the 'Jobs' tab and filters results in real-time.
- **Functional Media Library**: Completed the `MediaLibrary.jsx` component with a specialized sidebar and a full-featured video player for `output.mp4` streams. Added download support.

### 🎨 UI/UX Excellence
- **High-Contrast Prompt Styling**: Redesigned "Visual Tags" in the Script Review stage with a vibrant, premium look. Differentiates prompts from narrations to avoid user confusion about "disabled" inputs.
- **Flash-Free Transitions**: Adjusted state timing in `useStore.js` to ensure the loader remains active through the entire async drafting process. Eliminated the visual "flash" between input and review.
- **Custom Scrollbars & Micro-animations**: Added tailored scrollbars to script lists and pulse animations to "live" status indicators.

### 🛠️ Infrastructure & Git
- **Code Finalization**: Pushed all Phase 6 & 7 changes (8 files modified) to `origin main`.
- **API service layer**: Centralized all revision and search logic in `jobs.js` API service.

### 🛠️ Critical Fixes & Logic Refinements
- **Restored `generate_visuals` Endpoint**: Fixed a 404 error caused by an accidental deletion in `main.py`. Approving a script now correctly triggers image generation.
- **Smart AI Revision Detection**: Frontend now automatically compares the current script against the original. If edits are detected, it requests a revision that honors user changes; if not, it requests a general quality improvement.
- **Typography & Accessibility**: 
  - Header "SCRIPT REVIEW" now uses the `font-display` (Outfit) font.
  - Visual Tags inputs updated with high-contrast `text-white` and `bg-accent/30` for better visibility (no longer looks "disabled").
- **UX**: Removed the intrusive `prompt()` alert for AI revisions in favor of the automated "smart detect" logic.

---

## 📅 March 16, 2026 - Phonetic Stability & Pipeline Resilience (V3 Finalization)

### 🚀 Major Milestones
- **Definitive Phonetic Decoupling**: Completely removed the LLM from the phonetic generation bottleneck.
  - **The Problem**: LLMs consistently "over-phoneticized" common English, producing unnatural, broken speech.
  - **The Solution**: Removed all phonetic instructions from prompts. The backend now automatically duplicates `narration_text` into `narration_audio` by default.
  - **Manual Precision**: Preserved the "Phonetic Audio (TTS)" field in the UI, allowing users to provide surgical phonetic overrides for specific names or acronyms without AI interference.
- **Smart Image Pool & Intelligent Reuse**: Implemented a visual caching layer to drastically reduce SDXL generation time.
  - **Logic**: New `image_prompt` tags are compared against an `image_pool` table. If a tag overlap of **≥ 65%** is found, the system reuses the existing asset instead of generating a new one.
  - **Manual Override**: Manual tag edits or regenerations bypass this pool (95% threshold) to ensure user intent is always honored.
- **Frontend Resilience & State Synchronization**: Fixed "hanging" UI transitions caused by backend/frontend version mismatches.
  - **Standardization**: Converted all backend human-readable statuses (e.g. "Revising Script...") to machine-readable snake_case (e.g. `revising_script`).
  - **Resilience**: Updated `useStore.js` to handle both new snake_case and legacy strings (like "AI Visuals: X/Y"), ensuring the UI always transitions to the next stage regardless of minor API inconsistencies.

### 🎨 UI/UX Excellence
- **Live Visual Progress**: Updated `VisualReview.jsx` to support real-time card updates. In advanced mode, scenes now "pop in" with their generated images one by one as they finish, rather than waiting for the entire batch.
- **Media Library Script Viewer**: Added a highly requested "VIEW SCRIPT" feature to the Jobs Dashboard. Users can now audit the captions and visual tags of any completed job in a clean modal.
- **Bento Card Polish**: Fixed a regression where visual tag inputs in the review cards were read-only. They are now fully interactive.

### 🛠️ Infrastructure & Database
- **Robust Schema Migration**: Replaced the fragile `try/except` block in `database.py` with column-by-column `ALTER TABLE` checks. This prevents the system from skipping necessary migrations (like adding `narration_audio`) if other columns already exist.
- **Git Sync Strategy**: Established a workflow where critical UI patches are pushed to `main` and immediately pulled to the EC2 instance to keep the production mirror in sync.

---
*End of Context Document*
