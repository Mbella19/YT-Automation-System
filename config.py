"""
Configuration file for Video Editing Automation
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys - Load from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_TTS_API_KEY = os.getenv("GEMINI_TTS_API_KEY")

# Gemini model and client configuration
GEMINI_MODEL_NAME = "gemini-3-pro-preview"
GEMINI_API_VERSION = "v1beta"
GEMINI_THINKING_LEVEL = "high"

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

# Video processing settings
CLIP_DURATION_MIN = 15  # seconds
CLIP_DURATION_MAX = 40  # seconds

# Gemini TTS settings
GEMINI_TTS_MODEL = "gemini-2.5-flash-tts" # User requested model

# Gemini settings
GEMINI_TEMPERATURE = 1.0  # High creativity for long-form recap generation
GEMINI_TIMESTAMP_TEMPERATURE = 0.3  # Alignment call temperature
GEMINI_TWO_PASS_ANALYSIS = True  # Use two-pass analysis for better content sync (recommended but costs more)
GEMINI_API_DELAY_SECONDS = 60  # Delay between API calls (120s = 2 mins for free tier, 0 for paid tier)
GEMINI_API_MAX_RETRIES = 3  # Retry Gemini requests on transient failures
GEMINI_API_RETRY_BACKOFF_SECONDS = 5  # Base delay between retry attempts

# Video processing synchronization settings
AUDIO_START_DELAY_MS = 0  # Milliseconds of silence before narration starts (helps with perception)
USE_AUDIO_BASED_TIMING = True  # Use audio duration to determine clip length (recommended for perfect sync)

# Logging
LOG_FILE = BASE_DIR / "automation.log"

# Debug settings
SAVE_SCENES_JSON = True  # Save scene analysis to JSON file for review
VERBOSE_LOGGING = True  # Enable detailed logging for synchronization verification
