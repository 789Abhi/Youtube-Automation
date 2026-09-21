import os
import time
import logging
import math
import random
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Dict, Any, Optional
import textwrap
from PIL import Image, ImageDraw, ImageFont
import numpy as np

from config import GEMINI_API_KEY, DEFAULT_VEO_MODEL, CLIPS_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _get_font(size: int):
    """Finds the best available bold font across Windows and Linux (Streamlit Cloud)."""
    font_candidates = [
        "arialbd.ttf",
        "Arial-Bold.ttf",
        "Arial.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "C:\\Windows\\Fonts\\segoeuib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for candidate in font_candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None

def _download_ai_image(prompt: str, width: int, height: int, save_path: Path) -> bool:
    """
    Downloads a high-definition AI-generated scene image using Pollinations AI (Flux / SDXL).
    Zero API key required, highly reliable, and photorealistic.
    """
    enhanced_prompt = f"masterpiece, cinematic 8k, photorealistic, epic lighting, mythological fantasy art: {prompt}"
    encoded = urllib.parse.quote(enhanced_prompt)

    # Models to attempt in order of quality
    models = ["flux", "turbo"]
    seed = random.randint(1000, 999999)

    for model in models:
        url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true&model={model}&seed={seed}"
        try:
            logger.info(f"Generating AI image via {model} model...")
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AutoTube/2.0"}
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = resp.read()

            if len(data) > 5000: # Valid image returned
                with open(save_path, "wb") as f:
                    f.write(data)
                logger.info(f"AI image saved ({len(data)} bytes) to {save_path}")
                return True
        except Exception as e:
            logger.warning(f"Image generation with {model} notice: {e}. Trying next engine...")
            time.sleep(1)

    return False

def generate_scene_clip(
    video_id: str,
    scene_number: int,
    prompt: str,
    narration_text: str = "",
    format_type: str = "shorts",
    duration_sec: float = 5.0
) -> str:
    """
    Generates a cinematic video clip for a scene:
    1. Attempts Google Veo if an enterprise/Veo-enabled key is active.
    2. Uses high-definition Flux AI image generator with Ken Burns camera motion & viral subtitles.
    3. Falls back gracefully to dynamic procedural motion if offline.
    """
    output_clip_path = CLIPS_DIR / f"{video_id}_scene_{scene_number}.mp4"
    image_path = CLIPS_DIR / f"{video_id}_scene_{scene_number}.jpg"
    aspect_ratio = "9:16" if format_type == "shorts" else "16:9"
    target_w, target_h = (720, 1280) if format_type == "shorts" else (1280, 720)

    # 1. Attempt Google Veo (if specifically configured and supported)
    if GEMINI_API_KEY and os.getenv("ENABLE_GOOGLE_VEO", "false").lower() == "true":
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
                    duration_seconds=int(duration_sec)
                )
            )
            start_time = time.time()
            while not operation.done and (time.time() - start_time) < 180:
                time.sleep(5)
                operation = client.operations.get(operation)

            if operation.done and hasattr(operation, "response") and operation.response:
                generated_videos = getattr(operation.response, "generated_videos", [])
                if generated_videos and hasattr(generated_videos[0], "video"):
                    video_bytes = generated_videos[0].video.video_bytes
                    with open(output_clip_path, "wb") as f:
                        f.write(video_bytes)
                    logger.info(f"Veo clip saved to {output_clip_path}")
                    return str(output_clip_path)
        except Exception as e:
            logger.warning(f"Veo generation unavailable ({e}), proceeding with AI Visual Studio...")

    # 2. AI Character & Scene Image Generation (Flux / Photorealistic)
    image_ok = _download_ai_image(prompt, target_w, target_h, image_path)

    if image_ok and image_path.exists():
        try:
            _create_cinematic_kenburns_clip(
                image_path=image_path,
                output_path=output_clip_path,
                narration=narration_text,
                format_type=format_type,
                duration_sec=duration_sec,
                scene_idx=scene_number
            )
            return str(output_clip_path)
        except Exception as e:
            logger.error(f"Ken Burns rendering error: {e}, using dynamic backup...")

    # 3. Dynamic Procedural Visuals (Cosmic / Vibrant Particle Motion with Subtitles)
    logger.info(f"Rendering vibrant animated visuals for scene {scene_number}...")
    _create_procedural_clip(
        output_path=output_clip_path,
        prompt=prompt,
        narration=narration_text,
        format_type=format_type,
        duration_sec=duration_sec,
        scene_idx=scene_number
    )
    return str(output_clip_path)

def _create_cinematic_kenburns_clip(
    image_path: Path,
    output_path: Path,
    narration: str,
    format_type: str,
    duration_sec: float,
    scene_idx: int
) -> None:
    """
    Transforms a static AI image into an animated cinematic video:
    - Ken Burns slow zoom-in / zoom-out camera motion
    - Watermark removal and dynamic framing
    - High-impact, viral styled subtitles
    """
    from moviepy.editor import VideoClip

    target_w, target_h = (720, 1280) if format_type == "shorts" else (1280, 720)
    fps = 24

    # Load and clean base image (crop bottom watermark if present)
    base_img = Image.open(image_path).convert("RGB")
    orig_w, orig_h = base_img.size
    # Crop bottom 35px to eliminate any watermark
    cropped_base = base_img.crop((0, 0, orig_w, max(orig_h - 35, 100)))
    clean_img = cropped_base.resize((target_w, target_h), Image.Resampling.LANCZOS)

    # Subtitle layout preparation
    font_size = 36 if format_type == "shorts" else 30
    font = _get_font(font_size)
    wrap_width = 28 if format_type == "shorts" else 48
    lines = textwrap.wrap(narration.strip(), width=wrap_width) if narration else []

    line_height = int(font_size * 1.3)
    total_text_h = len(lines) * line_height + 24
    box_y = int(target_h * 0.72) if format_type == "shorts" else int(target_h * 0.78)

    # Alternating motion patterns across scenes for high visual retention
    motion_type = scene_idx % 4

    def make_frame(t):
        progress = min(max(t / max(duration_sec, 0.1), 0.0), 1.0)

        # Dynamic Camera Movement (Ken Burns)
        if motion_type == 1:
            # Slow Zoom In (1.00 -> 1.14)
            scale = 1.00 + 0.14 * progress
            dx, dy = 0, 0
        elif motion_type == 2:
            # Slow Zoom Out (1.14 -> 1.00)
            scale = 1.14 - 0.14 * progress
            dx, dy = 0, 0
        elif motion_type == 3:
            # Pan Up with slight zoom
            scale = 1.08 + 0.04 * progress
            dx = 0
            dy = int(-20 * progress)
        else:
            # Pan Down with slight zoom
            scale = 1.12 - 0.04 * progress
            dx = 0
            dy = int(20 * progress)

        curr_w = int(target_w * scale)
        curr_h = int(target_h * scale)
        frame_img = clean_img.resize((curr_w, curr_h), Image.Resampling.BILINEAR)

        # Center crop back to target canvas
        left = max(0, (curr_w - target_w) // 2 + dx)
        top = max(0, (curr_h - target_h) // 2 + dy)
        frame_img = frame_img.crop((left, top, left + target_w, top + target_h))

        # Add Subtitles if narration is available
        if lines and font:
            overlay = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
            ov_draw = ImageDraw.Draw(overlay)
            
            # Semi-transparent pill with gold border
            pad = 26
            ov_draw.rounded_rectangle(
                [(pad, box_y), (target_w - pad, box_y + total_text_h)],
                radius=14,
                fill=(10, 10, 15, 185),
                outline=(255, 215, 0, 220),
                width=2
            )

            blended = Image.alpha_composite(frame_img.convert("RGBA"), overlay)
            draw = ImageDraw.Draw(blended)
            curr_line_y = box_y + 12

            for line in lines:
                draw.text(
                    (target_w // 2, curr_line_y),
                    line,
                    font=font,
                    fill=(255, 255, 255),
                    stroke_width=2,
                    stroke_fill=(0, 0, 0),
                    anchor="mt"
                )
                curr_line_y += line_height

            return np.array(blended.convert("RGB"))

        return np.array(frame_img)

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

def _create_procedural_clip(
    output_path: Path,
    prompt: str,
    narration: str,
    format_type: str,
    duration_sec: float,
    scene_idx: int
) -> None:
    """Fallback cosmic animated clip with subtitles when offline."""
    from moviepy.editor import VideoClip

    width, height = (720, 1280) if format_type == "shorts" else (1280, 720)
    fps = 24

    palettes = [
        [(24, 18, 43), (63, 43, 100), (147, 51, 234)],   # Cosmic Purple
        [(15, 23, 42), (30, 58, 80), (14, 165, 233)],     # Deep Astral Cyan
        [(40, 15, 15), (120, 35, 35), (249, 115, 22)],    # Sacred Fire Amber
        [(20, 30, 25), (35, 78, 65), (34, 197, 94)],      # Vedic Emerald
    ]
    color_set = palettes[scene_idx % len(palettes)]

    c1 = np.array(color_set[0], dtype=float)
    c2 = np.array(color_set[1], dtype=float)
    c3 = np.array(color_set[2], dtype=float)

    font = _get_font(34 if format_type == "shorts" else 28)
    lines = textwrap.wrap(narration.strip(), width=28 if format_type == "shorts" else 48) if narration else []
    line_h = 44
    total_h = len(lines) * line_h + 20
    box_y = int(height * 0.72)

    def make_frame(t):
        progress = t / max(duration_sec, 0.1)
        pulse = (math.sin(progress * 2 * math.pi) + 1.0) / 2.0
        active_c2 = (1.0 - pulse) * c2 + pulse * c3

        y_coords = np.linspace(0, 1, height)[:, None]
        frame = (1.0 - y_coords) * c1 + y_coords * active_c2
        img_arr = np.clip(frame, 0, 255).astype(np.uint8)
        img_arr = np.repeat(img_arr, width, axis=1)

        pil_img = Image.fromarray(img_arr).convert("RGBA")
        overlay = Image.new("RGBA", pil_img.size, (255, 255, 255, 0))
        draw_ov = ImageDraw.Draw(overlay)

        # Draw decorative cosmic orb
        cx, cy = width // 2, int(height * 0.40)
        radius = int(80 + 15 * math.sin(progress * 4))
        draw_ov.ellipse(
            [(cx - radius, cy - radius), (cx + radius, cy + radius)],
            fill=(255, 215, 0, 60),
            outline=(255, 255, 255, 140),
            width=2
        )

        if lines and font:
            draw_ov.rounded_rectangle(
                [(25, box_y), (width - 25, box_y + total_h)],
                radius=14,
                fill=(10, 10, 15, 190),
                outline=(255, 215, 0, 220),
                width=2
            )

        blended = Image.alpha_composite(pil_img, overlay).convert("RGB")
        draw = ImageDraw.Draw(blended)

        # Scene Tag
        draw.text((width // 2, cy), f"SCENE {scene_idx}", font=font, fill=(255, 255, 255), anchor="mm")

        # Narration lines
        if lines and font:
            cur_y = box_y + 10
            for l in lines:
                draw.text((width // 2, cur_y), l, font=font, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0), anchor="mt")
                cur_y += line_h

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
