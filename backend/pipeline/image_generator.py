"""
Image Generator — Easy Diffusion (Stable Diffusion XL) integration.
Generates one anime-style image per scene via POST /render.
"""
import httpx
import base64
import logging
import asyncio
from pathlib import Path
from config import EASY_DIFFUSION_URL, SD_DEFAULT_PARAMS, VIDEO_LONG_RESOLUTION, VIDEO_SHORT_RESOLUTION

logger = logging.getLogger(__name__)

# Anime style prefix applied to all prompts for visual consistency
ANIME_STYLE_PREFIX = (
    "anime art style, masterpiece, best quality, detailed illustration, "
    "cinematic lighting, atmospheric, "
    "meaningful composition, clean lines, studio quality, "
)


async def generate_image(
    prompt: str,
    output_path: str | Path,
    video_type: str = "long",
    negative_prompt: str = "",
    session_id: str = "spinning-photon",
    sd_model_override: dict = None,
) -> str:
    """
    Generate a single anime-style image via Easy Diffusion.

    Args:
        prompt: Image description from the script
        output_path: Path to save the generated JPG
        video_type: 'long' (1920x1080) or 'short' (1080x1920)
        session_id: Easy Diffusion session ID
        sd_model_override: Optional DB config containing model_key, sampler_name, etc.

    Returns:
        Path to the saved image file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Set resolution based on video type
    if video_type == "short":
        width, height = VIDEO_SHORT_RESOLUTION
    else:
        width, height = VIDEO_LONG_RESOLUTION

    # Build the full prompt with anime style prefix
    full_prompt = f"{ANIME_STYLE_PREFIX}{prompt}"

    # Merge scene-level negative prompt with global defaults
    merged_negative = SD_DEFAULT_PARAMS.get("negative_prompt", "")
    if negative_prompt:
        merged_negative = f"{merged_negative}, {negative_prompt}"

    # Build the base payload matching Easy Diffusion's expected format
    import random
    payload = {
        **SD_DEFAULT_PARAMS,
        "prompt": full_prompt,
        "original_prompt": full_prompt,
        "negative_prompt": merged_negative,
        "width": width,
        "height": height,
        "session_id": session_id,
        "seed": random.randint(0, 2**32 - 1),  # fresh random seed every call
        "used_random_seed": True,
    }

    # Apply database-driven model overrides if provided
    if sd_model_override:
        if "model_key" in sd_model_override:
            payload["use_stable_diffusion_model"] = sd_model_override["model_key"]
        
        override_keys = [
            "sampler_name", "num_inference_steps", "guidance_scale", 
            "vram_usage_level", "clip_skip"
        ]
        for key in override_keys:
            if key in sd_model_override and sd_model_override[key] is not None:
                payload[key] = sd_model_override[key]

    logger.info(f"Generating image: {prompt[:80]}...")

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{EASY_DIFFUSION_URL}/render",
            json=payload,
        )
        response.raise_for_status()
        initial_result = response.json()

    # Easy Diffusion /render is asynchronous. It returns a task ID.
    task_id = initial_result.get("task")
    if not task_id:
        raise ValueError(f"No task ID returned from Easy Diffusion. Response: {initial_result}")

    # Poll for completion
    stream_url = f"{EASY_DIFFUSION_URL}/image/stream/{task_id}"
    logger.info(f"Polling {stream_url} for completion...")

    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            try:
                poll_resp = await client.get(stream_url)
                poll_resp.raise_for_status()

                text_data = poll_resp.text
                
                # The response at 200 OK could be a clean JSON object {"status": "succeeded", ...}
                # or it could be partial stream chunks: {"step": ...}
                # First try just parsing it directly if it's well-formed
                import json
                try:
                    result = poll_resp.json()
                except Exception:
                    # If it's a concatenated stream, find the last succeeded block
                    if '"status": "succeeded"' in text_data:
                        succeeded_idx = text_data.rfind('{"status": "succeeded"')
                        if succeeded_idx != -1:
                            try:
                                result = json.loads(text_data[succeeded_idx:])
                            except Exception:
                                # Fallback: Wait and let next poll maybe return cleaner JSON
                                await asyncio.sleep(2)
                                continue
                    else:
                        await asyncio.sleep(2)
                        continue

                status = result.get("status", "")
                if status == "succeeded":
                    break
                elif status == "failed":
                    raise ValueError(f"Easy Diffusion rendering failed. Task: {task_id}")
                
                # Still rendering
                await asyncio.sleep(2)
                continue
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 425:
                    # 425 Too Early means it's still rendering. Keep polling.
                    await asyncio.sleep(2)
                    continue
                else:
                    raise  # Re-raise if it's a different HTTP error
            except Exception as e:
                # Catch connection errors, etc., and keep polling
                logger.warning(f"Error polling stream: {e}. Retrying...")
                await asyncio.sleep(2)
                continue

    # Decode and save the first image
    output_images = result.get("output", [])
    if not output_images:
        raise ValueError("Easy Diffusion returned no images")

    # Decode and save the first image
    image_data = output_images[0].get("data", "")
    if image_data.startswith("data:"):
        # Strip data URI prefix (e.g., "data:image/jpeg;base64,")
        image_data = image_data.split(",", 1)[-1]

    try:
        image_bytes = base64.b64decode(image_data)
        output_path.write_bytes(image_bytes)
    except Exception as e:
        logger.error(f"Base64 decoding failed for image data: {e}. Data started with: {image_data[:50]}")
        raise ValueError(f"Failed to decode base64 image: {e}")

    logger.info(f"Saved image to {output_path}")
    return str(output_path)


async def generate_images_for_scenes(
    scenes: list[dict],
    job_dir: str | Path,
    video_type: str = "long",
    on_progress: callable = None,
) -> list[str]:
    """
    Generate images for all scenes sequentially.

    Args:
        scenes: List of scene dicts with 'image_prompt'
        job_dir: Directory to save images
        video_type: 'long' or 'short'
        on_progress: Optional callback(scene_index, total) for progress updates

    Returns:
        List of image file paths
    """
    job_dir = Path(job_dir)
    images_dir = job_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    image_paths = []
    total = len(scenes)

    for i, scene in enumerate(scenes):
        image_path = images_dir / f"scene_{i:03d}.jpg"
        try:
            path = await generate_image(
                prompt=scene["image_prompt"],
                output_path=image_path,
                video_type=video_type,
                negative_prompt=scene.get("negative_prompt", ""),
            )
            image_paths.append(path)
        except Exception as e:
            logger.error(f"Failed to generate image for scene {i}: {e}")
            # Generate a fallback solid-color image
            path = _create_fallback_image(image_path, video_type)
            image_paths.append(path)

        if on_progress:
            await on_progress(i + 1, total)

    return image_paths


def _create_fallback_image(output_path: Path, video_type: str) -> str:
    """Create a solid dark image as fallback if generation fails."""
    from PIL import Image

    if video_type == "short":
        w, h = VIDEO_SHORT_RESOLUTION
    else:
        w, h = VIDEO_LONG_RESOLUTION

    img = Image.new("RGB", (w, h), color=(20, 15, 30))  # Dark purple-black
    img.save(output_path)
    logger.warning(f"Created fallback image at {output_path}")
    return str(output_path)
