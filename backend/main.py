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
from fastapi.middleware.cors import CORSMiddleware

import database as db
from config import JOBS_DIR
from pipeline.orchestrator import (
    generate_job_script, 
    generate_job_visuals, 
    assemble_job_video,
    run_legacy_pipeline,
    expand_outline_to_scenes
)

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated assets (frames, final videos)
app.mount("/api/v2/assets/jobs", StaticFiles(directory=JOBS_DIR), name="jobs_assets")


# --- Request/Response Models ---

class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=2000, description="Video topic or title")
    video_type: str = Field("short", pattern="^(long|short)$", description="'long' (5-10 min) or 'short' (30-60s)")
    voice_type: str = Field("female", pattern="^(female|male)$", description="Voice type for narration")


class JobResponse(BaseModel):
    id: str
    topic: str
    video_type: str
    voice_type: str
    workflow_mode: str
    status: str
    progress_pct: int
    total_scenes: int | None
    completed_scenes: int | None
    approved_script: bool
    approved_visuals: bool
    created_at: str
    completed_at: str | None
    error_message: str | None

class SceneUpdate(BaseModel):
    scene_index: int
    edited_text: str | None = None
    edited_tags: str | None = None
    edited_audio: str | None = None

class ScenesUpdateRequest(BaseModel):
    scenes: list[SceneUpdate]

class GenerateV2Request(BaseModel):
    topic: str = Field(..., min_length=3, max_length=2000, description="Video topic or title")
    video_type: str = Field("short", pattern="^(long|short)$", description="'long' (5-10 min) or 'short' (30-60s)")
    voice_type: str = Field("female", pattern="^(female|male)$", description="Voice type for narration")
    workflow_mode: str = Field("advanced", pattern="^(basic|advanced)$")


# --- API Endpoints (V1 / Legacy) ---

@app.post("/api/generate", response_model=dict)
async def start_generation(request: GenerateRequest, background_tasks: BackgroundTasks):
    """Start a new video generation job (V1 monolithic)."""
    job = await db.create_job(
        topic=request.topic,
        video_type=request.video_type,
        voice_type=request.voice_type,
    )

    # Run pipeline in background
    background_tasks.add_task(
        run_legacy_pipeline,
        job_id=job["id"],
        topic=request.topic,
        video_type=request.video_type,
        voice_type=request.voice_type,
    )

    logger.info(f"Started job {job['id']}: {request.topic}")
    return {"job_id": job["id"], "status": "queued"}


# --- API Endpoints (V2 / Interactive) ---

@app.post("/api/v2/jobs", response_model=dict)
async def create_job_v2(request: GenerateV2Request, background_tasks: BackgroundTasks):
    """Initialize a V2 job. Auto-runs if basic mode."""
    job = await db.create_job(
        topic=request.topic,
        video_type=request.video_type,
        voice_type=request.voice_type,
        workflow_mode=request.workflow_mode,
    )
    
    if request.workflow_mode == "basic":
        # Basic mode just runs the legacy fully automated chain in the background
        background_tasks.add_task(
            run_legacy_pipeline,
            job_id=job["id"],
            topic=request.topic,
            video_type=request.video_type,
            voice_type=request.voice_type,
        )
    
    # Advanced mode returns immediately so the UI can sequence it
    return {"job_id": job["id"], "workflow_mode": job["workflow_mode"], "status": job["status"]}

@app.post("/api/v2/jobs/{job_id}/draft_script")
async def draft_job_script(job_id: str, background_tasks: BackgroundTasks):
    """Triggers the LLM script generation phase."""
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
        
    background_tasks.add_task(generate_job_script, job_id, job["topic"], job["video_type"])
    # For long-form advanced, the status will be 'generating_outline' instead of 'generating_script'
    return {"status": "generating_script"}


@app.post("/api/v2/jobs/{job_id}/resume")
async def resume_cancelled_job(job_id: str, background_tasks: BackgroundTasks):
    """Resumes a cancelled or failed job from its last known pipeline stage."""
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    from pipeline.orchestrator import resume_job
    background_tasks.add_task(resume_job, job_id)
    return {"status": "resuming"}


# --- Outline Endpoints (Long-Form Only) ---

class OutlineItemUpdate(BaseModel):
    id: str
    title: str
    description: str | None = None

class OutlineUpdateRequest(BaseModel):
    items: list[OutlineItemUpdate]

@app.get("/api/v2/jobs/{job_id}/outline")
async def get_job_outline(job_id: str):
    """Fetch the outline (chapters + sections) for a job."""
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    outline = await db.get_outline(job_id)
    return outline

@app.put("/api/v2/jobs/{job_id}/outline")
async def update_job_outline(job_id: str, request: OutlineUpdateRequest):
    """Save user edits to the outline."""
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    for item in request.items:
        update_data = {"title": item.title}
        if item.description is not None:
            update_data["description"] = item.description
        await db.update_outline_item(item.id, **update_data)
    return {"status": "success"}

@app.post("/api/v2/jobs/{job_id}/expand_outline")
async def expand_job_outline(job_id: str, background_tasks: BackgroundTasks):
    """Approve outline and trigger section-by-section scene expansion."""
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    # Needs to be imported inside the scope or globally
    from pipeline.orchestrator import expand_outline_to_scenes
    background_tasks.add_task(expand_outline_to_scenes, job_id)
    return {"status": "expanding_scenes"}

@app.get("/api/v2/jobs/{job_id}/scenes", response_model=list[dict])
async def get_job_scenes(job_id: str):
    """Fetch all scenes for a specific job."""
    scenes = await db.get_scenes(job_id)
    if not scenes:
        # It's possible script isn't drafted yet
        return []
    return scenes

@app.put("/api/v2/jobs/{job_id}/scenes")
async def update_job_scenes(job_id: str, request: ScenesUpdateRequest):
    """Saves user edits to the script text or image tags."""
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
        
    db_scenes = await db.get_scenes(job_id)
    scene_map = {s["scene_index"]: s["id"] for s in db_scenes}
    
    for scene_update in request.scenes:
        if scene_update.scene_index in scene_map:
            scene_id = scene_map[scene_update.scene_index]
            update_data = {}
            if scene_update.edited_text is not None:
                update_data["edited_text"] = scene_update.edited_text
            if scene_update.edited_tags is not None:
                update_data["edited_tags"] = scene_update.edited_tags
            if scene_update.edited_audio is not None:
                update_data["edited_audio"] = scene_update.edited_audio
            if update_data:
                await db.update_scene(scene_id, **update_data)
            
    await db.update_job(job_id, approved_script=True)
    return {"status": "success"}

class ReviseScriptRequest(BaseModel):
    feedback: str | None = ""
    scenes: list[dict] | None = None

@app.post("/api/v2/jobs/{job_id}/revise_script")
async def revise_job_script_endpoint(job_id: str, request: ReviseScriptRequest, background_tasks: BackgroundTasks):
    """Triggers the LLM to revise the script based on feedback or edits."""
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
        
    # We'll need a new function in orchestrator
    from pipeline.orchestrator import revise_job_script
    background_tasks.add_task(revise_job_script, job_id, job["topic"], request.feedback, request.scenes)
    return {"status": "revising_script"}

@app.post("/api/v2/jobs/{job_id}/generate_visuals")
async def start_visual_generation(job_id: str, background_tasks: BackgroundTasks):
    """Triggers Stable Diffusion generation for the approved scenes."""
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
        
    background_tasks.add_task(generate_job_visuals, job_id)
    return {"status": "generating_images"}

@app.post("/api/v2/jobs/{job_id}/assemble")
async def assemble_final_video(job_id: str, background_tasks: BackgroundTasks):
    """Triggers TTS, Captions, and MoviePy assembly."""
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
        
    await db.update_job(job_id, approved_visuals=True, status="assembling")
    background_tasks.add_task(assemble_job_video, job_id)
    return {"status": "assembling"}

class RegenerateSceneRequest(BaseModel):
    edited_tags: str | None = None

@app.post("/api/v2/jobs/{job_id}/scenes/{scene_index}/regenerate_image")
async def regenerate_job_scene_image(job_id: str, scene_index: int, request: RegenerateSceneRequest = None):
    """Triggers image re-generation for a single scene."""
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
        
    custom_tags = request.edited_tags if request else None
    from pipeline.orchestrator import regenerate_single_scene
    await regenerate_single_scene(job_id, scene_index, custom_tags)
    return {"status": "regenerating_complete", "scene_index": scene_index}


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


# --- Entry point ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_excludes=["jobs/*", "*.db", "temp/*"],
    )
