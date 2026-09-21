import json
import logging
from typing import Dict, Any, List
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, DEFAULT_GEMINI_MODEL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_video_script(topic: str, format_type: str = "shorts") -> Dict[str, Any]:
    """
    Generates an engaging, structured YouTube video script using Gemini.
    Returns:
        Dict with title, description, tags, and scenes (narration + visual prompt).
    """
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set. Using template/fallback script generator.")
        return _fallback_script(topic, format_type)

    client = genai.Client(api_key=GEMINI_API_KEY)

    aspect_desc = "vertical 9:16 (YouTube Shorts, 30-45 seconds, fast-paced, hook in first 3 seconds)" if format_type == "shorts" else "horizontal 16:9 (standard YouTube video, 1-2 minutes, well-structured)"

    system_instruction = f"""
You are an expert viral YouTube scriptwriter and video producer.
Create a high-retention video script for the following format: {aspect_desc}.

You MUST output strictly valid JSON matching this schema:
{{
  "title": "High CTR, engaging title under 70 characters",
  "description": "Engaging description with key takeaways, timestamps, and hashtags",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "scenes": [
    {{
      "scene_number": 1,
      "narration": "What the voiceover says for this scene. Keep it energetic and concise.",
      "visual_prompt": "Cinematic visual description for Google Veo AI video generation. Be descriptive with camera motion, lighting, and details.",
      "estimated_duration_sec": 5
    }}
  ]
}}

Number of scenes:
- For 'shorts': 4 to 6 scenes (total ~30-45 seconds).
- For 'standard': 6 to 10 scenes (total ~60-90 seconds).
"""

    prompt = f"Topic: {topic}\nFormat: {format_type}\nGenerate the complete YouTube script and Veo visual prompts."

    candidate_models = [
        DEFAULT_GEMINI_MODEL,
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash"
    ]
    # Deduplicate while preserving order
    seen = set()
    models_to_try = [m for m in candidate_models if not (m in seen or seen.add(m))]

    for model_name in models_to_try:
        try:
            logger.info(f"Generating video script using {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.7
                )
            )
            data = json.loads(response.text)
            logger.info(f"Successfully generated script with {model_name}!")
            return data
        except Exception as e:
            logger.warning(f"Model {model_name} encountered notice: {e}. Trying next available model...")

    logger.error("All Gemini models encountered spikes or errors. Falling back to template generator.")
    return _fallback_script(topic, format_type)

def _fallback_script(topic: str, format_type: str) -> Dict[str, Any]:
    """Generates a high-quality fallback script if Gemini API key is missing or encounters rate limits."""
    return {
        "title": f"The Mind-Blowing Truth About {topic.title()}! 🚀",
        "description": f"Discover the most incredible facts and secrets about {topic}.\n\nSubscribe for more daily AI-powered explorations!\n\n#Shorts #{topic.replace(' ', '')} #Facts",
        "tags": [topic.lower(), "shorts", "educational", "mindblowing", "facts"],
        "scenes": [
            {
                "scene_number": 1,
                "narration": f"Did you know the untold reality behind {topic}? Most people have it completely backwards!",
                "visual_prompt": f"Dramatic cinematic wide angle establishing shot of {topic}, volumetric cinematic lighting, 4k ultra realistic, smooth camera zoom-in.",
                "estimated_duration_sec": 6
            },
            {
                "scene_number": 2,
                "narration": f"Here is the crazy part. When scientists and explorers took a closer look, they uncovered something astonishing.",
                "visual_prompt": f"Dynamic rotating camera shot exploring intricate details of {topic}, glowing highlights, cinematic atmosphere.",
                "estimated_duration_sec": 7
            },
            {
                "scene_number": 3,
                "narration": "This completely changed how we understand this phenomenon today.",
                "visual_prompt": f"Futuristic holographic breakdown and visual comparison of {topic}, cyberpunk neon aesthetic, seamless motion.",
                "estimated_duration_sec": 6
            },
            {
                "scene_number": 4,
                "narration": "Drop a comment below on what you think, and hit follow for more daily insights!",
                "visual_prompt": "Cinematic outro with particles flowing upward, sunset lighting, vibrant colors.",
                "estimated_duration_sec": 5
            }
        ]
    }
