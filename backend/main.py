"""
spinning-photon — FastAPI application
YouTube Video Automation SaaS
"""
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import database as db
from config import JOBS_DIR
from pipeline.orchestrator import run_pipeline

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("LuminaCast")


# --- App Lifecycle ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await db.init_db()
    # Cancel any jobs that were running when the server previously shut down
    await db.mark_stuck_jobs_as_failed()
    logger.info("✨ LuminaCast started")
    yield
    logger.info("LuminaCast shutting down")


app = FastAPI(
    title="LuminaCast",
    description="YouTube Video Automation SaaS",
    version="0.1.0",
    lifespan=lifespan,
)


# --- Request/Response Models ---

class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=500, description="Video topic or title")
    video_type: str = Field("short", pattern="^(long|short)$", description="'long' (5-10 min) or 'short' (30-60s)")
    voice_type: str = Field("female", pattern="^(female|male)$", description="Voice type for narration")


class JobResponse(BaseModel):
    id: str
    topic: str
    video_type: str
    voice_type: str
    status: str
    progress_pct: int
    total_scenes: int | None
    completed_scenes: int | None
    created_at: str
    completed_at: str | None
    error_message: str | None


# --- API Endpoints ---

@app.post("/api/generate", response_model=dict)
async def start_generation(request: GenerateRequest, background_tasks: BackgroundTasks):
    """Start a new video generation job."""
    job = await db.create_job(
        topic=request.topic,
        video_type=request.video_type,
        voice_type=request.voice_type,
    )

    # Run pipeline in background
    background_tasks.add_task(
        run_pipeline,
        job_id=job["id"],
        topic=request.topic,
        video_type=request.video_type,
        voice_type=request.voice_type,
    )

    logger.info(f"Started job {job['id']}: {request.topic}")
    return {"job_id": job["id"], "status": "queued"}


@app.get("/api/jobs", response_model=list[dict])
async def list_all_jobs():
    """List all jobs, newest first."""
    jobs = await db.list_jobs()
    return jobs


@app.get("/api/jobs/{job_id}")
async def get_job_details(job_id: str):
    """Get job details including scene breakdown."""
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    scenes = await db.get_scenes(job_id)
    return {**job, "scenes": scenes}


@app.get("/api/jobs/{job_id}/download")
async def download_video(job_id: str):
    """Download the completed video."""
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Video not yet completed")

    output_path = job.get("output_path")
    if not output_path or not Path(output_path).exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    filename = f"spinning-photon-{job_id}.mp4"
    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename=filename,
    )


@app.get("/api/jobs/{job_id}/script")
async def get_job_script(job_id: str):
    """Get the generated script JSON for a job."""
    script_path = JOBS_DIR / job_id / "script.json"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="Script not found")
    import json
    return json.loads(script_path.read_text(encoding="utf-8"))


# --- Serve Frontend ---

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    @app.get("/")
    async def serve_dashboard():
        index_path = FRONTEND_DIR / "index.html"
        return FileResponse(str(index_path))

    # Mount static files AFTER explicit routes so API routes take priority
    # Serve at root so relative paths (./index.css, ./app.js) resolve correctly
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")


# --- Entry point ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
