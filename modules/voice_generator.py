import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import edge_tts
from config import AUDIO_DIR, DEFAULT_TTS_VOICE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Curated list of high quality voices available for user selection
AVAILABLE_VOICES = {
    "Christopher (Male, Energetic & Deep)": "en-US-ChristopherNeural",
    "Guy (Male, Casual & Engaging)": "en-US-GuyNeural",
    "Jenny (Female, Warm & Conversational)": "en-US-JennyNeural",
    "Aria (Female, Clear & Professional)": "en-US-AriaNeural",
    "Brian (Male, British Accent)": "en-GB-BrianNeural",
    "Sonia (Female, British Accent)": "en-GB-SoniaNeural",
}

async def _synthesize_edge_tts(text: str, voice: str, output_path: Path) -> None:
    """Run edge-tts async synthesis."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))

def generate_scene_audio(
    video_id: str,
    scenes: List[Dict[str, Any]],
    voice: str = DEFAULT_TTS_VOICE
) -> Tuple[List[str], str]:
    """
    Generates audio files for each scene and a master audio track.
    Returns:
        Tuple of (list_of_scene_audio_paths, master_audio_path)
    """
    scene_audio_paths = []
    full_narration_parts = []

    for i, scene in enumerate(scenes):
        narration = scene.get("narration", "").strip()
        if not narration:
            continue
        
        full_narration_parts.append(narration)
        scene_file = AUDIO_DIR / f"{video_id}_scene_{i+1}.mp3"
        
        logger.info(f"Generating TTS for scene {i+1} using voice {voice}...")
        try:
            asyncio.run(_synthesize_edge_tts(narration, voice, scene_file))
            scene_audio_paths.append(str(scene_file))
        except Exception as e:
            logger.error(f"Error generating scene {i+1} audio: {e}")

    # Generate master track with natural pauses
    master_text = " ... ".join(full_narration_parts)
    master_file = AUDIO_DIR / f"{video_id}_master.mp3"
    try:
        asyncio.run(_synthesize_edge_tts(master_text, voice, master_file))
    except Exception as e:
        logger.error(f"Error generating master audio track: {e}")

    return scene_audio_paths, str(master_file)
