
import json
from utils.gemini_analyzer import GeminiVideoAnalyzer

# Mock the init to avoid needing API keys
class MockAnalyzer(GeminiVideoAnalyzer):
    def __init__(self):
        pass

analyzer = MockAnalyzer()

problematic_response = """Based on the provided script and the video footage, here is the matched scene list. The script provided in the prompt starts with the "runt" storyline, which corresponds to events starting around the 4-minute mark of the video. The scenes have been reordered to match the narrative flow of the script.

```json
{
  "scenes": [
    {
      "scene_number": 1,
      "start_time": "04:55",
      "end_time": "05:05",
      "duration_seconds": 10,
      "narration": "Most runts don't make it through their first season."
    }
  ]
}
```"""

print("Testing _extract_json_from_response with problematic response:")
try:
    result = analyzer._extract_json_from_response(problematic_response)
    print("SUCCESS")
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"FAILED: {e}")

print("\nTesting with clean JSON:")
clean_response = '{"scenes": []}'
try:
    result = analyzer._extract_json_from_response(clean_response)
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")

print("\nTesting with markdown only:")
markdown_response = '```json\n{"scenes": []}\n```'
try:
    result = analyzer._extract_json_from_response(markdown_response)
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
