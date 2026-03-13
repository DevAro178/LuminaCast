"""
Script Generator — Ollama Mistral integration.
Generates a narration script with one scene per sentence,
each with an anime image prompt.
"""
import json
import httpx
import logging
from config import OLLAMA_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a professional YouTube script writer specializing in psychology content with anime-style visuals.

You write engaging, informative narration scripts. Your scripts are:
- Hook-based (grab attention in the first sentence)
- Educational yet conversational
- Emotionally resonant
- Written for voiceover (natural spoken language, not academic)

IMPORTANT RULES:
1. Each sentence in the narration becomes its own scene
2. For each sentence, provide a matching anime image description
3. Image descriptions should be detailed, vivid, and match the emotion/context of the sentence
4. Image descriptions must specify anime art style elements (lighting, mood, colors, character poses)
5. Never include text or words in image descriptions
6. Keep narration sentences concise — each should be spoken in 3-8 seconds"""

LONG_FORM_PROMPT = """Write a YouTube narration script about: "{topic}"

Target: Long-form video (5-10 minutes when spoken). Write 40-70 sentences.
Structure: Hook → Introduction → Main Points (3-5) → Deep Insight → Call to Action

Respond ONLY with valid JSON in this exact format, no markdown:
{{
  "title": "Video title",
  "scenes": [
    {{
      "narration_text": "One sentence of narration.",
      "image_prompt": "Detailed anime image description matching the sentence mood and content. Include: art style, lighting, colors, character details, environment, emotion."
    }}
  ]
}}"""

SHORT_FORM_PROMPT = """Write a YouTube Shorts narration script about: "{topic}"

Target: Short-form video (30-60 seconds when spoken). Write 8-15 sentences.
Structure: Shocking Hook → Quick Points → Punchline/CTA

Respond ONLY with valid JSON in this exact format, no markdown:
{{
  "title": "Video title",
  "scenes": [
    {{
      "narration_text": "One sentence of narration.",
      "image_prompt": "Detailed anime image description matching the sentence mood and content. Include: art style, lighting, colors, character details, environment, emotion."
    }}
  ]
}}"""


def _clean_json_response(text: str) -> str:
    """Extract JSON from LLM response, handling markdown code blocks."""
    text = text.strip()
    # Remove markdown code blocks if present
    if text.startswith("```"):
        # Find the end of the first line (```json or ```)
        first_newline = text.index("\n")
        last_backticks = text.rfind("```")
        if last_backticks > first_newline:
            text = text[first_newline + 1:last_backticks].strip()
        else:
            text = text[first_newline + 1:].strip()
    return text


async def generate_script(topic: str, video_type: str = "long") -> dict:
    """
    Generate a video script using Ollama Mistral.

    Args:
        topic: The video topic/title
        video_type: 'long' for 5-10 min, 'short' for 30-60s

    Returns:
        dict with 'title' and 'scenes' list
    """
    prompt_template = LONG_FORM_PROMPT if video_type == "long" else SHORT_FORM_PROMPT
    user_prompt = prompt_template.format(topic=topic)

    logger.info(f"Generating {video_type} script for topic: {topic}")

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": user_prompt,
                "system": SYSTEM_PROMPT,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 8192,
                }
            }
        )
        response.raise_for_status()
        result = response.json()

    raw_text = result.get("response", "")
    cleaned = _clean_json_response(raw_text)

    try:
        script_data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse script JSON: {e}")
        logger.error(f"Raw response: {raw_text[:500]}")
        raise ValueError(f"LLM returned invalid JSON: {e}")

    # Validate structure
    if "scenes" not in script_data:
        raise ValueError("Script missing 'scenes' key")

    scenes = script_data["scenes"]
    if not isinstance(scenes, list) or len(scenes) == 0:
        raise ValueError("Script has no scenes")

    for i, scene in enumerate(scenes):
        if "narration_text" not in scene or "image_prompt" not in scene:
            raise ValueError(f"Scene {i} missing required fields")

    logger.info(f"Generated script with {len(scenes)} scenes")
    return script_data
