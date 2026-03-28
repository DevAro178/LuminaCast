"""
Standalone Chatterbox TTS API Server Wrapper
Runs Resemble AI's Chatterbox model as a FastAPI service.
"""
import io
import os
import torch
import torchaudio as ta
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from chatterbox.tts import ChatterboxTTS

app = FastAPI(title="Chatterbox TTS Server")

# --- Configuration ---
# Root directory of the repository
ROOT_DIR = Path(__file__).resolve().parent
# User's specified NVMe path for model storage
NVME_BASE = Path("/opt/dlami/nvme")
MODEL_DIR = NVME_BASE / "models" / "chatterbox"
VOICE_SAMPLE = ROOT_DIR / "sample.wav"

model = None

@app.on_event("startup")
async def startup_event():
    global model
    print(f"🚀 Initializing Chatterbox TTS...")
    
    # Ensure model directory exists
    # Note: from_pretrained will download to default cache if we don't handle it,
    # but we will try to force it if possible or rely on the env var if the lib supports it.
    # For Chatterbox, it usually uses torch's default cache. 
    # Let's set the torch home to NVMe to be absolutely sure.
    os.environ["TORCH_HOME"] = str(NVME_BASE / "torch_cache")
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    try:
        # Load the model
        model = ChatterboxTTS.from_pretrained(device=device)
        print("✅ Chatterbox model loaded! Ready to generate expressive speech.")
        
        # Verify voice sample exists
        if not VOICE_SAMPLE.exists():
            print(f"⚠️ Warning: Reference voice sample not found at {VOICE_SAMPLE}. Zero-shot cloning will use defaults.")
        else:
            print(f"🎙️ Using reference voice for cloning: {VOICE_SAMPLE}")
            
    except Exception as e:
        print(f"❌ Failed to load Chatterbox model: {e}")

class TTSRequest(BaseModel):
    text: str
    voice: str = "default"
    speed: float = 1.0  # Chatterbox uses cfg_weight and exaggeration instead of simple speed usually
    exaggeration: float = 0.5
    cfg_weight: float = 0.5

@app.post("/api/generate")
async def generate_speech(req: TTSRequest):
    if not model:
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    
    try:
        # Generate audio
        # Using the user's sample.wav if it exists for zero-shot cloning
        audio_prompt = str(VOICE_SAMPLE) if VOICE_SAMPLE.exists() else None
        
        # Chatterbox .generate returns a tensor [1, T]
        wav = model.generate(
            text=req.text,
            audio_prompt_path=audio_prompt,
            exaggeration=req.exaggeration,
            cfg_weight=req.cfg_weight
        )
        
        # Convert tensor to WAV bytes
        buffer = io.BytesIO()
        # model.sr is the sample rate (usually 24000 or 44100)
        ta.save(buffer, wav.cpu(), model.sr, format="WAV")
        buffer.seek(0)
        
        return StreamingResponse(buffer, media_type="audio/wav")
        
    except Exception as e:
        print(f"TTS Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Port 8881 as configured in backend/config.py
    uvicorn.run(app, host="0.0.0.0", port=8881)
