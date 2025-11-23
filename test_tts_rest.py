import requests
import json
import os

from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("GEMINI_TTS_API_KEY")
URL = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={API_KEY}"

data = {
    "input": {"text": "Hello, this is a test."},
    "voice": {"languageCode": "en-US", "name": "en-US-Studio-O"},
    "audioConfig": {"audioEncoding": "MP3"}
}

print(f"Testing API Key: {API_KEY[:10]}...")
response = requests.post(URL, json=data)

if response.status_code == 200:
    print("SUCCESS! API Key is working via REST.")
    with open("test_output.mp3", "wb") as f:
        f.write(response.content)
    print("Saved test_output.mp3")
else:
    print(f"FAILED: {response.status_code}")
    print(response.text)
