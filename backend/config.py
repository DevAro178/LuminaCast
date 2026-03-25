"""
spinning-photon configuration
All service URLs, paths, and default settings.
"""
import os
from pathlib import Path

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
JOBS_DIR = PROJECT_ROOT / "jobs"
DB_PATH = PROJECT_ROOT / "lumina.db"

# Ensure jobs directory exists
JOBS_DIR.mkdir(exist_ok=True)

# --- Service URLs (all on same AWS instance) ---
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

EASY_DIFFUSION_URL = os.getenv("EASY_DIFFUSION_URL", "http://localhost:9000")

KOKORO_TTS_URL = os.getenv("KOKORO_TTS_URL", "http://localhost:8880")

# --- Video Defaults ---
VIDEO_FPS = 30
VIDEO_LONG_RESOLUTION = (1920, 1080)  # 16:9
VIDEO_SHORT_RESOLUTION = (1080, 1920)  # 9:16

# --- Easy Diffusion Defaults ---
SD_DEFAULT_PARAMS = {
    "seed": 42,
    "used_random_seed": True,
    "negative_prompt": "lowres, bad anatomy, bad hands, text, error, missing finger, extra digits, fewer digits, cropped, worst quality, low quality, low score, bad score, average score, signature, watermark, username, blurry, oversaturated, neon colors, overly bright, garish",
    "num_outputs": 1,
    "num_inference_steps": 40,
    "guidance_scale": 7.5,
    "vram_usage_level": "balanced",
    "sampler_name": "dpmpp_2m",
    "use_stable_diffusion_model": "animagine-xl-4.0",
    "clip_skip": False,
    "use_vae_model": "",
    "stream_progress_updates": True,
    "stream_image_progress": False,
    "show_only_filtered_image": True,
    "block_nsfw": False,
    "output_format": "jpeg",
    "output_quality": 95,
    "output_lossless": False,
    "metadata_output_format": "none",
    "active_tags": [],
    "inactive_tags": [],
    "enable_vae_tiling": True,
}

# --- TTS Defaults ---
TTS_VOICES = {
    "female": "af_heart",   # Kokoro female voice
    "male": "am_adam",      # Kokoro male voice
}

# --- Transition / Animation ---
CROSSFADE_DURATION = 0.3  # seconds
KEN_BURNS_ZOOM = 1.08     # 8% zoom over scene duration

# --- S3 Cloud Storage ---
S3_ENABLED = os.getenv("S3_ENABLED", "false").lower() == "true"
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "luminacast-public")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
S3_CUSTOM_DOMAIN = os.getenv("S3_CUSTOM_DOMAIN", "") # e.g. "cdn.luminacast.com"
