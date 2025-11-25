import os
from google import genai
import config

print("--- v1beta Models ---")
try:
    client = genai.Client(api_key=config.GEMINI_API_KEY, http_options={'api_version': 'v1beta'})
    for model in client.models.list():
        if "flash" in model.name.lower():
            print(f"Name: {model.name}")
            print(f"Display Name: {model.display_name}")
            try:
                print(f"Supported Methods: {model.supported_generation_methods}")
            except:
                pass
            print("-" * 20)
except Exception as e:
    print(f"Error listing v1beta models: {e}")

print("\n--- v1alpha Models ---")
try:
    client = genai.Client(api_key=config.GEMINI_API_KEY, http_options={'api_version': 'v1alpha'})
    for model in client.models.list():
        if "flash" in model.name.lower():
            print(f"Name: {model.name}")
            print(f"Display Name: {model.display_name}")
            try:
                print(f"Supported Methods: {model.supported_generation_methods}")
            except:
                pass
            print("-" * 20)
except Exception as e:
    print(f"Error listing v1alpha models: {e}")
