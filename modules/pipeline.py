import uuid
import logging
import sys
from datetime import datetime
from typing import Dict, Any, Callable, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from modules.db import create_video_record, update_video_record
from modules.script_generator import generate_video_script
from modules.voice_generator import generate_scene_audio
from modules.video_generator import generate_scene_clip
from modules.compositor import assemble_final_video
from modules.youtube_uploader import upload_video_to_youtube
from config import DEFAULT_TTS_VOICE, DEFAULT_PRIVACY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_video_pipeline(
    topic: str,
    format_type: str = "shorts",
    voice: str = DEFAULT_TTS_VOICE,
    privacy_status: str = DEFAULT_PRIVACY,
    auto_upload: bool = False,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Dict[str, Any]:
    """
    Executes the end-to-end video creation and upload pipeline.
    
    Args:
        topic: Concept/topic for the video.
        format_type: 'shorts' (9:16) or 'standard' (16:9).
        voice: Neural voice name.
        privacy_status: 'unlisted', 'private', or 'public'.
        auto_upload: Whether to immediately upload to YouTube upon assembly.
        progress_callback: Optional callback(pct, status_text) for UI progress updates.
    """
    video_id = f"vid_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
    
    def _notify(pct: float, msg: str):
        logger.info(f"[{int(pct*100)}%] {msg}")
        if progress_callback:
            progress_callback(pct, msg)

    # 1. Initialize Record
    record = create_video_record(
        video_id=video_id,
        topic=topic,
        format_type=format_type,
        voice=voice
    )
    _notify(0.05, "Initialized video project...")

    try:
        # 2. Script Generation
        _notify(0.15, "Generating viral script and Veo prompts with Gemini...")
        script_data = generate_video_script(topic, format_type=format_type)
        
        title = script_data.get("title", f"Video about {topic}")
        description = script_data.get("description", "")
        tags = script_data.get("tags", [])
        scenes = script_data.get("scenes", [])

        update_video_record(video_id, {
            "title": title,
            "description": description,
            "tags": tags,
            "scenes": scenes,
            "status": "script_ready"
        })
        _notify(0.30, f"Script created: '{title}'")

        # 3. Audio / Voiceover Generation
        _notify(0.40, "Generating realistic neural voiceover narration...")
        scene_audios, master_audio = generate_scene_audio(video_id, scenes, voice=voice)
        update_video_record(video_id, {
            "audio_path": master_audio,
            "status": "voice_ready"
        })
        _notify(0.50, "Voiceover generated successfully.")

        # 4. Video Generation (Scene by Scene)
        _notify(0.55, "Generating photorealistic AI visuals & cinematic scenes...")
        clip_paths = []
        total_scenes = len(scenes)
        for i, scene in enumerate(scenes):
            prompt = scene.get("visual_prompt", f"Cinematic shot of {topic}")
            narration = scene.get("narration", "")
            dur = float(scene.get("estimated_duration_sec", 5))

            # Match exact audio length if scene audio exists
            if i < len(scene_audios) and Path(scene_audios[i]).exists():
                try:
                    from moviepy.editor import AudioFileClip
                    a_clip = AudioFileClip(scene_audios[i])
                    dur = max(a_clip.duration + 0.3, 3.0)
                    a_clip.close()
                except Exception:
                    pass
            
            scene_pct = 0.55 + (0.25 * (i / max(total_scenes, 1)))
            _notify(scene_pct, f"Generating visual clip {i+1} of {total_scenes}...")
            
            clip = generate_scene_clip(
                video_id=video_id,
                scene_number=i+1,
                prompt=prompt,
                narration_text=narration,
                format_type=format_type,
                duration_sec=dur
            )
            clip_paths.append(clip)

        # 5. Media Assembly & Compositing
        _notify(0.82, "Assembling video clips, syncing audio track, and rendering final MP4...")
        final_video_path = assemble_final_video(
            video_id=video_id,
            clip_paths=clip_paths,
            audio_path=master_audio,
            format_type=format_type
        )
        thumb_path = str(final_video_path).replace(".mp4", "_thumb.png")

        record = update_video_record(video_id, {
            "title": title,
            "description": description,
            "tags": tags,
            "video_path": final_video_path,
            "thumbnail_path": thumb_path,
            "status": "draft_ready"
        })
        _notify(0.90, "Final video successfully assembled and ready for preview.")

        # 6. YouTube Upload (if requested)
        if auto_upload:
            _notify(0.92, "Uploading video to YouTube...")
            try:
                upload_res = upload_video_to_youtube(
                    video_path=final_video_path,
                    title=title,
                    description=description,
                    tags=tags,
                    privacy_status=privacy_status
                )
                yt_id = upload_res.get("video_id", "")
                yt_url = upload_res.get("youtube_url", "")

                record = update_video_record(video_id, {
                    "youtube_id": yt_id,
                    "youtube_url": yt_url,
                    "privacy_status": privacy_status,
                    "status": "uploaded",
                    "uploaded_at": datetime.now().isoformat()
                })
                _notify(1.0, f"Uploaded to YouTube! Live link: {yt_url}")
            except Exception as yt_err:
                logger.error(f"YouTube upload error: {yt_err}")
                record = update_video_record(video_id, {
                    "status": "upload_failed",
                    "error_message": str(yt_err)
                })
                _notify(1.0, f"Video rendered, but YouTube upload encountered an error: {yt_err}")
        else:
            _notify(1.0, "Video generation complete! Saved as Draft.")

        return record or get_video(video_id)

    except Exception as e:
        logger.error(f"Pipeline error for {video_id}: {e}", exc_info=True)
        record = update_video_record(video_id, {
            "status": "failed",
            "error_message": str(e)
        })
        _notify(1.0, f"Generation failed: {e}")
        return record
