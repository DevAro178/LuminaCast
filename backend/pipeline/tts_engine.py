"""
TTS Engine — Kokoro TTS integration.
Generates voiceover audio with word-level timestamps.
"""
import httpx
import logging
import json
import struct
import wave
import subprocess
from pathlib import Path
from config import CHATTERBOX_TTS_URL, VOICES_DIR

logger = logging.getLogger(__name__)


async def generate_speech(
    text: str,
    output_path: str | Path,
    voice_id: str = "adam",
    exaggeration: float = 0.5,
    cfg_weight: float = 0.5,
    speed: float = 1.0
) -> dict:
    """
    Generate speech audio for a text using Chatterbox TTS.

    Args:
        text: Text to convert to speech
        output_path: Path to save the WAV file
        voice_id: Refers to filename in voices dir {voice_id}.wav
        exaggeration: Chatterbox model param
        cfg_weight: Chatterbox model param
        speed: Speed multiplier to apply via ffmpeg

    Returns:
        dict with 'audio_path', 'duration', and 'timestamps' (word-level)
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    api_url = f"{CHATTERBOX_TTS_URL}/api/generate"
    voice_path = str(VOICES_DIR / f"{voice_id}.wav")

    payload = {
        "text": text,
        "audio_prompt_path": voice_path,
        "exaggeration": exaggeration,
        "cfg_weight": cfg_weight
    }

    logger.info(f"Generating TTS for voice {voice_id}: {text[:60]}...")

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(api_url, json=payload)
        if response.status_code == 400:
            raise ValueError(f"Chatterbox error: {response.text}")
        response.raise_for_status()

        # Raw audio response expected from Chatterbox
        output_path.write_bytes(response.content)

    # Autoregressive Pacing Normalization
    raw_duration = _get_wav_duration(output_path)
    word_count = len(text.split())
    
    # Prevent div/0 or over-correcting very short phrases (e.g. 1-3 words)
    if raw_duration > 0.5 and word_count >= 4:
        raw_wpm = (word_count / raw_duration) * 60
        TARGET_WPM = 155.0
        
        # If it hallucinates extreme speeds (e.g. >190 or <120 WPM), correct it
        if raw_wpm > 190 or raw_wpm < 120:
            correction_factor = TARGET_WPM / raw_wpm
            # Bound the max single-stretch to prevent extreme chipmunking/demonic voices
            correction_factor = max(0.6, min(1.6, correction_factor))
            
            speed *= correction_factor
            logger.info(f"TTS hallucinated abnormally at {raw_wpm:.0f} WPM. Normalizing with atempo={correction_factor:.2f}")

    # Constrain final speed to valid atempo bounds to avoid FFmpeg crashing
    speed = max(0.5, min(100.0, speed))

    # Apply speed manipulation if specified or if normalized
    # Floating point comparison safe up to 3 decimals
    if abs(speed - 1.0) > 0.001:
        temp_path = output_path.with_name(f"{output_path.stem}_unscaled.wav")
        output_path.rename(temp_path)
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", str(temp_path),
                "-filter:a", f"atempo={speed}",
                str(output_path)
            ]
            # Use run sync internally because we are inside async wrapper, but Popen is fast here
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    duration = _get_wav_duration(output_path)
    logger.info(f"Saved audio ({duration:.1f}s) to {output_path}")
    return {
        "audio_path": str(output_path),
        "duration": duration,
        "timestamps": [],
    }


async def generate_speech_for_scenes(
    scenes: list[dict],
    job_dir: str | Path,
    voice_id: str = "adam",
    exaggeration: float = 0.5,
    cfg_weight: float = 0.5,
    speed: float = 1.0,
    on_progress: callable = None,
) -> list[dict]:
    """
    Generate TTS audio for all scenes.

    Args:
        scenes: List of scene dicts with 'narration_text'
        job_dir: Directory to save audio files
        voice_id: 'adam', 'eve', etc
        on_progress: Optional callback(scene_index, total)

    Returns:
        List of dicts with 'audio_path', 'duration', 'timestamps'
    """
    job_dir = Path(job_dir)
    audio_dir = job_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    results = []
    total = len(scenes)

    for i, scene in enumerate(scenes):
        audio_path = audio_dir / f"scene_{i:03d}.wav"
        
        if audio_path.exists() and audio_path.stat().st_size > 0:
            logger.info(f"Audio already exists for scene {i}, skipping generation.")
            duration = _get_wav_duration(audio_path)
            results.append({
                "audio_path": str(audio_path),
                "duration": duration,
                "timestamps": [],
            })
            if on_progress:
                await on_progress(i + 1, total)
            continue
            
        try:
            result = await generate_speech(
                text=scene.get("narration_audio") or scene["narration_text"],
                output_path=audio_path,
                voice_id=voice_id,
                exaggeration=exaggeration,
                cfg_weight=cfg_weight,
                speed=speed
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to generate TTS for scene {i}: {e}")
            # Create a silent audio fallback
            duration = _estimate_duration(scene["narration_text"])
            _create_silent_audio(audio_path, duration)
            results.append({
                "audio_path": str(audio_path),
                "duration": duration,
                "timestamps": [],
            })

        if on_progress:
            await on_progress(i + 1, total)

    return results


def _get_wav_duration(path: Path) -> float:
    """Get duration of a WAV file in seconds."""
    try:
        with wave.open(str(path), 'rb') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate)
    except Exception:
        return 3.0  # Default fallback


def _estimate_duration(text: str) -> float:
    """Estimate speech duration from text (approx 150 words/min)."""
    words = len(text.split())
    return max(1.5, words / 2.5)  # ~150 wpm = 2.5 words/sec


def _create_silent_audio(path: Path, duration: float, sample_rate: int = 24000):
    """Create a silent WAV file as fallback."""
    num_frames = int(sample_rate * duration)
    with wave.open(str(path), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b'\x00\x00' * num_frames)
    logger.warning(f"Created silent fallback audio ({duration:.1f}s) at {path}")
