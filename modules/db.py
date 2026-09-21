import json
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from config import DB_PATH

_lock = threading.Lock()

def _load_data() -> Dict[str, Any]:
    if not DB_PATH.exists():
        return {"videos": []}
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"videos": []}

def _save_data(data: Dict[str, Any]) -> None:
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_all_videos() -> List[Dict[str, Any]]:
    """Retrieve all video records ordered by creation date descending."""
    with _lock:
        data = _load_data()
        videos = data.get("videos", [])
        # Return newest first
        return sorted(videos, key=lambda x: x.get("created_at", ""), reverse=True)

def get_video(video_id: str) -> Optional[Dict[str, Any]]:
    """Get single video record by ID."""
    with _lock:
        data = _load_data()
        for v in data.get("videos", []):
            if v.get("id") == video_id:
                return v
    return None

def create_video_record(
    video_id: str,
    topic: str,
    format_type: str = "shorts",
    voice: str = "en-US-ChristopherNeural"
) -> Dict[str, Any]:
    """Create a new video record with initial status."""
    record = {
        "id": video_id,
        "topic": topic,
        "format": format_type,
        "voice": voice,
        "title": "",
        "description": "",
        "tags": [],
        "scenes": [],
        "audio_path": "",
        "video_path": "",
        "thumbnail_path": "",
        "status": "pending",  # pending, script_ready, voice_ready, video_rendered, uploading, uploaded, failed
        "error_message": "",
        "youtube_id": "",
        "youtube_url": "",
        "privacy_status": "unlisted",
        "created_at": datetime.now().isoformat(),
        "uploaded_at": None,
    }
    with _lock:
        data = _load_data()
        data["videos"].append(record)
        _save_data(data)
    return record

def update_video_record(video_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update fields of an existing video record."""
    with _lock:
        data = _load_data()
        for i, v in enumerate(data.get("videos", [])):
            if v.get("id") == video_id:
                data["videos"][i].update(updates)
                _save_data(data)
                return data["videos"][i]
    return None

def delete_video_record(video_id: str) -> bool:
    """Delete a video record from registry."""
    with _lock:
        data = _load_data()
        original_len = len(data.get("videos", []))
        data["videos"] = [v for v in data.get("videos", []) if v.get("id") != video_id]
        if len(data["videos"]) < original_len:
            _save_data(data)
            return True
    return False
