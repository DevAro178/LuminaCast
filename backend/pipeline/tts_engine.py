"""
TTS Engine — Kokoro TTS integration.
Generates voiceover audio with word-level timestamps.
"""
import httpx
import logging
import json
import struct
import wave
from pathlib import Path
from config import KOKORO_TTS_URL, TTS_VOICES

logger = logging.getLogger(__name__)


async def generate_speech(
    text: str,
    output_path: str | Path,
    voice_type: str = "female",
) -> dict:
    """
    Generate speech audio for a text using Kokoro TTS.

    Args:
        text: Text to convert to speech
        output_path: Path to save the WAV file
        voice_type: 'female' or 'male'

    Returns:
        dict with 'audio_path', 'duration', and 'timestamps' (word-level)
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    voice_id = TTS_VOICES.get(voice_type, TTS_VOICES["female"])

    logger.info(f"Generating TTS ({voice_type}): {text[:60]}...")

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{KOKORO_TTS_URL}/api/generate",
            json={
                "text": text,
                "voice": voice_id,
                "speed": 0.85,
                "response_format": "wav",
            }
        )
        response.raise_for_status()

        # Check if the response is JSON (with timestamps) or raw audio
        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type:
            result = response.json()
            # Save audio from base64 or URL
            audio_data = result.get("audio", b"")
            if isinstance(audio_data, str):
                import base64
                audio_data = base64.b64decode(audio_data)
            output_path.write_bytes(audio_data)
            timestamps = result.get("timestamps", [])
            duration = result.get("duration", 0)
        else:
            # Raw audio response
            output_path.write_bytes(response.content)
            timestamps = []
            duration = _get_wav_duration(output_path)

    # Add a natural pause (0.6s) to the end of the clip for better pacing
    duration += 0.6

    logger.info(f"Saved audio ({duration:.1f}s) to {output_path}")
    return {
        "audio_path": str(output_path),
        "duration": duration,
        "timestamps": timestamps,
    }


async def generate_speech_for_scenes(
    scenes: list[dict],
    job_dir: str | Path,
    voice_type: str = "female",
    on_progress: callable = None,
) -> list[dict]:
    """
    Generate TTS audio for all scenes.

    Args:
        scenes: List of scene dicts with 'narration_text'
        job_dir: Directory to save audio files
        voice_type: 'female' or 'male'
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
        try:
            result = await generate_speech(
                text=scene["narration_text"],
                output_path=audio_path,
                voice_type=voice_type,
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
