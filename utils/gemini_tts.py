"""
Text-to-speech using Gemini's NATIVE TTS (generativelanguage API).

Why not Google Cloud TTS anymore?
  The old code called texttospeech.googleapis.com, which rejects API keys
  ("API keys are not supported by this API — expected OAuth2"). The new-format
  AI Studio Gemini keys only work against the generativelanguage endpoint, so we
  use Gemini's native speech generation here. This also matches the original
  config intent (GEMINI_TTS_MODEL = "gemini-*-tts").

Gemini TTS returns raw 16-bit PCM (mono, 24 kHz). We wrap it in a WAV header so
the file is directly readable by ffprobe/ffmpeg downstream.

Rate limiting: the TTS model has a very low free-tier quota (e.g. 3 requests/min),
so calls are paced and 429s are retried honoring the server-provided retry delay.
"""
import os
import re
import time
import wave
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from utils.logger import setup_logger

logger = setup_logger()

# Gemini native TTS emits signed 16-bit little-endian PCM.
_TTS_SAMPLE_WIDTH = 2      # bytes (16-bit)
_TTS_CHANNELS = 1          # mono
_DEFAULT_SAMPLE_RATE = 24000

# Retry these transient statuses (rate limit + server errors).
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _parse_sample_rate(mime_type, default=_DEFAULT_SAMPLE_RATE):
    """Pull the sample rate out of a mime type like 'audio/L16;rate=24000'."""
    if not mime_type:
        return default
    match = re.search(r"rate=(\d+)", mime_type)
    return int(match.group(1)) if match else default


def _retry_delay_from_error(exc, default):
    """
    Extract a suggested wait (seconds) from a 429 error. Gemini includes either
    'Please retry in 42.08s' or a 'retryDelay': '42s' field. Falls back to default.
    """
    text = str(exc)
    m = re.search(r"retry in ([\d.]+)s", text, re.IGNORECASE) \
        or re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?([\d.]+)s", text)
    if m:
        try:
            # Add a small cushion so we're safely past the window.
            return float(m.group(1)) + 1.0
        except ValueError:
            pass
    return default


def _is_daily_quota_exhausted(exc):
    """
    True if a 429 is a PER-DAY quota (e.g. free tier's 10 TTS requests/day).
    These won't clear for hours, so retrying is pointless — skip fast instead of
    waiting out the (misleading) per-minute retryDelay repeatedly.
    """
    text = str(exc)
    return "PerDay" in text or "RequestsPerDay" in text


class GeminiTTS:
    def __init__(self, api_key, model_name="gemini-2.5-flash-preview-tts",
                 voice_name="Kore", api_version="v1beta",
                 delay_seconds=0, max_retries=5, retry_backoff_seconds=20,
                 max_wait_seconds=120):
        """
        Initialize the Gemini native TTS client.

        Args:
            api_key: Gemini API key (AI Studio key works)
            model_name: A Gemini TTS model, e.g. 'gemini-2.5-flash-preview-tts'
            voice_name: A prebuilt Gemini voice, e.g. 'Kore', 'Puck', 'Charon'
            delay_seconds: Proactive pause between calls (helps low RPM tiers)
            max_retries: Attempts per call on transient (429/5xx) errors
            retry_backoff_seconds: Default backoff when the server gives no hint
        """
        self.api_key = api_key
        self.model_name = model_name
        self.voice_name = voice_name
        self.delay_seconds = max(delay_seconds, 0)
        self.max_retries = max(max_retries, 1)
        self.retry_backoff_seconds = max(retry_backoff_seconds, 1)
        self.max_wait_seconds = max(max_wait_seconds, 1)
        self._last_call_time = 0.0
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(api_version=api_version) if api_version else None,
        )
        logger.info(f"Gemini native TTS initialized (model={model_name}, voice={voice_name}, "
                    f"delay={self.delay_seconds}s, retries={self.max_retries})")

    def _wait_between_calls(self):
        """Respect a proactive minimum spacing between TTS calls."""
        if self.delay_seconds <= 0:
            return
        elapsed = time.time() - self._last_call_time
        if 0 < elapsed < self.delay_seconds and self._last_call_time > 0:
            time.sleep(self.delay_seconds - elapsed)

    def _synthesize(self, text):
        """Call Gemini TTS with retry/backoff; return (pcm_bytes, sample_rate)."""
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            self._wait_between_calls()
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=text,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=self.voice_name
                                )
                            )
                        ),
                    ),
                )
                self._last_call_time = time.time()

                for candidate in getattr(response, "candidates", []) or []:
                    content = getattr(candidate, "content", None)
                    for part in getattr(content, "parts", None) or []:
                        blob = getattr(part, "inline_data", None)
                        if blob and getattr(blob, "data", None):
                            return blob.data, _parse_sample_rate(getattr(blob, "mime_type", None))
                raise RuntimeError("Gemini TTS returned no audio content")

            except genai_errors.APIError as exc:
                self._last_call_time = time.time()
                status = getattr(exc, "code", None)
                if status is not None and status not in _RETRYABLE_STATUS:
                    raise
                last_error = exc
                # A daily-quota 429 won't clear for hours — don't burn retries
                # waiting out the per-minute hint repeatedly; give up now.
                if status == 429 and _is_daily_quota_exhausted(exc):
                    logger.error("TTS daily quota exhausted (free tier). Skipping without retry — "
                                 "enable billing to lift the daily limit.")
                    break
                if attempt >= self.max_retries:
                    break
                if status == 429:
                    wait = _retry_delay_from_error(exc, self.retry_backoff_seconds * attempt)
                else:
                    wait = self.retry_backoff_seconds * attempt
                # A wait longer than the cap signals a longer quota window (e.g.
                # daily limit) that retrying soon won't clear — give up now so the
                # scene is skipped instead of blocking the job for minutes/hours.
                if wait > self.max_wait_seconds:
                    logger.error(f"TTS 429 suggests waiting {wait:.0f}s (> cap {self.max_wait_seconds}s) — "
                                 f"treating as exhausted quota, not waiting.")
                    break
                logger.warning(f"TTS transient error {status} (attempt {attempt}/{self.max_retries}); "
                               f"waiting {wait:.0f}s...")
                time.sleep(wait)

        raise RuntimeError(f"TTS failed after {self.max_retries} attempts: {last_error}") from last_error

    def text_to_speech(self, text, output_path):
        """
        Convert text to speech and save as a WAV file.

        Args:
            text: Text to convert
            output_path: Path to save audio file (.wav)

        Returns:
            Path to saved audio file
        """
        pcm_bytes, sample_rate = self._synthesize(text)
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(_TTS_CHANNELS)
            wav_file.setsampwidth(_TTS_SAMPLE_WIDTH)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_bytes)
        return output_path

    def generate_audio_for_scenes(self, scenes_data, output_dir, skip_failed=True):
        """
        Generate audio for all scenes.

        Args:
            scenes_data: Dictionary containing scene information
            output_dir: Directory to save audio files
            skip_failed: If True, a scene that still fails after retries is skipped
                (its clip is omitted) rather than failing the whole job.

        Returns:
            List of dictionaries containing scene info and audio paths
        """
        audio_files = []
        scenes = scenes_data.get('scenes', [])
        failures = 0

        logger.info(f"Generating audio for {len(scenes)} scenes using Gemini native TTS")

        for i, scene in enumerate(scenes, 1):
            scene_num = scene.get('scene_number', i)
            narration = (scene.get('narration') or '').strip()

            if not narration:
                logger.warning(f"Skipping scene {scene_num}: No narration text")
                continue

            logger.info(f"Processing scene {i}/{len(scenes)} (narration length: {len(narration)} chars)")

            filename = f"scene_{scene_num:03d}.wav"
            audio_path = os.path.join(output_dir, filename)

            try:
                self.text_to_speech(narration, audio_path)
            except Exception as e:
                failures += 1
                if skip_failed:
                    logger.error(f"Scene {scene_num} audio failed after retries — skipping it: {e}")
                    continue
                logger.error(f"Error generating audio for scene {scene_num}: {e}")
                raise

            audio_files.append({
                'scene_number': scene_num,
                'audio_path': audio_path,
                'duration': scene.get('duration_seconds')
            })

        if not audio_files:
            raise RuntimeError(
                "No narration audio could be generated (all TTS calls failed — "
                "likely an exhausted quota). Check your Gemini plan/billing."
            )
        if failures:
            logger.warning(f"{failures} scene(s) had no audio and were skipped.")
        return audio_files
