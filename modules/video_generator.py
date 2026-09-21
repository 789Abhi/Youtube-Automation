import time
import logging
import math
from pathlib import Path
from typing import List, Dict, Any
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from config import GEMINI_API_KEY, DEFAULT_VEO_MODEL, CLIPS_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_scene_clip(
    video_id: str,
    scene_number: int,
    prompt: str,
    format_type: str = "shorts",
    duration_sec: int = 5
) -> str:
    """
    Generates a video clip for a scene using Google Veo AI.
    Falls back gracefully to high-quality procedural animated motion if Veo is unavailable/restricted.
    """
    output_clip_path = CLIPS_DIR / f"{video_id}_scene_{scene_number}.mp4"
    aspect_ratio = "9:16" if format_type == "shorts" else "16:9"

    # Attempt Google Veo generation if API key is provided
    if GEMINI_API_KEY:
        try:
            from google import genai
            from google.genai import types
            logger.info(f"Submitting scene {scene_number} to Google Veo ({DEFAULT_VEO_MODEL})...")
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            operation = client.models.generate_videos(
                model=DEFAULT_VEO_MODEL,
                prompt=prompt,
                config=types.GenerateVideosConfig(
                    aspect_ratio=aspect_ratio,
                    duration_seconds=duration_sec
                )
            )

            logger.info(f"Waiting for Veo video generation to complete for scene {scene_number}...")
            start_time = time.time()
            max_wait = 180
            while not operation.done and (time.time() - start_time) < max_wait:
                time.sleep(5)
                operation = client.operations.get(operation)

            if operation.done and hasattr(operation, "response") and operation.response:
                generated_videos = getattr(operation.response, "generated_videos", [])
                if generated_videos and hasattr(generated_videos[0], "video"):
                    video_bytes = generated_videos[0].video.video_bytes
                    with open(output_clip_path, "wb") as f:
                        f.write(video_bytes)
                    logger.info(f"Veo clip saved successfully to {output_clip_path}")
                    return str(output_clip_path)

        except Exception as e:
            logger.warning(
                f"Google Veo API generation notice for scene {scene_number}: {e}. "
                f"Switching to dynamic animated clip generator for this scene."
            )

    # Fallback / Animated Clip Generator using MoviePy and Pillow
    logger.info(f"Rendering animated visual clip for scene {scene_number}...")
    _create_procedural_clip(
        output_path=output_clip_path,
        text=prompt,
        format_type=format_type,
        duration_sec=duration_sec,
        scene_idx=scene_number
    )
    return str(output_clip_path)

def _create_procedural_clip(
    output_path: Path,
    text: str,
    format_type: str,
    duration_sec: int,
    scene_idx: int
) -> None:
    """
    Creates an animated, dynamic video clip with smooth color gradients,
    flowing motion, and scene labels using MoviePy and Pillow.
    """
    from moviepy.editor import VideoClip

    width, height = (720, 1280) if format_type == "shorts" else (1280, 720)
    fps = 24

    palettes = [
        [(20, 15, 38), (76, 53, 117), (99, 102, 241)],    # Indigo Glow
        [(15, 23, 42), (30, 58, 80), (14, 165, 233)],     # Ocean Cyan
        [(38, 16, 43), (120, 40, 140), (236, 72, 153)],   # Magenta Neon
        [(17, 34, 30), (33, 75, 60), (34, 197, 94)],      # Emerald Aurora
        [(41, 19, 14), (130, 45, 25), (249, 115, 22)],    # Amber Flare
    ]
    color_set = palettes[scene_idx % len(palettes)]

    # Clean text to display
    words = text.split()
    preview_words = " ".join(words[:12]) if len(words) > 12 else text

    # Pre-render base background
    c1 = np.array(color_set[0], dtype=float)
    c2 = np.array(color_set[1], dtype=float)
    c3 = np.array(color_set[2], dtype=float)

    def make_frame(t):
        progress = t / max(duration_sec, 0.1)
        pulse = (math.sin(progress * 2 * math.pi) + 1.0) / 2.0
        active_c2 = (1.0 - pulse) * c2 + pulse * c3

        # Vertical gradient frame
        y_coords = np.linspace(0, 1, height)[:, None]
        frame = (1.0 - y_coords) * c1 + y_coords * active_c2
        img_arr = np.clip(frame, 0, 255).astype(np.uint8)
        img_arr = np.repeat(img_arr, width, axis=1)

        # Convert to RGBA for semi-transparent shapes and text
        pil_img = Image.fromarray(img_arr).convert("RGBA")
        overlay = Image.new("RGBA", pil_img.size, (255, 255, 255, 0))
        draw_ov = ImageDraw.Draw(overlay)

        # Draw decorative badges with alpha
        box_top = int(height * 0.40)
        draw_ov.rectangle(
            [(width // 2 - 120, box_top), (width // 2 + 120, box_top + 40)],
            fill=(255, 255, 255, 40),
            outline=(255, 255, 255, 120)
        )
        draw_ov.text((width // 2, box_top + 20), f"SCENE {scene_idx}", fill=(255, 255, 255, 255), anchor="mm")

        # Visual prompt text box
        draw_ov.text((width // 2, int(height * 0.52)), preview_words, fill=(230, 235, 245, 230), anchor="mm")

        # Composite and convert back to RGB for moviepy
        blended = Image.alpha_composite(pil_img, overlay).convert("RGB")
        return np.array(blended)

    clip = VideoClip(make_frame, duration=duration_sec)
    clip.write_videofile(
        str(output_path),
        fps=fps,
        codec="libx264",
        audio=False,
        preset="ultrafast",
        logger=None
    )
    clip.close()
