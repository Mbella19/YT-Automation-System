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
"""
import os
import re
import wave
from google import genai
from google.genai import types
from utils.logger import setup_logger

logger = setup_logger()

# Gemini native TTS emits signed 16-bit little-endian PCM.
_TTS_SAMPLE_WIDTH = 2      # bytes (16-bit)
_TTS_CHANNELS = 1          # mono
_DEFAULT_SAMPLE_RATE = 24000


def _parse_sample_rate(mime_type, default=_DEFAULT_SAMPLE_RATE):
    """Pull the sample rate out of a mime type like 'audio/L16;rate=24000'."""
    if not mime_type:
        return default
    match = re.search(r"rate=(\d+)", mime_type)
    return int(match.group(1)) if match else default


class GeminiTTS:
    def __init__(self, api_key, model_name="gemini-2.5-flash-preview-tts",
                 voice_name="Kore", api_version="v1beta"):
        """
        Initialize the Gemini native TTS client.

        Args:
            api_key: Gemini API key (AI Studio key works)
            model_name: A Gemini TTS model, e.g. 'gemini-2.5-flash-preview-tts'
            voice_name: A prebuilt Gemini voice, e.g. 'Kore', 'Puck', 'Charon'
        """
        self.api_key = api_key
        self.model_name = model_name
        self.voice_name = voice_name
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(api_version=api_version) if api_version else None,
        )
        logger.info(f"Gemini native TTS initialized (model={model_name}, voice={voice_name})")

    def _synthesize(self, text):
        """Call Gemini TTS and return (pcm_bytes, sample_rate)."""
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

        # Find the first inline audio part.
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", None) or []:
                blob = getattr(part, "inline_data", None)
                if blob and getattr(blob, "data", None):
                    return blob.data, _parse_sample_rate(getattr(blob, "mime_type", None))

        raise RuntimeError("Gemini TTS returned no audio content")

    def text_to_speech(self, text, output_path):
        """
        Convert text to speech and save as a WAV file.

        Args:
            text: Text to convert
            output_path: Path to save audio file (.wav)

        Returns:
            Path to saved audio file
        """
        try:
            pcm_bytes, sample_rate = self._synthesize(text)

            with wave.open(str(output_path), "wb") as wav_file:
                wav_file.setnchannels(_TTS_CHANNELS)
                wav_file.setsampwidth(_TTS_SAMPLE_WIDTH)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm_bytes)

            return output_path
        except Exception as e:
            logger.error(f"Error in Gemini TTS: {str(e)}", exc_info=True)
            raise

    def generate_audio_for_scenes(self, scenes_data, output_dir):
        """
        Generate audio for all scenes in the scenes data.

        Args:
            scenes_data: Dictionary containing scene information
            output_dir: Directory to save audio files

        Returns:
            List of dictionaries containing scene info and audio paths
        """
        audio_files = []
        scenes = scenes_data.get('scenes', [])

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
                logger.error(f"Error generating audio for scene {scene_num}: {str(e)}")
                raise

            audio_files.append({
                'scene_number': scene_num,
                'audio_path': audio_path,
                'duration': scene.get('duration_seconds')
            })

        return audio_files
