"""
Caption Generator — Creates styled ASS subtitles from TTS timestamps.
Chunked captions with pop-in and fade transitions for viral-style engagement.
"""
import logging
import math
from pathlib import Path

logger = logging.getLogger(__name__)

# --- ASS Subtitle Headers ---
# Long-form (16:9) — captions at bottom
ASS_HEADER = """[Script Info]
Title: LuminaCast captions
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat,60,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,30,30,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

# Short-form (9:16) — captions centered vertically
ASS_HEADER_SHORTS = """[Script Info]
Title: LuminaCast captions
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat,68,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,5,30,30,500,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

# ASS override tags for pop-in + fade effect
# \fscx80\fscy80 = start at 80% scale
# \t(0,80,...) = animate to 100% scale over 80ms (pop)
# \fad(120,80) = 120ms fade-in, 80ms fade-out
POP_FADE_TAG = r"{\fad(120,80)\fscx80\fscy80\t(0,80,\fscx100\fscy100)}"


def _format_ass_time(seconds: float) -> str:
    """Format seconds into ASS timestamp (H:MM:SS.CC)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _chunk_sentence(text: str, max_words: int = 5) -> list[str]:
    """
    Split a sentence into short caption chunks of up to max_words.

    Tries to break at natural pauses (commas, semicolons) when possible.
    Falls back to fixed-size word groups.

    Args:
        text: The full narration sentence
        max_words: Maximum words per chunk

    Returns:
        List of short caption strings
    """
    text = text.strip()
    if not text:
        return []

    words = text.split()
    if len(words) <= max_words:
        return [text]

    chunks = []
    current_chunk = []

    for word in words:
        current_chunk.append(word)

        # Check if we've hit a natural break point (comma, semicolon, dash)
        is_natural_break = word.endswith((',', ';', '—', '–', ':'))
        at_max = len(current_chunk) >= max_words

        if at_max or (is_natural_break and len(current_chunk) >= 3):
            chunks.append(" ".join(current_chunk))
            current_chunk = []

    # Don't leave a dangling chunk of just 1-2 words — merge with previous
    if current_chunk:
        if len(current_chunk) <= 2 and chunks:
            chunks[-1] += " " + " ".join(current_chunk)
        else:
            chunks.append(" ".join(current_chunk))

    return chunks


def generate_captions_from_timestamps(
    scenes: list[dict],
    tts_results: list[dict],
    output_path: str | Path,
    video_type: str = "long",
    style: str = "chunked"
) -> str:
    """
    Generate ASS subtitle file with chunked captions and pop/fade transitions.

    Each narration sentence is broken into short 3-6 word phrases that appear
    one at a time with a pop-in scale animation and smooth fade transitions.

    Args:
        scenes: List of scene dicts with 'narration_text'
        tts_results: List of TTS result dicts with 'duration' and 'timestamps'
        output_path: Path to save the .ass file
        video_type: 'long' or 'short' (affects positioning)

    Returns:
        Path to the generated ASS file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    header = ASS_HEADER_SHORTS if video_type == "short" else ASS_HEADER
    events = []

    cumulative_time = 0.0
    SCENE_PAUSE = 0.5

    for i, (scene, tts) in enumerate(zip(scenes, tts_results)):
        text = scene["narration_text"]
        duration = tts["duration"]

        if style == "word_pop":
            words = text.split()
            if not words:
                cumulative_time += duration
                continue
            
            avg_duration = duration / len(words)
            for j, word in enumerate(words):
                chunk_duration = max(0.15, avg_duration)
                if j == len(words) - 1:
                    chunk_duration += SCENE_PAUSE

                start_str = _format_ass_time(cumulative_time)
                end_time = cumulative_time + chunk_duration
                end_str = _format_ass_time(end_time)

                clean_text = word.replace("\n", "")
                events.append(
                    f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{POP_FADE_TAG}{clean_text}"
                )
                cumulative_time = end_time

        else:
            # Chunked style
            chunks = _chunk_sentence(text)

            if not chunks:
                cumulative_time += duration
                continue

            # Distribute time across chunks weighted by word count
            total_words = sum(len(c.split()) for c in chunks)
            if total_words == 0:
                total_words = len(chunks)

            for j, chunk in enumerate(chunks):
                word_count = len(chunk.split())
                chunk_duration = (word_count / total_words) * duration
                # Ensure minimum duration of 0.4s for readability
                chunk_duration = max(0.4, chunk_duration)

                # If this is the last chunk of the sentence, keep it on screen 
                # during the scene's trailing silence (SCENE_PAUSE).
                if j == len(chunks) - 1:
                    chunk_duration += SCENE_PAUSE

                start_str = _format_ass_time(cumulative_time)
                end_time = cumulative_time + chunk_duration
                end_str = _format_ass_time(end_time)

                # Clean text for ASS format
                clean_text = chunk.replace("\n", "\\N")

                # Apply pop-in + fade animation tags
                events.append(
                    f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{POP_FADE_TAG}{clean_text}"
                )

                cumulative_time = end_time

        # Sync cumulative time with actual TTS duration + pause to prevent drift
        expected_end = sum(t["duration"] + SCENE_PAUSE for t in tts_results[:i+1])
        cumulative_time = expected_end

    ass_content = header + "\n".join(events) + "\n"
    output_path.write_text(ass_content, encoding="utf-8")

    logger.info(f"Generated chunked captions ({len(events)} events) at {output_path}")
    return str(output_path)
