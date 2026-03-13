"""
Caption Generator — Creates styled ASS subtitles from TTS timestamps.
Word-by-word highlight with anime-aesthetic styling.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ASS subtitle header with anime-style formatting
ASS_HEADER = """[Script Info]
Title: spinning-photon captions
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,58,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,30,30,60,1
Style: Highlight,Arial,62,&H0000E5FF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,2,2,30,30,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

ASS_HEADER_SHORTS = """[Script Info]
Title: spinning-photon captions
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,64,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,5,30,30,500,1
Style: Highlight,Arial,68,&H0000E5FF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,2,5,30,30,500,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _format_ass_time(seconds: float) -> str:
    """Format seconds into ASS timestamp (H:MM:SS.CC)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def generate_captions_from_timestamps(
    scenes: list[dict],
    tts_results: list[dict],
    output_path: str | Path,
    video_type: str = "long",
) -> str:
    """
    Generate ASS subtitle file from scene narrations and TTS timestamps.

    If word-level timestamps are available, creates word-by-word highlights.
    Otherwise, shows full sentence per scene.

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

    for i, (scene, tts) in enumerate(zip(scenes, tts_results)):
        text = scene["narration_text"]
        duration = tts["duration"]
        timestamps = tts.get("timestamps", [])

        if timestamps:
            # Word-by-word captions with highlighting
            for ts in timestamps:
                word = ts.get("word", "")
                start = cumulative_time + ts.get("start", 0)
                end = cumulative_time + ts.get("end", duration)
                start_str = _format_ass_time(start)
                end_str = _format_ass_time(end)
                events.append(
                    f"Dialogue: 0,{start_str},{end_str},Highlight,,0,0,0,,{word}"
                )
        else:
            # Full sentence caption for the scene duration
            start_str = _format_ass_time(cumulative_time)
            end_str = _format_ass_time(cumulative_time + duration)
            # Clean text for ASS format (replace newlines)
            clean_text = text.replace("\n", "\\N")
            events.append(
                f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{clean_text}"
            )

        cumulative_time += duration

    ass_content = header + "\n".join(events) + "\n"
    output_path.write_text(ass_content, encoding="utf-8")

    logger.info(f"Generated captions ({len(events)} events) at {output_path}")
    return str(output_path)
