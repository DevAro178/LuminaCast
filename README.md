# spinning-photon 🎬

YouTube Video Automation SaaS — generate AI-powered videos with anime-style visuals.

## Stack

| Component | Tool |
|-----------|------|
| Script writing | Ollama (Mistral) |
| Image generation | Easy Diffusion (animagine-xl-4.0) |
| Text-to-speech | Kokoro TTS |
| Video assembly | MoviePy + FFmpeg |
| Backend | FastAPI + SQLite |
| Frontend | Vanilla HTML/CSS/JS |

## Setup

```bash
# Install Python dependencies
cd backend
pip install -r requirements.txt

# Make sure FFmpeg is installed
ffmpeg -version

# Start the server
python main.py
```

Open `http://<your-ip>:8000` in your browser.

## Services Required

| Service | Port | Status |
|---------|------|--------|
| spinning-photon | 8000 | This app |
| Ollama (Mistral) | 11434 | `ollama serve` |
| Easy Diffusion | 9000 | Start via Easy Diffusion UI |
| Kokoro TTS | 8880 | TBD |

## API

- `POST /api/generate` — Start a video generation job
- `GET /api/jobs` — List all jobs
- `GET /api/jobs/{id}` — Job details + scenes
- `GET /api/jobs/{id}/download` — Download finished video
- `GET /api/jobs/{id}/script` — View generated script
