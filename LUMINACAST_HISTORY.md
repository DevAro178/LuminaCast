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
- **`config.py`**: Replaced generic negative prompt with proven animagine-xl-4.0 defaults: `lowres, bad anatomy, bad hands, text, error, missing finger, extra digits, fewer digits, cropped, worst quality, low quality, low score, bad score, average score, signature, watermark, username, blurry`.
- **`script_generator.py`**: Updated system prompt to instruct Mistral to generate richer `image_prompt` values (lighting direction, camera angles, symbolism, composition) and a `negative_prompt` per scene. Updated JSON schema in both long/short form prompts. Added graceful fallback if LLM omits `negative_prompt`.
- **`image_generator.py`**: `generate_image()` now accepts a `negative_prompt` parameter, merges it with global defaults, and passes the combined value to Easy Diffusion. `generate_images_for_scenes()` passes `scene["negative_prompt"]` through.

### Improvement 2: Toned-Down, Cinematic Visuals
- **`image_generator.py`**: Replaced `ANIME_STYLE_PREFIX` — removed "vibrant colors" and "high quality", added "masterpiece, best quality, cinematic lighting, warm color palette, atmospheric, meaningful composition". Balanced to avoid overly dark/dull output.
- **`config.py`**: Appended "oversaturated, neon colors, overly bright, garish" to global negative prompt.

## 6. Current State & Next Steps
**Status**: Pipeline fully functional. Improvements 1-2 complete.

**Remaining Improvements**:
1. ~~Smarter Script Prompts~~ ✅
2. ~~Toned-Down Visuals~~ ✅
3. **Caption Chunking + Transitions** — break sentences into 3-6 word chunks with pop/fade effects
4. **Premium Font (Montserrat ExtraBold)** — plus `setup_dependencies.sh` and `shutdown_all.sh`
5. **Background Music** — lo-fi tracks at ~15-20% volume (low priority, user provides files)

---
*End of Context Document*
