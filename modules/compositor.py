import logging
from pathlib import Path
from typing import List
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    concatenate_videoclips
)
from PIL import Image
from config import VIDEO_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def assemble_final_video(
    video_id: str,
    clip_paths: List[str],
    audio_path: str,
    format_type: str = "shorts"
) -> str:
    """
    Stitches scene video clips together, syncs voiceover audio,
    generates a thumbnail, and exports the final YouTube video.
    Returns:
        Path to the exported MP4 file.
    """
    output_video_path = VIDEO_DIR / f"{video_id}.mp4"
    thumbnail_path = VIDEO_DIR / f"{video_id}_thumb.jpg"

    logger.info(f"Assembling {len(clip_paths)} clips for video {video_id}...")
    loaded_clips = []
    
    for p in clip_paths:
        if Path(p).exists():
            loaded_clips.append(VideoFileClip(p))

    if not loaded_clips:
        raise ValueError("No valid video clips found to assemble.")

    # Concatenate all scene clips
    final_video = concatenate_videoclips(loaded_clips, method="compose")

    # Load audio track
    if Path(audio_path).exists():
        audio_clip = AudioFileClip(audio_path)
        audio_duration = audio_clip.duration
        video_duration = final_video.duration

        # Adjust video length if audio is longer
        if audio_duration > video_duration:
            # Loop video or hold last frame to match audio duration
            diff = audio_duration - video_duration
            last_clip = loaded_clips[-1]
            freeze_clip = last_clip.to_ImageClip(t=last_clip.duration - 0.1).set_duration(diff)
            final_video = concatenate_videoclips([final_video, freeze_clip])
        elif video_duration > audio_duration:
            # Trim video to match audio
            final_video = final_video.subclip(0, audio_duration + 0.5)

        final_video = final_video.set_audio(audio_clip)

    # Export final mp4 with YouTube-compatible codecs
    logger.info(f"Rendering final MP4 to {output_video_path}...")
    final_video.write_videofile(
        str(output_video_path),
        codec="libx264",
        audio_codec="aac",
        fps=24,
        preset="fast",
        logger=None
    )

    # Save thumbnail (middle frame)
    try:
        thumb_png = thumbnail_path.with_suffix(".png")
        final_video.save_frame(str(thumb_png), t=min(1.0, final_video.duration / 2.0))
        logger.info(f"Thumbnail saved to {thumb_png}")
    except Exception as e:
        logger.warning(f"Failed to generate thumbnail: {e}")

    # Clean up memory
    for c in loaded_clips:
        c.close()
    final_video.close()

    return str(output_video_path)
