import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Output and storage directories
OUTPUT_DIR = BASE_DIR / "outputs"
VIDEO_DIR = OUTPUT_DIR / "videos"
AUDIO_DIR = OUTPUT_DIR / "audio"
CLIPS_DIR = OUTPUT_DIR / "clips"
DATA_DIR = BASE_DIR / "data"

for directory in [OUTPUT_DIR, VIDEO_DIR, AUDIO_DIR, CLIPS_DIR, DATA_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "video_registry.json"

# API Keys & Credentials
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
YOUTUBE_CLIENT_SECRET_FILE = os.getenv("YOUTUBE_CLIENT_SECRET_FILE", str(BASE_DIR / "client_secret.json"))
YOUTUBE_TOKEN_FILE = os.getenv("YOUTUBE_TOKEN_FILE", str(BASE_DIR / "token.pickle"))

# Defaults
DEFAULT_VEO_MODEL = os.getenv("VEO_MODEL", "veo-3.1-generate-preview")
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
DEFAULT_TTS_VOICE = os.getenv("DEFAULT_TTS_VOICE", "en-US-ChristopherNeural") # Natural, professional English
DEFAULT_PRIVACY = os.getenv("DEFAULT_PRIVACY", "unlisted") # unlisted, private, public
