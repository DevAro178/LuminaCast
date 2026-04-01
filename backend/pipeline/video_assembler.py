"""
Video Assembler — MoviePy + FFmpeg composition.
Stitches scene images + audio + captions into final MP4.
Ken Burns effect, crossfade transitions, subtitle burn-in.
"""
import logging
from pathlib import Path
from moviepy import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    CompositeAudioClip,
    concatenate_videoclips,
    vfx,
)
import numpy as np

from config import VIDEO_FPS, VIDEO_LONG_RESOLUTION, VIDEO_SHORT_RESOLUTION, CROSSFADE_DURATION, KEN_BURNS_ZOOM, SCENE_PAUSE

logger = logging.getLogger(__name__)


def _ken_burns_effect(clip, zoom_factor=KEN_BURNS_ZOOM):
    """
    Apply Ken Burns (slow zoom) effect to an image clip.
    Starts at 100% and zooms to zoom_factor over the clip duration.
    """
    w, h = clip.size

    def make_frame(get_frame, t):
        progress = t / clip.duration if clip.duration > 0 else 0
        current_zoom = 1.0 + (zoom_factor - 1.0) * progress
        frame = get_frame(t)

        # Use PIL for high-quality subpixel crop and resize
        from PIL import Image
        pil_img = Image.fromarray(frame)
        
        # Calculate subpixel crop region
        new_w = w / current_zoom
        new_h = h / current_zoom
        x_offset = (w - new_w) / 2
        y_offset = (h - new_h) / 2
        
        # PIL.crop takes (left, top, right, bottom)
        left, top = x_offset, y_offset
        right, bottom = x_offset + new_w, y_offset + new_h
        
        # Resize to target with high-quality filter
        # crop() then resize() ensures subpixel accuracy
        return np.array(
            pil_img.crop((left, top, right, bottom))
            .resize((w, h), Image.LANCZOS)
        )

    return clip.transform(make_frame)


def _pan_left_effect(clip, zoom_factor=1.08):
    """Pan from right to left at a fixed zoom level."""
    w, h = clip.size

    def make_frame(get_frame, t):
        progress = t / clip.duration if clip.duration > 0 else 0
        frame = get_frame(t)
        from PIL import Image
        pil_img = Image.fromarray(frame)
        
        new_w = w / zoom_factor
        new_h = h / zoom_factor
        
        # Start looking at the right side, slide to the left side
        max_x_offset = w - new_w
        x_offset = max_x_offset * (1.0 - progress)
        y_offset = (h - new_h) / 2
        
        return np.array(
            pil_img.crop((x_offset, y_offset, x_offset + new_w, y_offset + new_h))
            .resize((w, h), Image.LANCZOS)
        )
    return clip.transform(make_frame)


def _pan_right_effect(clip, zoom_factor=1.08):
    """Pan from left to right at a fixed zoom level."""
    w, h = clip.size

    def make_frame(get_frame, t):
        progress = t / clip.duration if clip.duration > 0 else 0
        frame = get_frame(t)
        from PIL import Image
        pil_img = Image.fromarray(frame)
        
        new_w = w / zoom_factor
        new_h = h / zoom_factor
        
        # Start looking at the left side, slide to the right side
        max_x_offset = w - new_w
        x_offset = max_x_offset * progress
        y_offset = (h - new_h) / 2
        
        return np.array(
            pil_img.crop((x_offset, y_offset, x_offset + new_w, y_offset + new_h))
            .resize((w, h), Image.LANCZOS)
        )
    return clip.transform(make_frame)


def _zoom_out_effect(clip, start_zoom=1.08):
    """Start zoomed in and zoom out slowly to 1.0 (original)."""
    w, h = clip.size

    def make_frame(get_frame, t):
        progress = t / clip.duration if clip.duration > 0 else 0
        current_zoom = start_zoom - ((start_zoom - 1.0) * progress)
        frame = get_frame(t)
        from PIL import Image
        pil_img = Image.fromarray(frame)
        
        new_w = w / current_zoom
        new_h = h / current_zoom
        x_offset = (w - new_w) / 2
        y_offset = (h - new_h) / 2
        
        return np.array(
            pil_img.crop((x_offset, y_offset, x_offset + new_w, y_offset + new_h))
            .resize((w, h), Image.LANCZOS)
        )
    return clip.transform(make_frame)


def assemble_video(
    scenes: list[dict],
    tts_results: list[dict],
    image_paths: list[str],
    caption_path: str | None,
    output_path: str | Path,
    video_type: str = "long",
    effect_ids: list[str] = None,
    progress_callback: callable = None,
) -> str:
    """
    Assemble the final video from scenes, images, audio, and captions.

    Args:
        scenes: Scene dicts with narration_text
        tts_results: TTS results with audio_path and duration
        image_paths: Paths to generated images (one per scene)
        caption_path: Path to ASS subtitle file (or None)
        output_path: Path to save the final .mp4
        video_type: 'long' or 'short'
        progress_callback: Optional callable for percent updates

    Returns:
        Path to the final video file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if video_type == "short":
        target_w, target_h = VIDEO_SHORT_RESOLUTION
    else:
        target_w, target_h = VIDEO_LONG_RESOLUTION

    logger.info(f"Assembling {video_type} video: {len(scenes)} scenes, {target_w}x{target_h}")

    scene_clips = []
    audio_clips = []
    cumulative_time = 0.0

    for i, (scene, tts, img_path) in enumerate(zip(scenes, tts_results, image_paths)):
        if i % 10 == 0:
            logger.info(f"Processing scene clips: {i}/{len(scenes)}...")
            if progress_callback:
                # Map assembly progress (0-100%) to the 82%-98% job progress range
                assembly_pct = (i / len(scenes)) * 16.0
                progress_callback(82 + int(assembly_pct))
            
        # Ensure image path has .jpg extension
        img_path = str(img_path).replace(".png", ".jpg")
        duration = tts["duration"]
        audio_path = tts["audio_path"]

        if duration <= 0:
            logger.warning(f"Scene {i} has zero duration, skipping")
            continue

        # Use SCENE_PAUSE from config for audio gap between scenes

        # Create image clip
        visual_duration = duration + SCENE_PAUSE + (CROSSFADE_DURATION if CROSSFADE_DURATION > 0 else 0)
        
        img_clip = (
            ImageClip(img_path)
            .resized((target_w, target_h))
            .with_duration(visual_duration)
        )

        effects = effect_ids or ["ken_burns"]
        import random
        effect = random.choice(effects)

        if effect == "ken_burns":
            img_clip = _ken_burns_effect(img_clip)
        elif effect == "pan_left":
            img_clip = _pan_left_effect(img_clip)
        elif effect == "pan_right":
            img_clip = _pan_right_effect(img_clip)
        elif effect == "zoom_out":
            img_clip = _zoom_out_effect(img_clip)

        scene_clips.append(img_clip)

        # Load audio
        try:
            audio_clip = AudioFileClip(audio_path)
            audio_clips.append(audio_clip.with_start(cumulative_time))
        except Exception as e:
            logger.warning(f"Could not load audio for scene {i}: {e}")

        cumulative_time += duration + SCENE_PAUSE

    if not scene_clips:
        raise ValueError("No valid scene clips to assemble")

    # Concatenate scenes with crossfade transitions
    if len(scene_clips) > 1 and CROSSFADE_DURATION > 0:
        faded_clips = []
        for i, clip in enumerate(scene_clips):
            if i > 0:
                clip = clip.with_effects([vfx.CrossFadeIn(CROSSFADE_DURATION)])
            faded_clips.append(clip)
        
        final_video = concatenate_videoclips(
            faded_clips,
            method="compose",
            padding=-CROSSFADE_DURATION,
        )
    else:
        final_video = concatenate_videoclips(scene_clips)

    # Attach Audio
    final_audio = CompositeAudioClip(audio_clips)
    final_video = final_video.with_audio(final_audio)

    # Write output with subtitle burn-in if available
    ffmpeg_params = ["-c:v", "libx264", "-preset", "medium", "-crf", "23"]

    if caption_path and Path(caption_path).exists():
        # Burn in ASS subtitles via FFmpeg filter
        # Escape backslashes and colons for FFmpeg on windows/linux
        safe_caption_path = str(caption_path).replace("\\", "/").replace(":", "\\:")
        ffmpeg_params.extend([
            "-vf", f"ass='{safe_caption_path}'"
        ])

    logger.info(f"Writing final MP4 to {output_path}...")
    final_video.write_videofile(
        str(output_path),
        fps=VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        ffmpeg_params=ffmpeg_params,
        threads=4,
        logger=None,  # Suppress moviepy's verbose output
    )

    # Close clips to free resources
    final_video.close()
    for clip in scene_clips:
        clip.close()
    for clip in audio_clips:
        clip.close()

    logger.info(f"Video assembled successfully: {output_path}")
    return str(output_path)
