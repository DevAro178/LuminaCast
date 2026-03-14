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

---
*End of Context Document*
