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
"""

LONG_FORM_PROMPT = """Write a YouTube narration script about: "{topic}"

Target: Long-form video (5-10 minutes when spoken).
TOTAL LENGTH REQUIREMENT: You MUST write between 120 and 150 individual sentences. Each sentence becomes one scene.
Structure: Hook → Introduction → Main Points (Deep Dives, Context, Examples) → Reasoned Arguments → Call to Action

EXPANSION RULE: If the user provides a brief topic or a list of chapters, you MUST expand each point into 20-25 detailed scenes. Do not just summarize; provide depth, storytelling, and high-value psychological insights for every single scene.

CRITICAL VISUAL CONSTRAINT:
Generate approximately 75-80 distinct visuals maximum. You must map these across your 120-150 narrative scenes by STRATEGICALLY REUSING the exact same image_prompt strings for sequential or highly related points. This prevents the image server from overloading while maintaining a coherent visual narrative.

Respond ONLY with valid JSON in this exact format, no markdown:
{{
  "title": "Video title",
  "scenes": [
    {{
      "narration_text": "One grammatically correct sentence of narration for the captions.",
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
    vtype = str(video_type).strip().lower()
    prompt_template = LONG_FORM_PROMPT if vtype == "long" else SHORT_FORM_PROMPT
    user_prompt = prompt_template.format(topic=topic)

    # Long-form needs ~15k-20k tokens for 120-150 scenes of JSON; short only needs ~2k-4k
    token_limit = 32768 if vtype == "long" else 8192
    timeout = 600.0 if vtype == "long" else 300.0

    logger.info(f"Generating {vtype} script (mode: {'LONG' if vtype == 'long' else 'SHORT'}, tokens: {token_limit}) for topic: {topic}")

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": user_prompt,
                "system": SYSTEM_PROMPT,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": token_limit,
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
        
        # Manually duplicate narration_text to narration_audio as requested
        scene["narration_audio"] = scene["narration_text"]
        
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

    # Manually duplicate narration_text to narration_audio for revised scenes
    for scene in script_data.get("scenes", []):
        if "narration_text" in scene:
            scene["narration_audio"] = scene["narration_text"]

    return script_data


# ────────────────────────────────────────────────────────────────────────────
# ITERATIVE EXPANSION (Long-Form Only)
# ────────────────────────────────────────────────────────────────────────────

OUTLINE_PROMPT = """Create a detailed video outline for a YouTube deep-dive about: "{topic}"

Target: 7-8 minute video. Structure the content into 5-8 chapters.
Each chapter should have 2-4 sections that break down the key talking points.

Respond ONLY with valid JSON in this exact format, no markdown:
{{
  "title": "Video title",
  "chapters": [
    {{
      "title": "Chapter title",
      "description": "1-2 sentence summary of what this chapter covers",
      "sections": [
        {{
          "title": "Section title",
          "description": "1-2 sentence summary of the key point for this section"
        }}
      ]
    }}
  ]
}}"""

SECTION_EXPAND_PROMPT = """You are writing narration scenes for ONE section of a larger YouTube video script.

Video Topic: "{topic}"
Chapter: "{chapter_title}" — {chapter_desc}
Section: "{section_title}" — {section_desc}

Context (previous sections covered):
{context}

Write 8-15 narration sentences for THIS SECTION ONLY. Each sentence becomes one scene.
- Make it conversational and engaging, suitable for voiceover
- Provide Danbooru-style anime image tags for each scene
- Keep sentences concise (3-8 seconds when spoken)
- Build on the context of previous sections without repeating them

Respond ONLY with valid JSON in this exact format, no markdown:
{{
  "scenes": [
    {{
      "narration_text": "One grammatically correct sentence.",
      "image_prompt": "Comma-separated visual tags (Danbooru style).",
      "negative_prompt": "Scene-specific things to exclude."
    }}
  ]
}}"""


async def generate_outline(topic: str) -> dict:
    """
    Generate a chapter + section outline for a long-form video.
    This is a compact call (~1-2k tokens output) well within Mistral's limits.
    """
    user_prompt = OUTLINE_PROMPT.format(topic=topic)
    logger.info(f"Generating outline for topic: {topic}")

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
                    "num_predict": 4096,
                }
            }
        )
        response.raise_for_status()
        result = response.json()

    raw_text = result.get("response", "")
    cleaned = _clean_json_response(raw_text)

    try:
        outline_data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse outline JSON: {e}")
        logger.error(f"Raw response: {raw_text[:500]}")
        raise ValueError(f"LLM returned invalid JSON for outline: {e}")

    if "chapters" not in outline_data:
        raise ValueError("Outline missing 'chapters' key")

    chapters = outline_data["chapters"]
    if not isinstance(chapters, list) or len(chapters) == 0:
        raise ValueError("Outline has no chapters")

    total_sections = sum(len(ch.get("sections", [])) for ch in chapters)
    logger.info(f"Generated outline: {len(chapters)} chapters, {total_sections} sections")
    return outline_data


async def expand_section_to_scenes(
    topic: str,
    chapter_title: str,
    chapter_desc: str,
    section_title: str,
    section_desc: str,
    context: str = ""
) -> list[dict]:
    """
    Expand a single section into 8-15 narration scenes.
    Each call is small (~2k tokens output) — well within Mistral's comfort zone.
    """
    user_prompt = SECTION_EXPAND_PROMPT.format(
        topic=topic,
        chapter_title=chapter_title,
        chapter_desc=chapter_desc,
        section_title=section_title,
        section_desc=section_desc,
        context=context or "This is the first section."
    )

    logger.info(f"Expanding section: {chapter_title} > {section_title}")

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
                    "num_predict": 4096,
                }
            }
        )
        response.raise_for_status()
        result = response.json()

    raw_text = result.get("response", "")
    cleaned = _clean_json_response(raw_text)

    try:
        section_data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse section scenes JSON: {e}")
        raise ValueError(f"LLM returned invalid JSON for section expansion: {e}")

    scenes = section_data.get("scenes", [])

    for scene in scenes:
        # Mirror narration_text to narration_audio
        scene["narration_audio"] = scene.get("narration_text", "")
        if "negative_prompt" not in scene:
            scene["negative_prompt"] = ""

    logger.info(f"Expanded section '{section_title}' into {len(scenes)} scenes")
    return scenes

