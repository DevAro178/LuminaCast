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


async def run_pipeline(job_id: str, topic: str, video_type: str, voice_type: str):
    """
    Execute the full video generation pipeline for a job.

    Steps:
    1. Generate script (Ollama Mistral)
    2. Generate images (Easy Diffusion)
    3. Generate TTS audio (Kokoro)
    4. Generate captions (ASS subtitles)
    5. Assemble video (MoviePy + FFmpeg)
    """
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    try:
        # ---- Step 1: Generate Script ----
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
            status="generating_images",
            progress_pct=15,
            total_scenes=len(scenes),
        )
        logger.info(f"[{job_id}] Script generated: {len(scenes)} scenes")

        # ---- Step 2: Generate Images ----
        logger.info(f"[{job_id}] Step 2: Generating {len(scenes)} images...")

        async def on_image_progress(completed, total):
            pct = 15 + int((completed / total) * 35)  # 15% → 50%
            await db.update_job(job_id, progress_pct=pct, completed_scenes=completed)

        image_paths = await generate_images_for_scenes(
            scenes, job_dir, video_type, on_progress=on_image_progress
        )

        # Update scene records with image paths
        db_scenes = await db.get_scenes(job_id)
        for scene_rec, img_path in zip(db_scenes, image_paths):
            await db.update_scene(scene_rec["id"], image_path=img_path)

        await db.update_job(job_id, status="generating_audio", progress_pct=50)
        logger.info(f"[{job_id}] Images generated: {len(image_paths)} files")

        # ---- Step 3: Generate TTS Audio ----
        logger.info(f"[{job_id}] Step 3: Generating TTS audio...")

        async def on_tts_progress(completed, total):
            pct = 50 + int((completed / total) * 25)  # 50% → 75%
            await db.update_job(job_id, progress_pct=pct)

        tts_results = await generate_speech_for_scenes(
            scenes, job_dir, voice_type, on_progress=on_tts_progress
        )

        # Update scene records with audio paths and durations
        db_scenes = await db.get_scenes(job_id)
        for scene_rec, tts in zip(db_scenes, tts_results):
            await db.update_scene(
                scene_rec["id"],
                audio_path=tts["audio_path"],
                duration_seconds=tts["duration"],
            )

        await db.update_job(job_id, status="generating_captions", progress_pct=78)
        logger.info(f"[{job_id}] TTS audio generated")

        # ---- Step 4: Generate Captions ----
        logger.info(f"[{job_id}] Step 4: Generating captions...")

        caption_path = job_dir / "captions.ass"
        generate_captions_from_timestamps(
            scenes, tts_results, caption_path, video_type
        )

        await db.update_job(job_id, status="assembling_video", progress_pct=82)
        logger.info(f"[{job_id}] Captions generated")

        # ---- Step 5: Assemble Video ----
        logger.info(f"[{job_id}] Step 5: Assembling video...")

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
        logger.exception(f"[{job_id}] Pipeline failed: {e}")
        await db.update_job(
            job_id,
            status="error",
            error_message=str(e),
        )
        raise
