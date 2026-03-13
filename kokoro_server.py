"""
Standalone Kokoro TTS API Server Wrapper
Runs kokoro-onnx as a FastAPI service simulating the API we expect.
"""
import io
import os
import urllib.request
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import soundfile as sf
from kokoro_onnx import Kokoro

app = FastAPI(title="Kokoro TTS Server Wrapper")

# Initialize models path
root_dir = Path(__file__).parent.parent
model_path = root_dir / "kokoro-v1.0.onnx"
voices_path = root_dir / "voices-v1.0.bin"

model_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
voices_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

kokoro = None

def download_file(url: str, dest: Path):
    if not dest.exists():
        print(f"Downloading {dest.name}...")
        urllib.request.urlretrieve(url, dest)
        print(f"Downloaded {dest.name}")

@app.on_event("startup")
async def startup_event():
    global kokoro
    # Ensure model files exist before starting
    download_file(model_url, model_path)
    download_file(voices_url, voices_path)
    print("Loading Kokoro model...")
    kokoro = Kokoro(str(model_path), str(voices_path))
    print("Kokoro model loaded! Ready to generate speech.")

class TTSRequest(BaseModel):
    text: str
    voice: str = "af_heart"
    speed: float = 0.85
    response_format: str = "wav"

@app.post("/api/generate")
async def generate_speech(req: TTSRequest):
    if not kokoro:
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    try:
        samples, sample_rate = kokoro.create(
            req.text, voice=req.voice, speed=req.speed, lang="en-us"
        )
        # Write to in-memory bytes buffer
        buffer = io.BytesIO()
        sf.write(buffer, samples, sample_rate, format="WAV")
        buffer.seek(0)
        
        return StreamingResponse(buffer, media_type="audio/wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # 8880 is what we configured in spinning-photon/backend/config.py
    uvicorn.run(app, host="0.0.0.0", port=8880)
