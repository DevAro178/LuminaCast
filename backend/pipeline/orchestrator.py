"""
Pipeline Orchestrator — Chains all generation steps together.
Creates a job, runs the pipeline, and updates DB at each stage.
"""
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

import database as db
from config import JOBS_DIR
from pipeline.script_generator import generate_script
from pipeline.image_generator import generate_images_for_scenes
from pipeline.tts_engine import generate_speech_for_scenes
from pipeline.caption_generator import generate_captions_from_timestamps
from pipeline.video_assembler import assemble_video

logger = logging.getLogger(__name__)


async def generate_job_script(job_id: str, topic: str, video_type: str) -> dict:
    """
    Step 1: Generate the narrative script and scene breakdowns using the LLM.
    Returns the script data dictionary.
    """
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        await db.update_job(job_id, status="generating_script", progress_pct=5)
        logger.info(f"[{job_id}] Step 1: Generating script...")

        script_data = await generate_script(topic, video_type)
        scenes = script_data["scenes"]

        # Save script to file for reference
        script_path = job_dir / "script.json"
        script_path.write_text(json.dumps(script_data, indent=2), encoding="utf-8")

        # Save scenes to DB
        await db.create_scenes(job_id, scenes)
        await db.update_job(
            job_id,
            status=f"Drafted {len(scenes)} scenes" if "advanced" else "generating_images",
            progress_pct=15,
            total_scenes=len(scenes),
        )
        # Force the transition status to 'script_review' if in advanced mode
        if "advanced":
            await db.update_job(job_id, status="script_review")
            
        logger.info(f"[{job_id}] Script generated: {len(scenes)} scenes")
        return script_data
        
    except Exception as e:
        logger.exception(f"[{job_id}] Script generation failed: {e}")
        await db.update_job(job_id, status="error", error_message=str(e))
        raise

async def generate_job_visuals(job_id: str):
    """
    Step 2: Generate base images from the (potentially manually edited) scene scripts.
    """
    job_dir = JOBS_DIR / job_id
    job = await db.get_job(job_id)
    video_type = job["video_type"]
    
    # We retrieve the state-of-truth scenes directly from the DB, applying any manual edits.
    db_scenes = await db.get_scenes(job_id)
    # Reconstruct the scenes array exactly as the pipeline expects it
    scenes = []
    for rec in db_scenes:
        scenes.append({
            "narration_text": rec["edited_text"] or rec["narration_text"],
            "image_prompt": rec["edited_tags"] or rec["image_prompt"]
        })

    try:
        await db.update_job(job_id, status="generating_images", progress_pct=15)
        logger.info(f"[{job_id}] Step 2: Generating {len(scenes)} images...")

        async def on_image_progress(completed, total):
            pct = 15 + int((completed / total) * 35)  # 15% → 50%
            await db.update_job(
                job_id, 
                progress_pct=pct, 
                completed_scenes=completed,
                status=f"AI Visuals: {completed}/{total}"
            )

        image_paths = await generate_images_for_scenes(
            scenes, job_dir, video_type, on_progress=on_image_progress
        )

        # Update DB scene records with actual image paths
        for scene_rec, img_path in zip(db_scenes, image_paths):
            await db.update_scene(scene_rec["id"], image_path=img_path)

        await db.update_job(job_id, status="visual_review" if job["workflow_mode"] == "advanced" else "generating_audio", progress_pct=50)
        logger.info(f"[{job_id}] Images generated: {len(image_paths)} files")
        
    except Exception as e:
        logger.exception(f"[{job_id}] Image generation failed: {e}")
        await db.update_job(job_id, status="error", error_message=str(e))
        raise

async def assemble_job_video(job_id: str):
    """
    Step 3: Generate Kokoro TTS, ASS Captions, and render the final MP4 composite.
    """
    job_dir = JOBS_DIR / job_id
    job = await db.get_job(job_id)
    video_type = job["video_type"]
    voice_type = job["voice_type"]
    
    db_scenes = await db.get_scenes(job_id)
    scenes = []
    image_paths = []
    for rec in db_scenes:
        scenes.append({
            "narration_text": rec["edited_text"] or rec["narration_text"],
            "image_prompt": rec["edited_tags"] or rec["image_prompt"]
        })
        image_paths.append(rec["image_path"])

    try:
        # ---- Step 3.1: Generate TTS Audio ----
        await db.update_job(job_id, status="generating_audio", progress_pct=50)
        logger.info(f"[{job_id}] Step 3.1: Generating TTS audio...")

        async def on_tts_progress(completed, total):
            pct = 50 + int((completed / total) * 25)  # 50% → 75%
            await db.update_job(
                job_id, 
                progress_pct=pct,
                status=f"Generating Narration: {completed}/{total}"
            )

        tts_results = await generate_speech_for_scenes(
            scenes, job_dir, voice_type, on_progress=on_tts_progress
        )

        # Update scene records with audio paths and durations
        for scene_rec, tts in zip(db_scenes, tts_results):
            await db.update_scene(
                scene_rec["id"],
                audio_path=tts["audio_path"],
                duration_seconds=tts["duration"],
            )

        # ---- Step 3.2: Generate Captions ----
        await db.update_job(job_id, status="Captions & Graphics...", progress_pct=78)
        logger.info(f"[{job_id}] Step 3.2: Generating captions...")

        caption_path = job_dir / "captions.ass"
        generate_captions_from_timestamps(
            scenes, tts_results, caption_path, video_type
        )

        # ---- Step 3.3: Assemble Video ----
        await db.update_job(job_id, status="Final Rendering & Mixing...", progress_pct=82)
        logger.info(f"[{job_id}] Step 3.3: Assembling video...")

        output_path = job_dir / "output.mp4"
        assemble_video(
            scenes=scenes,
            tts_results=tts_results,
            image_paths=image_paths,
            caption_path=str(caption_path),
            output_path=output_path,
            video_type=video_type,
        )

        # ---- Done ----
        now = datetime.now(timezone.utc).isoformat()
        await db.update_job(
            job_id,
            status="completed",
            progress_pct=100,
            completed_at=now,
            output_path=str(output_path),
        )
        logger.info(f"[{job_id}] ✅ Pipeline complete! Video at {output_path}")

    except Exception as e:
        logger.exception(f"[{job_id}] Assembly failed: {e}")
        await db.update_job(job_id, status="error", error_message=str(e))
        raise

async def run_legacy_pipeline(job_id: str, topic: str, video_type: str, voice_type: str):
    """
    Wrapper for V1 backward-compatibility or basic mode auto-run.
    Executes the three new modular steps sequentially.
    """
    try:
        await generate_job_script(job_id, topic, video_type)
        await generate_job_visuals(job_id)
        await assemble_job_video(job_id)
    except:
        pass # Logging and error updating is handled by child functions

async def revise_job_script(job_id: str, topic: str, feedback: str = "", current_scenes: list = None):
    """Orchestrates script revision."""
    try:
        await db.update_job(job_id, status="Revising Script...", progress_pct=10)
        
        from pipeline.script_generator import revise_script
        script_data = await revise_script(topic, feedback, current_scenes)
        
        scenes = script_data["scenes"]
        
        # Clear old scenes
        await db.delete_scenes_for_job(job_id)
        
        # Create new scenes
        await db.create_scenes(job_id, scenes)
        
        await db.update_job(
            job_id, 
            status="script_review", 
            progress_pct=15, 
            total_scenes=len(scenes)
        )
        logger.info(f"[{job_id}] Script revised: {len(scenes)} scenes")
    except Exception as e:
        logger.error(f"[{job_id}] Revision failed: {e}")
        await db.update_job(job_id, status="error", error_message=str(e))
