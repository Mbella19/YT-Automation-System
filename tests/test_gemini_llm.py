import os
from dotenv import load_dotenv
import requests

load_dotenv()

def test_key(key_name, key_value):
    print(f"Testing {key_name}: {key_value[:10]}...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key_value}"
    response = requests.get(url)
    if response.status_code == 200:
        print(f"SUCCESS: {key_name} is valid.")
        return True
    else:
        print(f"FAILED: {key_name} returned {response.status_code}")
        print(response.text)
        return False

current_llm_key = os.getenv("GEMINI_API_KEY")
current_tts_key = os.getenv("GEMINI_TTS_API_KEY")

print("--- Testing Current LLM Key ---")
test_key("GEMINI_API_KEY", current_llm_key)

print("\n--- Testing New TTS Key for LLM ---")
test_key("GEMINI_TTS_API_KEY", current_tts_key)
