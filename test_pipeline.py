import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add project root
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from modules.pipeline import run_video_pipeline
from modules.db import get_all_videos

def test_dry_run():
    print("Testing Video Automation Pipeline (Dry Run / Local Render)...")
    topic = "The Secrets of the Mariana Trench"
    
    def on_progress(pct, msg):
        print(f"[{int(pct*100):3d}%] {msg}")

    result = run_video_pipeline(
        topic=topic,
        format_type="shorts",
        auto_upload=False,
        progress_callback=on_progress
    )

    print("\n--- Pipeline Result ---")
    print("ID:", result.get("id"))
    print("Title:", result.get("title"))
    print("Status:", result.get("status"))
    print("Video File:", result.get("video_path"))
    
    assert result.get("status") != "failed", f"Pipeline returned failed status: {result.get('error_message')}"
    
    video_path = Path(result.get("video_path", ""))
    assert video_path.exists(), f"Rendered video file not found at {video_path}"
    assert video_path.stat().st_size > 0, "Video file is empty"
    
    print(f"SUCCESS: Video successfully created! Size: {video_path.stat().st_size / (1024*1024):.2f} MB")
    
    all_vids = get_all_videos()
    print(f"Total videos tracked in registry: {len(all_vids)}")
    print("Verification completed successfully!")

if __name__ == "__main__":
    test_dry_run()
