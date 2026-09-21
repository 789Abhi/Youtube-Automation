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
    api_key = GEMINI_API_KEY
    if not api_key:
        try:
            import streamlit as st
            if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
                api_key = st.secrets["GEMINI_API_KEY"]
        except Exception:
            pass

    if not api_key:
        logger.warning("GEMINI_API_KEY not set. Using cinematic movie script generator.")
        return _fallback_script(topic, format_type)

    client = genai.Client(api_key=api_key)

    aspect_desc = "vertical 9:16 (YouTube Shorts, 30-45 seconds, fast-paced, hook in first 3 seconds)" if format_type == "shorts" else "horizontal 16:9 (standard YouTube video, 1-2 minutes, well-structured)"

    system_instruction = f"""
You are a world-class cinematic film director, epic screenwriter, and master visual storyteller (inspired by the grand scale of epic mythological cinema, Christopher Nolan, and high-budget movie trailers).
Your job is to transform concepts into breathtaking, high-retention, movie-trailer quality video scripts for: {aspect_desc}.

Guidelines:
1. Narration Style:
   - Deep, dramatic, atmospheric, and punchy movie-trailer narration.
   - Scene 1 MUST have a spine-chilling hook in the first 3 seconds that grips the audience immediately.
   - Pacing should build intense mystery, reveal astonishing ancient cosmic truths, and end on a mind-blowing cliffhanger.

2. Visual Prompts (Crucial for AI Character & Scene Art):
   - For every scene, describe a vivid, hyper-detailed, photorealistic cinematic masterpiece.
   - Specifically include character details: divine attire, ancient Vedic armor, sacred ornaments, intense expressions, glowing auras, weapons (Sudarshana Chakra, Trishul, divine bows).
   - Atmospheric cinematography: volumetric god rays, dark stormy skies, swirling embers, ancient megalithic temples, cosmic nebulae, 8k resolution, cinematic lighting.
   - Avoid generic text or placeholder descriptions. Focus on evocative, photorealistic imagery.

You MUST output strictly valid JSON matching this schema:
{{
  "title": "High CTR, cinematic click-worthy title under 70 characters (with emoji)",
  "description": "Epic movie-style description with hook, scene breakdown, and relevant hashtags",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "scenes": [
    {{
      "scene_number": 1,
      "narration": "Dramatic movie trailer voiceover text for this scene (concise, high impact).",
      "visual_prompt": "Hyper-realistic cinematic shot description. Mention characters, lighting, environment, and 8k cinematic details.",
      "estimated_duration_sec": 6
    }}
  ]
}}

Number of scenes:
- For 'shorts': 4 to 6 scenes (total ~30-45 seconds).
- For 'standard': 6 to 8 scenes (total ~60-90 seconds).
"""

    prompt = f"Topic: {topic}\nFormat: {format_type}\nGenerate the complete YouTube script and cinematic visual prompts."

    candidate_models = [
        "gemini-flash-latest",
        "gemini-3.5-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-2.5-flash",
        "gemini-pro-latest"
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

    logger.error("All Gemini models encountered temporary spikes. Using cinematic movie generator fallback.")
    return _fallback_script(topic, format_type)

def _fallback_script(topic: str, format_type: str) -> Dict[str, Any]:
    """Generates an epic cinematic movie trailer script tailored to the topic."""
    # Clean topic for title
    clean_topic = topic[:60].strip()
    return {
        "title": f"The Untold Prophecy of {clean_topic}! ⚡",
        "description": f"The cosmic secrets and untold prophecy of {topic}.\n\nWitness the clash of divine forces across time and yugas.\n\nSubscribe to Untold Yugas for daily mythological revelations!\n\n#UntoldYugas #Mythology #CosmicTruth #Shorts",
        "tags": ["untoldyugas", "mythology", "kalki", "ancientsecrets", "cosmicwar"],
        "scenes": [
            {
                "scene_number": 1,
                "narration": f"For millennia, ancient scriptures whispered of this cosmic reckoning: {clean_topic}.",
                "visual_prompt": f"Dramatic cinematic opening of {clean_topic}, apocalyptic storm clouds parted by blinding golden lightning, 8k photorealistic, epic atmosphere.",
                "estimated_duration_sec": 6
            },
            {
                "scene_number": 2,
                "narration": "When righteousness collapsed and darkness consumed the earth, celestial prophecies foretold an unstoppable awakening.",
                "visual_prompt": "Divine celestial deity with glowing eyes, wearing ornate Vedic golden armor, wielding a blazing energy sword amidst swirling cosmic nebulae, 8k masterpiece.",
                "estimated_duration_sec": 7
            },
            {
                "scene_number": 3,
                "narration": "A warrior of pure cosmic fire descends upon the battlefield, shattering the illusions of the dark age.",
                "visual_prompt": "Majestic white winged divine steed galloping across thunderous clouds, rider unleashing blinding celestial fire, hyper-detailed cinematic action shot.",
                "estimated_duration_sec": 6
            },
            {
                "scene_number": 4,
                "narration": "The old world ends in fire, and the eternal golden dawn of Satya Yuga begins. Subscribe to Untold Yugas.",
                "visual_prompt": "Breathtaking panoramic vista of a glorious golden temple rising above mountain peaks, surrounded by floating celestial orbs and serene golden sunlight.",
                "estimated_duration_sec": 6
            }
        ]
    }
