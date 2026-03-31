"""
Pipeline Orchestrator — Chains all generation steps together.
Creates a job, runs the pipeline, and updates DB at each stage.
"""
import json
import logging
import asyncio
import difflib
import shutil
from pathlib import Path
from datetime import datetime, timezone

import database as db
from config import JOBS_DIR
from pipeline.script_generator import generate_script, generate_outline, expand_section_to_scenes, segment_user_script
from pipeline.image_generator import generate_image, _create_fallback_image
from pipeline.tts_engine import generate_speech_for_scenes
from pipeline.caption_generator import generate_captions_from_timestamps
from pipeline.video_assembler import assemble_video
from utils.storage import storage

logger = logging.getLogger(__name__)


async def generate_job_script(job_id: str, topic: str, video_type: str) -> dict:
    """
    Step 1: Generate the narrative script and scene breakdowns using the LLM.
    For long-form advanced mode, this generates an OUTLINE instead (iterative expansion).
    For short-form, this generates scenes directly (unchanged behavior).
    """
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    job = await db.get_job(job_id)
    vtype = str(video_type).strip().lower()
    is_long_advanced = vtype == "long" and job and job.get("workflow_mode") == "advanced"
    
    try:
        if job and job.get("user_script"):
            # Custom Script flow
            await db.update_job(job_id, status="segmenting_script", progress_pct=5)
            logger.info(f"[{job_id}] Step 1: Segmenting user script...")
            script_data = await segment_user_script(job.get("user_script"))
        elif is_long_advanced:
            # Long-form advanced: generate outline (chapters + sections) for user approval
            return await generate_job_outline(job_id, topic)
        else:
            # Standard generation flow
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
            status="script_review",
            progress_pct=15,
            total_scenes=len(scenes),
        )
            
        logger.info(f"[{job_id}] Script generated: {len(scenes)} scenes")
        return script_data
        
    except Exception as e:
        logger.exception(f"[{job_id}] Script generation failed: {e}")
        await db.update_job(job_id, status="error", error_message=str(e))
        raise


async def generate_job_outline(job_id: str, topic: str) -> dict:
    """
    Step 1a (Long-form only): Generate chapters + sections outline for user approval.
    """
    try:
        await db.update_job(job_id, status="generating_outline", progress_pct=5)
        logger.info(f"[{job_id}] Step 1a: Generating outline...")

        outline_data = await generate_outline(topic)

        # Save outline to file for reference
        job_dir = JOBS_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        outline_path = job_dir / "outline.json"
        outline_path.write_text(json.dumps(outline_data, indent=2), encoding="utf-8")

        # Save to DB
        await db.delete_outline_for_job(job_id)  # Clear any previous outline
        await db.create_outline_items(job_id, outline_data["chapters"])
        await db.update_job(job_id, status="outline_review", progress_pct=10)

        total_sections = sum(len(ch.get("sections", [])) for ch in outline_data["chapters"])
        logger.info(f"[{job_id}] Outline generated: {len(outline_data['chapters'])} chapters, {total_sections} sections")
        return outline_data

    except Exception as e:
        logger.exception(f"[{job_id}] Outline generation failed: {e}")
        await db.update_job(job_id, status="error", error_message=str(e))
        raise


async def expand_outline_to_scenes(job_id: str) -> dict:
    """
    Step 1b (Long-form only): Expand approved outline into full scenes.
    Makes one LLM call per section, accumulating context as it goes.
    """
    try:
        job = await db.get_job(job_id)
        topic = job["topic"]
        
        await db.update_job(job_id, status="expanding_scenes", progress_pct=10)
        logger.info(f"[{job_id}] Step 1b: Expanding outline to scenes...")

        # Get the outline from DB and rebuild chapter/section structure
        outline_items = await db.get_outline(job_id)
        chapters = []
        current_chapter = None
        for item in outline_items:
            if item["type"] == "chapter":
                current_chapter = {
                    "title": item["title"],
                    "description": item.get("description", ""),
                    "sections": []
                }
                chapters.append(current_chapter)
            elif item["type"] == "section" and current_chapter is not None:
                current_chapter["sections"].append({
                    "title": item["title"],
                    "description": item.get("description", "")
                })

        # Count total sections for progress tracking
        total_sections = sum(len(ch["sections"]) for ch in chapters)
        completed_sections = 0
        all_scenes = []
        context_parts = []

        for chapter in chapters:
            for section in chapter["sections"]:
                # Build running context from previous sections
                context = "\n".join(context_parts[-5:]) if context_parts else ""

                scenes = await expand_section_to_scenes(
                    topic=topic,
                    chapter_title=chapter["title"],
                    chapter_desc=chapter["description"],
                    section_title=section["title"],
                    section_desc=section["description"],
                    context=context
                )
                all_scenes.extend(scenes)

                # Add to context for next section
                section_summary = f"- {chapter['title']} > {section['title']}: {len(scenes)} scenes covering {section['description']}"
                context_parts.append(section_summary)

                completed_sections += 1
                pct = 10 + int((completed_sections / total_sections) * 5)  # 10% → 15%
                await db.update_job(job_id, progress_pct=pct, status=f"expanding_scenes")
                logger.info(f"[{job_id}] Expanded section {completed_sections}/{total_sections}: {len(scenes)} scenes")

        # Save the full scene list to DB
        await db.delete_scenes_for_job(job_id)
        await db.create_scenes(job_id, all_scenes)

        # Save to file for reference
        job_dir = JOBS_DIR / job_id
        script_data = {"title": topic, "scenes": all_scenes}
        script_path = job_dir / "script.json"
        script_path.write_text(json.dumps(script_data, indent=2), encoding="utf-8")

        await db.update_job(
            job_id,
            status="script_review",
            progress_pct=15,
            total_scenes=len(all_scenes),
        )
        logger.info(f"[{job_id}] Outline expanded: {len(all_scenes)} total scenes from {total_sections} sections")
        return script_data

    except Exception as e:
        logger.exception(f"[{job_id}] Outline expansion failed: {e}")
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
        sd_model = None
        if job.get("sd_model_id"):
            sd_model = await db.get_sd_model(job["sd_model_id"])
            
        await db.update_job(job_id, status="generating_images", progress_pct=15)
        logger.info(f"[{job_id}] Step 2: Generating {len(scenes)} images (testing against smart pool)...")

        async def on_image_progress(completed, total):
            pct = 15 + int((completed / total) * 35)  # 15% → 50%
            await db.update_job(
                job_id, 
                progress_pct=pct, 
                completed_scenes=completed,
                status="generating_images"
            )

        images_dir = job_dir / "images"
        if images_dir.exists():
            # Clear existing images before generation to prevent indexing/sync bugs after scene removals
            logger.info(f"[{job_id}] Clearing stale images directory...")
            try:
                shutil.rmtree(images_dir)
            except Exception as e:
                logger.warning(f"Could not fully clear images dir: {e}")
        images_dir.mkdir(parents=True, exist_ok=True)
        
        image_paths = []
        total = len(scenes)
        pool_images = await db.get_all_pool_images()

        # Helper function for CPU-bound SequenceMatcher
        def _find_best_match(target_prompt, pool_images, threshold):
            import difflib
            best_m = None
            best_r = 0.0
            for p_img in pool_images:
                ratio = difflib.SequenceMatcher(None, target_prompt, p_img["image_tags"]).ratio()
                if ratio > best_r:
                    best_r = ratio
                    best_m = p_img
            if best_r >= threshold:
                return best_m, best_r
            return None, 0.0

        for i, (scene, scene_rec) in enumerate(zip(scenes, db_scenes)):
            image_path = images_dir / f"scene_{i:03d}.jpg"
            
            if image_path.exists() and image_path.stat().st_size > 0:
                logger.info(f"[{job_id}] Scene {i} image already exists on disk, skipping generation.")
                image_paths.append(str(image_path))
                await on_image_progress(i + 1, total)
                continue
                
            target_prompt = scene["image_prompt"]
            is_manual_override = bool(scene_rec["edited_tags"])
            similarity_threshold = 0.95 if is_manual_override else 0.65

            # Offload CPU-bound loop to a thread so it doesn't block the asyncio event loop
            best_match, best_ratio = await asyncio.to_thread(
                _find_best_match, target_prompt, pool_images, similarity_threshold
            )

            if best_match:
                logger.info(f"[{job_id}] Scene {i} reused image from pool (similarity: {best_ratio:.2f})")
                try:
                    # Offload synchronous disk I/O to a thread
                    await asyncio.to_thread(shutil.copy2, best_match["file_path"], image_path)
                    image_paths.append(str(image_path))
                except Exception as e:
                    logger.error(f"Failed to copy pool image: {e}")
                    best_match = None

            if not best_match:
                try:
                    path = await generate_image(
                        prompt=target_prompt,
                        output_path=image_path,
                        video_type=video_type,
                        negative_prompt=scene.get("negative_prompt", ""),
                        sd_model_override=sd_model
                    )
                    image_paths.append(path)
                    # Add newly generated image to the global pool!
                    await db.add_to_image_pool(target_prompt, path, job_id)
                except Exception as e:
                    logger.error(f"[{job_id}] Failed to generate image for scene {i}: {e}")
                    path = _create_fallback_image(image_path, video_type)
                    image_paths.append(path)

            await on_image_progress(i + 1, total)

        # Update DB scene records with S3 URLs (if enabled) or local paths
        for i, (scene_rec, local_img_path) in enumerate(zip(db_scenes, image_paths)):
            s3_key = f"jobs/{job_id}/images/scene_{i:03d}.jpg"
            # upload_file returns URL if enabled, else local_path string
            final_img_path = await asyncio.to_thread(storage.upload_file, local_img_path, s3_key)
            await db.update_scene(scene_rec["id"], image_path=final_img_path)

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
    local_image_paths = []
    for i, rec in enumerate(db_scenes):
        scenes.append({
            "narration_text": rec["edited_text"] or rec["narration_text"],
            "narration_audio": rec["edited_audio"] or rec["narration_audio"] or rec["edited_text"] or rec["narration_text"],
            "image_prompt": rec["edited_tags"] or rec["image_prompt"]
        })
        # Use local paths for MoviePy assembly (high performance)
        local_img = job_dir / "images" / f"scene_{i:03d}.jpg"
        local_image_paths.append(str(local_img))

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

        voice_id = job.get("voice_id", "adam")
        tts_exag = job.get("tts_exaggeration", 0.5)
        tts_cfg = job.get("tts_cfg_weight", 0.5)
        tts_speed = job.get("tts_speed", 1.0)

        tts_results = await generate_speech_for_scenes(
            scenes, job_dir, voice_id=voice_id, 
            exaggeration=tts_exag, cfg_weight=tts_cfg, speed=tts_speed,
            on_progress=on_tts_progress
        )

        # Update scene records with audio paths (S3 URLs if enabled) and durations
        for i, (scene_rec, tts) in enumerate(zip(db_scenes, tts_results)):
            local_audio_path = tts["audio_path"]
            s3_key = f"jobs/{job_id}/audio/scene_{i:03d}.mp3"
            final_audio_path = await asyncio.to_thread(storage.upload_file, local_audio_path, s3_key)
            
            await db.update_scene(
                scene_rec["id"],
                audio_path=final_audio_path,
                duration_seconds=tts["duration"],
            )

        # ---- Step 3.2: Generate Captions ----
        await db.update_job(job_id, status="Captions & Graphics...", progress_pct=78)
        logger.info(f"[{job_id}] Step 3.2: Generating captions...")

        caption_path = job_dir / "captions.ass"
        style = job.get("caption_style", "chunked")
        generate_captions_from_timestamps(
            scenes, tts_results, caption_path, video_type, style=style
        )

        # ---- Step 3.3: Assemble Video ----
        await db.update_job(job_id, status="Final Rendering & Mixing...", progress_pct=82)
        logger.info(f"[{job_id}] Step 3.3: Assembling video...")

        output_path = job_dir / "output.mp4"
        
        # Capture current event loop for threadsafe callback
        main_loop = asyncio.get_running_loop()
        async def update_progress(p):
            await db.update_job(job_id, progress_pct=p)

        try:
            effects = json.loads(job.get("effect_ids", '["ken_burns"]'))
        except (TypeError, json.JSONDecodeError):
            effects = ["ken_burns"]

        await asyncio.to_thread(
            assemble_video,
            scenes=scenes,
            tts_results=tts_results,
            image_paths=local_image_paths,
            caption_path=str(caption_path),
            output_path=output_path,
            video_type=video_type,
            effect_ids=effects,
            progress_callback=lambda p: asyncio.run_coroutine_threadsafe(update_progress(p), main_loop)
        )

        # ---- Done ----
        s3_video_key = f"jobs/{job_id}/results/output.mp4"
        final_video_url = await asyncio.to_thread(storage.upload_file, output_path, s3_video_key)
        
        now = datetime.now(timezone.utc).isoformat()
        await db.update_job(
            job_id,
            status="completed",
            progress_pct=100,
            completed_at=now,
            output_path=final_video_url,
        )
        logger.info(f"[{job_id}] ✅ Pipeline complete! Video at {final_video_url}")

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
        await db.update_job(job_id, status="revising_script", progress_pct=10)
        
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
async def regenerate_single_scene(job_id: str, scene_index: int, custom_tags: str = None):
    """
    Re-generates the image for a single scene without touching others.
    Useful for the Visual Review 'Regenerate' button.
    """
    job = await db.get_job(job_id)
    job_dir = JOBS_DIR / job_id
    video_type = job["video_type"]
    
    db_scenes = await db.get_scenes(job_id)
    # Find the specific scene
    target_scene = next((s for s in db_scenes if s["scene_index"] == scene_index), None)
    if not target_scene:
        logger.error(f"[{job_id}] Scene {scene_index} not found for regeneration")
        return
    
    image_prompt = custom_tags or target_scene["edited_tags"] or target_scene["image_prompt"]
    negative_prompt = target_scene.get("negative_prompt", "")
    
    if custom_tags:
        await db.update_scene(target_scene["id"], edited_tags=custom_tags)
    
    # Save to the same indexed path so the frontend always uses the same URL
    image_path = job_dir / "images" / f"scene_{scene_index:03d}.jpg"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        logger.info(f"[{job_id}] Regenerating scene {scene_index}: {image_prompt[:60]}...")
        from pipeline.image_generator import generate_image
        local_path = await generate_image(
            prompt=image_prompt,
            output_path=image_path,
            video_type=video_type,
            negative_prompt=negative_prompt,
        )
        
        # Upload to S3 if enabled
        s3_key = f"jobs/{job_id}/images/scene_{scene_index:03d}.jpg"
        from utils.storage import storage
        final_path = await asyncio.to_thread(storage.upload_file, local_path, s3_key)
        
        await db.update_scene(target_scene["id"], image_path=final_path)
        logger.info(f"[{job_id}] Scene {scene_index} regenerated → {final_path}")
    except Exception as e:
        logger.exception(f"[{job_id}] Failed to regenerate scene {scene_index}: {e}")

async def resume_job(job_id: str):
    """
    Resumes a job from where it left off.
    Checks the current status in the database and triggers the appropriate pipeline step.
    """
    job = await db.get_job(job_id)
    if not job:
        logger.error(f"[{job_id}] Cannot resume: Job not found.")
        return
        
    status = job["status"]
    logger.info(f"[{job_id}] Resuming job from status: {status}")

    if job["workflow_mode"] == "basic":
        # Basic mode just reruns from scratch if it failed
        await run_legacy_pipeline(job_id, job["topic"], job["video_type"], job.get("voice_type", "male"))
        return

    # Advanced Mode Resume Logic
    if status in ("generating_outline", "error", "failed"):
        # Since 'failed' obscures the exact step it crashed on, deduce it from DB state:
        outline = await db.get_outline(job_id)
        if not outline:
            await generate_job_outline(job_id, job["topic"])
            return

        scenes = await db.get_scenes(job_id)
        if not scenes:
            await expand_outline_to_scenes(job_id)
            return

        # If it crashed at generating_images, generating_audio, or assembling video,
        # it is perfectly safe to call generate_job_visuals because it is completely idempotent,
        # and if all images exist, it will instantly move to generating_audio!
        logger.info(f"[{job_id}] Attempting to resume by triggering image generation pipeline natively.")
        await generate_job_visuals(job_id)
        return
            
    elif status in ("expanding_scenes", "outline_review"):
        scenes = await db.get_scenes(job_id)
        if not scenes:
            await expand_outline_to_scenes(job_id)
        else:
            logger.info(f"[{job_id}] Scenes already exist, skipping to script_review")
            await db.update_job(job_id, status="script_review")
            
    elif status in ("generating_images", "script_review"):
        await generate_job_visuals(job_id)
        
    elif status in ("generating_audio", "visual_review", "visuals_review"):
        # `assemble_job_video` handles both TTS generation and final video composite seamlessly
        await assemble_job_video(job_id)
        
    elif status in ("assembling_video", "audio_review"):
        await assemble_job_video(job_id)
        
    else:
        logger.info(f"[{job_id}] Job state '{status}' does not need resuming.")
