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
22. Each sentence in the narration becomes its own scene
23. For each sentence, provide a matching anime image description
24. Image descriptions MUST be written as a comma-separated list of tags/keywords (Danbooru style), NOT full sentences. Include: character details, outfit, pose, expression, background, lighting tags, and quality tags.
   - Example: "1boy, vash the stampede, trigun stampede, red jacket, sunglasses, gun, hand on own hip, aiming, standing, looking at viewer, upper body, desert, cliff, cowboy shot"
25. Image descriptions must convey deep meaning and symbolism through specific visual tags that reinforce the sentence's meaning.
26. Never include text, words, or UI elements in image descriptions
27. Keep narration sentences concise — each should be spoken in 3-8 seconds
28. For each scene, provide a negative_prompt listing things to EXCLUDE from the image (e.g. artifacts, unwanted elements specific to that scene)
29. Provide a narration_audio field for voiceover. 
    - CRITICAL: By default, this field MUST be exactly the same as narration_text.
    - EXCEPTION: Only use phonetic spellings for names (e.g., "Ye-Suo" -> "Yeh-Suoh"), acronyms ("ADHD" -> "A-D-H-D"), or complex technical terms.
    - BAD EXAMPLE: "In-uh-world wair whed gamming iz laif" (DO NOT DO THIS)
    - GOOD EXAMPLE: "In a world where gaming is life, meet the masterminds of King's Avatar." (Keep normal words exactly as they are written).
    - Failure to keep common English words in their standard spelling will result in unnatural speech. Do not phoneticize simple words like "a", "the", "where", "is", "gaming", "life", etc.
"""

LONG_FORM_PROMPT = """Write a YouTube narration script about: "{topic}"

Target: Long-form video (5-10 minutes when spoken). Write 120-150 sentences.
Structure: Hook → Introduction → Main Points (Deep Dives & Context) → Reasoned Arguments → Call to Action

CRITICAL VISUAL CONSTRAINT:
Generate approximately 75-80 distinct visuals maximum. You must map these across your 120-150 narrative scenes by STRATEGICALLY REUSING the exact same image_prompt strings for sequential or highly related points. This prevents the image server from overloading while maintaining a coherent visual narrative.

Respond ONLY with valid JSON in this exact format, no markdown:
{{
  "title": "Video title",
  "scenes": [
    {{
      "narration_text": "One grammatically correct sentence of narration for the captions.",
      "narration_audio": "Exactly the same as narration_text. ONLY use phonetic overrides for names/acronyms if needed.",
      "image_prompt": "Comma-separated visual tags (Danbooru style). REUSE these exact strings frequently.",
      "negative_prompt": "Scene-specific things to exclude from the image."
    }}
  ]
}}"""

SHORT_FORM_PROMPT = """Write a YouTube Shorts narration script about: "{topic}"

Target: Short-form video (30-60 seconds when spoken). Write 7-17 sentences.
Structure: Shocking Hook → Quick Points → Punchline/CTA

Respond ONLY with valid JSON in this exact format, no markdown:
{{
  "title": "Video title",
  "scenes": [
    {{
      "narration_text": "One grammatically correct sentence of narration for the captions.",
      "narration_audio": "Exactly the same as narration_text. ONLY use phonetic overrides for names/acronyms.",
      "image_prompt": "Comma-separated visual tags (Danbooru style).",
      "negative_prompt": "Scene-specific things to exclude from the image."
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
        # Ensure negative_prompt has a fallback if the LLM omits it
        if "negative_prompt" not in scene:
            scene["negative_prompt"] = ""

    logger.info(f"Generated script with {len(scenes)} scenes")
    return script_data


REVISION_PROMPT = """You are refining an existing video script based on user feedback.

Original Topic: "{topic}"
Current Script Content:
{current_scenes}

User Feedback: "{feedback}"

TASK:
1. Review the current scenes and the user feedback.
2. Revise the narrations or image descriptions to better align with the feedback.
3. If narrations were changed by the user, ensure the new image descriptions or narrations maintain flow.
4. If no specific feedback was provided but a revision was requested, improve the overall quality and depth.

Respond ONLY with valid JSON in the exact same format as before:
{{
  "title": "Revised Video Title",
  "scenes": [
    {{
      "narration_text": "...",
      "narration_audio": "...",
      "image_prompt": "...",
      "negative_prompt": "..."
    }}
  ]
}}"""


async def revise_script(topic: str, feedback: str = "", current_scenes: list = None) -> dict:
    """
    Refine an existing script based on user feedback.
    """
    scenes_summary = ""
    if current_scenes:
        for i, s in enumerate(current_scenes):
            scenes_summary += f"Scene {i+1}: {s.get('narration_text', '')}\n"
            
    user_prompt = REVISION_PROMPT.format(
        topic=topic,
        current_scenes=scenes_summary,
        feedback=feedback or "Make it better."
    )

    logger.info(f"Revising script for topic: {topic}")

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": user_prompt,
                "system": SYSTEM_PROMPT,
                "stream": False,
                "options": {
                    "temperature": 0.5, # Lower temperature for better stickiness to previous content
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
        logger.error(f"Failed to parse revised script JSON: {e}")
        raise ValueError(f"LLM returned invalid JSON for revision: {e}")

    return script_data
