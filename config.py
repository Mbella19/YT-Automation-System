"""
Configuration file for Video Editing Automation
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def _env_bool(name, default):
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name, default):
    val = os.getenv(name)
    if val is None or not str(val).strip():
        return default
    try:
        return int(val)
    except ValueError:
        return default


# API Keys - Load from environment variables
# The new-format AI Studio keys ("AQ.*") authenticate the Gemini API for BOTH
# analysis and native text-to-speech, so a single key covers everything.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_TTS_API_KEY = os.getenv("GEMINI_TTS_API_KEY") or GEMINI_API_KEY

# Gemini model and client configuration
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-3.5-flash")
GEMINI_API_VERSION = os.getenv("GEMINI_API_VERSION", "v1beta")
GEMINI_THINKING_LEVEL = os.getenv("GEMINI_THINKING_LEVEL", "high")

# Directories
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
TEMP_DIR = BASE_DIR / "temp"
AUDIO_DIR = BASE_DIR / "audio"

# Create directories if they don't exist
for directory in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR, AUDIO_DIR]:
    directory.mkdir(exist_ok=True)

# FFmpeg settings
FFMPEG_PATH = "ffmpeg"  # Assumes ffmpeg is in PATH

# Clip length guidance (fed into the analysis/generation prompt)
CLIP_DURATION_MIN = _env_int("CLIP_DURATION_MIN", 5)   # seconds
CLIP_DURATION_MAX = _env_int("CLIP_DURATION_MAX", 20)  # seconds

# Gemini native TTS settings (uses the generativelanguage API, not Cloud TTS)
GEMINI_TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
GEMINI_TTS_VOICE = os.getenv("GEMINI_TTS_VOICE", "Kore")  # Prebuilt Gemini voice

# Gemini generation settings
# NOTE: alignment/timestamping wants deterministic output, so temperatures are low.
GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.7"))  # Narration/script generation
GEMINI_TIMESTAMP_TEMPERATURE = float(os.getenv("GEMINI_TIMESTAMP_TEMPERATURE", "0.0"))  # Alignment

# Autonomy: when no script is supplied, generate the recap directly from the video.
AUTO_GENERATE_SCRIPT = _env_bool("AUTO_GENERATE_SCRIPT", True)

# Rate limiting between Gemini API calls.
#   Free tier historically needs ~60s; paid/flash tiers can use a small value or 0.
#   The retry logic now also handles 429s, so a modest default is safe.
GEMINI_API_DELAY_SECONDS = _env_int("GEMINI_API_DELAY_SECONDS", 6)
GEMINI_API_MAX_RETRIES = _env_int("GEMINI_API_MAX_RETRIES", 3)
GEMINI_API_RETRY_BACKOFF_SECONDS = _env_int("GEMINI_API_RETRY_BACKOFF_SECONDS", 5)

# Video processing synchronization settings
AUDIO_START_DELAY_MS = _env_int("AUDIO_START_DELAY_MS", 0)  # Silence before narration starts
USE_AUDIO_BASED_TIMING = _env_bool("USE_AUDIO_BASED_TIMING", True)  # Clip length follows narration length

# YouTube upload settings (OAuth2 — API keys can't upload)
YOUTUBE_CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS", str(BASE_DIR / "client_secrets.json"))
YOUTUBE_TOKEN_FILE = os.getenv("YOUTUBE_TOKEN_FILE", str(BASE_DIR / "youtube_token.json"))
YOUTUBE_DEFAULT_PRIVACY = os.getenv("YOUTUBE_DEFAULT_PRIVACY", "private")  # private|unlisted|public

# Server settings
FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
FLASK_PORT = _env_int("FLASK_PORT", 5001)
FLASK_DEBUG = _env_bool("FLASK_DEBUG", False)
MAX_UPLOAD_MB = _env_int("MAX_UPLOAD_MB", 2048)  # Upload cap in MB (None-like: set 0 to disable)
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")  # Comma-separated origins, or "*"

# Logging
LOG_FILE = BASE_DIR / "automation.log"

# Debug settings
SAVE_SCENES_JSON = True  # Save scene analysis to JSON file for review
VERBOSE_LOGGING = True  # Enable detailed logging for synchronization verification
