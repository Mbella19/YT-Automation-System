import os
import config
from utils.gemini_tts import GeminiTTS

def test_tts():
    print("Testing Gemini TTS...")
    print(f"API Key present: {'Yes' if config.GEMINI_API_KEY else 'No'}")
    print(f"Model: {config.GEMINI_TTS_MODEL}")
    
    tts = GeminiTTS(api_key=config.GEMINI_API_KEY, model_name=config.GEMINI_TTS_MODEL)
    
    text = "This is a test of the Gemini Text to Speech system. If you can hear this, it is working correctly."
    output_file = "test_audio.mp3"
    
    try:
        print(f"Synthesizing text: '{text}'")
        tts.text_to_speech(text, output_file)
        print(f"Success! Audio saved to {output_file}")
        
        # Check if file exists and has size
        if os.path.exists(output_file):
            size = os.path.getsize(output_file)
            print(f"File size: {size} bytes")
        else:
            print("Error: File was not created.")
            
    except Exception as e:
        print(f"Error during TTS test: {e}")

if __name__ == "__main__":
    test_tts()
