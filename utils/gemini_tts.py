"""
Gemini TTS integration using Google Cloud Text-to-Speech API
"""
from google.cloud import texttospeech
from google.api_core import client_options
import os
from pathlib import Path
from utils.logger import setup_logger

logger = setup_logger()

import requests
import json
import base64
from utils.logger import setup_logger

logger = setup_logger()

class GeminiTTS:
    def __init__(self, api_key, model_name="gemini-2.5-flash-tts"):
        """
        Initialize Gemini TTS client using REST API
        
        Args:
            api_key: Google Cloud API Key
            model_name: TTS model name (e.g., 'gemini-2.5-flash-tts')
        """
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = "https://texttospeech.googleapis.com/v1/text:synthesize"
        
        logger.info(f"Gemini TTS initialized with model: {model_name} (REST API)")

    def text_to_speech(self, text, output_path):
        """
        Convert text to speech and save to file using REST API
        
        Args:
            text: Text to convert
            output_path: Path to save audio file
            
        Returns:
            Path to saved audio file
        """
        try:
            url = f"{self.base_url}?key={self.api_key}"
            
            data = {
                "input": {"text": text},
                "voice": {
                    "languageCode": "en-US",
                    "name": "en-US-Studio-O", # Default voice
                    # Note: model_name is not a standard field in v1 API but used for Gemini
                    # We'll stick to standard fields for now to ensure compatibility
                },
                "audioConfig": {
                    "audioEncoding": "MP3"
                }
            }
            
            response = requests.post(url, json=data)
            
            if response.status_code != 200:
                raise Exception(f"TTS API Error: {response.status_code} - {response.text}")
                
            response_json = response.json()
            audio_content = base64.b64decode(response_json["audioContent"])

            # Save the audio to file
            with open(output_path, "wb") as out:
                out.write(audio_content)
                
            return output_path

        except Exception as e:
            logger.error(f"Error in Gemini TTS: {str(e)}", exc_info=True)
            raise

    def generate_audio_for_scenes(self, scenes_data, output_dir):
        """
        Generate audio for all scenes in the scenes data
        
        Args:
            scenes_data: Dictionary containing scene information
            output_dir: Directory to save audio files
            
        Returns:
            List of dictionaries containing scene info and audio paths
        """
        audio_files = []
        scenes = scenes_data.get('scenes', [])
        
        logger.info(f"Generating audio for {len(scenes)} scenes using Gemini TTS")
        
        for i, scene in enumerate(scenes, 1):
            try:
                scene_num = scene.get('scene_number', i)
                narration = scene.get('narration', '').strip()
                
                if not narration:
                    logger.warning(f"Skipping scene {scene_num}: No narration text")
                    continue
                    
                logger.info(f"Processing scene {i}/{len(scenes)}")
                
                filename = f"scene_{scene_num:03d}.mp3"
                audio_path = os.path.join(output_dir, filename)
                
                logger.info(f"Converting text to speech (length: {len(narration)} chars)")
                self.text_to_speech(narration, audio_path)
                
                audio_files.append({
                    'scene_number': scene_num,
                    'audio_path': audio_path,
                    'duration': scene.get('duration_seconds')
                })
                
            except Exception as e:
                logger.error(f"Error generating audio for scene {scene_num}: {str(e)}")
                raise e
                
        return audio_files
