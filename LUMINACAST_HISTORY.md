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

## 3. Recently Solved Issues & Design Choices
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

## 4. Current State & Next Steps
**Status**: The pipeline is fully functional end-to-end. It successfully completes the database jobs and generates synchronized MP4 files with audio, captions, and images.

**Upcoming/Planned Improvements to Tackle Next**:
1. **Visual Style Tuning**: Adjusting Easy Diffusion prompts/negative prompts to ensure a more consistent anime aesthetic and stop weird artifacts.
2. **Caption Aesthetics**: Upgrading the generated `.ass` subtitle files to have flashier animations or word-tracking colors.
3. **Video Pacing**: Tweaking the Ken Burns effects, crossfade durations, or perhaps adding background lo-fi music.
4. **Script Polish**: Fine-tuning the Ollama Mistral prompt to write punchier TikTok hooks and better pacing.

---
*End of Context Document*
