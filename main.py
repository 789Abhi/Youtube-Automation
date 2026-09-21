import argparse
import sys
import os
import subprocess
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from modules.pipeline import run_video_pipeline
from config import DEFAULT_TTS_VOICE, DEFAULT_PRIVACY

def main():
    parser = argparse.ArgumentParser(description="AutoTube AI - Automated YouTube Video Generator & Uploader")
    parser.add_argument("--topic", type=str, help="Video topic or concept")
    parser.add_argument("--format", type=str, choices=["shorts", "standard"], default="shorts", help="Video format (shorts: 9:16, standard: 16:9)")
    parser.add_argument("--voice", type=str, default=DEFAULT_TTS_VOICE, help="TTS voice name")
    parser.add_argument("--privacy", type=str, choices=["unlisted", "private", "public"], default=DEFAULT_PRIVACY, help="YouTube upload privacy")
    parser.add_argument("--auto-upload", action="store_true", help="Upload to YouTube directly upon completion")
    parser.add_argument("--ui", action="store_true", help="Launch the Streamlit web dashboard")

    args = parser.parse_args()

    if args.ui:
        print("Launching AutoTube AI Web Dashboard on http://localhost:8501 ...")
        cmd = [sys.executable, "-m", "streamlit", "run", str(BASE_DIR / "app.py")]
        subprocess.run(cmd)
        return

    if not args.topic:
        print("No topic provided. Launching Web Dashboard...")
        cmd = [sys.executable, "-m", "streamlit", "run", str(BASE_DIR / "app.py")]
        subprocess.run(cmd)
        return

    print(f"\n=======================================================")
    print(f"🎬 Starting AutoTube Video Pipeline for: '{args.topic}'")
    print(f"Format: {args.format} | Voice: {args.voice} | Auto-Upload: {args.auto_upload}")
    print(f"=======================================================\n")

    result = run_video_pipeline(
        topic=args.topic,
        format_type=args.format,
        voice=args.voice,
        privacy_status=args.privacy,
        auto_upload=args.auto_upload
    )

    print("\n=======================================================")
    print(f"Status: {result.get('status')}")
    print(f"Video File: {result.get('video_path')}")
    if result.get('youtube_url'):
        print(f"YouTube Live Link: {result.get('youtube_url')}")
    print(f"=======================================================\n")

if __name__ == "__main__":
    main()
